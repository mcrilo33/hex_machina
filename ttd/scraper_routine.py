from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from ttd.scraper.rss_article import RSSArticleScraper
from ttd.storage.ttd_storage import TTDStorage
from ttd.config import load_config, update_config

config = load_config()
DB_PATH = config["db_path"]
LAST_RUN_DATE = config["last_scrape"]
if LAST_RUN_DATE:
    LAST_RUN_DATE = datetime.fromisoformat(LAST_RUN_DATE)
FEEDS_PATH = config["feeds_path"]
DEBUG = config["debug"]

def update_scrape_time():
    update_config({
        "last_scrape": datetime.isoformat(datetime.now())
    })

def run_rss_scraper_routine():
    # Initialize storage service
    storage = TTDStorage(DB_PATH)

    # Load RSS feeds from the specified file
    with open(FEEDS_PATH, "r") as f:
        rss_feeds = [line.strip() for line in f if line.strip()]

    # Define a subclass of RSSArticleScraper to pass additional arguments
    class CustomRSSArticleScraper(RSSArticleScraper):
        def __init__(self, *args, **kwargs):
            super().__init__(rss_feeds, storage,*args, **kwargs)
            self.last_date = LAST_RUN_DATE

    # Initialize and configure the CrawlerProcess
    process = CrawlerProcess(get_project_settings())
    process.crawl(CustomRSSArticleScraper)
    process.start()  # This will block until the crawling is finished

    # Update the last scrape time in the configuration
    if not DEBUG:
        update_scrape_time()


if __name__ == "__main__":
    run_rss_scraper_routine()
