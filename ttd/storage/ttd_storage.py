import time
from datetime import datetime
from typing import List
from pathlib import Path
from .base_storage import TinyDBStorageService
from .artifact_manager import ArtifactManager


class TTDStorage(TinyDBStorageService):
    """
    Unified storage interface for the full TTD application.
    Manages all entity tables (articles, models, tags, predictions, etc.)
    using TinyDB as backend.
    Automatically handles large object persistence using ArtifactManager.
    """

    def __init__(self, db_path):
        super().__init__(db_path)

        artifact_dir = Path(db_path).parent / "artifacts"
        self.artifacts = ArtifactManager(base_path=str(artifact_dir))

    def _serialize_datetimes(self, obj: dict) -> dict:
        def serialize(value):
            if isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, dict):
                return {k: serialize(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [serialize(v) for v in value]
            return value

        return serialize(obj)

    def save(self, table_name: str, objects):
        if not isinstance(objects, list):
            objects = [objects]

        result = []
        for obj in objects:
            obj["table_name"] = table_name
            obj["created_at"] = datetime.utcnow().isoformat()

            # Handle model-specific logic
            if table_name == "models":
                # TODO self.model_manager.save(obj)
                obj["last_updated"] = obj["created_at"]

            # Automatically offload large or structured fields
            obj = self.artifacts.save_large_fields(
                obj,
                table_name=table_name,
                timestamp=obj["created_at"]
            )

            result.append(obj)

        return [str(id) for id in self.insert(table_name, result)]

    def update(self, table_name: str, objects):
        if not isinstance(objects, list):
            objects = [objects]

        for obj in objects:
            obj["last_updated"] = datetime.utcnow().isoformat()
            obj = self.artifacts.save_large_fields(
                obj,
                table_name=table_name,
                timestamp=obj["last_updated"]
            )
            self.update_single(table_name, obj)

    def get_all(self, table_name: str):
        table = super().get_table(table_name)
        return [
            self.artifacts.lazy_load_fields({**record, "doc_id": str(record.doc_id)})
            for record in table
        ]

    def get_by_field(self, table_name: str, field_name: str, field_value: str):
        table = super().get_table(table_name)
        from tinydb import Query
        q = Query()
        for record in table.search(q[field_name] == field_value):
            return self.artifacts.lazy_load_fields({**record, "doc_id": str(record.doc_id)})
        return None
    
    def search(self, table_name: str, query):
        table = super().get_table(table_name)
        results = table.search(query)
        return [
            self.artifacts.lazy_load_fields({**record, "doc_id": str(record.doc_id)})
            for record in results
        ]
