import time
from datetime import datetime
from typing import List
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
            start_time = time.time()
            article = self.file_manager.store_article_files(article)
            elapsed_time = time.time() - start_time
            article["execution_time"] = int(elapsed_time)
        self.insert("articles", articles)

    def get_article_by_id(self, article_id):
        return self.get_table("articles").get(doc_id=article_id)

    def get_article_by_url(self, url):
        article = self.get_by_url('articles', url)
        return article

    def from_article_get_html(self, article):
        return self.file_manager.read_html(article)

    def from_article_get_text(self, article):
        return self.file_manager.read_text(article)

    # --- Models ---
    def save_model(self, model: dict):
        assert 'name' in model
        self.model_manager.save_model(model)
        self.insert('models', model)

    def update_model(self, model: dict):
        self.model_manager.update_model(model)
        for key, value in model.items():
            self.update('models', model, key, value)

    def get_model_by_name(self, name: str):
        model = self.get_by_name('models', name)
        return model

    def load_model_by_name(self, name: str):
        model = self.get_model_by_name(name)
        model["model_instance"] = self.model_manager.load_model(model)
        return model

    def get_input_from_article(self, article: dict, input: str):
        fields = input.split(",")
        input = []
        for field in fields:
            if field == "html_content":
                input.append(self.from_article_get_html(article))
            elif field == "text_content":
                input.append(self.from_article_get_text(article))
            elif field in article:
                input.append(article[field])
            else:
                raise ValueError(f"Invalid input field: {field}")

        if len(input) == 1:
            return input[0]

        return input

    def run_model_on_articles(self, model, articles, save=True):
        assert "model_instance" in model
        instance = model["model_instance"]
        assert hasattr(instance, "predict"), \
            f"Model '{instance}' must implement .predict()"

        predictions = []
        for article in articles:
            input = self.get_input_from_article(article, model["input_format"])
            start_time = time.time()
            output = instance.predict(input)
            elapsed_time = time.time() - start_time

            predictions.append({
                "article_id": article.doc_id,
                "model_id": model.doc_id,
                "task_type": model["output_format"],
                "output": output,
                "created_at": datetime.utcnow().isoformat(),
                "execution_time": int(elapsed_time)
            })

        if save:
            self.save_predictions(predictions)

        return predictions

    # --- Tags ---
    def save_tag(self, tag: dict):
        self.insert("tags", tag)

    # --- Predictions ---
    def save_predictions(self, predictions: List[dict]):
        for prediction in predictions:
            self.insert("predictions", prediction)

    # --- Concepts ---
