import re
from abc import ABC, abstractmethod
from typing import Optional
from ttd.storage.artifact_manager import ArtifactManager
from ttd.models.base_spec import PromptSpec


class Prompt:
    def __init__(self, prompt_spec: PromptSpec):
        self.prompt_spec = prompt_spec
        self.template = prompt_spec.template
        self.placeholders = self._extract_placeholders()

    def _extract_placeholders(self):
        return set(re.findall(r"{([\w]+)}", self.template))

    def __call__(self, **kwargs):
        missing = self.placeholders - kwargs.keys()
        if missing:
            raise ValueError(f"Missing values for placeholders: {missing}")
        return self.template.format(**kwargs)

    def __repr__(self):
        return f"<Prompt(name={self.prompt_spec.name}, placeholders={self.placeholders})>"


class BaseModel(ABC):
    def __init__(self, config: dict, artifact_manager: Optional[ArtifactManager] = None):
        self.artifact_manager = artifact_manager
        self.config = self._prepare_config(config)

    def _prepare_config(self, config: dict) -> dict:
        if "prompt" in config:
            self.prompt = Prompt(config["prompt"])
        return config

    @abstractmethod
    def predict(self, input_data: dict) -> dict:
        pass