""" Merge same tags step. """
import logging

logger = logging.getLogger(__name__)


def execute(flow):
    """Merge extracted tags across articles."""
    logger.info("Merging extracted tags...")

    merged_tags = {}
    for idx, (article, tags_pred) in enumerate(zip(flow.articles, flow.tags_preds)):
        if tags_pred is None:
            continue
        for jdx, tag in enumerate(tags_pred["tags"]):
            if tag not in merged_tags:
                merged_tags[tag] = {
                    "output": tag,
                    "history": [article["published_date"]],
                }
                logger.info(
                    f"✅ Merged {jdx+1} tag(s) {idx+1}/{len(flow.articles)}."
                )
            else:
                merged_tags[tag]["history"].append(article["published_date"])
                logger.info(
                    f"⚡ Skipped merging {idx+1}/{len(flow.articles)} (Non-AI)."
                )

    flow.merged_tags = merged_tags
    logger.info(f"✅ Merged {len(merged_tags)} unique tags across all articles.")
