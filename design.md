---
name: bambu-optimizer-design
description: Design spec for the Bambu Studio 3MF profile optimizer skill
metadata:
  type: project
---

# Bambu Optimizer — Design Spec
Date: 2026-05-16

## Goal

Skill that takes a Bambu Studio 3MF project file + screenshot, analyzes settings using 3d-print-master
domain knowledge and print history, proposes optimized settings as a readable diff, and on approval
writes an `_optimized.3mf` to the same directory.

## Architecture

Three layers:

```
SKILL.md (Claude orchestrator)
  ├── invoke 3d-print-master skill     ← domain knowledge + pre-flight
  ├── read H:\ObsidianVault\Cascade-Forge\print-log.md  ← past failure history
  ├── run apply_patch.py read <path>   ← extract current settings from 3MF
  ├── Claude analyzes screenshot + settings → generates patch JSON
  ├── render diff table → user approval loop
  └── run apply_patch.py write <path> <patch>  ← write _optimized.3mf
        └── append to print-log.md             ← auto-log
```

## Two Modes

### optimize (default)
Trigger: paste screenshot + provide 3MF path + optional goal string
Flow: preflight → detect filament (confirm or cancel) → read history → analyze → diff → approve → write

### feedback (post-print)
Trigger: "feedback: <outcome description> on <filename>"
Flow: find matching log entry → append structured outcome tag → no file written
Outcome tags: `[SUCCESS]`, `[FAILURE: <setting>]`, `[PARTIAL]` + filament + values

## apply_patch.py Contract

```
python apply_patch.py read <3mf_path>
  stdout: JSON of current settings from Metadata/project_settings.config

python apply_patch.py write <3mf_path> <patch_json_path>
  writes <name>_optimized.3mf to same directory
  delta only — writes changed keys, not full profile dump
  never overwrites original
  backs up original settings as comment in log
```

## Filament Detection

Read `filament_settings_id` from project_settings.config.
Show: "Detected: Polymaker PETG HF — confirm? (y/cancel)"
Cancel exits cleanly with message to create profile first.

## Diff Format

```
PROPOSED CHANGES - bracket.3mf
Goal: strength | Filament: Polymaker PETG HF (confirmed)

PROCESS
  wall_loops              3  →  5     stronger perimeters
  sparse_infill_density  15% → 40%   load-bearing
  sparse_infill_pattern  grid → gyroid  isotropic strength

FILAMENT
  nozzle_temperature     235 → 240   better layer bonding for PETG

SUPPORTS
  enable_support         off → on    ~55 deg overhang detected
  support_type           normal → tree  easier removal

REASONING FROM HISTORY
  [note from print-log.md if relevant]

Type 'approve', 'cancel', or describe adjustments.
```

## print-log.md Structure

```markdown
## 2026-05-16 - bracket.3mf
- Goal: strength
- Filament: Polymaker PETG HF
- Key changes: wall_loops 3→5, infill 15→40% gyroid, tree supports
- Output: C:\clients\smith\bracket_optimized.3mf
- Outcome: [PENDING]
```

Feedback mode appends outcome line:
```
- Outcome: [FAILURE: supports] [PETG] [tree] [spacing:0.20mm] — detached at layer 40
```

## Files

```
C:\Users\mfish\.claude\skills\bambu-optimizer\
  SKILL.md          — orchestrator Claude reads and follows
  apply_patch.py    — Python: read/write 3MF ZIP
  README.md         — usage instructions
```

## Integration Points

- **3d-print-master**: invoke at start of every optimize run for domain knowledge, pre-flight checklist,
  filament profiles, and Bambu Studio settings reference
- **print-log.md**: read before generating patch; write after approval
- **Profile JSONs**: `C:\Users\mfish\AppData\Roaming\BambuStudio\user\2590880668\process\` and `filament\`
  read for baseline values when project_settings.config is sparse

## Constraints

- Never overwrite original 3MF
- Bambu Studio can be open during 3MF write (writing new file, not in-use file)
- Delta writes only — preserve inheritance chain
- Array values in profile JSONs: `["value", "nil"]` = per-extruder format; nil = inherit from parent
- Python stdlib only for apply_patch.py (zipfile, json, shutil) — no pip installs required

## Skill Location

`C:\Users\mfish\.claude\skills\bambu-optimizer\`
Consistent with GSD at `C:\Users\mfish\.claude\get-shit-done\`
