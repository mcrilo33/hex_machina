""" Load articles step. """
import logging
from tinydb import Query
from dateutil.parser import parse as parse_date

from ttd.storage.ttd_storage import TTDStorage

# Initialize logger at module level
logger = logging.getLogger(__name__)


def execute(flow):
    """Load articles published after a date threshold."""
    logger.info("Loading articles...")
    storage = TTDStorage(flow.config.get("db_path"))

    Article = Query()
    date_threshold = parse_date(flow.date_threshold)
    articles = storage.search(
        "articles",
        Article.published_date.test(lambda d: parse_date(d) >= date_threshold)
    )
    flow.articles = articles[:flow.articles_limit]

    logger.info(f"✅ {len(flow.articles)} articles loaded after {flow.date_threshold}.")
