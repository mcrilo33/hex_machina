import scrapy
from urllib.parse import urljoin
from scrapy_playwright.page import PageMethod

class LastWeekInAIPlaywrightSpider(scrapy.Spider):
    name = "last_week_in_ai_playwright"
    allowed_domains = ["lastweekin.ai"]
    start_urls = ["https://lastweekin.ai/archive"]

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 2,
        "PLAYWRIGHT_CONTEXTS": {
            "default": {
                "ignore_https_errors": True
            }
        }
    }

    def start_requests(self):
        yield scrapy.Request(
            url=self.start_urls[0],
            callback=self.parse_archive,
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "networkidle"),
                    PageMethod("evaluate", """async () => {
                        for (let i = 0; i < 300; i++) {
                            window.scrollBy(0, document.body.scrollHeight);
                            await new Promise(r => setTimeout(r, 300));
                        }
                    }"""),
                    PageMethod("wait_for_timeout", 3000),
                ]
            }
        )

    def parse_archive(self, response):
        self.logger.info(f"Loaded archive: {response.url}")

        # Extract links from div.portable-archive-list and filter
        post_links = response.css("div.portable-archive-list a::attr(href)").getall()

        for href in set(post_links):
            full_url = urljoin(response.url, href)
            if "last-week-in-ai" in full_url:
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_post,
                    meta={"playwright": True}
                )

    def parse_post(self, response):
        self.logger.info(f"Parsing post: {response.url}")

        # Get all links inside div.body
        content_links = response.css("div.body a::attr(href)").getall()

        for link in content_links:
            yield {
                "origin_url": response.url,
                "link_url": link
            }
