""" Test the config file. """
import pytest
import warnings
import os
from datetime import datetime
from ttd.utils.config import load_config


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
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            try:
                dt = datetime.fromisoformat(content)
                assert isinstance(dt, datetime)
            except ValueError:
                pytest.fail(
                    "The 'last_scrape' file does not contain a valid ISO datetime."
                )
