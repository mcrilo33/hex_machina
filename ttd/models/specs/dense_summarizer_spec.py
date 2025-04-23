from ttd.models.base_spec import ModelSpec, PromptSpec

DENSE_SUMMARIZER_PROMPT = PromptSpec(
    name="dense_summarizer_prompt",
    version="v1.0.0",
    description="Extract a dense summary from an article.",
    input_schema="article__title,article__text_content",
    output_schema="dense_summary",
    template="""
You are an expert summarizer trained to produce high-density, information-rich summaries.

Your goal is to condense an article into the **shortest possible summary that preserves every critical point**:
- Facts, arguments, results, conclusions
- Technical terms and named entities
- No repetition or fluff
- No commentary, opinions, or rhetorical questions

You are **not optimizing for readability**. You are **optimizing for signal-to-noise ratio**.
Each sentence should carry **maximum unique information**.

You will be given:
- An article title
- The full article text

---

TITLE:
\"\"\"{article__title}\"\"\"
ARTICLE:
\"\"\"{article__text_content}\"\"\"

---

Your task:
Write the most **compressed and factual summary** possible (in under 300 words). Use neutral language. Do **not** include the title or metadata. Return only the summary.
"""
)

DENSE_SUMMARIZER_SPEC = ModelSpec(
    name="dense_summarizer_spec",
    version="v1",
    input_schema=DENSE_SUMMARIZER_PROMPT.input_schema,
    output_schema=DENSE_SUMMARIZER_PROMPT.output_schema,
    description="Extracts a dense summary from an article.",
    provider="openai",
    config={
        "base_url": "https://openrouter.ai/api/v1",
        "model_name": "openai/gpt-3.5-turbo",
        "api_key_env_var": "OPENROUTER_API_KEY",
        "prompt": DENSE_SUMMARIZER_PROMPT,
        "temperature": 0,
        "max_tokens": 5000,
        "n": 1
    }
)