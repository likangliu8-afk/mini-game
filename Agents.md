# Agents.md — Pixel Dice Ur 交接 / 验收文档（面向规划者 AI）

> 用途：本文件是执行者（Executor）→ 规划者（Planner）的交接与验收清单。所有数据均来自已完成的真实产物与本机运行证据，可逐条核对打勾。
> 代码位于 GitHub 仓库 `likangliu8-afk/mini-game` 的 `main` 分支；本文件建议放在仓库根目录（与 `README.md` 平级），不作为课程代码提交物。

---

## 1. 项目状态总览

| 项 | 状态 |
|---|---|
| 课程 | 5ENT1140 Artificial Intelligence Principles |
| 项目 | 《Pixel Dice Ur》双人含随机要素（Chance）回合制博弈游戏 |
| 语言 | 纯 Python（Phase 4 引入 pygame） |
| GitHub | https://github.com/likangliu8-afk/mini-game |
| Phase 3 commit | `cc4d987`（feat(phase3)：4 组 pixelfx 资产 + VFXManager） |
| Phase 4 commit | 本次提交（`main.py` + `gameplay_preview.png` + 本 `Agents.md` 更新） |

**阶段进度：**

- Phase 1 `game_state.py` ✅ 完成
- Phase 2 `ai_engine.py` + `evaluate_ai.py` ✅ 完成
- Phase 3 `vfx_manager.py` + 4 组 pixelfx 资产 ✅ 完成
- Phase 4 `main.py`（Pygame 主循环 + 棋盘 UI + 学号姓名顶栏 + AI 决策透视面板 + 特效绑定 + `--self-test`）✅ 完成

---

## 2. 合规红线自查（课程硬性要求，规划者优先核对）

- [ ] 每个 `.py` 文件顶部署名：`# Name: LAW LI KANG RAIN` / `# Student ID: 1904VECI`
- [ ] 每个函数定义 `def` 正上方使用 `#` 注释（非 `"""` docstring、非 `# ====` 装饰横幅），写明「做什么 + 每个参数/核心变量用途」
- [ ] 关键调参处附工程调试风格注释（如 `# Set FINISH_WEIGHT to 120.0 so finishing a piece always outweighs sitting on tile 4`）
- [ ] 固定常量未改动：`BOARD_END = 10`, `WAR_START = 3`, `WAR_END = 7`, `SAFE_TILES = (4, 8)`, `DICE_PROBS = {1: 0.25, 2: 0.50, 3: 0.25}`
- [ ] 固定状态属性未改动：`p1_pieces`（初始 `[0,0,0]`）、`p2_pieces`（初始 `[0,0,0]`）、`current_turn`（1/2）、`dice_roll`（1~3）
- [ ] 项目内零 JS：`dir /s /b pixel_dice_ur\*.js`、`*.mjs`、`package.json`、`node_modules` 均返回 **File Not Found**
- [ ] pixelfx 仅克隆在系统临时目录 `%TEMP%\pixelfx_exporter`（已彻底删除），未进入项目目录
- [ ] 代码注释 / 日志 / 字符串全部英文（无中文残留）

> **原创占比 >50% 说明**：项目全部 Python 逻辑（状态机、三种博弈算法、启发式评估函数、VFX 管理器、实验对比脚本）均为原创实现；pixelfx 仅作为**离线烘焙工具**一次性生成静态 PNG+JSON 美术资产，未引入任何 JS 运行时依赖。

---

## 3. 各 Phase 交付物与关键数据

### Phase 1 — `game_state.py`（commit `d816c49`）

- 6 个必需方法：`__init__`、`clone`（列表切片 `self.p1_pieces[:]` 快速克隆）、`roll_dice`（累积分布取点）、`get_legal_moves`、`apply_move`（吃子 / 额外回合 / 得分 + 返回 `event_info` 字典）、`is_terminal` + `get_winner`
- `apply_move` 返回 `(next_state, event_info)`，`event_info` 含 `captured` / `bonus_turn` / `scored` / `target_tile`，供 Phase 3/4 UI 触发对应特效
- 断言自测全部通过（克隆隔离、掷骰合法性、吃子回退、符文格连动、护盾格禁入、己方挡路、终局判定）；随机模拟整局正常终局

### Phase 2 — `ai_engine.py` + `evaluate_ai.py`（commit `363dc47`）

**启发式评估函数特征权重（模块顶部常量，便于报告引用）：**

`WIN_SCORE=1000.0`、`FINISH_WEIGHT=120.0`、`PROGRESS_WEIGHT=6.0`、`SHIELD_BONUS=18.0`、`DANGER_PENALTY=14.0`（暴露惩罚按 `DICE_PROBS[dist]` 加权，棋子在 3/5/6/7 时若敌方棋子在后方 1~3 格内扣 `14.0 × 概率`）

**三个 Agent 统一接口：** `choose_move(state) -> (best_move, move_scores, stats)`
- `best_move`：最优棋子下标 `int`（无合法走法返回 `None`）
- `move_scores`：`dict[int, float]`，记录每个合法走子的评估分（供 Phase 4 面板可视化）
- `stats`：`{"nodes": int, "time_ms": float}`

- `GreedyAgent`：单步展开所有合法走法 + 静态估值（`bonus_turn` 加小额即时奖励）
- `DeterministicMinimaxAgent(depth=4)`：Alpha-Beta 剪枝，未来固定假设 `dice_roll = 2`（对照组）
- `ExpectiminimaxAgent(depth=4)`：完整 Chance 节点（按 `DICE_PROBS` 加权求期望）+ P1 视角共享值 + Transposition Table

**三组对称对战（各 200 局 = 先手 100 + 后手 100，消除先手优势）：**

| Matchup | Agent A 胜 | Agent B 胜 | 单步耗时 A / B |
|---|---|---|---|
| Expectiminimax d=4 vs Greedy | 113（56.5%） | 87（43.5%） | 4.66 ms / 0.02 ms |
| Expectiminimax d=4 vs Minimax d=4 | 115（57.5%） | 85（42.5%） | 4.98 ms / 0.17 ms |
| Minimax d=4 vs Greedy | 90（45.0%） | 110（55.0%） | 0.18 ms / 0.02 ms |

**Expectiminimax 深度研究（对 GreedyAgent，每深度 25 局）：**

| depth | 平均耗时 | 最大耗时 | 平均节点数 |
|---|---|---|---|
| 2 | 0.13 ms | 0.82 ms | 7 |
| 3 | 0.78 ms | 3.74 ms | 48 |
| 4 | 4.83 ms | 17.58 ms | 307 |

> 结论：d=4 单步平均 4.83ms、最坏 17.6ms，**远低于 50ms 预算**（Transposition Table 起效明显）；Expectiminimax 同时压制另外两算法，印证随机博弈中建模 Chance 节点的必要性。
> 图表：`pixel_dice_ur/ai_comparison.png`（双子图：左=三组胜率对比，右=算法/深度的耗时与节点数）。

### Phase 3 — 4 组 pixelfx 资产 + `vfx_manager.py`（commit `cc4d987`）

4 组资产为 `node tools/render.mjs <id> --sheet --no-actor` 离线烘焙导出的静态 PNG + Aseprite 风格 JSON：

| 场景文件 | pixelfx 预设 id | PNG 总尺寸 | 单帧 | 帧数 | fps | loop | pivot | 列数 |
|---|---|---|---|---|---|---|---|---|
| `dice_roll` | `arcane/mana-burst` | 1456×1200 | 208×150 | 55 | 30 | 否 | [104,124] | 7 |
| `hit_explosion` | `explosions/small-explosion` | 3600×3360 | 300×240 | 163 | 30 | 否 | [150,196] | 12 |
| `rune_glow` | `arcane/rune-circle` | 1360×1200 | 136×100 | 120 | 30 | 是 | [68,80] | 10 |
| `score_burst` | `ui/confetti` | 1800×1680 | 200×140 | 103 | 30 | 否 | [100,126] | 9 |

**真实 pixelfx JSON Schema（`dice_roll.json` 的 meta 段 + 帧结构示例）：**

```json
{
  "frames": [
    { "filename": "mana-burst 0",
      "frame": { "x": 0, "y": 0, "w": 208, "h": 150 },
      "rotated": false, "trimmed": false,
      "spriteSourceSize": { "x": 0, "y": 0, "w": 208, "h": 150 },
      "sourceSize": { "w": 208, "h": 150 },
      "duration": 33 }
  ],
  "meta": {
    "app": "https://github.com/patch-gg/pixelfx", "version": "1",
    "image": "mana-burst.png", "format": "RGBA8888",
    "size": { "w": 1456, "h": 1200 }, "scale": "1",
    "frameTags": [ { "name": "mana-burst", "from": 0, "to": 54, "direction": "forward" } ],
    "pixelfx": { "id": "arcane/mana-burst", "name": "Mana burst",
      "fps": 30, "loop": false, "frames": 55,
      "frameSize": [208,150], "pivot": [104,124], "columns": 7 }
  }
}
```

> 关键字段：每帧 `frame.x/y` 是它在 PNG 网格里的裁剪坐标，`duration` 是毫秒（≈33ms = 30fps）；`meta.pixelfx.pivot` 是特效原点在单帧内的锚点（用于居中摆放），`loop` 决定播放次数。**注意** `meta.image` 保留原预设名（如 `mana-burst.png`），`vfx_manager.py` 按实际文件名 `dice_roll.png` 加载并忽略该字段。

**`vfx_manager.py` 统一接口：**

- `__init__(self, assets_dir=None, default_scale=0.65)`
- `spawn(self, effect_name, x, y, loop=False, max_duration_ms=None, scale=None) -> ActiveEffect`
- `trigger_shake(self, duration_ms=180, intensity=5)`
- `update(self, dt_ms)`
- `get_shake_offset(self) -> (ox, oy)`
- `draw(self, surface, offset=(0, 0))`
- `clear(self)`

行为要点：
- 屏幕震动预设：`hit_explosion` → 强震屏（220ms, 6px）；`score_burst` / `rune_glow` → 轻震屏（120ms, 3px）
- `rune_glow` 默认 `loop=False`，未显式传 `loop=True` 时自动 `max_duration_ms=1500` 播完即停，防止法阵在棋盘上永久残留
- pivot 随 `scale` 同比缩放，绘制严格按 `(x - scaled_pivot_x, y - scaled_pivot_y)` 锚定，让爆炸与法阵精准落在棋子脚下；`pygame.transform.scale`（nearest）保持锐利像素边缘
- 缺失 PNG 时自动回退生成 48×48 放大 2× 的 12 帧硬边缘像素序列（对应中心 pivot + 33ms），保证零外部图片时 100% 可运行

### Phase 4 — `main.py`（Pygame 主程序 + 可视化 + 特效绑定）

**文件头与署名展示（评分要求 1a）：**
- 模块顶部常量 `AUTHOR_NAME = "LAW LI KANG RAIN"`、`STUDENT_ID = "1904VECI"`，改这两处即可同步更新窗口标题与顶栏
- 顶栏常驻 `BANNER_TEXT = "PIXEL DICE UR   |   Name: LAW LI KANG RAIN   |   Student ID: 1904VECI"`（24px 字体）

**窗口与三区布局（1024×640 @60FPS）：**
- 顶部 48px 控制栏：左=署名横幅；右=`[AI: <算法名>]`（点击循环切换 Expectiminimax→Minimax→Greedy）+ `[New Game (R)]`
- 左侧 650px 战术棋盘：3 行 × 6 列网格（地砖 84×84，像素双层边框 + 阴影），`0..10` 逻辑格按 SHARED_CELL / LANE_CELL 映射
  - P1（人类，青蓝/金）走上排 → 中排共享战区 → 上排冲刺；P2（AI，绯红/紫）上下对称
  - 4 号格画金色护盾符文纹章（8 向光点 + 同心圆），10 号终点画绿心圣坛
  - 双方 "Scored: X/3" 计数托盘
- 右侧 374px 双面板：
  - 上：`AI DECISION INSPECTOR`——算法名 / 节点数 / 单步耗时 / Evaluation 优势条 / **候选走法得分表**（`#1→tile X  +NN.N` 每行带色条，`[BEST]` 高亮选中步）/ `[Hint: ON/OFF]` 开关（对当前人类局面实时跑 Expectiminimax d=4）
  - 下：`DICE & BATTLE LOG`——像素骰子（点数按 `dice_roll` 绘制）+ `[ROLL (Space)]` 按钮 + 概率提示 `P1=25% P2=50% P3=25%` + 最近 6 条战斗日志

**交互与节奏：**
- 人类合法棋子高亮脉冲外框；Hover 半透明预览目标格（吃子红 / 符文金 / 普通绿，带 `CAPTURE!` / `RUNE*` 标签）
- 点击棋子 / 点击目标格 / 按 `1/2/3` 数字键皆可走子；`Space` 掷骰；`R` 重开
- `legal_moves` 为空时提示 "No legal moves - Turn skipped" 并 700ms 后自动切回合
- 棋子 180ms 像素插值滑动；AI 回合 450ms 掷骰 → 展示评估 → 走子的自然节奏

**4 组 pixelfx 特效精确绑定（事件 → 触发点）：**

| 事件 | 触发条件 | 特效与参数 |
|---|---|---|
| 掷骰 | 人/AI `roll_dice()` 时 | `spawn("dice_roll", 骰子中心, scale=0.55)` |
| 吃子回退 | `event["captured"]` | `spawn("hit_explosion", 战区格中心, scale=0.65)` |
| 符文额外回合 | `event["bonus_turn"]` | `spawn("rune_glow", 符文格中心, scale=0.75)` |
| 抵达终点得分 | `event["scored"]` | `spawn("score_burst", 终点格中心, scale=0.75)`；整局胜利再错位连放 2 发庆祝 |

**⚠️ 震屏偏移已正确处理**：渲染棋盘/棋子时用 `vfx.get_shake_offset()` 偏移，随后 `vfx.draw(screen, (0, 0))` 传 `(0,0)`——因为 `vfx_manager.draw` 内部已自动叠加 `_shake_ox/_oy`，不重复传入避免双倍震动。

**`--self-test` 无头自检**：`SDL_VIDEODRIVER=dummy` 快进 30 步 AI vs AI，全 UI 渲染 + 4 种特效强制出现，保存 `pixel_dice_ur/gameplay_preview.png` 供规划者目检排版；正常无参运行则开真实窗口供人类游玩。

---

## 4. 验证证据

**无头自检（`SDL_VIDEODRIVER=dummy`，`python pixel_dice_ur/vfx_manager.py`）实际输出：**

```
[load] dice_roll: 55 frames, loop=False, pivot (104, 124) -> scaled pivot (67.6, 80.6) @ scale 0.65
[load] hit_explosion: 163 frames, loop=False, pivot (150, 196) -> scaled pivot (97.5, 127.4) @ scale 0.65
[load] rune_glow: 120 frames, loop=True, pivot (68, 80) -> scaled pivot (44.2, 52.0) @ scale 0.65
[load] score_burst: 103 frames, loop=False, pivot (100, 126) -> scaled pivot (65.0, 81.9) @ scale 0.65
[vfx] dice_roll: assets missing, using procedural pixel fallback      （空目录回退 ×4）
[self-test] all VFX checks passed (real assets + spawn/update/draw + fallback)
```

- 4 组 PNG+JSON 逐张断言：PNG 尺寸 == `meta.size`、帧数 == `meta.pixelfx.frames`，全部一致（`OK: all 4 pairs consistent`）
- 断言覆盖：真实资产全部从磁盘加载（非回退）、`spawn/update/draw` 全流程、吃子强震触发、`loop=True` 的 `rune_glow` 在 6.4s 窗口内持续存活、空目录回退模式同样通过

**Phase 4 无头自检（`python pixel_dice_ur/main.py --self-test`，SDL dummy driver）实际输出：**

```
[self-test] rendered 30 fast steps; preview saved to ...\pixel_dice_ur\gameplay_preview.png
[self-test] game over=False, winner=0, turns=36
[self-test] all main.py UI checks passed
```

- 30 步 AI vs AI 快进，全 UI 渲染 + 4 种特效强制出现，零报错；`gameplay_preview.png` 已目检：顶栏署名、Inspector（含候选分+ [BEST]）、双栏骰子/日志、4 组特效均无重叠/越界/遮挡

---

## 5. 本机运行环境（供复现）

- 运行解释器：Windows Python 3.12 — `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`（已安装 pygame 2.6.1、matplotlib）
- 默认 `python` 是 MSYS2 Python 3.14（无 pip，不能装包 / 不能跑 benchmark）
- Node v26.2.0 / npm 11.13.0（仅 Phase 3A 离线烘焙用，临时克隆已删除）

---

## 6. 留给规划者的决策点

**Phase 3 已确认（Approved）：**
- `score_burst` 选用 `ui/confetti`（103 帧多彩彩纸）而非 `pickups/collect-burst` ✅
- `meta.image` 保留原预设名，`vfx_manager.py` 按实际文件名加载并忽略该字段 ✅

**Phase 4 已实现，请规划者核对：**
- 顶栏 / 棋盘拓扑 / Inspector 面板 / 骰子日志布局是否符合预期？
- 特效触发映射与 scale 参数是否合适？
- `--self-test` 生成的 `gameplay_preview.png` 排版是否无重叠/越界/遮挡？
- 是否还有其他 UI 细节需要调整？

---

## 7. 复现命令

```
python pixel_dice_ur/game_state.py     # Phase 1 断言自测 + 随机对局
python pixel_dice_ur/evaluate_ai.py     # Phase 2 三组 200 局对战 + 深度研究 + 生成 ai_comparison.png
python pixel_dice_ur/vfx_manager.py     # Phase 3 无头自检（真实资产 + spawn/update/draw + 回退）
python pixel_dice_ur/main.py            # Phase 4 打开真实窗口游玩（P1 人类 vs P2 AI）
python pixel_dice_ur/main.py --self-test  # Phase 4 无头自检 + 生成 gameplay_preview.png
```
