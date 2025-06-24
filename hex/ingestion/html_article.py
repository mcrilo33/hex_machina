import time
import logging
import scrapy
from abc import abstractmethod
from typing import List, Optional, Dict, Any
from scrapy_playwright.page import PageMethod

from .base_article import BaseArticleScraper
from .parser import extract_domain, extract_markdown_from_html


logger = logging.getLogger(__name__)


class HTMLArticleScraper(BaseArticleScraper):
    """
    Generic HTML article scraper that uses Playwright for JavaScript-rendered content.
    Extends BaseArticleScraper and provides abstract methods for site-specific parsing.
    """

    name = "html_article_scraper"
    custom_settings = {
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "DOWNLOAD_TIMEOUT": 30,
        "RETRY_TIMES": 5,
        "TELNETCONSOLE_ENABLED": False,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408],
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com",
            "Connection": "close"
        },
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 100000,
    }

    def __init__(
        self,
        start_urls: List[str],
        storage,
        articles_table="articles",
        articles_limit=None,
        date_threshold=None,
        playwright_timeout: int = 60000,
        wait_for_js: int = 3000,
        *args,
        **kwargs
    ):
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )
        self.playwright_timeout = playwright_timeout
        self.wait_for_js = wait_for_js

    def start_requests(self):
        """Generate requests for each start URL."""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,
                meta={
                    "handle_httpstatus_all": True,
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod(
                            "evaluate",
                            "() => Object.defineProperty( \
                                navigator, 'webdriver', {get: () => undefined})"
                        ),
                        PageMethod("wait_for_timeout", self.wait_for_js),
                    ]
                }
            )

    def handle_error(self, failure):
        """Handle request errors."""
        error = {
            "status": failure.response.status if hasattr(failure, 'response') else None,
            "url": failure.response.url if hasattr(failure, 'response') else None,
            "message": str(failure.value)
        }
        logger.warning(f"Request failed: {error}")
        return []

    def parse(self, response):
        """
        Parse the main page and extract article links.
        Calls load_more_articles if needed, then processes each article.
        After processing all articles, handles pagination if needed.
        """
        if response.status != 200:
            logger.warning(
                f"Failed to load page {response.url}: status {response.status}"
            )
            return []

        # Load more articles if needed (pagination, infinite scroll, etc.)
        self.load_more_articles(response)

        # Extract article links from the page
        article_links = list(dict.fromkeys(self.extract_article_links(response)))
        article_links = article_links[:6]

        if not article_links:
            logger.info(f"No article links found on {response.url}")
        else:
            logger.info(f"Found {len(article_links)} article links on {response.url}")

            # Process each article link
            for link in article_links:
                if self.limit_is_reached():
                    break

                yield scrapy.Request(
                    url=link,
                    callback=self.parse_article_page,
                    errback=self.handle_article_error,
                    meta={
                        "handle_httpstatus_all": True,
                        "playwright": True,
                        "playwright_include_page": True,
                        "dont_redirect": False,
                        "playwright_page_methods": [
                            PageMethod(
                                "evaluate",
                                "() => Object.defineProperty( \
                                    navigator, 'webdriver', {get: () => undefined})"
                            ),
                            PageMethod("wait_for_timeout", self.wait_for_js),
                        ]
                    }
                )

        # Handle pagination after processing all articles
        next_page_url = self.get_next_page_url(response)
        if next_page_url and not self.limit_is_reached():
            logger.info(f"Following pagination to: {next_page_url}")
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
                errback=self.handle_error,
                meta={
                    "handle_httpstatus_all": True,
                    "playwright": True,
                    "playwright_include_page": True,
                    "dont_redirect": False,
                    "playwright_page_methods": [
                        PageMethod(
                            "evaluate",
                            "() => Object.defineProperty( \
                                navigator, 'webdriver', {get: () => undefined})"
                        ),
                        PageMethod("wait_for_timeout", self.wait_for_js),
                    ]
                }
            )

    def handle_article_error(self, failure):
        """Handle individual article request errors."""
        error = {
            "status": failure.response.status if hasattr(failure, 'response') else None,
            "url": failure.response.url if hasattr(failure, 'response') else None,
            "message": str(failure.value)
        }
        logger.warning(f"Article request failed: {error}")
        return []

    def parse_article_page(self, response):
        """
        Parse individual article pages and extract structured data.
        """
        if response.status != 200:
            logger.warning(
                f"Failed to load article {response.url}: status {response.status}"
            )
            return
        if self.limit_is_reached():
            return

        start_time = time.time()

        try:
            # Extract article data using abstract methods
            article_data = {
                "url": response.url,
                "url_domain": extract_domain(response.url),
                "title": self.get_title(response),
                "author": self.get_author(response),
                "published_date": self.get_published_date(response),
                "html_content": response.text,
                "text_content": self.get_text_content(response)
            }

            # Clean and validate the data
            if not article_data["title"]:
                logger.warning(f"No title found for article {response.url}")
                return

            if(article_data
               and article_data["title"] is not None
               and article_data["text_content"] is not None
               and article_data["published_date"] is not None):
                # Add metadata
                elapsed_time = time.time() - start_time
                article_data["metadata"] = {
                    "error": None,
                    "duration": int(elapsed_time)
                }

                # Store the article
                self.store([article_data])
                self.stored_count += 1

        except Exception as e:
            logger.error(f"Error processing article {response.url}: {e}")
            elapsed_time = time.time() - start_time
            error_article = {
                "url": response.url,
                "url_domain": extract_domain(response.url),
                "title": "Error processing article",
                "metadata": {
                    "error": {
                        "status": "Error processing article",
                        "message": str(e),
                        "url": response.url,
                    },
                    "duration": int(elapsed_time)
                }
            }
            self.store([error_article])
            self.stored_count += 1

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        This is a default implementation that can be overridden.
        """
        # Default implementation - extract all links that might be articles
        # Subclasses should override this with site-specific logic
        links = response.css("a[href]::attr(href)").getall()
        article_links = []
        
        for link in links:
            if link and self.is_article_link(link):
                article_links.append(response.urljoin(link))
        
        return article_links

    def is_article_link(self, link: str) -> bool:
        """
        Determine if a link points to an article.
        This is a default implementation that can be overridden.
        """
        # Default implementation - basic heuristics
        article_indicators = [
            "/article/", "/post/", "/story/", "/news/", 
            "/blog/", "/entry/", "/content/"
        ]
        
        link_lower = link.lower()
        return any(indicator in link_lower for indicator in article_indicators)

    @abstractmethod
    def get_published_date(self, response) -> Optional[str]:
        """
        Extract the published date from the article page.
        
        Args:
            response: Scrapy response object
            
        Returns:
            Published date string or None if not found
        """
        pass

    @abstractmethod
    def get_author(self, response) -> Optional[str]:
        """
        Extract the author from the article page.
        
        Args:
            response: Scrapy response object
            
        Returns:
            Author string or None if not found
        """
        pass

    @abstractmethod
    def get_title(self, response) -> Optional[str]:
        """
        Extract the title from the article page.
        
        Args:
            response: Scrapy response object
            
        Returns:
            Title string or None if not found
        """
        pass

    def get_text_content(self, response) -> Optional[str]:
        """
        Extract the main text content from the article page.
        Gets all text content within the section
        """
        # Get all text content from the section
        content_elements = extract_markdown_from_html(response.text)
        return content_elements

    @abstractmethod
    def load_more_articles(self, response) -> None:
        """
        Load more articles if needed (pagination, infinite scroll, etc.).
        This method can interact with the page to load additional content.
        
        Args:
            response: Scrapy response object
        """
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        This is a default implementation that can be overridden.
        
        Args:
            response: Scrapy response object
            
        Returns:
            Next page URL or None if no next page
        """
        # Default implementation - look for common next page patterns
        next_selectors = [
            'a[rel="next"]::attr(href)',
            '.next::attr(href)',
            '.next-page::attr(href)',
            '.pagination .next::attr(href)',
            'a:contains("Next")::attr(href)',
            'a:contains("Next Page")::attr(href)',
            'a:contains("Older")::attr(href)',
            'a:contains("More")::attr(href)',
        ]

        for selector in next_selectors:
            next_url = response.css(selector).get()
            if next_url:
                full_url = response.urljoin(next_url)
                return full_url

        return None 
    
    def parse_article(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse and enrich the raw article data.
        """
        pass