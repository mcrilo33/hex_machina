import shutil
import pytest
import copy
from unittest.mock import MagicMock
from ttd.storage.ttd_storage import TTDStorage


@pytest.fixture
def temp_storage(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("data")
    db_path = tmp_path / "db.json"
    storage = TTDStorage(str(db_path))
    yield storage
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def dummy_article():
    return {
        "url": "http://example.com",
        "html_content": "<html><body>Hello</body></html>",
        "text_content": "Hello"
    }


@pytest.fixture
def dummy_model():
    return {
        "name": "mock_model",
        "config": {
            "openai": {
                "api_key_env_var": "FAKE_API_KEY",
                "base_url": "http://localhost",
                "model": "gpt-3"
            }
        },
        "input_format": "text_content",
        "output_format": "text"
    }


@pytest.fixture
def storage_with_mock_model_and_article(tmp_path_factory, dummy_model, dummy_article):
    tmp_path = tmp_path_factory.mktemp("data")
    storage = TTDStorage(str(tmp_path / "db.json"))

    # Add dummy model with mocked instance
    mock_model_instance = MagicMock()
    mock_model_instance.predict = MagicMock(return_value="mock prediction")
    storage.save_model(dummy_model)

    model = storage.get_model_by_name("mock_model")
    model["model_instance"] = mock_model_instance
    model["doc_id"] = model.doc_id

    # Add dummy article
    storage.save_articles([dummy_article])
    article = storage.get_table("articles").all()[0]
    article.doc_id = article.doc_id

    yield storage, model, article
    shutil.rmtree(tmp_path, ignore_errors=True)


##############################################################################
# Test Article Handling
##############################################################################

class TestArticles:
    def test_save_and_get_article(self, temp_storage, dummy_article):
        temp_storage.save_articles([copy.deepcopy(dummy_article)])
        saved = temp_storage.get_table("articles").all()[0]

        assert "html_content_path" in saved
        assert "text_content_path" in saved
        assert saved["url"] == dummy_article["url"]

        html = temp_storage.from_article_get_html(saved)
        text = temp_storage.from_article_get_text(saved)

        assert html == dummy_article["html_content"]
        assert text == dummy_article["text_content"]


##############################################################################
# Test Model Lifecycle
##############################################################################

class TestModels:
    def test_model_lifecycle(self, temp_storage, dummy_model, dummy_article):
        # Patch loading logic
        temp_storage.model_manager.load_model = MagicMock(
            return_value=MagicMock(predict=lambda x: f"Predicted: {x}")
        )

        temp_storage.save_model(dummy_model)
        model = temp_storage.load_model_by_name("mock_model")
        assert "model_instance" in model

        temp_storage.save_articles([dummy_article])
        stored_article = temp_storage.get_table("articles").all()[0]

        predictions = temp_storage.run_model_on_articles(
            model,
            [stored_article],
            save=False
        )

        assert len(predictions) == 1
        assert predictions[0]["output"] == "Predicted: Hello"


##############################################################################
# Test Predictions
##############################################################################

class TestPredictions:
    def test_run_model_on_articles_and_store_predictions(
        self,
        storage_with_mock_model_and_article
    ):
        storage, model, article = storage_with_mock_model_and_article

        predictions = storage.run_model_on_articles(model, [article], save=True)
        assert len(predictions) == 1

        pred = predictions[0]
        assert pred["output"] == "mock prediction"
        assert pred["article_id"] == article.doc_id
        assert pred["model_id"] == model["doc_id"]
        assert pred["task_type"] == model["output_format"]
        assert isinstance(pred["execution_time"], int)
        assert "created_at" in pred

        # DB check
        stored_preds = storage.get_table("predictions").all()
        assert len(stored_preds) == 1
        assert stored_preds[0]["output"] == "mock prediction"

    def test_run_model_on_articles_without_saving(
        self,
        storage_with_mock_model_and_article
    ):
        storage, model, article = storage_with_mock_model_and_article

        predictions = storage.run_model_on_articles(model, [article], save=False)
        assert len(predictions) == 1
        assert storage.get_table("predictions").all() == []
