---
name: bambu-optimizer
description: >
  Optimize Bambu Studio 3MF project files for specific print goals (strength, speed, flexibility,
  detail, surface finish). Use when Mike provides a 3MF file and screenshot from Bambu Studio,
  or gives feedback about a past print outcome. Triggers on: "optimize", "improve settings",
  "print settings", any .3mf file reference, post-print feedback ("supports failed", "good print").
  Always use this skill for 3MF optimization requests.
---

# Bambu Optimizer

Optimize 3MF project files for Mike's Cascade Forge P2S printer. Combine visual analysis, print
history, and domain expertise to propose and apply settings improvements.

**Script:** `C:\Users\mfish\.claude\skills\bambu-optimizer\apply_patch.py`
**Print log:** `H:\ObsidianVault\Cascade-Forge\print-log.md`
**Profile base:** `C:\Users\mfish\AppData\Roaming\BambuStudio\user\2590880668\`

---

## MODE: optimize

Trigger: user provides 3MF path + screenshot (pasted inline) + optional goal.
Goal defaults to "general" if not stated.

### Step 1 — Invoke 3d-print-master
Use the Skill tool to invoke `3d-print-master`. Load domain knowledge, pre-flight checklist,
filament profiles, and Bambu Studio reference. Run the pre-flight visual assessment on the
screenshot now. Flag any mesh concerns (scan artifacts, non-manifold indicators) before proceeding.

### Step 2 — Read current settings
Run: `python "C:\Users\mfish\.claude\skills\bambu-optimizer\apply_patch.py" read "<3mf_path>"`

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
Read `H:\ObsidianVault\Cascade-Forge\print-log.md` in full.
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
python "C:\Users\mfish\.claude\skills\bambu-optimizer\apply_patch.py" write "<3mf_path>" "<temp_patch_path>"
```
Confirm output path from stdout. Delete the temp patch file.

### Step 10 — Auto-log
Append to `H:\ObsidianVault\Cascade-Forge\print-log.md`:

```
## [YYYY-MM-DD] - [original_filename]
- Goal: [goal]
- Filament: [detected filament]
- Key changes: [3-5 most impactful changes as brief bullets]
- Output: [full path to _optimized.3mf]
- Outcome: [PENDING]
```

Tell Mike: `Written: [output path]. Logged to Cascade Forge.`

---

## MODE: feedback

Trigger: "feedback: [description] on [filename]" or "that print [worked/failed]"

### Step 1 — Find log entry
Read `H:\ObsidianVault\Cascade-Forge\print-log.md`. Find entry matching the filename.

### Step 2 — Classify outcome
- SUCCESS: print met goal, no issues
- FAILURE: print failed — note what failed and which settings are implicated
- PARTIAL: some aspects worked, others didn't

### Step 3 — Append outcome line
Replace `- Outcome: [PENDING]` with structured result:

Success: `- Outcome: [SUCCESS] — [brief description]`
Failure: `- Outcome: [FAILURE: <what failed>] [<FILAMENT>] [<key>:<value>] — [description]`
Partial: `- Outcome: [PARTIAL: <what worked / what failed>] — [description]`

Examples:
- `- Outcome: [FAILURE: supports] [PETG] [support_type:tree] [spacing:0.20mm] — detached at 40% height`
- `- Outcome: [SUCCESS] — strong bracket, no warping, supports released cleanly`
- `- Outcome: [PARTIAL: walls good, top surface rough] — infill too sparse for top layer bridging`

### Step 4 — Save log
Write updated `print-log.md`. Confirm: `Outcome logged. Will inform future [filament] runs.`

---

## Rules

- Never overwrite the original 3MF
- Always confirm filament before proceeding with optimize
- Always read print-log.md before generating a patch
- Delta patches only — never rewrite keys that aren't changing
- If visual analysis reveals scan mesh artifacts: invoke 3d-print-master pre-flight before settings work
- Present diff and wait for approval — never write without 'approve'
- One clarifying question at a time if needed
