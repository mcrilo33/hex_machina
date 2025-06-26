from pydantic import BaseModel, Field, model_validator

from hex.models.base_spec import ModelSpec, PromptTemplateSpec
from hex.models.configs.open_router_config import OpenRouterConfig


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
You are an expert AI content classifier.

Your task is to extract a **clean, meaningful list of tags** from a dense article summary.
These tags will be used to group related articles in a knowledge graph and recommendation system, helping discover relevant AI topics.

Tagging Guidelines:
Ordering:
    - Begin with the most relevant, central themes of the article.
    - Within the same level of relevance, prefer more general tags before narrower ones.
Tag Types:
    - Key technical topics (e.g., “generative AI”, “reinforcement learning”)
    - Broader themes or domains (e.g., “AI policy”, “robotics”)
    - Named entities if they are central (e.g., “OpenAI”, “Google DeepMind”, “Anthropic”)
Selection Criteria:
    - Include only core topics that capture the article’s main message.
    - Tags must be useful for grouping related content — avoid overly niche or idiosyncratic terms.
    - All tags must be mutually distinct:
        - Do not include synonyms, abbreviations, or variations of tags already listed.
        - When in doubt, prefer the full descriptive form (e.g., “large language models” over “LLMs”).
        - Use standardized, recognizable terms common in professional and academic contexts.
    - Avoid duplicates, partial overlaps, or redundant phrases.
    - Return 3 to 7 tags, unless the content clearly supports more.

You will be provided with:
- A dense summary of the article.

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
        model_name="google/gemini-2.5-flash",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )

)
