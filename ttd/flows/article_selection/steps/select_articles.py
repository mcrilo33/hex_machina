""" Load articles step. """
import logging
import time
from typing import Callable
from collections import Counter, defaultdict
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
from copy import deepcopy

from ttd.storage.ttd_storage import TTDStorage


# Initialize logger at module level
logger = logging.getLogger(__name__)

def linear_order_metric(order: int) -> float:
    """Compute order metric based on the position in the list."""
    return 1 / (order + 1)  # Order starts at 0

def exponential_order_metric(decay: float = 0.5) -> Callable[[int], float]:
    """
    Returns a function that computes an exponentially decaying score
    based on the order index. Score = decay^order.

    :param decay: The decay base. Smaller means faster decay (0 < decay < 1).
    :return: A function that maps order (int) -> float
    """
    assert 0 < decay < 1, "Decay must be between 0 and 1"
    
    def metric(order: int) -> float:
        return decay ** order

    return metric

def compute_cluster_scores(articles: list, order_metric: Callable = linear_order_metric) -> dict:
    """Compute cluster scores based on the number of articles it belongs to."""

    key = 'clusters_names_in_order_added'
    cluster_counter = Counter()
    for article in articles:
        if key in article and article[key]:
            cluster_counter.update(article[key])
    
    # Only keep clusters that appear at least 2 times
    valid_clusters = {cluster for cluster, count in cluster_counter.items() if count >= 2}

    # Compute order weights (early tag = bigger weight)
    cluster_order_scores = defaultdict(list)
    for article in articles:
        tags = article.get(key, [])
        for order, tag in enumerate(tags):
            if tag in valid_clusters:
                cluster_order_scores[tag].append(order_metric(order))

    # Final cluster scores
    cluster_scores = {}
    for cluster, order_weights in cluster_order_scores.items():
        cum_order_weight = sum(order_weights)
        cluster_scores[cluster] = cum_order_weight

    return cluster_scores

def compute_article_cluster_scores(articles: list, cluster_scores: dict, order_metric: Callable = linear_order_metric) -> dict:
    """Compute article scores based on the clusters they belong to."""

    key = 'clusters_names_in_order_added'
    for article in articles:
        tags = article.get(key, [])
        scores = []
        for order, tag in enumerate(tags):
            if tag in cluster_scores:
                scores.append(order_metric(order))
        article["clusters_score"] = sum(scores)
    return articles

def get_top_n_articles(scored_articles, n=5):
    """Return the top n articles sorted by their score descending."""
    scored_articles = deepcopy(scored_articles)
    sorted_articles = sorted(scored_articles, key=lambda x: x["clusters_score"], reverse=True)
    
    return sorted_articles[:n]

def select_top_articles_with_diversity(
    articles_for_cluster_scores: list,
    articles_for_selection: list,
    order_metric: Callable = linear_order_metric,
    n: int = 10
) -> list:
    """
    Select top N articles based on cluster scores and diversity.

    :param articles: List of articles.
    :param cluster_scores: Dictionary of cluster scores.
    :param n: Number of top articles to select.
    :return: List of selected articles.
    """
    
    articles = deepcopy(articles_for_selection)

    # Compute initial cluster scores
    cluster_scores = compute_cluster_scores(articles_for_cluster_scores, order_metric=order_metric)
    articles = compute_article_cluster_scores(articles, cluster_scores, order_metric=order_metric)
    # Select top N articles based on cluster scores
    selected_articles = []
    for _ in range(n):
        # Select the article with the highest cluster score
        max_item = max(articles, key=lambda d: d["clusters_score"])
        selected_articles.append(max_item)
        # Remove best cluster of the selected item from the cluster scores
        # to ensure diversity
        cluster_scores[max_item["clusters_names_in_order_added"][0]] = 0
        articles.remove(max_item)
        articles = compute_article_cluster_scores(articles, cluster_scores, order_metric=order_metric)
    
    return selected_articles

def execute(flow):
    """Select articles"""
    logger.info("Selecting articles...")
    step_name = "select_articles"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time

    articles_for_cluster_scores = [
        article for article in flow.articles
        if parse_date(article["published_date"]) >= flow.parsed_cluster_date_threshold
        and "clusters_names_in_order_added" in article
    ]
    articles_for_selection = [
        article for article in flow.articles
        if parse_date(article["published_date"]) >= flow.parsed_date_threshold
        and "clusters_names_in_order_added" in article
    ]
    logger.info("✅ Scoring clusters...")
    linear_cluster_scores = compute_cluster_scores(articles_for_cluster_scores,
                                                   order_metric=linear_order_metric)
    exponential_cluster_scores = compute_cluster_scores(
        articles_for_cluster_scores, order_metric=exponential_order_metric(0.5)
    )

    logger.info("✅ Scoring articles...")
    linearly_scored_articles = compute_article_cluster_scores(
        articles_for_selection, linear_cluster_scores, order_metric=linear_order_metric
    )
    top_n_linearly_scored_articles = get_top_n_articles(linearly_scored_articles, n=flow.articles_limit)
    exponentialy_scored_articles = compute_article_cluster_scores(
        articles_for_selection, linear_cluster_scores, order_metric=exponential_order_metric(0.5)
    )
    top_n_exponentialy_scored_articles = get_top_n_articles(exponentialy_scored_articles, n=flow.articles_limit)
    top_n_linearly_scored_articles_with_diversity = select_top_articles_with_diversity(
        articles_for_cluster_scores, articles_for_selection,
        order_metric=linear_order_metric, n=flow.articles_limit
    )
    top_n_exponentialy_scored_articles_with_diversity = select_top_articles_with_diversity(
        articles_for_cluster_scores, articles_for_selection,
        order_metric=exponential_order_metric(0.5), n=flow.articles_limit
    )
    storage = TTDStorage(flow.config.get("db_path"))
    selection = {
        "selection_time": str(datetime.now(timezone.utc)),
        "linear_cluster_scores": linear_cluster_scores,
        "exponential_cluster_scores": exponential_cluster_scores,
        "linearly_selected_articles": top_n_linearly_scored_articles,
        "exponentially_selected_articles": top_n_exponentialy_scored_articles,
        "linearly_selected_articles_with_diversity": top_n_linearly_scored_articles_with_diversity,
        "exponentially_selected_articles_with_diversity": top_n_exponentialy_scored_articles_with_diversity
    }

    for article in top_n_exponentialy_scored_articles_with_diversity:
        storage.save("selected_articles", 
            {
                "original_table_name": flow.articles_table,
                "original_doc_id": article["doc_id"]
            }
        )
    storage.save("selections", selection)
    flow.selection = selection
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
