# Bambu Studio 2.5.3.61 Reference

Printer: Bambu Lab P2S
Nozzle: 0.4mm hardened steel
Bed: Textured PEI plate

---

## Key Print Settings Locations

All settings accessible via: Process panel (right side) or Edit Process Settings

### Layer and Quality
- Layer height: Process > Quality > Layer height
- First layer height: Process > Quality > First layer height
- Seam position: Process > Quality > Seam position

### Strength
- Walls: Process > Strength > Wall loops
- Top layers: Process > Strength > Top shell layers
- Bottom layers: Process > Strength > Bottom shell layers
- Infill density: Process > Strength > Sparse infill density
- Infill pattern: Process > Strength > Sparse infill pattern

### Support
- Enable support: Process > Support > Enable support
- Support type: Auto (default), Manual
- Support on build plate only: Process > Support > On build plate only (CHECK for most prints)
- Support interface: leave default unless fine surface needed

### Temperature
- Nozzle temp: Filament settings > Nozzle temperature
- Bed temp: Filament settings > Bed temperature

---

## Base Cut (Cut Tool)

Right-click model in 3D view > Edit > Cut
OR: Select model > top toolbar > Cut icon

Set cut plane at desired Z height. Use "Keep lower part" or "Keep upper part".

Base cuts per skull project:
- Cranium front (PLA): 0.60mm
- Cranium cap (PLA): 0.28mm
- Cranium cap (PETG): 0.24mm

---

## Fix Model

Right-click model > Fix model
Bambu auto-repairs non-manifold edges. For severe mesh issues, repair in MeshLab first.

---

## Hollow

Bambu Studio does NOT have a hollow function. Use Blender Solidify modifier for hollow models.

---

## Supports — Important Notes

- "Auto, touching buildplate only" = supports generate from bed upward only
- No support material inside hollow cavities with this setting
- For skull prints: dome-side down orientation = correct for this rule

---

## Slicing Verification

After slicing, use Layer view to confirm:
- No support inside hollow cavity
- Wall count correct at thin sections
- Seam position at rear (not visible face)
- First layer adhesion adequate

---

## Multi-color / AMS

AMS2 connected. Filament slots configurable in Device panel.
For single-color prints: assign all to same filament slot.

---

## Export G-code

Slice > Send to Printer or Export Plate Sliced File
