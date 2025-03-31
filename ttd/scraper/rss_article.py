import feedparser
import scrapy
from typing import List
from .base_article import BaseArticleScraper
from .utils import extract_domain


class RSSArticleScraper(BaseArticleScraper):
    """
    Scraper that parses RSS feeds, then follows article links for full scraping.
    The normalized RSS entry is passed via meta for enrichment.
    """

    name = "rss_article_scraper"

    def start_requests(self):
        for feed_url in self.start_urls:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                entry['domain'] = domain
                normalized = self.parse_article(entry)

                if self.should_skip_entry(normalized):
                    break # stop if entry is too old

                article_url = normalized.get("source_url")
                domain = extract_domain(article_url)
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
            "domain": entry.get("domain"),
            "source_url": entry.get("link"),
            "published_date": entry.get("published", entry.get("updated", "")),
            "summary": entry.get("summary", entry.get("description", "")),
            "author": entry.get("author", entry.get("dc_creator", "")),
            "tags": [tag["term"] for tag in entry.get("tags", [])] if "tags" in entry else [],
        }

    def parse(self, response):
        """
        Called for each full article page.
        You can enrich the original RSS data with full HTML content here.
        """
        rss_data = response.meta.get("rss_data", {})
        import ipdb; ipdb.set_trace()
        rss_data["html"] = response.text  # optionally store raw HTML or parse more

        self.store([rss_data])