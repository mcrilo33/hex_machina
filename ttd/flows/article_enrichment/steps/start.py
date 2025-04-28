import logging

from ttd.storage.ttd_storage import TTDStorage
from ttd.utils.config import load_config
from ttd.utils.git import get_git_metadata

logger = logging.getLogger(__name__)


def execute(flow):
    """ Initialize the pipeline, storage and metrics. """
    # Initialize storage
    flow.config = load_config()
    flow.git_metadata = get_git_metadata()
    storage = TTDStorage(flow.config.get("db_path"))
    logger.info("✅ Database first connection established.")
    
    # Clean up tables for a fresh run
    storage.db.drop_table("tags")
    storage.db.drop_table("tag_clusters")
    storage.db.drop_table(flow.replicate_table)
    logger.info("✅ Database cleaned.")
    
    # Initialize metrics dictionary
    flow.metrics = {}
    flow.errors = {}
    flow.prediction_times = {}
    flow.token_usage = {}