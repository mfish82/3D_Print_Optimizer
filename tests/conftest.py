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
