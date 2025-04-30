import pytest
from ttd.storage.model_manager import ModelManager


class DummyStorage:
    def __init__(self):
        self.db = {}


@pytest.fixture
def model_manager():
    return ModelManager(DummyStorage())


def test_save_model_metadata(model_manager):
    model = {"name": "test"}
    result = model_manager.save_model(model)
    assert "created_at" in result
    assert "last_updated" in result


def test_update_model_metadata(model_manager):
    model = {"name": "test"}
    updated = model_manager.update_model(model)
    assert "last_updated" in updated


def test_load_model_fails_on_unknown_endpoint(model_manager):
    model = {
        "config": {
            "unknown_provider": {}
        },
        "endpoint": "unknown"
    }
    with pytest.raises(NotImplementedError):
        model_manager.load_model(model)
