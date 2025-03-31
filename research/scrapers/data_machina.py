import scrapy
from urllib.parse import urljoin

class DataMachinaPlaywrightSpider(scrapy.Spider):
    name = "datamachina_playwright"
    allowed_domains = ["datamachina.com"]
    start_urls = ["https://datamachina.com/2024/01/28/data-machina-238/"]

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "PLAYWRIGHT_CONTEXTS": {
            "default": {
                "ignore_https_errors": True
            }
        },
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 2,
    }

    def start_requests(self):
        yield scrapy.Request(
            url=self.start_urls[0],
            callback=self.parse_issue,
            meta={"playwright": True}
        )

    def parse_issue(self, response):
        self.logger.info(f"Parsing issue page: {response.url}")

        # Extract and yield all links inside div.entry-content
        links = response.css("div.entry-content a::attr(href)").getall()
        for link in set(links):  # Remove duplicates
            yield {
                "origin_url": response.url,
                "link_url": link 
            }

        # Follow the "next" button if it exists
        next_page = response.css('a[rel="next"]::attr(href)').get()
        if next_page:
            next_url = urljoin(response.url, next_page)
            self.logger.info(f"Following next issue: {next_url}")
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_issue,
                meta={"playwright": True}
            )
        else:
            self.logger.info("No more issues found.")
