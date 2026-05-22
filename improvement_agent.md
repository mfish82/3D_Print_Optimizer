---
name: bambu-improvement-agent
description: Analyze resolved print outcome and auto-update SKILL.md and patch profiles
---

# Bambu Improvement Agent

Invoked automatically after every resolved print outcome. Reads full print history, detects
per-material patterns, and updates SKILL.md guidance and patch profiles in place. Commits all
changes to the GitHub repo.

**Config:** Read `config.md` in the skill directory before running. Use `{skill_dir}` and `{print_log}` from it for all paths below.

**Skill dir:** `{skill_dir}`
**Print log:** `{print_log}`

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
1. `{print_log}`
2. `{skill_dir}\SKILL.md`
3. `{skill_dir}\patches\<material_slug>.json` if it exists

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
- **Validated:** settings in SUCCESS entries, plus settings named in `Worked:` annotations on FAILURE/PARTIAL/CANCELLED entries (tag these as `[partial-validated]`)
- **Risky:** settings named in FAILURE/PARTIAL/CANCELLED outcome descriptions or key changes where outcome was bad

For CANCELLED entries: also note `stopped_at` value — records at what stage the print failed.

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

### CANCELLED outcome:

Treat implicated settings (named in outcome description or key changes) as Risky — same as FAILURE.
Note `stopped_at` value in the failure pattern entry if present:
```
- [MATERIAL] [setting_key:value] → description, stopped at <point> (YYYY-MM-DD)
```
Extract any `Worked:` annotations as `[partial-validated]` — same handling as FAILURE Worked.

### SUCCESS outcome:

Check if `## Material Knowledge` section contains a block for this material.

**If block exists:** update the validated ranges using values from this outcome's key changes.

**If no block for this material:** prepare a new block:
```markdown
### <Material Name>
- **Nozzle:** <temp>°C (validated <date>)
- **Bed:** <temp>°C
- **Validated settings for <goal>:** <key settings from Key changes>
- **Partial-validated (worked in failed/cancelled prints):** <setting:value, date>
- **Outcomes:** <N> total — <N> SUCCESS, <N> FAILURE, <N> PARTIAL, <N> CANCELLED
```

**For `[partial-validated]` settings:** add to the "Partial-validated" line of the block. These have weaker signal than full SUCCESS — don't use to override risky designations, but do use as supporting evidence.

### Conflicting signal check (any outcome type):

If a setting appears in both Validated and Risky lists across history:
→ Do NOT auto-update that setting
→ Surface to user (one line): `"Conflicting signal: <setting> succeeded <date> but failed <date>. Skipping auto-update for this setting."`
→ Continue with other non-conflicting updates

---

## Step 4 — Auto-Apply Rules

**Apply automatically without user prompt:**
- Append new entry to `## Known Failure Patterns` (FAILURE and CANCELLED)
- Add or update material block in `## Material Knowledge`
- Add partial-validated settings to material block (from `Worked:` annotations)
- Update numeric values in patch profile within ±20% of the value used in this outcome
- Create new patch file for a material that now has 2+ resolved outcomes (SUCCESS, FAILURE, PARTIAL, or CANCELLED all count)

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
cd "{skill_dir}"
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
| FAILURE | `"Optimizer updated: failure pattern added for <material> [<setting>]. Extracted <N> partial-validated setting(s). Will avoid in future runs."` |
| PARTIAL | `"Optimizer updated: partial outcome logged for <material>. Worked: <settings>. Pattern tracked."` |
| CANCELLED | `"Optimizer updated: cancellation pattern added for <material> [<setting>] stopped at <point>. Extracted <N> partial-validated setting(s)."` |
| Conflict | `"Conflicting signal on <setting> for <material> — auto-update skipped. Manual review: print-log.md"` |

---

## Rules

- Never overwrite `## Rules`, `## MODE: optimize`, `## MODE: feedback`, or any other SKILL.md section
- Only edit within `## Known Failure Patterns` and `## Material Knowledge` sections
- Delta-only: append and refine, never wholesale rewrite
- If uncertain about a setting's safety range, surface to user instead of guessing
- Always commit after any file change — even if only the notes array in a patch file changed
