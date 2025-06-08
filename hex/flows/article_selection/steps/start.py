import logging
from hex.utils.date import to_aware_utc

from hex.storage.hex_storage import HexStorage
from hex.utils.config import load_config
from hex.utils.git import get_git_metadata

logger = logging.getLogger(__name__)


def _clean_up_tables(storage, flow):
    """ Clean up tables for a fresh run. """
    if flow.clean_tables:
        storage.db.drop_table(flow.selected_articles_table)
        logger.info("✅ Database cleaned.")
    else:
        logger.info("✅ Database not cleaned.")


def execute(flow):
    """ Initialize the pipeline, storage and metrics. """
    # Initialize storage
    flow.config = load_config()
    flow.git_metadata = get_git_metadata()
    flow.parsed_date_threshold = to_aware_utc(flow.date_threshold)
    flow.parsed_cluster_date_threshold = to_aware_utc(flow.cluster_date_threshold)
    flow.min_parsed_date_threshold = min(flow.parsed_date_threshold,
                                         flow.parsed_cluster_date_threshold)
    storage = HexStorage(flow.config.get("db_path"))
    logger.info("✅ Database first connection established.")
    _clean_up_tables(storage, flow)
    
    # Initialize metrics dictionary
    flow.metrics = {}
    flow.errors = {}