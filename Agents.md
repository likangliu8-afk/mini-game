# PIXEL DICE UR — 项目圣经（Project Bible）

> **本文件是常驻交接文档。** 任何新窗口（人或 AI）只需读本文件 + 浏览 `pixel_dice_ur/` 下各 `.py` 顶部注释，即可 100% 恢复项目全部上下文。
> 每完成一个 Phase，在 §4 Phase Log 末尾按 §5 模板追加一条；**不得删除或改写已归档条目**（可追加"修订"小注）。

---

## §0 项目身份与不变量（Invariants — 永不修改）

| 项 | 值 |
|---|---|
| 课程 | 5ENT1140 Artificial Intelligence Principles |
| 项目名 | Pixel Dice Ur |
| 作者 | LAW LI KANG RAIN |
| 学号 | 1904VECI |
| 语言 | 纯 Python 3.12（Phase 4 引入 pygame） |
| GitHub | `likangliu8-afk/mini-game` → `main` 分支 |
| 本文件位置 | 仓库根目录（与 `README.md` 平级），不作为课程代码提交物 |

### 固定常量（`game_state.py` 顶部，禁止重命名/改值）

```python
BOARD_END = 10
WAR_START = 3
WAR_END = 7
SAFE_TILES = (4, 8)
DICE_PROBS = {1: 0.25, 2: 0.50, 3: 0.25}
```

### 固定状态属性（`GameState`）

| 属性 | 类型/初始值 |
|---|---|
| `p1_pieces` | `list[int]`，初始 `[0, 0, 0]` |
| `p2_pieces` | `list[int]`，初始 `[0, 0, 0]` |
| `current_turn` | `int`，`1` 或 `2` |
| `dice_roll` | `int`，`0`=未掷，`1~3`=已掷 |

### 合规红线（课程硬性要求，每个新文件/每次改动前核对）

- [ ] 每个 `.py` 顶部署名：`# Name: LAW LI KANG RAIN` / `# Student ID: 1904VECI`
- [ ] 每个 `def` 正上方用 `#` 注释（非 docstring、非装饰横幅）写明「做什么 + 每个参数/核心变量用途」
- [ ] 关键调参处附工程调试风格注释
- [ ] 项目内**零 JS**（无 `.js` / `.mjs` / `package.json` / `node_modules`）
- [ ] 代码注释 / 日志 / 字符串**全英文**（零中文）
- [ ] pixelfx 仅作离线烘焙工具（一次性生成静态 PNG+JSON），不引入 JS 运行时

> **原创占比 >50% 声明**：全部 Python 逻辑（状态机、三种博弈算法、启发式评估、VFX 管理器、实验脚本、像素美术库）均为原创实现。

---

## §1 恢复协议（Recovery Protocol — 新窗口必读）

1. **读本文件** §0（不变量）→ §3（环境）→ §4（Phase Log 最后一条 = 当前进度）→ §5（追加模板）。
2. **浏览代码**：`pixel_dice_ur/` 下各 `.py` 顶部 50 行注释（模块说明 + 常量 + 接口）。
3. **跑自检**（§3 命令）确认基线通过：
   ```
   python pixel_dice_ur/game_state.py
   python pixel_dice_ur/vfx_manager.py
   python pixel_dice_ur/main.py --self-test
   ```
4. **读 §6 待决策 / 下一步任务**，确认当前要做什么。
5. 完成后按 §5 模板追加 Phase Log 条目，更新 §6。

---

## §2 文件清单与职责

| 文件 | Phase | 职责 |
|---|---|---|
| `game_state.py` | 1 | 核心状态机：`GameState` 类（clone / roll_dice / get_legal_moves / apply_move / is_terminal / get_winner） |
| `ai_engine.py` | 2 | 三种 Agent（Greedy / DeterministicMinimax / Expectiminimax）+ 启发式评估函数 + 统一接口 `choose_move(state)` |
| `evaluate_ai.py` | 2 | 实验脚本：三组 200 局对称对战 + 深度研究 → 生成 `ai_comparison.png` |
| `vfx_manager.py` | 3 | `VFXManager`：加载 pixelfx PNG+JSON、帧播放、pivot 锚定、屏幕震动、procedural fallback |
| `assets/vfx/*.png|json` | 3 | 4 组离线烘焙的 pixelfx 静态资产（dice_roll / hit_explosion / rune_glow / score_burst） |
| `pixel_art.py` | 4.5 | 纯 Python 像素美术库：地砖 / 棋子 / 3D 骰子 / 路线导引 / 星尘 / 面板烘焙（零外部素材） |
| `main.py` | 4 / 4.5 | Pygame 主循环 + 棋盘 UI + Inspector 面板 + 特效绑定 + 交互 + `--self-test` |
| `sound_fx.py` | 4.8 | 纯 Python 程序化音频库：`array` 16-bit PCM 合成 BGM（Phrygian-Dominant 无缝循环 ~0.18）+ 7 种 SFX；headless 静默降级 no-op |
| `gameplay_preview.png` | 4.5 | `--self-test` 生成的 16 步中期对局截图（验收排版用） |
| `ai_comparison.png` | 2 | matplotlib 双子图（胜率对比 + 耗时/节点数） |

---

## §3 本机运行环境

| 项 | 值 |
|---|---|
| 解释器 | `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`（Python 3.12） |
| 已装包 | pygame 2.6.1, matplotlib |
| 默认 `python` | MSYS2 Python 3.14（无 pip，不能装包）——**跑本项目必须用上面的 3.12 全路径** |
| Node | v26.2.0（仅 Phase 3 离线烘焙用过，临时克隆 `%TEMP%\pixelfx_exporter` 已删除） |

### 复现命令

```bat
:: Phase 1 断言自测 + 随机对局
"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" pixel_dice_ur\game_state.py

:: Phase 2 三组 200 局对战 + 深度研究 + 生成 ai_comparison.png
"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" pixel_dice_ur\evaluate_ai.py

:: Phase 3 无头自检（真实资产 + spawn/update/draw + 回退）
"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" pixel_dice_ur\vfx_manager.py

:: Phase 4 打开真实窗口游玩（P1 人类 vs P2 AI）
"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" pixel_dice_ur\main.py

:: Phase 4 无头自检 + 生成 gameplay_preview.png
"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" pixel_dice_ur\main.py --self-test
```

---

## §4 Phase Log（Append-Only）

### Phase 1 — `game_state.py`（commit `d816c49`）✅ 完成

- **交付**：`GameState` 类 6 个方法（`__init__` / `clone` / `roll_dice` / `get_legal_moves` / `apply_move` / `is_terminal` + `get_winner`）
- **关键设计**：
  - `clone` 用列表切片 `self.p1_pieces[:]` 而非 deepcopy（高频调用优化）
  - `apply_move` 返回 `(next_state, event_info)`；`event_info` = `{"captured": bool, "bonus_turn": bool, "scored": bool, "target_tile": int}`，供 UI 触发特效
  - `roll_dice` 用 CDF 累积分布取点（0.25 / 0.75 分界）
- **规则要点**：
  - 吃子：进入 3..7 战区格且敌方棋子在此格 → 敌方棋子退回 0
  - 符文格（4, 8）：己方棋子到达 → 额外回合；敌方棋子占据 4 → 己方不可入
  - 终点（10）：必须精确到达，不得 overshoot
  - 己方棋子挡路：目标格有己方棋子 → 该子不可走
- **验证**：断言自测全通过（克隆隔离、掷骰合法性、吃子回退、符文格连动、护盾格禁入、己方挡路、终局判定）+ 随机模拟整局正常终局

---

### Phase 2 — `ai_engine.py` + `evaluate_ai.py`（commit `363dc47`）✅ 完成

- **交付**：三种 Agent + 启发式评估 + 200 局实验脚本
- **启发式权重**（`ai_engine.py` 模块顶部常量）：

  | 常量 | 值 | 用途 |
  |---|---|---|
  | `WIN_SCORE` | 1000.0 | 终局值，压倒所有局面项 |
  | `FINISH_WEIGHT` | 120.0 | 到达终点的权重（Set so finishing always outweighs sitting on tile 4） |
  | `PROGRESS_WEIGHT` | 6.0 | 每格前进 × 6 |
  | `SHIELD_BONUS` | 18.0 | 占据 4 号护盾格的额外加分 |
  | `DANGER_PENALTY` | 14.0 | 暴露惩罚，按 `DICE_PROBS[dist]` 加权（棋子在 3/5/6/7 且敌方在后方 1~3 格） |
  | `BONUS_TURN_REWARD` | 4.0 | GreedyAgent 额外回合小额奖励（< PROGRESS_WEIGHT × 3 = 18，不主导） |

- **统一接口**：`choose_move(state) -> (best_move: int|None, move_scores: dict[int,float], stats: {"nodes":int,"time_ms":float})`
- **三种 Agent**：
  - `GreedyAgent`：单步展开 + 静态估值
  - `DeterministicMinimaxAgent(depth=4)`：Alpha-Beta，未来固定 `dice_roll=2`（对照组）
  - `ExpectiminimaxAgent(depth=4)`：Chance 节点按 `DICE_PROBS` 加权 + P1 视角共享值 + Transposition Table
- **实验结果（三组 200 局对称对战）**：

  | Matchup | A 胜 | B 胜 | 单步耗时 A / B |
  |---|---|---|---|
  | Expectiminimax d4 vs Greedy | 113 (56.5%) | 87 (43.5%) | 4.66 ms / 0.02 ms |
  | Expectiminimax d4 vs Minimax d4 | 115 (57.5%) | 85 (42.5%) | 4.98 ms / 0.17 ms |
  | Minimax d4 vs Greedy | 90 (45.0%) | 110 (55.0%) | 0.18 ms / 0.02 ms |

- **深度研究（Expectiminimax vs Greedy，每深度 25 局）**：

  | depth | 平均耗时 | 最大耗时 | 平均节点数 |
  |---|---|---|---|
  | 2 | 0.13 ms | 0.82 ms | 7 |
  | 3 | 0.78 ms | 3.74 ms | 48 |
  | 4 | 4.83 ms | 17.58 ms | 307 |

- **结论**：d4 单步平均 4.83ms、最坏 17.6ms，远低于 50ms 预算（TT 起效）；Expectiminimax 同时压制另两算法，印证建模 Chance 节点的必要性。
- **图表**：`pixel_dice_ur/ai_comparison.png`

---

### Phase 3 — 4 组 pixelfx 资产 + `vfx_manager.py`（commit `cc4d987`）✅ 完成

- **交付**：`VFXManager` 类 + 4 组 PNG+JSON 资产
- **资产表**：

  | 场景文件 | pixelfx 预设 | PNG 尺寸 | 单帧 | 帧数 | fps | loop | pivot |
  |---|---|---|---|---|---|---|---|
  | `dice_roll` | `arcane/mana-burst` | 1456×1200 | 208×150 | 55 | 30 | 否 | [104,124] |
  | `hit_explosion` | `explosions/small-explosion` | 3600×3360 | 300×240 | 163 | 30 | 否 | [150,196] |
  | `rune_glow` | `arcane/rune-circle` | 1360×1200 | 136×100 | 120 | 30 | 是 | [68,80] |
  | `score_burst` | `ui/confetti` | 1800×1680 | 200×140 | 103 | 30 | 否 | [100,126] |

- **JSON Schema 要点**：
  - 每帧 `frame.x/y` = PNG 网格裁剪坐标；`duration` = ms（≈33ms = 30fps）
  - `meta.pixelfx.pivot` = 特效原点在单帧内的锚点（居中摆放）
  - `meta.pixelfx.loop` = 是否循环播放
  - `meta.image` 保留原预设名（如 `mana-burst.png`），`vfx_manager.py` **按实际文件名加载并忽略该字段**
- **`VFXManager` 接口**：

  ```python
  __init__(self, assets_dir=None, default_scale=0.65)
  spawn(self, effect_name, x, y, loop=False, max_duration_ms=None, scale=None) -> ActiveEffect
  trigger_shake(self, duration_ms=180, intensity=5)
  update(self, dt_ms)
  get_shake_offset(self) -> (ox, oy)
  draw(self, surface, offset=(0, 0))   # 内部已叠加 _shake_ox/_oy
  clear(self)
  ```

- **行为要点**：
  - 震屏预设：`hit_explosion` → (220ms, 6px)；`score_burst` / `rune_glow` → (120ms, 3px)
  - `rune_glow` 未显式 `loop=True` 时自动 `max_duration_ms=1500` 防永久残留
  - pivot 随 scale 同比缩放；绘制锚定 `(x - scaled_pivot_x, y - scaled_pivot_y)`
  - `pygame.transform.scale`（nearest）保持锐利像素边缘
  - 缺失 PNG → procedural fallback（48×48 放大 2×，12 帧硬边缘，33ms 帧间隔，中心 pivot）
- **验证**：`python pixel_dice_ur/vfx_manager.py` 全断言通过（真实资产加载、spawn/update/draw、吃子震屏、loop 存活 6.4s、空目录回退）

---

### Phase 4 — `main.py`（commit `67acf00`）✅ 完成

- **交付**：Pygame 主循环 + 完整 UI + 特效绑定 + `--self-test`
- **署名**：`AUTHOR_NAME` / `STUDENT_ID` 常量 → 窗口标题 + 顶栏 `BANNER_TEXT`
- **窗口**：1024×640 @ 60FPS，三区布局
  - 顶部 48px：左=署名横幅；右=`[AI: <算法名>]` 循环切换 + `[New Game (R)]`
  - 左侧 650px：3 行 × 6 列网格（地砖 84×84），`0..10` 逻辑格映射
    - P1（青蓝/金）走上排 → 中排战区 → 上排冲刺；P2（绯红/紫）上下对称
    - 4 号格金色护盾符文、10 号终点绿心圣坛、双方 "Scored: X/3" 计数
  - 右侧 374px：`AI DECISION INSPECTOR`（算法/节点/耗时/优势条/候选分表/[Hint]）+ `DICE & BATTLE LOG`（像素骰子/ROLL 按钮/概率/6 条日志）
- **交互**：
  - 合法棋子高亮脉冲；Hover 半透明预览目标格（吃子红 / 符文金 / 普通绿）
  - 点棋子 / 点目标格 / `1/2/3` 数字键走子；`Space` 掷骰；`R` 重开
  - 无合法走法 → "Turn skipped" + 700ms 自动切回合
  - 棋子 180ms 像素插值；AI 回合 450ms 节奏
- **特效绑定**：

  | 事件 | 触发 | 参数 |
  |---|---|---|
  | 掷骰 | `roll_dice()` | `spawn("dice_roll", 骰子中心, scale=0.55)` |
  | 吃子 | `event["captured"]` | `spawn("hit_explosion", 战区格中心, scale=0.65)` |
  | 符文 | `event["bonus_turn"]` | `spawn("rune_glow", 符文格中心, scale=0.75)` |
  | 得分 | `event["scored"]` | `spawn("score_burst", 终点格中心, scale=0.75)`；胜利再连放 2 发 |

- **⚠️ 震屏偏移**：渲染时用 `vfx.get_shake_offset()` 偏移棋盘/棋子，`vfx.draw(screen, (0, 0))` 传 `(0,0)`——内部已叠加 shake，不重复传入避免双倍震动。
- **`--self-test`**：`SDL_VIDEODRIVER=dummy`，30 步 AI vs AI，全 UI 渲染 + 4 种特效强制出现，保存 `gameplay_preview.png`

---

### Phase 4.5 — 交互 Bug 修复 + 像素美术重制（commit `8025ebe`）✅ 完成

- **交付**：4 个实机 bug 修复 + `pixel_art.py` 新增 + `main.py` 升级

#### 4 个 Bug 修复

| # | Bug | 修复 |
|---|---|---|
| 1 | `NameError: WAR_END`（悬停合法棋子闪退） | 顶部 `from game_state import ... WAR_END ...`；self-test 模拟全部人类交互分支 |
| 2 | 落点预览画在 `flip()` 后不可见；只能点棋子 | `draw_target_preview` 移入 `render()` 内 `flip()` 前；`on_click` 新增点预览格走子 |
| 3 | 起点 3 枚棋子重叠（`[0,0,0]` 同心） | 0 号改为 3 槽位备战托盘（P1/P2 RESERVE）；10 号改为 3 槽位得分托盘（P1/P2 SCORED）；去掉无意义 4 格，工字形拓扑 |
| 4 | `Hint: ON` 假开关 | `hint_on=True` + P1 选择回合 → Inspector 顶部青色 `[HUMAN HINT]` + 候选分 + `[RECOMMENDED]`；掷骰落地自动重算 |

#### `pixel_art.py` 像素美术库（纯 Python，零外部素材）

| 模块 | 说明 |
|---|---|
| 地砖贴图 | 28×28 像素级 → 3× 最近邻 → 84×84，启动一次烘焙。5 种：P1/P2 通道砖、交战区砖、符文护盾格、终点圣坛 |
| 路线导引层 | 烘焙在棋盘底层的虚线 + 像素箭头（备战槽→1→2→3..7→8→9→10） |
| 立体像素棋子 | 40×40 预渲染（投影 + 底座 + 金属包边 + 高光 + 数字 1/2/3） |
| 3D 像素骰子 | 72×72 等距立体；ROLL 时 260ms 骰面跳动 + 弹跳，定格瞬间爆开 dice_roll |
| 氛围背景 | 30 颗缓慢上浮闪烁的像素星尘 |
| 浮雕 UI 面板 | 双层暗金镶边 + 四角铆钉 + 渐变标题；按钮 Hover/禁用态；状态横幅 |

- **验证**：`main.py --self-test` 输出
  ```
  [self-test] interaction QA passed (Hint: ON, hover preview, target-cell click, AI button, piece click)
  [self-test] rendered 16 fast steps; preview saved to ...\pixel_dice_ur\gameplay_preview.png
  [self-test] game over=False, winner=0, turns=22
  [self-test] all main.py UI checks passed
  ```

---

### Phase 4.6 — 正常模式 4 个严重 Bug 精准修复（commit `f09d815`）✅ 完成

- **交付**：`main.py` + `pixel_art.py` 修复，`gameplay_preview.png` 重新生成
- **4 个 Bug 与修复**：

  | # | Bug | 修复 |
  |---|---|---|
  | 1 | `draw_board` 符文光晕 `tier = 1 + (self.pulse // 10) % 3 if self.pulse else 1`——`self.pulse` 是 float，离开 0.0 后产生 float 索引 → `TypeError: list indices must be integers or slices, not float` 第一帧崩溃（fast=True 时 pulse 恒 0 才侥幸不崩） | `tier = 1 + int(self.pulse * 2) % 3`（整数索引，随 pulse 平滑切换 1/2/3 档呼吸）；同时删除 `main.py` 顶部重复的第二个 `import math` |
  | 2 | `fast=False` 下 AI 走完第一步永久卡死：`do_ai_move()` 只设 `ai_moved=True` 从不切 phase → 永远卡在 `"ai_think"`；且进入 `ai_think` 时从不重置 `ai_roll_done` / `ai_moved` / `phase_ms` | 新增统一入口 `_enter_phase(name)`：一次切 phase + 重置 `phase_ms=0` + `ai_roll_done=False` + `ai_moved=False`；`commit_roll` / `human_move` / `skip_wait` 分支全部改走 `_enter_phase`；`do_ai_move()` 末尾：`current_turn==2`（符文 Bonus Turn）→ `_enter_phase("ai_think")` 继续下一轮，否则 → `_enter_phase("human_await_roll")` 交还人类。`reset()` 末尾也走 `_enter_phase` 保证标志一致 |
  | 3 | 左半屏 3 处坐标问题：A) `P1_DOCK`(x=245..501) 与 `P1_TRAY`(x=493..613) 横向重叠 8px；B) `_bake_dock` 硬编码 48px 槽位（总宽 160px）在 120×54 托盘上越界被裁，`tray_slot_center` 公式 `3*36+16=124>120` 也超宽；C) `draw_turn_banner` 画在 `y=514` 正好压在 `P2_DOCK`(482..558) 正中间挡住 P2 备战棋子 | 重排左侧 650px 面板：`GRID_Y` 218→228；`TURN_BANNER_Y = BANNER_H+14`（顶部横幅，离所有托盘 ≥56px）；`P1/P2_DOCK = (GRID_X+140, 上/下行, 200×72)`，`P1/P2_TRAY = (GRID_X+360, 上/下行, 164×72)`，上行 y=144 / 下行 y=494（494+72=566<640），横竖间距均 ≥12px 零重叠；`pixel_art` 新增模块级 `slot_centers(rect, slot_size, gap)` 共享槽心公式，`_bake_dock(rect, label, accent, slot_size=44, gap=8)` 按传入参数动态居中烘焙槽位，main.py 的 `dock_slot_center`/`tray_slot_center` 改为调用同一公式（备战槽 44/10、得分槽 44/8），棋子与烘焙凹槽永不漂移 |
  | 4 | `--self-test` 全走 `fast=True`（绕过真实 `dt_ms` 与状态机），掩盖了 Bug 1/2 | `self_test()` 新增 part 4：`fast=False` + `reset()` 后，`human_roll()` → 40×`update(50)` 走完 `ROLL_ANIM_MS` → 断言 phase ∈ {human_await_move, skip_wait} → `human_move(legal[0])` → ≤400 帧推进 AI 完整回合（掷骰翻滚/走子/覆盖 AI 连续回合），断言最终 `current_turn==1` 且 `phase=="human_await_roll"` 且 `pulse>0`，全程渲染零报错 |

- **参数 / 数值**：

  | 常量 | 旧值 | 新值 | 理由 |
  |---|---|---|---|
  | `GRID_Y` | 218 | 228 | 上/下行各留 12/14px 净空 |
  | `DOCK` 尺寸/位置 | 256×76 @ (245, 130)/(482) | 200×72 @ x=213, y=144/494 | 与 TRAY 横向留 20px |
  | `TRAY` 尺寸/位置 | 120×54 @ x=493 | 164×72 @ x=433, 与 DOCK 同 y | 3×44+2×8=148<164 槽位完整 |
  | 槽位 size/gap | 硬编码 48/8 | 备战 44/10、得分 44/8 | 与 `slot_centers` 单一公式一致 |
  | 回合横幅 | `y = GRID_Y+3*TILE+44` = 514 | `y = TURN_BANNER_Y = 62` | 不再遮挡 P2_DOCK |
  | glow tier | `(pulse // 10) % 3`（float 索引） | `int(pulse * 2) % 3` | 整数索引 + 更平滑的呼吸节奏 |

- **验证**（Python 3.12 全路径实测输出）：
  ```
  [self-test] interaction QA passed (Hint: ON, hover preview, target-cell click, AI button, piece click)
  [self-test] rendered 16 fast steps; preview saved to D:\PSB\...\pixel_dice_ur\gameplay_preview.png
  [self-test] game over=False, winner=0, turns=22
  [self-test] fast=False state-machine regression passed (human roll -> move -> AI roll -> AI move -> human turn)
  [self-test] all main.py UI checks passed
  ```
  - `game_state.py` / `vfx_manager.py` 基线自检同步回归通过
  - 新 `gameplay_preview.png` 已目检：横幅置顶、P1/P2 备战+得分托盘零重叠、44px 槽位棋子居中无裁剪、Inspector/骰子面板正常、4 组特效无越界遮挡

- **决策记录**：
  - 槽位几何唯一真源放 `pixel_art.slot_centers`（烘焙 + 锚点共用），main.py 只保留尺寸常量 `DOCK_SLOT/TRAY_SLOT` —— 任何一侧改尺寸都必须在注释里同步另一侧
  - AI 无合法走法时 `commit_roll(2)` 直接调 `do_ai_move(None)`，其内部末尾的 phase 切换保证 `update()` 不会重复触发（`ai_moved` 已置 True 且 phase 已离开 `ai_think`）
  - 回归测试窗口 ≤400 帧 × 50ms：足够覆盖 AI_ROLL_WAIT(450)+ROLL_ANIM(260)+AI_MOVE_WAIT(450)+slide(180) 的完整 AI 回合链，且保证不会打到终局
- **遗留 / 后续**：无

---

### Phase 4.7 — 全面重制版 main.py + pixel_art.py（commit `58275e1`）✅ 完成

- **交付**：规划者重制的 `main.py` + `pixel_art.py` 落地（覆盖 4.6 版本），重新生成 `gameplay_preview.png`
- **关键变化**（相对 4.6）：
  - **布局**：`GRID_Y` 228→188；备战/得分托盘改为 236×74 对称分布（左=RESERVE、右=SCORED，各离网格 14px）；新增底部 `LEGEND_RECT`（6 列宽 × 68px）规则/路线速查条
  - **路线导引**：S 形赛道方向箭头改为 RGBA chevron 风格（`_dash` 带描边），绘制在**地砖之上**保证跨格接缝 100% 可见；geo 新增 `shared_way`（战区横向导引，金色）
  - **得分动画**：到达 10 号格时棋子走两段插值 `from → 金圣坛(1,5) → 得分槽`（`SLIDE_MS × 1.6`），得分瞬间圣坛 + 槽位各爆一发 `score_burst`
  - **槽位几何**：唯一真源更新为 `pixel_art.slot_center_in_rect(rect, slot_idx, slot_size=44, gap=12)`（托盘 44/12），烘焙凹槽与棋子锚点共用；`_bake_dock` 槽内新增 `#1/#2/#3` 编号暗字
  - **交互**：`_pick_human_piece_at` 统一「点棋子 / 点目标格 / 点得分托盘」三条走子路径；`target_cell_of` 越界返回 None（防 `KeyError: 12`）；hover 高亮可走的目标格
  - **UI 文本**：`get_font` / `_font` 改用 `SysFont("consolas,verdana,arial")` 锐利字体；Inspector / 横幅 / 日志文案全面英文化重写（Advisor Hint、Board Eval、Battle Events）
  - **状态机**：保留 4.6 的 `_enter_phase` 统一入口 + `do_ai_move` 末尾交还控制权，未改动；fast 路径 P1 无走法时补了 `ai_think` 切换
- **验证**（Python 3.12 全路径实测输出）：
  ```
  [self-test] Part 1 passed: scoring hover guard + real-time human/AI cycle verified!
  [self-test] Part 2 passed: Advisor Hint, hover preview, and target-tile click verified!
  [self-test] Part 3 passed: saved preview to ...\pixel_dice_ur\gameplay_preview.png
  ```
  - `game_state.py` / `vfx_manager.py` 基线自检同步回归通过
  - 新 `gameplay_preview.png` 已目检：四托盘对称零重叠、S 形箭头清晰（青 P1 / 绯 P2 / 金战区）、规则条无越界
- **决策记录**：
  - 附件 `main.py` 第 130 行有一处变量名笔误（`p1_ entry_way` 中间空格 → SyntaxError），落地前已修正为 `p1_entry_way`
  - `slot_center_in_rect` 槽位 44px / gap 12px（236px 托盘：3×44+2×12=156 居中），取代 4.6 的 44/10 与 44/8 双规格
- **遗留 / 后续**：无

---

### Phase 4.8 — 终极打磨：程序化音频 + 圣殿夜空 + UI 质感（commit `1dc14c7`）✅ 完成

- **交付**：新增 `sound_fx.py`（纯 Python 程序化音频，零外部 .wav/.mp3）；`main.py` + `pixel_art.py` 升级（午夜圣殿背景、皇家棋盘边框、4 个动画火盆、浮动战斗文字、Match Summary 结算面板、顶栏/LEGEND/Battle Log 打磨）；`gameplay_preview.png` 重新生成
- **关键设计 / 接口**：
  - `sound_fx.py` 新 API：`init_audio()->bool` / `start_bgm()` / `play(name)` / `toggle_mute()->bool` / `is_muted()` / `is_enabled()`；7 个 SFX（dice_tick/dice_land/move/capture/bonus/score/win）+ 1 条 BGM
  - BGM：`_build_bgm(n)` 一次烘焙 ~9.7s（44 beat）无缝循环；D2 drone pad + Phrygian-Dominant（D Eb F# G A Bb C）motif + root-note bass pluck；pad/LFO 用整数周期数保证 loop 点无缝；通道音量 0.18
  - SFX 波形：`_tone`（tri/sine 扫频 + 指数衰减）/ `_noise`（一阶低通白噪 + 指数衰减）/ `_chain`（拼接琶音链）；全部 `array('h')` 16-bit signed PCM → `pygame.mixer.Sound(buffer=)`
  - 音频守卫：`init_audio()` 强制 mixer = (44100, -16, 1)；任何异常捕获后 `_ENABLED=False`，`play/start_bgm/toggle_mute` 全部静默 no-op
  - `pixel_art.py` 新增：`_bake_cityscape`（午夜蓝紫渐变 + 低对比度巴比伦砖墙 + ziggurat 剪影，半分辨率烘焙 2× 放大）、`_bake_casing`（588×348 皇家黑曜石/暗金边框，30px 边距 + 四角金饰 + 边中罗盘钉）、`_bake_brazier_frame(f)` ×4 帧 + `_bake_brazier_glow(f)` ×4 帧（128×128 暖橙光晕）
  - `main.py` 新增：`draw_braziers`（棋盘 4 个空格 concave corner 动画火盆，`int(pulse*3)%4` 切帧）、`draw_floats`（浮动战斗文字 ~900ms 上浮 + 黑描边）、`update()` 内 float 生命周期管理、`apply_and_animate` 绑定 4 种 SFX + 生成 3 种 float、`start_roll` 绑定 dice_tick、`commit_roll` 绑定 dice_land、`draw_game_over` 升级为 MATCH SUMMARY（FINAL SCORE 3-0、CAPTURES、BONUS TURNS、total turns）、`on_click` 绑定 `btn_sound`、`run()` 绑定 M 键
- **参数 / 数值**：
  | 常量 | 值 | 用途 |
  |---|---|---|
  | `SR` | 44100 | 音频采样率（mono 16-bit） |
  | `BGM_SECONDS` | 9.7 | 循环长度（44 beat × ~0.22s） |
  | `BGM_VOLUME` | 0.18 | 背景音乐通道音量 |
  | 火盆帧切 | `int(pulse*3)%4` | ~6 fps 火焰闪烁 |
  | float 生命周期 | 900 ms / 26 px 上浮 | 战斗文字上浮 + 淡出 |
  | 顶栏按钮 | `[Sound: ON (M)]` 160px / `[AI]` 170px / `[New Game]` 140px / 12px 间距 | 从右往左布局，左 banner 保留 ≥30px 安全距 |
  | LEGEND 首行 | `ROUTE: Start -> 1 -> 2 -> War (3..7) -> Sprint (8*->9) -> Shrine (10)` | ≤52 字符，13px 字体下不越界（右余量 ≥14px） |
  | Battle Log | 开场 `Ready! Press SPACE to roll.`；单行 >176px 时在空格处截断 | 永不切半词 |
- **验证**（Python 3.12 全路径实测输出）：
  ```
  [self-test] Part 1 passed: scoring hover guard + real-time human/AI cycle verified!
  [self-test] Part 2 passed: Advisor Hint, hover preview, and target-tile click verified!
  [self-test] Part 3 passed: saved preview to ...\pixel_dice_ur\gameplay_preview.png
  [self-test] Part 4 passed: audio silent-degradation + floating text lifecycle verified!
  ```
  - `game_state.py` / `vfx_manager.py` 基线自检同步回归通过
  - `sound_fx.py` 独立自检：真实设备 `enabled=True`，`SDL_AUDIODRIVER=weird_nonexistent_driver_xyz` 强制失败 `enabled=False` 且全程零异常
  - 新 `gameplay_preview.png` 已目检：午夜蓝紫夜空 + 城墙浮雕、皇家黑金边框、4 火盆、浮动文字三色（crimson/gold/emerald）、MATCH SUMMARY 面板（3-0 / CAPTURES 2/1 / BONUS 3/1 / 16 turns）、顶栏 3 按钮零重叠、LEGEND 无越界、Battle Log 开场 `Ready! Press SPACE to roll.`
- **决策记录**：
  - 火盆位置选「棋盘工字形 4 个空 concave 格」（row 0/2 × col 2/3），非 dock 外侧 —— 严格贴合 spec 且零 UI 遮挡
  - BGM pad / LFO 使用整数周期数（`two_pi * int(hz * n/SR) / n`）保证 loop 接缝相位 100% 对齐
  - 所有 SFX 用 `pygame.mixer.Sound(buffer=pcm.tobytes())` 一次性构造，零运行时合成开销
  - 顶栏按钮宽度由右往左推导（`btn_new` x=`WIN_W-12-140`；`btn_ai` x=`btn_new.x-gap-170`；`btn_sound` x=`btn_ai.x-gap-160`），banner 左对齐 14px 起，零覆盖
  - MATCH SUMMARY 用 `self.log` 中 `"P? #N -> ... (CAPTURED!)"` 计数 captures；bonus 计数用 `self.bonus_count` 字典（`reset()` 清零）
- **遗留 / 后续**：无

> [修订 2026-11-13]（commit `8e02b5c`）：实机截图发现 MATCH SUMMARY 数值错位——原实现把 P1/P2 两个数字拼成**一整串**按整串宽度居中在 `box.centerx`，且 y 比标签高 6px，导致数字飘到 "FINAL SCORE" 标签正上方。已改为固定三列表格：标签列左对齐（`box.x+44`），P1 列（青）/ P2 列（绯红）数字各自居中在自己的表头下方（`centerx-70` / `centerx+80`），同行同基线。self-test 4 Part 全通过，`gameplay_preview.png` 重新生成并目检对齐正确。

---

## §5 Phase Log 追加模板

每完成一个新 Phase，在 §4 末尾追加：

```markdown
### Phase N — <一句话标题>（commit `<short-sha>`）✅ 完成 / 🚧 进行中

- **交付**：<列出新增/修改的文件及其职责>
- **关键设计 / 接口**：<核心 API、常量、算法要点>
- **参数 / 数值**：<关键调参及其工程理由>
- **验证**：<self-test 命令 + 实际输出摘要>
- **决策记录**：<本 Phase 做出的技术选择及理由（如选 A 不选 B）>
- **遗留 / 后续**：<未解决或需后续处理的事项>
```

**规则**：
- 只追加，不删改已有条目（可加 `[修订 YYYY-MM-DD]` 小注）
- 必须附 commit SHA
- 验证证据必须是**实际运行输出**，不得凭记忆填写

---

## §6 待决策 / 下一步任务

> 每次 Phase 完成后更新本节。

**当前状态（截至 Phase 4.8 完成）**：

- [x] Phase 1–4.5 全部完成并自检通过
- [x] 4 个实机 bug 修复
- [x] 像素美术重制达到独立游戏级
- [x] Phase 4.6：正常窗口模式（fast=False）4 个严重 bug 修复 + 真实帧率状态机回归测试
- [x] Phase 4.7：规划者重制版 main.py / pixel_art.py 覆盖落地（S 形箭头压地砖、两段圣坛→得分槽插值、LEGEND 速查条、SysFont 锐利字体）
- [x] Phase 4.8：程序化音频（BGM + 7 SFX，headless 静默降级）+ 圣殿夜空 / 皇家边框 / 4 动画火盆 + 浮动战斗文字 + MATCH SUMMARY 结算 + 顶栏 3 按钮 / LEGEND / Battle Log 打磨；self-test 新增 Part 4 音频降级 + float 生命周期回归
- [x] Phase 4.8 修订（`8e02b5c`）：MATCH SUMMARY 数值错位修复（三列固定对齐，见 §4 修订小注）
- [ ] **下一步**：（规划者在此写新任务）

**已确认决策（不可回退）**：
- `score_burst` 选用 `ui/confetti`（103 帧多彩彩纸）而非 `pickups/collect-burst`
- `meta.image` 保留原预设名，`vfx_manager.py` 按实际文件名加载并忽略该字段
- 棋盘拓扑：工字形（去掉 4 个无意义侧行格）
- 备战/得分各 3 槽位独立展示；槽位几何唯一真源 = `pixel_art.slot_centers`（备战 44/10、得分 44/8）
- 状态机所有 phase 切换必须走 `_enter_phase()`（统一重置 phase_ms / ai_roll_done / ai_moved）

**开放问题**：
- （无）

---

## §7 已知坑 / 注意事项（Lessons Learned）

| # | 坑 | 解法 | 来源 |
|---|---|---|---|
| 1 | `main.py` 漏导入 `WAR_END` → 悬停即 `NameError` 闪退 | 顶部 `from game_state import ... WAR_END ...`；self-test 覆盖全交互分支 | Phase 4.5 bug#1 |
| 2 | 预览画在 `display.flip()` 后不可见 | `draw_target_preview` 必须在 `flip()` 之前调用 | Phase 4.5 bug#2 |
| 3 | 震屏偏移传两次导致双倍抖动 | `vfx.draw(screen, (0,0))`；`draw` 内部已叠加 shake | Phase 4 |
| 4 | `rune_glow` 不传 `loop=True` 会无限循环 | `VFXManager.spawn` 默认 `loop=False`，未显式传 True 时自动 1500ms 截断 | Phase 3 |
| 5 | MSYS2 Python 3.14 无 pip，不能装包 | 必须用 `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe` | 环境 |
| 6 | pixelfx `meta.image` 是原预设名（如 `mana-burst.png`），不是实际文件名 | `vfx_manager.py` 按 `dice_roll.png` 等实际名加载，忽略 `meta.image` | Phase 3 |
| 7 | 3 枚棋子初始 `[0,0,0]` 重叠 | 备战托盘 3 槽位独立坐标展示 | Phase 4.5 bug#3 |
| 8 | `self.pulse` 是 float，`(pulse // 10) % 3` 产生 float 列表索引 → 第一帧 `TypeError`（fast=True 时 pulse 恒 0 才侥幸不崩） | 用 `int(pulse * 2) % 3`；任何用浮点驱动列表索引的地方都必须 `int()` 显式取整 | Phase 4.6 bug#1 |
| 9 | `fast=True` 的 self-test 绕过真实 `dt_ms` 与状态机，掩盖了正常模式 AI 回合卡死 | `--self-test` 必须包含一段 `fast=False` 真实帧率回归（喂 `update(50)` 走完人类+AI 完整回合链） | Phase 4.6 bug#2/#4 |
| 10 | 烘焙贴图槽位尺寸与槽心公式各写一套 → 托盘上槽位越界被裁、棋子漂移 | 槽位几何单一真源 `pixel_art.slot_centers(rect, slot_size, gap)`，烘焙与锚点共用；尺寸常量改两侧同步注释 | Phase 4.6 bug#3 |
| 11 | 无头模式（`SDL_VIDEODRIVER=dummy` / 无音频设备）下 `pygame.mixer` 初始化可能失败或 `Sound.play()` 抛错 → 音频相关调用会让 `--self-test` 崩溃 | 所有音频入口（`init_audio` / `start_bgm` / `play` / `toggle_mute`）必须 try/except 全捕获 + `_ENABLED` 标志门控；失败时静默 no-op，绝不向外抛异常 | Phase 4.8 |
| 12 | 循环 BGM 用浮点频率直接采样 → 首尾相位错位产生 loop 接缝"咔哒"声 | loop 关键振荡器（drone pad / LFO）改整数周期数（`two_pi * int(hz*n/SR)/n`）；一次性 `buffer` 烘焙整条循环，`play(loops=-1)` | Phase 4.8 |
| 13 | 顶栏 / LEGEND / Battle Log 长文本溢出容器或与相邻按钮重叠 | 顶栏按钮宽度从右往左推导并预留 ≥30px banner 安全距；LOG 行 >176px 时在空格处截断（绝不切半词）；LEGEND 首行压到 ≤52 字符 | Phase 4.8 |
| 14 | MATCH SUMMARY 把两列数值拼成整串居中 → 数字宽度不对称时整体漂移，P1 数字落在标签正上方 | 表格类排版必须拆成独立列：每列 x 坐标固定，各列文本单独居中/对齐，绝不靠空格填充拼串 | Phase 4.8 修订 |

---

## §8 术语速查

| 术语 | 含义 |
|---|---|
| 战区（War Zone） | 逻辑格 3..7（`WAR_START..WAR_END`），可触发吃子 |
| 符文格（Rune/Shield Tile） | 逻辑格 4 和 8（`SAFE_TILES`），到达得额外回合；4 号格被敌方占据时己方不可入 |
| 终点（Finish/Board End） | 逻辑格 10，必须精确到达 |
| 备战托盘（Reserve Dock） | 逻辑格 0 的 3 槽位 UI 展示区 |
| 得分托盘（Scored Tray） | 逻辑格 10 的 3 槽位 UI 展示区 |
| Chance 节点 | Expectiminimax 中按概率展开的随机层 |
| Transposition Table | 共享搜索值缓存（P1 视角，key = state hash） |
| 像素插值（Pixel Lerp） | 棋子 180ms 从 A 格滑到 B 格的帧间位置计算 |
| pivot 锚定 | 特效帧中心对齐到触发点（`x - pivot_x, y - pivot_y`） |
| Phrygian-Dominant（弗里吉亚多利亚） | D Eb F# G A Bb C 音阶，BGM 动机使用 |
| 火盆（Brazier） | 棋盘工字形 4 个空 concave 格（row 0/2 × col 2/3）中的 4 帧动画暖橙火焰像素 |
| 浮动战斗文字（Floating Combat Text） | 事件格上方 ~900ms 上浮 + 淡出的描边像素文字（吃子红 / 符文金 / 得分绿） |
