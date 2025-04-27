from pydantic import BaseModel, Field, model_validator

from ttd.models.base_spec import ModelSpec, PromptTemplateSpec
from ttd.models.configs.open_router_config import OpenRouterConfig


class IsAIInput(BaseModel):
    """Schema for is_ai classifier input."""
    article__title: str = Field(..., description="The title of the article")
    article__text_content: str = Field(
        ..., description="The main content of the article"
    )


class IsAIOutput(BaseModel):
    """Schema for is_ai classifier output."""
    is_ai: bool = Field(..., description="Whether the article is primarily about AI")

    @model_validator(mode='before')
    def from_string(item):
        value = item["is_ai"].strip().lower()
        if value == "true":
            item["is_ai"] = True
        elif value == "false":
            item["is_ai"] = False
        else: 
            raise ValueError(
                f"Cannot convert '{value}' to boolean. Expected 'true' or 'false'."
            )
        return item


ARTICLE_IS_AI_PROMPT = PromptTemplateSpec(
    name="article_is_ai_prompt",
    version="v1.0.0",
    description="Determine whether an article is primarily about AI",
    input_schema=IsAIInput,
    output_schema=IsAIOutput,
    template="""
You are an expert AI researcher.

Your task is to determine if the following article is primarily about Artificial Intelligence (AI). This includes topics such as:
- AI models, large language models (LLMs), machine learning, generative AI
- AI applications in science, business, health, robotics, NLP, computer vision
- Ethical, regulatory, or economic implications of AI

Do **not** classify it as AI-related if:
- It only mentions AI briefly without relevance to the core topic
- It uses "AI" metaphorically or for unrelated tech or business news

---
TITLE:
\"\"\"{article__title}\"\"\"
ARTICLE:
\"\"\"{article__text_content}\"\"\"

---
Return ONLY `true` or `false` (no explanation, no punctuation).
"""
)

ARTICLE_IS_AI_CLASSIFIER_SPEC = ModelSpec(
    name="article_is_ai_classifier_spec",
    version="v1",
    description="Classifies if article is about AI",
    provider="openai",
    config=OpenRouterConfig(
        prompt_spec=ARTICLE_IS_AI_PROMPT,
        model_name="openai/gpt-3.5-turbo",
        api_key_env_var="OPENROUTER_API_KEY",
        temperature=0.0,
        max_tokens=5000,
        n=1
    )
)
