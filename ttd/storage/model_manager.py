import os
import copy
from dotenv import load_dotenv
from datetime import datetime
from .ttd_storage import TTDStorage
from pathlib import Path

dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path)

class TemplateFiller:
    def __init__(self, template: str):
        self.template = template
        self.placeholders = self._extract_placeholders()

    def _extract_placeholders(self):
        import re
        return set(re.findall(r"{([\w]+)}", self.template))

    def __call__(self, **kwargs):
        missing = self.placeholders - kwargs.keys()
        if missing:
            raise ValueError(f"Missing values for placeholders: {missing}")
        return self.template.format(**kwargs)

    def __repr__(self):
        return f"<TemplateFiller with placeholders: {self.placeholders}>"


class OpenAIModel:
    def __init__(self, config: dict):
        from openai import OpenAI
        assert "api_key_env_var" in config
        assert "base_url" in config
        assert "template" in config
        config = copy.deepcopy(config)

        self.template = TemplateFiller(config["template"])
        api_key = os.getenv(config["api_key_env_var"])
        self.client = OpenAI(
            base_url=config["base_url"],
            api_key=api_key,
        )
        self.model_name = config["model"]
        del config["base_url"]
        del config["api_key_env_var"]
        del config["model"]
        del config["template"]
        self.config = config

    def predict(self, input: dict) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": self.template(**input)}],
            **self.config
        )
        response = {
            "output": response.choices[0].message.content.strip(),
            "metadata": {
                         "prompt_tokens": response.usage.prompt_tokens,
                         "completion_tokens": response.usage.completion_tokens,
                         "total_tokens": response.usage.total_tokens
            }
        }
        return response


class ModelManager:
    def __init__(self, storage: TTDStorage):
        self.storage = storage

    def save_model(self, model: dict):
        return model

    def update_model(self, model: dict):
        model['last_updated'] = datetime.utcnow().isoformat()
        return model

    def load_model(self, model):
        """
        Loads and returns a model instance (e.g., an LLM client).
        """
        assert "config" in model

        if "openai" in model["config"]:
            return OpenAIModel(model['config']['openai'])
        # Add more integrations as needed
        else:
            raise NotImplementedError(
                f"Model endpoint '{model['endpoint']}' not supported yet."
            )
