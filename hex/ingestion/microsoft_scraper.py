import logging
import re
from typing import List, Optional
from datetime import datetime

from .html_article import HTMLArticleScraper


logger = logging.getLogger(__name__)


class MicrosoftScraper(HTMLArticleScraper):
    """
    Scraper for Microsoft AI news articles.
    Extracts articles from news.microsoft.com/source/view-all/?_categories=ai
    """

    name = "microsoft_scraper"
    
    # Custom settings for Microsoft news
    custom_settings = {
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "DOWNLOAD_TIMEOUT": 60,
        "RETRY_TIMES": 3,
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
            "Origin": "https://news.microsoft.com",
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
            start_urls = ["https://news.microsoft.com/source/view-all/?_categories=ai"]
        
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags in the second div.wp-block-columns
        """
        # Select all article links in the second div.wp-block-columns
        article_links = response.css(
            "div.wp-block-columns:nth-of-type(2) a::attr(href)"
        ).getall()
        
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
        Microsoft news articles should be valid URLs
        """
        return link and link.startswith(('http', '/')) and "/topics/" not in link

    def get_title(self, response) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from the first h2 in <article>
        """
        title = response.css("article h2:first-of-type split-text::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, response) -> Optional[str]:
        """
        Extract the author from the article page.
        Searches for pattern 'written by {author}' in span::text within 
        first div[role="paragraph"]
        """
        # Get all span text from the first div[role="paragraph"]
        paragraph_spans = response.css(
            'div[role="paragraph"] split-text::text'
        ).getall()
        
        if paragraph_spans:
            # Join all span text and search for 'written by' pattern
            full_text = ' '.join(
                [span.strip() for span in paragraph_spans if span.strip()]
            )
            
            # Search for 'written by {author}' pattern
            match = re.search(r'written by\s+([^,\.]+)', full_text, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                return author
        
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
        Searches for pattern 'June 16 2025' in span::text within 
        first div[role="paragraph"]
        """
        # Get all span text from the first div[role="paragraph"]
        paragraph_spans = response.css(
            'div[role="paragraph"] split-text::text'
        ).getall()
        
        if paragraph_spans:
            # Join all span text and search for date pattern
            full_text = ' '.join(
                [span.strip() for span in paragraph_spans if span.strip()]
            )
            
            # Search for date pattern like 'June 16 2025'
            date_pattern = r'([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})'
            match = re.search(date_pattern, full_text)
            
            if match:
                month, day, year = match.groups()
                try:
                    # Parse date in format 'June 16 2025'
                    date_str = f"{month} {day}, {year}"
                    parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                    formatted_date = parsed_date.strftime(
                        "%a, %d %b %Y 12:00:01 +0000"
                    )
                    return formatted_date
                except ValueError as e:
                    logger.warning(f"Failed to parse date '{date_str}': {e}")
        
        logger.warning("No valid date found in paragraph spans")
        return None

    def load_more_articles(self, response) -> None:
        """
        Load more articles if needed.
        No pagination needed for Microsoft news as specified.
        """
        # No pagination needed for Microsoft news
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        Returns None as no pagination is needed.
        """
        return None 