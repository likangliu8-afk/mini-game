# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 1: 核心棋盘数学模型、状态克隆、合法走子与胜负判定。
# 纯 Python 零重型依赖，供 Phase 2 的 AI 搜索树高频调用。

import random

# ---- 全项目固定常量（不得随意更改）----
BOARD_END = 10                 # 终点格：棋子必须恰好落在 10 才算得分
WAR_START = 3                  # 战场区起始格（吃子区 3..7）
WAR_END = 7                    # 战场区结束格
SAFE_TILES = (4, 8)            # 符文格：踩中可获得额外回合
DICE_PROBS = {1: 0.25, 2: 0.50, 3: 0.25}   # 骰子点数概率（等价于两枚硬币 + 底数 1）


class GameState:
    """一局《Pixel Dice Ur》的完整状态：双方棋子位置、当前回合与骰子点数。"""

    # 初始化一局游戏。p1_pieces / p2_pieces 是双方 3 枚棋子的位置列表
    # （传 None 时取默认 [0, 0, 0]，即全部在起点）；current_turn 为 1 或 2，
    # 表示当前轮到哪方走子；dice_roll 为当前骰子点数（0 表示尚未掷骰）。
    def __init__(self, p1_pieces=None, p2_pieces=None, current_turn=1, dice_roll=0):
        self.p1_pieces = p1_pieces if p1_pieces is not None else [0, 0, 0]
        self.p2_pieces = p2_pieces if p2_pieces is not None else [0, 0, 0]
        self.current_turn = current_turn
        self.dice_roll = dice_roll

    # 克隆当前状态，返回一个新的 GameState 实例。
    # 用列表切片 p1_pieces[:] / p2_pieces[:] 而不是 deepcopy：
    # 棋子列表是状态里唯一的可变数据，切片让 AI 搜索树的高频克隆飞快。
    def clone(self):
        return GameState(
            p1_pieces=self.p1_pieces[:],
            p2_pieces=self.p2_pieces[:],
            current_turn=self.current_turn,
            dice_roll=self.dice_roll,
        )

    # 按 DICE_PROBS 的分布随机掷骰：点数 1/2/3 的概率分别为 0.25/0.50/0.25。
    # 结果写回 self.dice_roll 并返回，方便调用方立刻使用。
    def roll_dice(self):
        r = random.random()
        # 累积分布取点：r<0.25 -> 1；0.25<=r<0.75 -> 2；r>=0.75 -> 3
        roll = 1 if r < 0.25 else (2 if r < 0.75 else 3)
        self.dice_roll = roll
        return roll

    # 生成当前玩家在指定点数下所有合法棋子下标列表（如 [0, 2] 表示 0 号与 2 号可走）。
    # dice_roll 参数：本回合用于判定的点数；传 None 时回退用 self.dice_roll。
    def get_legal_moves(self, dice_roll=None):
        if dice_roll is None:
            dice_roll = self.dice_roll
        pieces = self.p1_pieces if self.current_turn == 1 else self.p2_pieces
        enemy = self.p2_pieces if self.current_turn == 1 else self.p1_pieces
        legal = []
        for idx, pos in enumerate(pieces):
            target = pos + dice_roll
            if pos >= BOARD_END or target > BOARD_END:
                continue       # 已在终点或会越过终点，此子本回合不可走
            if target < BOARD_END and target in pieces:
                continue       # 目标格不允许有己方其他棋子（target > pos，不会误判自己）
            if target == 4 and 4 in enemy:
                continue       # 中央护盾符文格 4 被对方占据，不可进入
            legal.append(idx)
        return legal

    # 在新克隆出的状态上执行移动 piece_idx 号棋子，返回 (next_state, event_info)。
    # piece_idx=None 表示无子可走，跳过本回合并切换 current_turn；
    # dice_roll 参数：本次移动实际使用的点数，None 时回退用 self.dice_roll。
    # event_info 为字典：captured=是否吃子，bonus_turn=是否获得额外回合，
    # scored=是否到达终点，target_tile=目标格编号（跳过时为 -1），供 UI 触发 pixelfx 特效。
    def apply_move(self, piece_idx, dice_roll=None):
        if dice_roll is None:
            dice_roll = self.dice_roll
        next_state = self.clone()   # 在克隆体上操作，原状态保持不变（AI 搜索树依赖此约定）
        event = {"captured": False, "bonus_turn": False, "scored": False, "target_tile": -1}

        # 无子可走：直接跳过回合并切换玩家
        if piece_idx is None:
            next_state.current_turn = 2 if next_state.current_turn == 1 else 1
            return next_state, event

        pieces = next_state.p1_pieces if next_state.current_turn == 1 else next_state.p2_pieces
        enemy = next_state.p2_pieces if next_state.current_turn == 1 else next_state.p1_pieces

        target = pieces[piece_idx] + dice_roll
        event["target_tile"] = target
        pieces[piece_idx] = target

        # 吃子判定：战场区 3..7 内且不是护盾符文格 4，对方凡停在 target 的棋子全部击退回起点 0
        if WAR_START <= target <= WAR_END and target != 4:
            if target in enemy:
                for i in range(len(enemy)):
                    if enemy[i] == target:
                        enemy[i] = 0   # 同格多枚敌方棋子时逐一击退，避免 index() 只处理第一枚
                event["captured"] = True

        # 得分判定：恰好踩中终点格 10
        if target == BOARD_END:
            event["scored"] = True

        # 额外回合判定：踩中符文格 4/8 且游戏尚未结束 -> 同一玩家继续；否则切换回合
        if target in SAFE_TILES and not next_state.is_terminal():
            event["bonus_turn"] = True
        else:
            next_state.current_turn = 2 if next_state.current_turn == 1 else 1

        return next_state, event

    # 判断游戏是否终局：任意一方的 3 枚棋子全部位于终点 BOARD_END 即结束。
    def is_terminal(self):
        return self.get_winner() != 0

    # 返回获胜方编号：1 或 2；0 表示尚未分出胜负（棋局进行中）。
    def get_winner(self):
        if all(p == BOARD_END for p in self.p1_pieces):
            return 1
        if all(p == BOARD_END for p in self.p2_pieces):
            return 2
        return 0


if __name__ == "__main__":
    # ---------------- 断言自测：状态转移 / 吃子回退 / 符文格连动 ----------------
    s = GameState()
    assert s.p1_pieces == [0, 0, 0] and s.current_turn == 1 and s.dice_roll == 0

    # 克隆后修改新状态不影响原状态
    c = s.clone()
    c.p1_pieces[0] = 5
    assert s.p1_pieces[0] == 0, "clone must not share list references"

    # 掷骰 10000 次，点数必须全部落在 DICE_PROBS 的键内
    rolls = [GameState().roll_dice() for _ in range(10000)]
    assert all(r in DICE_PROBS for r in rolls)

    # 吃子：P1 0 号在 2 掷 1 -> 3，P2 0 号恰在 3，应被击退回 0，且 3 非符文格需切换回合
    g = GameState(p1_pieces=[2, 10, 10], p2_pieces=[3, 0, 0], current_turn=1, dice_roll=1)
    assert g.get_legal_moves() == [0]
    ns, ev = g.apply_move(0)
    assert ev["captured"] and ev["target_tile"] == 3 and ns.p2_pieces == [0, 0, 0]
    assert ns.current_turn == 2 and not ev["bonus_turn"]

    # 额外回合：P1 0 号在 1 掷 3 -> 4（符文格），P1 继续走子
    g2 = GameState(p1_pieces=[1, 10, 10], p2_pieces=[0, 0, 0], current_turn=1, dice_roll=3)
    assert g2.get_legal_moves() == [0]
    ns2, ev2 = g2.apply_move(0)
    assert ev2["bonus_turn"] and ns2.current_turn == 1 and ns2.p1_pieces == [4, 10, 10]

    # 护盾格 4 被对方占据时不可进入 -> 无合法走子，跳过回合
    g3 = GameState(p1_pieces=[1, 10, 10], p2_pieces=[4, 0, 0], current_turn=1, dice_roll=3)
    assert g3.get_legal_moves() == []
    ns3, ev3 = g3.apply_move(None)
    assert ns3.current_turn == 2 and ev3["target_tile"] == -1 and not ev3["captured"]

    # 己方棋子挡路：P1 [1, 4, 0] 掷 3 时，0 号(1->4)因目标格有己方 1 号被挡，仅 1 号(4->7)与 2 号(0->3)可走
    g5 = GameState(p1_pieces=[1, 4, 0], p2_pieces=[0, 0, 0], current_turn=1, dice_roll=3)
    assert g5.get_legal_moves() == [1, 2]

    # 胜负判定：P1 三子全到 10 即终局且获胜方为 1
    g4 = GameState(p1_pieces=[10, 10, 10], p2_pieces=[0, 3, 8])
    assert g4.is_terminal() and g4.get_winner() == 1

    print("[assertions] 全部自测断言通过")

    # ---------------- 随机模拟完整一局并打印关键回合日志 ----------------
    print("[random game] 开始随机模拟对战 ...")
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
            tags.append("吃子!")
        if ev["bonus_turn"]:
            tags.append("符文格额外回合")
        if ev["scored"]:
            tags.append("到达终点!")
        desc = f"移动 {idx} 号 -> 格 {ev['target_tile']}" if idx is not None else "无子可走, 跳过"
        print(f"  [{move_count:02d}] {mover} 掷出 {state.dice_roll} | {desc}"
              + (f" | {' '.join(tags)}" if tags else "")
              + f" | P1={state.p1_pieces} P2={state.p2_pieces}")
        if move_count >= 500:    # 安全上限，防止极端随机序列拖死演示
            print("  ... 超过 500 步, 停止演示")
            break

    winner = state.get_winner()
    print(f"[random game] 终局, 获胜方: {winner if winner else '无(被截断)'}, 共 {move_count} 步")
