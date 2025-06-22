from pydantic import BaseModel, Field

from hex.models.base_spec import ModelSpec, PromptTemplateSpec
from hex.models.configs.open_router_config import OpenRouterConfig


class NewsletterLinkedinPostInput(BaseModel):
    """Schema for tagger input data."""
    header: str = Field(
        ..., description="The header of the newsletter"
    )
    subtitle: str = Field(
        ..., description="The subtitle of the newsletter"
    )
    edito: str = Field(
        ..., description="The edito of the newsletter"
    )
    result: str = Field(
        ..., description="The selected articles"
    )


class NewsletterLinkedinPostOutput(BaseModel):
    """Schema for tagger output."""
    output: str = Field(
        ..., description=""
    )

# @model_validator(mode='before')
# def validate_output(item):
#    tags = item["output"].strip()
#    tags = tags.split(",")
#    tags = [tag.strip() for tag in tags]
#    item["output"] = tags
#    return item


NEWSLETTER_LINKEDIN_POST_PROMPT = PromptTemplateSpec(
    name="newsletter_linkedin_post_prompt",
    version="v1.0.0",
    description="Generate a LinkedIn post from the newsletter report.",
    input_schema=NewsletterLinkedinPostInput,
    output_schema=NewsletterLinkedinPostOutput,
    template="""
You are an expert copywriter for LinkedIn, ghost-writing on behalf of Mathieu
Crilout, the creator of Hex Machina—an autonomous AI newsletter.

OBJECTIVE
• Craft one LinkedIn post that showcases the latest issue: "{header}", proves
my AI/agent-building skills, and drives clicks to the newsletter.

SOURCE MATERIAL
- TITLE: \"\"\"{header}\"\"\"
- SUBTITLE: \"\"\"{subtitle}\"\"\"
- EDITO: \"\"\"{edito}\"\"\"
- SELECTED ARTICLES: \"\"\"{result}\"\"\"

STYLE & FORMAT
1. **Headline (1 bold line)** – Grab attention with a provocative insight or
stat.
2. **3 concise bullets** – Present the biggest "aha" moments from the issue
(use ✅/🚀/🧠 emojis sparingly).
3. **Why it matters paragraph** – Translate the insights into business or
career impact in ≤3 sentences.
4. **Build-in-public flex** – One sentence revealing that Hex Machina is
100 % machine-generated and "zero human touch").
7. **Hashtags** – Append 5-7 relevant, mixed-size tags (e.g. #AI
#MachineLearning #AIAgents #TechTrends #Newsletter).

TONE
• Professional but conversational ("I built…", "Here's why this matters").
• Crisp, no fluff, punchy verbs.
• Keep total length under 1 200 characters.

OUTPUT
Return ONLY the final LinkedIn post—no explanations, no markdown code fences.
"""
)

NEWSLETTER_LINKEDIN_POST_SPEC = ModelSpec(
    name="newsletter_linkedin_post_spec",
    version="v1",
    description="Generate",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=NEWSLETTER_LINKEDIN_POST_PROMPT,
        model_name="anthropic/claude-3.5-haiku",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=10000,
        n=1
    )
)
