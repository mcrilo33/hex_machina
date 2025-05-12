import logging
from dateutil.parser import parse as parse_date

from ttd.storage.ttd_storage import TTDStorage
from ttd.utils.config import load_config
from ttd.utils.git import get_git_metadata

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
    flow.parsed_date_threshold = parse_date(flow.date_threshold)
    storage = TTDStorage(flow.config.get("db_path"))
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