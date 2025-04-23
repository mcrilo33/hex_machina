import re
import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from ttd.utils.print import safe_pretty_print

DOTENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
if not load_dotenv(DOTENV_PATH):
    raise ValueError(f"Failed to load .env file from {DOTENV_PATH}")

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class PathResolver:
    def __init__(self, root: str):
        self.base_path = Path(root).resolve()

    def resolve_path(self, relative_path: Optional[str]) -> Path:
        """Resolves relative path under base path."""
        if not relative_path:
            return self.base_path
        return (self.base_path / relative_path).resolve()

    def resolve_env(self, env_key: str) -> str:
        """Resolves secret path under base path."""
        env_val = os.getenv(env_key)
        if env_val is None:
            raise ValueError(f"Missing environment variable: {env_key}")
        return env_val

    def resolve_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves all *_path and *_env_var keys in a flat or nested config dict.
        Modifies the config in-place.
        """
        def _resolve(obj: Dict[str, Any]):
            new_obj = {}
            for key, value in obj.items():
                if isinstance(value, dict):
                    new_obj[key] = _resolve(value)
                elif isinstance(value, str):
                    if key.endswith("_path") or  key.endswith("_dir"):
                        new_obj[key] = str(self.resolve_path(value))
                    elif key.endswith("_env_var"):
                        env_val = str(self.resolve_env(value))
                        base_key = key.replace("_env_var", "")
                        new_obj[base_key] = env_val
                    else:
                        new_obj[key] = value
                else:
                    new_obj[key] = value
            return new_obj
        return _resolve(config)
    

class OpenAIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict) and "json_data" in record.args:
            json_data = record.args["json_data"]
            messages = json_data.get("messages")
            if isinstance(messages, list):
                for msg in messages:
                    if "content" in msg:
                        msg["content"] = safe_pretty_print(msg["content"])
        return True

def setup_logging(debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    openai_logger = logging.getLogger("openai")
    openai_client_logger = logging.getLogger("openai._base_client")

    openai_logger.setLevel(logging.DEBUG if debug else logging.WARNING)
    openai_client_logger.setLevel(logging.DEBUG if debug else logging.WARNING)

    if debug:
        filter_ = OpenAIFilter()
        openai_logger.addFilter(filter_)
        openai_client_logger.addFilter(filter_)

def load_config(config_path: str = CONFIG_PATH):
    with open(config_path, "r") as f:
        yaml_config = yaml.safe_load(f)

    for key, value in yaml_config.items():
        if re.search(r'_dir$', key):
            yaml_config[key] = os.path.abspath(value)

    # Setup logging based on config
    setup_logging(debug=yaml_config.get("debug", False))

    return yaml_config

def load_path_resolver(config_path: str = CONFIG_PATH):
    config = load_config(config_path)
    return PathResolver(config["data_dir"])

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

