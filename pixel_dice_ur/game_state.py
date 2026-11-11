"""[Phase 1] 核心棋盘数学模型、状态克隆、合法走子与胜负判定。

Responsibilities:
- 棋盘数学模型（格子、骰子点数映射、玩家/棋子布局）
- GameState 不可变快照与状态克隆 (clone)
- 合法走子生成 (legal move generation)
- 胜负判定 (win/loss detection)
"""

# TODO(Phase 1):
# - 定义 Board / Piece / Player / Dice 数据结构
# - 实现 GameState.clone()（深拷贝，供 AI 搜索使用）
# - 实现 get_legal_moves(state, piece_id)
# - 实现 check_winner(state)
