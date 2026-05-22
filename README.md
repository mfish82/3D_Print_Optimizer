# Bambu 3D Print Optimizer

A Claude Code skill + Python tool that reads Bambu Studio `.3mf` project files, analyzes
print settings against a screenshot and your print history, proposes optimized settings as
a human-readable diff, and writes an `_optimized.3mf` on approval.

***NOTE: I JUST STARTED TO BUILD THIS OUT AND IS ONLY TUNES FOR BAMBU STUDIO WITH PLANS TO TEST ON ORCA SLICER AS WELL. OPEN TO FEEDBACK, FORKS, UPDATES, WHATEVER.
SO MANY OF US USE AI TO ANALYZE AND GIVE US OPTIMAL SETTINGS, THIS CREATES A SELF IMPROVING SKILL TO AID IN THAT EFFORT. THIS DOES REQUIRE THE USE OF A NOTE TAKING/BRAIN STYLE APP LIKE OBSIDIAN***

**No third-party dependencies** — Python stdlib only (`zipfile`, `json`, `shutil`, `tempfile`).

---

## How It Works

```
Claude (SKILL.md orchestrator)
  ├── invoke 3d-print-master skill     ← domain knowledge + pre-flight visual check
  ├── read print-log.md                ← learn from past failures
  ├── apply_patch.py read <file.3mf>   ← extract current settings
  ├── analyze screenshot + settings    ← generate targeted patch
  ├── show diff → approval loop        ← review before anything is written
  └── apply_patch.py write <file.3mf>  ← write _optimized.3mf
        └── append to print-log.md     ← auto-log outcome
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

## Optimization Goals

| Goal | What changes |
|------|-------------|
| `strength` | More walls (5–6), higher infill (35–50% gyroid), finer layers |
| `speed` | Fewer walls (2–3), lower infill (10–15% lightning), higher speeds |
| `flexibility` | TPU mode: 2 walls, 10–20% gyroid, all speeds 30–40 mm/s |
| `detail` | 0.12–0.16 mm layers, slow outer wall, Arachne wall generator |
| `surface finish` | 0.12 mm layers, 25–30 mm/s outer wall, more walls |

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

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Claude Code skill definition — orchestrates the optimize/feedback workflow |
| `apply_patch.py` | Python tool — reads, writes, and audits Bambu 3MF settings |
| `patches/` | Example patch JSON files for reference |
| `tests/` | pytest suite for apply_patch.py |
| `design.md` | Design spec and architecture notes |

---

## Filament Support

Settings guidance is built in for:

- **PETG** (including PolyMax PETG): nozzle 235–242°C, bed 70–80°C, fan ≤ 40%
- **PLA**: nozzle 215–225°C, bed 60–65°C
- **TPU**: nozzle 220–230°C, bed 30–40°C, minimal retraction

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

After printing, the feedback mode updates the outcome line:

```
- Outcome: [SUCCESS] — strong bracket, no warping, supports released cleanly
```

---

## Tests

```bash
cd bambu-optimizer
python -m pytest tests/ -v
```

All tests use a minimal synthetic 3MF — no real print files required.

---

## License

MIT — see [LICENSE](LICENSE).
