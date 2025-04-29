""" Save or update merged tags in the database. """
import logging
import time
from tinydb import Query
from ttd.storage.ttd_storage import TTDStorage
from ttd.utils.print import safe_pretty_print

logger = logging.getLogger(__name__)


def execute(flow):
    """Save or update tags in the database."""
    logger.info("Saving merged tags to database...")
    step_name = "save_tags"
    model_spec_name = "update_tags_db"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    flow.metrics.setdefault("models_spec_names", {})[step_name] = model_spec_name
    flow.metrics.setdefault("models_io", {})[model_spec_name] = {
        "inputs": [],
        "outputs": [],
        "errors": []
    }

    storage = TTDStorage(flow.config.get("db_path"))
    tags = []
    TagWord = Query()
    data = flow.merged_tags.values()
    for idx, pred in enumerate(data):
        try:
            pred_start_time = time.time()
            tag_records = storage.search("tags", TagWord.name == pred["output"])
            logger.info(f"✅ Update {idx+1}/{len(data)} ")
            logger.info(f"✅ Inputs:")
            logger.info(safe_pretty_print(pred))
            if tag_records:
                tag = tag_records[0]
                tag["history"] += pred["history"]
                logger.debug(f"✅ Updating existing tag: {tag['name']}")
            else:
                tag = {
                    "table_name": "tags",
                    "name": pred["output"],
                    "history": pred["history"]
                }
                logger.debug(f"✅ Creating new tag: {tag['name']}")

            ids = storage.save_or_update("tags", tag)
            tag["doc_id"] = ids[0]
            tags.append(tag)
            pred_duration = time.time() - pred_start_time
            flow.metrics["models_io"][model_spec_name]["outputs"].append({
                "duration": pred_duration
            })
        except Exception as e:
            logger.error(f"❌ Error in {step_name} at article {idx}: {str(e)}")
            flow.metrics["models_io"][model_spec_name]["errors"].append(
                flow.errors[step_name].append({
                    "index": idx,
                    "error_message": str(e),
                    "article_id": flow.articles[idx].get("doc_id", None)
                })
            )

    flow.tags = tags
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
