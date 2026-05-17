# Bambu Optimizer

Optimize Bambu Studio 3MF project files for specific print goals. Reads current settings,
analyzes a screenshot visually, checks past print history, proposes changes as a diff, and
writes an optimized 3MF to the same folder on approval.

## Requirements

- Python 3.x (stdlib only, no pip installs)
- Bambu Studio 3MF project file (not a raw STL — must be saved as project from Bambu Studio)

## Workflow

1. Open Bambu Studio, load your model, set filament
2. Take a screenshot (Win+Shift+S, save or copy)
3. Open Claude Code (desktop app or VSCode)
4. Paste the screenshot (Ctrl+V)
5. Say something like:

   ```
   optimize this for strength: C:\clients\smith\bracket.3mf
   ```

   Or drag the 3MF file path into the terminal and describe your goal.

6. Confirm the detected filament
7. Review the proposed diff
8. Type `approve` to write the optimized file, or describe adjustments
9. Open `bracket_optimized.3mf` in Bambu Studio and slice

## After Printing

Log the outcome so future runs learn from it:

```
feedback: supports detached at 60% height on bracket_optimized.3mf
```

or

```
feedback: perfect print on vase_optimized.3mf — strong walls, no warping
```

## Modes

| Mode | Trigger |
|------|---------|
| optimize | Mention a .3mf path + goal, or just paste screenshot and say "optimize" |
| feedback | Start with "feedback:" followed by outcome description and filename |

## File Locations

| Item | Path |
|------|------|
| Skill | `C:\Users\mfish\.claude\skills\bambu-optimizer\` |
| Python script | `apply_patch.py` in above directory |
| Print log | `H:\ObsidianVault\Cascade-Forge\print-log.md` |
| Process profiles | `C:\Users\mfish\AppData\Roaming\BambuStudio\user\2590880668\process\` |
| Filament profiles | `C:\Users\mfish\AppData\Roaming\BambuStudio\user\2590880668\filament\` |

## Goal Reference

| Goal | What changes |
|------|-------------|
| strength | More walls (5-6), higher infill (35-50% gyroid), possibly finer layers |
| speed | Fewer walls (2-3), lower infill (10-15% lightning), higher speeds |
| flexibility | TPU mode: 2 walls, 10-20% gyroid, all speeds 30-40 mm/s |
| detail | 0.12-0.16mm layers, slower outer wall, arachne wall generator |
| surface finish | 0.12mm layers, slow outer wall (25-30 mm/s), more walls |
