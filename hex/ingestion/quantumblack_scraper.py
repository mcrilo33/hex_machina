import logging
from typing import List, Optional
from datetime import datetime

from .html_article import HTMLArticleScraper


logger = logging.getLogger(__name__)


class QuantumBlackScraper(HTMLArticleScraper):
    """
    Scraper for QuantumBlack articles on Medium.
    Extracts articles from medium.com/quantumblack
    """

    name = "quantumblack_scraper"
    
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
            start_urls = ["https://medium.com/quantumblack"]
        
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags within div.js-collectionStream
        """
        # Select all article links within the collection stream
        article_links = (
            response.css("div.js-collectionStream a::attr(href)").getall()
        )
        
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
        Medium articles typically have URLs like /p/ or /@username/
        """
        # Medium article patterns
        medium_patterns = [
            "collection_home"
        ]
        
        link_lower = link.lower()
        return any(pattern in link_lower for pattern in medium_patterns)

    def get_title(self, response) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the first h1 within the section
        """
        title = response.css("section h1::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, response) -> Optional[str]:
        """
        Extract the author from the article page.
        For QuantumBlack, we'll return empty string as specified
        """
        return ""

    def get_published_date(self, response) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for span with data-testId="storyPublishDate"
        """
        date_element = response.css('span[data-testId="storyPublishDate"]::text').get()
        if date_element:
            # Convert 'Jun 12, 2025' to 'Mon, 16 Jun 2025 12:00:01 +0000'
            date_str = date_element.strip()
            try:
                parsed_date = datetime.strptime(date_str, "%b %d, %Y")
                formatted_date = parsed_date.strftime("%a, %d %b %Y 12:00:01 +0000")
                return formatted_date
            except ValueError as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")
                return date_str
        return None

    def load_more_articles(self, response) -> None:
        """
        Load more articles if needed.
        Medium typically loads content dynamically, but we don't need
        to handle pagination as specified.
        """
        # No pagination needed for QuantumBlack
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        Returns None as no pagination is needed.
        """
        return None 