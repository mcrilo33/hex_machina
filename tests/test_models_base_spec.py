import pytest
from pydantic import BaseModel
from typing import Optional, Any

from ttd.models.base_spec import BaseSpec, PromptTemplateSpec, ModelSpec


class DummyInput(BaseModel):
    text: str


class DummyOutput(BaseModel):
    result: str


class DummyConfig(BaseModel):
    param: int
    prompt_spec: Optional[Any] = None
    api_key: str = "dummy_api_key"
    model_name: str = "text-embedding-ada-002"
    matrix_cache_dir: str = "/tmp/cache"
    dimensions: Optional[int] = None


@pytest.fixture
def basic_spec_data():
    return {
        "name": "basic_spec",
        "version": "v1.0",
        "description": "A simple spec",
        "input_schema": DummyInput,
        "output_schema": DummyOutput,
    }


def test_basespec_validate_input_and_output(basic_spec_data):
    spec = BaseSpec(**basic_spec_data)

    input_data = {"text": "Hello"}
    output_data = {"result": "World"}

    validated_input = spec.validate_input(input_data)
    validated_output = spec.validate_output(output_data)

    assert isinstance(validated_input, DummyInput)
    assert validated_input.text == "Hello"
    assert isinstance(validated_output, DummyOutput)
    assert validated_output.result == "World"


def test_prompt_template_spec_fields(basic_spec_data):
    spec = PromptTemplateSpec(
        **basic_spec_data,
        template="Hello {{ text }}!"
    )

    assert spec.template == "Hello {{ text }}!"
    assert spec.input_schema == DummyInput
    assert spec.output_schema == DummyOutput


def test_model_spec_check_schema_presence_conflict():
    """Check ValueError when both schemas and prompt_spec exist."""

    class FakePromptSpec(BaseModel):
        input_schema: Optional[Any] = None
        output_schema: Optional[Any] = None

    dummy_config = DummyConfig(param=1, prompt_spec=FakePromptSpec())

    with pytest.raises(ValueError):
        ModelSpec(
            name="conflict_spec",
            version="v1",
            description="Conflict test",
            provider="openai",
            config=dummy_config,
            input_schema=DummyInput,
            output_schema=DummyOutput
        )
