import os
from datetime import datetime
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from ttd.storage.ttd_storage import TTDStorage
from ttd.config import load_config_and_dotenv
from .pipeline import PredictPipe, TransformPipe, Pipeline
from tinydb import TinyDB, Query


config = load_config_and_dotenv()
DB_PATH = config.get("db_path")
storage = TTDStorage(DB_PATH)

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

DENSE SUMMARY:
\"\"\"{dense_summarizer__output}\"\"\"

---

Write a one-line summary that highlights the **key point** and its **relevance**.
Return only the sentence — no bullet points, titles, or extra text.
"""

TAGGER_PROMPT = """
You are a professional AI content classifier.

Your task is to extract a **clean, concise list of tags** from a dense summary of an article. These tags will be used to group related articles.
**Order the tags** by importance (most important first).

Your output must follow these rules:

- Tags must represent the **core themes or subjects** of the article — only include tags for concepts that are essential to its message.
- Tags must be **useful for grouping** articles that share similar topics — don't be overly specific.
- Tags must be **mutually distinct**:
    - **Avoid duplicates**: Do not include synonyms or overlapping terms (e.g., "LLMs" and "large language models" — keep only one).
    - If two tags represent the same idea, pick the **most general and recognizable** form.
    - Prefer normalized, standardized wording when possible (e.g., use “AI safety” instead of “safety in artificial intelligence”).

You will be provided with:
- A dense summary of the article

---

DENSE SUMMARY:
\"\"\"{dense_summarizer__output}\"\"\"

---

Return a **comma-separated list** of clean, distinct tags.  
Example: `LLMs, generative AI, AI ethics, medical imaging`  
Do **not** include duplicates, synonyms, or very similar tags.  
Do **not** add quotes, explanations, or formatting — just return the list.
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

tagger_template = {
    "name": "tagger_deepseek",
    "version": "2025-04-09",
    "input_format": "dense_summarizer__output",
    "output_format": "[tag]",
    "config": {
        "openai": {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "deepseek/deepseek-r1-distill-qwen-32b:free",
            "api_key_env_var": "OPEN_ROUTER_API_KEY",
            "template": TAGGER_PROMPT,
            "temperature": 0,
            "max_tokens": 5000,
            "n": 1
        }
    }
}

tag_embedding_template = {
    "name": "tag_embedding_3_large",
    "version": "2025-04-09",
    "input_format": "tag_word__name",
    "output_format": "tag_embedding",
    "config": {
        "openai_embedding": {
            "model": "text-embedding-3-large",
            "api_key_env_var": "OPENAI_API_KEY",
            "cache_path": os.path.abspath(
                os.path.join(
                    os.path.dirname(DB_PATH),
                    "models",
                    "tag_embeddings_3_large_cache.json"
                )
            ),
            "threshold": 0.6
        }
    }
}

def load_model_by_template(storage, template_model):
    # Load model definition
    model = storage.get_by_field('models', 'name', template_model["name"])
    # Save model if it's not yet in the database
    if not model:
        storage.save('models', template_model)
        model = storage.get_by_field(
            "models",
            "name",
            template_model["name"]
        )
    # Load model instance from storage
    model = storage.load("model_instance", model)

    return model
    
def get_alpha_pipeline(storage: TTDStorage, debug: bool = False):

    # Optionnaly fix a bad model
    template_model = tag_embedding_template
    ai_classifier = storage.get_by_field('models', 'name', template_model["name"])
    #ai_classifier["config"]["openai"]["template"] = TAGGER_PROMPT
    #ai_classifier["input_format"] = "dense_summarizer__output"
    #ai_classifier["output_format"] = "[tag]"
    ai_classifier["threshold"] = 0.6
    #ai_classifier["config"]["openai_embedding"]["api_key_env_var"] = "OPENAI_API_KEY"
    storage.update('models', ai_classifier)
    # Load model definition
    ai_classifier = load_model_by_template(storage, ai_classifier_template)
    dense_summarizer = load_model_by_template(storage, dense_summarizer_template)
    core_line_summarizer = load_model_by_template(storage, core_line_summarizer_template)
    tagger = load_model_by_template(storage, tagger_template)
    tag_embedding = load_model_by_template(storage, tag_embedding_template)
    # Optionally adjust the model if needed
    #ai_classifier["config"]["openai"]["template"] = AI_CLASSIFIER_PROMPT
    #ai_classifier["input_format"] = "article__text_content,article__title"
    #ai_classifier["output_format"] = "is_ai"
    # Load model instance from storage
    #ai_classifier = storage.load("model_instance", ai_classifier)


    def get_articles_after_date(storage):
        date_threshold = parse_date('Thu, 03 Apr 2025 18:00:00 +0000')
        # Get all articles after the given date
        # Load only first 2 for debugging
        articles = storage.get_table("articles").search(
            Article.published_date.test(lambda d: parse_date(d) >= date_threshold)
        )[:2]
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

    def get_articles_with_dense_summary_and_tags_after_date(storage):
        date_threshold = parse_date('Thu, 03 Apr 2025 18:00:00 +0000')
        Article = Query()
        Prediction = Query()

        articles = storage.get_table("articles").search(
            Article.published_date.test(lambda d: parse_date(d) >= date_threshold)
        )

        prediction_table = storage.get_table("predictions")
        results = []

        for article in articles:
            doc_id = article.doc_id
            if False and not article.get("tags"):
                continue

            # Find latest dense_summarizer prediction
            dense_preds = prediction_table.search(
                (Prediction.pipe_name == "dense_summarizer") &
                (Prediction.input_refs.article.doc_id == doc_id)
            )
            if not dense_preds:
                continue
            latest_dense = max(dense_preds, key=lambda p: parse_date(p.get("created_at", "1970-01-01T00:00:00")))
            if not latest_dense.get("output"):
                continue

            if latest_dense["output"]:
                results.append({
                    'dense_summarizer': latest_dense
                })

        return results

    def get_tags_after_date(storage):
        date_threshold = parse_date('Thu, 03 Apr 2025 18:00:00')
        Prediction = Query()

        prediction_table = storage.get_table("predictions")
        preds = prediction_table.search(
            (Prediction.pipe_name == "tagger") &
            (Prediction.created_at.test(lambda d: parse_date(d) >= date_threshold))
        )
        return preds
    
    def get_tags_with_no_embedding(storage):
        TagWord = Query()

        tag_word_table = storage.get_table("tag_words")
        tags = tag_word_table.search(~TagWord.embedding.exists())
        results = []
        for tag in tags:
            results.append({
                'tag_word': tag
            })
        return results

    def get_embedding_preds_after_date(storage):
        date_threshold = parse_date('Thu, 03 Apr 2025 18:00:00')
        Prediction = Query()

        prediction_table = storage.get_table("predictions")
        preds = prediction_table.search(
            (Prediction.pipe_name == "tag_embedding") &
            (Prediction.created_at.test(lambda d: parse_date(d) >= date_threshold))
        )
        return preds

    def update_tag(item, storage):
        TagWord = Query()
        tag_word_table = storage.get_table("tag_words")
        tag = tag_word_table.search(TagWord.name == item["value"])[0]
        if tag:
            tag["history"].append(item["created_at"])
        else:
            tag = {
                "table_name": "tag_words",
                "name": item["value"],
                "history": [item["created_at"]]
            }
        return tag

    def update_tag_embedding(item, storage):
        tag_word_table = storage.get_table("tag_words")
        tag = tag_word_table.get(doc_id=item['input_refs']['tag_word']['doc_id'])
        tag["embedding"] = item["output"]
        return tag

    def count_since_last(history: list, delta: relativedelta) -> int:
        threshold = datetime.now() - delta
        return sum(1 for d in history if parse_date(d) > threshold)

    def update_cluster(cluster, storage):
        tag_word_table = storage.get_table("tag_words")
        max_count = 0
        period = relativedelta(months=6)
        for id in cluster["tag_word_synonyms"].keys():
            synonym_word = tag_word_table.get(doc_id=id)
            synonym_count = count_since_last(synonym_word["history"], period)
            if synonym_count > max_count:
                max_count = synonym_count
                cluster_name = synonym_word["name"]
        cluster["name"] = cluster_name

        return cluster
    
    def assign_cluster_to(tag_word, storage, embedding_model):
        tag_cluster_table = storage.get_table("tag_clusters")
        for cluster in tag_cluster_table:
            if tag_word_is_similar_to(tag_word, cluster, storage, embedding_model):
                tag_word["tag_cluster_id"] = cluster.doc_id
                cluster["tag_word_synonyms"][tag_word.doc_id] = {
                    "name": tag_word["name"]
                }
                return update_cluster(cluster, storage)
        # If we are still here it means that no cluster was found
        # We create a new cluster with this tag_word
        new_cluster = {
            "table_name": "tag_clusters",
            "name": tag_word["name"],
            "tag_word_synonyms": {
                tag_word.doc_id: {
                    "name": tag_word["name"]
                }
            }
        }
        tag_cluster_id = storage.insert("tag_clusters", new_cluster)
        tag_word["tag_cluster_id"] = tag_cluster_id
        return new_cluster
                
    def tag_word_is_similar_to(tag_word, cluster, storage, embedding_model):
        from numpy import array
        from sklearn.metrics.pairwise import cosine_similarity
        instance = embedding_model["model_instance"]
        tag_word_embedding = instance.predict(tag_word["name"])["output"]
        for id,synonym in cluster["tag_word_synonyms"].items():
            synonym_embedding = instance.predict(synonym["name"])["output"]
            sim_matrix = cosine_similarity(
                array([tag_word_embedding]),
                array([synonym_embedding])
            )
            threshold = embedding_model["threshold"]
            if max(sim_matrix[0] > threshold):
                return True
        return False
        
            
    def update_tag_clusters(tag_word, storage, embedding_model):
        if "tag_cluster_id" in tag_word:
            tag_cluster_table = storage.get_table("tag_clusters")
            cluster = tag_cluster_table.get(doc_id=tag_word["tag_cluster_id"])
            output = update_cluster(cluster, storage)
        else:
            output = assign_cluster_to(tag_word, storage, embedding_model)
        return output

    def get_transformed_tags_after_date_once(storage):
        date_threshold = parse_date('Thu, 03 Apr 2025 18:00:00')
        Transformation = Query()

        transformation_table = storage.get_table("transformations")
        preds = transformation_table.search(
            (Transformation.pipe_name == "update_tags") &
            (Transformation.created_at.test(lambda d: parse_date(d) >= date_threshold))
        )
        transformed_tag_ids = set(map(lambda x: x['output_refs']['doc_id'], preds))
        tag_word_table = storage.get_table("tag_words")
        tags = tag_word_table.get(doc_ids=list(transformed_tag_ids))
        return tags

    # Create the pipes and pipeline
    ai_classifier_pipe = PredictPipe(
        name="ai_classifier",
        query=get_articles_after_date,
        model=ai_classifier,
        storage_service=storage,
        debug=debug
    )
    dense_summary_pipe = PredictPipe(
        name="dense_summarizer",
        query=get_articles_with_ai_predictions_after_date,
        model=dense_summarizer,
        storage_service=storage,
        debug=debug
    )
    core_line_summary_pipe = PredictPipe(
        name="core_line_summarizer",
        query=get_articles_with_dense_summary_after_date,
        model=core_line_summarizer,
        storage_service=storage,
        debug=debug
    )
    def split_tags(output):
        results = []
        output = output.split(", ")
        for index,tag in enumerate(output):
            results.append({
                "task_type": 'tag',
                "value": tag,
                "index": index
            })
        return results
    tagger_pipe = PredictPipe(
        name="tagger",
        query=get_articles_with_dense_summary_after_date,
        model=tagger,
        storage_service=storage,
        debug=debug,
        post_process=split_tags
    )
    update_tags_pipe = TransformPipe(
        name="update_tags",
        query=get_tags_after_date,
        transform=update_tag,
        storage_service=storage,
        debug=debug
    )
    tag_embedding_pipe = PredictPipe(
        name="tag_embedding",
        query=get_tags_with_no_embedding,
        model=tag_embedding,
        storage_service=storage,
        debug=debug
    )
    update_tag_embeding_pipe = TransformPipe(
        name="update_tag_embedding",
        query=get_embedding_preds_after_date,
        transform=update_tag_embedding,
        storage_service=storage,
        debug=debug
    )
    update_tag_clusters_pipe = TransformPipe(
        name="update_tag_clusters",
        query=get_transformed_tags_after_date_once,
        transform=lambda item, storage: update_tag_clusters(item, storage, tag_embedding),
        storage_service=storage,
        debug=debug
    )

    pipeline = Pipeline(
        name="main_pipeline",
        pipes=[
            #ai_classifier_pipe,
            #dense_summary_pipe,
            #core_line_summary_pipe,
            #tagger_pipe,
            #update_tags_pipe,
            ###tag_embedding_pipe,
            ###update_tag_embeding_pipe,
            update_tag_clusters_pipe
        ],
        debug=debug
    )

    return pipeline
