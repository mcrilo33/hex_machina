import time
import feedparser
import scrapy
from scrapy.exceptions import CloseSpider
from scrapy_playwright.page import PageMethod
from .base_article import BaseArticleScraper
from .utils import extract_domain, extract_markdown_from_html, clean_markdown

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync


def parse_article(entry: dict) -> dict:
    """
    Normalize RSS entry into a structured article dict.
    """
    return {
        "title": entry.get("title"),
        "author": entry.get("author", entry.get("dc_creator", "")),
        "published_date": entry.get("published", entry.get("updated", "")),
        "url_domain": extract_domain(entry.get("link")),
        "url": entry.get("link", entry.get("url")),
        "summary": entry.get("summary", entry.get("description", "")),
        "tags":
            [tag["term"] for tag in entry.get("tags", [])]
            if "tags" in entry else [],
    }


def extract_article(self, entry: dict) -> dict:
    assert "html_content" in entry
    start_time = time.time()
    entry["text_content"] = extract_markdown_from_html(entry["html_content"])
    entry["html_content_length"] = len(entry["html_content"])
    entry["text_content_length"] = len(entry["text_content"])
    entry["summary"] = clean_markdown(entry["summary"])
    entry["summary_length"] = len(entry["summary"])
    entry["summary_text_ratio"] = \
        entry["summary_length"]/entry["text_content_length"]
    elapsed_time = time.time() - start_time
    entry["execution_time"] = int(elapsed_time)
    if entry["summary_text_ratio"] > 1.1:
        ratio = entry['summary_text_ratio']
        self.logger.warning(f"Weird Summary/Text ratio {ratio}")
    return entry


class StealthRSSArticleScraper(BaseArticleScraper):
    """
    Scraper that parses RSS feeds, then uses undetected Playwright for scraping.
    The normalized RSS entry is passed via meta for enrichment.
    """

    name = "rss_article_scraper"
    parse_count = 0

    def start_requests(self):
        from ttd.config import load_config
        config = load_config()
        DEBUG = config["debug"]
        for feed_url in self.start_urls:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                normalized = self.parse_article(entry)

                if self.should_skip_entry(normalized):
                    break  # stop if entry is too old

                article_url = normalized.get("url")
                if article_url:
                    html = self.fetch_with_undetected_playwright(article_url)
                    if html:
                        self.parse_count += 1
                        if DEBUG and self.parse_count > 2:
                            raise CloseSpider(
                                "DEBUG MODE : " +
                                "Reached 2 calls to parse; stopping spider."
                            )
                        normalized["html_content"] = html
                        normalized = extract_article(self, normalized)
                        self.store([normalized])
        return iter([])

    def fetch_with_undetected_playwright(self, url: str) -> str:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                    timezone_id="Europe/Paris"
                )
                page = context.new_page()
                stealth_sync(page)
                page.goto(url, timeout=60000)
                page.wait_for_timeout(3000)  # wait for JS to render
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            self.logger.warning(f"Undetected Playwright failed for {url}: {e}")
            return None

    def parse(self, response):
        pass  # unused now, handled in start_requests

    def parse_article(self, response):
        return parse_article(response)


class RSSArticleScraper(BaseArticleScraper):
    """
    Scraper that parses RSS feeds, then follows article links for full scraping.
    The normalized RSS entry is passed via meta for enrichment.
    """

    name = "rss_article_scraper"
    parse_count = 0
    custom_settings = {
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "DOWNLOAD_TIMEOUT": 30,
        "RETRY_TIMES": 5,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408],
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": ("text/html,application/xhtml+xml," +
                       "application/xml;q=0.9,image/webp,*/*;q=0.8"),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com",
            "Connection": "close"
        },
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 100000,
    }

    def start_requests(self):
        for feed_url in self.start_urls:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                normalized = self.parse_article(entry)

                if self.should_skip_entry(normalized):
                    break  # stop if entry is too old

                article_url = normalized.get("url")
                if article_url:
                    yield scrapy.Request(
                        url=article_url,
                        callback=self.parse,
                        errback=self.handle_error,
                        meta={
                            "rss_data": normalized,
                            "handle_httpstatus_all": True,
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_page_methods": [
                                PageMethod(
                                    "evaluate", "() => Object.defineProperty( \
                                        navigator, 'webdriver', {get: () => undefined})"
                                ),
                                PageMethod("wait_for_timeout", 2000),
                            ]
                        }
                    )

    def handle_error(self, failure):
        self.logger.warning(
            f"Request failed: {failure.request.url} | Reason: {failure.value}"
        )

    def parse(self, response):
        """
        Called for each full article page.
        You can enrich the original RSS data with full HTML content here.
        """
        from ttd.config import load_config

        if response.status != 200:
            self.logger.warning(f"Non-200 status {response.status} for {response.url}")
            return
        config = load_config()
        DEBUG = config["debug"]
        self.parse_count += 1
        if DEBUG and self.parse_count > 2:
            raise CloseSpider("DEBUG MODE : Reached 2 call to parse; stopping spider.")

        rss_data = response.meta.get("rss_data", {})
        rss_data["html_content"] = response.text
        rss_data = extract_article(self, rss_data)
        self.store([rss_data])

    def parse_article(self, response):
        return parse_article(response)
