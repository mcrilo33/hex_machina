from urllib.parse import quote
from ttd.storage.base import TinyDBStorageService
from typing import List


class TTDStorage(TinyDBStorageService):
    """
    Unified storage interface for the full TTD application.
    Manages all entity tables (articles, models, tags, predictions, etc.)
    using TinyDB as backend.
    """

    def _store_article_files(article):
        assert "html_content" in article
        assert "text_content" in article
        assert "timestamp" in article
        assert "url" in article
        
        try:
            timestamp = datetime.fromisoformat(article["timestamp"])
        except ValueError:
            raise ValueError(f"Invalid timestamp: {article['timestamp']}")
        safe_url = quote(article["url"], safe="")
        html_content = article["html_content"]
        text_content = article["text_content"]


        year_str = str(timestamp.year)
        month_str = f"{timestamp.month:02d}"  # zero-padded month

        base_path = os.path.join("data", "raw", year_str, month_str)
        os.makedirs(base_path, exist_ok=True)

        html_filename = f"{safe_url}_raw.html"
        text_filename = f"{safe_url}_extracted.txt"

        html_path = os.path.join(base_path, html_filename)
        text_path = os.path.join(base_path, text_filename)

        # Write HTML
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except OSError as e:
            logger.error(f"Failed writing HTML to {html_path}: {e}")
            return None

        # Write extracted text
        try:
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text_content)
        except OSError as e:
            logger.error(f"Failed writing HTML to {html_path}: {e}")
            return None
        
        # Update article
        article['html_content_path'] = html_path
        article['text_content_path'] = text_path
        del article["html_content"]
        del article["text_content"]

        return article

    # --- Articles ---
    def save_articles(self, articles: List[dict]):
        for article in articles:
            article = self._store_article_files(article)
        self.insert("articles", articles)

    def get_article_by_id(self, article_id):
        return self.get_table("articles").get(doc_id=article_id)

    # --- Models ---
    def save_model(self, model: dict):
        self.insert("models", model)

    # --- Tags ---
    def save_tag(self, tag: dict):
        self.insert("tags", tag)

    def get_tags_for_article(self, article_id):
        table = self.get_table("article_tags")
        return table.search(Query()["article_id"] == article_id)

    # --- Predictions ---
    def save_prediction(self, prediction: dict):
        self.insert("predictions", prediction)

    def get_predictions_for_article(self, article_id):
        return self.get_table("predictions").search(Query()["article_id"] == article_id)

    # --- Concepts ---