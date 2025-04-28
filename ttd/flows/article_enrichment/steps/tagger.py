""" Extract tags from dense summaries of AI articles. """
import logging
import time

from ttd.models.loader import load_model_spec

# Initialize logger
logger = logging.getLogger(__name__)


def execute(flow):
    """Extract tags from dense summaries of AI articles."""
    logger.info("Extracting tags from dense summaries...")
    step_name = "tagger"

    # Load tagger model
    flow.tagger_spec_name = "tagger_spec"
    tagger_spec = load_model_spec(flow.tagger_spec_name)

    # Initialize outputs
    flow.tags_preds = []

    # Initialize metrics tracking
    flow.metrics.setdefault("step_start_times", {})[step_name] = time.time()
    flow.errors.setdefault(step_name, [])
    flow.prediction_times.setdefault(step_name, [])
    flow.token_usage.setdefault(step_name, {
        "prompt_tokens": [],
        "completion_tokens": [],
        "total_tokens": []
    })

    # Process articles
    for idx, (is_ai_pred, dense_summary_pred) in enumerate(zip(flow.is_ai_preds, flow.dense_summaries_preds)):
        try:
            if is_ai_pred["is_ai"] and dense_summary_pred is not None:
                input_data = {
                    "dense_summarizer__output": dense_summary_pred["output"],
                }

                pred_start_time = time.time()
                tagger_spec.input_schema.model_validate(input_data)

                pred = tagger_spec._loaded_model.predict(input_data)

                output_data = {"tags": pred["output"]}
                tagger_spec.output_schema.model_validate(output_data)
                pred_duration = time.time() - pred_start_time

                # Clean tags
                pred["tags"] = [tag.strip() for tag in pred["output"].split(",") if tag.strip()]
                flow.tags_preds.append(pred)
                flow.prediction_times[step_name].append(pred_duration)

                # Save token usage if available
                if "metadata" in pred and pred["metadata"]:
                    meta = pred["metadata"]
                    flow.token_usage[step_name]["prompt_tokens"].append(meta.get("prompt_tokens", 0))
                    flow.token_usage[step_name]["completion_tokens"].append(meta.get("completion_tokens", 0))
                    flow.token_usage[step_name]["total_tokens"].append(meta.get("total_tokens", 0))
                else:
                    flow.token_usage[step_name]["prompt_tokens"].append(0)
                    flow.token_usage[step_name]["completion_tokens"].append(0)
                    flow.token_usage[step_name]["total_tokens"].append(0)

                logger.info(
                    f"✅ Tags generated for article {idx+1}/{len(flow.articles)} "
                    f"(prediction time: {pred_duration:.4f}s)."
                )
            else:
                flow.tags_preds.append(None)
                logger.info(
                    f"⚡ Skipped tagging for article {idx+1}/{len(flow.articles)} (Non-AI or missing dense summary)."
                )

        except Exception as e:
            logger.error(f"❌ Error in {step_name} on article {idx}: {str(e)}")
            flow.tags_preds.append(None)
            flow.errors[step_name].append({
                "index": idx,
                "error_message": str(e),
                "article_id": flow.articles[idx].get("doc_id", None)
            })

    # Finalize metrics
    total_time = time.time() - flow.metrics["step_start_times"][step_name]
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

    count_success = sum(1 for p in flow.tags_preds if p is not None)
    avg_pred_time = flow.metrics["avg_prediction_times"][step_name]
    error_count = len(flow.errors[step_name])

    logger.info(
        f"✅ Step {step_name} completed in {total_time:.2f}s, "
        f"{count_success}/{len(flow.articles)} successful tag generations "
        f"(avg pred time: {avg_pred_time:.4f}s, errors: {error_count})."
    )
