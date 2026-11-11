# Mini Game — Pixel Dice

Artificial Principles mini project: a pixel-art dice board game with AI opponents (Expectiminimax / Minimax / Greedy).

## Project Directory Structure

```
pixel_dice_ur/
├── assets/
│   └── vfx/                  # 存放从 patch-gg/pixelfx 导出的 PNG 精灵图与 JSON 时序文件
│       ├── dice_roll.png
│       ├── dice_roll.json
│       ├── hit_explosion.png
│       ├── hit_explosion.json
│       ├── rune_glow.png
│       └── rune_glow.json
├── game_state.py             # [Phase 1] 核心棋盘数学模型、状态克隆、合法走子与胜负判定
├── ai_engine.py              # [Phase 2] Expectiminimax、Minimax 与 Greedy 算法及启发式评估函数
├── evaluate_ai.py            # [Phase 2] 自动化 AI 对战测试脚本（跑 100 局生成胜率与耗时对比图）
├── vfx_manager.py            # [Phase 3] 读取 pixelfx 序列帧 + 纯 Python 像素粒子回退渲染器
└── main.py                   # [Phase 4] Pygame 主循环、网格棋盘 UI、学号姓名顶栏、AI 思考分值面板
```

## Development Phases

| Phase | Module | Scope |
|-------|--------|-------|
| 1 | `game_state.py` | Board math model, state cloning, legal move generation, win/loss detection |
| 2 | `ai_engine.py` + `evaluate_ai.py` | Expectiminimax / Minimax / Greedy search + heuristic evaluation; 100-game automated benchmark |
| 3 | `vfx_manager.py` | pixelfx sprite-sheet + JSON timeline loader with pure-Python pixel particle fallback |
| 4 | `main.py` | Pygame main loop, grid board UI, student-id/name top bar, AI thinking score panel |

## Getting Started

```bash
pip install pygame numpy matplotlib
python pixel_dice_ur/main.py
```
