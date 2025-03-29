from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Any
import scrapy


class BaseArticleScraper(scrapy.Spider, ABC):
    """
    Abstract base class for all article Scrapy-based article scrapers.
    Inherits from scrapy.Spider and enforces a standard scraping interface.
    """

    def __init__(self, start_urls: List[str], storage_service, last_date=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls
        self.storage_service = storage_service

        if last_date is not None and not isinstance(last_date, datetime):
            raise TypeError("last_date must be a datetime.datetime instance or None")
        self.last_date = last_date  # Optional[datetime]

    def should_skip_entry(self, entry: dict) -> bool:
        """
        Return True if the entry is older than self.last_date.
        """
        if not self.last_date:
            return False

        published_str = entry.get("published_date")
        if not published_str:
            return False

        try:
            published_dt = datetime.strptime(published_str, "%Y-%m-%d")
            return published_dt < self.last_date
        except Exception:
            return False

    @abstractmethod
    def parse(self, response):
        """
        Parse a raw source (HTML response or RSS entry) and return a list of article dicts.
        """
        pass

    @abstractmethod
    def parse_article(self, response):
        """
        Parse a single article block (HTML element or feed entry) into a structured dict.
        """
        pass

    def store(self, articles: List[dict]) -> None:
        """
        Store article data using the provided storage service.
        """
        if articles:
            self.storage_service.save_articles(articles)