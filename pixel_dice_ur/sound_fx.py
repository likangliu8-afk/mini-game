# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 4.8: Pure-Python procedural retro audio bank for Pixel Dice Ur.
# Every waveform is synthesized in-memory as 16-bit signed PCM (the `array`
# module) and wrapped in a pygame.mixer.Sound, so the project ships ZERO
# external .wav/.mp3 assets.
#
# Exposed API (every call is a silent no-op when no audio device is
# available, e.g. the headless SDL_VIDEODRIVER=dummy self-test run):
#   init_audio() -> bool   lazy mixer init + SFX bake (idempotent)
#   start_bgm()            start the ~9.7s seamless Phrygian-Dominant BGM loop
#   play(name)             one-shot SFX: dice_tick/dice_land/move/capture/bonus/score/win
#   toggle_mute() -> bool  flip mute state, returns the NEW state
#   is_muted() / is_enabled()
#
# BGM style: slow Babylonian Phrygian-Dominant (D Eb F# G A Bb C) motif over
# a D2 drone pad with a breathing LFO; all loop-critical oscillators use
# integer cycle counts so the loop point is perfectly seamless. Channel
# volume is kept at ~0.18 as specified.

import array
import math
import random

import pygame

SR = 44100            # mixer sample rate (mono, 16-bit)
BGM_SECONDS = 9.7     # loop length: 44 beats x ~0.22s
BGM_VOLUME = 0.18     # user-specified background-music loudness
_ENABLED = False      # True only when the mixer actually started
_MUTED = False
_BGM_WANTED = False   # restart the BGM automatically after un-muting
_BANK = {}            # sfx name -> pygame.mixer.Sound
_BGM_SOUND = None


# Triangle-wave sample from a fractional cycle phase, amplitude in [-1, 1].
# phase: oscillator phase in [0, 1).
def _tri(phase):
    return 4.0 * abs(phase - 0.5) - 1.0


# Attack/hold/release envelope value at time t inside a note of length dur.
# t: seconds from note start; att/rel: attack and release durations in s;
# dur: total note duration in s.
def _env(t, att, rel, dur):
    if t < att:
        return t / att if att > 0.0 else 1.0
    if t > dur - rel:
        return max(0.0, (dur - t) / rel) if rel > 0.0 else 0.0
    return 1.0


# Clamp and quantize one float sample into the 16-bit signed destination buffer.
# buf: array('h'); i: write index; v: float sample in any range (clamped).
def _put(buf, i, v):
    if v > 1.0:
        v = 1.0
    elif v < -1.0:
        v = -1.0
    buf[i] = int(v * 32000)


# Synthesize a short pitch-swept pluck tone.
# f0/f1: start and end frequency in Hz; dur: length in s; shape: "tri" or "sine";
# vol: peak amplitude 0..1.
def _tone(f0, f1, dur, shape, vol):
    n = int(dur * SR)
    buf = array.array("h", [0]) * n
    ph = 0.0
    for i in range(n):
        t = i / float(SR)
        f = f0 + (f1 - f0) * (i / max(1, n - 1))
        ph += 2.0 * math.pi * f / SR
        amp = vol * math.exp(-4.5 * t / max(1e-6, dur))
        frac = ph % (2.0 * math.pi) / (2.0 * math.pi)
        v = _tri(frac) if shape == "tri" else math.sin(ph)
        _put(buf, i, v * amp)
    return buf


# Synthesize a white-noise impact burst with a one-pole low-pass and exponential decay.
# dur: seconds; vol: peak amplitude; cut: low-pass smoothing 0..1 (higher = brighter).
def _noise(dur, vol, cut):
    n = int(dur * SR)
    buf = array.array("h", [0]) * n
    rng = random.Random(99)
    prev = 0.0
    for i in range(n):
        t = i / float(SR)
        x = rng.uniform(-1.0, 1.0)
        prev += cut * (x - prev)
        _put(buf, i, prev * vol * math.exp(-7.0 * t / max(1e-6, dur)))
    return buf


# Concatenate PCM buffers in order (for arpeggio chains).
# parts: tuple of array('h') buffers.
def _chain(*parts):
    out = array.array("h")
    for p in parts:
        out.extend(p)
    return out


# Build the BGM loop buffer: D2 drone pad + 44-beat Phrygian-Dominant motif +
# root-note bass plucks. Integer cycle counts on pad/LFO make the loop seamless.
# n: total sample count of the loop.
def _build_bgm(n):
    buf = array.array("h", [0]) * n
    two_pi = 2.0 * math.pi
    pad_hz = 73.416                                   # D2 drone
    pad_step = two_pi * int(pad_hz * n / SR) / n      # integer cycles -> seamless
    lfo_step = two_pi * 4 / n                         # 4 breathing swells per loop
    scale = [293.66, 311.13, 369.99, 392.0, 440.0, 466.16, 523.25]  # D Eb F# G A Bb C
    seq = [0, 1, 2, 3, 4, 6, 5, 4, 3, 2, 0, 2, 4, 2, 1, 4, 3, 2, 3, 4, 0]
    beat = n // 44
    notes = []
    pos = 0
    for deg in seq:
        notes.append((pos * beat, beat * 2, scale[deg]))
        pos += 2
    notes.append((pos * beat, beat * 4, scale[0]))    # final D cadence
    bass = [notes[i] for i in range(0, len(notes), 5)]
    np_, nb = len(notes), len(bass)
    pi = bi = 0
    pad_ph = lfo_ph = 0.0
    for i in range(n):
        pad_ph += pad_step
        lfo_ph += lfo_step
        v = 0.17 * (0.55 + 0.45 * math.sin(lfo_ph)) * math.sin(pad_ph)
        while pi + 1 < np_ and i >= notes[pi + 1][0]:
            pi += 1
        s0, dur, f = notes[pi]
        if s0 <= i < s0 + dur:
            t = (i - s0) / float(SR)
            v += 0.40 * _env(t, 0.03, 0.14, dur / SR) * _tri((f * t) % 1.0)
        while bi + 1 < nb and i >= bass[bi + 1][0]:
            bi += 1
        s0b, durb, fb = bass[bi]
        if s0b <= i < s0b + durb:
            tb = (i - s0b) / float(SR)
            v += 0.34 * _env(tb, 0.02, 0.10, durb / SR) * math.sin(fb * 0.5 * tb * two_pi)
        _put(buf, i, v)
    peak = 0
    for x in buf:
        ax = -x if x < 0 else x
        if ax > peak:
            peak = ax
    if peak > 0:
        gain = 18000 // peak
        if gain > 1:
            for i in range(n):
                buf[i] = buf[i] * gain
    return buf


# Lazily initialize the mixer (force 44100 / -16 / mono so Sound(buffer=)
# always matches) and bake all one-shot SFX. Safe to call repeatedly;
# returns True when audio is actually available, else silent no-op state.
def init_audio():
    global _ENABLED
    if _ENABLED:
        return True
    try:
        fmt = pygame.mixer.get_init()
        if fmt != (SR, -16, 1):
            pygame.mixer.quit()
            try:
                pygame.mixer.pre_init(SR, -16, 1, 256)
            except Exception:
                pass
            pygame.mixer.init()
        else:
            pygame.mixer.init()
        bank = {
            "dice_tick": _chain(_tone(3200.0, 2400.0, 0.05, "tri", 0.5),
                                _noise(0.03, 0.22, 0.6)),
            "dice_land": _chain(_tone(120.0, 58.0, 0.12, "sine", 0.85),
                                _noise(0.07, 0.40, 0.35)),
            "move": _tone(560.0, 880.0, 0.09, "tri", 0.5),
            "capture": _chain(_tone(320.0, 68.0, 0.30, "sine", 0.9),
                              _noise(0.18, 0.50, 0.5)),
            "bonus": _chain(_tone(293.66, 293.66, 0.09, "tri", 0.5),
                            _tone(440.0, 440.0, 0.09, "tri", 0.5),
                            _tone(587.33, 587.33, 0.09, "tri", 0.5),
                            _tone(739.99, 739.99, 0.14, "tri", 0.5)),
            "score": _chain(_tone(587.33, 587.33, 0.07, "tri", 0.5),
                            _tone(739.99, 739.99, 0.07, "tri", 0.5),
                            _tone(880.0, 880.0, 0.07, "tri", 0.5),
                            _tone(1046.5, 1046.5, 0.16, "tri", 0.5),
                            _noise(0.22, 0.12, 0.8)),
            "win": _chain(_tone(587.33, 587.33, 0.14, "tri", 0.55),
                          _tone(739.99, 739.99, 0.14, "tri", 0.55),
                          _tone(880.0, 880.0, 0.14, "tri", 0.55),
                          _tone(1174.7, 1174.7, 0.55, "tri", 0.55),
                          _noise(0.40, 0.10, 0.75)),
        }
        for name, pcm in bank.items():
            snd = pygame.mixer.Sound(buffer=pcm.tobytes())
            snd.set_volume(0.5)
            _BANK[name] = snd
        _ENABLED = True
    except Exception:
        _ENABLED = False
    return _ENABLED


# Start the seamless BGM loop at ~0.18 volume; builds the 10s buffer on first use.
# No-op when the mixer is unavailable or currently muted.
def start_bgm():
    global _BGM_WANTED, _BGM_SOUND
    _BGM_WANTED = True
    if not _ENABLED or _MUTED:
        return
    try:
        if _BGM_SOUND is None:
            _BGM_SOUND = pygame.mixer.Sound(buffer=_build_bgm(int(BGM_SECONDS * SR)).tobytes())
            _BGM_SOUND.set_volume(BGM_VOLUME)
        if _BGM_SOUND.get_num_channels() == 0:
            _BGM_SOUND.play(loops=-1)
    except Exception:
        _BGM_SOUND = None


# Play one one-shot SFX by key; silent no-op when muted or audio unavailable.
# name: one of the seven SFX keys in _BANK.
def play(name):
    if _ENABLED and not _MUTED:
        snd = _BANK.get(name)
        if snd is not None:
            snd.play()


# Flip the global mute state. Muting stops the BGM; un-muting restarts it
# when it was previously wanted. Returns the NEW muted state.
def toggle_mute():
    global _MUTED
    _MUTED = not _MUTED
    if _ENABLED:
        if _MUTED:
            if _BGM_SOUND is not None:
                _BGM_SOUND.stop()
        elif _BGM_WANTED:
            start_bgm()
    return _MUTED


# Current mute flag.
def is_muted():
    return _MUTED


# True only when the mixer actually initialized and the SFX bank was baked.
def is_enabled():
    return _ENABLED


# Convenience one-shots bound directly to game events in main.py.
# Play the short dice-shuffle blip at the start of the 260 ms tumble.
def dice_tick():
    play("dice_tick")


# Play the heavy "clack" when the 3D dice face locks onto its final value.
def dice_land():
    play("dice_land")


# Play the soft slide click when any token steps onto a new tile.
def move_sfx():
    play("move")


# Play the capture blast when a war-zone tile absorbs an enemy piece.
def capture_sfx():
    play("capture")


# Play the shimmering rune chime when a shield tile (4 or 8) grants a bonus turn.
def bonus_sfx():
    play("bonus")


# Play the rising arpeggio when a token lands on the Golden Shrine (tile 10).
def score_sfx():
    play("score")


# Play the victory fanfare when all three tokens of one side score.
def win_sfx():
    play("win")


if __name__ == "__main__":
    import os
    import sys

    # Headless silent-degradation self-test: must never raise, even with no audio device.
    if os.environ.get("SDL_VIDEODRIVER") != "dummy":
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    enabled = init_audio()
    start_bgm()
    for name in ("dice_tick", "dice_land", "move", "capture", "bonus", "score", "win"):
        play(name)
    toggle_mute()
    assert is_muted() is True
    toggle_mute()
    assert is_muted() is False
    start_bgm()
    print(f"[sound_fx self-test] OK: enabled={enabled}, muted={is_muted()} (headless safe, no exceptions)")
    pygame.quit()
