import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from ttd.storage.ttd_storage import TTDStorage


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.fixture
def storage(temp_dir):
    """Create a TTDStorage instance for testing."""
    db_path = Path(temp_dir) / "test.json"
    storage = TTDStorage(str(db_path))
    yield storage


def test_init(temp_dir):
    """Test initialization of TTDStorage."""
    db_path = Path(temp_dir) / "test.json"
    storage = TTDStorage(str(db_path))

    assert storage.db_path == str(db_path)
    assert Path(storage.artifacts.base_path) == Path(temp_dir) / "artifacts"


@patch('ttd.storage.ttd_storage.datetime')
def test_save_single_object(mock_datetime, storage):
    """Test saving a single object."""
    mock_datetime.utcnow.return_value = datetime(2023, 1, 1)
    mock_timestamp = "2023-01-01T00:00:00"

    with patch.object(storage.artifacts, 'save_large_fields') as mock_save_large:
        mock_save_large.return_value = {"name": "test", "processed": True}

        with patch.object(storage, 'insert') as mock_insert:
            mock_insert.return_value = [1]

            result = storage.save("articles", {"name": "test"})

            mock_save_large.assert_called_once_with(
                {"name": "test", "table_name": "articles",
                 "created_at": mock_timestamp},
                table_name="articles",
                timestamp=mock_timestamp
            )

            mock_insert.assert_called_once_with(
                "articles", [{"name": "test", "processed": True}]
            )
            assert result == ["1"]


@patch('ttd.storage.ttd_storage.datetime')
def test_save_multiple_objects(mock_datetime, storage):
    """Test saving multiple objects."""
    mock_datetime.utcnow.return_value = datetime(2023, 1, 1)

    with patch.object(storage.artifacts, 'save_large_fields') as mock_save_large:
        mock_save_large.side_effect = lambda obj, **kwargs: {**obj, "processed": True}

        with patch.object(storage, 'insert') as mock_insert:
            mock_insert.return_value = [1, 2]

            result = storage.save("articles", [{"name": "test1"}, {"name": "test2"}])

            assert mock_save_large.call_count == 2
            assert mock_insert.call_count == 1
            assert result == ["1", "2"]


@patch('ttd.storage.ttd_storage.datetime')
def test_save_model(mock_datetime, storage):
    """Test saving a model object with special handling."""
    mock_datetime.utcnow.return_value = datetime(2023, 1, 1)
    mock_timestamp = "2023-01-01T00:00:00"

    with patch.object(storage.artifacts, 'save_large_fields') as mock_save_large:
        mock_save_large.return_value = {"name": "model1", "processed": True}

        with patch.object(storage, 'insert') as mock_insert:
            mock_insert.return_value = [1]

            result = storage.save("models", {"name": "model1"})

            model_obj = {
                "name": "model1", 
                "table_name": "models", 
                "created_at": mock_timestamp,
                "last_updated": mock_timestamp
            }

            mock_save_large.assert_called_once_with(
                model_obj,
                table_name="models",
                timestamp=mock_timestamp
            )

            assert result == ["1"]


@patch('ttd.storage.ttd_storage.datetime')
def test_update_single_object(mock_datetime, storage):
    """Test updating a single object."""
    mock_datetime.utcnow.return_value = datetime(2023, 1, 1)
    mock_timestamp = "2023-01-01T00:00:00"

    with patch.object(storage.artifacts, 'save_large_fields') as mock_save_large:
        mock_save_large.return_value = \
            {"doc_id": "1", "name": "updated", "processed": True}

        with patch.object(storage, 'update_single') as mock_update:
            mock_update.return_value = 1

            result = storage.update("articles", {"doc_id": "1", "name": "updated"})

            expected_obj = {
                "doc_id": "1", 
                "name": "updated", 
                "last_updated": mock_timestamp
            }

            mock_save_large.assert_called_once_with(
                expected_obj,
                table_name="articles",
                timestamp=mock_timestamp
            )

            mock_update.assert_called_once()
            assert result == ["1"]


@patch('ttd.storage.ttd_storage.datetime')
def test_update_multiple_objects(mock_datetime, storage):
    """Test updating multiple objects."""
    mock_datetime.utcnow.return_value = datetime(2023, 1, 1)

    with patch.object(storage.artifacts, 'save_large_fields') as mock_save_large:
        mock_save_large.side_effect = lambda obj, **kwargs: {**obj, "processed": True}

        with patch.object(storage, 'update_single') as mock_update:
            mock_update.side_effect = [1, 2]

            result = storage.update("articles", [
                {"doc_id": "1", "name": "updated1"},
                {"doc_id": "2", "name": "updated2"}
            ])

            assert mock_save_large.call_count == 2
            assert mock_update.call_count == 2
            assert result == ["1", "2"]


def test_get_all(storage):
    """Test retrieving all records from a table."""
    mock_record1 = MagicMock()
    mock_record1.doc_id = 1
    mock_record1.__getitem__.side_effect = \
        lambda key: "value1" if key == "name" else None

    mock_record2 = MagicMock()
    mock_record2.doc_id = 2
    mock_record2.__getitem__.side_effect = \
        lambda key: "value2" if key == "name" else None

    with patch('ttd.storage.base_storage.TinyDBStorageService.get_table') \
            as mock_get_table:
        mock_table = MagicMock()
        mock_table.__iter__.return_value = [mock_record1, mock_record2]
        mock_get_table.return_value = mock_table

        result = storage.get_all("articles")

        mock_get_table.assert_called_once_with("articles")
        assert len(result) == 2
        assert result[0]["doc_id"] == "1"
        assert result[1]["doc_id"] == "2"


def test_search(storage):
    """Test searching for records in a table."""
    mock_record = MagicMock()
    mock_record.doc_id = 1
    mock_record.__getitem__.side_effect = lambda key: "test" if key == "name" else None

    with patch('ttd.storage.base_storage.TinyDBStorageService.get_table') \
            as mock_get_table:
        mock_table = MagicMock()
        mock_table.search.return_value = [mock_record]
        mock_get_table.return_value = mock_table

        query = MagicMock()  # Could be a Query object from TinyDB
        result = storage.search("articles", query)

        mock_get_table.assert_called_once_with("articles")
        mock_table.search.assert_called_once_with(query)
        assert len(result) == 1
        assert result[0]["doc_id"] == "1"


def test_lazy_load(storage):
    """Test lazy loading of fields."""
    with patch.object(storage.artifacts, 'lazy_load_fields') as mock_lazy_load:
        mock_lazy_load.side_effect = lambda obj: {**obj, "lazy_loaded": True}

        result = storage.lazy_load([{"name": "test1"}, {"name": "test2"}])

        assert mock_lazy_load.call_count == 2
        assert all(item["lazy_loaded"] for item in result)


def test_save_or_update_new(storage):
    """Test save_or_update for new objects."""
    with patch.object(storage, 'save') as mock_save:
        mock_save.return_value = ["new_id"]

        result = storage.save_or_update("articles", {"name": "new"})

        mock_save.assert_called_once_with("articles", {"name": "new"})
        assert result == ["new_id"]


def test_save_or_update_existing(storage):
    """Test save_or_update for existing objects."""
    with patch.object(storage, 'update') as mock_update:
        mock_update.return_value = ["1"]

        result = storage.save_or_update("articles", {"doc_id": "1", "name": "updated"})

        mock_update.assert_called_once_with(
            "articles", {"doc_id": "1", "name": "updated"}
        )
        assert result == ["1"]


def test_save_or_update_mixed(storage):
    """Test save_or_update with a mix of new and existing objects."""
    with patch.object(storage, 'save') as mock_save, \
         patch.object(storage, 'update') as mock_update:

        mock_save.return_value = ["new_id"]
        mock_update.return_value = ["1"]

        result = storage.save_or_update("articles", [
            {"name": "new"},
            {"doc_id": "1", "name": "updated"}
        ])

        mock_save.assert_called_once_with("articles", {"name": "new"})
        mock_update.assert_called_once_with(
            "articles", {"doc_id": "1", "name": "updated"}
        )
        assert result == ["new_id", "1"]
