from pydantic import BaseModel, Field

from ttd.models.base_spec import ModelSpec, PromptTemplateSpec
from ttd.models.configs.open_router_config import OpenRouterConfig


class DenseSummarizerInput(BaseModel):
    """Schema for dense summarizer input."""
    title: str = Field(..., description="The title of the article")
    text_content: str = Field(
        ..., description="The main content of the article"
    )


class DenseSummarizerOutput(BaseModel):
    """Schema for dense summarizer output."""
    output: str = Field(..., description="Dense summary of the article")


DENSE_SUMMARIZER_PROMPT = PromptTemplateSpec(
    name="dense_summarizer_prompt",
    version="v1.0.0",
    description="Extract a dense summary from an article.",
    input_schema=DenseSummarizerInput,
    output_schema=DenseSummarizerOutput,
    template="""
You are an expert summarizer trained to produce high-density, information-rich summaries.

Your goal is to condense an article into the **shortest possible summary that preserves every critical point**:
- Facts, arguments, results, conclusions
- Technical terms and named entities
- No repetition or fluff
- No commentary, opinions, or rhetorical questions

You are **not optimizing for readability**. You are **optimizing for signal-to-noise ratio**.
Each sentence should carry **maximum unique information**.

You will be given:
- An article title
- The full article text

---

TITLE:
\"\"\"{title}\"\"\"
ARTICLE:
\"\"\"{text_content}\"\"\"

---

Your task:
Write the most **compressed and factual summary** possible (in under 300 words). Use neutral language. Do **not** include the title or metadata. Return only the summary.
"""
)

DENSE_SUMMARIZER_SPEC = ModelSpec(
    name="dense_summarizer_spec",
    version="v1",
    description="Extracts a dense summary from an article.",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=DENSE_SUMMARIZER_PROMPT,
        model_name="meta-llama/llama-4-maverick:free",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )
)
