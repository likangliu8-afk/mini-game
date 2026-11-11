# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 4.5: pygame main loop with an indie-grade retro pixel look (pixel_art bank),
# the AI Decision Inspector panel, dice console + battle log, the four pixelfx
# effects bound to game events, dice tumble animation and a --self-test that also
# exercises every human interaction branch (hover preview, button/piece/target
# clicks, Hint: ON) before saving gameplay_preview.png.
#
# Usage:
#     python pixel_dice_ur/main.py               # real window for a human player
#     python pixel_dice_ur/main.py --self-test   # headless render + interaction QA + preview png

import math
import math
import os
import sys
import random

# import the sibling Phase 1/2/3 modules (works both as a script and as a module)
try:
    from game_state import (BOARD_END, DICE_PROBS, SAFE_TILES, WAR_START,
                            WAR_END, GameState)
    from ai_engine import (DeterministicMinimaxAgent, ExpectiminimaxAgent,
                           GreedyAgent, evaluate_state)
    from vfx_manager import VFXManager
    import pixel_art
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from game_state import (BOARD_END, DICE_PROBS, SAFE_TILES, WAR_START,
                            WAR_END, GameState)
    from ai_engine import (DeterministicMinimaxAgent, ExpectiminimaxAgent,
                           GreedyAgent, evaluate_state)
    from vfx_manager import VFXManager
    import pixel_art

import pygame

# ---- authorship shown in the window title and the top banner (change once here) ----
AUTHOR_NAME = "LAW LI KANG RAIN"
STUDENT_ID = "1904VECI"
BANNER_TEXT = f"PIXEL DICE UR   |   Name: {AUTHOR_NAME}   |   Student ID: {STUDENT_ID}"

# ---- window / layout ----
WIN_W, WIN_H = 1024, 640
BANNER_H = 48
FPS = 60

TILE = 84                       # one tile is 84x84 px
GRID_X, GRID_Y = 73, 218        # top-left of the 3x6 grid
LEFT_W = 650                    # left board panel width; right panel is WIN_W - LEFT_W

# reserve dock / scored tray slots (3 per side, one dedicated slot per piece)
DOCK_H = 76
P1_DOCK = pygame.Rect(GRID_X + 2 * TILE + 4, GRID_Y - DOCK_H - 12, 256, DOCK_H)
P2_DOCK = pygame.Rect(GRID_X + 2 * TILE + 4, GRID_Y + 3 * TILE + 12, 256, DOCK_H)
TRAY_H = 54
P1_TRAY = pygame.Rect(GRID_X + 5 * TILE, GRID_Y - TRAY_H - 8, 120, TRAY_H)
P2_TRAY = pygame.Rect(GRID_X + 5 * TILE, GRID_Y + 3 * TILE + 8, 120, TRAY_H)
SLOT_W, SLOT_GAP = 48, 8
SLOT_X0 = (256 - (3 * SLOT_W + 2 * SLOT_GAP)) // 2   # same math as the baked dock art

# middle-row tile kinds: cols 0..4 = war tiles 3..7 (col 1 is the rune tile 4),
# col 5 = finish; top/bottom rows: cols 0,1 = lane tiles 1,2; col 2 = dock;
# cols 4,5 = lane tiles 8,9 (col 4 is the rune tile 8)
TILE_KIND = {
    (1, 0): "war", (1, 1): "rune", (1, 2): "war", (1, 3): "war", (1, 4): "war",
    (1, 5): "finish",
    (0, 0): "lane_p1", (0, 1): "lane_p1", (0, 4): "rune", (0, 5): "lane_p1",
    (2, 0): "lane_p2", (2, 1): "lane_p2", (2, 4): "rune", (2, 5): "lane_p2",
}
TILE_LABEL = {
    (0, 0): "2", (0, 1): "1", (0, 4): "8*", (0, 5): "9",
    (1, 0): "3", (1, 1): "4*", (1, 2): "5", (1, 3): "6", (1, 4): "7", (1, 5): "10",
    (2, 0): "2", (2, 1): "1", (2, 4): "8*", (2, 5): "9",
}

# ---- timing (ms) ----
HUMAN_PAUSE_MS = 700           # "No legal moves - Turn skipped" pause
AI_ROLL_WAIT_MS = 450          # natural pacing: roll -> show evaluation -> move
AI_MOVE_WAIT_MS = 450
SLIDE_MS = 180                 # short pixel slide of the moved piece
ROLL_ANIM_MS = 260             # dice tumble: face flickers, then the dice_roll VFX pops

# ---- palette (text / accents only; surfaces come from pixel_art) ----
TEXT = (228, 224, 240)
TEXT_DIM = (150, 146, 168)
P1_FILL = (64, 200, 220)
P2_FILL = (214, 60, 84)
GOLD = (240, 200, 80)
GREEN = (90, 210, 120)
RED = (230, 80, 70)
HI = (255, 240, 120)
BTN_BLUE = (52, 60, 90)
BTN_RED = (60, 44, 60)

_font_cache = {}
# Cache a default bitmap font for a given pixel height (retro look, fast to render).
# size: font height in pixels.
def get_font(size):
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]


# Return the grid cell (row, col) for a lane tile (1, 2, 8, 9) of a player.
# player: 1 = top lane, 2 = bottom lane; tile: the logical lane tile.
def lane_cell(player, tile):
    row = 0 if player == 1 else 2
    return {1: (row, 1), 2: (row, 0), 8: (row, 4), 9: (row, 5)}[tile]


# Return the grid cell (row, col) for a logical tile shared by both players.
# tile: 3..7 (middle row) or 10 (finish, middle row, right end).
def shared_cell(tile):
    return {3: (1, 0), 4: (1, 1), 5: (1, 2), 6: (1, 3), 7: (1, 4), 10: (1, 5)}[tile]


# Return the pixel centre of a grid cell.
# row, col: the cell; used to place pieces and to anchor the pixelfx pivots.
def cell_center(row, col):
    return (GRID_X + col * TILE + TILE // 2, GRID_Y + row * TILE + TILE // 2)


# Return the Rect of a grid cell.
# row, col: the cell.
def cell_rect(row, col):
    return pygame.Rect(GRID_X + col * TILE, GRID_Y + row * TILE, TILE, TILE)


class Game:
    # Build the game.
    # fast: when True (self-test) all waits collapse to 0, the human side auto-plays
    # with a GreedyAgent and slide/dice animations are skipped so a full game can
    # be simulated headlessly in a loop.
    def __init__(self, fast=False):
        pygame.display.set_caption(f"Pixel Dice Ur - {AUTHOR_NAME} - {STUDENT_ID}")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.fast = fast
        # bake all pixel-art textures once; geometry dict feeds the baked route layer
        geo = {
            "win": (WIN_W, WIN_H),
            "p1_dock": P1_DOCK, "p2_dock": P2_DOCK,
            "p1_tray": P1_TRAY, "p2_tray": P2_TRAY,
            "p1_way": self._waypoints(1), "p2_way": self._waypoints(2),
        }
        self.art = pixel_art.PixelArtBank(geo)
        self.reset()

    # Compute the route-guide waypoints for one player: dock slot -> tile 1 -> tile 2
    # -> war-zone entry -> war-zone exit -> tile 8 -> tile 9 -> finish 10.
    # player: 1 or 2; returns a list of (x, y) screen points.
    def _waypoints(self, player):
        row = 0 if player == 1 else 2
        dock = P1_DOCK if player == 1 else P2_DOCK
        return [
            (dock.centerx, dock.centery),
            cell_center(row, 1),
            cell_center(row, 0),
            cell_center(1, 0),
            cell_center(1, 4),
            cell_center(row, 4),
            cell_center(row, 5),
            cell_center(1, 5),
        ]

    # Reset to a fresh game: new state, cleared VFX, fresh logs, decisions, dice
    # animation and the auto-play agent. The selected P2 AI index is kept.
    def reset(self):
        if not hasattr(self, "ai_index"):
            self.ai_index = 0          # 0=Expectiminimax, 1=Minimax, 2=Greedy
        self.state = GameState()
        self.vfx = VFXManager()
        self.turns = 0                 # total completed moves
        self.log = []
        self.last_decision = None      # most recent AI decision (for the inspector)
        self.rich_decision = None      # most recent AI decision that had real candidates
        self.hint = None               # live Expectiminimax hint for the human position
        self.hint_on = False
        self.slides = {}               # (player, idx) -> slide animation dict
        self.phase = "human_await_roll"
        self.phase_ms = 0
        self.dice_rolling = False      # 260 ms tumble animation before the VFX pops
        self.dice_roll_ms = 0
        self.ai_roll_done = False      # AI turn: has the die been committed yet
        self.ai_moved = False          # AI turn: has the AI applied its move yet
        self.over = False
        self.hover_idx = None          # human piece under the cursor (target preview)
        self.pulse = 0.0               # drives the legal-move pulsing frame
        self.human_agent = GreedyAgent() if self.fast else None

    # Return the centre point of one reserve-dock slot for a player.
    # player: 1 or 2; slot: 0, 1 or 2 (the piece index).
    def dock_slot_center(self, player, slot):
        dock = P1_DOCK if player == 1 else P2_DOCK
        x = dock.x + SLOT_X0 + slot * (SLOT_W + SLOT_GAP) + SLOT_W // 2
        return (x, dock.y + 20 + 24)

    # Return the centre point of one scored-tray slot for a player.
    # player: 1 or 2; slot: 0, 1 or 2.
    def tray_slot_center(self, player, slot):
        tray = P1_TRAY if player == 1 else P2_TRAY
        tw = 36
        tx0 = tray.x + (tray.width - (3 * tw + 2 * SLOT_GAP)) // 2
        x = tx0 + slot * (tw + SLOT_GAP) + tw // 2
        return (x, tray.y + 18 + tw // 2)

    # Compute the centre screen point where a moved piece's pixelfx pivot should sit.
    # player: 1 or 2; tile: logical destination; piece: the piece index (dock slots are
    # per-piece, so a tile 0 event is anchored at that piece's own dock slot; the finish
    # anchors at the scored-tray slot; lane/war tiles use their grid cell centres).
    def tile_point(self, player, tile, piece=None):
        if tile == 0:
            return self.dock_slot_center(player, piece if piece is not None else 0)
        if tile == BOARD_END:
            return self.tray_slot_center(player, piece if piece is not None else 2)
        r, c = lane_cell(player, tile) if tile in (1, 2, 8, 9) else shared_cell(tile)
        return cell_center(r, c)

    # Begin the dice tumble: the face flickers for ROLL_ANIM_MS then commits.
    def start_roll(self):
        self.dice_rolling = True
        self.dice_roll_ms = 0

    # Commit the dice result once the tumble ends: set the real value, pop the
    # dice_roll VFX at the dice face, log it, and advance the phase.
    # player: 1 or 2, who just rolled.
    def commit_roll(self, player):
        roll = self.state.roll_dice()
        cx, cy = self.dice_center()
        self.vfx.spawn("dice_roll", cx, cy, scale=0.55)
        self.log.append(f"P{player} rolled {roll}")
        if player == 1:
            self.hint = self._compute_hint()     # refresh hint right after the die lands
            if not self.state.get_legal_moves():
                self.phase = "skip_wait"
                self.log.append("P1 no legal moves - Turn skipped")
            else:
                self.phase = "human_await_move"
        else:
            self.ai_roll_done = True
            if not self.state.get_legal_moves():
                self.do_ai_move(None)            # no legal move: the AI still "plays" the skip

    # Compute the live human hint (Expectiminimax d=4) when the hint toggle is on.
    # Returns a dict with scores / best / targets, or None when off.
    def _compute_hint(self):
        if not self.hint_on or self.state.current_turn != 1:
            return None
        move, scores, stats = ExpectiminimaxAgent(depth=4).choose_move(self.state)
        targets = {i: self.state.p1_pieces[i] + self.state.dice_roll for i in scores}
        return {"scores": scores, "best": move, "targets": targets,
                "nodes": stats["nodes"], "ms": stats["time_ms"]}

    # Perform the AI's chosen move: run the selected agent, record the decision for
    # the inspector, apply it, animate the slide and fire the event effects.
    # move_idx: the piece index to move, or None to skip the turn.
    def do_ai_move(self, move_idx):
        agent = self.make_ai_agent()
        # decide BEFORE applying so the inspector can show every candidate score
        best, scores, stats = agent.choose_move(self.state)
        roll = self.state.dice_roll
        targets = {i: self.state.p2_pieces[i] + roll for i in scores}
        self.last_decision = {
            "alg": AGENTS[self.ai_index][0],
            "nodes": stats["nodes"],
            "ms": stats["time_ms"],
            "scores": scores,
            "best": best,
            "targets": targets,
            "eval_p1": evaluate_state(self.state, 1),
        }
        if scores:
            self.rich_decision = dict(self.last_decision)
        self.apply_and_animate(2, best if best is not None else move_idx, roll)
        self.ai_moved = True

    # Apply a move for player to the current state, then animate the slide and trigger
    # the four pixelfx effects according to the returned event_info dict.
    # player: 1 or 2; idx: piece index to move or None to skip; roll: the die value used.
    def apply_and_animate(self, player, idx, roll):
        pieces = self.state.p1_pieces if player == 1 else self.state.p2_pieces
        from_tile = pieces[idx] if idx is not None else -1
        self.state, ev = self.state.apply_move(idx, roll)
        self.turns += 1
        to_tile = ev["target_tile"]
        # slide the moved piece from its old spot to the new one (skipped in fast mode)
        if idx is not None and not self.fast:
            from_pt = self.tile_point(player, from_tile, idx)
            to_pt = self.tile_point(player, to_tile, idx)
            self.slides[(player, idx)] = {"from": from_pt, "to": to_pt, "t": 0}
        # event effects, anchored at the destination cell (dock slot for sends-back)
        cx, cy = self.tile_point(player, to_tile, idx) if to_tile >= 0 else (WIN_W // 2, WIN_H // 2)
        if ev["captured"]:
            self.vfx.spawn("hit_explosion", cx, cy, scale=0.65)
        if ev["bonus_turn"]:
            self.vfx.spawn("rune_glow", cx, cy, scale=0.75)
        if ev["scored"]:
            self.vfx.spawn("score_burst", cx, cy, scale=0.75)
        if self.state.is_terminal():
            self.over = True
            # celebrate a win with two extra offset score_bursts
            self.vfx.spawn("score_burst", cx - 40, cy - 20, scale=0.7)
            self.vfx.spawn("score_burst", cx + 40, cy - 20, scale=0.7)
        # battle log line
        if idx is not None:
            tags = []
            if ev["captured"]:
                tags.append("CAPTURED!")
            if ev["bonus_turn"]:
                tags.append("BONUS TURN!")
            if ev["scored"]:
                tags.append("SCORED!")
            self.log.append(f"P{player} piece #{idx+1} to tile {to_tile}" + (f" ({', '.join(tags)})" if tags else ""))
        else:
            self.log.append(f"P{player} no legal moves - skipped")
        self.log = self.log[-40:]

    # Build the AI agent currently selected for P2.
    # Returns a fresh agent of the class at self.ai_index (depth 4 for the two searchers).
    def make_ai_agent(self):
        cls = AGENTS[self.ai_index][1]
        if cls.__name__ == "GreedyAgent":
            return cls()
        return cls(depth=4)

    # Return the centre of the dice face on the right panel (dice_roll effect anchor).
    # Must match the dice sprite drawn in draw_dice_log.
    def dice_center(self):
        x0 = LEFT_W + 10
        y0 = BANNER_H + 344
        return (x0 + 76, y0 + 92)

    # Human roll: start the 260 ms dice tumble (commits inside update()).
    def human_roll(self):
        if not self.dice_rolling:
            self.start_roll()

    # Human move: apply the chosen piece and animate/effects; on a bonus turn the
    # human rolls again, otherwise the turn passes to the AI.
    # idx: piece index to move (must be in get_legal_moves()).
    def human_move(self, idx):
        self.apply_and_animate(1, idx, self.state.dice_roll)
        self.hint = None
        if not self.over:
            if self.state.current_turn == 1:
                self.phase = "human_await_roll"    # bonus turn: roll again
            else:
                self.phase = "ai_think"
                self.phase_ms = 0

    # Advance the game one update tick.
    # dt_ms: real milliseconds since the previous update; drives timers, slides,
    # the dice tumble, VFX and the pulse.
    def update(self, dt_ms):
        dt = 0 if self.fast else dt_ms
        self.pulse += (0 if self.fast else dt_ms) * 0.005
        self.vfx.update(dt)
        # progress slide animations
        if self.slides:
            for key in list(self.slides):
                s = self.slides[key]
                s["t"] += dt
                if s["t"] >= SLIDE_MS:
                    del self.slides[key]
        if self.over:
            return
        # dice tumble: flicker the face for ROLL_ANIM_MS then commit the real roll
        if self.dice_rolling:
            self.dice_roll_ms += dt
            if self.dice_roll_ms >= ROLL_ANIM_MS:
                self.dice_rolling = False
                self.commit_roll(self.state.current_turn)
            return
        self.phase_ms += dt
        if self.fast:
            # auto-drive whichever side is to move with zero delay and no flags:
            # a fresh die is rolled at the start of every side's turn (bonus turns
            # keep current_turn, so this simply fires again with a new value).
            if self.state.current_turn == 1:
                roll = self.state.roll_dice()
                self.vfx.spawn("dice_roll", *self.dice_center(), scale=0.55)
                self.log.append(f"P1 rolled {roll}")
                legal = self.state.get_legal_moves()
                if not legal:
                    self.apply_and_animate(1, None, roll)
                else:
                    move, _, _ = self.human_agent.choose_move(self.state)
                    self.human_move(move if move is not None else None)
            else:
                roll = self.state.roll_dice()
                self.vfx.spawn("dice_roll", *self.dice_center(), scale=0.55)
                self.log.append(f"P2 rolled {roll}")
                agent = self.make_ai_agent()
                best, scores, stats = agent.choose_move(self.state)
                targets = {i: self.state.p2_pieces[i] + roll for i in scores}
                self.last_decision = {
                    "alg": AGENTS[self.ai_index][0], "nodes": stats["nodes"],
                    "ms": stats["time_ms"], "scores": scores, "best": best,
                    "targets": targets, "eval_p1": evaluate_state(self.state, 1),
                }
                if scores:
                    self.rich_decision = dict(self.last_decision)
                self.apply_and_animate(2, best, roll)
            return
        # normal (human vs AI) pacing
        if self.phase == "ai_think":
            if not self.ai_roll_done:
                if self.phase_ms >= AI_ROLL_WAIT_MS:
                    self.start_roll()
            elif not self.ai_moved:
                if self.phase_ms >= AI_ROLL_WAIT_MS + AI_MOVE_WAIT_MS + ROLL_ANIM_MS:
                    self.do_ai_move(None)
        elif self.phase == "skip_wait":
            if self.phase_ms >= HUMAN_PAUSE_MS:
                self.apply_and_animate(1, None, self.state.dice_roll)
                self.hint = None
                if not self.over and self.state.current_turn == 2:
                    self.phase = "ai_think"
                    self.phase_ms = 0

    # Return the screen position to render a piece at, honouring any active slide.
    # player, idx: which piece; dock pieces sit in their own slot, scored pieces in
    # their tray slot, mid-slide pieces get the interpolated position, and shared
    # tiles nudge P1 up / P2 down so two opponents stay visible on one tile.
    def piece_pos(self, player, idx):
        key = (player, idx)
        if key in self.slides:
            s = self.slides[key]
            f = min(1.0, s["t"] / SLIDE_MS)
            x = s["from"][0] + (s["to"][0] - s["from"][0]) * f
            y = s["from"][1] + (s["to"][1] - s["from"][1]) * f
            return int(x), int(y)
        tile = (self.state.p1_pieces if player == 1 else self.state.p2_pieces)[idx]
        if tile == 0:
            return self.dock_slot_center(player, idx)
        if tile == BOARD_END:
            return self.tray_slot_center(player, idx)
        cx, cy = self.tile_point(player, tile, idx)
        enemy = 2 if player == 1 else 1
        enemy_tiles = self.state.p2_pieces if enemy == 2 else self.state.p1_pieces
        if enemy_tiles.count(tile) and tile in (3, 4, 5, 6, 7, 10):
            cy = cy - 9 if player == 1 else cy + 9
        return cx, cy

    # ---- rendering ----
    def render(self):
        self.screen.fill((20, 18, 30))
        self.draw_stars()
        ox, oy = self.vfx.get_shake_offset()   # board + pieces follow the shake
        self.draw_board(ox, oy)
        self.draw_pieces(ox, oy)
        # target preview MUST be drawn before the flip inside this function so it
        # actually reaches the screen (drawn over the tiles, under the VFX layer)
        self.draw_target_preview(ox, oy)
        self.draw_banner()
        self.draw_turn_banner()
        self.draw_inspector()
        self.draw_dice_log()
        # VFX draws with offset=(0,0): it already adds the shake internally, so the
        # effects do not get a double shake on top of the board's own offset
        self.vfx.draw(self.screen, (0, 0))
        if self.over:
            self.draw_game_over()
        pygame.display.flip()

    # Draw the ambient stardust: every star's position drifts up over time and its
    # brightness follows a twinkle sine, so the idle screen still breathes.
    def draw_stars(self):
        t = self.pulse
        for star in self.art.stars:
            y = int(star["y"] - (t * star["spd"] * 0.06) % WIN_H)
            alpha = int(40 + 36 * (1.0 + math.sin(t * 0.8 + star["ph"])) / 2.0)
            surf = pixel_art.draw_star_surface(star, alpha)
            self.screen.blit(surf, (star["x"], y))

    # Draw the board: baked tile textures for every logical cell (cells (0,3) and
    # (2,3) are skipped - the hourglass / I-shape board has no tiles there), the
    # baked route-guide layer, the dock/tray plates and the breathing rune glow.
    # ox, oy: the screen-shake offset applied to every board element.
    def draw_board(self, ox, oy):
        self.screen.blit(self.art.path_layer, (ox, oy))
        for row in range(3):
            for col in range(6):
                if row in (0, 2) and col in (2, 3):
                    continue                  # side rows: no tiles where the dock and the gap sit
                kind = TILE_KIND[(row, col)]
                rect = pygame.Rect(ox + GRID_X + col * TILE, oy + GRID_Y + row * TILE, TILE, TILE)
                self.screen.blit(self.art.tiles[kind], rect)
                label = TILE_LABEL.get((row, col))
                if label:
                    self.screen.blit(get_font(15).render(label, True, TEXT_DIM), (rect.x + 5, rect.y + 4))
        # dock + tray plates (baked backgrounds) with their slot occupants
        self.screen.blit(self.art.docks[1], (ox + P1_DOCK.x, oy + P1_DOCK.y))
        self.screen.blit(self.art.docks[2], (ox + P2_DOCK.x, oy + P2_DOCK.y))
        self.screen.blit(self.art.trays[1], (ox + P1_TRAY.x, oy + P1_TRAY.y))
        self.screen.blit(self.art.trays[2], (ox + P2_TRAY.x, oy + P2_TRAY.y))
        # breathing glow on the two rune tiles (4 middle, 8 top/bottom lane ends)
        tier = 1 + (self.pulse // 10) % 3 if self.pulse else 1
        glow = self.art.glow[tier]
        for r, c in ((1, 1), (0, 4), (2, 4)):
            cx, cy = cell_center(r, c)
            self.screen.blit(glow, (cx + ox - 32, cy + oy - 32))

    # Draw all six pieces at their current (possibly sliding) positions using the
    # baked token sprites; legal human pieces get a pulsing highlight box.
    # ox, oy: the screen-shake offset.
    def draw_pieces(self, ox, oy):
        for player in (1, 2):
            pieces = self.state.p1_pieces if player == 1 else self.state.p2_pieces
            legal = self.state.get_legal_moves() if (player == 1 and self.phase in ("human_await_move", "skip_wait")) else []
            for idx in range(3):
                cx, cy = self.piece_pos(player, idx)
                cx, cy = cx + ox, cy + oy
                token = self.art.tokens[(player, idx)]
                self.screen.blit(token, (cx - 20, cy - 17))
                if idx in legal:
                    glow = 20 + int(5 * math.sin(self.pulse))
                    pygame.draw.rect(self.screen, HI, pygame.Rect(cx - glow, cy - glow, glow * 2, glow * 2), 2, border_radius=6)

    # Draw the top banner: title + author on the left, AI/New-Game buttons on the
    # right (both with hover states driven by the mouse position).
    def draw_banner(self):
        hover = pygame.mouse.get_pos() if not self.fast else (-1, -1)
        pixel_art.draw_panel(self.screen, pygame.Rect(0, 0, WIN_W, BANNER_H))
        self.screen.blit(get_font(24).render(BANNER_TEXT, True, TEXT), (14, 10))
        self.btn_ai = pygame.Rect(WIN_W - 340, 10, 160, 28)
        pixel_art.draw_button(self.screen, self.btn_ai, f"AI: {AGENTS[self.ai_index][0]}", BTN_BLUE,
                              self.btn_ai.collidepoint(hover))
        self.btn_new = pygame.Rect(WIN_W - 168, 10, 154, 28)
        pixel_art.draw_button(self.screen, self.btn_new, "New Game (R)", BTN_RED,
                              self.btn_new.collidepoint(hover))

    # Draw the turn-status banner under the board so the current owner and the
    # expected action are never ambiguous.
    def draw_turn_banner(self):
        ox, oy = self.vfx.get_shake_offset()
        if self.over:
            text, col = "GAME OVER", GOLD
        elif self.state.current_turn == 1:
            if self.dice_rolling:
                text, col = "ROLLING...", P1_FILL
            elif self.phase == "human_await_roll":
                text, col = "YOUR TURN - ROLL DICE", P1_FILL
            elif self.phase == "human_await_move":
                text, col = "YOUR TURN - SELECT A PIECE", P1_FILL
            else:
                text, col = "NO LEGAL MOVES - TURN SKIPPED", TEXT_DIM
        else:
            text, col = "AI THINKING...", P2_FILL
        f = get_font(20)
        surf = f.render(text, True, col)
        x = GRID_X + (5 * TILE - surf.get_width()) // 2 + ox
        y = GRID_Y + 3 * TILE + 44 + oy
        pygame.draw.rect(self.screen, (30, 28, 44), pygame.Rect(x - 10, y - 3, surf.get_width() + 20, surf.get_height() + 7), 2)
        self.screen.blit(surf, (x, y))

    # Draw the AI Decision Inspector panel on the right.
    # Shows: the human hint (when ON) in cyan with [RECOMMENDED], the most recent
    # AI decision (algorithm / nodes / time / evaluation bar / candidate scores),
    # and the Hint toggle button.
    def draw_inspector(self):
        x0 = LEFT_W + 10
        pw = WIN_W - x0 - 10
        panel = pygame.Rect(x0, BANNER_H + 10, pw, 320)
        pixel_art.draw_panel(self.screen, panel)
        pixel_art.draw_title(self.screen, x0 + 14, BANNER_H + 16, pw - 28, "AI DECISION INSPECTOR", GOLD)
        y = BANNER_H + 56
        # live human hint block (only when the toggle is ON and P1 is choosing)
        if self.hint:
            h = self.hint
            self.screen.blit(get_font(18).render(f"[HUMAN HINT - Expectiminimax d=4]  {h['nodes']} nodes  {h['ms']:.1f} ms", True, P1_FILL), (x0 + 14, y))
            y += 20
            for idx in range(3):
                if idx not in h["scores"]:
                    continue
                mark = " [RECOMMENDED]" if idx == h["best"] else ""
                line = f"#{idx+1} -> tile {h['targets'][idx]}   {h['scores'][idx]:+7.1f}{mark}"
                color = P1_FILL if idx == h["best"] else TEXT
                self.screen.blit(get_font(17).render(line, True, color), (x0 + 14, y))
                y += 19
            y += 4
        # most recent AI decision
        d = self.last_decision
        if d:
            self.screen.blit(get_font(18).render(f"Last AI - {d['alg']}: {d['nodes']} nodes, {d['ms']:.2f} ms", True, TEXT), (x0 + 14, y))
            y += 22
            val = max(-1000, min(1000, d["eval_p1"]))
            bar = pygame.Rect(x0 + 14, y, pw - 28, 14)
            mid = bar.centerx
            pygame.draw.rect(self.screen, (40, 38, 54), bar)
            w = abs(val) / 1000 * bar.width // 2
            if val >= 0:
                pygame.draw.rect(self.screen, P1_FILL, (bar.x, bar.y, w, bar.height))
            else:
                pygame.draw.rect(self.screen, P2_FILL, (mid - w, bar.y, w, bar.height))
            pygame.draw.line(self.screen, TEXT_DIM, (mid, bar.y - 2), (mid, bar.y + bar.height + 2), 1)
            self.screen.blit(get_font(13).render("P1 lead" if val >= 0 else "P2 lead", True, TEXT_DIM), (bar.right - 52, y - 14))
            y += 20
            self.screen.blit(get_font(15).render("Candidate Move Scores", True, TEXT_DIM), (x0 + 14, y))
            y += 16
            best = d["best"]
            for idx in range(3):
                if idx not in d["scores"]:
                    continue
                score = d["scores"][idx]
                mark = " [BEST]" if idx == best else ""
                line = f"#{idx+1} -> tile {d['targets'].get(idx, '?')}   {score:+7.1f}{mark}"
                color = HI if idx == best else TEXT
                self.screen.blit(get_font(17).render(line, True, color), (x0 + 14, y))
                bw = int(90 * max(0.0, min(1.0, (score + 200) / 400)))
                pygame.draw.rect(self.screen, GREEN if score >= 0 else RED, (bar.right - bw, y + 4, bw, 5))
                y += 19
        else:
            self.screen.blit(get_font(18).render("Waiting for the AI to decide...", True, TEXT_DIM), (x0 + 14, y))
        self.btn_hint = pygame.Rect(x0 + 14, panel.bottom - 32, 150, 24)
        hover = pygame.mouse.get_pos() if not self.fast else (-1, -1)
        pixel_art.draw_button(self.screen, self.btn_hint, f"Hint: {'ON' if self.hint_on else 'OFF'}", BTN_BLUE,
                              self.btn_hint.collidepoint(hover))

    # Draw the dice console (3D pixel dice + ROLL button + probabilities) and the
    # battle log (last 6 events, right column of the lower panel).
    def draw_dice_log(self):
        x0 = LEFT_W + 10
        y0 = BANNER_H + 344
        panel = pygame.Rect(x0, y0, WIN_W - x0 - 10, WIN_H - y0 - 10)
        pixel_art.draw_panel(self.screen, panel)
        pixel_art.draw_title(self.screen, x0 + 14, y0 + 10, 190, "DICE & BATTLE LOG", GOLD)
        dx, dy = self.dice_center()
        can_roll = (not self.over and not self.fast
                    and self.state.current_turn == 1 and self.phase == "human_await_roll")
        # face: "?" before the first roll, a random flicker mid-tumble, the real value after
        face = 0
        if self.dice_rolling:
            face = 1 + int((self.dice_roll_ms * 7) % 3)
        elif self.state.dice_roll and not self.state.is_terminal():
            face = self.state.dice_roll
        if self.state.is_terminal():
            face = self.state.dice_roll or 1
        # light bounce while tumbling: the sprite rises up to 4 px near the midpoint
        bounce = int(4 * abs(math.sin(self.dice_roll_ms / ROLL_ANIM_MS * math.pi))) if self.dice_rolling else 0
        die = self.art.dice[face]
        self.screen.blit(die, (dx - 36, dy - 36 - bounce))
        self.btn_roll = pygame.Rect(dx - 62, dy + 44, 124, 26)
        hover = pygame.mouse.get_pos() if not self.fast else (-1, -1)
        pixel_art.draw_button(self.screen, self.btn_roll, "ROLL (Space)", (44, 84, 52),
                              self.btn_roll.collidepoint(hover), can_roll)
        self.screen.blit(get_font(14).render("P(1)=25% P(2)=50% P(3)=25%", True, TEXT_DIM), (dx - 58, dy + 78))
        # right column: battle log (last 6, newest at the bottom)
        lx = x0 + 170
        ly = y0 + 44
        self.screen.blit(get_font(15).render("Last events:", True, TEXT_DIM), (lx, ly))
        ly += 18
        for line in self.log[-6:]:
            self.screen.blit(get_font(15).render(line[:34], True, TEXT), (lx, ly))
            ly += 20

    # Draw the semi-transparent game-over overlay with the winner and a play-again button.
    def draw_game_over(self):
        dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        self.screen.blit(dim, (0, 0))
        box = pygame.Rect(WIN_W // 2 - 210, WIN_H // 2 - 120, 420, 240)
        pixel_art.draw_panel(self.screen, box)
        winner = self.state.get_winner()
        who = "P1 (HUMAN)" if winner == 1 else "P2 (AI)"
        col = P1_FILL if winner == 1 else P2_FILL
        f = get_font(40)
        surf = f.render(f"{who} WINS!", True, col)
        self.screen.blit(surf, (box.centerx - surf.get_width() // 2, box.y + 34))
        t = get_font(22).render(f"Total turns: {self.turns}", True, TEXT)
        self.screen.blit(t, (box.centerx - t.get_width() // 2, box.y + 94))
        self.btn_again = pygame.Rect(box.centerx - 95, box.y + 148, 190, 40)
        hover = pygame.mouse.get_pos() if not self.fast else (-1, -1)
        pixel_art.draw_button(self.screen, self.btn_again, "Play Again (R)", (44, 84, 52),
                              self.btn_again.collidepoint(hover))

    # Handle one mouse press: buttons first, then legal pieces, then the hovered
    # target-preview cell (clicking the preview directly also moves the piece).
    # pos: (x, y) click coordinate.
    def on_click(self, pos):
        if self.over:
            if hasattr(self, "btn_again") and self.btn_again.collidepoint(pos):
                self.reset()
            return
        if hasattr(self, "btn_ai") and self.btn_ai.collidepoint(pos):
            self.ai_index = (self.ai_index + 1) % len(AGENTS)
            self.log.append(f"Opponent AI switched to {AGENTS[self.ai_index][0]}")
            return
        if hasattr(self, "btn_new") and self.btn_new.collidepoint(pos):
            self.reset()
            return
        if hasattr(self, "btn_hint") and self.btn_hint.collidepoint(pos):
            self.hint_on = not self.hint_on
            self.hint = self._compute_hint()      # compute on toggle, refresh after each roll
            return
        if hasattr(self, "btn_roll") and self.btn_roll.collidepoint(pos):
            if self.state.current_turn == 1 and self.phase == "human_await_roll" and not self.dice_rolling:
                self.human_roll()
            return
        # clicking a legal piece, or directly clicking its highlighted target cell, moves it
        if self.state.current_turn == 1 and self.phase == "human_await_move" and not self.dice_rolling:
            for idx in self.state.get_legal_moves():
                cx, cy = self.piece_pos(1, idx)
                if pygame.Rect(cx - 24, cy - 24, 48, 48).collidepoint(pos):
                    self.human_move(idx)
                    return
            target = self.target_cell_of(1, self.hover_idx) if self.hover_idx is not None else None
            if target is not None:
                r, c = target
                if cell_rect(r, c).collidepoint(pos):
                    self.human_move(self.hover_idx)
                    return

    # Update the hovered piece for the target-preview overlay.
    # pos: mouse (x, y); sets self.hover_idx (None when no legal piece is under it).
    def on_hover(self, pos):
        self.hover_idx = None
        if self.state.current_turn == 1 and self.phase == "human_await_move":
            for idx in self.state.get_legal_moves():
                cx, cy = self.piece_pos(1, idx)
                if pygame.Rect(cx - 24, cy - 24, 48, 48).collidepoint(pos):
                    self.hover_idx = idx
                    break

    # Return the grid cell of the target tile for a hovered piece.
    # player, idx: whose piece and which index; None when idx is None.
    def target_cell_of(self, player, idx):
        if idx is None:
            return None
        roll = self.state.dice_roll
        target = (self.state.p1_pieces if player == 1 else self.state.p2_pieces)[idx] + roll
        if target in (1, 2, 8, 9):
            return lane_cell(player, target)
        return shared_cell(target)

    # Draw the translucent target-tile preview for the hovered human piece.
    # ox, oy: shake offset; the preview uses red for a capture and gold for a rune.
    def draw_target_preview(self, ox, oy):
        if self.hover_idx is None:
            return
        target = self.state.p1_pieces[self.hover_idx] + self.state.dice_roll
        cell = self.target_cell_of(1, self.hover_idx)
        if cell is None:
            return
        r, c = cell
        rect = pygame.Rect(ox + GRID_X + c * TILE, oy + GRID_Y + r * TILE, TILE, TILE)
        enemy = self.state.p2_pieces
        capture = WAR_START <= target <= WAR_END and target != 4 and target in enemy
        rune = target in SAFE_TILES
        color = RED if capture else (GOLD if rune else GREEN)
        overlay = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        overlay.fill((*color, 60))
        self.screen.blit(overlay, rect)
        pygame.draw.rect(self.screen, color, rect, 3, border_radius=6)
        tag = "CAPTURE!" if capture else ("RUNE*" if rune else "GO")
        f = get_font(15)
        self.screen.blit(f.render(tag, True, color), (rect.centerx - f.size(tag)[0] // 2, rect.y + rect.height - 18))

    # Run the main event loop until the window is closed.
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.on_hover(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.on_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_SPACE:
                        if self.state.current_turn == 1 and self.phase == "human_await_roll" and not self.dice_rolling:
                            self.human_roll()
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        idx = event.key - pygame.K_1
                        if (self.state.current_turn == 1 and self.phase == "human_await_move"
                                and not self.dice_rolling and idx in self.state.get_legal_moves()):
                            self.human_move(idx)
            self.update(dt)
            self.render()
        pygame.quit()

    # Headless self-test: (1) fast-forward 30 AI steps with full rendering,
    # (2) exercise every human interaction branch (hover preview, button clicks,
    # piece click, target-cell click, Hint: ON), (3) force all four pixelfx
    # effects, advance a few frames and save gameplay_preview.png.
    def self_test(self):
        # ---- part 1: fast AI-vs-AI steps with full rendering ----
        steps = 0
        while steps < 30 and not self.over:
            self.update(16)
            self.render()
            steps += 1
        # ---- part 2: scripted human interaction QA on a fresh state ----
        self.reset()
        self.fast = True          # keep zero-delay updates for the scripted steps
        # force a known human position: P1 pieces at 0/1/2, P2 at 3, roll 2
        self.state = GameState(p1_pieces=[0, 1, 2], p2_pieces=[3, 0, 0], current_turn=1, dice_roll=2)
        self.phase = "human_await_move"
        legal = self.state.get_legal_moves()
        assert len(legal) > 0, "scripted position must have legal moves"
        # toggle Hint: ON while P1 is choosing - the hint must be computed live
        self.render()
        self.on_click(self.btn_hint.center)
        assert self.hint_on, "hint button must enable the hint"
        assert self.hint is not None and self.hint["scores"], "hint must be computed when toggled on a live position"
        self.render()
        # hover: the target preview rect must be valid and the preview draws without error
        cx, cy = self.piece_pos(1, legal[0])
        self.on_hover((cx, cy))
        assert self.hover_idx == legal[0], "hover must pick up the legal piece"
        target = self.target_cell_of(1, self.hover_idx)
        assert target is not None, "hovered piece must have a target cell"
        self.render()
        self.draw_target_preview(*self.vfx.get_shake_offset())
        # click the target preview cell directly: the move must be applied
        tr, tc = target
        self.on_click((GRID_X + tc * TILE + TILE // 2, GRID_Y + tr * TILE + TILE // 2))
        assert self.state.p1_pieces[legal[0]] in (2, 3, 4), f"target-cell click must move the piece, got {self.state.p1_pieces}"
        # click the AI toggle on a fresh scripted position: the opponent must cycle
        self.state = GameState(p1_pieces=[0, 1, 2], p2_pieces=[3, 0, 0], current_turn=1, dice_roll=2)
        self.phase = "human_await_move"
        self.hint = None
        before = self.ai_index
        self.render()
        self.on_click(self.btn_ai.center)
        assert self.ai_index != before, "AI button click must cycle the opponent"
        # click a legal piece centre: the move must be applied
        legal2 = self.state.get_legal_moves()
        cx2, cy2 = self.piece_pos(1, legal2[0])
        self.on_click((cx2, cy2))
        assert self.state.p1_pieces[legal2[0]] in (2, 3, 4), f"piece click must move it, got {self.state.p1_pieces}"
        self.render()
        print("[self-test] interaction QA passed (Hint: ON, hover preview, target-cell click, AI button, piece click)")
        # ---- part 3: fresh fast game mid-play, force all four effects, save the
        # preview (stop well before the game can end, so the overlay never covers the shot)
        self.reset()
        self.fast = True
        steps = 0
        while steps < 16 and not self.over:
            self.update(16)
            self.render()
            steps += 1
        c3, c4, c10 = self.tile_point(1, 3), self.tile_point(1, 4), self.tile_point(1, 10)
        self.vfx.spawn("dice_roll", *self.dice_center(), scale=0.55)
        self.vfx.spawn("hit_explosion", c3[0], c3[1], scale=0.65)
        self.vfx.spawn("rune_glow", c4[0], c4[1], scale=0.75)
        self.vfx.spawn("score_burst", c10[0], c10[1], scale=0.75)
        for _ in range(6):
            self.update(16)
        if self.rich_decision:
            self.last_decision = self.rich_decision
        self.render()
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gameplay_preview.png")
        pygame.image.save(self.screen, out)
        print(f"[self-test] rendered {steps} fast steps; preview saved to {out}")
        print(f"[self-test] game over={self.over}, winner={self.state.get_winner()}, turns={self.turns}")
        assert out and os.path.isfile(out), "preview png was not written"
        print("[self-test] all main.py UI checks passed")


# The selectable P2 opponents: (label, class). The two searchers run at depth 4.
AGENTS = [
    ("Expectiminimax", ExpectiminimaxAgent),
    ("Minimax", DeterministicMinimaxAgent),
    ("Greedy", GreedyAgent),
]


if __name__ == "__main__":
    random.seed(2026)
    self_test = "--self-test" in sys.argv
    if self_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    game = Game(fast=self_test)
    if self_test:
        game.self_test()
        pygame.quit()
    else:
        game.run()
