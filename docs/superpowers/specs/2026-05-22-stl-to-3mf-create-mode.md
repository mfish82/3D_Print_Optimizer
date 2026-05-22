# Spec: STL → 3MF Create Mode

**Date:** 2026-05-22  
**Status:** DRAFT  
**Target:** `apply_patch.py` — new `create` mode  

---

## Goal

Given an STL file + settings patch, produce a valid Bambu Studio `.3mf` project file that opens
cleanly, slices correctly, and can be fed into the existing `optimize` → `feedback` → `improve` loop.

This closes the gap for users who have an STL but no existing 3MF — they can now start the optimizer
from the raw mesh rather than needing to round-trip through Bambu Studio first.

---

## What a Bambu 3MF Is

A `.3mf` file is a ZIP archive. Bambu Studio project saves contain at minimum:

```
<file>.3mf
├── 3D/
│   └── 3dmodel.model          ← 3MF XML: mesh geometry + object metadata
├── Metadata/
│   ├── project_settings.config ← JSON: all process/filament overrides (what apply_patch.py reads/writes)
│   ├── model_settings.config   ← JSON: per-object settings (support enforcers, layer modifiers)
│   └── Bambu_studio.json       ← version metadata
└── [Content_Types].xml         ← OPC content type manifest
    _rels/.rels                 ← OPC relationship file
```

The `3dmodel.model` carries the mesh geometry in 3MF XML format. When Bambu Studio opens a 3MF,
it reads the geometry from `3dmodel.model` and the settings from `project_settings.config`.

---

## STL → 3MF Conversion Requirements

### Mesh conversion (STL → 3MF XML)
STL is a list of triangles (binary or ASCII). 3MF XML `<mesh>` contains `<vertices>` and `<triangles>`.

**STL binary format:**
- 80-byte header (ignore)
- 4-byte uint32: triangle count
- Per triangle: 12-byte normal (float32 ×3) + 3 vertices (float32 ×3 each) + 2-byte attribute

**STL ASCII format:**
- `solid <name>` … `endsolid`
- Each facet: `facet normal nx ny nz` / `outer loop` / `vertex x y z` ×3 / `endloop` / `endfacet`

**3MF XML vertex deduplication:**
3MF requires a vertex list with triangle indices (no duplicate vertices per triangle allowed in
well-formed 3MF). STL gives a flat triangle list — must deduplicate vertices.

Strategy: dict `(x, y, z) → idx`. Tolerance: exact float match (no fuzzy — STL vertices are already
shared by construction for manifold meshes).

### Minimal valid `3dmodel.model`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US"
       xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
       xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06">
  <resources>
    <object id="1" type="model">
      <mesh>
        <vertices>
          <vertex x="..." y="..." z="..."/>
          ...
        </vertices>
        <triangles>
          <triangle v1="..." v2="..." v3="..."/>
          ...
        </triangles>
      </mesh>
    </object>
  </resources>
  <build>
    <item objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
  </build>
</model>
```

### Minimal `project_settings.config`

Start from the printer baseline settings (read from `{profile_base}/process/<printer_profile>.json`
if available, else use hardcoded P2S defaults from SKILL.md baselines). Merge the user-supplied
settings patch on top.

Required keys at minimum (Bambu Studio will error or use defaults for missing keys):

```json
{
  "filament_settings_id": ["<profile_name>"],
  "printer_settings_id": "<printer_profile>",
  "process_settings_id": "<process_profile>",
  "layer_height": "0.20",
  "initial_layer_print_height": "0.20",
  "wall_loops": "3",
  "sparse_infill_density": "15%",
  "sparse_infill_pattern": "grid",
  "enable_support": "0",
  "nozzle_temperature": ["220"],
  "hot_plate_temp": "65",
  "hot_plate_temp_initial_layer": "65"
}
```

### `[Content_Types].xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
  <Override PartName="/Metadata/project_settings.config"
            ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
```

### `_rels/.rels`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0"
                Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
```

### `Metadata/Bambu_studio.json`

```json
{"BambuStudio": "02.05.03.61"}
```

Bambu Studio uses this to check version compatibility. Any 2.x value should work.

---

## CLI Interface

```bash
# Create a new 3MF from an STL with default P2S settings
python apply_patch.py create model.stl

# Create with a settings patch applied on top of defaults
python apply_patch.py create model.stl patch.json

# Create and immediately run audit
python apply_patch.py create model.stl patch.json --audit
```

Output: `<stl_basename>.3mf` in same directory as input STL.

Return codes: 0 = success, 1 = STL parse error, 2 = invalid patch, 3 = write error.

---

## Integration with Optimize Workflow

After `create`, the resulting `.3mf` is immediately usable as input to `optimize` mode:

```
1. apply_patch.py create model.stl           → model.3mf (baseline settings)
2. [paste screenshot of STL in slicer]
3. "optimize for strength: model.3mf"        → model_optimized.3mf
4. [print] → feedback → improve loop
```

SKILL.md `## MODE: optimize` Step 2 already handles the resulting 3MF — no changes needed there.

---

## What SKILL.md Needs

Add detection for STL input in `## MODE: optimize` trigger:

```
Trigger: user provides STL path OR 3MF path + screenshot + optional goal.
If STL provided: run apply_patch.py create <stl> first to generate baseline 3MF, then proceed.
```

Add one line to Step 2:
> If input is an `.stl` file, run `create` mode first to generate a baseline 3MF, then read it.

---

## Edge Cases

| Case | Handling |
|------|---------|
| ASCII STL | Parse text format, same output |
| Binary STL with 0 triangles | Error: "Empty mesh — check STL file" |
| Non-manifold geometry | Pass through — Bambu Studio will auto-repair; note in stdout |
| Very large STL (>500K tri) | Warn: "High poly mesh — consider decimating before slicing" |
| STL with multiple solids (ASCII) | Merge all into single object (most common scenario) |
| Patch references unknown filament profile | Warn in stdout, still write — user confirms in slicer |

---

## Python Implementation Notes

- Pure stdlib: `struct` for binary STL parse, `xml.etree.ElementTree` for 3MF XML, `zipfile` for archive
- No numpy — keep dependency-free
- Vertex dedup: `dict` with `(round(x,6), round(y,6), round(z,6))` key — avoids float equality issues from STL format
- Default settings: hardcode P2S baseline dict in `create` mode, same values as SKILL.md baselines table
- Profile base optional: if `--profile-base` arg not provided, use hardcoded defaults only

---

## Files to Change

| File | Change |
|------|--------|
| `apply_patch.py` | Add `create` mode with STL parse + 3MF write |
| `SKILL.md` | Two-line addition to optimize trigger and Step 2 |
| `tests/test_create_mode.py` | New test file — round-trip test: generate synthetic STL → create → read → verify keys |
| `README.md` | Add `create` to apply_patch.py usage table |

---

## Test Plan

```python
# tests/test_create_mode.py

def make_cube_stl_binary() -> bytes:
    """Generate a minimal valid binary STL (2 triangles = 1 face of cube for simplicity, 
    or 12 triangles for full cube)"""

def test_create_produces_valid_zip(tmp_path):
    stl = make_cube_stl_binary()
    stl_file = tmp_path / "cube.stl"
    stl_file.write_bytes(stl)
    result = subprocess.run(["python", "apply_patch.py", "create", str(stl_file)], ...)
    assert result.returncode == 0
    out_file = tmp_path / "cube.3mf"
    assert out_file.exists()
    with zipfile.ZipFile(out_file) as z:
        assert "3D/3dmodel.model" in z.namelist()
        assert "Metadata/project_settings.config" in z.namelist()

def test_create_settings_readable_by_read_mode(tmp_path):
    """create → read round-trip: settings written by create are readable by read"""

def test_create_with_patch_applies_overrides(tmp_path):
    """patch keys appear in project_settings.config"""

def test_create_ascii_stl(tmp_path):
    """ASCII format STL parses correctly"""

def test_create_empty_stl_fails_gracefully(tmp_path):
    """Zero triangles → exit code 1, useful error message"""
```

---

## Out of Scope (this spec)

- Multi-object 3MF (multiple STL files in one project) — future
- AMS multi-material — future  
- Support enforcers / layer modifiers (model_settings.config) — future
- Bambu Studio internal plate/layout metadata — Bambu Studio sets this on open, not needed for slicing
