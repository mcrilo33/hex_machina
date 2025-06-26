"""
Submodule for all scraper-related logic.
Includes base classes and specialized scrapers (e.g., RSS, HTML).
"""

from .base_article import BaseArticleScraper
from .rss_article import RSSArticleScraper, StealthRSSArticleScraper
from .html_article import HTMLArticleScraper
from .parser import extract_domain, extract_markdown_from_html, clean_markdown

__all__ = [
    "BaseArticleScraper",
    "RSSArticleScraper",
    "StealthRSSArticleScraper",
    "HTMLArticleScraper",
    "extract_domain",
    "extract_markdown_from_html",
    "clean_markdown"
]
