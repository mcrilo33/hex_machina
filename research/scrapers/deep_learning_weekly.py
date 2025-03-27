import scrapy
from urllib.parse import urljoin
from scrapy_playwright.page import PageMethod

class DeepLearningWeeklyPlaywrightSpider(scrapy.Spider):
    name = "deep_learning_weekly_playwright"
    allowed_domains = ["deeplearningweekly.com"]
    start_urls = ["https://www.deeplearningweekly.com/archive"]

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30_000,
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 2,
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
                        for (let i = 0; i < 20; i++) {
                            window.scrollBy(0, document.body.scrollHeight);
                            await new Promise(r => setTimeout(r, 500));
                        }
                    }"""),
                    PageMethod("wait_for_timeout", 2000),
                ]
            }
        )

    def parse_archive(self, response):
        self.logger.info(f"Loaded archive page: {response.url} (status {response.status})")

        # Get all post links inside div.portable-archive-list
        post_links = response.css("div.portable-archive-list a::attr(href)").getall()
        post_links = set([link for link in post_links if "deep-learning-weekly" in link and "comment" not in link])

        for href in post_links:
            full_url = urljoin(response.url, href)
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
