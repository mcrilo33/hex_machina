from typing import Optional
from pydantic import BaseModel, Field


class OpenAIEmbeddingConfig(BaseModel):
    """Configuration for OpenAI Embedding API model."""
    model_name: str = Field(
        "text-embedding-3-large", description="Model name/identifier"
    )
    matrix_cache_dir: Optional[str] = Field(
        None, description="Directory to cache matrix data"
    )
    api_key_env_var: Optional[str] = Field(
        "OPENAI_API_KEY", description="Environment variable for API key"
    )
    api_key: Optional[str] = Field(None, description="API key")
    # Only supported in text-embedding-3 and later models.
    dimensions: Optional[int] = Field(
        None, description="Number of dimensions for the embedding"
    )
