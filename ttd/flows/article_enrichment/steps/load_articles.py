""" Load articles step. """
import logging
import time
from tinydb import Query
from dateutil.parser import parse as parse_date

from ttd.storage.ttd_storage import TTDStorage

# Initialize logger at module level
logger = logging.getLogger(__name__)

def _load_query(storage, articles_table, date_threshold, articles_limit):
    """Load articles from the database."""
    Article = Query()
    articles = storage.search(
        articles_table,
        Article.published_date.test(lambda d: parse_date(d) >= date_threshold)
    )
    articles = articles[:articles_limit]
    logger.info(f"✅ Loaded {len(articles)} articles from '{articles_table}': "
                f"len(articles)={len(articles)}, date_threshold='{date_threshold}'")
    return articles

def _filter_already_replicated_articles(storage, articles, replicates_table):
    """Filter out already replicated articles."""
    replicated_articles = storage.get_all(replicates_table)
    filtered_out = []
    kept_articles = []
    ids = set()
    for rep in replicated_articles:
        ids.add(rep["original_doc_id"])
    logger.info(f"✅ There are {len(ids)} already replicated articles")
    for article in articles:
        if article["doc_id"] in ids:
            filtered_out.append(article)
        else:
            kept_articles.append(article)
    logger.info(f"✅ Filtered out {len(filtered_out)} already replicated articles "
                f"from '{replicates_table}'")
    return kept_articles

def execute(flow):
    """Load articles published after a date threshold."""
    logger.info("Loading articles...")
    step_name = "load_articles"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    storage = TTDStorage(flow.config.get("db_path"))

    articles = _load_query(storage, flow.articles_table, flow.date_threshold,
                           flow.articles_limit)

    logger.info("✅ Filtering out already replicated articles if needed : "
                f"keep_replicates={flow.keep_replicates}")
    if flow.keep_replicates:
        articles = _filter_already_replicated_articles(storage, articles,
                                                      flow.replicates_table)
    flow.articles = articles
    logger.info(f"✅ Loaded {len(flow.articles)} articles...")
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
