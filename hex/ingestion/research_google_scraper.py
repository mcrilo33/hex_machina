import logging
from typing import List, Optional
from datetime import datetime

from .html_article import HTMLArticleScraper


logger = logging.getLogger(__name__)


class ResearchGoogleScraper(HTMLArticleScraper):
    """
    Scraper for Google Research blog articles.
    Extracts articles from research.google/blog/
    """

    name = "research_google_scraper"
    
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
            start_urls = ["https://research.google/blog/"]
        
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags within div.list-wrapper
        """
        # Select all article links within the list-wrapper div
        article_links = response.css("div.list-wrapper a::attr(href)").getall()
        
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
        Google Research articles contain /blog/ in the URL
        """
        return "/blog/" in link

    def get_title(self, response) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from h1.headline-1
        """
        title = response.css("h1.headline-1::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, response) -> Optional[str]:
        """
        Extract the author from the article page.
        Gets the text from the second <p> in div.basic-hero--blog-detail__description
        """
        # Get the second <p> element within the description div
        author_elements = response.css(
            "div.basic-hero--blog-detail__description p::text"
        ).getall()
        if len(author_elements) >= 2:
            author = author_elements[1].strip()
            return author
        return None

    def get_published_date(self, response) -> Optional[str]:
        """
        Extract the published date from the article page.
        Gets the text from the first <p> in div.basic-hero--blog-detail__description
        """
        # Get the first <p> element within the description div
        date_elements = response.css(
            "div.basic-hero--blog-detail__description p::text"
        ).getall()
        if date_elements:
            date_str = date_elements[0].strip()
            try:
                # Parse date in format 'June 23, 2025'
                parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                formatted_date = parsed_date.strftime("%a, %d %b %Y 12:00:01 +0000")
                return formatted_date
            except ValueError as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")
                return date_str
        return None

    def load_more_articles(self, response) -> None:
        """
        Load more articles if needed.
        No pagination needed for Google Research as specified.
        """
        # No pagination needed for Google Research
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        Returns None as no pagination is needed.
        """
        return None 