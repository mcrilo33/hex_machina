""" Is AI articles step. """
import logging
import time

from ttd.storage.ttd_storage import TTDStorage
from ttd.models.loader import load_model_spec

logger = logging.getLogger(__name__)


def execute(flow):
    """ Classify if articles are AI-related. """
    logger.info("Classifying articles as AI-related...")
    step_name = "is_ai_articles"

    # Reload storage and lazy load articles
    storage = TTDStorage(flow.config.get("db_path"))
    articles = storage.lazy_load(flow.articles)

    # Load classifier model
    flow.is_ai_classifier_spec_name = "article_is_ai_classifier_spec"
    is_ai_classifier_spec = load_model_spec(flow.is_ai_classifier_spec_name)

    flow.is_ai_preds = []

    # Initialize metrics
    flow.metrics.setdefault("step_start_times", {})[step_name] = time.time()
    flow.errors.setdefault(step_name, [])
    flow.prediction_times.setdefault(step_name, [])
    flow.token_usage.setdefault(step_name, {
        "prompt_tokens": [],
        "completion_tokens": [],
        "total_tokens": []
    })

    for idx, article in enumerate(articles):
        try:
            input = {
                "article__title": article["title"],
                "article__text_content": article["text_content"]
            }
            pred_start_time = time.time()
            is_ai_classifier_spec.input_schema.model_validate(input)
            pred = is_ai_classifier_spec._loaded_model.predict(input)
            output = {"is_ai": pred["output"]}
            is_ai_classifier_spec.output_schema.model_validate(output)
            pred_duration = time.time() - pred_start_time

            # Save predictions
            pred["is_ai"] = output["is_ai"]
            flow.is_ai_preds.append(pred)
            flow.prediction_times[step_name].append(pred_duration)

            # Save token usage if available
            if "metadata" in pred and pred["metadata"]:
                meta = pred["metadata"]
                flow.token_usage[step_name]["prompt_tokens"].append(meta.get("prompt_tokens", 0))
                flow.token_usage[step_name]["completion_tokens"].append(meta.get("completion_tokens", 0))
                flow.token_usage[step_name]["total_tokens"].append(meta.get("total_tokens", 0))

            article_type = 'AI' if pred['is_ai'] else 'Non-AI'
            logger.info(
                f"✅ Article {idx+1}/{len(articles)} classified as {article_type} "
                f"(prediction time: {pred_duration:.4f}s)"
            )
        except Exception as e:
            logger.error(f"❌ Error in {step_name} on article {idx}: {str(e)}")
            flow.errors[step_name].append({
                "index": idx,
                "error_message": str(e),
                "article_id": article.get("doc_id", None)
            })

    flow.articles = [dict(articles) for articles in articles]
    total_time = time.time() - flow.metrics["step_start_times"][step_name]
    
    # Finalize Metrics
    flow.metrics.setdefault("processing_times", {})[step_name] = total_time
    flow.metrics.setdefault("avg_prediction_times", {})[step_name] = (
        sum(flow.prediction_times[step_name]) / len(flow.prediction_times[step_name])
        if flow.prediction_times[step_name] else 0.0
    )
    flow.metrics.setdefault("avg_tokens_usage", {})[step_name] = {
        "avg_prompt_tokens": sum(flow.token_usage[step_name]["prompt_tokens"]) / len(flow.token_usage[step_name]["prompt_tokens"]),
        "avg_completion_tokens": sum(flow.token_usage[step_name]["completion_tokens"]) / len(flow.token_usage[step_name]["completion_tokens"]),
        "avg_total_tokens": sum(flow.token_usage[step_name]["total_tokens"]) / len(flow.token_usage[step_name]["total_tokens"]),
    }

    avg_pred_time = flow.metrics["avg_prediction_times"][step_name]
    logger.info(
        f"✅ Step {step_name} done in {total_time:.2f}s, "
        f"avg pred time: {avg_pred_time:.4f}s, "
        f"errors: {len(flow.errors[step_name])}"
    )