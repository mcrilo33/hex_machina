import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from io import BytesIO
from datetime import datetime, timezone
from metaflow import step, card, current
from metaflow.cards import Markdown, Table, Image

from hex.flows.analysis import get_reference_domains, format_duration, \
                               prepare_article_distribution_indexed_by_date, \
                               plot_article_distribution_indexed_by_date, \
                               prepare_error_distribution_by_domain_and_status, \
                               plot_error_distribution_by_domain_and_status, \
                               prepare_domain_counts, generate_domain_match_markdown, \
                               prepare_field_coverage, generate_field_coverage_markdown
from hex.flows.analysis import get_articles_with_no_error
from hex.storage.hex_storage import HexStorage

logger = logging.getLogger(__name__)

def render_domain_match_card_group(articles, rss_files: dict):
    """
    Generate one markdown section per RSS file (with title), comparing domains.
    """
    current.card.append(Markdown("## 🗂️ Domain Distribution in Ingested Articles"))

    domain_counts = prepare_domain_counts(articles)

    for label, path in rss_files.items():
        reference_domains = get_reference_domains(path)
        markdown = generate_domain_match_markdown(domain_counts, reference_domains, label)
        current.card.append(Markdown(markdown))

def render_article_distribution_indexed_by_date(articles):
    current.card.append(Markdown("## 📊 Article Repartition Over Time (by Domain)"))

    grouped = prepare_article_distribution_indexed_by_date(articles)
    if grouped.empty:
        current.card.append(Markdown("_No valid articles to plot._"))
        return
    
    fig = plot_article_distribution_indexed_by_date(grouped)
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    current.card.append(Image(buf.read()))


def render_error_distribution_by_domain_and_status(articles):
    current.card.append(Markdown("## ❗ Error Distribution by Domain and Status"))

    if not articles:
        current.card.append(Markdown("_No articles available._"))
        return

    grouped = prepare_error_distribution_by_domain_and_status(articles)

    if grouped.empty:
        current.card.append(Markdown("_No error records with status found._"))
        return

    fig = plot_error_distribution_by_domain_and_status(grouped)

    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    current.card.append(Image(buf.read()))

def render_field_coverage_card(articles):
    total = len(articles)
    field_coverage = prepare_field_coverage(articles)
    markdown = generate_field_coverage_markdown(field_coverage, total)

    current.card.append(Markdown("## 🧾 Field Coverage Summary"))
    current.card.append(Markdown(markdown))

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
        ["Website Scraper Count",
                flow.metrics["stored_count"]["ingest_rss_articles"]["website_scraper"]],
        ["Total Count",
                (flow.metrics["stored_count"]["ingest_rss_articles"]["rss_article_scraper"]
                 + flow.metrics["stored_count"]["ingest_rss_articles"]["stealth_rss_article_scraper"]
                 + flow.metrics["stored_count"]["ingest_rss_articles"]["website_scraper"])],
        ["Start Time", dt.isoformat()],
        ["Duration", format_duration(
            flow.metrics["step_duration"]["ingest_rss_articles"]
        )]
    ]

    current.card.append(Table(
        headers=["Parameter", "Value"],
        data=rows
    ))

    storage = HexStorage(flow.config.get("db_path"))
    articles = storage.get_obj_in_range(
        flow.articles_table,
        flow.first_id,
        flow.last_id
    )
    articles_with_no_error = get_articles_with_no_error(articles)

    rss_files = {
        "Regular RSS Feeds": Path(Path(storage.db_path).parent,'rss_feeds.txt'),
        "Stealth RSS Feeds": Path(Path(storage.db_path).parent,'rss_feeds_stealth.txt'),
        "Regular HTML Websites": Path(Path(storage.db_path).parent,'website_urls.txt')
    }
    render_domain_match_card_group(articles_with_no_error, rss_files)

    render_article_distribution_indexed_by_date(articles_with_no_error)

    render_error_distribution_by_domain_and_status(articles)

    render_field_coverage_card(articles_with_no_error)
