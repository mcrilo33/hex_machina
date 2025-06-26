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
ROLE
You're an elite LinkedIn ghostwriter crafting posts for Hex Machina—the fully autonomous AI newsletter.

GOAL
Write a scroll-stopping LinkedIn post designed to:
- Capture attention of busy tech leaders immediately.
- Drive engagement and direct traffic to the latest issue of Hex Machina.

INPUTS
- TITLE: \"\"\"{header}\"\"\"
- SUBTITLE: \"\"\"{subtitle}\"\"\"
- EDITO: \"\"\"{edito}\"\"\"
- SELECTED ARTICLES: \"\"\"{result}\"\"\"

OUTPUT FORMAT
Structure your LinkedIn post exactly as follows:
- Bold, provocative 1-line hook to instantly grab attention (use a striking insight, surprising stat, or emerging trend).
- Bold 1-line introduction by Hex Machina highlighting urgency or uniqueness (e.g., "90% of what you're reading about AI is already outdated.") without writing "Hex Machina" or "Hex" in the text.
- Clearly formatted newsletter title and subtitle.
- "This week’s insights:" followed by exactly three concise, action-oriented bullets derived from the selected articles (each bullet: one short line).
- Brief (2–3 lines) "Why it matters" paragraph clearly tying insights back to reader's career, products, or strategic advantage.
- Direct link clearly labeled (e.g., "Read the full issue:").
- Engagement question (one open-ended line) to spark comments and dialogue.
- Short "build-in-public" flex line showcasing Hex's autonomous nature and tangible benefit (time saved, clarity provided, etc.).
- 5–7 targeted hashtags (e.g., #AIAgents, #AgentOps, #AInewsletter, #LLMs, #TechTrends, #Automation, #AIcuration).

RULES
- Professional yet conversational (written as a smart, opinionated founder).
- Clear, punchy, direct—no fluff.
- Max 1,200 characters total.

Begin.
"""
)

NEWSLETTER_LINKEDIN_POST_SPEC = ModelSpec(
    name="newsletter_linkedin_post_spec",
    version="v1",
    description="Generate",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=NEWSLETTER_LINKEDIN_POST_PROMPT,
        model_name="openai/gpt-4.1",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=10000,
        n=1
    )
)
