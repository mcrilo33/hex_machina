from pydantic import BaseModel, Field, model_validator

from hex.models.base_spec import ModelSpec, PromptTemplateSpec
from hex.models.configs.open_router_config import OpenRouterConfig


class IsAIInput(BaseModel):
    """Schema for is_ai classifier input."""
    title: str = Field(..., description="The title of the article")
    text_content: str = Field(
        ..., description="The main content of the article"
    )


class IsAIOutput(BaseModel):
    """Schema for is_ai classifier output."""
    output: bool = Field(..., description="Whether the article is primarily about AI")

    @model_validator(mode='before')
    def validate_output(item):
        value = item["output"].strip().lower()
        if value == "true":
            item["output"] = True
        elif value == "false":
            item["output"] = False
        else: 
            raise ValueError(
                f"Cannot convert '{value}' to boolean. Expected 'true' or 'false'."
            )
        return item
    
    class Config:
        extra = 'allow'


ARTICLE_IS_AI_PROMPT = PromptTemplateSpec(
    name="article_is_ai_prompt",
    version="v1.0.0",
    description="Determine whether an article is primarily about AI",
    input_schema=IsAIInput,
    output_schema=IsAIOutput,
    template="""
You are an expert AI researcher.
Your task is to determine if the following article is primarily about one (or more) of these topics:
- Generative-AI productivity hacks.
- Prompt engineering & AI literacy.
- AI career & salary trends.
- AI-powered marketing & hyper-personalization.
- AI governance & regulation (e.g., EU AI Act).
- AI agents & autonomous workflows.
- Multimodal AI breakthroughs.

Do not classify it as one of these topics if:
- The article only references the sub-topic(s) briefly or tangentially.
- The terms are used metaphorically or in unrelated contexts.

---
TITLE:
\"\"\"{title}\"\"\"
ARTICLE:
\"\"\"{text_content}\"\"\"

---
Return ONLY true or false (no explanation, no punctuation).
"""
)

ARTICLE_IS_AI_CLASSIFIER_SPEC = ModelSpec(
    name="article_is_ai_classifier_spec",
    version="v1",
    description="Classifies if article is about AI",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=ARTICLE_IS_AI_PROMPT,
        model_name="google/gemini-2.5-flash",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )
)
