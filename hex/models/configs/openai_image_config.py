from typing import Optional
from pydantic import BaseModel, Field
from hex.models.base_spec import PromptTemplateSpec

class OpenAIImageConfig(BaseModel):
    prompt_spec: PromptTemplateSpec = Field(
        ..., description="Prompt specification"
    )
    model: str = Field(
        "dall-e-3", description="Image model name"
    )
    size: str = Field(
        "1792x1024", description="Image size"
    )
    quality: str = Field(
        "hd", description="Image quality"
    )
    api_key_env_var: Optional[str] = Field(
        "OPENAI_API_KEY", description="Environment variable for API key"
    )
    api_key: Optional[str] = Field(
        None, description="API key"
    )
    response_format: str = Field(
        "b64_json", description="Response format"
    )
    n: int = Field(
        1, description="Number of images to generate"
    )