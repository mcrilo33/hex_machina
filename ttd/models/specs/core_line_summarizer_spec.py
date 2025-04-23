from ttd.models.base_spec import ModelSpec, PromptSpec

CORE_LINE_SUMMARIZER_PROMPT = PromptSpec(
    name="core_line_summarizer_prompt",
    version="v1.0.0",
    description="Extract a core line from an article.",
    input_schema="dense_summarizer__output",
    output_schema="core_line_summary",
    template="""
You are a professional summarizer tasked with producing a **single-sentence summary** that captures the **main idea and significance** of a dense technical or factual summary.

Your summary must be:
- **Concise**: 1 sentence only (ideally under 30 words)
- **Clear**: Use plain, direct, and factual language
- **Focused**: Emphasize the core message and why it matters
- **No fluff**: Avoid generic phrases, opinions, or vague statements

You will be given:
- A dense summary of an article

---

DENSE SUMMARY:
\"\"\"{dense_summarizer__output}\"\"\"

---

Write a one-line summary that highlights the **key point** and its **relevance**.
Return only the sentence — no bullet points, titles, or extra text.
"""
)

CORE_LINE_SUMMARIZER_SPEC = ModelSpec(
    name="core_line_summarizer_spec",
    version="v1",
    input_schema=CORE_LINE_SUMMARIZER_PROMPT.input_schema,
    output_schema=CORE_LINE_SUMMARIZER_PROMPT.output_schema,
    description="Extracts a dense summary from an article.",
    provider="openai",
    config={
        "base_url": "https://openrouter.ai/api/v1",
        "model_name": "openai/gpt-3.5-turbo",
        "api_key_env_var": "OPENROUTER_API_KEY",
        "prompt": CORE_LINE_SUMMARIZER_PROMPT,
        "temperature": 0,
        "max_tokens": 5000,
        "n": 1
    }
)