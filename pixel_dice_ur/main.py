# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 4.8: Pygame main loop with Babylonian pixel-art visuals (pixel_art bank),
# procedural retro audio (sound_fx, zero external assets, headless-safe),
# midnight temple background with animated braziers, floating combat text,
# match-summary game-over panel, and polished top bar / legend / battle log.
# All Phase 4.6/4.7 fixes are preserved: unified _enter_phase state machine,
# integer glow tier, target_cell_of out-of-range guard, S-curve arrows painted
# over tiles, and two-stage Shrine->Tray scoring slide.

import math
import os
import random
import sys

try:
    from game_state import (BOARD_END, DICE_PROBS, SAFE_TILES, WAR_START,
                            WAR_END, GameState)
    from ai_engine import (DeterministicMinimaxAgent, ExpectiminimaxAgent,
                           GreedyAgent, evaluate_state)
    from vfx_manager import VFXManager
    import pixel_art
    import sound_fx
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from game_state import (BOARD_END, DICE_PROBS, SAFE_TILES, WAR_START,
                            WAR_END, GameState)
    from ai_engine import (DeterministicMinimaxAgent, ExpectiminimaxAgent,
                           GreedyAgent, evaluate_state)
    from vfx_manager import VFXManager
    import pixel_art
    import sound_fx

import pygame

# Update AUTHOR_NAME and STUDENT_ID here once before final submission
AUTHOR_NAME = "LAW LI KANG RAIN"
STUDENT_ID = "1904VECI"
# Phase 4.8: compact left banner; three right-side buttons follow it with a safe gap.
BANNER_TEXT = f"PIXEL DICE UR | {AUTHOR_NAME} | ID: {STUDENT_ID}"

WIN_W, WIN_H = 1024, 640
BANNER_H = 48
FPS = 60

TILE = 84
GRID_X, GRID_Y = 73, 188        # 3x6 grid spans x=73..577, y=188..440 (cleanly centered in LEFT_W=650)
LEFT_W = 650

# Non-overlapping symmetrical 3-slot Reserve Docks and Scored Trays (74px tall, 32px horizontal gap)
DOCK_W, DOCK_H = 236, 74
P1_DOCK = pygame.Rect(GRID_X, GRID_Y - DOCK_H - 14, DOCK_W, DOCK_H)
P1_TRAY = pygame.Rect(GRID_X + 6 * TILE - DOCK_W, GRID_Y - DOCK_H - 14, DOCK_W, DOCK_H)
P2_DOCK = pygame.Rect(GRID_X, GRID_Y + 3 * TILE + 14, DOCK_W, DOCK_H)
P2_TRAY = pygame.Rect(GRID_X + 6 * TILE - DOCK_W, GRID_Y + 3 * TILE + 14, DOCK_W, DOCK_H)
LEGEND_RECT = pygame.Rect(GRID_X, P2_DOCK.bottom + 12, 6 * TILE, 68)

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

HUMAN_PAUSE_MS = 700
AI_ROLL_WAIT_MS = 420
AI_MOVE_WAIT_MS = 450
SLIDE_MS = 220
ROLL_ANIM_MS = 260

TEXT = (232, 228, 244)
TEXT_DIM = (156, 150, 176)
P1_FILL = (64, 208, 228)
P2_FILL = (224, 64, 90)
GOLD = (244, 204, 88)
GREEN = (96, 220, 132)
RED = (234, 82, 74)
HI = (255, 242, 126)
BTN_BLUE = (48, 62, 96)
BTN_RED = (72, 42, 62)

_font_cache = {}


# Return a cached crisp system font for UI text so labels look clean rather than jagged.
# size: target height in pixels; font_obj: cached pygame.font.Font instance.
def get_font(size):
    if size not in _font_cache:
        font_obj = pygame.font.SysFont("consolas,verdana,arial", max(11, int(size * 0.72)), bold=True)
        if font_obj is None:
            font_obj = pygame.font.Font(None, size)
        _font_cache[size] = font_obj
    return _font_cache[size]


# Map a player's private lane tile (1, 2, 8, or 9) to its `(row, col)` on the 3x6 grid.
# player: 1 (human top lane) or 2 (AI bottom lane); tile: integer lane index.
def lane_cell(player, tile):
    row = 0 if player == 1 else 2
    return {1: (row, 1), 2: (row, 0), 8: (row, 4), 9: (row, 5)}[tile]


# Map a shared war-zone or finish tile (3..7 or 10) to its `(row, col)` on the middle row.
# tile: integer shared tile index (safely returns None if out of range).
def shared_cell(tile):
    return {3: (1, 0), 4: (1, 1), 5: (1, 2), 6: (1, 3), 7: (1, 4), 10: (1, 5)}.get(tile)


# Compute the pixel center `(cx, cy)` of grid cell `(row, col)`.
# row, col: 0-based grid coordinates on the 3x6 board.
def cell_center(row, col):
    return (GRID_X + col * TILE + TILE // 2, GRID_Y + row * TILE + TILE // 2)


# Build the bounding `pygame.Rect` of grid cell `(row, col)`.
# row, col: 0-based grid coordinates on the 3x6 board.
def cell_rect(row, col):
    return pygame.Rect(GRID_X + col * TILE, GRID_Y + row * TILE, TILE, TILE)


class Game:
    # Initialize the Pygame display, pre-bake pixel-art surfaces, start the
    # procedural audio bank, and start a fresh match.
    # fast: True only during headless fast-forward steps; False for normal 60 FPS gameplay.
    def __init__(self, fast=False):
        pygame.display.set_caption(f"Pixel Dice Ur - {AUTHOR_NAME} - {STUDENT_ID}")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.fast = fast
        p1_entry_way, p1_exit_way = self._lane_waypoints(1)
        p2_entry_way, p2_exit_way = self._lane_waypoints(2)
        geo = {
            "win": (WIN_W, WIN_H),
            "p1_dock": P1_DOCK, "p2_dock": P2_DOCK,
            "p1_tray": P1_TRAY, "p2_tray": P2_TRAY,
            "p1_way": p1_entry_way + [(0, 0)] if False else p1_entry_way,
            "p2_way": p2_entry_way,
            "shared_way": [cell_center(1, c) for c in range(5)],
        }
        # Combine entry and sprint segments per player cleanly for `_bake_path_layer`
        self.art = pixel_art.PixelArtBank(geo)
        # Also paint the sprint exit arrows `7 -> 8* -> 9 -> 10 (Shrine)` onto `path_layer`!
        self.art._dash(self.art.path_layer, p1_exit_way, (90, 218, 240, 215))
        self.art._dash(self.art.path_layer, p2_exit_way, (240, 96, 128, 215))
        # Phase 4.8: lazy audio init (silent no-op under SDL_VIDEODRIVER=dummy),
        # floating combat text list, and per-player bonus-turn counters.
        sound_fx.init_audio()
        self.floats = []
        self.bonus_count = {1: 0, 2: 0}
        self.reset()
        sound_fx.start_bgm()

    # Build the entry (`Reserve -> 1 -> 2 -> 3`) and exit (`7 -> 8* -> 9 -> 10`) waypoint
    # chains so every single step along the S-curve track has a visible directional arrow!
    # player: 1 or 2; row/dock: player-specific lane row and starting dock Rect.
    def _lane_waypoints(self, player):
        row = 0 if player == 1 else 2
        dock = P1_DOCK if player == 1 else P2_DOCK
        entry = [
            (cell_center(row, 1)[0], dock.bottom if player == 1 else dock.top),
            cell_center(row, 1),
            cell_center(row, 0),
            cell_center(1, 0),
        ]
        sprint = [
            cell_center(1, 4),
            cell_center(row, 4),
            cell_center(row, 5),
            cell_center(1, 5),
        ]
        return entry, sprint

    # Reset match state, animations, logs, and turn timers while keeping the chosen AI difficulty.
    # self.ai_index: index into AGENTS selecting Expectiminimax, Minimax, or Greedy.
    def reset(self):
        if not hasattr(self, "ai_index"):
            self.ai_index = 0
        if not hasattr(self, "hint_on"):
            self.hint_on = False
        self.state = GameState()
        self.vfx = VFXManager()
        self.turns = 0
        self.log = ["Ready! Press SPACE to roll."]
        self.floats = []
        self.bonus_count = {1: 0, 2: 0}
        self.last_decision = None
        self.rich_decision = None
        self.hint = None
        self.slides = {}
        self.dice_rolling = False
        self.dice_roll_ms = 0
        self.over = False
        self.hover_idx = None
        self.pulse = 0.0
        self.human_agent = GreedyAgent()
        self._enter_phase("human_await_roll")

    # Transition cleanly into a turn phase and reset all per-phase timers, hover, and AI flags.
    # name: phase identifier ("human_await_roll", "human_await_move", "skip_wait", "ai_think").
    def _enter_phase(self, name):
        self.phase = name
        self.phase_ms = 0
        self.ai_roll_done = False
        self.ai_moved = False
        self.hover_idx = None

    # Return the exact screen center of piece `slot` inside a player's reserve dock.
    # player: 1 or 2; slot: piece index 0, 1, or 2.
    def dock_slot_center(self, player, slot):
        dock = P1_DOCK if player == 1 else P2_DOCK
        return pixel_art.slot_center_in_rect(dock, slot)

    # Return the exact screen center of piece `slot` inside a player's scored goal tray.
    # player: 1 or 2; slot: piece index 0, 1, or 2.
    def tray_slot_center(self, player, slot):
        tray = P1_TRAY if player == 1 else P2_TRAY
        return pixel_art.slot_center_in_rect(tray, slot)

    # Map `(player, tile, piece)` to its screen pixel anchor for rendering tokens and VFX.
    # player: 1 or 2; tile: logical position 0..10; piece: piece index 0..2 for dock/tray slots.
    def tile_point(self, player, tile, piece=None):
        if tile == 0:
            return self.dock_slot_center(player, piece if piece is not None else 0)
        if tile == BOARD_END:
            return self.tray_slot_center(player, piece if piece is not None else 0)
        cell = lane_cell(player, tile) if tile in (1, 2, 8, 9) else shared_cell(tile)
        if cell is None:
            return self.tray_slot_center(player, piece if piece is not None else 0)
        return cell_center(*cell)

    # Trigger the 260 ms 3D dice tumble animation before committing the random roll,
    # playing the short `dice_tick` blip for the shuffle.
    # self.dice_rolling/self.dice_roll_ms: animation state flags.
    def start_roll(self):
        self.hover_idx = None
        self.dice_rolling = True
        self.dice_roll_ms = 0
        sound_fx.dice_tick()

    # Finalize a dice roll after tumbling, spawn `dice_roll` VFX, and update the turn phase.
    # player: 1 or 2 indicating who rolled; roll: sampled die outcome 1..3.
    def commit_roll(self, player):
        roll = self.state.roll_dice()
        cx, cy = self.dice_center()
        self.vfx.spawn("dice_roll", cx, cy, scale=0.55)
        sound_fx.dice_land()
        self.log.append(f"P{player} rolled {roll}")
        if player == 1:
            self.hint = self._compute_hint()
            if not self.state.get_legal_moves():
                self._enter_phase("skip_wait")
                self.log.append("P1 has no legal moves -> skipping")
            else:
                self._enter_phase("human_await_move")
        else:
            self.ai_roll_done = True
            self.phase_ms = 0
            if not self.state.get_legal_moves():
                self.do_ai_move(None)

    # Run Expectiminimax (depth=4) on the human's live position when `Hint: ON` is active.
    # move/scores/stats: candidate evaluation results returned by ExpectiminimaxAgent.
    def _compute_hint(self):
        if not self.hint_on or self.state.current_turn != 1 or not self.state.dice_roll:
            return None
        legal = self.state.get_legal_moves()
        if not legal:
            return None
        move, scores, stats = ExpectiminimaxAgent(depth=4).choose_move(self.state)
        targets = {i: self.state.p1_pieces[i] + self.state.dice_roll for i in scores}
        return {
            "scores": scores, "best": move, "targets": targets,
            "nodes": stats["nodes"], "ms": stats["time_ms"],
        }

    # Execute the AI opponent's move, record candidate evaluations for the Inspector panel,
    # and cleanly hand control back to the human (or re-enter `ai_think` on a bonus turn).
    # move_idx: fallback move index (None when skipping); best/scores/stats: AI search output.
    def do_ai_move(self, move_idx):
        agent = self.make_ai_agent()
        best, scores, stats = agent.choose_move(self.state)
        roll = self.state.dice_roll
        targets = {i: self.state.p2_pieces[i] + roll for i in scores}
        chosen = best if best is not None else move_idx
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
        self.apply_and_animate(2, chosen, roll)
        self.ai_moved = True
        if not self.over:
            if self.state.current_turn == 2:
                self._enter_phase("ai_think")
            else:
                self._enter_phase("human_await_roll")

    # Apply a player's move to `self.state`, start two-stage Shrine->Tray slide when scoring,
    # and trigger the bound pixelfx animations.
    # player: 1 or 2; idx: moved piece index 0..2 or None on skip; roll: die value 1..3.
    def apply_and_animate(self, player, idx, roll):
        pieces = self.state.p1_pieces if player == 1 else self.state.p2_pieces
        from_tile = pieces[idx] if idx is not None else -1
        self.state, ev = self.state.apply_move(idx, roll)
        self.turns += 1
        to_tile = ev["target_tile"]
        shrine_pt = cell_center(1, 5)
        if idx is not None and not self.fast:
            from_pt = self.tile_point(player, from_tile, idx)
            to_pt = self.tile_point(player, to_tile, idx)
            via_pt = shrine_pt if to_tile == BOARD_END else None
            self.slides[(player, idx)] = {"from": from_pt, "via": via_pt, "to": to_pt, "t": 0.0}
        if to_tile == BOARD_END:
            cx, cy = shrine_pt
            tray_x, tray_y = self.tray_slot_center(player, idx if idx is not None else 0)
        elif to_tile >= 0:
            cx, cy = self.tile_point(player, to_tile, idx)
            tray_x, tray_y = cx, cy
        else:
            cx, cy = WIN_W // 2, WIN_H // 2
            tray_x, tray_y = cx, cy
        if ev["captured"]:
            self.vfx.spawn("hit_explosion", cx, cy, scale=0.65)
            sound_fx.capture_sfx()
            self.floats.append({"text": "-1 FOE! CAPTURED!", "color": (234, 82, 74),
                                "x": cx, "y": cy - 26, "t": 0.0})
        if ev["bonus_turn"]:
            self.vfx.spawn("rune_glow", cx, cy, scale=0.75)
            sound_fx.bonus_sfx()
            self.bonus_count[player] += 1
            self.floats.append({"text": "+BONUS TURN!", "color": (244, 204, 88),
                                "x": cx, "y": cy - 26, "t": 0.0})
        if ev["scored"]:
            self.vfx.spawn("score_burst", cx, cy, scale=0.75)
            sound_fx.score_sfx()
            if idx is not None:
                self.vfx.spawn("score_burst", tray_x, tray_y, scale=0.55)
            self.floats.append({"text": "+1 SCORED!", "color": (96, 220, 132),
                                "x": cx, "y": cy - 26, "t": 0.0})
        if idx is not None:
            sound_fx.move_sfx()
        if self.state.is_terminal():
            self.over = True
            self.hover_idx = None
            sound_fx.win_sfx()
            self.vfx.spawn("score_burst", cx - 45, cy - 20, scale=0.75)
            self.vfx.spawn("score_burst", cx + 45, cy - 20, scale=0.75)
        if idx is not None:
            tags = []
            if ev["captured"]:
                tags.append("CAPTURED!")
            if ev["bonus_turn"]:
                tags.append("BONUS TURN!")
            if ev["scored"]:
                tags.append("SCORED!")
            suffix = f" ({', '.join(tags)})" if tags else ""
            self.log.append(f"P{player} #{idx+1} -> tile {to_tile}{suffix}")
        else:
            self.log.append(f"P{player} no legal moves -> skipped")
        self.log = self.log[-40:]

    # Instantiate the currently selected AI agent class for Player 2.
    # cls: GreedyAgent, DeterministicMinimaxAgent, or ExpectiminimaxAgent.
    def make_ai_agent(self):
        cls = AGENTS[self.ai_index][1]
        return cls() if cls is GreedyAgent else cls(depth=4)

    # Return the screen pixel center of the 3D dice cube on the lower-right console.
    # x0, y0: top-left origin of the lower-right panel.
    def dice_center(self):
        x0 = LEFT_W + 10
        y0 = BANNER_H + 344
        return (x0 + 72, y0 + 88)

    # Start the human player's dice roll animation when allowed.
    def human_roll(self):
        if not self.dice_rolling and self.phase == "human_await_roll":
            self.start_roll()

    # Commit the human player's chosen piece move and transition to bonus roll or AI turn.
    # idx: chosen legal piece index 0, 1, or 2.
    def human_move(self, idx):
        self.hover_idx = None
        self.apply_and_animate(1, idx, self.state.dice_roll)
        self.hint = None
        if not self.over:
            if self.state.current_turn == 1:
                self._enter_phase("human_await_roll")
            else:
                self._enter_phase("ai_think")

    # Advance animations, VFX, dice tumbles, floating combat text, and turn timers
    # by `dt_ms` milliseconds.
    # dt_ms: elapsed frame time in ms; dt: 0 in headless fast-forward mode, else dt_ms.
    def update(self, dt_ms):
        dt = 0 if self.fast else dt_ms
        if not self.fast:
            self.pulse += dt_ms * 0.005
        self.vfx.update(dt_ms if self.fast else dt)
        # Phase 4.8: drift-up + fade every floating combat text popup over ~900 ms
        for fl in list(self.floats):
            fl["t"] += dt_ms
            if fl["t"] >= 900:
                self.floats.remove(fl)
        if self.slides:
            for key in list(self.slides):
                s = self.slides[key]
                dur = SLIDE_MS * 1.6 if s.get("via") else SLIDE_MS
                s["t"] += dt
                if s["t"] >= dur:
                    del self.slides[key]
        if self.over:
            return
        if self.dice_rolling:
            self.dice_roll_ms += dt
            if self.dice_roll_ms >= ROLL_ANIM_MS:
                self.dice_rolling = False
                self.commit_roll(self.state.current_turn)
            return
        if self.fast:
            if self.state.current_turn == 1:
                roll = self.state.roll_dice()
                self.vfx.spawn("dice_roll", *self.dice_center(), scale=0.55)
                sound_fx.dice_land()
                self.log.append(f"P1 rolled {roll}")
                legal = self.state.get_legal_moves()
                if not legal:
                    self.apply_and_animate(1, None, roll)
                    if not self.over and self.state.current_turn == 2:
                        self._enter_phase("ai_think")
                else:
                    move, _, _ = self.human_agent.choose_move(self.state)
                    self.human_move(move)
            else:
                roll = self.state.roll_dice()
                self.vfx.spawn("dice_roll", *self.dice_center(), scale=0.55)
                self.log.append(f"P2 rolled {roll}")
                self.do_ai_move(None)
            return
        self.phase_ms += dt
        if self.phase == "ai_think":
            if not self.ai_roll_done:
                if self.phase_ms >= AI_ROLL_WAIT_MS:
                    self.start_roll()
            elif not self.ai_moved:
                if self.phase_ms >= AI_MOVE_WAIT_MS:
                    self.do_ai_move(None)
        elif self.phase == "skip_wait":
            if self.phase_ms >= HUMAN_PAUSE_MS:
                self.apply_and_animate(1, None, self.state.dice_roll)
                self.hint = None
                if not self.over:
                    if self.state.current_turn == 2:
                        self._enter_phase("ai_think")
                    else:
                        self._enter_phase("human_await_roll")

    # Compute the current pixel center `(cx, cy)` of piece `(player, idx)`, smoothly
    # passing through the Golden Shrine `(1, 5)` first whenever a piece reaches `10`!
    # player: 1 or 2; idx: piece index 0..2; f: normalized slide interpolation progress.
    def piece_pos(self, player, idx):
        key = (player, idx)
        if key in self.slides:
            s = self.slides[key]
            if s.get("via"):
                dur = SLIDE_MS * 1.6
                f = min(1.0, s["t"] / dur)
                if f < 0.55:
                    u = f / 0.55
                    x = s["from"][0] + (s["via"][0] - s["from"][0]) * u
                    y = s["from"][1] + (s["via"][1] - s["from"][1]) * u
                else:
                    u = (f - 0.55) / 0.45
                    x = s["via"][0] + (s["to"][0] - s["via"][0]) * u
                    y = s["via"][1] + (s["to"][1] - s["via"][1]) * u
                return (int(x), int(y))
            f = min(1.0, s["t"] / SLIDE_MS)
            x = s["from"][0] + (s["to"][0] - s["from"][0]) * f
            y = s["from"][1] + (s["to"][1] - s["from"][1]) * f
            return (int(x), int(y))
        tile = (self.state.p1_pieces if player == 1 else self.state.p2_pieces)[idx]
        if tile == 0:
            return self.dock_slot_center(player, idx)
        if tile == BOARD_END:
            return self.tray_slot_center(player, idx)
        cx, cy = self.tile_point(player, tile, idx)
        enemy_tiles = self.state.p2_pieces if player == 1 else self.state.p1_pieces
        if tile in enemy_tiles and tile in (3, 4, 5, 6, 7):
            cy = cy - 9 if player == 1 else cy + 9
        return (cx, cy)

    # Render one complete frame in strict back-to-front layer order before flipping display.
    # ox, oy: current screen-shake offset applied to board elements; VFX applies its own internally.
    def render(self):
        # Phase 4.8: baked midnight night-sky + city-wall bas-relief background
        self.screen.blit(self.art.bg, (0, 0))
        self.draw_stars()
        ox, oy = self.vfx.get_shake_offset()
        self.draw_braziers(ox, oy)
        self.draw_board(ox, oy)
        self.draw_target_preview(ox, oy)
        self.draw_pieces(ox, oy)
        self.draw_floats()
        self.draw_legend()
        self.draw_banner()
        self.draw_turn_banner()
        self.draw_inspector()
        self.draw_dice_log()
        self.vfx.draw(self.screen, (0, 0))
        if self.over:
            self.draw_game_over()
        pygame.display.flip()

    # Render twinkling upward-drifting background stardust motes over the night sky.
    # t: current animation time phase; y/alpha: wrapped vertical coordinate and star opacity.
    def draw_stars(self):
        t = self.pulse
        usable_h = WIN_H - BANNER_H
        for star in self.art.stars:
            y = BANNER_H + int((star["y"] - BANNER_H - t * star["spd"] * 3.0) % usable_h)
            alpha = int(38 + 42 * (1.0 + math.sin(t * 1.4 + star["ph"])) * 0.5)
            surf = pixel_art.draw_star_surface(star, alpha)
            self.screen.blit(surf, (star["x"], y))

    # Draw the four animated pixel braziers sitting in the board's empty concave
    # corners (the four grid cells that the hourglass layout leaves empty: rows 0
    # and 2, columns 2 and 3), cycling 4 flame frames + matching warm glow at ~6 fps.
    # ox, oy: screen-shake offsets; f: current integer flame frame 0..3.
    def draw_braziers(self, ox, oy):
        # The four empty concave grid cells of the hourglass board (no tile lives here)
        spots = [
            cell_center(0, 2),
            cell_center(0, 3),
            cell_center(2, 2),
            cell_center(2, 3),
        ]
        f = int(self.pulse * 3) % 4
        flame = self.art.braziers[f]
        glow = self.art.brazier_glow[f]
        for sx, sy in spots:
            x, y = sx + ox, sy + oy
            self.screen.blit(glow, (x - 64, y - 70))
            self.screen.blit(flame, (x - 22, y - 30))

    # Draw the hourglass 14-tile Babylonian board, crisp tile badges, S-curve directional
    # arrows ON TOP OF tile seams, non-overlapping docks/trays, and breathing rune halos.
    # ox, oy: integer screen-shake pixel offsets; tier: integer glow level in {1, 2, 3}.
    def draw_board(self, ox, oy):
        # Phase 4.8: ornate obsidian/dark-gold royal casing baked under the 14-tile hourglass
        casing = self.art.casing
        self.screen.blit(casing, (ox + GRID_X - 30, oy + GRID_Y - 30))
        for row in range(3):
            for col in range(6):
                if row in (0, 2) and col in (2, 3):
                    continue
                kind = TILE_KIND[(row, col)]
                rect = pygame.Rect(ox + GRID_X + col * TILE, oy + GRID_Y + row * TILE, TILE, TILE)
                self.screen.blit(self.art.tiles[kind], rect)
                label = TILE_LABEL.get((row, col))
                if label:
                    lbl_col = GOLD if ("*" in label or label == "10") else TEXT
                    txt_s = get_font(14).render(label, True, lbl_col)
                    pill = pygame.Rect(rect.x + 4, rect.y + 4, txt_s.get_width() + 6, txt_s.get_height() + 2)
                    pygame.draw.rect(self.screen, (16, 14, 24), pill, border_radius=3)
                    self.screen.blit(txt_s, (pill.x + 3, pill.y + 1))
        # Drawn AFTER tiles so every directional chevron arrow across tile seams is 100% visible!
        self.screen.blit(self.art.path_layer, (ox, oy))
        self.screen.blit(self.art.docks[1], (ox + P1_DOCK.x, oy + P1_DOCK.y))
        self.screen.blit(self.art.docks[2], (ox + P2_DOCK.x, oy + P2_DOCK.y))
        self.screen.blit(self.art.trays[1], (ox + P1_TRAY.x, oy + P1_TRAY.y))
        self.screen.blit(self.art.trays[2], (ox + P2_TRAY.x, oy + P2_TRAY.y))
        tier = 1 + (int(self.pulse * 1.5) % 3)
        glow = self.art.glow[tier]
        for r, c in ((1, 1), (0, 4), (2, 4)):
            cx, cy = cell_center(r, c)
            self.screen.blit(glow, (cx + ox - 32, cy + oy - 32))

    # Draw all six player tokens and pulsing selection rings around movable human pieces.
    # ox, oy: screen-shake offsets; legal: list of movable piece indices for Player 1.
    def draw_pieces(self, ox, oy):
        legal = (
            self.state.get_legal_moves()
            if (not self.over and self.state.current_turn == 1 and self.phase == "human_await_move")
            else []
        )
        for player in (1, 2):
            for idx in range(3):
                cx, cy = self.piece_pos(player, idx)
                cx, cy = cx + ox, cy + oy
                token = self.art.tokens[(player, idx)]
                self.screen.blit(token, (cx - 20, cy - 17))
                if player == 1 and idx in legal:
                    rad = 19 + int(3 * math.sin(self.pulse * 2.2))
                    col = GOLD if idx == self.hover_idx else HI
                    pygame.draw.circle(self.screen, col, (cx, cy - 2), rad, 2)

    # Phase 4.8: draw floating pixel combat text popups that drift up ~26px and fade
    # over ~900 ms (capture = crimson, rune = gold, finish = emerald, black outline).
    # fl: popup dict with text/color/x/y/t keys; f01: normalized popup age 0..1.
    def draw_floats(self):
        ox, oy = self.vfx.get_shake_offset()
        for fl in self.floats:
            f01 = fl["t"] / 900.0
            y = int(fl["y"] - 26 * f01) + oy
            x = int(fl["x"]) + ox
            s = get_font(15)
            txt = s.render(fl["text"], True, (10, 10, 16))
            main = s.render(fl["text"], True, fl["color"])
            off = 2
            for dx in (-off, 0, off):
                for dy in (-off, 0, off):
                    if dx or dy:
                        self.screen.blit(txt, (x - main.get_width() // 2 + dx, y + dy))
            self.screen.blit(main, (x - main.get_width() // 2, y))

    # Draw the bottom-left tactical rules & route legend strip (zero overlap with docks).
    # l1, l2: concise quick-reference strings, kept short enough to stay inside
    # LEGEND_RECT with >= 14 px right margin.
    def draw_legend(self):
        pixel_art.draw_panel(self.screen, LEGEND_RECT)
        f = get_font(13)
        l1 = "ROUTE: Start -> 1 -> 2 -> War (3..7) -> Sprint (8*->9) -> Shrine (10)"
        l2 = "RULES: 3,5,6,7 = Capture Foe  |  4* & 8* = Bonus Turn (4* = Shield)"
        self.screen.blit(f.render(l1, True, TEXT), (LEGEND_RECT.x + 12, LEGEND_RECT.y + 14))
        self.screen.blit(f.render(l2, True, GOLD), (LEGEND_RECT.x + 12, LEGEND_RECT.y + 38))

    # Draw the mandatory top banner: compact left banner text plus three right-side
    # buttons ([Sound], [AI], [New Game]) with a safe 12px gap between each.
    # hover: current mouse coordinate tuple used for button highlight feedback.
    def draw_banner(self):
        hover = pygame.mouse.get_pos() if not self.fast else (-1, -1)
        pixel_art.draw_panel(self.screen, pygame.Rect(0, 0, WIN_W, BANNER_H))
        self.screen.blit(get_font(19).render(BANNER_TEXT, True, GOLD), (14, 14))
        gap = 12
        self.btn_new = pygame.Rect(WIN_W - 12 - 140, 10, 140, 28)
        self.btn_ai = pygame.Rect(self.btn_new.x - gap - 170, 10, 170, 28)
        self.btn_sound = pygame.Rect(self.btn_ai.x - gap - 160, 10, 160, 28)
        snd_label = "Sound: ON (M)" if not sound_fx.is_muted() else "Sound: OFF (M)"
        pixel_art.draw_button(
            self.screen, self.btn_sound, snd_label,
            (42, 92, 56) if not sound_fx.is_muted() else (48, 62, 96),
            self.btn_sound.collidepoint(hover)
        )
        pixel_art.draw_button(
            self.screen, self.btn_ai, f"AI: {AGENTS[self.ai_index][0]}",
            BTN_BLUE, self.btn_ai.collidepoint(hover)
        )
        pixel_art.draw_button(
            self.screen, self.btn_new, "New Game (R)",
            BTN_RED, self.btn_new.collidepoint(hover)
        )

    # Draw the centered turn-status badge cleanly at the top of the left board area (y=56..84).
    # text, col: status prompt string and its corresponding highlight RGB color.
    def draw_turn_banner(self):
        if self.over:
            w = self.state.get_winner()
            text = "VICTORY! PLAYER 1 WINS!" if w == 1 else "DEFEAT! AI PLAYER 2 WINS!"
            col = GOLD
        elif self.state.current_turn == 1:
            if self.dice_rolling:
                text, col = "ROLLING RUNES...", P1_FILL
            elif self.phase == "human_await_roll":
                text, col = "YOUR TURN  -  PRESS [SPACE] OR CLICK ROLL", P1_FILL
            elif self.phase == "human_await_move":
                text, col = f"ROLLED [{self.state.dice_roll}]  -  CLICK A GLOWING PIECE OR TARGET TILE", HI
            else:
                text, col = f"ROLLED [{self.state.dice_roll}]  -  NO LEGAL MOVES, SKIPPING...", TEXT_DIM
        else:
            text, col = "AI OPPONENT IS EVALUATING CONSEQUENCES...", P2_FILL
        badge = pygame.Rect(GRID_X, BANNER_H + 8, 6 * TILE, 28)
        pygame.draw.rect(self.screen, (28, 26, 44), badge, border_radius=5)
        pygame.draw.rect(self.screen, col, badge, 2, border_radius=5)
        surf = get_font(15).render(text, True, col)
        self.screen.blit(surf, (badge.centerx - surf.get_width() // 2, badge.centery - surf.get_height() // 2))

    # Draw the right-hand AI Decision Inspector panel showing candidate move evaluations
    # and the optional live Expectiminimax human advisor (`Advisor Hint: ON`).
    # x0, pw, panel: panel geometry; d: last AI decision dictionary; h: human hint dictionary.
    def draw_inspector(self):
        x0 = LEFT_W + 10
        pw = WIN_W - x0 - 10
        panel = pygame.Rect(x0, BANNER_H + 10, pw, 322)
        pixel_art.draw_panel(self.screen, panel)
        pixel_art.draw_title(self.screen, x0 + 14, BANNER_H + 18, pw - 28, "AI DECISION INSPECTOR", GOLD)
        y = BANNER_H + 48
        if self.hint:
            h = self.hint
            hdr = f"[ADVISOR: Expectiminimax d=4] ({h['nodes']} nd, {h['ms']:.1f}ms)"
            self.screen.blit(get_font(14).render(hdr, True, P1_FILL), (x0 + 14, y))
            y += 18
            for idx in range(3):
                if idx not in h["scores"]:
                    continue
                is_best = (idx == h["best"])
                tag = " [RECOMMENDED]" if is_best else ""
                line = f"  Piece #{idx+1} -> Tile {h['targets'][idx]}: {h['scores'][idx]:+6.1f}{tag}"
                self.screen.blit(get_font(14).render(line, True, HI if is_best else TEXT), (x0 + 14, y))
                y += 17
            y += 6
        d = self.last_decision
        if d:
            self.screen.blit(
                get_font(15).render(f"AI ({d['alg']}): {d['nodes']} nodes | {d['ms']:.2f} ms", True, TEXT),
                (x0 + 14, y)
            )
            y += 20
            val = max(-1000.0, min(1000.0, float(d["eval_p1"])))
            bar = pygame.Rect(x0 + 14, y, pw - 28, 12)
            mid = bar.centerx
            pygame.draw.rect(self.screen, (18, 16, 28), bar, border_radius=3)
            pygame.draw.rect(self.screen, (82, 76, 110), bar, 1, border_radius=3)
            w = int(abs(val) / 1000.0 * (bar.width // 2))
            if val >= 0:
                pygame.draw.rect(self.screen, P1_FILL, (mid, bar.y + 1, w, bar.height - 2))
            else:
                pygame.draw.rect(self.screen, P2_FILL, (mid - w, bar.y + 1, w, bar.height - 2))
            pygame.draw.line(self.screen, GOLD, (mid, bar.y - 2), (mid, bar.bottom + 2), 2)
            lead_txt = f"Board Eval: {'P1' if val >= 0 else 'P2'} ({val:+.1f})"
            self.screen.blit(get_font(13).render(lead_txt, True, TEXT_DIM), (x0 + 14, y + 15))
            y += 34
            self.screen.blit(get_font(14).render("Evaluated AI Candidate Moves:", True, GOLD), (x0 + 14, y))
            y += 18
            if d["scores"]:
                for idx in range(3):
                    if idx not in d["scores"]:
                        continue
                    score = d["scores"][idx]
                    is_best = (idx == d["best"])
                    mark = " [BEST]" if is_best else ""
                    line = f"Piece #{idx+1} -> Tile {d['targets'].get(idx, '?')}  {score:+7.1f}{mark}"
                    self.screen.blit(get_font(14).render(line, True, HI if is_best else TEXT), (x0 + 14, y))
                    bw = max(4, int(72 * max(0.0, min(1.0, (score + 200.0) / 400.0))))
                    pygame.draw.rect(
                        self.screen, GREEN if score >= 0 else RED,
                        (panel.right - 14 - bw, y + 4, bw, 6), border_radius=2
                    )
                    y += 19
            else:
                self.screen.blit(get_font(14).render("No legal moves on last AI roll.", True, TEXT_DIM), (x0 + 14, y))
        else:
            self.screen.blit(
                get_font(15).render("Roll & move to watch AI evaluate all paths...", True, TEXT_DIM),
                (x0 + 14, y)
            )
        self.btn_hint = pygame.Rect(x0 + 14, panel.bottom - 34, 168, 24)
        hover = pygame.mouse.get_pos() if not self.fast else (-1, -1)
        pixel_art.draw_button(
            self.screen, self.btn_hint, f"Advisor Hint: {'ON' if self.hint_on else 'OFF'}",
            BTN_BLUE, self.btn_hint.collidepoint(hover)
        )

    # Draw the lower-right 3D dice console, ROLL button, probability distribution, and battle log.
    # x0, y0, panel: console panel coordinates; face/bounce: animated 3D die state.
    def draw_dice_log(self):
        x0 = LEFT_W + 10
        y0 = BANNER_H + 342
        panel = pygame.Rect(x0, y0, WIN_W - x0 - 10, WIN_H - y0 - 10)
        pixel_art.draw_panel(self.screen, panel)
        pixel_art.draw_title(self.screen, x0 + 14, y0 + 10, panel.width - 28, "DICE & BATTLE LOG", GOLD)
        dx, dy = self.dice_center()
        can_roll = (
            not self.over and not self.fast and not self.dice_rolling
            and self.state.current_turn == 1 and self.phase == "human_await_roll"
        )
        if self.dice_rolling:
            face = 1 + (int(self.dice_roll_ms // 45) % 3)
            bounce = int(6 * abs(math.sin(self.dice_roll_ms / float(ROLL_ANIM_MS) * math.pi)))
        else:
            face = self.state.dice_roll if self.state.dice_roll in (1, 2, 3) else 0
            bounce = 0
        self.screen.blit(self.art.dice[face], (dx - 36, dy - 36 - bounce))
        self.btn_roll = pygame.Rect(dx - 58, dy + 38, 116, 28)
        hover = pygame.mouse.get_pos() if not self.fast else (-1, -1)
        pixel_art.draw_button(
            self.screen, self.btn_roll, "ROLL (Space)", (42, 92, 56),
            self.btn_roll.collidepoint(hover), can_roll
        )
        self.screen.blit(get_font(12).render("1:25%  2:50%  3:25%", True, TEXT_DIM), (dx - 56, dy + 72))
        lx = x0 + 142
        ly = y0 + 42
        self.screen.blit(get_font(13).render("Recent Battle Events:", True, GOLD), (lx, ly))
        ly += 18
        for line in self.log[-7:]:
            col = HI if ("CAPTURED" in line or "BONUS" in line or "SCORED" in line) else TEXT
            # Phase 4.8: never truncate mid-word - drop to the previous space if needed
            txt = line
            if get_font(13).size(txt)[0] > 176:
                cut = txt[:33]
                sp = cut.rfind(" ")
                txt = cut if sp < 14 else cut[:sp] + ".."
            self.screen.blit(get_font(13).render(txt, True, col), (lx, ly))
            ly += 18

    # Draw the modal MATCH SUMMARY overlay when all 3 pieces of either player score:
    # winner, total turns, P1 vs P2 final score, captures, and bonus turns earned.
    # winner: 1 (human) or 2 (AI); box: centered modal panel Rect; p1_cap/p2_cap:
    # capture tallies derived from the battle log for the summary grid.
    def draw_game_over(self):
        p1_cap = sum(1 for l in self.log if l.startswith("P1") and "CAPTURED" in l)
        p2_cap = sum(1 for l in self.log if l.startswith("P2") and "CAPTURED" in l)
        dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 185))
        self.screen.blit(dim, (0, 0))
        box = pygame.Rect(WIN_W // 2 - 250, WIN_H // 2 - 160, 500, 320)
        pixel_art.draw_panel(self.screen, box)
        pixel_art.draw_title(self.screen, box.x + 14, box.y + 10, box.width - 28, "MATCH SUMMARY", GOLD)
        winner = self.state.get_winner()
        who = "PLAYER 1 (HUMAN) WINS!" if winner == 1 else "PLAYER 2 (AI) WINS!"
        col = P1_FILL if winner == 1 else P2_FILL
        title = get_font(26).render(who, True, col)
        self.screen.blit(title, (box.centerx - title.get_width() // 2, box.y + 44))
        f = get_font(16)
        # Phase 4.8 revision: fixed three-column table - labels left-aligned in their
        # own column, P1/P2 numbers each centered under their header (no more
        # combined value string drifting onto top of the label text).
        label_x = box.x + 44
        col1 = box.centerx - 70
        col2 = box.centerx + 80
        y = box.y + 100
        h1 = f.render("PLAYER 1 (HUMAN)", True, P1_FILL)
        h2 = f.render("PLAYER 2 (AI)", True, P2_FILL)
        self.screen.blit(h1, (col1 - h1.get_width() // 2, y - 4))
        self.screen.blit(h2, (col2 - h2.get_width() // 2, y - 4))
        y += 30
        rows = [
            ("FINAL SCORE", f"{3 if winner == 1 else 0}", f"{0 if winner == 1 else 3}"),
            ("CAPTURES", str(p1_cap), str(p2_cap)),
            ("BONUS TURNS", str(self.bonus_count[1]), str(self.bonus_count[2])),
        ]
        for label, v1, v2 in rows:
            self.screen.blit(get_font(13).render(label, True, TEXT_DIM), (label_x, y))
            s1 = f.render(v1, True, P1_FILL)
            s2 = f.render(v2, True, P2_FILL)
            self.screen.blit(s1, (col1 - s1.get_width() // 2, y - 4))
            self.screen.blit(s2, (col2 - s2.get_width() // 2, y - 4))
            y += 30
        turns_s = get_font(14).render(f"Completed in {self.turns} total turns", True, TEXT)
        self.screen.blit(turns_s, (box.centerx - turns_s.get_width() // 2, y + 6))
        self.btn_again = pygame.Rect(box.centerx - 100, box.bottom - 52, 200, 40)
        hover = pygame.mouse.get_pos() if not self.fast else (-1, -1)
        pixel_art.draw_button(
            self.screen, self.btn_again, "Play Again (R)", (42, 92, 56),
            self.btn_again.collidepoint(hover)
        )

    # Resolve which legal human piece corresponds to a given mouse `(x, y)` position,
    # matching either the piece token itself OR its destination board cell / goal tray!
    # pos: `(x, y)` screen coordinate; legal: list of currently movable P1 piece indices.
    def _pick_human_piece_at(self, pos):
        if self.over or self.state.current_turn != 1 or self.phase != "human_await_move" or self.dice_rolling:
            return None
        legal = self.state.get_legal_moves()
        for idx in legal:
            cx, cy = self.piece_pos(1, idx)
            if pygame.Rect(cx - 24, cy - 24, 48, 48).collidepoint(pos):
                return idx
        for idx in legal:
            cell = self.target_cell_of(1, idx)
            if cell is not None and cell_rect(*cell).collidepoint(pos):
                return idx
            if self.state.p1_pieces[idx] + self.state.dice_roll == BOARD_END and P1_TRAY.collidepoint(pos):
                return idx
        return None

    # Handle left mouse clicks on UI buttons, movable pieces, or highlighted destination tiles.
    # pos: `(x, y)` click coordinate in window pixels.
    def on_click(self, pos):
        if self.over:
            if hasattr(self, "btn_again") and self.btn_again.collidepoint(pos):
                self.reset()
            return
        if hasattr(self, "btn_ai") and self.btn_ai.collidepoint(pos):
            self.ai_index = (self.ai_index + 1) % len(AGENTS)
            self.log.append(f"Switched AI to {AGENTS[self.ai_index][0]}")
            return
        if hasattr(self, "btn_sound") and self.btn_sound.collidepoint(pos):
            m = sound_fx.toggle_mute()
            self.log.append("Audio muted" if m else "Audio on")
            return
        if hasattr(self, "btn_new") and self.btn_new.collidepoint(pos):
            self.reset()
            return
        if hasattr(self, "btn_hint") and self.btn_hint.collidepoint(pos):
            self.hint_on = not self.hint_on
            self.hint = self._compute_hint()
            return
        if hasattr(self, "btn_roll") and self.btn_roll.collidepoint(pos):
            if self.state.current_turn == 1 and self.phase == "human_await_roll" and not self.dice_rolling:
                self.human_roll()
            return
        picked = self._pick_human_piece_at(pos)
        if picked is not None:
            self.human_move(picked)

    # Update `self.hover_idx` when the cursor hovers over either a movable piece or its target tile.
    # pos: `(x, y)` mouse cursor coordinate.
    def on_hover(self, pos):
        self.hover_idx = self._pick_human_piece_at(pos)

    # Return the `(row, col)` destination cell on the 3x6 grid for piece `(player, idx)`,
    # safely returning `None` whenever `idx` is invalid or `target > BOARD_END`!
    # player: 1 or 2; idx: piece index 0..2; target: destination logical tile index.
    def target_cell_of(self, player, idx):
        if idx is None or not (0 <= idx < 3):
            return None
        pieces = self.state.p1_pieces if player == 1 else self.state.p2_pieces
        target = pieces[idx] + self.state.dice_roll
        if target > BOARD_END or target <= 0:
            return None
        if target in (1, 2, 8, 9):
            return lane_cell(player, target)
        return shared_cell(target)

    # Highlight legal destination tiles during human move selection, emphasizing the hovered move.
    # ox, oy: screen-shake offsets; legal: currently movable P1 piece indices.
    def draw_target_preview(self, ox, oy):
        if self.over or self.state.current_turn != 1 or self.phase != "human_await_move":
            return
        legal = self.state.get_legal_moves()
        if not legal:
            return
        shown = [self.hover_idx] if self.hover_idx in legal else legal
        for idx in shown:
            if idx not in legal:
                continue
            target = self.state.p1_pieces[idx] + self.state.dice_roll
            cell = self.target_cell_of(1, idx)
            if cell is None:
                continue
            r, c = cell
            rect = pygame.Rect(ox + GRID_X + c * TILE, oy + GRID_Y + r * TILE, TILE, TILE)
            enemy = self.state.p2_pieces
            capture = (WAR_START <= target <= WAR_END and target != 4 and target in enemy)
            rune = (target in SAFE_TILES)
            color = RED if capture else (GOLD if rune else GREEN)
            is_focus = (idx == self.hover_idx)
            overlay = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            overlay.fill((*color, 72 if is_focus else 34))
            self.screen.blit(overlay, rect)
            pygame.draw.rect(self.screen, color, rect, 3 if is_focus else 2, border_radius=6)
            if is_focus:
                tag = "CAPTURE!" if capture else ("BONUS*" if rune else ("SCORE!" if target == BOARD_END else f"#{idx+1} GO"))
                f = get_font(14)
                tw, _ = f.size(tag)
                self.screen.blit(f.render(tag, True, color), (rect.centerx - tw // 2, rect.bottom - 18))

    # Run the interactive 60 FPS window event loop for human play.
    # dt: frame delta milliseconds returned by `self.clock.tick(FPS)`.
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
                    elif event.key == pygame.K_m:
                        m = sound_fx.toggle_mute()
                        self.log.append("Audio muted" if m else "Audio on")
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

    # Execute comprehensive automated QA covering:
    # (1) real-time `fast=False` state-machine progression & scoring edge case (`KeyError: 12` guard),
    # (2) human UI interactions (Advisor Hint, hover, target-cell click, AI switch),
    # (3) mid-game snapshot saving `gameplay_preview.png` with all four pixelfx effects,
    # floating combat text, animated braziers, and the MATCH SUMMARY overlay active,
    # (4) Phase 4.8 procedural audio silent-degradation + floating text lifecycle checks.
    def self_test(self):
        # Part 1: Real-time (fast=False) state-machine + exact scoring hover regression test!
        self.fast = False
        self.reset()
        # Explicitly reproduce the old KeyError: 12 scenario (piece on 8 rolls 2 -> scores to 10 while hovered)
        self.state = GameState(p1_pieces=[8, 0, 0], p2_pieces=[0, 0, 0], current_turn=1, dice_roll=2)
        self._enter_phase("human_await_move")
        self.hover_idx = 0
        self.render()
        self.human_move(0)
        self.state.current_turn = 1
        self.state.dice_roll = 2
        self._enter_phase("human_await_move")
        self.hover_idx = 0   # Even if stale hover_idx=0 were forced, must NOT raise KeyError: 12!
        self.render()

        self.reset()
        self.human_roll()
        for _ in range(10):
            self.update(45)
            self.render()
        assert self.pulse > 0.0, "real-time pulse must advance without float indexing errors"
        if self.phase == "human_await_move":
            self.human_move(self.state.get_legal_moves()[0])
        if self.state.current_turn == 1:
            self.state.current_turn = 2
            self._enter_phase("ai_think")
        ticks = 0
        while self.phase == "ai_think" and not self.over and ticks < 120:
            self.update(50)
            self.render()
            ticks += 1
        assert self.over or self.phase == "human_await_roll", "AI turn must hand back to human"
        print("[self-test] Part 1 passed: scoring hover guard + real-time human/AI cycle verified!")

        # Part 2: Human UI click/hover/hint regression test
        self.reset()
        self.fast = False
        self.state = GameState(p1_pieces=[0, 1, 2], p2_pieces=[3, 0, 0], current_turn=1, dice_roll=2)
        self._enter_phase("human_await_move")
        self.render()
        self.on_click(self.btn_hint.center)
        assert self.hint_on and self.hint is not None, "Advisor Hint button must compute live scores"
        legal = self.state.get_legal_moves()
        tr, tc = self.target_cell_of(1, legal[0])
        target_px = cell_center(tr, tc)
        self.on_hover(target_px)
        assert self.hover_idx is not None, "Hovering over destination tile must highlight move"
        self.render()
        self.on_click(target_px)
        assert self.state.p1_pieces != [0, 1, 2], "Clicking destination tile must move piece"
        print("[self-test] Part 2 passed: Advisor Hint, hover preview, and target-tile click verified!")

        # Part 3: Fast-forward 16 turns and save gameplay_preview.png with all 4 VFX +
        # floating combat text popups + animated braziers + match summary active
        self.fast = True
        self.reset()
        self.hint_on = True
        steps = 0
        while steps < 16 and not self.over:
            self.update(16)
            self.render()
            steps += 1
        self.fast = False
        self.pulse = 2.4
        c3, c4, c10 = cell_center(1, 0), cell_center(1, 1), cell_center(1, 5)
        self.vfx.spawn("dice_roll", *self.dice_center(), scale=0.55)
        self.vfx.spawn("hit_explosion", c3[0], c3[1], scale=0.65)
        self.vfx.spawn("rune_glow", c4[0], c4[1], scale=0.75)
        self.vfx.spawn("score_burst", c10[0], c10[1], scale=0.75)
        for _ in range(6):
            self.vfx.update(33)
        if self.rich_decision:
            self.last_decision = self.rich_decision
        # Phase 4.8: showcase the three floating combat text styles in the snapshot
        self.floats = [
            {"text": "-1 FOE! CAPTURED!", "color": (234, 82, 74), "x": c3[0], "y": c3[1] - 26, "t": 300.0},
            {"text": "+BONUS TURN!", "color": (244, 204, 88), "x": c4[0], "y": c4[1] - 26, "t": 150.0},
            {"text": "+1 SCORED!", "color": (96, 220, 132), "x": c10[0], "y": c10[1] - 26, "t": 450.0},
        ]
        self.render()
        # Phase 4.8: also snapshot the MATCH SUMMARY overlay in the same preview
        self.state = GameState(p1_pieces=[10, 10, 10], p2_pieces=[0, 0, 0],
                               current_turn=2, dice_roll=0)
        self.over = True
        self.floats = []
        self.bonus_count = {1: 3, 2: 1}
        self.log.append("P1 #3 -> tile 10 (SCORED!)")
        self.log.append("P1 #2 -> tile 10 (CAPTURED!)")
        self.render()
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gameplay_preview.png")
        pygame.image.save(self.screen, out)
        assert os.path.isfile(out), "gameplay_preview.png was not written"
        print(f"[self-test] Part 3 passed: saved preview to {out}")

        # Part 4: Phase 4.8 regression - procedural audio must silently no-op under
        # SDL_VIDEODRIVER=dummy (or when no device exists) and every floating combat
        # text popup must advance and expire without raising.
        sound_fx.init_audio()
        sound_fx.start_bgm()
        for name in ("dice_tick", "dice_land", "move", "capture", "bonus", "score", "win"):
            sound_fx.play(name)
        m1 = sound_fx.toggle_mute()
        assert m1 is True
        m2 = sound_fx.toggle_mute()
        assert m2 is False
        sound_fx.start_bgm()
        self.floats = [{"text": "+BONUS TURN!", "color": (244, 204, 88),
                        "x": 300, "y": 300, "t": 0.0}]
        for _ in range(70):
            self.update(16)
            self.render()
        assert self.floats == [], "floating combat text must expire after ~900 ms"
        print("[self-test] Part 4 passed: audio silent-degradation + floating text lifecycle verified!")


AGENTS = [
    ("Expectiminimax", ExpectiminimaxAgent),
    ("Minimax", DeterministicMinimaxAgent),
    ("Greedy", GreedyAgent),
]


if __name__ == "__main__":
    random.seed(2026)
    is_self_test = "--self-test" in sys.argv
    if is_self_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    app = Game(fast=is_self_test)
    if is_self_test:
        app.self_test()
        pygame.quit()
    else:
        app.run()
