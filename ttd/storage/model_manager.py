import os
from datetime import datetime
from typing import Optional

from .ttd_storage import TTDStorage
from dotenv import load_dotenv

load_dotenv()  # Load .env vars, assuming it's not already done elsewhere


class ModelManager:
    def __init__(self, storage: TTDStorage):
        self.storage = storage

    def save_model(self, model: dict):
        assert 'name' in model
        model['created_at'] = datetime.utcnow().isoformat()
        model['last_updated'] = model['created_at']
        self.storage.insert('models', model)

    def update_model(self, model: dict):
        model['last_updated'] = datetime.utcnow().isoformat()
        self.storage.update('models', model['id'], model)

    def get_model(self, model_id: int) -> Optional[dict]:
        return self.storage.get_by_id('models', model_id)

    def get_model_by_name(self, name: str) -> Optional[dict]:
        # results = self.storage.query('models', where('name') == name)
        results = None
        return results[0] if results else None

    def load_model(self, name: str):
        """
        Loads and returns a model instance (e.g., an LLM client).
        """
        model = self.get_model_by_name(name)
        if not model:
            raise ValueError(f"Model '{name}' not found in registry.")

        if "openai" in model["endpoint"]:
            return self._load_openai_model(model)
        elif "anthropic" in model["endpoint"]:
            return self._load_claude_model(model)
        # Add more integrations as needed
        else:
            raise NotImplementedError(
                f"Model endpoint '{model['endpoint']}' not supported yet."
            )

    def _load_openai_model(self, model: dict):
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        return openai.ChatCompletion

    def _load_claude_model(self, model: dict):
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return client.messages
