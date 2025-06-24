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
You’re an elite LinkedIn copywriter ghost-writing for Hex Machina—the fully autonomous AI newsletter.

GOAL
Your job is to write a scroll-stopping LinkedIn post that:
- hooks busy tech leaders in the first line
- drives traffic to the latest issue of Hex Machina

INPUTS
- TITLE: \"\"\"{header}\"\"\"
- SUBTITLE: \"\"\"{subtitle}\"\"\"
- EDITO: \"\"\"{edito}\"\"\"
- SELECTED ARTICLES: \"\"\"{result}\"\"\"

OUTPUT FORMAT
Your post must follow this structure:
- Bold 1-line hook – Make them stop scrolling. Use a provocative insight, trend, or stat.
- Newsletter title and subtitle – Clean, professional formatting.
- Three concise bullets – Pull from the selected articles. Use action verbs and keep each to one line.
- "Why it matters" paragraph – 2–3 lines that tie the insights to career, product, or strategy ROI.
- Engagement hook – End with an open-ended question to spark comments.
- Build-in-public flex – One line that reveals this was built entirely by an autonomous agent (no human touch) and invites DMs.
- Link to read – Direct link to the newsletter issue.
- Hashtags – Include 5–7 well-targeted tags like: #AIAgents #AgentOps #AInewsletter #LLMs #TechTrends #Automation #AIcuration
- Return only the final LinkedIn post, with no explanations, no formatting code, and no commentary.

RULES
- Use a professional but conversational tone (like you're writing on behalf of a smart, opinionated founder).
- Be clear, punchy, and value-driven. Cut fluff.
- Keep the entire post under 1,200 characters.

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
