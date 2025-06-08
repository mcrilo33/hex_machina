import os
import tempfile
from pathlib import Path

import pytest

from ttd.storage.artifact_manager import ArtifactManager


@pytest.fixture
def temp_dir():
    """Fixture to create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def artifact_manager(temp_dir):
    """Fixture to create an ArtifactManager with the temp dir."""
    return ArtifactManager(base_path=temp_dir, max_inline_bytes=50)


def test_should_offload_string(artifact_manager):
    """Test _should_offload for strings."""
    small_text = "short"
    big_text = "x" * 100

    assert not artifact_manager._should_offload(small_text)
    assert artifact_manager._should_offload(big_text)


def test_should_offload_list_dict(artifact_manager):
    """Test _should_offload for lists and dicts."""
    small_list = ["a", "b"]
    big_list = ["x" * 100] * 10

    small_dict = {"key": "val"}
    big_dict = {"k": "x" * 1000}

    assert not artifact_manager._should_offload(small_list)
    assert artifact_manager._should_offload(big_list)
    assert not artifact_manager._should_offload(small_dict)
    assert artifact_manager._should_offload(big_dict)


def test_save_large_fields_and_lazy_load(artifact_manager, temp_dir):
    """Test saving large fields and lazy loading them."""
    table_name = "test_table"
    timestamp = "2025-04-27T18:00:00"
    original_record = {
        "doc_id": "123",
        "small_field": "small value",
        "large_field": "x" * 1000
    }

    saved_record = artifact_manager.save_large_fields(
        original_record, table_name, timestamp
    )

    # Assert that large fields were offloaded
    assert "large_field_artifact" in saved_record
    assert "large_field" not in saved_record
    assert saved_record["small_field"] == "small value"

    # Assert that artifacts exist
    for artifact_key in ["large_field_artifact"]:
        path = saved_record[artifact_key]["path"]
        assert os.path.exists(path)

    # Test lazy loading
    lazy_record = artifact_manager.lazy_load_fields(saved_record)

    # Fields should be accessible transparently
    assert lazy_record["small_field"] == "small value"
    assert lazy_record["large_field"] == "x" * 1000


def test_generate_artifact_path_structure(artifact_manager):
    """Test _generate_artifact_path creates correct structure."""
    table_name = "articles"
    doc_id = "abc123"
    field_name = "summary"
    timestamp = "2025-04-27T15:30:00"

    artifact_path = artifact_manager._generate_artifact_path(
        table_name, doc_id, field_name, timestamp
    )

    # Check parts of path
    assert "articles" in artifact_path.parts
    assert "2025" in artifact_path.parts
    assert "04" in artifact_path.parts
    assert "article_abc123" in artifact_path.parts
    assert artifact_path.name == "summary.txt"


def test_save_without_doc_id(artifact_manager):
    """Test save_large_fields generates UUID when doc_id missing."""
    table_name = "no_id_table"
    timestamp = "2025-04-27T18:00:00"
    record = {
        "large_content": "X" * 1000
    }

    updated = artifact_manager.save_large_fields(record, table_name, timestamp)

    assert "large_content_artifact" in updated
    assert "large_content" not in updated
    assert "doc_id" not in record  # Original record untouched

    # Path should exist
    path = updated["large_content_artifact"]["path"]
    assert Path(path).exists()


def test_lazy_load_handles_missing_files(artifact_manager):
    """Test lazy loading missing files safely."""
    record = {
        "field_artifact": {
            "path": "/nonexistent/path.txt",
            "format": "text",
            "encoding": "utf-8"
        }
    }
    lazy_record = artifact_manager.lazy_load_fields(record)

    # Accessing non-existing artifact should raise KeyError
    with pytest.raises(KeyError):
        _ = lazy_record["field"]
