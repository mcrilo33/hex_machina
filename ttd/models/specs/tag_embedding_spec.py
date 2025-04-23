from ttd.models.base_spec import ModelSpec, PromptSpec

TAG_EMBEDDING_SPEC = ModelSpec(
    name="tag_embedding_spec",
    version="v1",
    input_schema="tagger__output",
    output_schema="tag_embedding",
    description="Calculates an embedding for a tag.",
    provider="openai_embedding",
    config={
        "model_name": "text-embedding-3-large",
        "matrix_cache_dir": "models/text-embedding-3-large",
        "api_key_env_var": "OPENAI_API_KEY",
        "max_tokens": 5000,
        "n": 1,
        # "dimensions": 1536  # Only supported in text-embedding-3 and later models.
    }
)