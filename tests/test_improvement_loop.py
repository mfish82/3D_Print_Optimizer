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
        settings = re.findall(r"`(\w+)`\s+.+→\s+(.+?)(?:\s+\(|$)", block, re.MULTILINE)

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
    """Verify improvement-agent-created patch files have all required keys."""
    patch_dir = Path(__file__).parent.parent / "patches"
    for patch_file in patch_dir.glob("*.json"):
        data = json.loads(patch_file.read_text(encoding="utf-8"))
        if "outcome_count" not in data:
            continue  # Bambu Studio profile export, not an improvement-agent patch
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
