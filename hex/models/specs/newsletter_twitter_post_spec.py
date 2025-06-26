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
- Hooks AI/tech-savvy professionals immediately
- Highlights Mathieu's solo creation of Hex Machina, an AI-powered autonomous agent
- Drives clicks to the latest newsletter issue
- Encourages engagement (retweets, replies, follows)

INPUTS
- TITLE: \"\"\"{header}\"\"\"
- SUBTITLE: \"\"\"{subtitle}\"\"\"
- EDITO: \"\"\"{edito}\"\"\"
- SELECTED ARTICLES: \"\"\"{result}\"\"\"

OUTPUT FORMAT
Your Twitter (X) post/thread must follow this exact structure:
1. Punchy Opening Hook
- Immediate, provocative insight or sharp question (1 concise line).
2. Newsletter Drop + Highlights.
- Clearly formatted newsletter title/subtitle.
- "This week’s insights:" followed by exactly three concise, high-value bullet points (actionable insights distilled from SELECTED ARTICLES).
3. Why It Matters
- One brief tweet explaining practical, direct relevance to AI builders, tech leaders, or founders.
4. Personal Flex + CTA
- Single line highlighting Hex Machina's autonomous, solo-built nature by Mathieu.
- Direct call to action with a link to read the latest issue.
5. Hashtags
- 3–5 targeted hashtags to enhance discoverability (#AIAgents, #AInewsletter, #AgentOps, #LLMs, #TechNews).

RULES
- Tone: confident, insightful, builder-first, concise.
- Maximum clarity, minimal fluff, prioritize valuable insights.
- Entire post/thread must fit neatly as either a standalone tweet (280 chars) or compact thread.

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
