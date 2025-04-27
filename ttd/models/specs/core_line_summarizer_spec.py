from pydantic import BaseModel, Field

from ttd.models.base_spec import ModelSpec, PromptTemplateSpec
from ttd.models.configs.open_router_config import OpenRouterConfig


class CoreLineSummarizerInput(BaseModel):
    """Schema for core line summarizer input data."""
    dense_summarizer__output: str = Field(
        ..., description="A dense summary of the article"
    )


class CoreLineSummarizerOutput(BaseModel):
    """Schema for core line summarizer output."""
    core_line_summary: str = Field(
        ..., description="A single-sentence summary of the dense summary"
    )


CORE_LINE_SUMMARIZER_PROMPT = PromptTemplateSpec(
    name="core_line_summarizer_prompt",
    version="v1.0.0",
    description="Extract a core line from an article",
    input_schema=CoreLineSummarizerInput,
    output_schema=CoreLineSummarizerOutput,
    template="""
You are a professional summarizer tasked with producing a **single-sentence summary** that captures the **main idea and significance** of a dense technical or factual summary.

Your summary must be:
- **Concise**: 1 sentence only (ideally under 30 words)
- **Clear**: Use plain, direct, and factual language
- **Focused**: Emphasize the core message and why it matters
- **No fluff**: Avoid generic phrases, opinions, or vague statements

You will be given:
- A dense summary of an article

---

DENSE SUMMARY:
\"\"\"{dense_summarizer__output}\"\"\"

---

Write a one-line summary that highlights the **key point** and its **relevance**.
Return only the sentence — no bullet points, titles, or extra text.
"""
)

CORE_LINE_SUMMARIZER_SPEC = ModelSpec(
    name="core_line_summarizer_spec",
    version="v1",
    description="Extracts a dense summary from an article",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=CORE_LINE_SUMMARIZER_PROMPT,
        model_name="openai/gpt-3.5-turbo",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )
)
