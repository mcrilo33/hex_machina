import pytest
from datetime import datetime
from ttd.scraper.base_article import BaseArticleScraper


class DummyScraper(BaseArticleScraper):
    """Minimal concrete subclass of BaseArticleScraper for testing."""
    name = "dummy_scraper"

    def parse(self, response):
        pass

    def parse_article(self, raw_article):
        pass


@pytest.fixture
def dummy_scraper():
    return DummyScraper(
        start_urls=["https://example.com"],
        storage_service=None,
        last_date=datetime(2024, 3, 1)
    )


def test_should_skip_entry_with_older_date(dummy_scraper):
    entry = {"published_date": "2024-02-28"}
    assert dummy_scraper.should_skip_entry(entry) is True


def test_should_skip_entry_with_newer_date(dummy_scraper):
    entry = {"published_date": "2024-03-15"}
    assert dummy_scraper.should_skip_entry(entry) is False


def test_should_skip_entry_with_missing_date(dummy_scraper):
    entry = {}
    assert dummy_scraper.should_skip_entry(entry) is False


def test_should_skip_entry_with_invalid_format(dummy_scraper):
    entry = {"published_date": "March 1st, 2024"}
    assert dummy_scraper.should_skip_entry(entry) is False


def test_should_skip_entry_when_no_last_date():
    scraper = DummyScraper(
        start_urls=[],
        storage_service=None,
        last_date=None
    )
    entry = {"published_date": "2024-01-01"}
    assert scraper.should_skip_entry(entry) is False