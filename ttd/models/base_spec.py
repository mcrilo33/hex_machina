import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from ttd.utils.print import safe_pretty_print
from ttd.utils.config import load_path_resolver


FIELD_PATH_PATTERN = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)(__[a-zA-Z_][a-zA-Z0-9_]*)*$')


def _validate_schema_format(v: str, field_name: str) -> str:
    fields = [f.strip() for f in v.split(",") if f.strip()]
    for field_str in fields:
        if not FIELD_PATH_PATTERN.match(field_str):
            raise ValueError(f"Invalid field format in `{field_name}`: '{field_str}'")
    return v


def _parse_schema(schema_str: str) -> Dict:
    fields = schema_str.split(',')
    return {f.strip(): True for f in fields if f.strip()}


class BaseSpec(BaseModel):
    name: str = Field(..., description="Unique identifier for this spec.")
    version: str = Field(..., description="Semantic version (e.g., v1.0.0).")
    description: Optional[str] = Field(None, description="Optional human-readable description.")
    input_schema: str = Field(..., description="Comma-separated list of input fields (nested using '__').")
    output_schema: str = Field(..., description="Comma-separated list of output fields (nested using '__').")

    @field_validator("input_schema")
    @classmethod
    def validate_input_schema(cls, v: str) -> str:
        return _validate_schema_format(v, "input_schema")

    @field_validator("output_schema")
    @classmethod
    def validate_output_schema(cls, v: str) -> str:
        return _validate_schema_format(v, "output_schema")

    def parsed_input_schema(self) -> Dict:
        return _parse_schema(self.input_schema)

    def parsed_output_schema(self) -> Dict:
        return _parse_schema(self.output_schema)


class PromptSpec(BaseSpec):
    template: str = Field(..., description="Jinja-style template with placeholders from input_schema.")


class ModelSpec(BaseSpec):
    def __init__(self, **data):
        super().__init__(**data)
        self.config = load_path_resolver().resolve_config(self.config)
            
    model_id: Optional[str] = None
    provider: str = Field(..., description="Name of the model provider (e.g., 'openai').")
    config: Dict[str, Any] = Field(..., description="Model configuration (temperature, etc.)")
    _loaded_model: Optional[Any] = None

    @property
    def prompt(self) -> Optional[PromptSpec]:
        if "prompt" in self.config:
            return self.config["prompt"]
        return None


# === Prompt Compatibility Validation ===

def validate_input_prompt_compatibility(model_spec: ModelSpec):
    if model_spec.input_schema and "prompt" in model_spec.config:
        input_fields = _parse_schema(model_spec.input_schema)
        template = model_spec.config["prompt"].template
        prompt_fields = re.findall(r"{([^{}]+)}", template, re.DOTALL)

        error_msg = f"\nINPUT FORMAT: '{model_spec.input_schema}'\nprompt: {safe_pretty_print(template)}\n"

        unused_inputs = [f for f in input_fields if f not in prompt_fields]
        if unused_inputs:
            raise ValueError(error_msg + f"Unused input fields from `input_schema`: {unused_inputs}")

        missing_inputs = [f for f in prompt_fields if f not in input_fields]
        if missing_inputs:
            raise ValueError(error_msg + f"Missing input fields from `input_schema`: {missing_inputs}")
