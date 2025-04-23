import pytest
import warnings
import os
import shutil
from datetime import datetime
import yaml
from ttd.utils.config import update_config, load_config, CONFIG_FILE


def test_config_has_required_fields():
    config = load_config()

    assert "db_path" in config, "Missing 'db_path' in data section"
    assert "last_scrape" in config, "Missing 'last_scrape' in data section"

    assert isinstance(config["db_path"], str)

    if not config["last_scrape"]:
        warnings.warn("'last_scrape' path is empty in config.yaml")
    else:
        assert isinstance(config["last_scrape"], str)

def test_last_scrape_file_can_be_parsed_or_null():
    config = load_config()
    path = config["last_scrape"]

    if not path:
        pytest.skip("No path set for 'last_scrape' in config")

    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read().strip()
            try:
                dt = datetime.fromisoformat(content)
                assert isinstance(dt, datetime)
            except ValueError:
                pytest.fail("The 'last_scrape' file does not contain a valid ISO datetime.")

@pytest.fixture
def temp_config_file(tmp_path):
    # Copy original config.yaml to a temp location
    temp_file = tmp_path / "config.yaml"
    shutil.copy(CONFIG_FILE, temp_file)

    # Patch CONFIG_FILE to point to this temp file
    original_path = CONFIG_FILE
    import ttd.utils.config as config_module
    config_module.CONFIG_FILE = temp_file
    yield temp_file

    # Restore original CONFIG_FILE
    config_module.CONFIG_FILE = original_path


def test_update_config_modifies_yaml(temp_config_file):
    test_value = datetime(2024, 3, 28).isoformat()

    update_config({
        "last_scrape": test_value
    })

    config = load_config()
    assert config["last_scrape"] == test_value

    # Also directly load the YAML to verify it was saved to disk
    with open(temp_config_file, "r") as f:
        raw = yaml.safe_load(f)
        assert raw["last_scrape"] == test_value