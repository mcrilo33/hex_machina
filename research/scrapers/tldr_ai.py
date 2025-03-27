import scrapy
from urllib.parse import urljoin

class TldrPlaywrightSpider(scrapy.Spider):
    name = "tldr_playwright"
    allowed_domains = ["tldr.tech"]
    start_urls = ["https://tldr.tech/ai/archives"]

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
        'DOWNLOAD_DELAY': 1,         # 1 second delay between requests
        'CONCURRENT_REQUESTS': 2,    # Reduce concurrent requests
    }

    def start_requests(self):
        yield scrapy.Request(
            url=self.start_urls[0],
            callback=self.parse,
            meta={"playwright": True}
        )

    def parse(self, response):
        self.logger.info(f"Loaded page: {response.url} (status {response.status})")

        # Exemple : tous les liens dans les hrefs qui commencent par "/ai"
        ai_links = response.css('a[href^="/ai"]::attr(href)').getall()

        for href in ai_links:
            full_url = urljoin(response.url, href)
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_ai_section,
                meta={"playwright": True}
            )

    def parse_ai_section(self, response):
        # Tous les liens dans div.content-center
        content_links = response.css("div.content-center a::attr(href)").getall()
        for link in content_links:
            yield {
                "origin_url": response.url,
                "link_url": link
            }