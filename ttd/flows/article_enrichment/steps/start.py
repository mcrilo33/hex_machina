import logging
from dateutil.parser import parse as parse_date

from ttd.storage.ttd_storage import TTDStorage
from ttd.utils.config import load_config
from ttd.utils.git import get_git_metadata

logger = logging.getLogger(__name__)


def _clean_up_tables(storage, flow):
    """ Clean up tables for a fresh run. """
    if not flow.keep_replicates:
        storage.db.drop_table("tags")
        storage.db.drop_table("tag_clusters")
        storage.db.drop_table(flow.replicates_table)
        logger.info("✅ Database cleaned.")
    else:
        logger.info("✅ Database not cleaned, keeping replicates.")

def execute(flow):
    """ Initialize the pipeline, storage and metrics. """
    # Initialize storage
    flow.config = load_config()
    flow.git_metadata = get_git_metadata()
    flow.date_threshold = parse_date(flow.date_threshold)
    storage = TTDStorage(flow.config.get("db_path"))
    logger.info("✅ Database first connection established.")
    _clean_up_tables(storage, flow)
    
    # Initialize metrics dictionary
    flow.metrics = {}
    flow.errors = {}
    flow.prediction_times = {}
    flow.token_usage = {}