import scrapy
import logging
from hex.utils.date import to_aware_utc
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
        self.parsed_date_threshold = (
            to_aware_utc(date_threshold) if date_threshold else None
        )
        # Cache existing articles for duplicate checking
        self._existing_article_combinations = self._load_existing_combinations()

    def _load_existing_combinations(self) -> set:
        """
        Load existing article (title, url_domain) combinations from database.
        Called once during initialization.

        Returns:
            Set of (title, url_domain) tuples for fast duplicate checking
        """
        existing_articles = self.storage.get_all(self.articles_table)
        existing_combinations = set()

        for article in existing_articles:
            title = article.get("title", "").strip()
            url_domain = article.get("url_domain", "").strip()
            if title and url_domain:
                existing_combinations.add((title, url_domain))

        logger.info(
            f"Loaded {len(existing_combinations)} existing article combinations "
            f"for duplicate checking"
        )
        return existing_combinations

    def should_skip_entry(self, entry: dict) -> bool:
        """ Return True if the entry should be skipped. """

        return (
            self.limit_is_reached() or
            self.too_old_entry(entry)
        )

    def limit_is_reached(self) -> bool:
        if self.articles_limit is not None and self.stored_count >= self.articles_limit:
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

    def _filter_duplicate_articles(self, articles: List[dict]) -> List[dict]:
        """
        Filter out articles that already exist in the database based on
        title and url_domain combination.

        Args:
            articles: List of article dictionaries to check

        Returns:
            List of articles that don't already exist in the database
        """
        if not articles:
            return []

        # Filter out duplicates using cached combinations
        unique_articles = []
        for article in articles:
            title = article.get("title", "").strip()
            url_domain = article.get("url_domain", "").strip()

            if not title or not url_domain:
                logger.warning(
                    f"Article missing title or url_domain: "
                    f"title='{title}', url_domain='{url_domain}'"
                )
                continue

            if (title, url_domain) not in self._existing_article_combinations:
                unique_articles.append(article)
                # Add to cache to prevent duplicates within the same session
                self._existing_article_combinations.add((title, url_domain))
            else:
                logger.info(
                    f"Skipping duplicate article: '{title}' from {url_domain}"
                )

        return unique_articles

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
        Store the parsed articles in the database, filtering out duplicates
        based on title and url_domain combination.
        """
        # Filter out duplicate articles
        unique_articles = self._filter_duplicate_articles(articles)

        if not unique_articles:
            logger.info("No new unique articles to store")
            return []

        logger.info(
            f"Storing {len(unique_articles)} unique articles "
            f"(filtered out {len(articles) - len(unique_articles)} duplicates)"
        )

        return self.storage.save(self.articles_table, unique_articles)
