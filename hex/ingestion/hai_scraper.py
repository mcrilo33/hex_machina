import logging
from typing import List, Optional
from datetime import datetime

from .html_article import HTMLArticleScraper


logger = logging.getLogger(__name__)


class HAIScraper(HTMLArticleScraper):
    """
    Scraper for Stanford HAI news articles.
    Extracts articles from hai.stanford.edu/news?filterBy=news
    """

    name = "hai_scraper"
    
    # Custom settings for Stanford HAI
    custom_settings = {
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "DOWNLOAD_TIMEOUT": 60,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [400, 403, 429, 500, 502, 503, 504, 522, 524, 408],
        "TELNETCONSOLE_ENABLED": False,
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
            "Origin": "https://hai.stanford.edu",
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
            start_urls = ["https://hai.stanford.edu/news?filterBy=news"]
        
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags with href containing /news/
        """
        # Select all article links with /news/ pattern
        article_links = response.css("a[href*='/news/']::attr(href)").getall()
        
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
        Stanford HAI articles contain /news/ in the URL
        """
        return "/news/" in link and not "filterBy" in link

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
        No author information available for Stanford HAI articles
        """
        return None

    def get_text_content(self, response) -> Optional[str]:
        """
        Extract the main text content from the article page.
        Gets all text from p elements
        """
        # Get all text from p elements
        p_divs = response.css("p::text").getall()
        
        if p_divs:
            # Join all paragraph text with newlines
            content = '\n\n'.join([text.strip() for text in p_divs if text.strip()])
            return content if content else None
        
        logger.warning("No text content found in p elements")
        return None

    def get_published_date(self, response) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for div element with date format 'June 23, 2025'
        """
        # Look for div elements that might contain dates
        date_divs = response.css("div::text").getall()
        
        for div_text in date_divs:
            if div_text:
                date_str = div_text.strip()
                try:
                    # Parse date in format 'June 23, 2025'
                    parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                    formatted_date = parsed_date.strftime(
                        "%a, %d %b %Y 12:00:01 +0000"
                    )
                    return formatted_date
                except ValueError:
                    # Continue checking other divs if this one doesn't match the format
                    continue
        
        logger.warning("No valid date found in div elements")
        return None

    def load_more_articles(self, response) -> None:
        """
        Load more articles if needed.
        No pagination needed for Stanford HAI news as specified.
        """
        # No pagination needed for Stanford HAI news
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        Returns None as no pagination is needed.
        """
        return None
