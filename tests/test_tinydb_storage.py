import pytest
from tempfile import NamedTemporaryFile
from ttd.storage.base import TinyDBStorageService


@pytest.fixture
def tinydb_storage():
    with NamedTemporaryFile(suffix=".json") as temp_db:
        yield TinyDBStorageService(temp_db.name)


def test_insert_and_get_all(tinydb_storage):
    tinydb_storage.insert("articles", {"id": 1, "title": "Test Article"})
    all_articles = tinydb_storage.get_all("articles")
    assert len(all_articles) == 1
    assert all_articles[0]["title"] == "Test Article"


def test_insert_multiple(tinydb_storage):
    data = [
        {"id": 2, "title": "Article A"},
        {"id": 3, "title": "Article B"},
    ]
    tinydb_storage.insert("articles", data)
    assert tinydb_storage.count_records("articles") == 2


def test_update_record(tinydb_storage):
    tinydb_storage.insert("models", {"id": 1, "name": "Model A"})
    tinydb_storage.update("models", {"name": "Updated Model"}, "id", 1)
    models = tinydb_storage.get_all("models")
    assert models[0]["name"] == "Updated Model"


def test_delete_record(tinydb_storage):
    tinydb_storage.insert("tags", {"id": 1, "name": "AI"})
    tinydb_storage.delete("tags", "id", 1)
    assert tinydb_storage.count_records("tags") == 0


def test_count_records(tinydb_storage):
    tinydb_storage.insert("concepts", {"id": 10, "name": "Machine Learning"})
    assert tinydb_storage.count_records("concepts") == 1