"""
Submodule for all scraper-related logic.
Includes base classes and specialized scrapers (e.g., RSS, HTML).
"""

from .base_article import BaseArticleScraper
from .rss_article import RSSArticleScraper
from .utils import extract_domain, extract_markdown_from_html

__all__ = [
    "BaseArticleScraper",
    "RSSArticleScraper",
]