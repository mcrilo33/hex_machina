from pydantic import BaseModel, Field

from hex.models.base_spec import ModelSpec, PromptTemplateSpec
from hex.models.configs.open_router_config import OpenRouterConfig


class CoreLineSummarizerInput(BaseModel):
    """Schema for core line summarizer input data."""
    output: str = Field(
        ..., description="A dense summary of the article"
    )


class CoreLineSummarizerOutput(BaseModel):
    """Schema for core line summarizer output."""
    output: str = Field(
        ..., description="A single-sentence summary of the dense summary"
    )


CORE_LINE_SUMMARIZER_PROMPT = PromptTemplateSpec(
    name="core_line_summarizer_prompt",
    version="v1.0.0",
    description="Extract a core line from an article",
    input_schema=CoreLineSummarizerInput,
    output_schema=CoreLineSummarizerOutput,
    template="""
You are a professional summarizer crafting a single-sentence hook that distills the most important idea and why it matters — designed to make curious readers want to dive deeper.
Your sentence must be:
- Brief: Max one sentence (preferably under 30 words)
- Plainspoken: No jargon, no filler — clarity above all
- Impactful: Focus on what’s new, surprising, or useful
- Magnetic: Phrase it so that someone reading it wants the full story
- Objective: Avoid hype, opinions, or speculation

You will be given:
A dense article summary

---

DENSE SUMMARY:
\"\"\"{output}\"\"\"

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
        model_name="google/gemini-2.5-flash",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )
)
