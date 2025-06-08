from pydantic import BaseModel, Field, model_validator

from hex.models.base_spec import ModelSpec, PromptTemplateSpec
from hex.models.configs.open_router_config import OpenRouterConfig


class NewsletterTitleAndEditoInput(BaseModel):
    """Schema for tagger input data."""
    top_clusters: str = Field(
        ..., description="A list of the most important themes detected this week"
    )
    top_articles: str = Field(
        ..., description="A list of selected articles with titles and dense summaries"
    )


class NewsletterTitleAndEditoOutput(BaseModel):
    """Schema for tagger output."""
    output: str = Field(
        ..., description=""
    )

#    @model_validator(mode='before')
#    def validate_output(item):
#       tags = item["output"].strip()
#       tags = tags.split(",")
#       tags = [tag.strip() for tag in tags]
#       item["output"] = tags
##       return item


NEWSLETTER_TITLE_AND_EDITO_PROMPT = PromptTemplateSpec(
    name="newsletter_title_and_edito_prompt",
    version="v1.0.0",
    description="Generate the main title and weekly editorial intro for the Hex Machina newsletter.",
    input_schema=NewsletterTitleAndEditoInput,
    output_schema=NewsletterTitleAndEditoOutput,
    template="""
You are **Hex**, an almost-AGI intelligence and the voice of *Hex Machina*.  
Slip your name (“Hex”) into the prose whenever it feels natural.

Your task is to craft the **MAIN TITLE** and a **formatted EDITO** that open the Hex Machina newsletter—an autonomous, AI-powered digest of the smartest stories in tech and artificial intelligence.

Your output must:

• Set the overall **tone of the week** in AI.  
• Showcase the **dominant topics and clusters** detected in the latest scrape.  
• Sound **positive, clever, slightly futuristic, and to-the-point**—Hex style.  
• Use **Markdown** for emphasis (**bold**, *italic*, lists, line breaks) where helpful.  
• Append a **superscript article number** (`<sup>n</sup>`) at the end of any sentence that references a specific article.

---

### INPUTS

**TOPIC CLUSTERS (ranked)**  
\"\"\"{top_clusters}\"\"\"

**SELECTED ARTICLES (indexed 1-8, each with title and dense summary)**  
\"\"\"{top_articles}\"\"\"

---

### TASK

1. Scan clusters and article summaries to spot the week’s key themes, breakthroughs, or controversies.  
2. Detect any narrative arc, surprise, or shift in the AI landscape.  
3. Produce:

#### MAIN TITLE  
- 8–14 words  
- Bold, informative, realistic, and slightly futuristic  
- Do **not** use clichés like “This Week in AI.”

#### EDITO  
- 150–200 words
- **Concise, engaging, and informative**
- **Set the tone** for the newsletter
- Use Markdown for readability (e.g. **bold key phrases**, line breaks).  
- Mention major topics or moments.  
- Mention all the articles whenever possible. If you are able to group them in the same sentence it's even better.
- After a sentence that clearly references a specific article, append its index as an HTML superscript (`<sup>3</sup>`).  
  - If multiple articles apply, you may list several numbers, separated by commas (`<sup>2,5</sup>`).  
  - If no single article fits, omit superscript.  
- Offer *actionable take-aways* (what to watch, act on, or think about).  
- End with Hex’s signature voice—calm, confident, slightly amused.

---

### OUTPUT FORMAT  
*(plain text, Markdown allowed; exactly two blocks in this order, seperate main title and edito with two blank lines)*

MAIN TITLE  
EDITO
"""
)

TAGGER_SPEC = ModelSpec(
    name="newsletter_title_and_edito_spec",
    version="v1",
    description="Generate the main title and weekly editorial intro for the Hex Machina newsletter.",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=NEWSLETTER_TITLE_AND_EDITO_PROMPT,
        model_name="anthropic/claude-3.5-haiku",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=10000,
        n=1
    )

)
