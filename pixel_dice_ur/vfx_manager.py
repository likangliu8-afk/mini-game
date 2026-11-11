# Name: LAW LI KANG RAIN
# Student ID: 1904VECI
#
# Phase 3: pixelfx sprite-sheet loader + pure-Python pixel particle fallback renderer.
#
# Responsibilities:
# - parse assets/vfx/*.json timelines and slice the PNG sprite sheets
# - drive sprite-frame playback (dice_roll / hit_explosion / rune_glow)
# - pure-Python pixel particle fallback renderer when assets are missing

# TODO(Phase 3):
# - implement SpriteSheetLoader(path_png, path_json)
# - implement EffectPlayer: update(dt) / draw(surface, x, y)
# - implement PixelParticleFallback (fallback particles when assets are absent)
