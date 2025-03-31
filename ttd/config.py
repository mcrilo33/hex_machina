import yaml
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.yaml"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)

def update_config(new_data: dict):
    config = load_config()

    # Deep merge new_data into config
    for section, updates in new_data.items():
        if section in config and isinstance(config[section], dict):
            config[section].update(updates)
        else:
            config[section] = updates

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, sort_keys=False)