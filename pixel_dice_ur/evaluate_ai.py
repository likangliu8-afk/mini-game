# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 2: automated AI benchmark. Plays three symmetric matchups (200 games each,
# 100 per starting order to neutralise first-move bias), runs an Expectiminimax
# depth study (depth 2/3/4), prints a stats table and renders an academic
# two-panel chart ai_comparison.png with matplotlib.
#
# Usage:
#     python pixel_dice_ur/evaluate_ai.py

import os
import random
import sys
import time

import matplotlib
matplotlib.use("Agg")   # headless backend so the script can run without a display
import matplotlib.pyplot as plt

# Import from the same directory when run directly, or from the parent package layout
# when imported by another module from a different cwd
try:
    from game_state import DICE_PROBS, GameState
    from ai_engine import (DeterministicMinimaxAgent, ExpectiminimaxAgent,
                           GreedyAgent)
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from game_state import DICE_PROBS, GameState
    from ai_engine import (DeterministicMinimaxAgent, ExpectiminimaxAgent,
                           GreedyAgent)

GAMES_PER_MATCHUP = 200     # 100 games with agent_a moving first + 100 with agent_b moving first
GAMES_PER_DEPTH = 25        # quick depth-study sample, keeps the total runtime low
MAX_MOVES_PER_GAME = 600    # safety cap against pathological random loops


# Play one full headless game between two agents and collect per-move statistics.
# agent_a: plays P1 when starting_side=1, otherwise P2; agent_b plays the other side.
# starting_side: 1 means agent_a is P1 (first mover), 2 means agent_b is P1.
# stats_a / stats_b: optional dicts holding time_ms_list / nodes_list for each agent;
# every decision's timing and node count is appended so callers can average over a
# whole batch of games (pass None for the agent whose stats you do not need).
def play_game(agent_a, agent_b, starting_side=1, stats_a=None, stats_b=None):
    state = GameState()
    a_side = 1 if starting_side == 1 else 2   # the player number agent_a controls in this game
    moves = 0
    while not state.is_terminal():
        state.roll_dice()
        if state.current_turn == a_side:
            agent, stats = agent_a, stats_a   # record each agent's decisions in its own stats dict
        else:
            agent, stats = agent_b, stats_b
        move, scores, s = agent.choose_move(state)
        if stats is not None:
            stats["time_ms_list"].append(s["time_ms"])
            stats["nodes_list"].append(s["nodes"])
        state, _ = state.apply_move(move, state.dice_roll)
        moves += 1
        if moves >= MAX_MOVES_PER_GAME:    # cap: an extreme random game must not stall the benchmark
            break
    winner = state.get_winner()
    # map the raw winner number back to the agent it belongs to: 1 -> agent_a, -1 -> agent_b, 0 -> draw/cap
    if winner == 0:
        return 0
    return 1 if winner == a_side else -1


# Run a whole matchup: GAMES_PER_MATCHUP symmetric games split evenly between
# starting orders so the weak first-move advantage is averaged out.
# agent_a_cls / agent_b_cls: the agent classes to pit against each other (one shared
# instance per side; agent search state resets inside every choose_move call).
# Returns a dict: wins_a, wins_b, total wall time, and per-move stats of both agents.
def run_matchup(agent_a_cls, agent_b_cls, games=GAMES_PER_MATCHUP):
    agent_a = agent_a_cls()
    agent_b = agent_b_cls()
    stats_a = {"time_ms_list": [], "nodes_list": []}
    stats_b = {"time_ms_list": [], "nodes_list": []}
    wins_a = wins_b = draws = 0
    half = games // 2
    t0 = time.perf_counter()
    for starting_side in (1, 2):
        for _ in range(half):
            result = play_game(agent_a, agent_b, starting_side, stats_a, stats_b)
            # play_game normalises the winner to the agent: +1 -> agent_a, -1 -> agent_b, 0 -> capped/draw
            if result == 0:
                draws += 1
            elif result == 1:
                wins_a += 1
            else:
                wins_b += 1
    total_time = time.perf_counter() - t0
    return {"wins_a": wins_a, "wins_b": wins_b, "draws": draws,
            "stats_a": stats_a, "stats_b": stats_b, "total_time_s": total_time}


# Run the Expectiminimax depth study: play GAMES_PER_DEPTH games per depth against
# a GreedyAgent and record average decision time and node count per depth.
# Returns one dict per depth with keys: depth, avg_ms, max_ms, avg_nodes, n_moves.
def run_depth_study():
    rows = []
    for depth in (2, 3, 4):
        exp = ExpectiminimaxAgent(depth=depth)
        greedy = GreedyAgent()
        stats = {"time_ms_list": [], "nodes_list": []}   # only the Expectiminimax agent's decisions are tracked
        half = GAMES_PER_DEPTH // 2
        for starting_side in (1, 2):
            for _ in range(half):
                play_game(exp, greedy, starting_side, stats_a=stats, stats_b=None)
        rows.append({
            "depth": depth,
            "avg_ms": sum(stats["time_ms_list"]) / len(stats["time_ms_list"]),
            "max_ms": max(stats["time_ms_list"]),
            "avg_nodes": sum(stats["nodes_list"]) / len(stats["nodes_list"]),
            "n_moves": len(stats["time_ms_list"]),
        })
    return rows


# Draw the academic two-panel figure: win-rate bars on the left, average decision
# time and node counts on the right; saved to out_path next to this script.
# matchup_results: list of (label, wins_a, wins_b) tuples for the three pairings;
# depth_rows: output of run_depth_study(); baseline_times / baseline_nodes: average
# ms and node counts of Greedy and Minimax measured during the matchup runs.
def make_chart(matchup_results, depth_rows, baseline_times, baseline_nodes, out_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6), dpi=150)

    # Left panel: win rate bars for the two agents of each matchup
    labels = [m[0] for m in matchup_results]
    a_rates = [100.0 * m[1] / m[3] for m in matchup_results]
    b_rates = [100.0 * m[2] / m[3] for m in matchup_results]
    x = range(len(labels))
    ax1.bar([i - 0.2 for i in x], a_rates, width=0.4, label="Agent A", color="#3b6fb6")
    ax1.bar([i + 0.2 for i in x], b_rates, width=0.4, label="Agent B", color="#d98c3f")
    for i, (ra, rb) in enumerate(zip(a_rates, b_rates)):
        ax1.text(i - 0.2, ra + 1.2, f"{ra:.1f}", ha="center", fontsize=8)
        ax1.text(i + 0.2, rb + 1.2, f"{rb:.1f}", ha="center", fontsize=8)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, fontsize=8, rotation=12)
    ax1.set_ylabel("Win Rate (%)")
    ax1.set_title("Win Rate by Matchup (200 symmetric games each)")
    ax1.set_ylim(0, 110)
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", linestyle=":", alpha=0.6)

    # Right panel: average decision time (bars) and average node count (line) per algorithm/depth
    names = ["Greedy", "Minimax d=4"] + [f"Expect d={r['depth']}" for r in depth_rows]
    times = list(baseline_times) + [r["avg_ms"] for r in depth_rows]
    nodes = list(baseline_nodes) + [r["avg_nodes"] for r in depth_rows]
    x2 = range(len(names))
    ax2.bar(x2, times, color="#7a9e5f", label="avg time (ms)")
    ax2_t = ax2.twinx()
    ax2_t.plot(x2, nodes, "o-", color="#b6484f", label="avg nodes")
    for i, (t, n) in enumerate(zip(times, nodes)):
        ax2.text(i, t + max(times) * 0.02, f"{t:.2f}", ha="center", fontsize=7)
        ax2_t.text(i, n + max(nodes) * 0.02, f"{n:.0f}", ha="center", fontsize=7, color="#b6484f")
    ax2.set_xticks(list(x2))
    ax2.set_xticklabels(names, fontsize=8, rotation=12)
    ax2.set_ylabel("Average decision time (ms)", color="#7a9e5f")
    ax2_t.set_ylabel("Average search nodes", color="#b6484f")
    ax2.set_title("Decision Time & Node Count by Algorithm / Depth")
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_t.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper left")

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    random.seed(2026)
    bench_start = time.perf_counter()

    print("=" * 78)
    print("Pixel Dice Ur - AI Benchmark (Phase 2)")
    print("=" * 78)

    # ---- Matchups: 200 symmetric games each (100 per starting order) ----
    matchup_specs = [
        ("Expect d=4 vs Greedy", ExpectiminimaxAgent, GreedyAgent),
        ("Expect d=4 vs Minimax d=4", ExpectiminimaxAgent, DeterministicMinimaxAgent),
        ("Minimax d=4 vs Greedy", DeterministicMinimaxAgent, GreedyAgent),
    ]

    matchup_results = []
    for label, agent_a_cls, agent_b_cls in matchup_specs:
        res = run_matchup(agent_a_cls, agent_b_cls)
        matchup_results.append((label, res["wins_a"], res["wins_b"],
                                res["wins_a"] + res["wins_b"] + res["draws"],
                                res["stats_a"], res["stats_b"], res["total_time_s"]))
        print(f"\nMatchup: {label}  ({res['total_time_s']:.1f}s wall time)")
        print(f"  Agent A wins: {res['wins_a']:3d}  |  Agent B wins: {res['wins_b']:3d}  |  "
              f"draws(capped): {res['draws']}")
        for side, st in (("A", res["stats_a"]), ("B", res["stats_b"])):
            if st["time_ms_list"]:
                print(f"  Agent {side}: avg {sum(st['time_ms_list'])/len(st['time_ms_list']):.2f} ms/decision, "
                      f"avg {sum(st['nodes_list'])/len(st['nodes_list']):.0f} nodes")

    # ---- Expectiminimax depth study ----
    depth_rows = run_depth_study()
    print(f"\nExpectiminimax depth study ({GAMES_PER_DEPTH} games per depth, vs GreedyAgent):")
    print(f"  {'depth':>6} | {'avg ms':>9} | {'max ms':>9} | {'avg nodes':>10} | {'moves':>6}")
    for row in depth_rows:
        print(f"  {row['depth']:6d} | {row['avg_ms']:9.2f} | {row['max_ms']:9.2f} | "
              f"{row['avg_nodes']:10.0f} | {row['n_moves']:6d}")

    # ---- Chart data: baseline averages for Greedy/Minimax come from the matchup runs ----
    # Greedy is Agent B in matchup 1, Minimax is Agent B in matchup 2
    greedy_stats = matchup_results[0][5]
    minimax_stats = matchup_results[1][5]
    baseline_times = [sum(greedy_stats["time_ms_list"]) / len(greedy_stats["time_ms_list"]),
                      sum(minimax_stats["time_ms_list"]) / len(minimax_stats["time_ms_list"])]
    baseline_nodes = [sum(greedy_stats["nodes_list"]) / len(greedy_stats["nodes_list"]),
                      sum(minimax_stats["nodes_list"]) / len(minimax_stats["nodes_list"])]

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_comparison.png")
    make_chart(matchup_results, depth_rows, baseline_times, baseline_nodes, out)
    print(f"\nChart saved to: {out}")
    print(f"Total benchmark time: {time.perf_counter() - bench_start:.1f}s")
