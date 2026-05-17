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
