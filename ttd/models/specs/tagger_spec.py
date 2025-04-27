from pydantic import BaseModel, Field, model_validator

from ttd.models.base_spec import ModelSpec, PromptTemplateSpec
from ttd.models.configs.open_router_config import OpenRouterConfig


class TaggerInput(BaseModel):
    """Schema for tagger input data."""
    dense_summarizer__output: str = Field(
        ..., description="A dense summary of the article"
    )


class TaggerOutput(BaseModel):
    """Schema for tagger output."""
    tags: list[str] = Field(
        ..., description="A list of tags for the article"
    )

    @model_validator(mode='before')
    def from_string(item):
        tags = item["tags"].strip()
        tags = tags.split(",")
        tags = [tag.strip() for tag in tags]
        item["tags"] = tags
        return item


TAGGER_PROMPT = PromptTemplateSpec(
    name="tagger_prompt",
    version="v1.0.0",
    description="Find the most relevant tags for an article.",
    input_schema=TaggerInput,
    output_schema=TaggerOutput,
    template="""
You are a professional AI content classifier.

Your task is to extract a **clean, concise list of tags** from a dense summary of an article. These tags will be used to group related articles.
**Order the tags** by importance (most important first).

Your output must follow these rules:

- Tags must represent the **core themes or subjects** of the article — only include tags for concepts that are essential to its message.
- Tags must be **useful for grouping** articles that share similar topics — don't be overly specific.
- Tags must be **mutually distinct**:
    - **Avoid duplicates**: Do not include synonyms or overlapping terms (e.g., "LLMs" and "large language models" — keep only one).
    - If two tags represent the same idea, pick the **most general and recognizable** form.
    - Prefer normalized, standardized wording when possible (e.g., use “AI safety” instead of “safety in artificial intelligence”).

You will be provided with:
- A dense summary of the article

---

DENSE SUMMARY:
\"\"\"{dense_summarizer__output}\"\"\"

---

Return a **comma-separated list** of clean, distinct tags.
Example: `LLMs,generative AI,AI ethics,medical imaging`
Do **not** include duplicates, synonyms, or very similar tags.
Do **not** add quotes, explanations, or formatting — just return the list.
"""
)

TAGGER_SPEC = ModelSpec(
    name="tagger_spec",
    version="v1",
    description="Extracts a dense summary from an article.",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=TAGGER_PROMPT,
        model_name="openai/gpt-3.5-turbo",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )

)
