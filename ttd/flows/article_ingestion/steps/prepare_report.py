import logging
from datetime import datetime, timezone
from tinydb import Query
from metaflow import step, card, current
from metaflow.cards import Markdown, Table

from ttd.storage.ttd_storage import TTDStorage

logger = logging.getLogger(__name__)

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
from metaflow.cards import Markdown, Image
from email.utils import parsedate_to_datetime


def render_article_repartition_over_time(articles):
    current.card.append(Markdown("## 📊 Article Repartition Over Time (by Domain)"))

    if not articles:
        current.card.append(Markdown("_No articles found to plot._"))
        return

    # Parse dates and collect domains
    parsed_data = []
    for article in articles:
        pub_date = article.get("published_date")
        domain = article.get("url_domain", "Unknown")
        try:
            dt = parsedate_to_datetime(pub_date) if isinstance(pub_date, str) else pub_date
            parsed_data.append({"date": dt.date(), "domain": domain})
        except Exception:
            continue

    if not parsed_data:
        current.card.append(Markdown("_No valid dates to plot._"))
        return

    # Create a DataFrame
    df = pd.DataFrame(parsed_data)

    # Pivot table: rows = date, columns = domain, values = counts
    grouped = df.groupby(["date", "domain"]).size().unstack(fill_value=0)

    # Plot stacked bar chart
    fig, ax = plt.subplots(figsize=(12, 5))
    grouped.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_title("Articles per Day by Domain")
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Articles")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save to card
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    current.card.append(Image(buf.read()))

def render_error_distribution_by_domain_and_status(articles):
    current.card.append(Markdown("## Error Distribution by Domain and Status"))

    if not articles:
        current.card.append(Markdown("_No articles available._"))
        return

    # Extract (domain, status) for each article with an error
    records = []
    for article in articles:
        metadata = article.get("metadata", {})
        error = metadata.get("error")
        if error:
            records.append({"domain": article["url_domain"], "status": error["status"]})
        else:
            records.append({"domain": article["url_domain"], "status": "OK"})

    if not records:
        current.card.append(Markdown("_No error records with status found._"))
        return

    # Create DataFrame
    df = pd.DataFrame(records)

    # Group by domain and status
    grouped = df.groupby(["domain", "status"]).size().unstack(fill_value=0)

    # Plot stacked bar chart
    fig, ax = plt.subplots(figsize=(12, 6))
    grouped.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_title("❗ Errors by Domain and Status")
    ax.set_xlabel("URL Domain")
    ax.set_ylabel("Number of Errors")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save to card
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    current.card.append(Image(buf.read()))

def format_duration(seconds: float) -> str:
    """Convert duration in seconds into a human-readable string."""
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"

    mins, secs = divmod(seconds, 60)
    if mins < 60:
        return f"{mins}m {secs}s"

    hrs, mins = divmod(mins, 60)
    return f"{hrs}h {mins}m {secs}s"


def get_articles_in_range(storage, table_name, first_id, last_id):
    """Fetch articles with ID between first_id and last_id (inclusive)."""
    articles = storage.get_all(table_name)
    articles = [article for article in articles if
                int(article.get("doc_id")) > first_id and
                int(article.get("doc_id")) <= last_id]

    return articles

@card
@step
def execute(flow):
    """Prepare a comprehensive report of the article selection process."""
    current.card.append(Markdown("# 📋 Ingestion Overview"))

    # --- Key-value pairs for reporting ---
    timestamp = flow.metrics["step_start_times"]["ingest_rss_articles"]
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    rows = [
        ["Articles Table", flow.articles_table],
        ["Articles Limit", flow.articles_limit],
        ["Date Threshold", str(flow.date_threshold)],
        ["First ID", flow.first_id],
        ["Last ID", flow.last_id],
        ["RSS Article Scraper Count",
                flow.metrics["stored_count"]["ingest_rss_articles"]["rss_article_scraper"]],
        ["Stealth RSS Article Scraper Count",
                flow.metrics["stored_count"]["ingest_rss_articles"]["stealth_rss_article_scraper"]],
        ["Total Count",
                (flow.metrics["stored_count"]["ingest_rss_articles"]["stealth_rss_article_scraper"]
                 + flow.metrics["stored_count"]["ingest_rss_articles"]["rss_article_scraper"])],
        ["Start Time", dt.isoformat()],
        ["Duration", format_duration(
            flow.metrics["step_duration"]["ingest_rss_articles"]
        )]
    ]

    current.card.append(Table(
        headers=["Parameter", "Value"],
        data=rows
    ))

    storage = TTDStorage(flow.config.get("db_path"))
    articles = get_articles_in_range(
        storage,
        flow.articles_table,
        flow.first_id,
        flow.last_id
    )
    articles_with_no_error = []
    for article in articles:
        if not article.get("metadata", {}).get("error"):
            articles_with_no_error.append(article)
    render_article_repartition_over_time(articles_with_no_error)
    render_error_distribution_by_domain_and_status(articles)