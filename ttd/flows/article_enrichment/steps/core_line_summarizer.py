""" Core line summarizer step. """
import logging
import time

from ttd.models.loader import load_model_spec

logger = logging.getLogger(__name__)


def execute(flow):
    """Generate core line summaries based on dense summaries."""
    logger.info("Generating core line summaries for AI-related articles...")
    step_name = "core_line_summarizer"

    # Load model spec
    flow.core_line_summarizer_spec_name = "core_line_summarizer_spec"
    core_line_summarizer_spec = load_model_spec(flow.core_line_summarizer_spec_name)

    # Initialize outputs
    flow.core_line_summaries_preds = []

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
                core_line_summarizer_spec.input_schema.model_validate(input_data)
                pred = core_line_summarizer_spec._loaded_model.predict(input_data)
                output_data = {"core_line_summary": pred["output"]}
                core_line_summarizer_spec.output_schema.model_validate(output_data)
                pred_duration = time.time() - pred_start_time

                flow.core_line_summaries_preds.append(pred)
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
                    f"✅ Core line summary {idx+1}/{len(flow.articles)} generated "
                    f"(prediction time: {pred_duration:.4f}s)."
                )
            else:
                flow.core_line_summaries_preds.append(None)
                logger.info(
                    f"⚡ Skipped core line summary {idx+1}/{len(flow.articles)} (Non-AI article or missing dense summary)."
                )

        except Exception as e:
            logger.error(f"❌ Error in {step_name} on article {idx}: {str(e)}")
            flow.core_line_summaries_preds.append(None)
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

    count_success = sum(1 for p in flow.core_line_summaries_preds if p is not None)
    avg_pred_time = flow.metrics["avg_prediction_times"][step_name]
    error_count = len(flow.errors[step_name])

    logger.info(
        f"✅ Step {step_name} completed in {total_time:.2f}s, "
        f"{count_success}/{len(flow.articles)} successful core summaries "
        f"(avg pred time: {avg_pred_time:.4f}s, errors: {error_count})."
    )
