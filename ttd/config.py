import re
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path)

CONFIG_FILE = Path(__file__).parent / "config.yaml"

def load_config_and_dotenv():
    load_dotenv()
    with open(CONFIG_FILE, "r") as f:
        yaml_config = yaml.safe_load(f)
    for key, value in yaml_config.items():
        if re.search(r'_path$', key):
            yaml_config[key] = os.path.abspath(yaml_config[key])
    return yaml_config

def update_config(new_data: dict):
    config = load_config_and_dotenv()

    # Deep merge new_data into config
    for section, updates in new_data.items():
        if section in config and isinstance(config[section], dict):
            config[section].update(updates)
        else:
            config[section] = updates

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, sort_keys=False)