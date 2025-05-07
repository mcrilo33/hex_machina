""" Merge same tags step. """
import logging
import time

from ttd.utils.print import safe_pretty_print

logger = logging.getLogger(__name__)


def execute(flow):
    """Merge extracted tags across articles."""
    logger.info("Merging extracted tags...")
    step_name = "merge_same_tags"
    model_spec_name = "merge_same_tags_db"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    flow.metrics.setdefault("models_spec_names", {})[step_name] = model_spec_name
    flow.metrics.setdefault("models_io", {})[model_spec_name] = {
        "inputs": [],
        "outputs": [],
        "errors": []
    }

    merged_tags = {}

    data = flow.metrics["models_io"]["tagger_spec"]["outputs"]
    count_tags = 0
    for idx, tags_pred in enumerate(data):
        if tags_pred is None:
            continue
        tags_pred = tags_pred["output"]
        try:
            pred_start_time = time.time()
            flow.metrics["models_io"][model_spec_name]["inputs"].append(tags_pred)
            logger.info(f"✅ Merge {idx+1}/{len(data)} ")
            logger.info(f"✅ Inputs:")
            logger.info(safe_pretty_print(tags_pred))
            for jdx, tag in enumerate(tags_pred):
                count_tags += 1
                logger.info(f"✅ {tag} {idx+1}/{len(tags_pred)} - {count_tags} Items")
                if tag not in merged_tags:
                    merged_tags[tag] = {
                        "output": tag,
                        "history": [flow.articles[idx]["published_date"]],
                        "doc_ids": [{
                            "original_table_name": flow.articles_table,
                            "original_doc_id": str(flow.articles[idx]["doc_id"])
                        }]
                    }
                else:
                    merged_tags[tag]["history"].append(flow.articles[idx]["published_date"])
                    merged_tags[tag]["doc_ids"].append({
                        "original_table_name": flow.articles_table,
                        "original_doc_id": str(flow.articles[idx]["doc_id"])
                    })
                logger.info(f"✅ Merged tags {len(merged_tags)} - {count_tags} Items")
                logger.info(safe_pretty_print(merged_tags))
            pred_duration = time.time() - pred_start_time
            flow.metrics["models_io"][model_spec_name]["outputs"].append({
                "duration": pred_duration
            })
        except Exception as e:
            logger.error(f"❌ Error in {step_name} at article {idx}: {str(e)}")
            flow.metrics["models_io"][model_spec_name]["errors"].append(
                flow.metrics.models_io[step_name].append({
                    "index": idx,
                    "error_message": str(e),
                    "article_id": flow.articles[idx].get("doc_id", None)
                })
            )

    flow.merged_tags = merged_tags
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
