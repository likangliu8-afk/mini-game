# assets/vfx

存放从 [patch-gg/pixelfx](https://github.com/patch-gg/pixelfx) 导出的 PNG 精灵图与 JSON 时序文件。

| File | Effect | Used by |
|------|--------|---------|
| `dice_roll.png` / `dice_roll.json` | 掷骰子序列帧动画 | `vfx_manager.py` |
| `hit_explosion.png` / `hit_explosion.json` | 命中爆炸序列帧动画 | `vfx_manager.py` |
| `rune_glow.png` / `rune_glow.json` | 符文发光序列帧动画 | `vfx_manager.py` |

> 每个效果包含一张 sprite sheet（PNG）与一个时序描述文件（JSON，帧坐标 / 时长 / 播放次数）。
> 若文件缺失，`vfx_manager.py` 将回退到纯 Python 像素粒子渲染。
