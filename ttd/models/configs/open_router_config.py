from typing import Optional
from pydantic import BaseModel, Field
from ttd.models.base_spec import PromptTemplateSpec


class OpenRouterConfig(BaseModel):
    """Configuration for OpenRouter API model."""
    prompt_spec: PromptTemplateSpec = Field(
        default=None, description="Prompt specification"
    )
    base_url: str = Field(
        "https://openrouter.ai/api/v1", description="API base URL"
    )
    model_name: str = Field(
        "meta-llama/llama-4-maverick:free", description="Model name / identifier"
    )
    api_key_env_var: Optional[str] = Field(
        "OPENROUTER_API_KEY", description="Environment variable for API key"
    )
    api_key: Optional[str] = Field(None, description="API key")
    temperature: Optional[float] = Field(0.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(5000, description="Maximum tokens to generate")
    n: Optional[int] = Field(1, description="Number of completions to generate")
