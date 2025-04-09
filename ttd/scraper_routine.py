import os
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from ttd.scraper.rss_article import RSSArticleScraper, StealthRSSArticleScraper
from ttd.storage.ttd_storage import TTDStorage
from ttd.config import load_config_and_dotenv, update_config

config = load_config_and_dotenv()
DB_PATH = os.path.abspath(config.get("db_path"))
LAST_SCRAPE_DATE = config.get("last_scrape")
if LAST_SCRAPE_DATE and not DEBUG:
    LAST_SCRAPE_DATE = datetime.fromisoformat(LAST_SCRAPE_DATE)
FEEDS_PATH = config.get("feeds_path")
FEEDS_STEALTH_PATH = config.get("feeds_stealth_path")
DEBUG = config.get("debug", False)

def update_scrape_time():
    update_config({
        "last_scrape": datetime.isoformat(datetime.now())
    })


def run_rss_scraper_routine():
    # Initialize storage service
    storage = TTDStorage(DB_PATH)

    # Load RSS feeds from the specified files
    with open(FEEDS_PATH, "r") as f:
        rss_feeds = [line.strip() for line in f if line.strip()]
    with open(FEEDS_STEALTH_PATH, "r") as f:
        rss_stealth_feeds = [line.strip() for line in f if line.strip()]

    # Define a subclasses
    class CustomRSSArticleScraper(RSSArticleScraper):
        def __init__(self, *args, **kwargs):
            super().__init__(rss_feeds, storage, *args, **kwargs)
            self.last_date = LAST_SCRAPE_DATE

    class CustomStealthRSSArticleScraper(StealthRSSArticleScraper):
        def __init__(self, *args, **kwargs):
            super().__init__(rss_stealth_feeds, storage, *args, **kwargs)
            self.last_date = LAST_SCRAPE_DATE

    # Initialize and configure the CrawlerProcess
    process = CrawlerProcess(get_project_settings())
    process.crawl(CustomRSSArticleScraper)
    process.crawl(CustomStealthRSSArticleScraper)
    process.start()  # This will block until the crawling is finished

    # Update the last scrape time in the configuration
    if not DEBUG:
        update_scrape_time()


if __name__ == "__main__":
    run_rss_scraper_routine()
