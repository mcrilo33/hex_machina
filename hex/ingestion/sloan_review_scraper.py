import logging
from typing import List, Optional
from datetime import datetime

from .html_article import HTMLArticleScraper
from .parser import extract_markdown_from_html


logger = logging.getLogger(__name__)


class SloanReviewScraper(HTMLArticleScraper):
    """
    Scraper for Sloan Review articles.
    Extracts articles from sloanreview.mit.edu/topic/data-ai-machine-learning/
    """

    name = "sloan_review_scraper"
    
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
            start_urls = ["https://sloanreview.mit.edu/topic/data-ai-machine-learning/"]
        
        super().__init__(
            start_urls, storage, articles_table, articles_limit, date_threshold,
            *args, **kwargs
        )

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags within div#Data-AI-and_Machine-Learning_Tiled
        """
        # Select all article links within the Data-AI-and_Machine-Learning_Tiled div
        article_links = response.css(
            "div#Data-AI-and-Machine-Learning-Tiled a::attr(href)"
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
        Sloan Review articles contain /article/ in the URL
        """
        return "/article/" in link

    def get_title(self, response) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from h1.article-header
        """
        title = response.css("h1.article-header__title::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, response) -> Optional[str]:
        """
        Extract the author from the article page.
        Gets the text from a[href="#article-authors"]
        """
        author = response.css('a[href="#article-authors"]::text').get()
        if author:
            return author.strip()
        return None

    def get_text_content(self, response) -> Optional[str]:
        """
        Extract the main text content from the article page.
        Gets all text content within the section
        """
        # Get all text content from the section
        article_html = response.css("div.article-content").get()
        if article_html:
            content_elements = extract_markdown_from_html(article_html)
        else:
            content_elements = None
        return content_elements

    def get_published_date(self, response) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for abbr.published element
        """
        date_element = response.css('abbr.published::text').get()
        if date_element:
            date_str = date_element.strip()
            try:
                # Parse date in format 'June 17, 2025'
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
        No pagination needed for Sloan Review as specified.
        """
        # No pagination needed for Sloan Review
        pass

    def get_next_page_url(self, response) -> Optional[str]:
        """
        Extract the next page URL for pagination.
        Returns None as no pagination is needed.
        """
        return None 