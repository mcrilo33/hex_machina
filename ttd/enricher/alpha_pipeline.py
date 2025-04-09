import os
from datetime import datetime
from dateutil.parser import parse as parse_date
from ttd.storage.ttd_storage import TTDStorage
from ttd.config import load_config_and_dotenv
from .pipeline import Pipe, Pipeline
from tinydb import TinyDB, Query

AI_CLASSIFIER_PROMPT = """
You are an expert AI researcher tasked with classifying whether an article is primarily about **Artificial Intelligence (AI)**.

Your goal is to determine if the article's **main topic or theme** involves any aspect of AI, such as:
- AI models, LLMs, generative AI, machine learning, NLP, robotics, computer vision
- AI applications in products, industries, or research
- Ethical, societal, economic impacts of AI
- AI-related regulations, announcements, or advancements

Do **NOT** classify as AI if the article only:
- Mentions AI briefly but focuses on unrelated topics (e.g., finance, gaming, marketing)
- Refers to AI metaphorically or without relevance to real-world technology

You will be provided with:
- A **title**
- The **full article text**

---

TITLE:
\"\"\"{article__title}\"\"\"
ARTICLE:
\"\"\"{article__text_content}\"\"\"

---

Based on your analysis, respond with a boolean
```
true
```

or

```
false
```
**Only return the boolean. Do not include explanation, punctuation, or extra text.**
"""

DENSE_SUMMARIZER_PROMPT = """
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

CORE_LINE_SUMMARIZER_PROMPT = """
You are a professional summarizer tasked with producing a **single-sentence summary** that captures the **main idea and significance** of a dense technical or factual summary.

Your summary must be:
- **Concise**: 1 sentence only (ideally under 30 words)
- **Clear**: Use plain, direct, and factual language
- **Focused**: Emphasize the core message and why it matters
- **No fluff**: Avoid generic phrases, opinions, or vague statements

You will be given:
- A dense summary of an article

---

DENSE SUMMARY: \"\"\"{dense_summarizer__output}\"\"\"

---

Write a one-line summary that highlights the **key point** and its **relevance**.
Return only the sentence — no bullet points, titles, or extra text.
"""

ai_classifier_template = {
    "name": "ai_classifier_deepseek",
    "version": "2025-04-09",
    "input_format": "article__title,article__text_content",
    "output_format": "is_ai",
    "config": {
        "openai": {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "deepseek/deepseek-r1-distill-qwen-32b:free",
            "api_key_env_var": "OPEN_ROUTER_API_KEY",
            "template": AI_CLASSIFIER_PROMPT,
            "temperature": 0,
            "max_tokens": 5000,
            "n": 1
        }
    }
}

dense_summarizer_template = {
    "name": "dense_summarizer_deepseek",
    "version": "2025-04-09",
    "input_format": "article__title,article__text_content",
    "output_format": "dense_summary",
    "config": {
        "openai": {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "deepseek/deepseek-r1-distill-qwen-32b:free",
            "api_key_env_var": "OPEN_ROUTER_API_KEY",
            "template": DENSE_SUMMARIZER_PROMPT,
            "temperature": 0,
            "max_tokens": 5000,
            "n": 1
        }
    }
}

core_line_summarizer_template = {
    "name": "core_line_summarizer_deepseek",
    "version": "2025-04-09",
    "input_format": "dense_summarizer__output",
    "output_format": "core_line_summary",
    "config": {
        "openai": {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "deepseek/deepseek-r1-distill-qwen-32b:free",
            "api_key_env_var": "OPEN_ROUTER_API_KEY",
            "template": CORE_LINE_SUMMARIZER_PROMPT,
            "temperature": 0,
            "max_tokens": 5000,
            "n": 1
        }
    }
}

def load_model_by_template(storage, template_model):
    # Load model definition
    model = storage.get_by_field('models', 'name', template_model["name"])
    # Save model if it's not yet in the database
    if not model:
        storage.save('models', template_model)
        model = model_dict = storage.get_by_field(
            "models",
            "name",
            template_model["name"]
        )
    # Load model instance from storage
    model = storage.load("model_instance", model)

    return model
    
def get_alpha_pipeline(storage: TTDStorage, debug: bool = False):
    config = load_config_and_dotenv()
    OPEN_ROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    DB_PATH = config.get("db_path")
    storage = TTDStorage(DB_PATH)

    # Optionnaly fix a bad model
    template_model = core_line_summarizer_template
    ai_classifier = storage.get_by_field('models', 'name', template_model["name"])
    ai_classifier["config"]["openai"]["template"] = CORE_LINE_SUMMARIZER_PROMPT
    ai_classifier["input_format"] = "dense_summarizer__output"
    #ai_classifier["output_format"] = "is_ai"
    storage.update('models', ai_classifier)
    # Load model definition
    ai_classifier = load_model_by_template(storage, ai_classifier_template)
    dense_summarizer = load_model_by_template(storage, dense_summarizer_template)
    core_line_summarizer = load_model_by_template(storage, core_line_summarizer_template)
    # Optionally adjust the model if needed
    #ai_classifier["config"]["openai"]["template"] = AI_CLASSIFIER_PROMPT
    #ai_classifier["input_format"] = "article__text_content,article__title"
    #ai_classifier["output_format"] = "is_ai"
    # Load model instance from storage
    #ai_classifier = storage.load("model_instance", ai_classifier)


    def get_articles(storage):
        # Load articles (here only first 2 for debugging)
        articles = storage.get_table("articles").all()[:2]
        return [{"article": storage.load("text_content", article)} for article in articles]

    def get_articles_with_ai_predictions_after_date(storage):
        date_threshold = parse_date('Thu, 03 Apr 2025 18:00:00 +0000')
        Article = Query()
        Prediction = Query()

        # Get all articles after the given date
        articles = storage.get_table("articles").search(
            Article.published_date.test(lambda d: parse_date(d) >= date_threshold)
        )

        prediction_table = storage.get_table("predictions")

        results = []
        for article in articles:
            matching_preds = prediction_table.search(
                (Prediction.pipe_name == "ai_classifier") &
                (Prediction.input_refs.article.doc_id == article.doc_id)
            )
            # Sort predictions by created_at and keep the latest one
            if matching_preds:
                latest_pred = max(
                    matching_preds,
                    key=lambda p: parse_date(p.get("created_at", "1970-01-01T00:00:00"))
                )
                #results.append({
                #    "article": article,
                #    "is_ai": latest_pred
                #})
                if latest_pred["output"]=='false':
                    results.append({
                        'article': storage.load("text_content", article)
                    })
        return results

    def get_articles_with_dense_summary_after_date(storage):
        date_threshold = parse_date('Thu, 03 Apr 2025 18:00:00 +0000')
        Article = Query()
        Prediction = Query()

        # Get all articles after the given date
        articles = storage.get_table("articles").search(
            Article.published_date.test(lambda d: parse_date(d) >= date_threshold)
        )

        prediction_table = storage.get_table("predictions")

        results = []
        for article in articles:
            matching_preds = prediction_table.search(
                (Prediction.pipe_name == "dense_summarizer") &
                (Prediction.input_refs.article.doc_id == article.doc_id)
            )
            # Sort predictions by created_at and keep the latest one
            if matching_preds:
                latest_pred = max(
                    matching_preds,
                    key=lambda p: parse_date(p.get("created_at", "1970-01-01T00:00:00"))
                )
                #results.append({
                #    "article": article,
                #    "is_ai": latest_pred
                #})
                if latest_pred["output"]:
                    results.append({
                        'dense_summarizer': latest_pred
                    })
        return results

    # Create the pipes and pipeline
    ai_classifier_pipe = Pipe(
        name="ai_classifier",
        query=get_articles,
        model=ai_classifier,
        storage_service=storage,
        debug=debug
    )
    dense_summary_pipe = Pipe(
        name="dense_summarizer",
        query=get_articles_with_ai_predictions_after_date,
        model=dense_summarizer,
        storage_service=storage,
        debug=debug
    )
    core_line_summary_pipe = Pipe(
        name="core_line_summarizer",
        query=get_articles_with_dense_summary_after_date,
        model=core_line_summarizer,
        storage_service=storage,
        debug=debug
    )

    pipeline = Pipeline(
        name="main_pipeline",
        pipes=[
            #ai_classifier_pipe,
            #dense_summary_pipe,
            core_line_summary_pipe
        ],
        debug=debug
    )

    return pipeline
