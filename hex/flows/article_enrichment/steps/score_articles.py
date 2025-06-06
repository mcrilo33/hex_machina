""" Compute cluster and article scores. """
import logging
import math
from collections import Counter, defaultdict
from hex.storage.hex_storage import HexStorage

logger = logging.getLogger(__name__)


def execute(flow):
    """Compute article scores based on clusters frequency and order."""

    logger.info("⚡ Computing article scores...")

    articles = flow.replicated_articles
    cluster_counter = Counter()
    storage = HexStorage(flow.config.get("db_path"))

    # First pass: count how many times each cluster appears
    for article in articles:
        clusters = article.get('clusters_names_in_order_added', [])
        if clusters:
            cluster_counter.update(clusters)

    # Only keep clusters appearing at least 3 times
    valid_clusters = {cluster for cluster, count in cluster_counter.items() if count >= 2}

    # Compute order weights (early tag = bigger weight)
    cluster_order_scores = defaultdict(list)
    for article in articles:
        tags = article.get("tags", [])
        for order, tag in enumerate(tags):
            if tag in valid_clusters:
                cluster_order_scores[tag].append(1 / (order + 1))  # Order starts at 0

    # Final cluster scores
    cluster_scores = {}
    for cluster, penalties in cluster_order_scores.items():
        avg_penalty = sum(penalties) / len(penalties)
        frequency = cluster_counter[cluster]
        cluster_scores[cluster] = frequency * avg_penalty

    logger.info(f"✅ Computed scores for {len(cluster_scores)} valid clusters.")

    # Compute per-article scores
    enriched_articles = []
    for idx, article in enumerate(articles):
        tags = article.get("tags", [])
        article_score = sum(cluster_scores.get(tag, 0) for tag in tags)

        enriched_article = dict(article)
        enriched_article["score"] = article_score
        enriched_articles.append(enriched_article)

        logger.info(f"🏷️ Scored article {idx+1}/{len(articles)} with score {article_score:.2f}")

    # Save enriched articles back to flow
    storage.update(flow.replicates_table, storage.lazy_load(enriched_article))
    flow.replicated_articles = enriched_articles
    logger.info("✅ Article scoring completed.")