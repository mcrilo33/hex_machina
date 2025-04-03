import shutil
import pytest
from ttd.storage.text_file_manager import TextFileManager


@pytest.fixture
def file_manager(tmp_path):
    base_dir = tmp_path / "database.json"
    manager = TextFileManager(str(base_dir))
    yield manager
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_store_and_read_article(file_manager):
    article = {
        "url": "http://test.com",
        "html_content": "<html><p>Test</p></html>",
        "text_content": "Test text"
    }

    updated = file_manager.store_article_files(article)
    assert "html_content_path" in updated
    assert "text_content_path" in updated

    html = file_manager.read_html(updated)
    text = file_manager.read_text(updated)

    assert html == "<html><p>Test</p></html>"
    assert text == "Test text"
