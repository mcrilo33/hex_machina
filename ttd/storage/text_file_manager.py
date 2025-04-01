import os
from urllib.parse import quote, unquote
from datetime import datetime

class TextFileManager:
    def __init__(self, base_dir: str):
        """
        Handles storing and reading raw HTML and extracted text for articles.
        
        Args:
            base_dir (str): Base directory for storage (usually from db_path)
        """
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(base_dir), "raw"))

    def _build_paths(self, url: str, timestamp: str):
        dt = datetime.fromisoformat(timestamp)
        safe_url = quote(url, safe="")

        year = str(dt.year)
        month = f"{dt.month:02d}"
        base_path = os.path.join(self.base_dir, year, month)
        os.makedirs(base_path, exist_ok=True)

        html_filename = f"{safe_url}_raw.html"
        text_filename = f"{safe_url}_extracted.txt"

        html_path = os.path.join(base_path, html_filename)
        text_path = os.path.join(base_path, text_filename)

        return html_path, text_path

    def store_article_files(self, article: dict) -> dict:
        assert "html_content" in article
        assert "text_content" in article
        assert "url" in article

        article["created_at"] = datetime.utcnow().isoformat()

        html_path, text_path = self._build_paths(
            article["url"], article["created_at"])

        # Write HTML
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(article["html_content"])
        except OSError as e:
            logger.error(f"Failed writing HTML to {html_path}: {e}")
            return None
        # Write extracted text
        try:
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(article["text_content"])
        except OSError as e:
            logger.error(f"Failed writing HTML to {html_path}: {e}")
            return None

        article["html_content_path"] = html_path
        article["text_content_path"] = text_path
        del article["html_content"]
        del article["text_content"]

        return article

    def read_html(self, article: dict) -> str:
        assert "html_content_path" in article
        full_path = os.path.abspath(article["html_content_path"])

        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def read_text(self, article: dict) -> str:
        assert "text_content_path" in article
        full_path = os.path.abspath(article["text_content_path"])

        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
