import logging
from typing import List, Optional
from datetime import datetime

from .html_article import HTMLArticleScraper


logger = logging.getLogger(__name__)


class SyncedReviewScraper(HTMLArticleScraper):
    """
    Scraper for Synced Review articles.
    Extracts articles from syncedreview.com
    """

    name = "synced_review_scraper"
    
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
            start_urls = ["https://syncedreview.com"]
        
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags within div#primary
        """
        # Select all article links within the primary div
        article_links = response.css("div#primary a::attr(href)").getall()
        
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
        Synced Review articles have URLs like /YYYY/MM/DD/
        """
        # Synced Review article pattern: /YYYY/MM/DD/
        import re
        pattern = r'/20\d{2}/\d{2}/\d{2}/'
        return bool(re.search(pattern, link)) and "#comments" not in link

    def get_title(self, response) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from h1.entry-title
        """
        title = response.css("h1.entry-title::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, response) -> Optional[str]:
        """
        Extract the author from the article page.
        Gets the text from span.author a
        """
        author = response.css("span.author a::text").get()
        if author:
            return author.strip()
        return None

    def get_published_date(self, response) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for time.published element
        """
        date_element = response.css('time.published::text').get()
        if date_element:
            date_str = date_element.strip()
            try:
                # Parse date in format '2025-06-16'
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = parsed_date.strftime("%a, %d %b %Y 12:00:01 +0000")
                return formatted_date
            except ValueError as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")
                return date_str
        return None

    def load_more_articles(self, response) -> None:
        """
        Load more articles if needed.
        No pagination needed for Synced Review as specified.
        """
        # No pagination needed for Synced Review
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        Returns None as no pagination is needed.
        """
        return None 