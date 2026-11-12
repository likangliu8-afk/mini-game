# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 4.6: pre-baked pixel-art bank for the retro UI. Every texture is painted
# pixel by pixel at low resolution and scaled up with nearest-neighbour, so the
# game gets a hard-edged indie look with zero external art assets. All baking
# happens once at startup; the main loop only blits cached surfaces.
# Phase 4.6: _bake_dock now computes slot recesses from a caller-supplied
# slot_size/gap and the shared slot_centers() helper keeps the baked recess
# centres and main.py's piece anchors on one identical formula.

import math
import random

import pygame

TILE_SRC = 28      # tiles are painted at 28x28 and scaled 3x to 84x84
TILE_SCALE = 3


# Set one pixel on a surface, ignoring out-of-range writes so the pattern math
# never needs boundary checks. s: destination surface; x, y: pixel coordinate;
# c: RGB color tuple.
def _px(s, x, y, c):
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((x, y), c)


# Mix two RGB colors toward each other. a, b: RGB tuples; t: weight of b in [0, 1].
def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


_font_cache = {}
# Return a cached default bitmap font. size: font height in pixels.
def _font(size):
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]


# Lane motif: four small dark diamond pips in a 2x2 arrangement (lapis look).
# s: the 28x28 tile surface; tone: the darker diamond color.
def _pat_lane(s, tone):
    for cx, cy in ((8, 8), (20, 8), (8, 20), (20, 20)):
        _px(s, cx, cy - 1, tone)
        _px(s, cx - 1, cy, tone)
        _px(s, cx, cy, tone)
        _px(s, cx + 1, cy, tone)
        _px(s, cx, cy + 1, tone)


# War-zone motif: two crossed blade diagonals plus a few battle-scar nicks.
# s: the 28x28 tile surface (colors are fixed to the obsidian palette).
def _pat_war(s):
    blade = (96, 44, 52)
    ink = (18, 12, 16)
    for i in range(4, TILE_SRC - 4):
        _px(s, i, i, blade)                    # main diagonal
        _px(s, TILE_SRC - 1 - i, i, blade)     # anti-diagonal
    for i in (7, 13, 19):
        _px(s, i, TILE_SRC - 4 - i, ink)       # chip marks along the blades


# Rune motif: a Babylonian eight-point rosette - gold rays, a purple ring of
# pips and a cyan core. s: the 28x28 tile surface.
def _pat_rune(s):
    gold = (240, 200, 80)
    ring = (190, 140, 230)
    cyan = (120, 220, 230)
    cx = cy = 14
    for k in range(8):
        ang = k * math.pi / 4
        dx, dy = int(round(math.cos(ang))), int(round(math.sin(ang)))
        for r in range(4, 10):                 # the eight rays
            _px(s, cx + dx * r, cy + dy * r, gold)
    for k in range(16):                        # the outer ring of pips
        ang = k * math.pi / 8
        _px(s, cx + int(round(math.cos(ang) * 11)), cy + int(round(math.sin(ang) * 11)), ring)
    for ddx in (-1, 0, 1):                     # the cyan core
        for ddy in (-1, 0, 1):
            if abs(ddx) + abs(ddy) <= 1:
                _px(s, cx + ddx, cy + ddy, cyan)


# Finish motif: a golden stepped temple with a green gem on top.
# s: the 28x28 tile surface.
def _pat_finish(s):
    gold = (214, 178, 84)
    bright = (246, 222, 130)
    green = (110, 220, 140)

    def tier(x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                _px(s, x, y, gold)
        for x in range(x0, x1 + 1):            # lit top edge of each tier
            _px(s, x, y0, bright)

    tier(5, 20, 22, 26)
    tier(8, 14, 19, 19)
    tier(11, 8, 16, 13)
    for y in range(4, 8):
        for x in range(12, 16):
            _px(s, x, y, green)
    _px(s, 13, 5, (230, 255, 220))             # gem sparkle


# Bake one 84x84 tile texture from a 28x28 pixel painting: base stone color,
# seeded speckle, the motif, a bevel (light top/left, dark bottom/right) and
# four metal corner pips.
# base: main stone color; hi/lo: bevel light/shadow; corner: metal dot color;
# pattern: callable painting the inner motif; seed: speckle rng seed.
def _bake_tile(base, hi, lo, corner, pattern, seed):
    s = pygame.Surface((TILE_SRC, TILE_SRC))
    s.fill(base)
    rng = random.Random(seed)                  # stable speckle so the stone does not look flat
    for _ in range(46):
        _px(s, rng.randrange(TILE_SRC), rng.randrange(TILE_SRC), mix(base, lo, 0.3))
    pattern(s)
    for i in range(TILE_SRC):
        _px(s, i, 0, hi)
        _px(s, 0, i, hi)
        _px(s, i, TILE_SRC - 1, lo)
        _px(s, TILE_SRC - 1, i, lo)
    for dx, dy in ((2, 2), (TILE_SRC - 3, 2), (2, TILE_SRC - 3), (TILE_SRC - 3, TILE_SRC - 3)):
        _px(s, dx, dy, corner)
        _px(s, dx + 1, dy, corner)
        _px(s, dx, dy + 1, corner)
    return pygame.transform.scale(s, (TILE_SRC * TILE_SCALE, TILE_SRC * TILE_SCALE))


class PixelArtBank:
    # Bake every texture once at startup so the game loop only blits cached
    # surfaces. geo: dict with the game geometry - p1_dock/p2_dock/p1_tray/
    # p2_tray (Rects for the baked dock/tray backgrounds), p1_way/p2_way
    # (waypoint lists for the route guide layer) and win (window size tuple).
    def __init__(self, geo):
        self.geo = geo
        self.tiles = {
            "lane_p1": _bake_tile((36, 58, 86), (66, 98, 132), (20, 34, 52), (130, 158, 190),
                                  lambda s: _pat_lane(s, (24, 42, 64)), 11),
            "lane_p2": _bake_tile((66, 32, 58), (98, 48, 84), (40, 18, 36), (158, 108, 158),
                                  lambda s: _pat_lane(s, (48, 20, 42)), 22),
            "war": _bake_tile((44, 30, 36), (64, 46, 54), (24, 16, 20), (110, 84, 96), _pat_war, 33),
            "rune": _bake_tile((58, 42, 74), (86, 64, 106), (34, 24, 46), (180, 150, 210), _pat_rune, 44),
            "finish": _bake_tile((56, 46, 26), (86, 72, 42), (32, 26, 14), (150, 130, 70), _pat_finish, 55),
        }
        self.tokens = {}
        self.tokens[(1, 0)] = self._bake_token((64, 200, 220), (38, 148, 168), (240, 210, 90), 1)
        self.tokens[(1, 1)] = self._bake_token((64, 200, 220), (38, 148, 168), (240, 210, 90), 2)
        self.tokens[(1, 2)] = self._bake_token((64, 200, 220), (38, 148, 168), (240, 210, 90), 3)
        self.tokens[(2, 0)] = self._bake_token((214, 60, 84), (148, 38, 58), (150, 70, 170), 1)
        self.tokens[(2, 1)] = self._bake_token((214, 60, 84), (148, 38, 58), (150, 70, 170), 2)
        self.tokens[(2, 2)] = self._bake_token((214, 60, 84), (148, 38, 58), (150, 70, 170), 3)
        self.dice = {face: self._bake_dice(face) for face in (0, 1, 2, 3)}
        # slot geometry mirrors main.py DOCK_SLOT/DOCK_SLOT_GAP (44, 10) for the
        # reserve docks and TRAY_SLOT/TRAY_SLOT_GAP (44, 8) for the scored trays -
        # keep the two in sync or pieces drift off the baked recesses
        self.docks = {
            1: self._bake_dock(geo["p1_dock"], "P1 RESERVE", (64, 200, 220), 44, 10),
            2: self._bake_dock(geo["p2_dock"], "P2 RESERVE", (214, 60, 84), 44, 10),
        }
        self.trays = {
            1: self._bake_dock(geo["p1_tray"], "P1 SCORED", (240, 200, 80), 44, 8),
            2: self._bake_dock(geo["p2_tray"], "P2 SCORED", (240, 200, 80), 44, 8),
        }
        # three breathing intensity levels for the rune-tile glow (index 0 = off)
        self.glow = [None] + self._bake_glow((240, 200, 80))
        self.path_layer = self._bake_path_layer()
        self.stars = self._make_stars()

    # Bake one 40x40 token sprite: ground shadow strip, 3px thick dark base,
    # colored body with a metallic rim, a bottom shade arc, a pixel highlight
    # and the centered piece number.
    # fill: body color; dark: base/shade color; ring: rim color; num: piece number 1-3.
    def _bake_token(self, fill, dark, ring, num):
        s = pygame.Surface((40, 40), pygame.SRCALPHA)
        shadow = pygame.Surface((26, 7), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 96))             # soft ground shadow (fill alpha is reliable)
        s.blit(shadow, (7, 31))
        pygame.draw.circle(s, dark, (20, 18), 14)     # thick base (3px lip under the body)
        pygame.draw.circle(s, fill, (20, 15), 13)      # body
        pygame.draw.circle(s, ring, (20, 15), 13, 2)   # metallic rim
        for i in range(13):                         # bottom shade arc for depth
            a = math.pi * (0.15 + 0.7 * i / 12)
            _px(s, int(20 + 11 * math.cos(a)), int(15 + 11 * math.sin(a)), dark)
        _px(s, 12, 8, (240, 250, 255))              # pixel highlight
        _px(s, 13, 8, (240, 250, 255))
        label = _font(22).render(str(num), True, (14, 14, 22))
        s.blit(label, (20 - label.get_width() // 2, 15 - label.get_height() // 2))
        return s

    # Bake one 72x72 isometric pixel die face: white front, lighter top, shaded
    # right side, ink outlines and 1-3 pips (0 draws a "?").
    # face: the pip count 0..3 to bake.
    def _bake_dice(self, face):
        s = pygame.Surface((72, 72), pygame.SRCALPHA)
        ink = (26, 24, 34)
        top = [(12, 16), (60, 16), (70, 4), (22, 4)]
        right = [(60, 16), (70, 4), (70, 52), (60, 64)]
        face_r = pygame.Rect(12, 16, 48, 48)
        pygame.draw.polygon(s, (255, 255, 255), top)
        pygame.draw.polygon(s, (198, 198, 214), right)
        pygame.draw.rect(s, (244, 244, 250), face_r)
        pygame.draw.line(s, (225, 225, 235), (14, 18), (58, 18))
        pygame.draw.polygon(s, ink, top, 2)
        pygame.draw.polygon(s, ink, right, 2)
        pygame.draw.rect(s, ink, face_r, 2)
        pips = {0: [], 1: [(36, 40)], 2: [(26, 30), (46, 50)], 3: [(26, 30), (36, 40), (46, 50)]}
        for x, y in pips[face]:
            pygame.draw.circle(s, ink, (x, y), 5)
        if face == 0:
            q = _font(26).render("?", True, ink)
            s.blit(q, (36 - q.get_width() // 2, 40 - q.get_height() // 2))
        return s

    # Bake one reserve/score tray background: dark plate, double gold border,
    # colored label and three recessed slots.
    # rect: target size (width/height); label: text; accent: label color;
    # slot_size: square recess size in px; gap: px between recesses. The recess
    # positions come from slot_centers(rect, slot_size, gap) so they match the
    # piece anchors in main.py exactly (Phase 4.6 - no more hardcoded 48/8 that
    # overflowed the 120px scored tray).
    def _bake_dock(self, rect, label, accent, slot_size=44, gap=8):
        s = pygame.Surface((rect.width, rect.height))
        s.fill((28, 26, 40))
        pygame.draw.rect(s, (122, 100, 54), s.get_rect(), 2)
        pygame.draw.rect(s, (58, 52, 78), s.get_rect().inflate(-6, -6), 1)
        s.blit(_font(16).render(label, True, accent), (8, 4))
        x0 = (rect.width - (3 * slot_size + 2 * gap)) // 2
        y0 = (rect.height - slot_size) // 2
        for i in range(3):
            slot = pygame.Rect(x0 + i * (slot_size + gap), y0, slot_size, slot_size)
            pygame.draw.rect(s, (14, 13, 20), slot)
            pygame.draw.rect(s, (74, 68, 96), slot, 2)
            pygame.draw.line(s, (44, 40, 60), (slot.x + 2, slot.y + 2), (slot.right - 3, slot.y + 2))
        return s

    # Bake the glow tiers: one 64x64 sprite per breathing level.
    # color: glow RGB; returns three surfaces whose alpha ramps from dim to bright.
    def _bake_glow(self, color):
        tiers = []
        for peak in (30, 52, 78):
            s = pygame.Surface((64, 64), pygame.SRCALPHA)
            for r in range(30, 0, -1):
                a = int(peak * (1.0 - r / 32.0) ** 2)
                ring = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
                ring.fill((*color, a))
                s.blit(ring, (32 - r, 32 - r))
            tiers.append(s)
        return tiers

    # Bake the route-guide layer: muted dashed waypoint chains with arrowheads
    # for both players (dock -> 1 -> 2 -> war zone -> 8 -> 9 -> 10).
    def _bake_path_layer(self):
        w, h = self.geo["win"]
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        self._dash(s, self.geo["p1_way"], (52, 96, 112))    # cyan-mute guide for P1
        self._dash(s, self.geo["p2_way"], (110, 52, 88))    # crimson-mute guide for P2
        return s

    # Paint one waypoint chain as 2px dashed segments, one arrowhead per link.
    # s: destination surface; way: list of (x, y) waypoints; color: line color.
    def _dash(self, s, way, color):
        for i in range(len(way) - 1):
            a, b = way[i], way[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy) or 1.0
            ux, uy = dx / length, dy / length
            for t0 in range(0, int(length) - 10, 8):
                pygame.draw.line(s, color,
                                 (int(a[0] + ux * t0), int(a[1] + uy * t0)),
                                 (int(a[0] + ux * (t0 + 4)), int(a[1] + uy * (t0 + 4))), 2)
            px, py = -uy, ux                              # perpendicular for the arrow wings
            pygame.draw.polygon(s, color, [
                (b[0], b[1]),
                (int(b[0] - ux * 10 + px * 5), int(b[1] - uy * 10 + py * 5)),
                (int(b[0] - ux * 10 - px * 5), int(b[1] - uy * 10 - py * 5)),
            ])

    # Build the ambient stardust field: 30 motes with drift speed, twinkle phase
    # and a gold/cyan/white color pick.
    def _make_stars(self):
        rng = random.Random(42)
        cols = ((240, 220, 150), (150, 220, 230), (220, 220, 235))
        return [
            {"x": rng.randrange(0, self.geo["win"][0]),
             "y": rng.randrange(0, self.geo["win"][1]),
             "spd": rng.randint(5, 14),
             "ph": rng.random() * math.tau,
             "sz": rng.choice((1, 2)),
             "col": rng.choice(cols)}
            for _ in range(30)
        ]


# Return the screen centre of each of the 3 slots of a dock/tray plate, using
# the SAME centring math as _bake_dock so piece anchors always sit inside the
# baked recesses.
# rect: the plate Rect; slot_size: square slot width in px; gap: px between slots.
def slot_centers(rect, slot_size, gap):
    x0 = rect.x + (rect.width - (3 * slot_size + 2 * gap)) // 2
    y0 = rect.y + (rect.height - slot_size) // 2
    return [(x0 + i * (slot_size + gap) + slot_size // 2, y0 + slot_size // 2)
            for i in range(3)]


# Draw a raised pixel panel: dark vertical gradient fill, double gold border and
# four corner rivets. surf: destination; rect: panel bounds.
def draw_panel(surf, rect):
    bands = 8
    for i in range(bands):
        y = rect.y + i * rect.height // bands
        h = rect.height // bands + 1
        pygame.draw.rect(surf, mix((40, 38, 56), (26, 24, 38), i / (bands - 1)), (rect.x, y, rect.width, h))
    pygame.draw.rect(surf, (122, 100, 54), rect, 2)
    pygame.draw.rect(surf, (74, 62, 34), rect.inflate(-6, -6), 1)
    for cx, cy in ((rect.x + 4, rect.y + 4), (rect.right - 7, rect.y + 4),
                   (rect.x + 4, rect.bottom - 7), (rect.right - 7, rect.bottom - 7)):
        pygame.draw.rect(surf, (180, 150, 80), (cx, cy, 3, 3))
        _px(surf, cx, cy, (240, 220, 150))


# Draw a panel title with a 4-row gradient underline strip.
# surf: destination; x, y: text position; w: strip width; text: title; accent: tint.
def draw_title(surf, x, y, w, text, accent):
    surf.blit(_font(24).render(text, True, (240, 230, 200)), (x, y - 2))
    for i in range(4):
        pygame.draw.rect(surf, mix(accent, (20, 18, 28), i / 3), (x, y + 22 + i, w, 1))


# Draw a pixel button with hover and disabled states.
# surf: destination; rect: button bounds; label: text; base: body color;
# hover: whether the cursor is inside; enabled: False dims the body and text.
def draw_button(surf, rect, label, base, hover, enabled=True):
    if not enabled:
        body = (46, 44, 60)
    elif hover:
        body = mix(base, (255, 255, 255), 0.18)
    else:
        body = base
    pygame.draw.rect(surf, body, rect, border_radius=4)
    pygame.draw.rect(surf, (150, 124, 66) if enabled else (70, 66, 88), rect, 2, border_radius=4)
    text = _font(20).render(label, True, (232, 228, 244) if enabled else (140, 136, 158))
    surf.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


# Build one small stardust sprite at the requested brightness.
# star: dict with "col" and "sz"; alpha: 0..255 twinkle level.
def draw_star_surface(star, alpha):
    s = pygame.Surface((star["sz"] * 2 + 1, star["sz"] * 2 + 1), pygame.SRCALPHA)
    s.fill((*star["col"], int(alpha)))
    return s
