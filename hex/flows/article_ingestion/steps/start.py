import logging
from hex.utils.date import to_aware_utc

from hex.storage.hex_storage import HexStorage
from hex.utils.config import load_config
from hex.utils.git import get_git_metadata

logger = logging.getLogger(__name__)


def _clean_up_tables(storage, flow):
    """ Clean up tables for a fresh run. """
    if flow.clean_tables:
        storage.db.drop_table(flow.articles_table)
        logger.info("✅ Database cleaned.")
    else:
        logger.info("✅ Database not cleaned.")

def execute(flow):
    """ Initialize the pipeline, storage and metrics. """
    # Initialize storage
    flow.config = load_config()
    with open(flow.config["feeds_path"], "r") as f:
        flow.rss_feeds = [line.strip() for line in f if line.strip()]
    with open(flow.config["feeds_stealth_path"], "r") as f:
        flow.rss_stealth_feeds = [line.strip() for line in f if line.strip()]
    flow.git_metadata = get_git_metadata()
    flow.parsed_date_threshold = to_aware_utc(flow.date_threshold)
    storage = HexStorage(flow.config.get("db_path"))
    logger.info("✅ Database first connection established.")
    _clean_up_tables(storage, flow)
    
    # Initialize metrics dictionary
    flow.metrics = {}
    flow.errors = {}
    articles = storage.get_all(flow.articles_table)
    if len(articles) == 0:
        flow.first_id = 0
    else:
        flow.first_id = max([int(doc.get("doc_id")) for doc in articles])