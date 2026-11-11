# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 3: VFX manager - pixelfx sprite-sheet playback + procedural pixel fallback + screen shake.
#
# The four effect pairs in assets/vfx/ are STATIC assets baked offline from the
# open-source patch-gg/pixelfx repo (MIT) with:
#   node tools/render.mjs <id> --sheet --no-actor
#   dice_roll      <- arcane/mana-burst            (one-shot magical burst)
#   hit_explosion  <- explosions/small-explosion   (one-shot capture explosion)
#   rune_glow      <- arcane/rune-circle           (loopable rune tile aura)
#   score_burst    <- ui/confetti                  (one-shot finish celebration)
# Each .json is Aseprite-style: per-frame {x, y, w, h} + duration(ms), and
# meta.pixelfx carries fps, loop, frameSize and the pivot anchor [px, py].

import json
import math
import os
import random
import sys

import pygame

# effect names shipped with the game (must match the file names in assets/vfx)
VFX_NAMES = ("dice_roll", "hit_explosion", "rune_glow", "score_burst")

# screen-shake presets per effect name: (duration_ms, intensity_px)
SHAKE_PRESETS = {
    "hit_explosion": (220, 6),   # a capture should hit hard
    "score_burst": (120, 3),     # a finish is a light celebration pop
    "rune_glow": (120, 3),       # landing on a rune tile is a soft thud
}

# procedural fallback geometry: 48x48 low-res hard-edge frames upscaled 2x
FALLBACK_FRAMES = 12
FALLBACK_FRAME_MS = 33           # same 30 fps cadence as the baked sheets
FALLBACK_SIZE = (96, 96)
FALLBACK_PIVOT = (48, 48)        # centred pivot so a fallback drops in where the real effect would
FALLBACK_PALETTES = {
    "dice_roll": [(255, 255, 255), (160, 200, 255), (220, 240, 255)],
    "hit_explosion": [(255, 240, 180), (255, 160, 60), (255, 90, 40)],
    "rune_glow": [(200, 140, 255), (150, 90, 220), (240, 220, 255)],
    "score_burst": [(255, 90, 90), (90, 255, 120), (255, 230, 90), (120, 180, 255)],
}


# One baked effect: all of its frames, per-frame durations and the pivot anchor.
# frames: list of pygame Surface (unscaled, cropped from the sheet); durations_ms:
# per-frame playback time in ms; pivot: [px, py] anchor inside one frame;
# loop: whether the source effect is designed to cycle; is_fallback: True when the
# frames were generated procedurally because the PNG assets are missing.
class Effect:
    def __init__(self, name, frames, durations_ms, pivot, loop, is_fallback=False):
        self.name = name
        self.frames = frames
        self.durations_ms = durations_ms
        self.pivot = tuple(pivot)
        self.loop = loop
        self.is_fallback = is_fallback
        self._scaled_cache = {}   # scale factor -> list of pre-scaled frames

    # Return every frame scaled to the given factor (cached per effect).
    # scale: float multiplier applied to both axes; pygame.transform.scale uses
    # nearest-neighbour by default so the upscaled pixels stay hard-edged.
    def get_scaled(self, scale):
        key = round(scale, 3)
        if key not in self._scaled_cache:
            sized = (max(1, int(self.frames[0].get_width() * key)),
                     max(1, int(self.frames[0].get_height() * key)))
            self._scaled_cache[key] = [pygame.transform.scale(f, sized) for f in self.frames]
        return self._scaled_cache[key]


# Write one pixel onto a low-res fallback surface, silently ignoring out-of-bounds
# points so the ring/flare math never has to special-case the border.
# low: the 48x48 SRCALPHA surface; x, y: the pixel to write; color: RGBA tuple.
def _put(low, x, y, color):
    if 0 <= x < low.get_width() and 0 <= y < low.get_height():
        low.set_at((x, y), color)


# Draw one procedural fallback frame.
# name: which effect look to fake; frame: 0-based frame index; t: normalized progress
# 0..1 (frame / 11) used for growth and fade; palette: the color ramp for this effect.
# Returns a 48x48 SRCALPHA surface with hard pixel edges.
def _draw_fallback_frame(name, frame, t, palette):
    low = pygame.Surface((48, 48), pygame.SRCALPHA)
    rng = random.Random(f"{name}-{frame}")   # seeded so the fallback is deterministic
    cx = cy = 24
    if name in ("dice_roll", "hit_explosion"):
        # expanding ring + fading core: the burst rolls out then dissipates
        radius = 3 + int(t * 15)
        fade = 255 - int(t * 180)
        core = min(radius // 3, 6)
        if core > 0:
            pygame.draw.circle(low, (255, 255, 255), (cx, cy), core)
        pygame.draw.circle(low, palette[0], (cx, cy), radius, width=2)
        pygame.draw.circle(low, palette[1], (cx, cy), max(1, radius - 2), width=1)
        for _ in range(6):
            a = rng.random() * math.tau
            _put(low, int(cx + math.cos(a) * (radius + 2 + rng.randint(0, 4))),
                 int(cy + math.sin(a) * (radius + 2 + rng.randint(0, 4))),
                 (*palette[2 % len(palette)], fade))
    elif name == "rune_glow":
        # a steady ring with 8 orbiting motes: stepping the angle per frame makes the loop
        pygame.draw.circle(low, palette[1], (cx, cy), 14, width=2)
        for i in range(8):
            a = (i / 8) * math.tau + frame * 0.785
            _put(low, int(cx + math.cos(a) * 14), int(cy + math.sin(a) * 14), palette[0])
        for _ in range(4):
            _put(low, cx + rng.randint(-10, 10), cy + rng.randint(-10, 10), palette[2])
    else:
        # confetti: 10 colored dots arcing up then drifting down, classic celebration look
        for i in range(10):
            px = cx + rng.randint(-16, 16)
            py = cy + int(t * 20) + rng.randint(-6, 2)   # rising arc over time
            color = palette[i % len(palette)]
            _put(low, px, py, color)
            _put(low, px, py - 1, color)
    return low


# Build the procedural pixel fallback for a missing asset pair.
# name: which effect to fake; the result is 12 hard-edge frames of 33 ms each,
# centred pivot, and loop=True only for rune_glow (the only loopable baked effect).
def _make_fallback_effect(name):
    palette = FALLBACK_PALETTES.get(name, FALLBACK_PALETTES["dice_roll"])
    low_frames = [_draw_fallback_frame(name, f, f / (FALLBACK_FRAMES - 1), palette)
                  for f in range(FALLBACK_FRAMES)]
    frames = [pygame.transform.scale(sf, FALLBACK_SIZE) for sf in low_frames]
    return Effect(name, frames, [FALLBACK_FRAME_MS] * FALLBACK_FRAMES,
                  FALLBACK_PIVOT, name == "rune_glow", is_fallback=True)


# Load "<name>.png" + "<name>.json" from assets_dir.
# name: effect file name without extension; assets_dir: the folder to read from.
# Returns an Effect, or None when either file is missing (the caller falls back).
# meta.image is ignored on purpose: it still holds the original pixelfx preset
# name (e.g. "mana-burst.png"), not our renamed file.
def _load_effect_from_disk(name, assets_dir):
    png_path = os.path.join(assets_dir, name + ".png")
    json_path = os.path.join(assets_dir, name + ".json")
    if not (os.path.isfile(png_path) and os.path.isfile(json_path)):
        return None
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    sheet = pygame.image.load(png_path)
    # convert_alpha() needs a display surface to exist; with a plain SDL context the
    # regular loaded surface works fine, so only convert when a display is up
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert_alpha()
    frames, durations = [], []
    frame_wh = (0, 0)   # size of the most recent frame, used as a pivot default
    for entry in data.get("frames", []):
        # crop each frame with its {x, y, w, h} rect from the Aseprite JSON and COPY it
        # out into its own surface: subsurface would keep referencing the whole sheet
        # pixels (and even the dark background buffer), so the copies stay lightweight
        # and the big sheet can be released
        fr = entry["frame"]
        w, h = int(fr["w"]), int(fr["h"])
        frame_wh = (w, h)
        tile = pygame.Surface((w, h), pygame.SRCALPHA)
        tile.blit(sheet, (-int(fr["x"]), -int(fr["y"])))
        frames.append(tile)
        durations.append(entry.get("duration", 33))
    fx = data.get("meta", {}).get("pixelfx", {})
    pivot = tuple(fx.get("pivot", (frame_wh[0] // 2, frame_wh[1] // 2)))
    loop = bool(fx.get("loop", False))
    return Effect(name, frames, durations, pivot, loop)


# One playing instance of an effect at a fixed board position.
# effect: the Effect to play; x, y: board-space point where the effect pivot should
# sit; scale: size factor (the pivot is scaled by the same factor); loop: wrap the
# frame list instead of stopping; max_ms: optional hard stop in ms (None = play the
# whole sequence once and stay on the last frame until it finishes).
class ActiveEffect:
    def __init__(self, effect, x, y, scale, loop, max_ms):
        self.effect = effect
        self.x, self.y = int(x), int(y)
        self.scale = scale
        self.loop = loop
        self.max_ms = max_ms
        self.elapsed_ms = 0.0
        self.frame_idx = 0
        self.frame_clock_ms = 0.0
        self.done = False
        # pivot in scaled frame pixels: the anchor keeps pointing at the same game spot
        self.pivot_x = effect.pivot[0] * scale
        self.pivot_y = effect.pivot[1] * scale

    # Advance playback by dt milliseconds of real time.
    # dt_ms: time that passed since the last update; frame_clock_ms accumulates inside
    # the current frame and rolls the index forward (or wraps when loop is set).
    def update(self, dt_ms):
        self.elapsed_ms += dt_ms
        if self.max_ms is not None and self.elapsed_ms >= self.max_ms:
            self.done = True
            return
        n = len(self.effect.durations_ms)
        self.frame_clock_ms += dt_ms
        while self.frame_clock_ms >= self.effect.durations_ms[self.frame_idx]:
            self.frame_clock_ms -= self.effect.durations_ms[self.frame_idx]
            if self.frame_idx + 1 >= n:
                if self.loop:
                    self.frame_idx = 0
                else:
                    self.frame_idx = n - 1   # hold the final frame until it times out
                    self.done = True
                    return
            else:
                self.frame_idx += 1


class VFXManager:
    # Build the manager.
    # assets_dir: folder holding "<effect>.png/.json" pairs; None = the assets/vfx
    # directory next to this file. default_scale: size factor applied to every spawn
    # that does not pass its own scale (the baked frames are large, so 0.65 fits a
    # 640-wide board with big pivots like hit_explosion's 300x240 still under the piece).
    def __init__(self, assets_dir=None, default_scale=0.65):
        if assets_dir is None:
            assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "vfx")
        self.assets_dir = assets_dir
        self.default_scale = default_scale
        self._effects = {}      # name -> Effect cache (disk load or fallback)
        self._active = []       # ActiveEffect instances still playing
        self._shake_left_ms = 0.0   # remaining shake time
        self._shake_total_ms = 0.0  # original shake time, used to fade intensity down
        self._shake_intensity = 0   # max random offset in px
        self._shake_ox = 0          # current random offsets (ints)
        self._shake_oy = 0

    # Return the cached Effect for name, loading it on first use.
    # name: one of the shipped effect names; when its PNG/JSON pair is missing from
    # assets_dir the procedural fallback is built instead so the game still runs
    # with zero hard errors.
    def load_effect(self, name):
        if name not in self._effects:
            effect = _load_effect_from_disk(name, self.assets_dir)
            if effect is None:
                print(f"[vfx] {name}: assets missing, using procedural pixel fallback")
                effect = _make_fallback_effect(name)
            self._effects[name] = effect
        return self._effects[name]

    # Start playing one effect at board position (x, y).
    # effect_name: which effect to play; x, y: where its pivot anchor should sit on
    # screen; loop: play forever (default False - even the loopable rune_glow only
    # auto-stops at max_duration_ms=1500 unless loop=True is passed explicitly);
    # max_duration_ms: optional hard stop in ms; scale: optional size override for
    # this spawn only. Returns the ActiveEffect instance.
    def spawn(self, effect_name, x, y, loop=False, max_duration_ms=None, scale=None):
        scale = self.default_scale if scale is None else scale
        # the rune tile must not stay lit forever on a normal landing
        if effect_name == "rune_glow" and not loop and max_duration_ms is None:
            max_duration_ms = 1500
        effect = self.load_effect(effect_name)
        active = ActiveEffect(effect, x, y, scale, loop, max_duration_ms)
        self._active.append(active)
        # impact feedback: captures shake hard, scoring and rune landings shake lightly
        preset = SHAKE_PRESETS.get(effect_name)
        if preset:
            self.trigger_shake(preset[0], preset[1])
        return active

    # (Re)start the screen shake.
    # duration_ms: how long the shake lasts; intensity: max random offset in pixels.
    # A weaker shake never overwrites a stronger one that is still running.
    def trigger_shake(self, duration_ms=180, intensity=5):
        if duration_ms > self._shake_left_ms or intensity >= self._shake_intensity:
            self._shake_left_ms = float(duration_ms)
            self._shake_total_ms = float(duration_ms)
            self._shake_intensity = intensity

    # Advance every active effect and decay the screen shake.
    # dt_ms: milliseconds since the previous update call (e.g. the pygame frame delta).
    def update(self, dt_ms):
        for active in self._active:
            active.update(dt_ms)
        self._active = [a for a in self._active if not a.done]
        # shake: random offset that scales down linearly as the remaining time runs out
        if self._shake_left_ms > 0:
            self._shake_left_ms = max(0.0, self._shake_left_ms - dt_ms)
            progress = self._shake_left_ms / self._shake_total_ms if self._shake_total_ms else 0.0
            amp = int(round(self._shake_intensity * progress))
            self._shake_ox = random.randint(-amp, amp) if amp else 0
            self._shake_oy = random.randint(-amp, amp) if amp else 0
        else:
            self._shake_ox = self._shake_oy = 0

    # Return the current shake offset in integer pixels.
    # The main loop adds this to whatever it draws (or to the VFX draw offset) so the
    # whole view jumps while a capture or score lands.
    def get_shake_offset(self):
        return (self._shake_ox, self._shake_oy)

    # Blit every active effect onto surface.
    # surface: the destination pygame Surface; offset: extra (ox, oy) the caller
    # already applies (typically the board camera offset); the global shake is added
    # on top, and each frame is positioned through its own scaled pivot so the effect
    # stays anchored exactly at the (x, y) it was spawned with.
    def draw(self, surface, offset=(0, 0)):
        ox = offset[0] + self._shake_ox
        oy = offset[1] + self._shake_oy
        for active in self._active:
            frames = active.effect.get_scaled(active.scale)
            frame = frames[active.frame_idx]
            surface.blit(frame, (active.x + ox - active.pivot_x, active.y + oy - active.pivot_y))

    # Stop all playing effects immediately (e.g. on game over or restart).
    def clear(self):
        self._active = []


if __name__ == "__main__":
    # Headless self-test: SDL_VIDEODRIVER=dummy gives a real display surface without a
    # window, so convert_alpha() and every pygame call below run exactly like in-game.
    import tempfile

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    screen = pygame.display.set_mode((640, 360))
    step_ms = 16   # ~60 fps, the same cadence the Pygame main loop will use

    # --- real assets: every shipped pair must load from disk, never fall back ---
    mgr = VFXManager()
    for name in VFX_NAMES:
        effect = mgr.load_effect(name)
        assert not effect.is_fallback, f"{name} should load from disk"
        sx = effect.pivot[0] * mgr.default_scale
        sy = effect.pivot[1] * mgr.default_scale
        print(f"[load] {name}: {len(effect.frames)} frames, loop={effect.loop}, "
              f"pivot {effect.pivot} -> scaled pivot ({sx:.1f}, {sy:.1f}) @ scale {mgr.default_scale}")

    # --- spawn / update / draw full flow over the real assets ---
    mgr.spawn("dice_roll", 320, 180)
    mgr.spawn("hit_explosion", 200, 150)
    assert mgr._shake_intensity == 6 and mgr._shake_total_ms == 220, "capture must trigger the strong shake"
    mgr.spawn("rune_glow", 420, 220)                     # default bounded play (1500 ms)
    mgr.spawn("score_burst", 500, 120)
    mgr.spawn("dice_roll", 100, 300, scale=1.0)          # per-spawn scale override
    assert len(mgr._active) == 5
    # longest bounded effect is hit_explosion (163 frames * 33 ms = 5.4 s), so a 6.4 s
    # window guarantees every non-looping effect the test spawned has fully finished
    for _ in range(400):
        mgr.update(step_ms)
        mgr.draw(screen, (0, 0))
    assert mgr._active == [], "all bounded effects should have finished"
    assert mgr.get_shake_offset() == (0, 0), "shake should decay to zero"

    # --- loop=True keeps the rune circle playing indefinitely ---
    mgr.spawn("rune_glow", 320, 200, loop=True)
    for _ in range(300):
        mgr.update(step_ms)
        mgr.draw(screen, (0, 0))
    assert len(mgr._active) == 1, "a looping effect must survive the 4.8 s test window"
    mgr.clear()

    # --- fallback: point an empty dir at the manager and everything still runs ---
    with tempfile.TemporaryDirectory() as empty_dir:
        mgr2 = VFXManager(assets_dir=empty_dir)
        for name in VFX_NAMES:
            effect = mgr2.load_effect(name)
            assert effect.is_fallback, f"{name} should fall back procedurally"
            assert len(effect.frames) == FALLBACK_FRAMES, f"{name} fallback frame count"
            assert effect.pivot == FALLBACK_PIVOT, f"{name} fallback pivot"
        mgr2.spawn("hit_explosion", 100, 100)
        mgr2.spawn("rune_glow", 200, 200, loop=True)
        for _ in range(300):
            mgr2.update(step_ms)
            mgr2.draw(screen, (4, 4))   # caller offset also flows through draw()
        assert len(mgr2._active) == 1, "fallback bounded effect finished, loop survives"
        mgr2.clear()

    print("[self-test] all VFX checks passed (real assets + spawn/update/draw + fallback)")
