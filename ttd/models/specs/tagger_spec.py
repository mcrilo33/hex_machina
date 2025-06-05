from pydantic import BaseModel, Field, model_validator

from ttd.models.base_spec import ModelSpec, PromptTemplateSpec
from ttd.models.configs.open_router_config import OpenRouterConfig


class TaggerInput(BaseModel):
    """Schema for tagger input data."""
    output: str = Field(
        ..., description="A dense summary of the article"
    )


class TaggerOutput(BaseModel):
    """Schema for tagger output."""
    output: list[str] = Field(
        ..., description="A list of tags for the article"
    )

    @model_validator(mode='before')
    def validate_output(item):
        tags = item["output"].strip()
        tags = tags.split(",")
        tags = [tag.strip() for tag in tags]
        item["output"] = tags
        return item


TAGGER_PROMPT = PromptTemplateSpec(
    name="tagger_prompt",
    version="v1.0.0",
    description="Find the most relevant tags for an article.",
    input_schema=TaggerInput,
    output_schema=TaggerOutput,
    template="""
You are a professional AI content classifier.

Your task is to extract a **clean, concise list of tags** from a dense summary of an article.
These tags will be used to group related articles in a knowledge graph and recommendation system.

**Order the tags** by relevance and generality:
1. Start with the tags that best represent the article's main theme.
2. Between same relevance tags, prefer the most general ones first.

Your output must follow these rules:

- Tags must represent the **core themes or subjects** of the article — only include tags essential to its message.
- Tags must be **useful for grouping** articles by shared topics - avoid overly specific tags.
- Tags must be **mutually distinct**:
    - Do **not include synonyms, variants, or abbreviations of other tags** already listed (e.g., "large language models" and "LLMs" — choose only one).
    - When multiple forms of a concept exist, **always prefer the full descriptive form** (e.g., "large language models" instead of "LLMs").
    - Use **standardized, recognizable terminology**.
- Do **not include duplicates**, partial matches, or overlapping phrases.
- Keep the list between 3 and 7 tags, unless the content clearly demands more.

You will be provided with:
- A dense summary of the article

---

DENSE SUMMARY:
\"\"\"{output}\"\"\"

---

Return a **comma-separated list** of clean, distinct tags.
Example: `large language models,generative AI,AI ethics,medical imaging`

Do **not** include duplicates, synonyms, or near-duplicates.
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
        model_name="google/gemini-2.0-flash-001",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )

)
