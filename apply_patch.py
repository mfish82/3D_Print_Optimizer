#!/usr/bin/env python3
"""
apply_patch.py - Read, write, and audit Bambu Studio 3MF project settings.

Usage:
  python apply_patch.py read <3mf_path>
      Prints current project_settings.config as JSON to stdout.

  python apply_patch.py write <3mf_path> <patch_json_path>
      Applies patch (delta only) and writes <name>_optimized.3mf
      to the same directory. Never modifies the original file.
      Automatically runs full audit after write.

  python apply_patch.py review <3mf_path>
      Prints a full human-readable audit of all critical settings,
      grouped by category. Flags values that look suspicious.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import json
import zipfile
import shutil
import os
import tempfile
from pathlib import Path

CONFIG_PATH = "Metadata/project_settings.config"

# ── Helpers ────────────────────────────────────────────────────────────────

def _val(settings: dict, key: str, default="—"):
    """Return scalar or first-element of array, or default."""
    v = settings.get(key, None)
    if v is None:
        return default
    if isinstance(v, list):
        return v[0] if v else default
    return v

def _arr(settings: dict, key: str):
    """Return list value, normalising scalar to single-element list."""
    v = settings.get(key, None)
    if v is None:
        return []
    return v if isinstance(v, list) else [v]

def _num(val):
    """Parse numeric string, return float or None."""
    try:
        return float(str(val).rstrip('%').strip())
    except (ValueError, TypeError):
        return None

# ── Core I/O ───────────────────────────────────────────────────────────────

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

# ── Audit / Review ─────────────────────────────────────────────────────────

def review_3mf(path: str) -> str:
    """
    Full line-by-line audit of critical settings. Returns formatted report string.
    Flags values that are likely wrong for the detected filament type or goal.
    """
    s = read_3mf(path)
    warnings = []
    lines = []

    def row(label, value, warn=None):
        flag = "  !!" if warn else "   "
        lines.append(f"  {flag} {label:<38} {value}")
        if warn:
            warnings.append(f"  !! {label}: {warn}")

    lines.append("")
    lines.append(f"{'='*62}")
    lines.append(f"  SETTINGS AUDIT — {Path(path).name}")
    lines.append(f"{'='*62}")

    # ── FILAMENT ──────────────────────────────────────────────
    lines.append("\n  FILAMENT")
    filament_id  = _val(s, 'filament_settings_id')
    filament_arr = _arr(s, 'filament_settings_id')
    nozzle_temp  = _val(s, 'nozzle_temperature')
    bed_temp     = _val(s, 'hot_plate_temp')
    fan_max      = _val(s, 'fan_max_speed')
    fan_min      = _val(s, 'fan_min_speed')
    vol_speed    = _val(s, 'filament_max_volumetric_speed')

    row("filament_settings_id", filament_id)
    row("nozzle_temperature",   f"{nozzle_temp}°C",
        "Very high — check stringing" if _num(nozzle_temp) and _num(nozzle_temp) > 270 else None)
    curr_bed = _val(s, 'curr_bed_type', '')
    bed_warn = None
    if "PETG" in filament_id.upper() and _num(bed_temp) and _num(bed_temp) < 65:
        if curr_bed not in ('Engineering Plate',):
            bed_warn = f"Low for PETG — use 70°C min (curr_bed_type={curr_bed or 'unknown'})"
    row("hot_plate_temp",       f"{bed_temp}°C", bed_warn)
    row("fan_max_speed",        f"{fan_max}%",
        "Too high for PETG — max 40%" if _num(fan_max) and _num(fan_max) > 50
        and "PETG" in filament_id.upper() else None)
    row("fan_min_speed",        f"{fan_min}%")
    row("filament_max_volumetric_speed", f"{vol_speed} mm³/s",
        "High for PolyMax — should be 4" if _num(vol_speed) and _num(vol_speed) > 8
        and "polymax" in filament_id.lower() else None)

    # ── QUALITY ───────────────────────────────────────────────
    lines.append("\n  QUALITY")
    layer_h = _val(s, 'layer_height')
    walls   = _val(s, 'wall_loops')
    top_sh  = _val(s, 'top_shell_layers')
    bot_sh  = _val(s, 'bottom_shell_layers')
    infill  = _val(s, 'sparse_infill_density')
    pattern = _val(s, 'sparse_infill_pattern')
    row("layer_height",         f"{layer_h} mm")
    row("wall_loops",           walls,
        "Low for structural/mold use" if _num(walls) and _num(walls) < 4 else None)
    row("top_shell_layers",     top_sh)
    row("bottom_shell_layers",  bot_sh)
    row("sparse_infill_density",infill,
        "Very low — mold masters need 30%+" if _num(infill) and _num(infill) < 20 else None)
    row("sparse_infill_pattern",pattern)

    # ── SPEED ─────────────────────────────────────────────────
    lines.append("\n  SPEED")
    lh  = _num(layer_h) or 0.2
    mvs = _num(vol_speed) or 999
    line_w = 0.42  # typical for 0.4mm nozzle

    def speed_warn(key_label, spd_val):
        n = _num(spd_val)
        if n is None:
            return None
        theoretical_max = mvs / (lh * line_w)
        if n > theoretical_max * 1.05:
            return f"Exceeds volumetric cap ({mvs} mm³/s → max ~{theoretical_max:.0f} mm/s)"
        if n > 100 and mvs < 10:
            return "Very fast for low-volumetric-speed material"
        return None

    speed_keys = [
        ("outer_wall_speed",           "Outer wall"),
        ("inner_wall_speed",           "Inner wall"),
        ("top_surface_speed",          "Top surface"),
        ("sparse_infill_speed",        "Sparse infill"),
        ("internal_solid_infill_speed","Internal solid infill"),
        ("initial_layer_speed",        "Initial layer"),
        ("initial_layer_infill_speed", "Initial layer infill"),
    ]
    for key, label in speed_keys:
        v = _val(s, key)
        if v == "—":
            continue
        row(label, f"{v} mm/s", speed_warn(label, v))

    # ── SUPPORT ───────────────────────────────────────────────
    lines.append("\n  SUPPORT")
    sup_en       = _val(s, 'enable_support')
    sup_type     = _val(s, 'support_type')
    sup_style    = _val(s, 'support_style')
    sup_z        = _val(s, 'support_top_z_distance')
    sup_z_bot    = _val(s, 'support_bottom_z_distance')
    sup_angle    = _val(s, 'support_threshold_angle')
    sup_crit     = _val(s, 'support_critical_regions_only')
    sup_iface_t  = _val(s, 'support_interface_top_layers')
    sup_iface_b  = _val(s, 'support_interface_bottom_layers')
    sup_ispace   = _val(s, 'support_interface_spacing')
    sup_xy       = _val(s, 'support_object_xy_distance')
    sup_base_sp  = _val(s, 'support_base_pattern_spacing')
    ind_height   = _val(s, 'independent_support_layer_height')

    row("enable_support",              sup_en)
    row("support_type",                sup_type)
    row("support_style",               sup_style)
    row("support_threshold_angle",     f"{sup_angle}°",
        "Low — may over-support organic geometry" if _num(sup_angle) and _num(sup_angle) < 38 else None)
    row("support_critical_regions_only", sup_crit)
    lh_num = _num(layer_h)
    sup_z_num = _num(sup_z)
    z_warn = None
    if sup_z_num is not None and lh_num and lh_num > 0:
        remainder = round(sup_z_num % lh_num, 6)
        if remainder > 0.001 and (lh_num - remainder) > 0.001:
            z_warn = f"Not a clean layer boundary (layer={lh_num}mm, remainder={remainder:.3f}mm)"
    row("support_top_z_distance",      f"{sup_z} mm", z_warn)
    row("support_bottom_z_distance",   f"{sup_z_bot} mm")
    row("support_interface_top_layers",sup_iface_t,
        "Interface with same-material PETG bonds aggressively — consider 0" if
        _num(sup_iface_t) and _num(sup_iface_t) > 0 and "PETG" in filament_id.upper() else None)
    row("support_interface_bottom_layers", sup_iface_b)
    row("support_interface_spacing",   f"{sup_ispace} mm")
    row("support_object_xy_distance",  f"{sup_xy} mm")
    row("support_base_pattern_spacing",f"{sup_base_sp} mm")
    row("independent_support_layer_height", ind_height)

    # ── WARNINGS SUMMARY ──────────────────────────────────────
    lines.append("")
    if warnings:
        lines.append(f"{'─'*62}")
        lines.append(f"  !! {len(warnings)} WARNING(S):")
        for w in warnings:
            lines.append(w)
    else:
        lines.append(f"  OK No warnings detected.")
    lines.append(f"{'='*62}")
    lines.append("")

    return "\n".join(lines)

# ── CLI ────────────────────────────────────────────────────────────────────

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
        print(review_3mf(out))

    elif mode == 'review':
        print(review_3mf(path))

    else:
        print(f"Error: unknown mode '{mode}'. Use 'read', 'write', or 'review'.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
