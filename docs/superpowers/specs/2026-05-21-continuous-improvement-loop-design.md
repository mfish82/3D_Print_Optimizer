# Continuous Optimizer Improvement Loop — Design Spec

**Date:** 2026-05-21
**Repo:** https://github.com/mfish82/3D_Print_Optimizer
**Printer:** Bambu Lab P2S, 0.4mm hardened steel nozzle, AMS
**Status:** Approved for implementation

---

## Problem

The bambu-optimizer skill makes decisions using static guidance in SKILL.md and static patch profiles in `patches/`. Every print outcome — success or failure — contains signal about what works for this specific printer, materials, and geometry. That signal is currently logged but never fed back to improve the skill itself. Over time, the skill should get smarter without manual intervention.

---

## Goal

Every time a print outcome is recorded, the skill automatically analyzes the result and updates its own guidance and patch profiles. The skill learns from every print it optimizes.

---

## Core Flow

```
User: "feedback: supports detached at 60% on skull_optimized.3mf"
  → bambu-optimizer FEEDBACK mode (existing Step 1–4)
      → Step 1: find log entry
      → Step 2: classify outcome (FAILURE/SUCCESS/PARTIAL)
      → Step 3: write resolved outcome to print-log.md
      → Step 4: confirm to user
      → Step 5 (NEW): invoke improvement agent inline
          → reads: print-log.md + SKILL.md + patches/<material>.json
          → analyzes: material × goal × settings → outcome correlation
          → generates: targeted updates
          → writes changes to SKILL.md and/or patches/
          → commits with structured message
          → reports one line to user
```

---

## Components

### 1. Improvement Agent (new)

Invoked after every outcome write. Lives as a subagent called from feedback mode Step 5.

**Reads:**
- `H:\ObsidianVault\Cascade-Forge\print-log.md` — full history
- `C:\Users\mfish\.claude\skills\bambu-optimizer\SKILL.md` — current guidance
- `C:\Users\mfish\.claude\skills\bambu-optimizer\patches\<material>.json` — current profile
- The triggering log entry specifically (material, goal, outcome tag, settings listed)

**Analyzes:**
- All prior entries for same material — find success/failure patterns
- Settings named in FAILURE/PARTIAL entries — mark as risky
- Settings used in SUCCESS entries — reinforce as validated
- Conflicting signals — same setting, different outcomes across runs

**Generates updates for:**

| Target | What changes |
|--------|-------------|
| `SKILL.md` — material block | Validated temp/speed/density ranges for this material |
| `SKILL.md` — failure pattern library | Append new failure pattern if FAILURE or PARTIAL |
| `patches/<material>.json` | Refine settings that correlated with outcome |
| New `patches/<material>.json` | Create if new material has 2+ outcomes |

---

### 2. SKILL.md: New Sections Added Over Time

**Material-specific blocks** (added/updated per material as data accumulates):
```markdown
## Material: PolyMax PETG (P2S 0.4mm)
- Nozzle: 248–252°C (validated range)
- Bed: 70°C engineering plate
- Outer wall: 25mm/s max for mold quality
- Volumetric cap: 4 mm³/s (flow limit)
- Support Z gap: 0.36mm (3 layers) — tighter causes adhesion failures
```

**Failure pattern library** (append-only, never overwritten):
```markdown
## Known Failure Patterns
- [PETG] [support_top_z_distance < 0.20mm] → interface adhesion, support bonding to part
- [PLA] [support_threshold_angle > 45°] → over-support on organic geometry
- [PETG] [support_interface_spacing < 0.5mm] → removal force too high on curved surfaces
```

---

### 3. Auto-Apply Rules

**Apply automatically (no user prompt):**
- Numeric refinements within known-safe ranges (temps ±5°C, speeds ±10mm/s, densities ±10%)
- New failure pattern appended to library
- Patch profile updates for settings already in the profile
- New patch file creation for new material

**Surface to user (one-line only, not a warning block):**
- Conflicting signals detected (same setting → success 2× then failure)
- Structural SKILL.md logic change (new print mode, new goal type)
- Settings outside known-safe ranges suggested

User message format when surfacing:
> `"Conflicting signal on support_top_z_distance for PolyMax PETG — worked at 0.12mm (2026-05-17), failed at 0.36mm (2026-05-18). Review print-log.md?"`

---

### 4. Commit Convention

Every auto-improvement commits to the repo with:
```
chore(optimizer): update PolyMax PETG support guidance [FAILURE 2026-05-18]
```

Pattern: `chore(optimizer): <action> <material> <topic> [<outcome> <date>]`

This builds a complete audit trail of skill evolution in git history.

---

### 5. Trigger Architecture

**Primary:** Feedback mode Step 5 — after writing outcome to print-log.md, immediately call improvement agent. Covers all normal usage.

**Fallback (PostToolUse hook):** If print-log.md is written directly (not via feedback mode), hook detects a non-PENDING outcome written to that file and fires the same improvement agent. Prevents missed improvement if log is hand-edited.

Hook placement: `PostToolUse` on `Write|Edit`, checks `input.file_path` matches `print-log.md` and content contains `[SUCCESS]`, `[FAILURE]`, or `[PARTIAL]`.

---

### 6. Failure Pattern Conflict Resolution

When agent detects conflicting signals across history:
1. Count: how many SUCCESS vs FAILURE for this setting+value
2. If 2:1 or better in one direction → apply that direction, note the outlier
3. If 1:1 → surface to user, make no change, log the conflict in SKILL.md as ambiguous

---

## File Layout After Implementation

```
C:\Users\mfish\.claude\skills\bambu-optimizer\
├── SKILL.md                    ← extended with feedback Step 5 + new sections
├── apply_patch.py              ← unchanged
├── patches\
│   ├── polymax_petg_p2s_v2.json     ← refined per outcomes
│   └── <new materials>.json         ← auto-created as data accumulates
└── improvement_agent.md        ← new: improvement agent instructions

H:\ObsidianVault\Cascade-Forge\
└── print-log.md                ← outcomes drive improvement

GitHub: mfish82/3D_Print_Optimizer
└── mirrors the skill directory (source of truth for version history)
```

---

## What Does NOT Change

- `apply_patch.py` — unchanged, no modifications needed
- Optimize mode workflow — unchanged
- User interaction for normal optimize/feedback usage — unchanged
- Print log format — unchanged

---

## Success Criteria

- Every logged outcome triggers an improvement analysis within same session
- SKILL.md failure pattern library grows with each FAILURE/PARTIAL
- Material patch profiles refine with each resolved outcome
- Git history shows improvement commits with structured messages
- No user approval required for incremental numeric improvements
- User is surfaced a one-liner only for conflicting signals or structural changes
- After 10+ outcomes, SKILL.md contains materially better guidance than initial version

---

## Constraints

- Windows paths throughout (no POSIX paths)
- Python stdlib only in apply_patch.py (no pip installs)
- Improvement agent runs inline as subagent from feedback mode
- No external services — all logic is local + git
- Must not overwrite existing SKILL.md sections wholesale — append and refine only
