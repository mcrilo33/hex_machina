from hex.models.base_spec import ModelSpec
from hex.models.configs.openai_embedding_config import OpenAIEmbeddingConfig


TAG_EMBEDDING_SPEC = ModelSpec(
    name="tag_embedding_spec",
    version="v1",
    description="Calculates an embedding for a tag.",
    provider="openai_embedding",
    config=OpenAIEmbeddingConfig(
        model_name="text-embedding-3-large",
        matrix_cache_dir="models/text-embedding-3-large",
        api_key_env_var="OPENAI_API_KEY",
    )
)
