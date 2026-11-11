# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 4: pygame main loop - retro pixel UI, board, top banner, AI Decision
# Inspector panel, dice console, battle log, the four pixelfx effects bound to
# game events, and an optional --self-test headless run that renders 30 AI steps
# and saves gameplay_preview.png for planner visual QA.
#
# Usage:
#     python pixel_dice_ur/main.py               # real window for a human player
#     python pixel_dice_ur/main.py --self-test   # headless render + save preview png

import os
import sys
import random

# import the sibling Phase 1/2/3 modules (works both as a script and as a module)
try:
    from game_state import BOARD_END, DICE_PROBS, SAFE_TILES, WAR_START, GameState
    from ai_engine import (DeterministicMinimaxAgent, ExpectiminimaxAgent,
                           GreedyAgent, evaluate_state)
    from vfx_manager import VFXManager
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from game_state import BOARD_END, DICE_PROBS, SAFE_TILES, WAR_START, GameState
    from ai_engine import (DeterministicMinimaxAgent, ExpectiminimaxAgent,
                           GreedyAgent, evaluate_state)
    from vfx_manager import VFXManager

import pygame

# ---- authorship shown in the window title and the top banner (change once here) ----
AUTHOR_NAME = "LAW LI KANG RAIN"
STUDENT_ID = "1904VECI"
BANNER_TEXT = f"PIXEL DICE UR   |   Name: {AUTHOR_NAME}   |   Student ID: {STUDENT_ID}"

# ---- window / layout ----
WIN_W, WIN_H = 1024, 640
BANNER_H = 48
FPS = 60

BOARD_X0, BOARD_Y0 = 73, 218   # top-left of the 3x6 tile grid, centred in the left panel
TILE = 84                      # one tile is 84x84 px
LEFT_W = 650                   # left board panel width; right panel is WIN_W - LEFT_W

# ---- timing (ms) ----
HUMAN_PAUSE_MS = 700           # "No legal moves - Turn skipped" pause
AI_ROLL_WAIT_MS = 450          # natural pacing: roll -> show evaluation -> move
AI_MOVE_WAIT_MS = 450
SLIDE_MS = 180                 # short pixel slide of the moved piece

# ---- board topology: logical tile -> grid cell (row, col) on a 3x6 grid ----
# P1 = human = top lane (cyan/gold), P2 = AI = bottom lane (crimson/purple).
# Both share the middle war-zone row for tiles 3..7 and the finish tile 10.
#   P1: tile1/2 top row, tiles 3..7 shared middle, tiles 8/9 top-right, 10 middle-right
#   P2: mirrored on the bottom row
SHARED_CELL = {3: (1, 0), 4: (1, 1), 5: (1, 2), 6: (1, 3), 7: (1, 4), 10: (1, 5)}
LANE_CELL = {
    "1_0": (0, 2), "1_1": (0, 1), "1_2": (0, 0), "1_8": (0, 4), "1_9": (0, 5),
    "2_0": (2, 2), "2_1": (2, 1), "2_2": (2, 0), "2_8": (2, 4), "2_9": (2, 5),
}

# ---- palette ----
BG = (24, 22, 34)
PANEL = (34, 32, 48)
PANEL_EDGE = (64, 60, 92)
LANE_P1 = (38, 54, 70)
LANE_P2 = (58, 36, 54)
WAR = (46, 34, 54)
RUNE = (60, 44, 74)
FINISH = (52, 44, 28)
TEXT = (228, 224, 240)
TEXT_DIM = (150, 146, 168)
P1_FILL = (64, 200, 220)
P1_RING = (240, 210, 90)
P2_FILL = (214, 60, 84)
P2_RING = (150, 70, 170)
GOLD = (240, 200, 80)
GREEN = (90, 210, 120)
RED = (230, 80, 70)
HI = (255, 240, 120)


# Return the grid cell (row, col) for a player's logical tile.
# player: 1 or 2; tile: 0..10. Shared war/finish tiles use SHARED_CELL, the rest use
# the per-player lane mapping in LANE_CELL.
def tile_cell(player, tile):
    if tile in SHARED_CELL:
        return SHARED_CELL[tile]
    return LANE_CELL[f"{player}_{tile}"]


# Return the pygame Rect of a grid cell.
# row, col: the cell coordinates; the rect is TILE x TILE starting at the board origin.
def cell_rect(row, col):
    return pygame.Rect(BOARD_X0 + col * TILE, BOARD_Y0 + row * TILE, TILE, TILE)


# Return the pixel centre of a grid cell.
# row, col: the cell; used to place pieces and to anchor the pixelfx pivots.
def cell_center(row, col):
    return (BOARD_X0 + col * TILE + TILE // 2, BOARD_Y0 + row * TILE + TILE // 2)


# Cache a default bitmap font for a given pixel height (retro look, fast to render).
# size: font height in pixels.
_font_cache = {}
def get_font(size):
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]


# Draw a pixel-style rounded button and return its Rect for click hit-testing.
# surface: where to blit; rect: button bounds; label: text; color/fill: body colors;
# enabled: when False the button is dimmed. Returns rect.
def draw_button(surface, rect, label, color, enabled=True):
    fill = color if enabled else (50, 48, 66)
    pygame.draw.rect(surface, fill, rect, border_radius=4)
    pygame.draw.rect(surface, TEXT if enabled else TEXT_DIM, rect, 2, border_radius=4)
    font = get_font(18)
    surf = font.render(label, True, TEXT if enabled else TEXT_DIM)
    surface.blit(surf, (rect.centerx - surf.get_width() // 2, rect.centery - surf.get_height() // 2))
    return rect


class Game:
    # Build the game.
    # fast: when True (self-test) all waits collapse to 0, the human side auto-plays
    # with a GreedyAgent, and slide animation is skipped so a full game can be
    # simulated headlessly in a loop.
    def __init__(self, fast=False):
        pygame.display.set_caption(f"Pixel Dice Ur - {AUTHOR_NAME} - {STUDENT_ID}")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.fast = fast
        self.reset()

    # Reset to a fresh game: new state, clear VFX/shake, fresh logs and decision data.
    # The selected P2 AI is kept so New Game restarts against the same opponent.
    def reset(self):
        if not hasattr(self, "ai_index"):
            self.ai_index = 0          # 0=Expectiminimax, 1=Minimax, 2=Greedy
        self.state = GameState()
        self.vfx = VFXManager()
        self.turns = 0                 # total completed moves
        self.log = []
        self.last_decision = None      # most recent AI decision (for the inspector)
        self.rich_decision = None     # most recent AI decision that had real candidates (for the preview)
        self.hint = None               # live Expectiminimax hint for the human position
        self.hint_on = False
        self.slides = {}               # (player, idx) -> slide animation dict
        self.phase = "idle"            # "human_await_roll" | "human_await_move" | "ai_think" | "skip_wait"
        self.phase_ms = 0
        self.ai_roll_done = False
        self.ai_moved = False
        self.over = False
        self.hover_idx = None          # human piece under the cursor (for target preview)
        self.pulse = 0.0              # drives the legal-move pulsing frame
        # P1 human auto-play helper for fast/self-test mode
        self.human_agent = GreedyAgent() if self.fast else None
        self.set_phase("human_await_roll")

    # Advance a game to a new named phase and reset its timer.
    # name: one of the phase states; the phase timer restarts at 0.
    def set_phase(self, name):
        self.phase = name
        self.phase_ms = 0
        self.ai_roll_done = False
        self.ai_moved = False

    # Compute the centre screen point where a moved piece's pixelfx pivot should sit.
    # player, tile: whose piece and at which logical tile; uses cell_center of its cell.
    def tile_point(self, player, tile):
        r, c = tile_cell(player, tile)
        return cell_center(r, c)

    # Begin the AI's turn: first wait, then roll the die (with a dice_roll effect at the
    # dice icon), so the player can watch the AI "think" before it commits.
    def ai_begin(self):
        self.set_phase("ai_think")
        cx, cy = self.dice_center()
        self.vfx.spawn("dice_roll", cx, cy, scale=0.55)
        self.state.roll_dice()
        self.log.append(f"P2 rolled {self.state.dice_roll}")
        self.ai_roll_done = True
        if not self.state.get_legal_moves():
            self.do_ai_move(None)      # no legal move: the AI still "plays" the skip

    # Perform the AI's chosen move: run the selected agent, record the decision for the
    # inspector, apply it, animate the slide and fire the event effects.
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
        from_tile = (self.state.p1_pieces if player == 1 else self.state.p2_pieces)[idx] if idx is not None else -1
        self.state, ev = self.state.apply_move(idx, roll)
        self.turns += 1
        to_tile = ev["target_tile"]
        # slide the moved piece (skipped entirely in fast mode)
        if idx is not None and not self.fast:
            # a captured enemy piece snaps back to its staging tile instantly (its own
            # tile 0), so no slide is needed for it - the explosion VFX sells the capture
            from_c = tile_cell(player, from_tile)
            to_c = tile_cell(player, to_tile)
            self.slides[(player, idx)] = {"from": cell_center(*from_c), "to": cell_center(*to_c), "t": 0}
        # event effects, anchored at the target/finish tile
        cx, cy = self.tile_point(player, to_tile) if to_tile >= 0 else (WIN_W // 2, WIN_H // 2)
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

    # Return the centre of the dice icon on the right panel (dice_roll effect anchor).
    # Must match the dice face drawn in draw_dice_log (left column of the lower panel).
    def dice_center(self):
        x0 = LEFT_W + 10
        y0 = BANNER_H + 344
        return (x0 + 70, y0 + 88)

    # Human roll: roll the die, spawn the dice_roll effect, and move to move selection.
    def human_roll(self):
        self.state.roll_dice()
        cx, cy = self.dice_center()
        self.vfx.spawn("dice_roll", cx, cy, scale=0.55)
        self.log.append(f"P1 rolled {self.state.dice_roll}")
        if not self.state.get_legal_moves():
            self.set_phase("skip_wait")
            self.log.append("P1 no legal moves - Turn skipped")
        else:
            self.set_phase("human_await_move")

    # Human move: apply the chosen piece and animate/effects; if the result is a skip or
    # bonus we re-evaluate the phase, otherwise hand the turn to the AI.
    # idx: piece index to move.
    def human_move(self, idx):
        self.apply_and_animate(1, idx, self.state.dice_roll)
        if not self.over:
            if self.state.current_turn == 1:
                # bonus turn: P1 keeps moving, roll again
                self.set_phase("human_await_roll")
            else:
                self.set_phase("ai_think")

    # Advance the game one update tick.
    # dt_ms: real milliseconds since last update; drives timers, slides, VFX, pulse.
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
        self.phase_ms += dt
        if self.fast:
            # auto-drive whichever side is to move with zero delay.
            # apply_move never clears dice_roll, so roll a fresh die at the start of
            # every side's turn (including bonus turns, which keep current_turn).
            if self.state.current_turn == 1:
                self.state.roll_dice()
                move, _, _ = self.human_agent.choose_move(self.state)
                self.human_move(move if move is not None else None)
            else:
                self.state.roll_dice()
                self.log.append(f"P2 rolled {self.state.dice_roll}")
                agent = self.make_ai_agent()
                move, scores, stats = agent.choose_move(self.state)
                roll = self.state.dice_roll
                targets = {i: self.state.p2_pieces[i] + roll for i in scores}
                # populate the inspector with this decision
                self.last_decision = {
                    "alg": AGENTS[self.ai_index][0],
                    "nodes": stats["nodes"],
                    "ms": stats["time_ms"],
                    "scores": scores,
                    "best": move,
                    "targets": targets,
                    "eval_p1": evaluate_state(self.state, 1),
                }
                if scores:
                    self.rich_decision = dict(self.last_decision)
                self.apply_and_animate(2, move, roll)
            return
        # normal (human vs AI) pacing
        if self.phase == "ai_think":
            if self.phase_ms >= AI_ROLL_WAIT_MS and not self.ai_roll_done:
                self.ai_begin()
            if self.phase_ms >= AI_ROLL_WAIT_MS + AI_MOVE_WAIT_MS and self.ai_roll_done and not self.ai_moved:
                self.do_ai_move(None)
        elif self.phase == "skip_wait":
            if self.phase_ms >= HUMAN_PAUSE_MS:
                # apply the skip then hand to the AI
                self.apply_and_animate(1, None, self.state.dice_roll)
                if not self.over and self.state.current_turn == 2:
                    self.set_phase("ai_think")

    # Return the screen position to render a piece at, honouring any active slide.
    # player, idx: which piece; if it is mid-slide, return the interpolated centre,
    # otherwise its static cell centre (with a small vertical nudge when the enemy
    # also sits on the same shared tile).
    def piece_pos(self, player, idx):
        key = (player, idx)
        if key in self.slides:
            s = self.slides[key]
            f = min(1.0, s["t"] / SLIDE_MS)
            x = s["from"][0] + (s["to"][0] - s["from"][0]) * f
            y = s["from"][1] + (s["to"][1] - s["from"][1]) * f
            return int(x), int(y)
        tile = (self.state.p1_pieces if player == 1 else self.state.p2_pieces)[idx]
        cx, cy = self.tile_point(player, tile)
        enemy = 2 if player == 1 else 1
        enemy_tiles = self.state.p2_pieces if enemy == 2 else self.state.p1_pieces
        if enemy_tiles.count(tile) and tile in SHARED_CELL:
            cy = cy - 8 if player == 1 else cy + 8
        return cx, cy

    # ---- rendering ----
    def render(self):
        self.screen.fill(BG)
        ox, oy = self.vfx.get_shake_offset()   # board + pieces follow the shake
        self.draw_board(ox, oy)
        self.draw_pieces(ox, oy)
        self.draw_banner()
        self.draw_inspector()
        self.draw_dice_log()
        # VFX draws with offset=(0,0): it already adds the shake internally, so the
        # effects do not get a double shake on top of the board's own offset
        self.vfx.draw(self.screen, (0, 0))
        if self.over:
            self.draw_game_over()
        pygame.display.flip()

    # Draw the 3x6 tile grid with per-tile styling (lanes, war zone, rune sigil, finish).
    # ox, oy: the screen-shake offset applied to every board element.
    def draw_board(self, ox, oy):
        for r in range(3):
            for c in range(6):
                rect = pygame.Rect(ox + BOARD_X0 + c * TILE, oy + BOARD_Y0 + r * TILE, TILE, TILE)
                # classify this cell's logical identity for the top lane / middle / bottom
                color = (30, 28, 42)
                label_tile = None
                if r == 1:
                    if c in (0, 1, 2, 3, 4):
                        color, label_tile = WAR, c + 3          # shared war zone 3..7
                    elif c == 5:
                        color, label_tile = FINISH, 10          # finish tile
                elif r == 0:
                    p1_tile = {0: 2, 1: 1, 2: 0, 4: 8, 5: 9}.get(c)
                    if c == 2:
                        color, label_tile = LANE_P1, 0
                    elif p1_tile:
                        color, label_tile = LANE_P1, p1_tile
                else:
                    p2_tile = {0: 2, 1: 1, 2: 0, 4: 8, 5: 9}.get(c)
                    if c == 2:
                        color, label_tile = LANE_P2, 0
                    elif p2_tile:
                        color, label_tile = LANE_P2, p2_tile
                pygame.draw.rect(self.screen, color, rect, border_radius=6)
                # pixel double border + soft shadow
                pygame.draw.rect(self.screen, (18, 16, 26), rect, 3, border_radius=6)
                pygame.draw.rect(self.screen, (70, 66, 96), rect.inflate(-6, -6), 1, border_radius=4)
                # rune sigil on tile 4
                if label_tile == 4:
                    pygame.draw.rect(self.screen, RUNE, rect, border_radius=6)
                    pygame.draw.circle(self.screen, GOLD, (rect.centerx, rect.centery), 24, 3)
                    pygame.draw.circle(self.screen, (200, 120, 255), (rect.centerx, rect.centery), 16, 2)
                    for a in range(8):
                        import math
                        x = rect.centerx + int(math.cos(a * math.pi / 4) * 22)
                        y = rect.centery + int(math.sin(a * math.pi / 4) * 22)
                        pygame.draw.circle(self.screen, GOLD, (x, y), 2)
                # finish mark on tile 10
                if label_tile == 10:
                    pygame.draw.circle(self.screen, GOLD, (rect.centerx, rect.centery), 18, 2)
                    pygame.draw.circle(self.screen, GREEN, (rect.centerx, rect.centery), 8)
                if label_tile is not None and label_tile not in (4, 10):
                    tag = f"{label_tile}"
                    if label_tile in SAFE_TILES:
                        tag += "*"
                    f = get_font(16)
                    self.screen.blit(f.render(tag, True, TEXT_DIM), (rect.x + 6, rect.y + 5))
        # lane direction arrows (P1 top left->right into the war zone; P2 bottom)
        for (ax, ay, dx) in ((BOARD_X0 + 40, BOARD_Y0 + 12, 1), (BOARD_X0 + 40, BOARD_Y0 + 2 * TILE - 12, 1)):
            pygame.draw.polygon(self.screen, TEXT_DIM,
                                [(ax + ox, ay + oy), (ax + dx * 16 + ox, ay + oy - 8), (ax + dx * 16 + ox, ay + oy + 8)])
        # scored trays
        p1_scored = sum(1 for p in self.state.p1_pieces if p == BOARD_END)
        p2_scored = sum(1 for p in self.state.p2_pieces if p == BOARD_END)
        f = get_font(18)
        self.screen.blit(f.render(f"P1 Scored: {p1_scored}/3", True, P1_FILL), (ox + BOARD_X0, oy + BOARD_Y0 - 26))
        self.screen.blit(f.render(f"P2 Scored: {p2_scored}/3", True, P2_FILL), (ox + BOARD_X0, oy + BOARD_Y0 + 3 * TILE + 8))

    # Draw all six pieces at their current (possibly sliding) positions.
    # ox, oy: the screen-shake offset.
    def draw_pieces(self, ox, oy):
        for player, fill, ring in ((1, P1_FILL, P1_RING), (2, P2_FILL, P2_RING)):
            pieces = self.state.p1_pieces if player == 1 else self.state.p2_pieces
            legal = self.state.get_legal_moves() if (player == 1 and self.phase in ("human_await_move", "skip_wait")) else []
            for idx in range(3):
                if pieces[idx] >= BOARD_END and pieces[idx] == BOARD_END:
                    # finished pieces sit in the score tray, not on the board
                    continue
                cx, cy = self.piece_pos(player, idx)
                cx, cy = cx + ox, cy + oy
                pygame.draw.circle(self.screen, ring, (cx, cy), 16, 3)
                pygame.draw.circle(self.screen, fill, (cx, cy), 13)
                f = get_font(18)
                self.screen.blit(f.render(f"{idx+1}", True, (12, 12, 16)), (cx - 5, cy - 9))
                if idx in legal:
                    import math
                    glow = 12 + int(6 * math.sin(self.pulse))
                    pygame.draw.rect(self.screen, HI, pygame.Rect(cx - glow, cy - glow, glow * 2, glow * 2), 2, border_radius=6)

    # Draw the top banner: title + author on the left, AI/New-Game buttons on the right.
    def draw_banner(self):
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(0, 0, WIN_W, BANNER_H))
        pygame.draw.line(self.screen, PANEL_EDGE, (0, BANNER_H - 1), (WIN_W, BANNER_H - 1), 2)
        f = get_font(24)
        self.screen.blit(f.render(BANNER_TEXT, True, TEXT), (14, 10))
        self.btn_ai = pygame.Rect(WIN_W - 330, 10, 150, 28)
        draw_button(self.screen, self.btn_ai, f"AI: {AGENTS[self.ai_index][0]}", (52, 60, 90), True)
        self.btn_new = pygame.Rect(WIN_W - 160, 10, 146, 28)
        draw_button(self.screen, self.btn_new, "New Game (R)", (60, 44, 60), True)

    # Draw the AI Decision Inspector panel on the right.
    def draw_inspector(self):
        x0 = LEFT_W + 10
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(x0, BANNER_H + 10, WIN_W - x0 - 10, 320), border_radius=6)
        pygame.draw.rect(self.screen, PANEL_EDGE, pygame.Rect(x0, BANNER_H + 10, WIN_W - x0 - 10, 320), 2, border_radius=6)
        self.screen.blit(get_font(22).render("AI DECISION INSPECTOR", True, GOLD), (x0 + 14, BANNER_H + 20))
        y = BANNER_H + 50
        if self.last_decision:
            d = self.last_decision
            self.screen.blit(get_font(18).render(f"Algorithm: {d['alg']}   Nodes: {d['nodes']}   Time: {d['ms']:.2f} ms", True, TEXT), (x0 + 14, y))
            y += 24
            # evaluation bar: P1 lead to the left (cyan), P2 lead to the right (crimson)
            val = max(-1000, min(1000, d["eval_p1"]))
            bar = pygame.Rect(x0 + 14, y, WIN_W - x0 - 42, 16)
            mid = bar.centerx
            self.screen.blit(get_font(14).render("Evaluation", True, TEXT_DIM), (x0 + 14, y + 18))
            pygame.draw.rect(self.screen, (40, 38, 54), bar)
            w = abs(val) / 1000 * bar.width // 2
            if val >= 0:
                pygame.draw.rect(self.screen, P1_FILL, (bar.x, bar.y, w, bar.height))
            else:
                pygame.draw.rect(self.screen, P2_FILL, (mid - w, bar.y, w, bar.height))
            pygame.draw.line(self.screen, TEXT_DIM, (mid, bar.y - 2), (mid, bar.y + bar.height + 2), 1)
            y += 44
            # candidate move scores
            self.screen.blit(get_font(16).render("Candidate Move Scores", True, TEXT_DIM), (x0 + 14, y))
            y += 18
            best = d["best"]
            for idx in range(3):
                if idx not in d["scores"]:
                    continue
                score = d["scores"][idx]
                target = d["targets"].get(idx, "?")
                mark = " [BEST]" if idx == best else ""
                line = f"#{idx+1} -> tile {target}   {score:+8.1f}{mark}"
                color = HI if idx == best else TEXT
                self.screen.blit(get_font(18).render(line, True, color), (x0 + 14, y))
                # small horizontal score bar
                bw = int(120 * max(0, min(1, (score + 200) / 400)))
                pygame.draw.rect(self.screen, GREEN if score >= 0 else RED,
                                 (x0 + WIN_W - x0 - 140, y + 5, bw, 6))
                y += 22
        else:
            self.screen.blit(get_font(18).render("Waiting for the AI to decide...", True, TEXT_DIM), (x0 + 14, y))
        # hint toggle for the human position
        self.btn_hint = pygame.Rect(x0 + 14, BANNER_H + 10 + 320 - 34, 150, 24)
        draw_button(self.screen, self.btn_hint, f"Hint: {'ON' if self.hint_on else 'OFF'}", (52, 60, 90), True)

    # Draw the dice console and the rolling battle log on the lower-right panel.
    # Layout: left column holds the pixel dice + ROLL button + probability line;
    # right column holds the last 6 battle-log events, so nothing overlaps the title.
    def draw_dice_log(self):
        x0 = LEFT_W + 10
        y0 = BANNER_H + 344
        h = WIN_H - y0 - 10
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(x0, y0, WIN_W - x0 - 10, h), border_radius=6)
        pygame.draw.rect(self.screen, PANEL_EDGE, pygame.Rect(x0, y0, WIN_W - x0 - 10, h), 2, border_radius=6)
        self.screen.blit(get_font(20).render("DICE & BATTLE LOG", True, GOLD), (x0 + 14, y0 + 10))
        # left column: pixel dice face
        dx = x0 + 70
        dy = y0 + 88
        can_roll = (not self.over and self.state.current_turn == 1
                    and self.phase == "human_await_roll" and not self.fast)
        pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(dx - 28, dy - 28, 56, 56), border_radius=6)
        pygame.draw.rect(self.screen, (20, 20, 30), pygame.Rect(dx - 28, dy - 28, 56, 56), 2, border_radius=6)
        face = self.state.dice_roll or 0
        dots = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)]}
        for gx, gy in dots.get(face, []):
            pygame.draw.circle(self.screen, (20, 20, 30), (dx + gx * 14, dy + gy * 14), 5)
        if face == 0:
            self.screen.blit(get_font(28).render("?", True, (20, 20, 30)), (dx - 8, dy - 12))
        # roll button + probability line under the dice
        self.btn_roll = pygame.Rect(dx - 62, dy + 38, 124, 26)
        draw_button(self.screen, self.btn_roll, "ROLL (Space)", GREEN, can_roll)
        self.screen.blit(get_font(14).render("P1=25% P2=50% P3=25%", True, TEXT_DIM), (dx - 55, dy + 70))
        # right column: battle log (last 6, newest at the bottom)
        lx = x0 + 170
        ly = y0 + 40
        self.screen.blit(get_font(15).render("Last events:", True, TEXT_DIM), (lx, ly))
        ly += 18
        for line in self.log[-6:]:
            self.screen.blit(get_font(15).render(line[:34], True, TEXT), (lx, ly))
            ly += 20

    # Draw the semi-transparent game-over overlay with the winner and a play-again button.
    def draw_game_over(self):
        dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        self.screen.blit(dim, (0, 0))
        box = pygame.Rect(WIN_W // 2 - 200, WIN_H // 2 - 110, 400, 220)
        pygame.draw.rect(self.screen, PANEL, box, border_radius=10)
        pygame.draw.rect(self.screen, GOLD, box, 3, border_radius=10)
        winner = self.state.get_winner()
        who = "P1 (HUMAN)" if winner == 1 else "P2 (AI)"
        col = P1_FILL if winner == 1 else P2_FILL
        self.screen.blit(get_font(40).render(f"{who} WINS!", True, col), (box.centerx - 110, box.y + 30))
        self.screen.blit(get_font(22).render(f"Total turns: {self.turns}", True, TEXT), (box.centerx - 70, box.y + 90))
        self.btn_again = pygame.Rect(box.centerx - 90, box.y + 140, 180, 40)
        draw_button(self.screen, self.btn_again, "Play Again (R)", GREEN, True)

    # Handle one mouse press.
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
            if self.hint_on and self.state.dice_roll:
                move, scores, stats = ExpectiminimaxAgent(depth=4).choose_move(self.state)
                self.hint = {"scores": scores, "best": move}
            return
        if hasattr(self, "btn_roll") and self.btn_roll.collidepoint(pos):
            if self.state.current_turn == 1 and self.phase == "human_await_roll":
                self.human_roll()
            return
        # clicking a legal piece or its target preview moves it
        if self.state.current_turn == 1 and self.phase == "human_await_move":
            for idx in self.state.get_legal_moves():
                cx, cy = self.piece_pos(1, idx)
                if pygame.Rect(cx - 24, cy - 24, 48, 48).collidepoint(pos):
                    self.human_move(idx)
                    return

    # Update the hovered piece for the target-preview overlay.
    # pos: mouse (x, y); returns nothing, sets self.hover_idx.
    def on_hover(self, pos):
        self.hover_idx = None
        if self.state.current_turn == 1 and self.phase == "human_await_move":
            for idx in self.state.get_legal_moves():
                cx, cy = self.piece_pos(1, idx)
                if pygame.Rect(cx - 24, cy - 24, 48, 48).collidepoint(pos):
                    self.hover_idx = idx
                    break

    # Draw the translucent target-tile preview for the hovered human piece.
    # ox, oy: shake offset; the preview uses red for a capture and gold/purple for a rune.
    def draw_target_preview(self, ox, oy):
        if self.hover_idx is None:
            return
        roll = self.state.dice_roll
        target = self.state.p1_pieces[self.hover_idx] + roll
        r, c = tile_cell(1, target)
        rect = pygame.Rect(ox + BOARD_X0 + c * TILE, oy + BOARD_Y0 + r * TILE, TILE, TILE)
        enemy = self.state.p2_pieces
        capture = WAR_START <= target <= WAR_END and target != 4 and target in enemy
        rune = target in SAFE_TILES
        color = RED if capture else (GOLD if rune else GREEN)
        overlay = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        overlay.fill((*color, 60))
        self.screen.blit(overlay, rect)
        pygame.draw.rect(self.screen, color, rect, 3, border_radius=6)
        tag = "CAPTURE!" if capture else ("RUNE*" if rune else "")
        if tag:
            self.screen.blit(get_font(16).render(tag, True, color), (rect.centerx - 30, rect.y + rect.height - 18))

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
                        if self.state.current_turn == 1 and self.phase == "human_await_roll":
                            self.human_roll()
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        idx = event.key - pygame.K_1
                        if self.state.current_turn == 1 and self.phase == "human_await_move" and idx in self.state.get_legal_moves():
                            self.human_move(idx)
            self.update(dt)
            self.render()
            self.draw_target_preview(*self.vfx.get_shake_offset())
        pygame.quit()

    # Headless self-test: fast-forward ~30 AI-vs-AI steps with full rendering and VFX,
    # then force all four effects on a mid-game frame and save gameplay_preview.png.
    def self_test(self):
        # fast-forward 30 steps of a simulated AI-vs-AI game, rendering every step
        steps = 0
        while steps < 30 and not self.over:
            self.update(16)
            self.render()
            self.draw_target_preview(0, 0)
            steps += 1
        # force all four pixelfx effects to appear in the preview for planner visual QA
        c3, c4 = self.tile_point(1, 4), self.tile_point(2, 4)
        c10 = self.tile_point(1, 10)
        self.vfx.spawn("dice_roll", self.dice_center()[0], self.dice_center()[1], scale=0.55)
        self.vfx.spawn("hit_explosion", c3[0], c3[1], scale=0.65)
        self.vfx.spawn("rune_glow", c4[0], c4[1], scale=0.75)
        self.vfx.spawn("score_burst", c10[0], c10[1], scale=0.75)
        # advance a couple of frames so the effects are mid-animation in the shot
        for _ in range(6):
            self.update(16)
        # show the most recent AI decision that had real candidate scores so the
        # planner can QA the inspector panel (a bare "skip" step leaves it empty)
        if self.rich_decision:
            self.last_decision = self.rich_decision
        self.render()
        self.draw_target_preview(0, 0)
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
