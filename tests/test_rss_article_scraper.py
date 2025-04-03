import pytest
from scrapy.http import HtmlResponse, Request
from ttd.scraper.rss_article import RSSArticleScraper, parse_article
from unittest.mock import patch


def test_start_requests_yields_requests_with_rss_data(fake_rss_entry):
    fake_feed = type("FakeFeed", (), {"entries": [fake_rss_entry]})
    mock_normalized = {
        "url": "https://example.com/ai-news",
        "execution_time": 123
    }

    with patch("ttd.scraper.rss_article.feedparser.parse", return_value=fake_feed), \
         patch.object(RSSArticleScraper, "parse_article", return_value=mock_normalized):
        scraper = RSSArticleScraper(
            start_urls=["https://fake-feed.com"],
            storage_service=None
        )
        requests = list(scraper.start_requests())

        assert len(requests) == 1
        req = requests[0]
        assert isinstance(req, Request)
        assert req.url == "https://example.com/ai-news"
        assert "rss_data" in req.meta
        rss_data = req.meta["rss_data"]
        assert "execution_time" in rss_data
        assert isinstance(rss_data["execution_time"], int)
        assert rss_data["execution_time"] >= 0  # at least 0 milliseconds


@pytest.fixture
def fake_rss_entry():
    return {
        "title": "AI Breakthrough",
        "domain": "fake-feed",
        "link": "https://example.com/ai-news",
        "published": "2024-03-28",
        "summary": "Big news in AI this week...",
        "author": "Jane Doe",
        "tags": [{"term": "AI"}, {"term": "ML"}],
    }


def test_parse_article(fake_rss_entry):
    parsed = parse_article(fake_rss_entry)

    assert parsed["title"] == "AI Breakthrough"
    assert parsed["url"] == "https://example.com/ai-news"
    assert parsed["published_date"] == "2024-03-28"
    assert parsed["summary"] == "Big news in AI this week..."
    assert parsed["author"] == "Jane Doe"
    assert "AI" in parsed["tags"]


class MockStorage:
    def __init__(self):
        self.saved = []

    def save_articles(self, articles):
        self.saved.extend(articles)


def test_parse_adds_html_to_rss_data(fake_rss_entry):
    scraper = RSSArticleScraper(start_urls=[], storage_service=MockStorage())

    html = "<html><body><h1>AI Breakthrough</h1></body></html>"
    request = Request(url=fake_rss_entry["link"], meta={"rss_data": fake_rss_entry})
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=html,
        encoding="utf-8"
    )

    scraper.parse(response)

    # Check if MockStorage captured the article
    stored = scraper.storage_service.saved
    assert len(stored) == 1
    assert stored[0]["html_content"] == html
