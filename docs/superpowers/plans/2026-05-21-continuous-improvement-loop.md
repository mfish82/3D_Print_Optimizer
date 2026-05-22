# Continuous Optimizer Improvement Loop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After every print outcome is logged, automatically analyze the result and update SKILL.md guidance and patch profiles — the skill gets smarter with every print.

**Architecture:** Extend the existing feedback mode (SKILL.md) with a Step 5 that reads improvement_agent.md and runs inline improvement logic. The improvement agent reads full print history, detects patterns, and edits SKILL.md + patches/ directly. All changes commit to the GitHub repo; a directory junction keeps the Claude skill directory in sync with no copy step.

**Tech Stack:** Claude Code skill system (markdown), Python 3 (tests only), Git, Windows directory junctions

---

## Task 1: Directory Junction — Repo as Single Source of Truth

**Files:**
- Modify: `C:\Users\mfish\.claude\skills\bambu-optimizer\` (replaced by junction)

- [ ] **Step 1: Back up current skill directory contents to repo (verify parity)**

Check that everything in the skill dir is already in the repo:

```powershell
Compare-Object `
  (Get-ChildItem "C:\Users\mfish\.claude\skills\bambu-optimizer" -Recurse -File | Select-Object -ExpandProperty Name | Sort-Object) `
  (Get-ChildItem "C:\Users\mfish\3D_Print_Optimizer" -Recurse -File | Where-Object { $_.Name -ne "LICENSE" } | Select-Object -ExpandProperty Name | Sort-Object)
```

Expected: no output (identical). If differences appear, copy missing files to repo before continuing.

- [ ] **Step 2: Copy any skill-only files to repo first**

```powershell
# Only if Step 1 found differences — copy skill dir files not in repo
# Example: __pycache__ can be ignored
Copy-Item "C:\Users\mfish\.claude\skills\bambu-optimizer\*" `
  "C:\Users\mfish\3D_Print_Optimizer\" -Recurse -Force -Exclude "__pycache__"
```

- [ ] **Step 3: Remove skill directory and create junction**

```powershell
Remove-Item "C:\Users\mfish\.claude\skills\bambu-optimizer" -Recurse -Force
cmd /c mklink /J "C:\Users\mfish\.claude\skills\bambu-optimizer" "C:\Users\mfish\3D_Print_Optimizer"
```

Expected output: `Junction created for C:\Users\mfish\.claude\skills\bambu-optimizer <<===>> C:\Users\mfish\3D_Print_Optimizer`

- [ ] **Step 4: Verify junction works**

```powershell
Get-Item "C:\Users\mfish\.claude\skills\bambu-optimizer" | Select-Object FullName, LinkType, Target
ls "C:\Users\mfish\.claude\skills\bambu-optimizer\SKILL.md"
```

Expected: LinkType = Junction, SKILL.md present.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/mfish/3D_Print_Optimizer"
git add .
git commit -m "chore: verify repo parity before junction setup

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Add Failure Pattern Library + Material Knowledge Sections to SKILL.md

**Files:**
- Modify: `C:\Users\mfish\3D_Print_Optimizer\SKILL.md`

- [ ] **Step 1: Append failure pattern library section to end of SKILL.md**

Open `C:\Users\mfish\3D_Print_Optimizer\SKILL.md` and append at the very end:

```markdown

---

## Known Failure Patterns

<!-- Auto-updated by improvement agent. Do not edit manually. -->
<!-- Format: - [MATERIAL] [setting_key:value] → description (date) -->
```

- [ ] **Step 2: Append material knowledge section**

Immediately after the failure patterns section, append:

```markdown

---

## Material Knowledge

<!-- Auto-updated by improvement agent. Do not edit manually. -->
<!-- Each material block added after first resolved outcome. -->
```

- [ ] **Step 3: Verify sections appear correctly**

```bash
grep -n "Known Failure Patterns\|Material Knowledge" "C:/Users/mfish/3D_Print_Optimizer/SKILL.md"
```

Expected: two matching lines near the end of the file.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/mfish/3D_Print_Optimizer"
git add SKILL.md
git commit -m "feat(optimizer): add failure pattern library and material knowledge sections to SKILL.md

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Create improvement_agent.md

**Files:**
- Create: `C:\Users\mfish\3D_Print_Optimizer\improvement_agent.md`

- [ ] **Step 1: Create improvement_agent.md with full improvement logic**

Create `C:\Users\mfish\3D_Print_Optimizer\improvement_agent.md` with this exact content:

```markdown
---
name: bambu-improvement-agent
description: Analyze resolved print outcome and auto-update SKILL.md and patch profiles
---

# Bambu Improvement Agent

Invoked automatically after every resolved print outcome. Reads full print history, detects
per-material patterns, and updates SKILL.md guidance and patch profiles in place. Commits all
changes to the GitHub repo.

**Repo / skill path:** `C:\Users\mfish\3D_Print_Optimizer\` (junction: `C:\Users\mfish\.claude\skills\bambu-optimizer\`)
**Print log:** `H:\ObsidianVault\Cascade-Forge\print-log.md`

---

## Context Received from Caller

Feedback mode passes these values when invoking this agent:
- Material name (e.g., "PolyMax PETG")
- Goal (e.g., "mold master", "detail", "strength")
- Outcome type: SUCCESS | FAILURE | PARTIAL
- Date of outcome (YYYY-MM-DD)
- Full outcome line text from the log

---

## Step 1 — Read Current State

Read all three sources in full:
1. `H:\ObsidianVault\Cascade-Forge\print-log.md`
2. `C:\Users\mfish\3D_Print_Optimizer\SKILL.md`
3. `C:\Users\mfish\3D_Print_Optimizer\patches\<material_slug>.json` if it exists

**Material slug rule:** lowercase, spaces to underscores, remove special chars.
- "PolyMax PETG" → `polymax_petg`
- "Bambu PLA Basic" → `bambu_pla_basic`
- "PLA-CF (Fiberon)" → `pla_cf_fiberon`

---

## Step 2 — Extract History for This Material

From print-log.md, collect ALL entries where the Filament line matches the material.

For each matching entry, extract:
- Date
- Goal
- Key changes (each bullet = one setting change)
- Outcome line (SUCCESS/FAILURE/PARTIAL + description)

Build two lists:
- **Validated:** settings in SUCCESS entries
- **Risky:** settings named in FAILURE/PARTIAL outcome descriptions or key changes where outcome was bad

---

## Step 3 — Determine What to Update

### FAILURE or PARTIAL outcome:

Find settings named in the outcome description or key changes for this entry.
Check `## Known Failure Patterns` section of SKILL.md.
If this exact pattern (material + setting + approximate value) is NOT already there:
→ Prepare append entry:
```
- [MATERIAL] [setting_key:value] → failure description (YYYY-MM-DD)
```

Example:
```
- [PolyMax PETG] [support_top_z_distance:0.12mm] → interface bonded to part, required force to remove (2026-05-18)
```

### SUCCESS outcome:

Check if `## Material Knowledge` section contains a block for this material.

**If block exists:** update the validated ranges using values from this outcome's key changes.

**If no block for this material:** prepare a new block:
```markdown
### <Material Name>
- **Nozzle:** <temp>°C (validated <date>)
- **Bed:** <temp>°C
- **Validated settings for <goal>:** <key settings from Key changes>
- **Outcomes:** <N> total — <N> SUCCESS, <N> FAILURE, <N> PARTIAL
```

### Conflicting signal check (any outcome type):

If a setting appears in both Validated and Risky lists across history:
→ Do NOT auto-update that setting
→ Surface to user (one line): `"Conflicting signal: <setting> succeeded <date> but failed <date>. Skipping auto-update for this setting."`
→ Continue with other non-conflicting updates

---

## Step 4 — Auto-Apply Rules

**Apply automatically without user prompt:**
- Append new entry to `## Known Failure Patterns`
- Add or update material block in `## Material Knowledge`
- Update numeric values in patch profile within ±20% of the value used in this outcome
- Create new patch file for a material that now has 2+ resolved outcomes

**Surface to user (one line) and skip:**
- Conflicting signal detected (same setting, different outcomes)
- Suggested update is outside ±20% of ALL prior values for that setting
- Material has only 1 prior outcome (not enough signal) — log it, don't update patch

---

## Step 5 — Edit SKILL.md

Use the Edit tool with exact string matching.

**To append to `## Known Failure Patterns`:**
Find the line `<!-- Format: - [MATERIAL] [setting_key:value] → description (date) -->` and append after it.

**To add/update `## Material Knowledge` block:**
Find the line `<!-- Each material block added after first resolved outcome. -->` and append new block after it.
If updating existing block, find the exact lines to change and use Edit tool on them specifically.

Never overwrite sections outside these two blocks.

---

## Step 6 — Update Patch Profile

**If patch file exists** (`patches/<material_slug>.json`):

Read current content. Add to `"notes"` array:
```json
"[YYYY-MM-DD] <OUTCOME_TYPE>: <brief description>"
```

For SUCCESS: merge validated settings into `"process"` or `"filament"` keys (whichever applies per Bambu Studio field).
For FAILURE: add a `"avoid"` key if not present, list the risky setting+value.
Increment `"outcome_count"`.

**If no patch file exists and material has 2+ outcomes:**

Create `patches/<material_slug>.json`:
```json
{
  "description": "<Material Name> profile for P2S 0.4mm hardened steel — auto-refined from print history",
  "generated": "YYYY-MM-DD",
  "outcome_count": 2,
  "process": {},
  "filament": {},
  "avoid": [],
  "notes": [
    "[date] <OUTCOME_TYPE>: <description>"
  ]
}
```

**If only 1 outcome so far:** do not create patch file yet. Note in user report.

---

## Step 7 — Commit Changes

```bash
cd "C:\Users\mfish\3D_Print_Optimizer"
git add SKILL.md patches/
git commit -m "chore(optimizer): update <material_slug> <what changed> [<OUTCOME_TYPE> <date>]"
```

Examples:
- `chore(optimizer): update polymax_petg failure patterns [FAILURE 2026-05-18]`
- `chore(optimizer): add bambu_pla_basic material knowledge [SUCCESS 2026-05-17]`
- `chore(optimizer): refine polymax_petg patch profile [SUCCESS 2026-05-20]`

---

## Step 8 — Report to User

One line only, appended after the existing feedback mode confirmation:

| Outcome | Report format |
|---------|--------------|
| SUCCESS | `"Optimizer updated: <material> knowledge reinforced. (<N> outcomes tracked)"` |
| FAILURE | `"Optimizer updated: failure pattern added for <material> [<setting>]. Will avoid in future runs."` |
| PARTIAL | `"Optimizer updated: partial outcome logged for <material>. Pattern tracked."` |
| Conflict | `"Conflicting signal on <setting> for <material> — auto-update skipped. Manual review: print-log.md"` |

---

## Rules

- Never overwrite `## Rules`, `## MODE: optimize`, `## MODE: feedback`, or any other SKILL.md section
- Only edit within `## Known Failure Patterns` and `## Material Knowledge` sections
- Delta-only: append and refine, never wholesale rewrite
- If uncertain about a setting's safety range, surface to user instead of guessing
- Always commit after any file change — even if only the notes array in a patch file changed
```

- [ ] **Step 2: Verify file was created**

```bash
ls "C:/Users/mfish/3D_Print_Optimizer/improvement_agent.md"
grep -c "Step" "C:/Users/mfish/3D_Print_Optimizer/improvement_agent.md"
```

Expected: file exists, grep returns 8 (Steps 1–8).

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/mfish/3D_Print_Optimizer"
git add improvement_agent.md
git commit -m "feat(optimizer): add improvement agent — auto-updates SKILL.md and patches per outcome

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Extend Feedback Mode — Add Step 5

**Files:**
- Modify: `C:\Users\mfish\3D_Print_Optimizer\SKILL.md`

- [ ] **Step 1: Locate the end of feedback mode Step 4 in SKILL.md**

```bash
grep -n "Step 4\|Outcome logged\|inform future" "C:/Users/mfish/3D_Print_Optimizer/SKILL.md"
```

Note the line number of the last line in Step 4 (the `Confirm:` line).

- [ ] **Step 2: Append Step 5 immediately after Step 4 in the feedback mode section**

Find this exact text in SKILL.md:
```
### Step 4 — Save log
Write updated `print-log.md`. Confirm: `Outcome logged. Will inform future [filament] runs.`
```

Replace with:
```
### Step 4 — Save log
Write updated `print-log.md`. Confirm: `Outcome logged. Will inform future [filament] runs.`

### Step 5 — Invoke improvement agent
Read `C:\Users\mfish\3D_Print_Optimizer\improvement_agent.md` in full and follow it.

Pass this context to the agent:
- Material: the filament name from Step 1
- Goal: the goal from the log entry
- Outcome type: SUCCESS | FAILURE | PARTIAL (from Step 2)
- Date: the date from the log entry
- Outcome line: the full outcome text written in Step 3

The agent runs inline. Do not wait for user input before invoking.
```

- [ ] **Step 3: Verify Step 5 appears in file**

```bash
grep -n "Step 5\|improvement agent" "C:/Users/mfish/3D_Print_Optimizer/SKILL.md"
```

Expected: two matching lines in the feedback mode section.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/mfish/3D_Print_Optimizer"
git add SKILL.md
git commit -m "feat(optimizer): add Step 5 to feedback mode — invoke improvement agent after every outcome

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Write Verification Tests

**Files:**
- Create: `C:\Users\mfish\3D_Print_Optimizer\tests\test_improvement_loop.py`

These tests verify the log parsing logic and section update format that the improvement agent relies on. They use fixture files, not live files.

- [ ] **Step 1: Create fixture directory and files**

Create `C:\Users\mfish\3D_Print_Optimizer\tests\fixtures\` with these two files:

`tests\fixtures\sample_print_log.md`:
```markdown
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
```

`tests\fixtures\sample_skill.md`:
```markdown
# Bambu Optimizer

## Known Failure Patterns

<!-- Auto-updated by improvement agent. Do not edit manually. -->
<!-- Format: - [MATERIAL] [setting_key:value] → description (date) -->

## Material Knowledge

<!-- Auto-updated by improvement agent. Do not edit manually. -->
<!-- Each material block added after first resolved outcome. -->
```

- [ ] **Step 2: Create test file**

Create `C:\Users\mfish\3D_Print_Optimizer\tests\test_improvement_loop.py`:

```python
"""
Verify the improvement loop logic assumptions:
- Log entries parse to correct material, goal, outcome type, settings
- SKILL.md section anchors exist and are findable by exact string
- Patch file format is valid JSON with required keys
"""

import json
import re
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
LOG_FILE = FIXTURES / "sample_print_log.md"
SKILL_FILE = FIXTURES / "sample_skill.md"


def parse_log_entries(log_text: str) -> list[dict]:
    """Extract structured data from print log entries."""
    entries = []
    blocks = re.split(r"\n## \d{4}-\d{2}-\d{2}", log_text)
    dates = re.findall(r"## (\d{4}-\d{2}-\d{2})", log_text)

    for date, block in zip(dates, blocks[1:]):
        entry = {"date": date}
        goal_match = re.search(r"- Goal: (.+)", block)
        filament_match = re.search(r"- Filament: (.+)", block)
        outcome_match = re.search(r"- Outcome: \[(\w+)[:\]]", block)
        settings = re.findall(r"`(\w+)`\s+.+→\s+(.+?)(?:\s+\(|$)", block)

        entry["goal"] = goal_match.group(1).strip() if goal_match else ""
        entry["filament"] = filament_match.group(1).strip() if filament_match else ""
        entry["outcome_type"] = outcome_match.group(1) if outcome_match else "PENDING"
        entry["settings"] = {k: v.strip() for k, v in settings}
        entries.append(entry)

    return entries


def test_log_parses_two_entries():
    log_text = LOG_FILE.read_text(encoding="utf-8")
    entries = parse_log_entries(log_text)
    assert len(entries) == 2


def test_success_entry_parsed_correctly():
    log_text = LOG_FILE.read_text(encoding="utf-8")
    entries = parse_log_entries(log_text)
    success = next(e for e in entries if e["outcome_type"] == "SUCCESS")
    assert "Bambu PLA Basic" in success["filament"]
    assert success["goal"].startswith("accuracy")
    assert "support_threshold_angle" in success["settings"]


def test_failure_entry_parsed_correctly():
    log_text = LOG_FILE.read_text(encoding="utf-8")
    entries = parse_log_entries(log_text)
    failure = next(e for e in entries if e["outcome_type"] == "FAILURE")
    assert "PolyMax PETG" in failure["filament"]
    assert "support_top_z_distance" in failure["settings"]


def test_skill_has_failure_patterns_anchor():
    skill_text = SKILL_FILE.read_text(encoding="utf-8")
    anchor = "<!-- Format: - [MATERIAL] [setting_key:value] → description (date) -->"
    assert anchor in skill_text, "Failure pattern anchor missing from SKILL.md"


def test_skill_has_material_knowledge_anchor():
    skill_text = SKILL_FILE.read_text(encoding="utf-8")
    anchor = "<!-- Each material block added after first resolved outcome. -->"
    assert anchor in skill_text, "Material knowledge anchor missing from SKILL.md"


def test_failure_pattern_format():
    """Verify the expected append format is parseable."""
    sample = "- [PolyMax PETG] [support_top_z_distance:0.12mm] → interface bonded to part (2026-05-18)"
    pattern = re.compile(r"- \[(.+?)\] \[(.+?):(.+?)\] → (.+?) \((\d{4}-\d{2}-\d{2})\)")
    match = pattern.match(sample)
    assert match is not None
    assert match.group(1) == "PolyMax PETG"
    assert match.group(2) == "support_top_z_distance"
    assert match.group(3) == "0.12mm"


def test_patch_file_has_required_keys():
    """Verify existing patch file has all keys the improvement agent expects."""
    patch_dir = Path(__file__).parent.parent / "patches"
    for patch_file in patch_dir.glob("*.json"):
        data = json.loads(patch_file.read_text(encoding="utf-8"))
        for key in ("description", "process", "filament"):
            assert key in data, f"{patch_file.name} missing key: {key}"


def test_material_slug_conversion():
    """Verify material name → slug logic."""
    cases = [
        ("PolyMax PETG", "polymax_petg"),
        ("Bambu PLA Basic @BBL P2S", "bambu_pla_basic__bbl_p2s"),
        ("PLA-CF (Fiberon)", "pla_cf__fiberon_"),
    ]
    def to_slug(name: str) -> str:
        return re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")

    for name, expected_prefix in cases:
        slug = to_slug(name)
        assert slug.startswith(expected_prefix.rstrip("_")), f"{name} → {slug}, expected prefix {expected_prefix}"
```

- [ ] **Step 3: Run tests**

```bash
cd "C:/Users/mfish/3D_Print_Optimizer"
py -m pytest tests/test_improvement_loop.py -v
```

Expected output:
```
PASSED tests/test_improvement_loop.py::test_log_parses_two_entries
PASSED tests/test_improvement_loop.py::test_success_entry_parsed_correctly
PASSED tests/test_improvement_loop.py::test_failure_entry_parsed_correctly
PASSED tests/test_improvement_loop.py::test_skill_has_failure_patterns_anchor
PASSED tests/test_improvement_loop.py::test_skill_has_material_knowledge_anchor
PASSED tests/test_improvement_loop.py::test_failure_pattern_format
PASSED tests/test_improvement_loop.py::test_patch_file_has_required_keys
PASSED tests/test_improvement_loop.py::test_material_slug_conversion
8 passed
```

Fix any failures before committing.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/mfish/3D_Print_Optimizer"
git add tests/
git commit -m "test(optimizer): add improvement loop verification tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Push to GitHub

- [ ] **Step 1: Verify all commits are present**

```bash
cd "C:/Users/mfish/3D_Print_Optimizer"
git log --oneline -10
```

Expected: see commits from Tasks 1–5 in order.

- [ ] **Step 2: Push**

```bash
cd "C:/Users/mfish/3D_Print_Optimizer"
git push origin main
```

- [ ] **Step 3: Verify on GitHub**

```bash
gh repo view mfish82/3D_Print_Optimizer --web
```

Confirm: improvement_agent.md, updated SKILL.md, tests/test_improvement_loop.py, design spec all present.

---

## Self-Review Checklist

**Spec coverage:**
- [x] Every outcome triggers improvement → Task 4 (feedback Step 5)
- [x] Improvement agent reads log + SKILL.md + patches → improvement_agent.md Steps 1–2
- [x] Failure patterns appended → improvement_agent.md Step 3 + Task 2
- [x] Material knowledge updated → improvement_agent.md Step 3 + Task 2
- [x] Patch profiles refined → improvement_agent.md Step 6
- [x] Auto-apply vs surface rules → improvement_agent.md Step 4
- [x] Commit on every change → improvement_agent.md Step 7
- [x] One-line user report → improvement_agent.md Step 8
- [x] Conflicting signal handling → improvement_agent.md Step 3
- [x] Directory junction → Task 1
- [x] Tests → Task 5

**No placeholders:** All steps contain actual content — no TBD, no "handle edge cases", no "implement later."

**Type consistency:** `material_slug` used consistently; `improvement_agent.md` referenced by exact path throughout.
