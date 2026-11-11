"""[Phase 3] 读取 pixelfx 序列帧 + 纯 Python 像素粒子回退渲染器。

Responsibilities:
- 解析 assets/vfx/*.json 时序文件并切分 PNG sprite sheet
- 按帧驱动播放序列动画（dice_roll / hit_explosion / rune_glow）
- 文件缺失时的纯 Python 像素粒子回退渲染器
"""

# TODO(Phase 3):
# - 实现 SpriteSheetLoader(path_png, path_json)
# - 实现 EffectPlayer: update(dt) / draw(surface, x, y)
# - 实现 PixelParticleFallback（无素材时的回退粒子效果）
