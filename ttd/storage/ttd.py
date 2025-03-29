from ttd.storage.base import TinyDBStorageService
from typing import List


class TTDStorage(TinyDBStorageService):
    """
    Unified storage interface for the full TTD application.
    Manages all entity tables (articles, models, tags, predictions, etc.)
    using TinyDB as backend.
    """

    # --- Articles ---
    def save_articles(self, articles: List[dict]):
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