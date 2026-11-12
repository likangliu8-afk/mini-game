# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 4.6: pre-baked pixel-art bank for the retro Babylonian UI. Every texture
# is painted pixel by pixel at low resolution and scaled up with nearest-neighbour
# so the game gets a crisp indie pixel look with zero external image dependencies
# beyond the baked pixelfx VFX sheets.

import math
import random

import pygame

TILE_SRC = 28      # tiles are painted at 28x28 and scaled 3x to 84x84
TILE_SCALE = 3


# Set one pixel on a surface while ignoring out-of-bounds coordinates.
# s: target pygame Surface; x, y: integer pixel coordinates; c: RGB/RGBA color tuple.
def _px(s, x, y, c):
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((x, y), c)


# Linearly interpolate between two RGB colors.
# a, b: source and target RGB 3-tuples; t: blend factor in [0.0, 1.0].
def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


_font_cache = {}


# Return a cached crisp font for the given pixel height, preferring clean pixel-friendly
# monospace/sans system fonts before falling back to Pygame's built-in bitmap font.
# size: requested font height in pixels; font_obj: internal candidate font object.
def _font(size):
    if size not in _font_cache:
        font_obj = pygame.font.SysFont("consolas,verdana,arial", max(11, int(size * 0.72)), bold=True)
        if font_obj is None:
            font_obj = pygame.font.Font(None, size)
        _font_cache[size] = font_obj
    return _font_cache[size]


# Paint the private-lane motif: four small lapis diamond studs in a 2x2 grid plus
# subtle inner mosaic border dots.
# s: the 28x28 tile Surface; tone: darker accent RGB tuple; hi_dot: lighter inlay RGB tuple.
def _pat_lane(s, tone, hi_dot):
    for i in range(4, TILE_SRC - 4, 2):
        _px(s, i, 3, tone)
        _px(s, i, TILE_SRC - 4, tone)
        _px(s, 3, i, tone)
        _px(s, TILE_SRC - 4, i, tone)
    for cx, cy in ((9, 9), (18, 9), (9, 18), (18, 18)):
        _px(s, cx, cy - 1, tone)
        _px(s, cx - 1, cy, tone)
        _px(s, cx, cy, hi_dot)
        _px(s, cx + 1, cy, tone)
        _px(s, cx, cy + 1, tone)


# Paint the shared war-zone motif: crossed obsidian blades with crimson hazard trim.
# s: the 28x28 tile Surface; blade/edge/ink: RGB colors for the crossed swords.
def _pat_war(s):
    blade = (122, 54, 64)
    edge = (168, 78, 86)
    ink = (22, 14, 18)
    for i in range(5, TILE_SRC - 5):
        _px(s, i, i, blade)
        _px(s, TILE_SRC - 1 - i, i, blade)
        if 8 <= i <= 19:
            _px(s, i, i - 1, edge)
            _px(s, TILE_SRC - 1 - i, i - 1, edge)
    for i in (7, 13, 20):
        _px(s, i, TILE_SRC - 4 - i, ink)


# Paint the Babylonian eight-pointed rosette motif on safe/bonus rune tiles (4 and 8).
# s: the 28x28 tile Surface; gold/ring/cyan: RGB colors for petals, ring pips, and core.
def _pat_rune(s):
    gold = (244, 204, 88)
    ring = (196, 144, 238)
    cyan = (116, 228, 240)
    cx = cy = 14
    for k in range(8):
        ang = k * math.pi / 4
        dx, dy = int(round(math.cos(ang))), int(round(math.sin(ang)))
        for r in range(4, 10):
            _px(s, cx + dx * r, cy + dy * r, gold)
    for k in range(16):
        ang = k * math.pi / 8
        _px(s, cx + int(round(math.cos(ang) * 11)), cy + int(round(math.sin(ang) * 11)), ring)
    for ddx in (-2, -1, 0, 1, 2):
        for ddy in (-2, -1, 0, 1, 2):
            if abs(ddx) + abs(ddy) <= 2:
                _px(s, cx + ddx, cy + ddy, cyan if abs(ddx) + abs(ddy) <= 1 else gold)


# Paint the finish shrine motif on tile 10: a stepped golden ziggurat crowned with an emerald gem.
# s: the 28x28 tile Surface; gold/bright/green: RGB colors for steps and top gem.
def _pat_finish(s):
    gold = (214, 178, 84)
    bright = (248, 226, 136)
    green = (96, 228, 142)
    for x0, y0, x1, y1 in ((5, 20, 22, 25), (8, 14, 19, 19), (11, 9, 16, 13)):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                _px(s, x, y, gold)
        for x in range(x0, x1 + 1):
            _px(s, x, y0, bright)
    for y in range(4, 9):
        for x in range(12, 16):
            _px(s, x, y, green)
    _px(s, 13, 5, (235, 255, 230))


# Bake one 84x84 stone tile texture from a 28x28 pixel canvas with bevels and corner rivets.
# base: stone fill RGB; hi/lo: top-left highlight and bottom-right shadow RGB;
# corner: metallic rivet RGB; pattern: motif drawing function; seed: deterministic RNG seed.
def _bake_tile(base, hi, lo, corner, pattern, seed):
    s = pygame.Surface((TILE_SRC, TILE_SRC))
    s.fill(base)
    rng = random.Random(seed)
    for _ in range(48):
        _px(s, rng.randrange(TILE_SRC), rng.randrange(TILE_SRC), mix(base, lo, 0.32))
    pattern(s)
    for i in range(TILE_SRC):
        _px(s, i, 0, hi)
        _px(s, 0, i, hi)
        _px(s, i, 1, mix(base, hi, 0.45))
        _px(s, i, TILE_SRC - 1, lo)
        _px(s, TILE_SRC - 1, i, lo)
        _px(s, i, TILE_SRC - 2, mix(base, lo, 0.65))
    for dx, dy in ((2, 2), (TILE_SRC - 4, 2), (2, TILE_SRC - 4), (TILE_SRC - 4, TILE_SRC - 4)):
        _px(s, dx, dy, corner)
        _px(s, dx + 1, dy, corner)
        _px(s, dx, dy + 1, corner)
    return pygame.transform.scale(s, (TILE_SRC * TILE_SCALE, TILE_SRC * TILE_SCALE))


# Compute the exact pixel center of slot `slot_idx` inside a 3-slot dock or scored tray rect.
# rect: the enclosing pygame.Rect of the dock/tray; slot_idx: piece index 0, 1, or 2;
# slot_size: square side length of each recessed slot; gap: horizontal spacing between slots.
def slot_center_in_rect(rect, slot_idx, slot_size=44, gap=12):
    total_w = 3 * slot_size + 2 * gap
    x0 = rect.x + (rect.width - total_w) // 2
    y0 = rect.y + 22
    return (x0 + slot_idx * (slot_size + gap) + slot_size // 2, y0 + slot_size // 2)


class PixelArtBank:
    # Pre-bake all board tiles, 3D tokens, dice faces, docks, route arrows, and stardust.
    # geo: geometry dictionary containing window dimensions, dock/tray Rects, and path waypoints.
    def __init__(self, geo):
        self.geo = geo
        self.tiles = {
            "lane_p1": _bake_tile(
                (36, 62, 92), (76, 118, 160), (18, 32, 50), (140, 180, 214),
                lambda s: _pat_lane(s, (22, 42, 66), (86, 164, 204)), 11
            ),
            "lane_p2": _bake_tile(
                (72, 34, 60), (118, 58, 98), (38, 16, 32), (184, 122, 168),
                lambda s: _pat_lane(s, (48, 20, 40), (168, 78, 122)), 22
            ),
            "war": _bake_tile(
                (48, 30, 38), (82, 52, 64), (24, 14, 20), (138, 98, 108),
                _pat_war, 33
            ),
            "rune": _bake_tile(
                (62, 44, 82), (108, 78, 140), (32, 22, 46), (218, 184, 102),
                _pat_rune, 44
            ),
            "finish": _bake_tile(
                (60, 50, 28), (108, 90, 50), (32, 26, 14), (224, 190, 92),
                _pat_finish, 55
            ),
        }
        self.tokens = {}
        for idx in range(3):
            self.tokens[(1, idx)] = self._bake_token((64, 208, 228), (30, 118, 142), (246, 214, 94), idx + 1)
            self.tokens[(2, idx)] = self._bake_token((224, 64, 90), (132, 28, 48), (192, 118, 224), idx + 1)
        self.dice = {face: self._bake_dice(face) for face in (0, 1, 2, 3)}
        self.docks = {
            1: self._bake_dock(geo["p1_dock"], "P1 RESERVE (START)", (64, 208, 228)),
            2: self._bake_dock(geo["p2_dock"], "P2 AI RESERVE (START)", (224, 64, 90)),
        }
        self.trays = {
            1: self._bake_dock(geo["p1_tray"], "P1 SCORED (10 -> GOAL)", (244, 204, 88)),
            2: self._bake_dock(geo["p2_tray"], "P2 SCORED (10 -> GOAL)", (244, 204, 88)),
        }
        # index 0 is unused placeholder; indices 1, 2, 3 hold soft->bright breathing rune halos
        self.glow = [None] + self._bake_glow((244, 204, 88))
        self.path_layer = self._bake_path_layer()
        self.stars = self._make_stars()

    # Bake one 40x40 3D bevelled war-token sprite with drop shadow, rim, and number label.
    # fill: token top RGB; dark: cylinder side RGB; ring: metallic border RGB; num: piece label 1..3.
    def _bake_token(self, fill, dark, ring, num):
        s = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 110), pygame.Rect(6, 28, 28, 9))
        pygame.draw.circle(s, dark, (20, 19), 14)
        pygame.draw.circle(s, fill, (20, 15), 13)
        pygame.draw.circle(s, ring, (20, 15), 13, 2)
        pygame.draw.circle(s, mix(fill, (255, 255, 255), 0.45), (15, 10), 3)
        label = _font(19).render(str(num), True, (14, 14, 22))
        s.blit(label, (20 - label.get_width() // 2, 15 - label.get_height() // 2))
        return s

    # Bake one 72x72 isometric 3D pixel die sprite for value 0..3 (0 shows "?" before first roll).
    # face: integer die value 0, 1, 2, or 3; top/right/face_r: polygon/rect faces of the cube.
    def _bake_dice(self, face):
        s = pygame.Surface((72, 72), pygame.SRCALPHA)
        ink = (24, 22, 34)
        top = [(10, 16), (56, 16), (66, 6), (20, 6)]
        right = [(56, 16), (66, 6), (66, 52), (56, 62)]
        face_r = pygame.Rect(10, 16, 46, 46)
        pygame.draw.polygon(s, (255, 252, 240), top)
        pygame.draw.polygon(s, (188, 184, 206), right)
        pygame.draw.rect(s, (242, 240, 248), face_r)
        pygame.draw.polygon(s, ink, top, 2)
        pygame.draw.polygon(s, ink, right, 2)
        pygame.draw.rect(s, ink, face_r, 2)
        pips = {0: [], 1: [(33, 39)], 2: [(23, 29), (43, 49)], 3: [(23, 29), (33, 39), (43, 49)]}
        for px, py in pips[face]:
            pygame.draw.circle(s, (196, 48, 68) if face == 3 else ink, (px, py), 5)
        if face == 0:
            q = _font(24).render("?", True, ink)
            s.blit(q, (33 - q.get_width() // 2, 39 - q.get_height() // 2))
        return s

    # Bake a 3-slot recessed stone dock or scored tray matching `slot_center_in_rect` geometry.
    # rect: target pygame.Rect dimensions; label: header string; accent: header RGB color;
    # slot_size/gap: recessed slot dimensions guaranteed to fit cleanly inside `rect`.
    def _bake_dock(self, rect, label, accent, slot_size=44, gap=12):
        s = pygame.Surface((rect.width, rect.height))
        s.fill((28, 26, 42))
        pygame.draw.rect(s, (136, 112, 62), s.get_rect(), 2)
        pygame.draw.rect(s, (62, 56, 86), s.get_rect().inflate(-6, -6), 1)
        hdr = _font(14).render(label, True, accent)
        s.blit(hdr, (rect.width // 2 - hdr.get_width() // 2, 4))
        total_w = 3 * slot_size + 2 * gap
        x0 = (rect.width - total_w) // 2
        for i in range(3):
            slot = pygame.Rect(x0 + i * (slot_size + gap), 22, slot_size, slot_size)
            pygame.draw.rect(s, (14, 13, 22), slot, border_radius=4)
            pygame.draw.rect(s, (78, 72, 104), slot, 2, border_radius=4)
            num_lbl = _font(13).render(f"#{i+1}", True, (52, 48, 72))
            s.blit(num_lbl, (slot.centerx - num_lbl.get_width() // 2, slot.centery - num_lbl.get_height() // 2))
        return s

    # Bake three concentric alpha-blended radial glow surfaces for breathing rune tiles.
    # color: RGB glow tint; tiers: list of three 64x64 SRCALPHA surfaces.
    def _bake_glow(self, color):
        tiers = []
        for peak in (24, 42, 64):
            s = pygame.Surface((64, 64), pygame.SRCALPHA)
            for r in range(28, 4, -4):
                alpha = int(peak * (1.0 - r / 30.0))
                pygame.draw.circle(s, (*color, alpha), (32, 32), r)
            tiers.append(s)
        return tiers

    # Bake the translucent board route-guide overlay drawn ON TOP OF tile seams so
    # every step `Reserve -> 1 -> 2 -> 3 -> 4* -> 5 -> 6 -> 7 -> 8* -> 9 -> 10` is unmistakable.
    # w, h: full window dimensions; s: transparent overlay Surface.
    def _bake_path_layer(self):
        w, h = self.geo["win"]
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        self._dash(s, self.geo["p1_way"], (90, 218, 240, 215))
        self._dash(s, self.geo["p2_way"], (240, 96, 128, 215))
        self._dash(s, self.geo["shared_way"], (248, 212, 104, 225))
        return s

    # Paint crisp directional chevron arrows at the seam midpoint between adjacent tiles.
    # s: target SRCALPHA surface; way: list of `(x, y)` tuples; color: RGBA arrow color.
    def _dash(self, s, way, color):
        outline = (16, 14, 24, 230)
        for i in range(len(way) - 1):
            a, b = way[i], way[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy) or 1.0
            ux, uy = dx / length, dy / length
            for t0 in range(26, max(26, int(length) - 24), 12):
                pygame.draw.line(
                    s, color,
                    (int(a[0] + ux * t0), int(a[1] + uy * t0)),
                    (int(a[0] + ux * (t0 + 5)), int(a[1] + uy * (t0 + 5))), 2
                )
            mid_x, mid_y = int((a[0] + b[0]) * 0.5), int((a[1] + b[1]) * 0.5)
            px, py = -uy, ux
            tri = [
                (int(mid_x + ux * 8), int(mid_y + uy * 8)),
                (int(mid_x - ux * 6 + px * 6), int(mid_y - uy * 6 + py * 6)),
                (int(mid_x - ux * 6 - px * 6), int(mid_y - uy * 6 - py * 6)),
            ]
            pygame.draw.polygon(s, color, tri)
            pygame.draw.polygon(s, outline, tri, 1)

    # Create 32 deterministic floating stardust particles for subtle background atmosphere.
    # rng: seeded Random instance; cols: palette of soft gold/cyan/silver star tints.
    def _make_stars(self):
        rng = random.Random(42)
        cols = ((240, 220, 150), (130, 216, 232), (210, 206, 236))
        return [
            {
                "x": rng.randrange(0, self.geo["win"][0]),
                "y": rng.randrange(48, self.geo["win"][1]),
                "spd": rng.randint(6, 15),
                "ph": rng.random() * math.tau,
                "sz": rng.choice((1, 2)),
                "col": rng.choice(cols),
            }
            for _ in range(32)
        ]


# Draw an embossed royal dark-gold UI panel with subtle gradient bands and corner rivets.
# surf: target pygame Surface; rect: bounding pygame.Rect of the panel.
def draw_panel(surf, rect):
    bands = 8
    for i in range(bands):
        y = rect.y + i * rect.height // bands
        h = rect.height // bands + 1
        pygame.draw.rect(surf, mix((40, 38, 58), (24, 22, 36), i / (bands - 1)), (rect.x, y, rect.width, h))
    pygame.draw.rect(surf, (142, 116, 64), rect, 2)
    pygame.draw.rect(surf, (72, 60, 38), rect.inflate(-6, -6), 1)
    for cx, cy in ((rect.x + 4, rect.y + 4), (rect.right - 7, rect.y + 4),
                   (rect.x + 4, rect.bottom - 7), (rect.right - 7, rect.bottom - 7)):
        pygame.draw.rect(surf, (192, 160, 88), (cx, cy, 3, 3))
        _px(surf, cx, cy, (248, 230, 160))


# Draw a crisp section header with a gilded gradient underline bar.
# surf: target Surface; x, y: top-left coordinates; w: underline width; text: title string; accent: RGB color.
def draw_title(surf, x, y, w, text, accent):
    surf.blit(_font(20).render(text, True, (244, 232, 196)), (x, y))
    for i in range(3):
        pygame.draw.rect(surf, mix(accent, (24, 22, 36), i / 2.0), (x, y + 20 + i, w, 1))


# Draw a bevelled interactive pixel button supporting hover highlight and disabled dimming.
# surf: target Surface; rect: button pygame.Rect; label: button text; base: fill RGB;
# hover: True if mouse is over button; enabled: False to grey out non-interactive buttons.
def draw_button(surf, rect, label, base, hover, enabled=True):
    if not enabled:
        body = (42, 40, 54)
        border = (68, 64, 84)
        fg = (124, 120, 142)
    else:
        body = mix(base, (255, 255, 255), 0.20) if hover else base
        border = (218, 186, 102) if hover else (154, 126, 68)
        fg = (244, 240, 252)
    pygame.draw.rect(surf, body, rect, border_radius=4)
    pygame.draw.rect(surf, border, rect, 2, border_radius=4)
    text_surf = _font(16).render(label, True, fg)
    surf.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))


# Create a tiny alpha-blended square particle surface for one twinkling background star.
# star: star dictionary with keys "sz" and "col"; alpha: integer opacity 0..255.
def draw_star_surface(star, alpha):
    s = pygame.Surface((star["sz"] * 2, star["sz"] * 2), pygame.SRCALPHA)
    s.fill((*star["col"], max(0, min(255, int(alpha)))))
    return s
