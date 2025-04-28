""" Save or update merged tags in the database. """
import logging
import time
from tinydb import Query
from ttd.storage.ttd_storage import TTDStorage

logger = logging.getLogger(__name__)


def execute(flow):
    """Save or update tags in the database."""
    logger.info("Saving merged tags to database...")
    step_name = "save_tags"

    # Initialize metrics tracking
    flow.metrics.setdefault("step_start_times", {})[step_name] = time.time()
    flow.errors.setdefault(step_name, [])
    flow.prediction_times.setdefault(step_name, [])

    storage = TTDStorage(flow.config.get("db_path"))
    flow.tags = []
    TagWord = Query()

    for idx, pred in enumerate(flow.merged_tags.values()):
        try:
            start_time = time.time()

            tag_records = storage.search("tags", TagWord.name == pred["output"])
            
            if tag_records:
                tag = tag_records[0]
                tag["history"] += pred["history"]
                logger.debug(f"Updating existing tag: {tag['name']}")
            else:
                tag = {
                    "table_name": "tags",
                    "name": pred["output"],
                    "history": pred["history"]
                }
                logger.debug(f"Creating new tag: {tag['name']}")

            ids = storage.save_or_update("tags", tag)
            tag["doc_id"] = ids[0]
            flow.tags.append(tag)

            duration = time.time() - start_time
            flow.prediction_times[step_name].append(duration)

            logger.info(f"✅ Saved tag {idx+1}/{len(flow.merged_tags)}: {tag['name']} "
                        f"(save time: {duration:.4f}s)")

        except Exception as e:
            logger.error(f"❌ Error saving tag at index {idx}: {str(e)}")
            flow.errors[step_name].append({
                "index": idx,
                "error_message": str(e),
                "tag_name": pred.get("output", None)
            })
            flow.prediction_times[step_name].append(0.0)

    # Finalize metrics
    total_time = time.time() - flow.metrics["step_start_times"][step_name]
    flow.metrics.setdefault("processing_times", {})[step_name] = total_time
    flow.metrics.setdefault("avg_prediction_times", {})[step_name] = (
        sum(flow.prediction_times[step_name]) / len(flow.prediction_times[step_name])
        if flow.prediction_times[step_name] else 0.0
    )

    count_tags = len(flow.tags)
    avg_time = flow.metrics["avg_prediction_times"][step_name]
    error_count = len(flow.errors[step_name])

    logger.info(
        f"✅ Step {step_name} completed in {total_time:.2f}s, "
        f"{count_tags} tags saved or updated "
        f"(avg save time: {avg_time:.4f}s, errors: {error_count})."
    )
