import os
import re
import copy
from datetime import datetime
from pathlib import Path
from ttd.utils import safe_pretty_print
from .ttd_storage import TTDStorage

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
        if hasattr(response, 'error'):
            error = response.error
            message = response.error.get('message', 'No message')
            code = response.error.get('code', 'No code')
            provider = response.error.get("metadata").get(
                'provider_name',
                'Unknown provider'
            ).upper()
            raise ValueError(f"PROVIDER [[{provider}]]\n== Error {code}: {message}")
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

    def _validate_input_format_usage_with_template(self, model):
        input_format = model.get("input_format", "")
        template = model.get("config", {}).get("openai", {}).get("template", "")

        input_fields = [field.strip() for field in input_format.split(",") if field.strip()]
        template_fields = re.findall(r"{([^{}]+)}", template, re.DOTALL)

        # Check if every input field is used in the template
        unused_inputs = [field for field in input_fields if field not in template_fields]
        error_msg = "\nINPUT FORMAT: '"\
            + input_format + f"'\nTEMPLATE: {safe_pretty_print(template)}\n"
        if unused_inputs:
            raise ValueError(
                error_msg+f"The following input fields from 'input_format' are not used in the template: {unused_inputs}"
            )

        # Check if every template field is present in input_format
        missing_inputs = [field for field in template_fields if field not in input_fields]
        if missing_inputs:
            raise ValueError(
                error_msg+f"The following fields are used in the template but missing from 'input_format': {missing_inputs}"
            )

    def save(self, model: dict):
        return model

    def update(self, model: dict):
        return model

    def load(self, model):
        """
        Loads and returns a model instance (e.g., an LLM client).
        """
        assert "config" in model

        if "input_format" in model and "template" in model['config']['openai']:
            self._validate_input_format_usage_with_template(model)
        if "openai" in model["config"]:
            return OpenAIModel(model['config']['openai'])
        # Add more integrations as needed
        else:
            raise NotImplementedError(
                f"Model endpoint '{model['endpoint']}' not supported yet."
            )
