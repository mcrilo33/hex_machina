import logging
from typing import List, Optional
from datetime import datetime

from .html_article import HTMLArticleScraper


logger = logging.getLogger(__name__)


class HBRScraper(HTMLArticleScraper):
    """
    Scraper for Harvard Business Review latest articles.
    Extracts articles from hbr.org/the-latest
    """

    name = "hbr_scraper"
    
    # Custom settings for HBR
    custom_settings = {
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "DOWNLOAD_TIMEOUT": 60,
        "RETRY_TIMES": 3,
        "TELNETCONSOLE_ENABLED": False,
        "RETRY_HTTP_CODES": [400, 403, 429, 500, 502, 503, 504, 522, 524, 408],
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.google.com/",
            "Origin": "https://hbr.org",
        },
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 120000,
    }
    
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
        # Set default start URL if not provided
        if not start_urls:
            start_urls = ["https://hbr.org/the-latest"]
        
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags in <stream-list> that start with "/YYYY/MM/"
        """
        # Select all article links in <stream-list>
        article_links = response.css("stream-list a::attr(href)").getall()
        
        # Filter and clean the links
        cleaned_links = []
        for link in article_links:
            if link and self.is_article_link(link):
                full_url = response.urljoin(link)
                cleaned_links.append(full_url)
        
        logger.info(f"Found {len(cleaned_links)} article links")
        return cleaned_links

    def is_article_link(self, link: str) -> bool:
        """
        Determine if a link points to an article.
        HBR articles start with "/YYYY/MM/" pattern
        """
        import re
        return link and re.match(r'/\d{4}/\d{2}/', link)

    def get_title(self, response) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from the first h1
        """
        title = response.css("h1:first-of-type::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, response) -> Optional[str]:
        """
        Extract the author from the article page.
        No author information available for HBR articles
        """
        return None

    def get_text_content(self, response) -> Optional[str]:
        """
        Extract the main text content from the article page.
        Uses the parent method get_text_content
        """
        return super().get_text_content(response)

    def get_published_date(self, response) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for span element with date format 'June 23, 2025'
        """
        # Look for span elements that might contain dates
        date_spans = response.css("span::text").getall()
        
        for span_text in date_spans:
            if span_text:
                date_str = span_text.strip()
                try:
                    # Parse date in format 'June 23, 2025'
                    parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                    formatted_date = parsed_date.strftime(
                        "%a, %d %b %Y 12:00:01 +0000"
                    )
                    return formatted_date
                except ValueError:
                    # Continue checking other spans if this one doesn't match the format
                    continue
        
        logger.warning("No valid date found in span elements")
        return None

    def load_more_articles(self, response) -> None:
        """
        Load more articles if needed.
        No pagination needed for HBR latest as specified.
        """
        # No pagination needed for HBR latest
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        Returns None as no pagination is needed.
        """
        return None 