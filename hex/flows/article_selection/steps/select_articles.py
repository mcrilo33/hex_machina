""" Load articles step. """
import logging
import time
from typing import Callable
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hex.utils.date import to_aware_utc
from hex.flows.analysis import filter_articles_by_clusters
from copy import deepcopy

from hex.storage.hex_storage import HexStorage


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


def compute_cluster_scores(
    articles: list, order_metric: Callable = linear_order_metric
) -> dict:
    """Compute cluster scores based on the number of articles it belongs to."""

    key = 'clusters_names_in_order_added'
    cluster_counter = Counter()
    for article in articles:
        if key in article and article[key]:
            cluster_counter.update(article[key])

    # Only keep clusters that appear at least 2 times
    valid_clusters = {
        cluster for cluster, count in cluster_counter.items() if count >= 2
    }

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


def compute_article_cluster_scores(
    articles: list, cluster_scores: dict, order_metric: Callable = linear_order_metric
) -> dict:
    """Compute article scores based on the clusters they belong to."""

    key = 'clusters_names_in_order_added'
    for article in articles:
        tags = article.get(key, [])
        scores = []
        for order, tag in enumerate(tags):
            if tag in cluster_scores:
                tag_score = cluster_scores[tag] * order_metric(order)
                scores.append(tag_score)
        article["clusters_score"] = sum(scores)
    return articles


def get_top_n_articles(scored_articles, n=5):
    """Return the top n articles sorted by their score descending."""
    scored_articles = deepcopy(scored_articles)
    sorted_articles = sorted(
        scored_articles, key=lambda x: x["clusters_score"], reverse=True
    )

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
    cluster_scores = compute_cluster_scores(
        articles_for_cluster_scores, order_metric=order_metric
    )
    articles = compute_article_cluster_scores(
        articles, cluster_scores, order_metric=order_metric
    )
    # Select top N articles based on cluster scores
    selected_articles = []
    title_already_selected = set()
    url_domain_already_selected = set()
    for _ in range(n):
        # Select the article with the highest cluster score
        selected = False
        while not selected:
            max_item = max(articles, key=lambda d: d["clusters_score"])
            articles.remove(max_item)
            if(max_item["title"] not in title_already_selected
               and max_item["url_domain"] not in url_domain_already_selected):
                selected = True
                title_already_selected.add(max_item["title"])
                url_domain_already_selected.add(max_item["url_domain"])
        selected_articles.append(max_item)
        # Remove best cluster of the selected item from the cluster scores
        # to ensure diversity
        cluster_scores[max_item["clusters_names_in_order_added"][0]] = 0
        articles = compute_article_cluster_scores(
            articles, cluster_scores, order_metric=order_metric
        )

    return cluster_scores, selected_articles


def generate_ingestion_summary(articles) -> str:
    """
    Generates a summary sentence about the number of ingested articles,
    unique sources, and estimated reading time saved.
    """
    num_articles = len(articles)
    unique_sources = set()
    total_reading_time_min = 0

    for article in articles:
        source = article.get("url_domain", "N/A")
        if source != "N/A":
            unique_sources.add(source)

        # Use the same reading time estimation logic as format_article_brief
        text_length = article.get("text_content_length", 0)
        if text_length:
            reading_time_min = max(5, int(text_length / 5 / 180))
        else:
            reading_time_min = 0
        total_reading_time_min += reading_time_min

    num_sources = len(unique_sources)
    total_reading_time_hours = round(total_reading_time_min / 60)

    return (
        f"For this digest it ingested more than {num_articles} articles from "
        f"{num_sources} sources (saving you {total_reading_time_hours} hours of "
        f"reading)."
    )


def execute(flow):
    """Select articles"""
    logger.info("Selecting articles...")
    step_name = "select_articles"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time

    flow.articles = filter_articles_by_clusters(
        flow.articles,
        ["artificial intelligence", "large language models", "India"]
    )
    articles_for_cluster_scores = [
        article for article in flow.articles
        if to_aware_utc(article["published_date"]) >= flow.parsed_cluster_date_threshold
        and "clusters_names_in_order_added" in article
    ]
    articles_for_selection = [
        article for article in flow.articles
        if to_aware_utc(article["published_date"]) >= flow.parsed_date_threshold
        and "clusters_names_in_order_added" in article
    ]
    logger.info(f"✅ {len(articles_for_cluster_scores)} articles for cluster scores")
    logger.info(f"✅ {len(articles_for_selection)} articles for selection")
    logger.info("✅ Scoring clusters...")

    limit = min(flow.articles_limit, len(articles_for_selection))
    cluster_scores, top_n_linearly_scored_articles_with_diversity = \
        select_top_articles_with_diversity(
            articles_for_cluster_scores, articles_for_selection,
            order_metric=linear_order_metric, n=limit
        )
    storage = HexStorage(flow.config.get("db_path"))
    selection = {
        "selection_time": str(datetime.now(timezone.utc)),
        "clusters_scores": cluster_scores,
        "linearly_selected_articles_with_diversity": (
            top_n_linearly_scored_articles_with_diversity
        ),
        "ingestion_summary": generate_ingestion_summary(flow.articles)
    }

    for article in top_n_linearly_scored_articles_with_diversity:
        storage.save(
            flow.selected_articles_table,
            {
                "original_table_name": flow.articles_table,
                "original_doc_id": article["doc_id"]
            }
        )
    doc_id = storage.save("selections", selection)[0]
    selection["doc_id"] = doc_id
    flow.selection = selection
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
