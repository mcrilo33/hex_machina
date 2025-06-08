""" Load articles step. """
import logging
import time
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from hex.ingestion.rss_article import RSSArticleScraper, StealthRSSArticleScraper
from hex.storage.hex_storage import HexStorage


logger = logging.getLogger(__name__)

def execute(flow):
    """Ingest articles from RSS feeds."""
    logger.info("Ingesting RSS articles...")
    step_name = "ingest_rss_articles"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    flow.metrics.setdefault("stored_count", {})[step_name] = {}

    storage = HexStorage(flow.config.get("db_path"))

    class CustomRSSArticleScraper(RSSArticleScraper):
        def __init__(self, *args, **kwargs):
            super().__init__(
                flow.rss_feeds,
                storage,
                articles_table=flow.articles_table,
                articles_limit=flow.articles_limit,
                date_threshold=flow.date_threshold,
                *args,
                **kwargs
            )
        
        def closed(self, reason):
            flow.metrics["stored_count"][step_name]["rss_article_scraper"] = \
                self.stored_count

    class CustomStealthRSSArticleScraper(StealthRSSArticleScraper):
        def __init__(self, *args, **kwargs):
            super().__init__(
                flow.rss_stealth_feeds,
                storage,
                articles_table=flow.articles_table,
                articles_limit=flow.articles_limit,
                date_threshold=flow.date_threshold,
                *args,
                **kwargs
            )

        def closed(self, reason):
            flow.metrics["stored_count"][step_name]["stealth_rss_article_scraper"] = \
                self.stored_count

    process = CrawlerProcess(get_project_settings())
    flow.metrics["stored_count"][step_name]["rss_article_scraper"] = 0
    process.crawl(CustomRSSArticleScraper)
    flow.metrics["stored_count"][step_name]["stealth_rss_article_scraper"] = 0
    process.crawl(CustomStealthRSSArticleScraper)
    process.start()
    articles = storage.get_all(flow.articles_table)
    if len(articles) == 0:
        flow.last_id = 0
    else:
        flow.last_id = max([int(doc.get("doc_id")) for doc in articles])
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
    storage.save("ingestions",
        {
            "articles_table": flow.articles_table,
            "articles_limit": flow.articles_limit,
            "date_threshold": flow.date_threshold,
            "rss_article_scraper":
                flow.metrics["stored_count"][step_name]["rss_article_scraper"],
            "stealth_rss_article_scraper":
                flow.metrics["stored_count"][step_name]["stealth_rss_article_scraper"],
            "first_id": flow.first_id,
            "last_id": flow.last_id,
            "duration": total_time
        }
    )
