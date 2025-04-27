import logging
from tinydb import Query
from ttd.storage.ttd_storage import TTDStorage

logger = logging.getLogger(__name__)


def execute(flow):
    """Save or update tags in the database."""
    logger.info("Saving merged tags to database...")

    storage = TTDStorage(flow.config.get("db_path"))
    flow.tags = []
    TagWord = Query()

    for idx, pred in enumerate(flow.merged_tags.values()):
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
        logger.info(f"✅ Updating tag {idx+1}/{len(flow.merged_tags)}: {tag['name']}")

        # Save or update
        ids = storage.save_or_update("tags", tag)
        tag["doc_id"] = ids[0]
        flow.tags.append(tag)

    logger.info(f"✅ {len(flow.tags)} tags saved or updated.")
