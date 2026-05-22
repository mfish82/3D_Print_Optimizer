# Cascade Forge Print Log

## 2026-05-17 - skull halves.3mf
- Goal: accuracy > surface quality > minimize material use (client prototype)
- Filament: Bambu PLA Basic @BBL P2S
- Key changes:
  - `support_threshold_angle` 35° → 40°
  - `support_interface_spacing` 0.8 → 1.0mm
- Output: G:\Cascade Forge Client Projects\skull_optimized.3mf
- Outcome: [SUCCESS] — support removal successful, client approved

## 2026-05-18 - skull halves - Mold Master v1.3mf
- Goal: extreme detail + accuracy, mold master
- Filament: Polymaker PolyMax PETG
- Key changes:
  - `layer_height` 0.28 → 0.12mm
  - `support_top_z_distance` 0.12 → 0.36mm
  - `outer_wall_speed` 200 → 25mm/s
- Output: G:\Cascade Forge Client Projects\skull mold master.3mf
- Outcome: [FAILURE: supports] [PETG] [support_top_z_distance:0.12mm] — interface bonded to part
