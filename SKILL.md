---
name: bambu-optimizer
description: >
  Optimize Bambu Studio 3MF project files for specific print goals (strength, speed, flexibility,
  detail, surface finish). Use for any request involving a .3mf file, screenshot from Bambu Studio,
  or feedback about a past print outcome. Triggers on: "optimize", "improve settings",
  "print settings", any .3mf file reference, post-print feedback ("supports failed", "good print").
  Always use this skill for 3MF optimization requests.
---

# Bambu Optimizer

Optimize 3MF project files for your Bambu printer. Combine visual analysis, print history, and
domain expertise to propose and apply settings improvements.

**Config:** Read `config.md` in this skill directory at the start of every session. Substitute
`{skill_dir}`, `{print_log}`, `{profile_base}`, and `{printer}` throughout with the values defined
there. If `config.md` is missing, run `## MODE: setup` before any other mode.

**Script:** `{skill_dir}\apply_patch.py`
**Print log:** `{print_log}`
**Profile base:** `{profile_base}`
**Printer:** `{printer}`

---

## Mesh Pre-Flight Reference

Run before any visual analysis. No external skill needed — all domain knowledge is in this file.

### CAD vs scan detection
- **CAD**: clean parametric geometry, uniform topology, hard edges — safe for all operations
- **Scan**: organic topology, variable triangle density, wavy surfaces, photogrammetry/CT origin — treat with caution

### Scan mesh flags (surface when detected)
- Non-manifold risk → note: "Bambu will auto-repair; verify in slicer layer preview before printing"
- High poly (>500K tri) → note: "Recommend MeshLab decimation to ~200K before slicing"
- Hollowing needed → note: "Use Blender Solidify modifier — Meshmixer Hollow creates two-shell problem on scan meshes"
- Boolean needed → note: "Use Blender Boolean — Meshmixer crashes on high-poly scans"

### Correct scan mesh prep order (when flags fire)
1. MeshLab: repair non-manifold edges + fill holes
2. MeshLab: decimate to ~200K triangles if needed
3. Blender: Solidify modifier for hollowing (thickness in meters, offset -1, uncheck Rim Fill)
4. Bambu Studio: import, verify repair in slicer preview, then optimize

### Mesh prep tool quick-ref
| Need | Tool |
|------|------|
| Non-manifold repair, hole fill | MeshLab — Filters > Cleaning and Repairing |
| Hollow / solidify | Blender Solidify modifier |
| Parametric parts (posts, collars, brackets) | OpenSCAD |
| Slicer/print settings reference | `references/bambu-studio.md` in this repo |

---

## Printer & Filament Baselines

**Printer:** Bambu Lab P2S | **Nozzle:** 0.4mm hardened steel | **Bed:** Textured PEI | **Bed prep:** Glue stick before each print

### PLA Prototype (Polymaker PolyLite PLA — Cascade Forge default)
| Setting | Baseline |
|---------|---------|
| `layer_height` | 0.20mm |
| `initial_layer_print_height` | 0.20mm |
| `nozzle_temperature` | 220°C |
| `hot_plate_temp` | 65°C |
| `sparse_infill_density` | 15% |
| `sparse_infill_pattern` | grid |
| `wall_loops` | 3 |
| `support_type` | auto, buildplate only |

### PETG Master (Polymaker PolyMax PETG — mold masters, client work)
| Setting | Baseline |
|---------|---------|
| `layer_height` | 0.12mm |
| `nozzle_temperature` | 235–242°C |
| `hot_plate_temp` | 70–80°C |
| `overhang_fan_speed` | 40–60% |
| `wall_loops` | 4+ |

### TPU (flexible parts)
| Setting | Baseline |
|---------|---------|
| `nozzle_temperature` | 220–230°C |
| `hot_plate_temp` | 30–40°C |
| Retraction | minimal or off |
| All speeds | 30–40 mm/s max |

---

## MODE: optimize

Trigger: user provides 3MF path + screenshot (pasted inline) + optional goal.
Goal defaults to "general" if not stated.

### Step 1 — Mesh pre-flight
Using `## Mesh Pre-Flight Reference` and `## Printer & Filament Baselines` above — no external skill needed.

Determine from the screenshot whether the mesh is CAD or scan-derived.
- CAD: proceed to Step 2
- Scan indicators detected: surface relevant flags (non-manifold, high poly, hollow/boolean caveats) before continuing

Do not invoke any external skill. All domain knowledge is in this file.

### Step 2 — Read current settings
Run: `python "{skill_dir}\apply_patch.py" read "<3mf_path>"`

Parse JSON output. Track these keys at minimum:
- `filament_settings_id` — filament profile name (array, use index 0)
- `wall_loops` — wall count
- `sparse_infill_density` — infill percentage
- `sparse_infill_pattern` — infill pattern
- `layer_height` — layer height mm
- `initial_layer_print_height` — first layer height mm
- `enable_support` — "0" or "1"
- `support_type` — support style
- `nozzle_temperature` — array, use index 0
- `hot_plate_temp` or `hot_plate_temp_initial_layer` — bed temp

If a key is missing from the 3MF output, read the matching user profile JSON from the profile
base directory under `process\` or `filament\`.

### Step 3 — Detect and confirm filament
Show: `Detected filament: [filament_settings_id[0]]. Confirm to continue, or cancel to create/select a profile first.`
Wait for response. Cancel = exit cleanly with no files written. Confirm = proceed.

### Step 4 — Read print history
Read `{print_log}` in full.
Find entries with same filament or similar filename. Note any `[FAILURE]` tags and the settings
they name. This informs recommendations — if a setting failed before, avoid repeating it.

### Step 5 — Visual analysis
Analyze the screenshot:
- Estimate overhang angles (flag anything over 45 deg as potentially needing support)
- Identify bridge spans
- Note thin features, sharp details, or fragile geometry
- Assess surface finish expectations (visible faces vs internal structure)
- Geometry type: organic/scan vs clean CAD

### Step 6 — Generate patch
Combine: goal, current settings, filament profile, visual analysis, failure history.

**Line-by-line audit (MANDATORY).** Before generating the patch, walk every setting category in
order and explicitly evaluate each one. Do not skip a category because it "seems fine." Each
category must produce either a proposed change or an explicit "no change — [reason]" note.

Settings categories to audit in sequence:
1. **Layer / quality**: layer_height, initial_layer_print_height, initial_layer_line_width
2. **Walls**: wall_loops, wall_generator (classic/arachne), outer_wall_speed, inner_wall_speed, outer_wall_line_width
3. **Infill**: sparse_infill_density, sparse_infill_pattern, infill_speed
4. **Supports**: enable_support, support_type, support_threshold_angle, support_top_z_distance,
   support_bottom_z_distance, support_interface_spacing, support_critical_regions_only,
   support_speed, support_interface_speed, support_object_xy_distance
5. **Temperature**: nozzle_temperature, hot_plate_temp, hot_plate_temp_initial_layer
6. **Cooling**: fan_max_speed, fan_min_speed, overhang_fan_speed, slow_down_layer_time
7. **Speeds (top-level)**: outer_wall_speed, sparse_infill_speed, internal_solid_infill_speed,
   top_surface_speed, travel_speed
8. **Retraction**: retraction_length, retraction_speed (skip for TPU)
9. **First layer**: initial_layer_speed, initial_layer_infill_speed

If a key is absent from the 3MF output, check the profile base directory before skipping.

Goal guidance:
- **strength**: wall_loops 5-6, infill 35-50% gyroid, may reduce layer_height to 0.16
- **speed**: wall_loops 2-3, infill 10-15% lightning, raise sparse_infill_speed
- **flexibility** (TPU only): wall_loops 2, infill 10-20% gyroid, all speeds 30-40 mm/s
- **detail**: layer_height 0.12-0.16mm, lower outer_wall_speed, wall_generator arachne
- **surface finish**: layer_height 0.12mm, outer_wall_speed 25-30, wall_loops 4

PETG-specific: nozzle 235-242C, bed 70-80C, overhang_fan_speed 40-60%, avoid rapid cooling.
TPU-specific: nozzle 220-230C, bed 30-40C, retraction minimal or off.
PLA-specific: nozzle 215-225C, bed 60-65C.

Generate only keys that change. Attach a reason to each change.

### Step 7 — Present diff

```
PROPOSED CHANGES - [filename]
Goal: [goal] | Filament: [name] (confirmed)

PROCESS
  [setting_key]    [current] -> [proposed]    [reason]

FILAMENT
  [setting_key]    [current] -> [proposed]    [reason]

SUPPORTS
  [setting_key]    [current] -> [proposed]    [reason]

REASONING FROM HISTORY
  [paste relevant log note, or omit section entirely if no history]

Type 'approve', 'cancel', or describe adjustments.
```

### Step 8 — Approval loop
- **approve**: proceed to Step 9
- **cancel**: exit, nothing written, confirm to Mike
- **[adjustment text]**: update patch accordingly, re-present diff, loop back to Step 8

### Step 9 — Write optimized 3MF
Write the patch dict to a temp JSON file, then run:
```
python "{skill_dir}\apply_patch.py" write "<3mf_path>" "<temp_patch_path>"
```
Confirm output path from stdout. Delete the temp patch file.

### Step 10 — Auto-log
Append to `{print_log}`:

```
## [YYYY-MM-DD] - [original_filename]
- Goal: [goal]
- Filament: [detected filament]
- Key changes: [3-5 most impactful changes as brief bullets]
- Output: [full path to _optimized.3mf]
- Outcome: [PENDING]
```

Confirm: `Written: [output path]. Logged.`

---

## MODE: feedback

Trigger: "feedback: [description] on [filename]" or "that print [worked/failed]"

### Step 1 — Find log entry
Read `{print_log}`. Find entry matching the filename.

### Step 2 — Classify outcome
Ask about ALL aspects of the print — do not limit to pass/fail:
- SUCCESS: print met goal — note settings that worked especially well
- FAILURE: print failed — note what failed (settings, cause) AND any aspects that printed well
- PARTIAL: some aspects worked, others didn't — capture both sides explicitly
- CANCELLED: print stopped early — note why, where it stopped, and which settings are implicated

For FAILURE and CANCELLED: always ask "what looked good before it failed?" to extract validated signals.

### Step 3 — Append outcome line
Replace `- Outcome: [PENDING]` with structured result:

Success: `- Outcome: [SUCCESS] — [brief description]. Validated: [key settings that worked well]`
Failure: `- Outcome: [FAILURE: <what failed>] [<FILAMENT>] [<key>:<value>] — [description]. Worked: [aspects that printed well]`
Partial: `- Outcome: [PARTIAL: <what worked / what failed>] — [description]. Worked: [specifics]. Failed: [specifics with settings]`
Cancelled: `- Outcome: [CANCELLED: <reason>] [<FILAMENT>] [stopped_at:<point or %>] [<key>:<value if implicated>] — [description]. Worked: [anything that printed well before stop]`

Examples:
- `- Outcome: [FAILURE: supports] [PETG] [support_type:tree] [spacing:0.20mm] — detached at 40% height. Worked: walls clean, layer adhesion solid`
- `- Outcome: [SUCCESS] — strong bracket, no warping, supports released cleanly. Validated: support_top_z_distance:0.25mm, wall_loops:5`
- `- Outcome: [PARTIAL: walls good, top surface rough] — infill too sparse for top layer bridging. Worked: wall_loops:4 solid. Failed: sparse_infill_density too low`
- `- Outcome: [CANCELLED: spaghetti at 35%] [PLA] [stopped_at:35%] [layer_height:0.28mm] — layer shifted after support detached. Worked: first 10 layers adhesion excellent`

### Step 4 — Save log
Write updated `print-log.md`. Confirm: `Outcome logged. Will inform future [filament] runs.`

### Step 5 — Invoke improvement agent
Read `{skill_dir}\improvement_agent.md` in full and follow it.

Pass this context to the agent:
- Material: the filament name from Step 1
- Goal: the goal from the log entry
- Outcome type: SUCCESS | FAILURE | PARTIAL | CANCELLED (from Step 2)
- Date: the date from the log entry
- Outcome line: the full outcome text written in Step 3

The agent runs inline. Do not wait for user input before invoking.

---

## MODE: setup

Trigger: `config.md` is missing from the skill directory, or user says "setup".

### Step 1 — Detect skill directory
The skill directory is wherever SKILL.md was loaded from. Confirm the path.

### Step 2 — Gather config values
Ask the following questions (one message, all at once):
1. What Bambu printer model do you have? (e.g. P2S, X1C, A1, A1Mini)
2. Where is your BambuStudio user profile directory?
   - Windows default: `C:\Users\<name>\AppData\Roaming\BambuStudio\user\<numeric_id>`
   - Browse to that path and paste the full directory
3. Where should print history be logged?
   - Paste a full path to an existing markdown file, or a new path to create one

### Step 3 — Create config.md
Write `config.md` to the skill directory with the values from Step 2.
Use `config.example.md` as the template format.

### Step 4 — Confirm and continue
Confirm: `Config saved. Ready to optimize.`
Offer to run optimize or feedback mode immediately.

---

## Rules

- Never overwrite the original 3MF
- Always confirm filament before proceeding with optimize
- Always read print-log.md before generating a patch
- Delta patches only — never rewrite keys that aren't changing
- If visual analysis reveals scan mesh artifacts: invoke 3d-print-master pre-flight before settings work
- Present diff and wait for approval — never write without 'approve'
- One clarifying question at a time if needed

---

## Known Failure Patterns

<!-- Auto-updated by improvement agent. Do not edit manually. -->
<!-- Format: - [MATERIAL] [setting_key:value] → description (date) -->

---

## Material Knowledge

<!-- Auto-updated by improvement agent. Do not edit manually. -->
<!-- Each material block added after first resolved outcome. -->

### Bambu PLA Basic
- **Nozzle:** 215°C (validated 2026-05-17)
- **Bed:** not recorded in log entry
- **Validated settings for accuracy/prototype:** `support_top_z_distance` 0.28mm, `support_critical_regions_only` ON, `support_threshold_angle` 40°, `support_interface_spacing` 1.0mm
- **Notes:** Heavy Support profile used (AMS slot 2). Support removal successful on organic skull geometry (high-poly scan mesh).
- **Outcomes:** 1 total — 1 SUCCESS, 0 FAILURE, 0 PARTIAL
