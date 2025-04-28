""" Merge same tags step. """
import logging
import time

logger = logging.getLogger(__name__)


def execute(flow):
    """Merge extracted tags across articles."""
    logger.info("Merging extracted tags...")
    step_name = "merge_same_tags"

    # Initialize timing and error tracking
    flow.metrics.setdefault("step_start_times", {})[step_name] = time.time()
    flow.errors.setdefault(step_name, [])
    flow.prediction_times.setdefault(step_name, [])

    merged_tags = {}

    for idx, (article, tags_pred) in enumerate(zip(flow.articles, flow.tags_preds)):
        try:
            start_time = time.time()

            if tags_pred is None:
                flow.prediction_times[step_name].append(0.0)
                continue

            for jdx, tag in enumerate(tags_pred["tags"]):
                if tag not in merged_tags:
                    merged_tags[tag] = {
                        "output": tag,
                        "history": [article["published_date"]],
                    }
                    logger.info(
                        f"✅ Merged tag {tag} from article {idx+1}/{len(flow.articles)}."
                    )
                else:
                    merged_tags[tag]["history"].append(article["published_date"])
                    logger.info(
                        f"⚡ Updated tag {tag} history from article {idx+1}/{len(flow.articles)}."
                    )

            merge_time = time.time() - start_time
            flow.prediction_times[step_name].append(merge_time)

        except Exception as e:
            logger.error(f"❌ Error in {step_name} at article {idx}: {str(e)}")
            flow.errors[step_name].append({
                "index": idx,
                "error_message": str(e),
                "article_id": article.get("doc_id", None)
            })
            flow.prediction_times[step_name].append(0.0)

    # Save merged tags to flow
    flow.merged_tags = merged_tags

    # Finalize timing
    total_time = time.time() - flow.metrics["step_start_times"][step_name]
    flow.metrics.setdefault("processing_times", {})[step_name] = total_time
    flow.metrics.setdefault("avg_prediction_times", {})[step_name] = (
        sum(flow.prediction_times[step_name]) / len(flow.prediction_times[step_name])
        if flow.prediction_times[step_name] else 0.0
    )

    count_tags = len(flow.merged_tags)
    avg_time = flow.metrics["avg_prediction_times"][step_name]
    error_count = len(flow.errors[step_name])

    logger.info(
        f"✅ Step {step_name} completed in {total_time:.2f}s, "
        f"{count_tags} unique tags merged, "
        f"avg merge time: {avg_time:.4f}s, "
        f"errors: {error_count}."
    )