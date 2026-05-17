# Bambu Optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that reads a Bambu Studio 3MF, analyzes it with screenshot + print history, proposes optimized settings as a diff, and writes an `_optimized.3mf` on approval.

**Architecture:** Two-layer. Python script (`apply_patch.py`) handles all 3MF file I/O via stdlib `zipfile` + `json`. Claude (SKILL.md) handles visual analysis, settings reasoning, diff presentation, and orchestration. Clean interface: script reads/writes; Claude decides what to change and why.

**Tech Stack:** Python 3.x (stdlib only — zipfile, json, shutil, tempfile, pathlib), Markdown (SKILL.md), pytest for script tests.

---

## File Map

```
C:\Users\mfish\.claude\skills\bambu-optimizer\
  apply_patch.py     — 3MF read/write. Two modes: read (stdout JSON) and write (apply delta patch).
  SKILL.md           — Claude orchestrator. Defines the optimize and feedback workflows.
  README.md          — Usage instructions for Mike.
  design.md          — Design spec (already exists).
  plan.md            — This file.
  tests\
    test_apply_patch.py  — pytest tests for apply_patch.py
    conftest.py          — shared fixtures
```

---

## Task 1: Test infrastructure and fixtures

**Files:**
- Create: `C:\Users\mfish\.claude\skills\bambu-optimizer\tests\conftest.py`
- Create: `C:\Users\mfish\.claude\skills\bambu-optimizer\tests\test_apply_patch.py`

- [ ] **Step 1.1: Create tests directory**

```powershell
New-Item -ItemType Directory -Force "C:\Users\mfish\.claude\skills\bambu-optimizer\tests"
```

- [ ] **Step 1.2: Create conftest.py with shared fixtures**

```python
# C:\Users\mfish\.claude\skills\bambu-optimizer\tests\conftest.py
import json
import zipfile
import pytest
from pathlib import Path

CONFIG_PATH = "Metadata/project_settings.config"

SAMPLE_SETTINGS = {
    "filament_settings_id": ["Polymaker PETG HF @BBL P2S 0.4 nozzle"],
    "wall_loops": "3",
    "sparse_infill_density": "15%",
    "sparse_infill_pattern": "grid",
    "layer_height": "0.20",
    "enable_support": "0",
    "support_type": "normal",
    "nozzle_temperature": ["235", "nil"],
    "hot_plate_temp": ["70", "nil"],
    "initial_layer_print_height": "0.25",
    "sparse_infill_speed": ["150", "nil"]
}

MODEL_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
  <resources>
    <object id="1" type="model"><mesh><vertices/><triangles/></mesh></object>
  </resources>
  <build><item objectid="1"/></build>
</model>'''


@pytest.fixture
def sample_settings():
    return dict(SAMPLE_SETTINGS)


@pytest.fixture
def sample_3mf(tmp_path):
    """Minimal valid Bambu 3MF with project_settings.config."""
    path = tmp_path / "test_model.3mf"
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr("3D/3dmodel.model", MODEL_XML)
        z.writestr(CONFIG_PATH, json.dumps(SAMPLE_SETTINGS, indent=4))
    return path


@pytest.fixture
def no_config_3mf(tmp_path):
    """3MF missing project_settings.config — for error path testing."""
    path = tmp_path / "no_config.3mf"
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr("3D/3dmodel.model", MODEL_XML)
    return path
```

- [ ] **Step 1.3: Write all failing tests**

```python
# C:\Users\mfish\.claude\skills\bambu-optimizer\tests\test_apply_patch.py
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from apply_patch import read_3mf, write_3mf


class TestRead:
    def test_returns_all_settings_keys(self, sample_3mf, sample_settings):
        result = read_3mf(str(sample_3mf))
        for key in sample_settings:
            assert key in result, f"Missing key: {key}"

    def test_wall_loops_value(self, sample_3mf):
        result = read_3mf(str(sample_3mf))
        assert result["wall_loops"] == "3"

    def test_filament_detection(self, sample_3mf):
        result = read_3mf(str(sample_3mf))
        assert result["filament_settings_id"] == ["Polymaker PETG HF @BBL P2S 0.4 nozzle"]

    def test_array_values_preserved(self, sample_3mf):
        result = read_3mf(str(sample_3mf))
        assert result["nozzle_temperature"] == ["235", "nil"]

    def test_raises_on_missing_config(self, no_config_3mf):
        with pytest.raises(ValueError, match="project_settings.config not found"):
            read_3mf(str(no_config_3mf))

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            read_3mf("nonexistent.3mf")


class TestWrite:
    def test_creates_optimized_file(self, sample_3mf):
        patch = {"wall_loops": "5"}
        out = write_3mf(str(sample_3mf), patch)
        assert Path(out).exists()

    def test_output_filename_has_optimized_suffix(self, sample_3mf):
        patch = {"wall_loops": "5"}
        out = write_3mf(str(sample_3mf), patch)
        assert Path(out).name == "test_model_optimized.3mf"

    def test_output_in_same_directory(self, sample_3mf):
        patch = {"wall_loops": "5"}
        out = write_3mf(str(sample_3mf), patch)
        assert Path(out).parent == sample_3mf.parent

    def test_original_not_modified(self, sample_3mf):
        patch = {"wall_loops": "5"}
        write_3mf(str(sample_3mf), patch)
        original = read_3mf(str(sample_3mf))
        assert original["wall_loops"] == "3"

    def test_patch_applied(self, sample_3mf):
        patch = {"wall_loops": "5", "sparse_infill_density": "40%"}
        out = write_3mf(str(sample_3mf), patch)
        result = read_3mf(out)
        assert result["wall_loops"] == "5"
        assert result["sparse_infill_density"] == "40%"

    def test_unchanged_keys_preserved(self, sample_3mf):
        patch = {"wall_loops": "5"}
        out = write_3mf(str(sample_3mf), patch)
        result = read_3mf(out)
        assert result["sparse_infill_pattern"] == "grid"
        assert result["layer_height"] == "0.20"
        assert result["nozzle_temperature"] == ["235", "nil"]
        assert result["filament_settings_id"] == ["Polymaker PETG HF @BBL P2S 0.4 nozzle"]

    def test_all_3mf_files_preserved(self, sample_3mf):
        """Other files in the ZIP (e.g. 3dmodel.model) must survive the write."""
        import zipfile
        patch = {"wall_loops": "5"}
        out = write_3mf(str(sample_3mf), patch)
        with zipfile.ZipFile(out, 'r') as z:
            names = z.namelist()
        assert "3D/3dmodel.model" in names
        assert "Metadata/project_settings.config" in names

    def test_multi_key_patch(self, sample_3mf):
        patch = {
            "wall_loops": "6",
            "sparse_infill_density": "45%",
            "sparse_infill_pattern": "gyroid",
            "enable_support": "1",
            "nozzle_temperature": ["240", "nil"]
        }
        out = write_3mf(str(sample_3mf), patch)
        result = read_3mf(out)
        assert result["wall_loops"] == "6"
        assert result["sparse_infill_pattern"] == "gyroid"
        assert result["nozzle_temperature"] == ["240", "nil"]
```

- [ ] **Step 1.4: Run tests to confirm all fail (apply_patch.py doesn't exist yet)**

```powershell
cd "C:\Users\mfish\.claude\skills\bambu-optimizer"
python -m pytest tests\ -v 2>&1 | Select-Object -First 30
```

Expected: `ModuleNotFoundError: No module named 'apply_patch'`

---

## Task 2: Implement apply_patch.py — read mode

**Files:**
- Create: `C:\Users\mfish\.claude\skills\bambu-optimizer\apply_patch.py`

- [ ] **Step 2.1: Create apply_patch.py with read_3mf**

```python
#!/usr/bin/env python3
"""
apply_patch.py - Read and write Bambu Studio 3MF project settings.

Usage:
  python apply_patch.py read <3mf_path>
      Prints current project_settings.config as JSON to stdout.

  python apply_patch.py write <3mf_path> <patch_json_path>
      Applies patch (delta only) and writes <name>_optimized.3mf
      to the same directory. Never modifies the original file.
"""

import sys
import json
import zipfile
import shutil
import os
import tempfile
from pathlib import Path

CONFIG_PATH = "Metadata/project_settings.config"


def read_3mf(path: str) -> dict:
    """Read project_settings.config from a Bambu 3MF. Returns parsed dict."""
    if not Path(path).exists():
        raise FileNotFoundError(f"File not found: {path}")
    with zipfile.ZipFile(path, 'r') as z:
        if CONFIG_PATH not in z.namelist():
            raise ValueError(f"project_settings.config not found in {path}")
        raw = z.read(CONFIG_PATH).decode('utf-8')
    return json.loads(raw)


def write_3mf(src_path: str, patch: dict) -> str:
    """Apply patch delta to 3MF. Writes <name>_optimized.3mf. Returns output path."""
    src = Path(src_path)
    dst = src.parent / f"{src.stem}_optimized{src.suffix}"

    fd, tmp_path = tempfile.mkstemp(suffix='.3mf')
    os.close(fd)

    try:
        with zipfile.ZipFile(src_path, 'r') as z_in:
            with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as z_out:
                for item in z_in.infolist():
                    if item.filename == CONFIG_PATH:
                        current = json.loads(z_in.read(item.filename).decode('utf-8'))
                        current.update(patch)
                        z_out.writestr(item, json.dumps(current, indent=4))
                    else:
                        z_out.writestr(item, z_in.read(item.filename))
        shutil.move(tmp_path, str(dst))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return str(dst)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    path = sys.argv[2]

    if mode == 'read':
        settings = read_3mf(path)
        print(json.dumps(settings, indent=2))

    elif mode == 'write':
        if len(sys.argv) < 4:
            print("Error: write mode requires <patch_json_path>", file=sys.stderr)
            sys.exit(1)
        patch_path = sys.argv[3]
        with open(patch_path, 'r') as f:
            patch = json.load(f)
        out = write_3mf(path, patch)
        print(f"Written: {out}")

    else:
        print(f"Error: unknown mode '{mode}'. Use 'read' or 'write'.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2.2: Run read tests only**

```powershell
cd "C:\Users\mfish\.claude\skills\bambu-optimizer"
python -m pytest tests\test_apply_patch.py::TestRead -v
```

Expected: all 6 TestRead tests PASS.

- [ ] **Step 2.3: Run write tests to confirm they fail correctly**

```powershell
python -m pytest tests\test_apply_patch.py::TestWrite -v
```

Expected: all tests PASS (write_3mf is already implemented). If any fail, fix before continuing.

- [ ] **Step 2.4: Run full test suite**

```powershell
python -m pytest tests\ -v
```

Expected: all tests PASS.

- [ ] **Step 2.5: Smoke test read on real 3MF**

```powershell
python apply_patch.py read "C:\Users\mfish\mcp-3d-printer-server\src\test\3DBenchy.3mf"
```

Expected: JSON output. If `project_settings.config` not found (generic 3MF), expected error:
`ValueError: project_settings.config not found` — this is correct behavior for non-Bambu 3MF files.

---

## Task 3: Write SKILL.md orchestrator

**Files:**
- Create: `C:\Users\mfish\.claude\skills\bambu-optimizer\SKILL.md`

- [ ] **Step 3.1: Write SKILL.md**

```markdown
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

If key missing from 3MF, read from the matching user profile JSON in the profile base directory.

### Step 3 — Detect and confirm filament
Show: `Detected filament: [filament_settings_id[0]]. Confirm to continue, or cancel to create/select a profile first.`
Wait. Cancel = exit cleanly. Confirm = proceed.

### Step 4 — Read print history
Read `H:\ObsidianVault\Cascade-Forge\print-log.md` in full.
Find entries with same filament or similar filename. Note any `[FAILURE]` tags and the settings
they name. This informs recommendations — if a setting failed before, avoid repeating it.

### Step 5 — Visual analysis
Analyze the screenshot:
- Estimate overhang angles (flag anything over 45 deg as needing support)
- Identify bridge spans
- Note thin features, sharp details, or fragile geometry
- Assess surface finish expectations (visible faces vs internal)
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
Write patch dict to a temp file, then run:
```
python "C:\Users\mfish\.claude\skills\bambu-optimizer\apply_patch.py" write "<3mf_path>" "<temp_patch_path>"
```
Confirm output path from stdout. Delete temp patch file.

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
```

- [ ] **Step 3.2: Verify SKILL.md is valid Markdown**

```powershell
Get-Content "C:\Users\mfish\.claude\skills\bambu-optimizer\SKILL.md" | Measure-Object -Line
```

Expected: line count > 100. No errors.

---

## Task 4: Write README.md

**Files:**
- Create: `C:\Users\mfish\.claude\skills\bambu-optimizer\README.md`

- [ ] **Step 4.1: Write README.md**

```markdown
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
```

---

## Task 5: End-to-end smoke test

- [ ] **Step 5.1: Run full test suite one final time**

```powershell
cd "C:\Users\mfish\.claude\skills\bambu-optimizer"
python -m pytest tests\ -v
```

Expected: all tests PASS, no failures.

- [ ] **Step 5.2: Verify script help output**

```powershell
python apply_patch.py
```

Expected: prints usage/docstring, exits with code 1.

- [ ] **Step 5.3: Verify read mode with error handling**

```powershell
python apply_patch.py read "nonexistent.3mf"
```

Expected: `FileNotFoundError` traceback (or clean error message).

- [ ] **Step 5.4: Create a test Bambu 3MF and run full read/write cycle**

```python
# Run this once in Python to create a test fixture:
import zipfile, json
from pathlib import Path

settings = {
    "filament_settings_id": ["Polymaker PETG HF @BBL P2S 0.4 nozzle"],
    "wall_loops": "3",
    "sparse_infill_density": "15%",
    "sparse_infill_pattern": "grid",
    "layer_height": "0.20",
    "enable_support": "0",
    "nozzle_temperature": ["235", "nil"],
    "hot_plate_temp": ["70", "nil"]
}
path = Path(r"C:\Users\mfish\.claude\skills\bambu-optimizer\test_fixture.3mf")
with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr("3D/3dmodel.model", "<model/>")
    z.writestr("Metadata/project_settings.config", json.dumps(settings, indent=4))
print(f"Created: {path}")
```

```powershell
# Run it:
python -c "
import zipfile, json; from pathlib import Path
settings = {'filament_settings_id': ['Polymaker PETG HF @BBL P2S 0.4 nozzle'], 'wall_loops': '3', 'sparse_infill_density': '15%', 'sparse_infill_pattern': 'grid', 'layer_height': '0.20', 'enable_support': '0', 'nozzle_temperature': ['235', 'nil'], 'hot_plate_temp': ['70', 'nil']}
path = Path(r'C:\Users\mfish\.claude\skills\bambu-optimizer\test_fixture.3mf')
z = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
z.writestr('3D/3dmodel.model', '<model/>')
z.writestr('Metadata/project_settings.config', json.dumps(settings, indent=4))
z.close(); print(f'Created: {path}')
"
```

- [ ] **Step 5.5: Read test fixture**

```powershell
python apply_patch.py read "C:\Users\mfish\.claude\skills\bambu-optimizer\test_fixture.3mf"
```

Expected: JSON with `wall_loops: "3"`, filament detected as `Polymaker PETG HF @BBL P2S 0.4 nozzle`.

- [ ] **Step 5.6: Write a patch and verify output**

```powershell
# Write patch file
Set-Content -Path "C:\Users\mfish\.claude\skills\bambu-optimizer\test_patch.json" -Value '{"wall_loops": "5", "sparse_infill_density": "40%", "sparse_infill_pattern": "gyroid"}'

# Apply patch
python apply_patch.py write "C:\Users\mfish\.claude\skills\bambu-optimizer\test_fixture.3mf" "C:\Users\mfish\.claude\skills\bambu-optimizer\test_patch.json"
```

Expected: `Written: C:\Users\mfish\.claude\skills\bambu-optimizer\test_fixture_optimized.3mf`

- [ ] **Step 5.7: Verify optimized file**

```powershell
python apply_patch.py read "C:\Users\mfish\.claude\skills\bambu-optimizer\test_fixture_optimized.3mf"
```

Expected: `wall_loops: "5"`, `sparse_infill_density: "40%"`, `sparse_infill_pattern: "gyroid"`,
`layer_height: "0.20"` (unchanged), `filament_settings_id` intact.

- [ ] **Step 5.8: Clean up test artifacts**

```powershell
Remove-Item "C:\Users\mfish\.claude\skills\bambu-optimizer\test_fixture.3mf" -ErrorAction SilentlyContinue
Remove-Item "C:\Users\mfish\.claude\skills\bambu-optimizer\test_fixture_optimized.3mf" -ErrorAction SilentlyContinue
Remove-Item "C:\Users\mfish\.claude\skills\bambu-optimizer\test_patch.json" -ErrorAction SilentlyContinue
```

---

## Self-Review Checklist

- [x] Spec coverage: read mode, write mode, SKILL.md orchestration, two modes (optimize/feedback), filament confirmation, print log read/write, diff format, approval loop — all covered
- [x] No placeholders: all steps have actual code/commands
- [x] Type consistency: `read_3mf` returns `dict`, `write_3mf` accepts `str` path + `dict`, returns `str` path — consistent across tests and implementation
- [x] Error paths tested: missing file, missing config key
- [x] Delta-only write verified in tests (unchanged keys preserved)
- [x] Array value preservation tested (`nozzle_temperature: ["235", "nil"]`)
