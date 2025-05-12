""" Load articles step. """
import logging
import time
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from ttd.ingestion.rss_article import RSSArticleScraper, StealthRSSArticleScraper
from ttd.storage.ttd_storage import TTDStorage


logger = logging.getLogger(__name__)

def execute(flow):
    """Ingest articles from RSS feeds."""
    logger.info("Ingesting RSS articles...")
    step_name = "ingest_rss_articles"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    flow.metrics.setdefault("stored_count", {})[step_name] = {}

    storage = TTDStorage(flow.config.get("db_path"))

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
    process.crawl(CustomRSSArticleScraper)
    process.crawl(CustomStealthRSSArticleScraper)
    process.start()
    flow.last_id = max([int(doc.get("doc_id")) for doc in storage.get_all(flow.articles_table)])
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
