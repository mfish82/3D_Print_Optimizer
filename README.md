# Bambu 3D Print Optimizer

A Claude Code skill + Python tool that reads Bambu Studio `.3mf` project files, analyzes
print settings against a screenshot and your print history, proposes optimized settings as
a human-readable diff, and writes an `_optimized.3mf` on approval.

***NOTE: I JUST STARTED TO BUILD THIS OUT AND ONLY TUNES FOR BAMBU STUDIO WITH PLANS TO TEST ON ORCA SLICER AS WELL. OPEN TO FEEDBACK, FORKS, UPDATES, WHATEVER.
SO MANY OF US USE AI TO ANALYZE AND GIVE US OPTIMAL SETTINGS FOR OUR PRINTS, THIS IS MY ATTEMPT AT A SELF IMPROVING SKILL TO AID IN THAT EFFORT. THIS DOES REQUIRE THE USE OF A NOTE TAKING/BRAIN STYLE APP LIKE OBSIDIAN***

**No third-party dependencies** — Python stdlib only (`zipfile`, `json`, `shutil`, `tempfile`).

---

## How It Works

```
Claude (SKILL.md orchestrator)
  ├── mesh pre-flight (inline)         ← CAD vs scan, flag issues, no external skill needed
  ├── read print-log.md                ← learn from past failures
  ├── apply_patch.py read <file.3mf>   ← extract current settings
  ├── analyze screenshot + settings    ← generate targeted patch
  ├── show diff → approval loop        ← review before anything is written
  └── apply_patch.py write <file.3mf>  ← write _optimized.3mf
        ├── append to print-log.md     ← auto-log outcome
        └── improvement_agent.md       ← update SKILL.md + patches from outcome
```

---

## Requirements

- Python 3.x
- [Claude Code](https://claude.ai/code) (desktop or VSCode extension)
- Bambu Studio `.3mf` project file — must be a **project save**, not a raw STL export

---

## Setup

1. Clone this repo into your Claude Code skills directory:

   ```
   %USERPROFILE%\.claude\skills\bambu-optimizer\
   ```

2. Edit `SKILL.md` and update the three path variables near the top:

   ```
   Script:    path to apply_patch.py
   Print log: path to your print-log.md
   Profiles:  path to your BambuStudio user profile directory
   ```

3. The skill auto-activates in Claude Code when you mention a `.3mf` file or say "optimize".

---

## Usage

### Optimize a print

1. Open Bambu Studio, load your model, set your filament profile
2. Take a screenshot (Win+Shift+S)
3. Open Claude Code, paste the screenshot (Ctrl+V)
4. Say something like:

   ```
   optimize this for strength: C:\prints\bracket.3mf
   ```

5. Confirm the detected filament profile
6. Review the proposed diff
7. Type `approve` to write `bracket_optimized.3mf`, or describe adjustments
8. Open the optimized file in Bambu Studio and slice

### Log a print outcome

After the print finishes, feed the result back so future runs learn from it:

```
feedback: supports detached at 60% on bracket_optimized.3mf
```

```
feedback: perfect print on vase_optimized.3mf — no warping, clean release
```

---

## What to Give Claude for Best Results

The more context you provide, the better the recommendations. Below is ranked by impact.

### Minimum (required)

| Input | Why |
|-------|-----|
| `.3mf` project file | Contains current settings — optimizer can't run without it |
| Bambu Studio screenshot | Visual analysis drives support, speed, and layer decisions |
| Goal or use case | Even one word: `strength`, `speed`, `mold master`, `living hinge` |

### High impact (strongly recommended)

| Input | Why |
|-------|-----|
| **Filament brand + product name** | "PolyMax PETG" vs "generic PETG" changes temps, fan, and volumetric caps significantly |
| **Vendor data sheet or published print settings** | Manufacturer specs override heuristic defaults — paste key values or link the PDF |
| **Multiple screenshot angles** | Single-angle views hide overhangs and bridges; top + front + side gives full geometry picture |
| **Post-processing intent** | "gets XTC coated and sanded" → prioritize layer bonding over surface; "straight to client" → surface finish matters |
| **Structural requirements** | "needs to hold 20 lb load" or "living hinge, flexes 180° daily" changes wall count and infill pattern |

### Useful when available

| Input | Why |
|-------|-----|
| STL file | Allows mesh pre-flight — catches non-manifold geometry and scan artifacts before slicing |
| Previous print outcome for this filament | Confirms what temps/speeds already worked; avoids repeating failures |
| Time or filament budget | "needs to finish in under 6 hours" or "can't use more than 80g" — optimizer adjusts trade-offs |
| AMS slot assignment | Multi-material setups have different retraction and purge requirements |

### What makes a good screenshot

- Slicer view (not model view) — shows actual slice geometry and layer lines
- Rotate to expose the worst overhangs and bridge spans
- Include support preview if enabled
- Zoom in on thin walls, sharp details, or problem areas
- Multiple angles > one perfect angle

---

## Optimization Goals

Goals are **starting points, not constraints**. You can mix, stack, or describe anything — Claude
interprets natural language. The built-in profiles are:

| Goal | What changes |
|------|-------------|
| `strength` | More walls (5–6), higher infill (35–50% gyroid), finer layers |
| `speed` | Fewer walls (2–3), lower infill (10–15% lightning), higher speeds |
| `flexibility` | TPU mode: 2 walls, 10–20% gyroid, all speeds 30–40 mm/s |
| `detail` | 0.12–0.16 mm layers, slow outer wall, Arachne wall generator |
| `surface finish` | 0.12 mm layers, 25–30 mm/s outer wall, more walls |

### Custom and mixed requests

You're not limited to the table above. Describe the print's actual requirements and Claude will
compose the right settings from first principles:

**Combining goals:**
```
optimize for strength but I need it done in under 8 hours — it's structural but not load-critical
```

**Use-case driven:**
```
mold master — needs to survive 3 pours of silicone and hold fine facial detail. Surface finish
on the front face only, sides and back are irrelevant.
```

**Constraint-based:**
```
maximize strength under 100g filament budget, 0.4mm nozzle, PETG
```

**Geometry-specific:**
```
thin-wall scan of a skull with known mesh artifacts — be conservative on speeds, prioritize
layer bonding over surface finish. Tree supports, no interface layers.
```

**Material + process combo:**
```
this gets XTC-3D coated and block sanded to 2000 grit — trade surface finish for bonding.
Bump temp to upper range. Overhang fan off.
```

**Failure-informed:**
```
last two prints warped at the corners — PETG on textured PEI. Prioritize bed adhesion over everything.
```

The diff step lets you adjust anything before writing. The approval loop means nothing gets
applied until you say `approve`.

---

## apply_patch.py

The Python script handles all 3MF file I/O. You can also use it directly:

```bash
# Read current settings from a 3MF
python apply_patch.py read project.3mf

# Apply a patch and write _optimized.3mf (auto-audits after write)
python apply_patch.py write project.3mf patch.json

# Full human-readable audit of all critical settings
python apply_patch.py review project.3mf
```

Patch files are plain JSON — delta only. Only keys you include are changed:

```json
{
    "wall_loops": "5",
    "sparse_infill_density": "40%",
    "sparse_infill_pattern": "gyroid",
    "nozzle_temperature": ["240", "nil"]
}
```

The `write` mode **never modifies the original file**. It writes `<name>_optimized.3mf`
to the same directory.

---

## Audit / Review Mode

After every write, `apply_patch.py` runs a full audit and flags suspicious values:

- Temperatures out of range for the detected filament type
- Fan speeds too high for PETG
- Support Z-distance not on a clean layer boundary
- Speeds exceeding the volumetric flow cap
- Wall counts or infill too low for structural use

---

## Current Challenges

Known limitations to be aware of:

**Profile inheritance is opaque.**
Bambu Studio 3MF project files only store *overrides* — values inherited from the base profile
are not written to `project_settings.config`. If a setting isn't in the 3MF, the optimizer
reads the profile JSON directly, but the full inheritance chain (custom → base → system) isn't
always traversed. Some settings may appear as default when they're actually overridden higher up.

**Visual analysis depends on screenshot quality.**
A single slicer angle can hide overhangs entirely. Claude can't rotate the model — you need to
provide multiple angles for complex geometry. Organic or scan-derived meshes are especially
prone to missed overhangs.

**Audit thresholds are heuristic, not material-spec.**
The warning flags in review mode are based on general PETG/PLA/TPU ranges. Specialty materials
(ASA, ABS, PA-CF, filled filaments) won't get accurate warnings without a data sheet. Always
cross-check against the manufacturer's published settings.

**No in-slicer verification.**
The optimizer writes a valid 3MF but can't open Bambu Studio to confirm the slice looks correct.
Always re-slice and visually check the layer preview before printing — especially for supports,
first layer adhesion, and top surface bridging.

**Filament profile must exist in Bambu Studio.**
The patch writes a `filament_settings_id` reference. If that profile isn't installed in your
Bambu Studio, it will silently fall back to defaults. Confirm the profile name in your BambuStudio
user profiles directory before patching.

**Print log grows unbounded.**
No pruning, search, or summarization built in. Long logs slow down history reads. Periodically
archive old entries if the log gets unwieldy.

**No AMS multi-material support.**
Patches target extruder index 0. Multi-material prints with AMS require per-extruder
settings (`["value1", "value2", ...]`) which the current patch format doesn't manage explicitly.

---

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Claude Code skill definition — orchestrates the optimize/feedback/improvement workflow |
| `improvement_agent.md` | Inline improvement agent — auto-updates SKILL.md and patch profiles per outcome |
| `apply_patch.py` | Python tool — reads, writes, and audits Bambu 3MF settings |
| `patches/` | Per-material patch profiles, auto-refined by improvement agent |
| `references/bambu-studio.md` | Bambu Studio 2.5.3.61 settings reference (process panel locations, base cuts, support behavior) |
| `tests/` | pytest suite for apply_patch.py and improvement loop logic |
| `design.md` | Design spec and architecture notes |

---

## Filament Support

Settings guidance is built in for:

- **PETG** (including PolyMax PETG): nozzle 235–242°C, bed 70–80°C, fan ≤ 40%
- **PLA**: nozzle 215–225°C, bed 60–65°C
- **TPU**: nozzle 220–230°C, bed 30–40°C, minimal retraction

For other materials, paste the data sheet values into your prompt and Claude will use them directly.

---

## Print Log

The skill reads and writes a Markdown print log so every optimization run is tracked:

```markdown
## 2026-05-21 - bracket.3mf
- Goal: strength
- Filament: Polymaker PETG PolyMax
- Key changes: wall_loops 3→5, infill 15→40% gyroid, tree supports
- Output: C:\prints\bracket_optimized.3mf
- Outcome: [PENDING]
```

After printing, the feedback mode updates the outcome line and **automatically triggers the improvement agent**:

```
- Outcome: [SUCCESS] — strong bracket, no warping, supports released cleanly. Validated: wall_loops:5, support_top_z_distance:0.25mm
- Outcome: [FAILURE: supports] [PETG] [support_type:tree] — detached at 60%. Worked: walls clean, layer adhesion solid
- Outcome: [CANCELLED: spaghetti at 35%] [PLA] [stopped_at:35%] [layer_height:0.28mm] — layer shifted. Worked: first 10 layers excellent
```

The improvement agent reads your full print history, detects per-material patterns, and updates
`SKILL.md`'s `## Known Failure Patterns` and `## Material Knowledge` sections automatically.
Every resolved outcome — including stops and partial prints — feeds the loop.

---

## Tests

```bash
cd bambu-optimizer
python -m pytest tests/ -v
```

All tests use a minimal synthetic 3MF — no real print files required.

---

## Changelog

### v0.5 — 2026-05-22
- **Self-contained** — no longer depends on `3d-print-master` skill. All domain knowledge inlined.
- Added `## Mesh Pre-Flight Reference` section: CAD vs scan detection, scan mesh flags, correct prep order, tool quick-ref
- Added `## Printer & Filament Baselines` section: P2S specs, PLA/PETG/TPU baseline settings tables
- Optimize mode Step 1 replaced: inline mesh pre-flight (no external skill invocation)
- Added `references/bambu-studio.md`: Bambu Studio 2.5.3.61 settings reference

### v0.4 — 2026-05-22
- Feedback mode captures `CANCELLED` outcome type (stopped prints) with `stopped_at` tracking
- Every outcome now records `Worked:` / `Validated:` annotations — extracts positive signals even from failures
- Improvement agent extracts `[partial-validated]` settings from `Worked:` annotations on FAILURE/CANCELLED entries
- Material Knowledge blocks now track partial-validated settings and CANCELLED counts separately

### v0.3 — 2026-05-22
- **Continuous improvement loop**: every resolved feedback outcome auto-invokes `improvement_agent.md`
- `improvement_agent.md`: 8-step inline agent reads print history, updates `SKILL.md` sections, refines patch profiles, and commits — no manual steps
- `SKILL.md`: added `## Known Failure Patterns` and `## Material Knowledge` auto-updated sections
- Feedback mode Step 5 added — improvement agent runs inline after every log save
- `C:\Users\mfish\.claude\skills\bambu-optimizer\` is now a directory junction → repo (single source of truth)
- Added `tests/test_improvement_loop.py` with fixture-based verification of log parsing and anchor integrity

### v0.2 — 2026-05-21
- `apply_patch.py`: added `review` mode — full settings audit with per-category warning flags
- Review runs automatically after every `write`
- Added `patches/polymax_petg_p2s_v2.json` — example patch for Polymaker PolyMax PETG on P2S
- MIT license
- README: generic paths, customization guide, required inputs, challenges

### v0.1 — 2026-05-16
- Initial implementation: `apply_patch.py` with `read` and `write` modes
- `SKILL.md` orchestrator with `optimize` and `feedback` workflows
- pytest suite with synthetic 3MF fixtures — no real files required

---

## License

MIT — see [LICENSE](LICENSE).
