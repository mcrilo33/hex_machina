from ttd.models.base_spec import ModelSpec, PromptSpec

ARTICLE_IS_AI_PROMPT = PromptSpec(
    name="article_is_ai_prompt",
    version="v1.0.0",
    description="Determine whether an article is primarily about Artificial Intelligence (AI).",
    input_schema="article__title,article__text_content",
    output_schema="is_ai",
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
Return `true` or `false` (no explanation, no punctuation).
"""
)

ARTICLE_IS_AI_CLASSIFIER_SPEC = ModelSpec(
    name="article_is_ai_classifier_spec",
    version="v1",
    input_schema=ARTICLE_IS_AI_PROMPT.input_schema,
    output_schema=ARTICLE_IS_AI_PROMPT.output_schema,
    description="Classifies if article is about AI.",
    provider="openai",
    config={
        "base_url": "https://openrouter.ai/api/v1",
        "model_name": "openai/gpt-3.5-turbo",
        "api_key_env_var": "OPENROUTER_API_KEY",
        "prompt": ARTICLE_IS_AI_PROMPT,
        "temperature": 0.0,
        "max_tokens": 5000,
        "n": 1
    }
)