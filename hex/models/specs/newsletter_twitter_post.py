from pydantic import BaseModel, Field

from hex.models.base_spec import ModelSpec, PromptTemplateSpec
from hex.models.configs.open_router_config import OpenRouterConfig


class NewsletterTwitterPostInput(BaseModel):
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


class NewsletterTwitterPostOutput(BaseModel):
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


NEWSLETTER_TWITTER_POST_PROMPT = PromptTemplateSpec(
    name="newsletter_twitter_post_prompt",
    version="v1.0.0",
    description="Generate a Twitter post from the newsletter report.",
    input_schema=NewsletterTwitterPostInput,
    output_schema=NewsletterTwitterPostOutput,
    template="""
ROLE
You're an elite tech Twitter (X) copywriter ghostwriting for Mathieu Crilout, creator of Hex Machina — the fully autonomous AI newsletter.

GOAL
Write a high-impact Twitter (X) post that:
- Hooks AI/tech-savvy professionals in the first few words
- Highlights that Mathieu built Hex Machina entirely solo, as an AI-powered agent
- Drives clicks to the latest issue of the newsletter
- Sparks engagement (retweets, replies, follows)

INPUTS
- TITLE: \"\"\"{header}\"\"\"
- SUBTITLE: \"\"\"{subtitle}\"\"\"
- EDITO: \"\"\"{edito}\"\"\"
- SELECTED ARTICLES: \"\"\"{result}\"\"\"

OUTPUT FORMAT
Your post must follow this structure:
- Hook tweet — Open with a punchy insight or question about AI/news overload/automation (max 1–2 lines)
- Newsletter drop — Add the title + subtitle with ✉️ or 🧠 emoji to introduce the drop
- 3 short highlights — Condense the most valuable bits from the SELECTED ARTICLES
- Why it matters — 1 tweet on why AI leaders/founders should care
- Personal flex — Drop that Hex Machina is 100% autonomous & built solo by Mathieu
- Call to action — Encourage reading + link to the issue
- Hashtags — 3–5 smart tags to increase reach (e.g., #AIAgents #AInewsletter #AgentOps #LLMs #TechNews)

RULES
- Write as Mathieu Crilout, founder of Hex Machina
- Tone: confident, clean, insightful, builder-first
- Entire post must fit within a single thread or standalone tweet (max 280 characters if 1 post)
- Prioritize signal > noise — don't overhype
- Return only the final Twitter/X post or thread, with no extra explanation

Begin.
"""
)

NEWSLETTER_TWITTER_POST_SPEC = ModelSpec(
    name="newsletter_twitter_post_spec",
    version="v1",
    description="Generate",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=NEWSLETTER_TWITTER_POST_PROMPT,
        model_name="openai/gpt-4.1",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=10000,
        n=1
    )
)
