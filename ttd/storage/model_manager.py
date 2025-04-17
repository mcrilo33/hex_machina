import os
import re
import copy
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import hashlib
import json
from ttd.utils import safe_pretty_print
from .ttd_storage import TTDStorage


class TemplateFiller:
    def __init__(self, template: str):
        self.template = template
        self.placeholders = self._extract_placeholders()

    def _extract_placeholders(self):
        return set(re.findall(r"{([\w]+)}", self.template))

    def __call__(self, **kwargs):
        missing = self.placeholders - kwargs.keys()
        if missing:
            raise ValueError(f"Missing values for placeholders: {missing}")
        return self.template.format(**kwargs)

    def __repr__(self):
        return f"<TemplateFiller with placeholders: {self.placeholders}>"


class BaseModel(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.input_format = config.get("input_format")
        self.output_format = config.get("output_format")
        self._validate_input_format()
        self._validate_output_format()
        self.expected_input_fields = \
            [f.strip() for f in self.input_format.split(",") if f.strip()]
        self.expected_output_fields = \
            [field.strip() for field in self.output_format.split(",") if field.strip()]
        self.is_list_fields = {}
        for field in self.expected_output_fields:
            is_list_expected = re.fullmatch(r"\[[\w_]+\]", field)
            key = field.strip("[]") if is_list_expected else field
            self.is_list_fields[key] = is_list_expected != None

    def predict(self, input: dict) -> dict:
        self._validate_input(input)
        output = self._predict(input)
        return output

    def expect_one_output(self):
        return (len(self.expected_output_fields) == 1 and
            not self.is_list_fields[self.expected_output_fields[0]])
        
    def _validate_input_format(self):
        if not isinstance(self.input_format, str) or not self.input_format:
            raise ValueError("input_format must be a non-empty string")
        fields = self.input_format.split(",")
        if not all(re.fullmatch(r"[\w_]+", field.strip()) for field in fields):
            raise ValueError(f"Invalid input_format: {self.input_format}")

    def _validate_output_format(self):
        if not isinstance(self.output_format, str) or not self.output_format:
            raise ValueError("output_format must be a non-empty string")
        fields = [field.strip() for field in self.output_format.split(",") if field.strip()]
        for field in fields:
            if not re.fullmatch(r"[\w_]+|\[[\w_]+\]", field):
                raise ValueError(f"Invalid output_format component: {field}")

    def _validate_input(self, input: dict):
        # If it expects one output, then the output format is free.
        if self.expect_one_output():
            return
        missing = set(self.expected_input_fields) - set(input.keys())
        if missing:
            error_msg = f"\nINPUT:\n{safe_pretty_print(input)}\n" + \
                f"INPUT_FORMAT: '{self.input_format}'\n" + \
                f"Missing input fields: {missing}"
            raise ValueError(error_msg)

    def validate_output(self, output: dict):
        assert 'output' in output
        output_fields = {}
        is_list_fields = {}
        for field,value in self.is_list_fields.items():
            output_fields[field] = 0
        raw_output = output['output']
        error_msg = f"\nOUTPUT: {safe_pretty_print(output)}\n" + \
                f"OUTPUT_FORMAT: '{self.output_format}'\n"
        # If it expects one output, then the output format is free.
        if self.expect_one_output():
            return
        for index,item in enumerate(raw_output):
            if not isinstance(item, dict):
                raise ValueError(error_msg + f"Expected output to be a list of dicts, got {type(item)} for output at position {index}") 
            if 'task_type' not in item:
                raise ValueError(error_msg + f"Task_type not in output at position {index}")  
            if 'value' not in item:
                raise ValueError(error_msg + f"Value not in output at position {index}")  
            if item['task_type'] not in output_fields:
                raise ValueError(error_msg + f"Invalid task_type :'{item['task_type']}', not in output_format :'{self.output_format}' for output at position {index}")
            output_fields[item['task_type']] += 1
            if output_fields[item['task_type']] > 1 and not is_list_fields[item['task_type']]:
                raise ValueError(error_msg + f"Multiple values for task_type :'{item['task_type']}' while it is not a list field in output_format :'{self.output_format}'")
        for key,value in output_fields.items():
            if value == 0:
                raise ValueError(error_msg + f"Output missing expected key '{key}'")

    @abstractmethod
    def _predict(self, input_data: dict) -> dict:
        pass


class OpenAIModel(BaseModel):
    def __init__(self, config: dict):
        super().__init__(config)
        from openai import OpenAI

        model_config = config["config"]["openai"]
        assert "api_key_env_var" in model_config
        assert "base_url" in model_config
        assert "template" in model_config

        self.template = TemplateFiller(model_config["template"])
        api_key = os.getenv(model_config["api_key_env_var"])

        client = OpenAI(
            base_url=model_config["base_url"],
            api_key=api_key,
        )

        self.model_name = model_config["model"]

        del model_config["base_url"]
        del model_config["api_key_env_var"]
        del model_config["model"]
        del model_config["template"]

        self.client = client
        self.config = model_config

    def _predict(self, input_data: dict) -> dict:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": self.template(**input_data)}],
            **self.config
        )

        if hasattr(response, 'error'):
            message = response.error.get('message', 'No message')
            code = response.error.get('code', 'No code')
            provider = response.error.get("metadata").get('provider_name', 'Unknown provider').upper()
            raise ValueError(f"PROVIDER [[{provider}]]\n== Error {code}: {message}")

        return {
            "output": response.choices[0].message.content.strip(),
            "metadata": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }


class OpenAIEmbedding():
    def __init__(self, config: dict):
        from openai import OpenAI

        model_config = config["config"]["openai_embedding"]
        assert "api_key_env_var" in model_config

        api_key = os.getenv(model_config["api_key_env_var"])

        self.client = OpenAI(api_key=api_key)
        self.model_name = model_config["model"]
        self.config = model_config

        # Prepare cache
        self.cache_path = model_config.get("cache_path", "embedding_cache.json")
        self._load_cache()

        # Clean up config
        del model_config["api_key_env_var"]
        del model_config["model"]
        model_config.pop("cache_path", None)

    def _load_cache(self):
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r") as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump(self.cache, f, indent=2)

    def _hash_input(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def predict(self, input_text: dict) -> dict:
        input_key = self._hash_input(input_text)

        # Check cache
        if input_key in self.cache:
            return {
                "output": self.cache[input_key]["embedding"],
                "metadata": self.cache[input_key]["metadata"]
            }

        # Make API call
        response = self.client.embeddings.create(
            input=input_text,
            model=self.model_name
        )

        embedding = response.data[0].embedding
        metadata = {
            "model": response.model,
            "object": response.object,
            "usage": dict(response.usage) if hasattr(response, "usage") else {},
        }

        # Save to cache
        self.cache[input_key] = {
            "text": input_text,
            "embedding": embedding,
            "metadata": metadata,
        }
        self._save_cache()

        return {
            "output": embedding,
            "metadata": metadata
        }


class ModelManager:
    def __init__(self, storage: TTDStorage):
        self.storage = storage

    def _validate_input_format_usage_with_template(self, model):
        input_format = model.get("input_format", "")
        template = model.get("config", {}).get("openai", {}).get("template", "")

        input_fields = [field.strip() for field in input_format.split(",") if field.strip()]
        template_fields = re.findall(r"{([^{}]+)}", template, re.DOTALL)

        unused_inputs = [field for field in input_fields if field not in template_fields]
        error_msg = "\nINPUT FORMAT: '" + input_format + f"'\nTEMPLATE: {safe_pretty_print(template)}\n"
        if unused_inputs:
            raise ValueError(
                error_msg + f"The following input fields from 'input_format' are not used in the template: {unused_inputs}"
            )

        missing_inputs = [field for field in template_fields if field not in input_fields]
        if missing_inputs:
            raise ValueError(
                error_msg + f"The following fields are used in the template but missing from 'input_format': {missing_inputs}"
            )

    def save(self, model: dict):
        return model

    def update(self, model: dict):
        return model

    def load(self, model):
        model = copy.deepcopy(model)
        assert "config" in model

        if "openai" in model["config"]:
            if "input_format" in model and "template" in model['config']['openai']:
                self._validate_input_format_usage_with_template(model)
            return OpenAIModel(model)
        
        elif "openai_embedding" in model["config"]:
            return OpenAIEmbedding(model)

        raise NotImplementedError(
            f"Model endpoint '{model['endpoint']}' not supported yet."
        )
