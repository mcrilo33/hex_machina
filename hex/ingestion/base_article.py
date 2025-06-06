import scrapy
import logging
from ttd.utils.date import to_aware_utc
from abc import ABC, abstractmethod
from typing import List


logger = logging.getLogger(__name__)

class BaseArticleScraper(scrapy.Spider, ABC):
    """
    Abstract base class for all article Scrapy-based article scrapers.
    Inherits from scrapy.Spider and enforces a standard scraping interface.
    """

    def __init__(
        self,
        start_urls: List[str],
        storage,
        articles_table="articles",
        articles_limit=None,
        date_threshold=None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls
        self.storage = storage
        self.stored_count = 0
        self.articles_table = articles_table
        self.articles_limit = articles_limit
        self.date_threshold = date_threshold
        self.parsed_date_threshold = to_aware_utc(date_threshold) if date_threshold else None

    def should_skip_entry(self, entry: dict) -> bool:
        """ Return True if the entry should be skipped. """
    
        return (
            self.limit_is_reached() or
            self.too_old_entry(entry)
        )
        
    def limit_is_reached(self) -> bool:
        if self.articles_limit != 0 and self.stored_count >= self.articles_limit:
            return True
        else:
            return False

    def too_old_entry(self, entry: dict) -> bool:
        """ Return True if the entry is older than self.last_date. """
        if not self.date_threshold:
            return False

        published_str = entry.get("published_date")
        if not published_str:
            return False

        try:
            return to_aware_utc(published_str) < self.parsed_date_threshold
        except Exception as e:
            logger.warning(
                f"Failed to parse published date {published_str}: {e}"
            )
            return False

    @abstractmethod
    def parse(self, response):
        """
        Parse a raw source (HTML response or RSS entry)
        and return a list of article dicts.
        """
        pass

    @abstractmethod
    def parse_article(self, response):
        """
        Parse a single article block (HTML element or feed entry)
        into a structured dict.
        """
        pass

    def store(self, articles: List[dict]):
        """
        Store the parsed articles in the database.
        """
        return self.storage.save(self.articles_table, articles)
