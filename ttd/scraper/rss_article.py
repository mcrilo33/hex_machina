import feedparser
import scrapy
from typing import List
from datetime import datetime
from scrapy.exceptions import CloseSpider
from .base_article import BaseArticleScraper
from .utils import extract_domain, extract_markdown_from_html


class RSSArticleScraper(BaseArticleScraper):
    """
    Scraper that parses RSS feeds, then follows article links for full scraping.
    The normalized RSS entry is passed via meta for enrichment.
    """

    name = "rss_article_scraper"

    parse_count = 0
    
    def start_requests(self):
        for feed_url in self.start_urls:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                normalized = self.parse_article(entry)

                if self.should_skip_entry(normalized):
                    break # stop if entry is too old

                article_url = normalized.get("url")
                if article_url:
                    yield scrapy.Request(
                        url=article_url,
                        callback=self.parse,
                        meta={
                            "rss_data": normalized,
                            "playwright": True
                        }
                    )

    def parse_article(self, entry: dict) -> dict:
        """
        Normalize RSS entry into a structured article dict.
        """
        return {
            "title": entry.get("title"),
            "author": entry.get("author", entry.get("dc_creator", "")),
            "published_date": entry.get("published", entry.get("updated", "")),
            "url_domain": extract_domain(entry.get("link")),
            "url": entry.get("link"),
            "summary": entry.get("summary", entry.get("description", "")),
            "tags": [tag["term"] for tag in entry.get("tags", [])] if "tags" in entry else [],
        }

    def parse(self, response):
        """
        Called for each full article page.
        You can enrich the original RSS data with full HTML content here.
        """
        self.parse_count += 1
        if self.parse_count > 5:
            raise CloseSpider("Reached 5 calls to parse; stopping spider.")

        rss_data = response.meta.get("rss_data", {})
        rss_data["html_content"] = response.text  # optionally store raw HTML or parse more
        rss_data["text_content"] = extract_markdown_from_html(rss_data["html_content"])

        self.store([rss_data])