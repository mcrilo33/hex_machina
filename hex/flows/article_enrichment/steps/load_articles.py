""" Load articles step. """
import logging
import time
from tinydb import Query
from ttd.utils.date import to_aware_utc

from ttd.storage.ttd_storage import TTDStorage

# Initialize logger at module level
logger = logging.getLogger(__name__)

def get_articles_with_no_error(articles):
    articles_with_no_error = []
    for article in articles:
        if not article.get("metadata", {}).get("error"):
            articles_with_no_error.append(article)

    return articles_with_no_error

def _load_query(storage, articles_table, date_threshold, articles_limit):
    """Load articles from the database."""
    Article = Query()
    articles = storage.search(
        articles_table,
        Article.published_date.test(lambda d: to_aware_utc(d) >= date_threshold)
    )
    if articles_limit is not None:
        articles = articles[:articles_limit]
    articles = get_articles_with_no_error(articles)
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

    articles = _load_query(storage, flow.articles_table, flow.parsed_date_threshold,
                           flow.articles_limit)

    logger.info("✅ Filtering out already replicated articles...")
    articles = _filter_already_replicated_articles(storage, articles,
                                                      flow.replicates_table)
    flow.articles = articles
    logger.info(f"✅ Loaded {len(flow.articles)} articles...")
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
