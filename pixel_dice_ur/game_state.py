# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 1: core board math model, state cloning, legal move generation and win/loss detection.
# Pure Python with no heavy external dependencies, designed for high-frequency
# calls from the Phase 2 AI search tree.

import random

# ---- Project-wide fixed constants (do not rename) ----
BOARD_END = 10                 # finishing tile: a piece must land exactly on 10 to score
WAR_START = 3                  # start of the war zone (capture range 3..7)
WAR_END = 7                    # end of the war zone
SAFE_TILES = (4, 8)            # rune tiles: landing here grants a bonus turn
DICE_PROBS = {1: 0.25, 2: 0.50, 3: 0.25}   # die value probabilities (equivalent to two coins + base 1)


# Full game state of one Pixel Dice Ur match: both sides' piece positions, the
# current turn owner and the latest die roll. Every method clones or mutates this
# single source of truth; the UI and the AI engines never invent their own state.
class GameState:

    # Initialize one game. p1_pieces / p2_pieces hold the 3 piece positions for each
    # player (default [0, 0, 0] when None, i.e. all pieces start at the origin);
    # current_turn is 1 or 2, the player to move; dice_roll is the current die value
    # (0 means the die has not been rolled yet).
    def __init__(self, p1_pieces=None, p2_pieces=None, current_turn=1, dice_roll=0):
        self.p1_pieces = p1_pieces if p1_pieces is not None else [0, 0, 0]
        self.p2_pieces = p2_pieces if p2_pieces is not None else [0, 0, 0]
        self.current_turn = current_turn
        self.dice_roll = dice_roll

    # Clone the current state and return a new GameState instance.
    # Uses list slicing p1_pieces[:] / p2_pieces[:] instead of deepcopy:
    # the piece lists are the only mutable data in the state, and slicing
    # keeps the AI search tree's frequent cloning fast.
    def clone(self):
        return GameState(
            p1_pieces=self.p1_pieces[:],
            p2_pieces=self.p2_pieces[:],
            current_turn=self.current_turn,
            dice_roll=self.dice_roll,
        )

    # Roll the die with the DICE_PROBS distribution: values 1/2/3 have
    # probabilities 0.25/0.50/0.25. Stores the result in self.dice_roll
    # and returns it so callers can use it immediately.
    def roll_dice(self):
        r = random.random()
        # CDF sampling: r<0.25 -> 1; 0.25<=r<0.75 -> 2; r>=0.75 -> 3
        roll = 1 if r < 0.25 else (2 if r < 0.75 else 3)
        self.dice_roll = roll
        return roll

    # Return the list of legal piece indexes for the current player with the given
    # die value (e.g. [0, 2] means pieces 0 and 2 may move).
    # dice_roll parameter: the value used for legality checks; falls back to
    # self.dice_roll when None.
    def get_legal_moves(self, dice_roll=None):
        if dice_roll is None:
            dice_roll = self.dice_roll
        pieces = self.p1_pieces if self.current_turn == 1 else self.p2_pieces
        enemy = self.p2_pieces if self.current_turn == 1 else self.p1_pieces
        legal = []
        for idx, pos in enumerate(pieces):
            target = pos + dice_roll
            if pos >= BOARD_END or target > BOARD_END:
                continue       # already finished or would overshoot the finish: this piece cannot move
            if target < BOARD_END and target in pieces:
                continue       # our own piece blocks the target tile (target > pos, so we never flag ourselves)
            if target == 4 and 4 in enemy:
                continue       # central shield rune tile 4 is occupied by the enemy: cannot enter
            legal.append(idx)
        return legal

    # Move piece piece_idx on a cloned state and return (next_state, event_info).
    # piece_idx=None means no piece can move: skip the turn and switch current_turn.
    # dice_roll parameter: the value actually used for this move; falls back to
    # self.dice_roll when None.
    # event_info is a dict: captured=whether a piece was taken, bonus_turn=whether a
    # bonus turn was earned, scored=whether the piece reached the finish,
    # target_tile=destination tile index (-1 on skip) so the UI can trigger pixelfx effects.
    def apply_move(self, piece_idx, dice_roll=None):
        if dice_roll is None:
            dice_roll = self.dice_roll
        next_state = self.clone()   # mutate the clone so the original state stays unchanged (the AI search tree relies on this)
        event = {"captured": False, "bonus_turn": False, "scored": False, "target_tile": -1}

        # No piece can move: just skip the turn and switch player
        if piece_idx is None:
            next_state.current_turn = 2 if next_state.current_turn == 1 else 1
            return next_state, event

        pieces = next_state.p1_pieces if next_state.current_turn == 1 else next_state.p2_pieces
        enemy = next_state.p2_pieces if next_state.current_turn == 1 else next_state.p1_pieces

        target = pieces[piece_idx] + dice_roll
        event["target_tile"] = target
        pieces[piece_idx] = target

        # Capture check: inside the war zone 3..7 and not the shield rune tile 4,
        # every enemy piece sitting on target is sent back to the origin 0
        if WAR_START <= target <= WAR_END and target != 4:
            if target in enemy:
                for i in range(len(enemy)):
                    if enemy[i] == target:
                        enemy[i] = 0   # walk the whole list so multiple enemy pieces on the same tile are all sent back (index() would only handle the first)
                event["captured"] = True

        # Score check: landing exactly on the finish tile 10
        if target == BOARD_END:
            event["scored"] = True

        # Bonus turn check: landing on rune tile 4/8 while the game is not over ->
        # the same player keeps moving; otherwise switch to the other player
        if target in SAFE_TILES and not next_state.is_terminal():
            event["bonus_turn"] = True
        else:
            next_state.current_turn = 2 if next_state.current_turn == 1 else 1

        return next_state, event

    # Check whether the game is terminal: it ends when any side has all 3 pieces
    # on the finish tile BOARD_END.
    def is_terminal(self):
        return self.get_winner() != 0

    # Return the winner: 1 or 2; 0 means the game is still in progress.
    def get_winner(self):
        if all(p == BOARD_END for p in self.p1_pieces):
            return 1
        if all(p == BOARD_END for p in self.p2_pieces):
            return 2
        return 0


if __name__ == "__main__":
    # ---------------- Assertion self-tests: state transition / capture reset / rune-tile bonus turn ----------------
    s = GameState()
    assert s.p1_pieces == [0, 0, 0] and s.current_turn == 1 and s.dice_roll == 0

    # Mutating a clone must not affect the original state
    c = s.clone()
    c.p1_pieces[0] = 5
    assert s.p1_pieces[0] == 0, "clone must not share list references"

    # 10000 rolls: every value must be a key in DICE_PROBS
    rolls = [GameState().roll_dice() for _ in range(10000)]
    assert all(r in DICE_PROBS for r in rolls)

    # Capture: P1 piece 0 rolls 1 from 2 to 3, P2 piece 0 sits on 3 and must be sent back to 0;
    # 3 is not a rune tile, so the turn switches
    g = GameState(p1_pieces=[2, 10, 10], p2_pieces=[3, 0, 0], current_turn=1, dice_roll=1)
    assert g.get_legal_moves() == [0]
    ns, ev = g.apply_move(0)
    assert ev["captured"] and ev["target_tile"] == 3 and ns.p2_pieces == [0, 0, 0]
    assert ns.current_turn == 2 and not ev["bonus_turn"]

    # Bonus turn: P1 piece 0 rolls 3 from 1 to 4 (rune tile), P1 keeps the move
    g2 = GameState(p1_pieces=[1, 10, 10], p2_pieces=[0, 0, 0], current_turn=1, dice_roll=3)
    assert g2.get_legal_moves() == [0]
    ns2, ev2 = g2.apply_move(0)
    assert ev2["bonus_turn"] and ns2.current_turn == 1 and ns2.p1_pieces == [4, 10, 10]

    # Shield tile 4 occupied by the enemy -> no legal move, turn is skipped
    g3 = GameState(p1_pieces=[1, 10, 10], p2_pieces=[4, 0, 0], current_turn=1, dice_roll=3)
    assert g3.get_legal_moves() == []
    ns3, ev3 = g3.apply_move(None)
    assert ns3.current_turn == 2 and ev3["target_tile"] == -1 and not ev3["captured"]

    # Own-piece blocking: P1 [1, 4, 0] rolls 3, piece 0 (1->4) is blocked by own piece 1
    # on tile 4, so only pieces 1 (4->7) and 2 (0->3) are legal
    g5 = GameState(p1_pieces=[1, 4, 0], p2_pieces=[0, 0, 0], current_turn=1, dice_roll=3)
    assert g5.get_legal_moves() == [1, 2]

    # Win detection: P1 with all 3 pieces on 10 -> terminal and winner is 1
    g4 = GameState(p1_pieces=[10, 10, 10], p2_pieces=[0, 3, 8])
    assert g4.is_terminal() and g4.get_winner() == 1

    print("[assertions] all self-test assertions passed")

    # ---------------- Random full game simulation with key turn log ----------------
    print("[random game] starting random simulation ...")
    state = GameState()
    move_count = 0
    while not state.is_terminal():
        state.roll_dice()
        mover = "P1" if state.current_turn == 1 else "P2"
        legal = state.get_legal_moves()
        idx = random.choice(legal) if legal else None
        state, ev = state.apply_move(idx)
        move_count += 1

        tags = []
        if ev["captured"]:
            tags.append("CAPTURED!")
        if ev["bonus_turn"]:
            tags.append("rune-tile bonus turn")
        if ev["scored"]:
            tags.append("reached finish!")
        desc = f"moved piece {idx} -> tile {ev['target_tile']}" if idx is not None else "no legal move, skipped"
        print(f"  [{move_count:02d}] {mover} rolled {state.dice_roll} | {desc}"
              + (f" | {' '.join(tags)}" if tags else "")
              + f" | P1={state.p1_pieces} P2={state.p2_pieces}")
        if move_count >= 500:    # safety cap in case an extreme random sequence drags the demo on
            print("  ... hit 500 moves, stopping the demo")
            break

    winner = state.get_winner()
    print(f"[random game] game over, winner: {winner if winner else 'none (truncated)'}, total moves: {move_count}")
