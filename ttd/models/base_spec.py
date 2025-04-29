from typing import Any, Optional, Type, TypeVar
from pydantic import BaseModel, Field, model_validator

from ttd.utils.config import load_path_resolver
from ttd.models.providers.openai_model import OpenAIModel
from ttd.models.providers.openai_embedding import OpenAIEmbedding

InputType = TypeVar('InputType', bound=BaseModel)
OutputType = TypeVar('OutputType', bound=BaseModel)
ModelConfig = TypeVar('ModelConfig', bound=BaseModel)

def extract_nested_fields_from_schema(schema: type(BaseModel), inputs: dict) -> dict:
    """Extract fields matching model_class from possibly nested inputs."""
    result = {}
    for field in schema.__fields__:
        keys = field.split("__")  # Split field into nested keys
        value = inputs
        try:
            for key in keys:
                value = value[key]
            result[field] = value
        except (KeyError, TypeError):
            raise ValueError(
                f"Field '{field}' not found in input data. "
                f"Expected structure: {model_class.__fields__}"
            )
    return result

class BaseSpec(BaseModel):
    """Base class for all specs with common fields."""
    name: str = Field(..., description="Unique identifier for this spec.")
    version: str = Field(..., description="Semantic version (e.g., v1.0.0).")
    description: Optional[str] = \
        Field(None, description="Optional human-readable description.")
    input_schema: Optional[Type[InputType]] = \
        Field(None, description="Schema for model inputs.")
    output_schema: Optional[Type[OutputType]] = \
        Field(None, description="Schema for model outputs.")

    # Use model_config for Pydantic v2
    model_config = {
        "arbitrary_types_allowed": True,
    }

    def extract_and_validate_input(self, data: Any) -> InputType:
        """Extract and validate input data against the input schema."""
        extracted = extract_nested_fields_from_schema(self.input_schema, data)
        self.input_schema.model_validate(extracted)
        return extracted

    def validate_output(self, data: Any) -> OutputType:
        """Validate output data against the output schema."""
        self.output_schema.model_validate(data)
        return data


class PromptTemplateSpec(BaseSpec):
    """Specification for prompt templates."""
    template: str = \
        Field(..., description="Jinja-style template with " +
                               "placeholders from input_schema.")
    input_schema: Type[InputType] = \
        Field(..., description="Schema for prompt inputs.")
    output_schema: Type[OutputType] = \
        Field(..., description="Schema for prompt outputs.")


class ModelSpec(BaseSpec):
    """Base class for model specifications."""
    def __init__(self, **data):
        super().__init__(**data)

    model_id: Optional[str] = None
    provider: str = \
        Field(..., description="Name of the model provider (e.g., 'openai').")
    config: ModelConfig = \
        Field(..., description="Model configuration (temperature, etc.)")
    _loaded_model: Optional[Any] = None

    def load_model(self):
        """ Load the model instance based on the given provider and config.
        """

        if self.provider == "openai":
            self._loaded_model = OpenAIModel(self.config)

        elif self.provider == "openai_embedding":
            self._loaded_model = OpenAIEmbedding(self.config)

        else:
            raise NotImplementedError(
                f"No model provider found for given name: {self.provider}"
            )

    @model_validator(mode='after')
    def resolve_config_paths(self):
        """Resolve configuration paths after model initialization."""
        self.config = load_path_resolver().resolve_config(self.config)
        return self

    @model_validator(mode='after')
    def set_prompt_schemas(self):
        """Set input and output schemas based on prompt specification
        if available."""
        if self.config is not None and hasattr(self.config, "prompt_spec"):
            prompt_spec = self.config.prompt_spec
            if prompt_spec is not None:
                self.input_schema = prompt_spec.input_schema
                self.output_schema = prompt_spec.output_schema
        return self

    @model_validator(mode='before')
    def check_schemas_presence(self):
        """Check if input or output schema is specified
        when there's a prompt specification."""
        if "config" in self and hasattr(self["config"], "prompt_spec"):
            if "input_schema" in self or "output_schema" in self:
                raise ValueError(
                    "Input or output schema should not be specified \
                    when there's a prompt specification.")
        return self
