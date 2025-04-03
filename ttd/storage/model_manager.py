import os
from dotenv import load_dotenv
from datetime import datetime
from .ttd_storage import TTDStorage
from pathlib import Path

dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path)


class OpenAIModel:
    def __init__(self, config: dict):
        from openai import OpenAI
        assert "api_key_env_var" in config
        assert "base_url" in config

        api_key = os.getenv(config["api_key_env_var"])
        self.client = OpenAI(
            base_url=config["base_url"],
            api_key=api_key,
        )
        self.model_name = config["model"]
        del config["base_url"]
        del config["api_key_env_var"]
        del config["model"]
        self.config = config

    def predict(self, article: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": article}],
            **self.config
        )
        return response.choices[0].message.content.strip()


class ModelManager:
    def __init__(self, storage: TTDStorage):
        self.storage = storage

    def save_model(self, model: dict):
        model['created_at'] = datetime.utcnow().isoformat()
        model['last_updated'] = model['created_at']

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
