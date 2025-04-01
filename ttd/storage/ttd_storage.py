from typing import List
from tinydb import Query
from .base_storage import TinyDBStorageService


class TTDStorage(TinyDBStorageService):
    """
    Unified storage interface for the full TTD application.
    Manages all entity tables (articles, models, tags, predictions, etc.)
    using TinyDB as backend.
    """

    def __init__(self, db_path):
        super().__init__(db_path)
        from ttd.storage.model_manager import ModelManager
        from ttd.storage.text_file_manager import TextFileManager
        self.model_manager = ModelManager(self)
        self.file_manager = TextFileManager(db_path)

    # --- Articles ---
    def save_articles(self, articles: List[dict]):
        for article in articles:
            article = self.file_manager.store_article_files(article)
        self.insert("articles", articles)

    def get_article_by_id(self, article_id):
        return self.get_table("articles").get(doc_id=article_id)

    def from_article_get_html(self, article):
        return self.file_manager.read_html(article)

    def from_article_get_text(self, article):
        return self.file_manager.read_text(article)

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
