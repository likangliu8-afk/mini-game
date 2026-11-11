# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 2: heuristic evaluation + Greedy / DeterministicMinimax / Expectiminimax AI agents.
# Pure Python; every search value is computed from the P1 perspective so a single
# transposition table can be shared across both players' subtrees.

import os
import sys
import time

# Import from the same directory when run directly, or from the parent package layout when
# imported by evaluate_ai.py which is launched as "python pixel_dice_ur/evaluate_ai.py"
try:
    from game_state import BOARD_END, DICE_PROBS, GameState
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from game_state import BOARD_END, DICE_PROBS, GameState

# ---- Heuristic feature weights (module constants, cited in the course report) ----
WIN_SCORE = 1000.0        # terminal value: a finished game dwarfs every positional term
FINISH_WEIGHT = 120.0     # Set FINISH_WEIGHT to 120.0 so finishing a piece always outweighs sitting on tile 4
PROGRESS_WEIGHT = 6.0     # each non-finished piece earns pos * PROGRESS_WEIGHT
SHIELD_BONUS = 18.0       # extra points for holding the central shield rune tile 4
DANGER_PENALTY = 14.0     # exposure penalty when an enemy piece can capture this piece
BONUS_TURN_REWARD = 4.0   # small GreedyAgent nudge for earning a bonus turn; kept below
                          # PROGRESS_WEIGHT * 3 = 18.0 so real board progress always dominates


# Compute the raw positional score of one side's 3 pieces.
# pieces: this side's piece position list; enemy: the opponent's position list, used
# to measure how exposed each piece is to an enemy roll from 1..3 tiles behind.
def _side_score(pieces, enemy):
    total = 0.0
    for pos in pieces:
        if pos == BOARD_END:
            total += FINISH_WEIGHT
            continue
        total += pos * PROGRESS_WEIGHT
        if pos == 4:
            total += SHIELD_BONUS
        # exposure tiles: war zone 3..7 minus the shield rune tile 4, i.e. 3, 5, 6, 7
        if pos in (3, 5, 6, 7):
            for ep in enemy:
                dist = pos - ep
                # an enemy piece sitting dist tiles behind can roll exactly dist to capture this one
                if 1 <= dist <= 3:
                    total -= DANGER_PENALTY * DICE_PROBS[dist]   # weighted by the roll probability of dist
    return total


# Static heuristic evaluation from ai_player's perspective: positive means ai_player
# is ahead, negative means the opponent is ahead; ±WIN_SCORE on terminal states.
# state: the GameState to evaluate; ai_player: 1 or 2, the viewpoint player.
def evaluate_state(state, ai_player=2):
    winner = state.get_winner()
    if winner:
        return WIN_SCORE if winner == ai_player else -WIN_SCORE
    p1 = _side_score(state.p1_pieces, state.p2_pieces)
    p2 = _side_score(state.p2_pieces, state.p1_pieces)
    diff = p1 - p2
    return diff if ai_player == 1 else -diff


class GreedyAgent:
    # Single-step AI: expand only the current legal moves and score each result statically.

    # Pick the best piece for the current player.
    # state: a GameState whose dice_roll is already known (1/2/3) and whose current_turn
    # is the player this call decides for; ai_player/local legal: derived below from state.
    def choose_move(self, state):
        t0 = time.perf_counter()
        ai_player = state.current_turn   # the player this agent acts for in this call
        legal = state.get_legal_moves()
        if not legal:
            return None, {}, {"nodes": 0, "time_ms": (time.perf_counter() - t0) * 1000.0}
        best_move, best_score = None, float("-inf")
        move_scores = {}
        for idx in legal:
            next_state, ev = state.apply_move(idx, state.dice_roll)
            score = evaluate_state(next_state, ai_player)
            if ev["bonus_turn"]:
                score += BONUS_TURN_REWARD   # tiny nudge: the static eval cannot see the extra move yet
            move_scores[idx] = score
            if score > best_score:
                best_score, best_move = score, idx
        nodes = len(legal)                  # one static leaf evaluated per legal move
        stats = {"nodes": nodes, "time_ms": (time.perf_counter() - t0) * 1000.0}
        return best_move, move_scores, stats


class DeterministicMinimaxAgent:
    # Control-group AI: classic alpha-beta minimax that ignores dice randomness by
    # assuming every future roll equals the mean value ASSUMED_ROLL = 2.

    ASSUMED_ROLL = 2   # fixed future die value; the mean of the 1/2/3 DICE_PROBS distribution

    # Prepare the agent. depth: number of decision plies searched under the current move.
    def __init__(self, depth=4):
        self.depth = depth
        self._nodes = 0   # decision nodes expanded during the current choose_move call

    # Root entry: expand every legal move for the known dice_roll, search each with
    # alpha-beta, and return the best move plus per-move scores and search stats.
    # state: a GameState with dice_roll already rolled (1/2/3).
    def choose_move(self, state):
        t0 = time.perf_counter()
        self._nodes = 0
        ai_player = state.current_turn
        legal = state.get_legal_moves()
        if not legal:
            return None, {}, {"nodes": 0, "time_ms": (time.perf_counter() - t0) * 1000.0}
        best_move, best_score = None, float("-inf")
        move_scores = {}
        for idx in legal:
            next_state, _ = state.apply_move(idx, state.dice_roll)
            v = self._search(next_state, self.ASSUMED_ROLL, self.depth - 1,
                             float("-inf"), float("inf"))
            score = v if ai_player == 1 else -v   # search values are P1-perspective
            move_scores[idx] = score
            if score > best_score:
                best_score, best_move = score, idx
        stats = {"nodes": self._nodes, "time_ms": (time.perf_counter() - t0) * 1000.0}
        return best_move, move_scores, stats

    # Alpha-beta minimax on a decision node with a known die value.
    # state: position to analyse; roll: the die value the mover will use; d: plies left
    # (0 -> static eval); alpha/beta: P1-perspective bound window; self._nodes counts
    # expanded decision nodes for the stats dict.
    def _search(self, state, roll, d, alpha, beta):
        winner = state.get_winner()
        if winner:
            return WIN_SCORE if winner == 1 else -WIN_SCORE
        if d <= 0:
            return evaluate_state(state, 1)   # P1 perspective so both players share one value space
        self._nodes += 1
        legal = state.get_legal_moves(roll)
        if not legal:
            next_state, _ = state.apply_move(None, roll)   # skip turn, still costs one ply
            return self._search(next_state, roll, d - 1, alpha, beta)
        # Bonus turns are handled naturally: max/min comes from state.current_turn,
        # never from mechanically alternating, so a player on a rune tile keeps the same role
        if state.current_turn == 1:
            v = float("-inf")
            for idx in legal:
                ns, _ = state.apply_move(idx, roll)
                v = max(v, self._search(ns, self.ASSUMED_ROLL, d - 1, alpha, beta))
                alpha = max(alpha, v)
                if alpha >= beta:
                    break
            return v
        v = float("inf")
        for idx in legal:
            ns, _ = state.apply_move(idx, roll)
            v = min(v, self._search(ns, self.ASSUMED_ROLL, d - 1, alpha, beta))
            beta = min(beta, v)
            if alpha >= beta:
                break
        return v


class ExpectiminimaxAgent:
    # Core AI: full chance-node search. Decision nodes branch over legal moves and
    # chance nodes branch over DICE_PROBS, accumulating prob * value. A per-move
    # transposition table keyed on (p1, p2, current_turn, [roll], depth) keeps the
    # depth=4 single-step decision comfortably under 50ms.

    # Prepare the agent. depth: decision plies searched under the current move.
    def __init__(self, depth=4):
        self.depth = depth
        self._nodes = 0   # chance + decision nodes expanded during the current call
        self._tt = {}     # transposition table, cleared at the start of every choose_move

    # Root entry: for the already-known dice_roll, expand every legal move into a
    # chance node, and return the best move with per-move scores and search stats.
    # state: a GameState with dice_roll already rolled (1/2/3).
    def choose_move(self, state):
        t0 = time.perf_counter()
        self._nodes = 0
        self._tt = {}     # a fresh table per move: depth is relative, so entries must not leak between calls
        ai_player = state.current_turn
        legal = state.get_legal_moves()
        if not legal:
            return None, {}, {"nodes": 0, "time_ms": (time.perf_counter() - t0) * 1000.0}
        best_move, best_score = None, float("-inf")
        move_scores = {}
        for idx in legal:
            next_state, _ = state.apply_move(idx, state.dice_roll)
            v = self._chance(next_state, self.depth - 1)   # P1-perspective value
            score = v if ai_player == 1 else -v
            move_scores[idx] = score
            if score > best_score:
                best_score, best_move = score, idx
        stats = {"nodes": self._nodes, "time_ms": (time.perf_counter() - t0) * 1000.0}
        return best_move, move_scores, stats

    # Expectation over the chance node: average the decision values weighted by
    # DICE_PROBS. state: position just before the die is rolled (state.current_turn
    # is the roller); d: decision plies remaining; a transposition-table hit
    # returns the cached P1-perspective value immediately.
    def _chance(self, state, d):
        winner = state.get_winner()
        if winner:
            return WIN_SCORE if winner == 1 else -WIN_SCORE
        if d <= 0:
            return evaluate_state(state, 1)
        # chance value is independent of which roll led here, so roll is not in the key
        key = (tuple(state.p1_pieces), tuple(state.p2_pieces), state.current_turn, d)
        hit = self._tt.get(key)
        if hit is not None:
            return hit
        self._nodes += 1
        total = 0.0
        for roll, prob in DICE_PROBS.items():
            total += prob * self._decision(state, roll, d)
        self._tt[key] = total
        return total

    # Decision node with a known die value: P1 takes the max over legal moves, P2 the
    # min; with no legal move the turn is skipped via apply_move(None, roll).
    # state: position to move; roll: the concrete die value; d: plies remaining;
    # the result is stored in self._tt under (p1, p2, current_turn, roll, d).
    def _decision(self, state, roll, d):
        winner = state.get_winner()
        if winner:
            return WIN_SCORE if winner == 1 else -WIN_SCORE
        if d <= 0:
            return evaluate_state(state, 1)
        key = (tuple(state.p1_pieces), tuple(state.p2_pieces), state.current_turn, roll, d)
        hit = self._tt.get(key)
        if hit is not None:
            return hit
        self._nodes += 1
        legal = state.get_legal_moves(roll)
        if not legal:
            next_state, _ = state.apply_move(None, roll)
            v = self._chance(next_state, d - 1)
        elif state.current_turn == 1:
            v = float("-inf")
            for idx in legal:
                ns, _ = state.apply_move(idx, roll)
                v = max(v, self._chance(ns, d - 1))
        else:
            v = float("inf")
            for idx in legal:
                ns, _ = state.apply_move(idx, roll)
                v = min(v, self._chance(ns, d - 1))
        self._tt[key] = v
        return v


if __name__ == "__main__":
    # quick smoke test: each agent must return a legal move with per-move scores and stats
    import random

    for Agent in (GreedyAgent, lambda: DeterministicMinimaxAgent(depth=4),
                  lambda: ExpectiminimaxAgent(depth=4)):
        random.seed(7)
        state = GameState()
        state.p1_pieces = [2, 0, 0]
        state.p2_pieces = [4, 1, 0]
        state.current_turn = 2
        state.dice_roll = 3
        agent = Agent()
        move, scores, stats = agent.choose_move(state)
        legal = state.get_legal_moves()
        assert (move is None and not legal) or move in legal, f"illegal move {move}"
        assert set(scores) == set(legal), f"move_scores must cover every legal move: {scores} vs {legal}"
        assert stats["nodes"] >= 0 and stats["time_ms"] >= 0
        print(f"{Agent.__name__ if hasattr(Agent, '__name__') and Agent.__name__ != 'lambda' else 'agent'}: "
              f"move={move} scores={ {k: round(v, 2) for k, v in scores.items()} } "
              f"nodes={stats['nodes']} time_ms={stats['time_ms']:.2f}")

    # evaluation sanity: a clearly better position scores higher from the owner's view
    good = GameState(p1_pieces=[8, 4, 2], p2_pieces=[0, 1, 0])
    bad = GameState(p1_pieces=[0, 0, 0], p2_pieces=[8, 4, 2])
    assert evaluate_state(good, 1) > 0 and evaluate_state(bad, 1) < 0
    assert evaluate_state(good, 2) < 0 and evaluate_state(bad, 2) > 0
    terminal = GameState(p1_pieces=[10, 10, 10], p2_pieces=[0, 3, 8])
    assert evaluate_state(terminal, 1) == WIN_SCORE and evaluate_state(terminal, 2) == -WIN_SCORE
    print("[smoke test] all AI agent checks passed")
