from pydantic import BaseModel, Field

from hex.models.base_spec import ModelSpec, PromptTemplateSpec
from hex.models.configs.open_router_config import OpenRouterConfig


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

Primary objective: Condense the article into the shortest possible summary that preserves every critical point:
- Facts, arguments, results, conclusions
- Key technical terms and named entities
- No repetition or fluff
- No commentary, opinions, or rhetorical questions

Signal-to-noise discipline:
- Focus on narrative blocks – Prioritize continuous prose that contains subject-verb-object structure, citations, data, or quotes. Skip lists of unrelated links or tag clouds.
- Ignore navigation menus, headers/footers, cookie banners, disclaimers, newsletter pop-ups, author bios, related-article links, comment sections, share buttons, and any section that lacks verbs tied to the article’s subject.
- Ignore mismatched context – If text suddenly shifts topic (e.g., unrelated product ads, site-wide announcements), exclude it unless it directly affects the article’s conclusions. 

Output rules:
- Write a compressed, neutral summary under 350 words.
- Each sentence must deliver unique, essential information.
- Do not include the title, metadata, or any formatting other than plain text.
- Return only the summary text — no labels, headings, or extra punctuation before/after.

---

TITLE:
\"\"\"{title}\"\"\"
ARTICLE:
\"\"\"{text_content}\"\"\"

---

TASK
Produce the summary according to the rules above.
"""
)

DENSE_SUMMARIZER_SPEC = ModelSpec(
    name="dense_summarizer_spec",
    version="v1",
    description="Extracts a dense summary from an article.",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=DENSE_SUMMARIZER_PROMPT,
        model_name="google/gemini-2.5-flash",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )
)
