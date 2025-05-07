""" Unified storage interface for the full TTD application. """
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

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

    def save(self, table_name: str, data) -> List[str]:
        """
        Save data to the specified table.
        Handles automatic offloading of large fields.
        Returns list of doc_ids.
        """
        if not isinstance(data, list):
            data = [data]

        result = []
        for obj in data:
            obj["table_name"] = table_name
            obj["created_at"] = datetime.utcnow().isoformat()

            # Handle model-specific logic
            if table_name == "models":
                # TODO ADD self.model_manager.save(obj)
                obj["last_updated"] = obj["created_at"]

            # Automatically offload large or structured fields
            obj = self.artifacts.save_large_fields(
                obj,
                table_name=table_name,
                timestamp=obj["created_at"]
            )

            result.append(obj)

        return [str(id) for id in self.insert(table_name, result)]

    def update(self, table_name: str, data: List[Dict[str, Any]]) -> List[str]:
        """
        Update existing records in the specified table.
        Handles automatic offloading of large fields.
        Add doc_id to results.
        Returns list of doc_ids.
        """
        if not isinstance(data, list):
            data = [data]

        ids = []
        for obj in data:
            obj["last_updated"] = datetime.utcnow().isoformat()
            obj = self.artifacts.save_large_fields(
                obj,
                table_name=table_name,
                timestamp=obj["last_updated"]
            )
            ids.append(self.update_single(table_name, obj))

        return [str(id) for id in ids]

    def get_all(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all records from the specified table.
        Add doc_id to results.
        """
        table = super().get_table(table_name)
        return [{**record, "doc_id": str(record.doc_id)} for record in table]

    def search(self, table_name: str, query) -> List[Dict[str, Any]]:
        """
        Search for records in the specified table using a query.
        Add doc_id to results.
        """
        table = super().get_table(table_name)
        results = table.search(query)
        return [{**record, "doc_id": str(record.doc_id)} for record in results]

    def lazy_load(self, data) -> List[Dict[str, Any]]:
        """ Turn data into lazy load objects. """
        if not isinstance(data, list):
            data = [data]

        return [
            self.artifacts.lazy_load_fields(obj)
            for obj in data
        ]

    def save_or_update(self, table_name: str, data) -> List[str]:
        """
        Save or update data in the specified table.
        If data contains a doc_id, update the record.
        Otherwise, save a new record.
        Return a list of doc_ids.
        """
        if not isinstance(data, list):
            data = [data]
        ids = []
        for obj in data:
            if "doc_id" in obj:
                self.update(table_name, obj)
                ids.append(obj["doc_id"])
            else:
                obj_id = self.save(table_name, obj)[0]
                ids.append(obj_id)
        return ids
