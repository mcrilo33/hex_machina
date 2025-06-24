import logging
from typing import List, Optional
from datetime import datetime

from .html_article import HTMLArticleScraper


logger = logging.getLogger(__name__)


class DeepMindGoogleScraper(HTMLArticleScraper):
    """
    Scraper for DeepMind Google blog articles.
    Extracts articles from deepmind.google/discover/blog/
    """

    name = "deepmind_google_scraper"
    
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
            start_urls = ["https://deepmind.google/discover/blog/"]
        
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags within <gdm-filter>
        """
        # Select all article links within the gdm-filter element
        article_links = response.css("gdm-filter a::attr(href)").getall()
        
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
        DeepMind articles contain googleblog.com in the URL
        """
        return "google" in link and "blog" in link

    def get_title(self, response) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from h1.glue-headline
        """
        title = response.css("h1.glue-headline::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, response) -> Optional[str]:
        """
        Extract the author from the article page.
        Gets the text from all div.author-obj a elements
        """
        # Get all author elements and join them
        author_elements = response.css("div.author-obj a::text").getall()
        if author_elements:
            # Join multiple authors with commas
            authors = [author.strip() for author in author_elements if author.strip()]
            return ", ".join(authors)
        return None

    def get_published_date(self, response) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for div.published_date element
        """
        date_element = response.css('div.published_date::text').get()
        if date_element:
            date_str = date_element.strip()
            try:
                # Parse date in format 'JUNE 17, 2025'
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
        No pagination needed for DeepMind as specified.
        """
        # No pagination needed for DeepMind
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        Returns None as no pagination is needed.
        """
        return None 