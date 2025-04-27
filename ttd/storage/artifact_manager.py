import json
import uuid
from pathlib import Path
from typing import Any
from datetime import datetime


class ArtifactManager:
    def __init__(self, base_path: str, max_inline_bytes: int = 10000):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.max_inline_bytes = max_inline_bytes

    def _should_offload(self, value: Any) -> bool:
        if isinstance(value, (dict, list, str)):
            size = len(json.dumps(value)) if not isinstance(value, str) else len(value)
            return size > self.max_inline_bytes
        return False

    def _generate_artifact_path(self, table_name: str, doc_id: str,
                                field_name: str, timestamp: str) -> Path:
        dt = datetime.fromisoformat(timestamp)
        artifact_dir = self.base_path / table_name / f"{dt.year:04}" / \
            f"{dt.month:02}" / f"{table_name[:-1]}_{doc_id}"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir / f"{field_name}.txt"

    def save_large_fields(self, record: dict, table_name: str, timestamp: str) -> dict:
        updated = dict(record)
        doc_id = str(record.get("doc_id") or uuid.uuid4().hex)

        for key, value in record.items():
            if self._should_offload(value):
                path = self._generate_artifact_path(table_name, doc_id, key, timestamp)
                with open(path, "w", encoding="utf-8") as f:
                    if isinstance(value, str):
                        f.write(value)
                    else:
                        json.dump(value, f, ensure_ascii=False, indent=2)

                updated.pop(key)
                updated[f"{key}_artifact"] = {
                    "path": str(path),
                    "format": "text",
                    "encoding": "utf-8"
                }

        return updated

    def lazy_load_fields(self, record: dict) -> dict:
        class LazyRecord(dict):
            def __getitem__(self, item):
                # New format: field_artifact = { path, ... }
                artifact_key = f"{item}_artifact"
                if artifact_key in self:
                    info = self[artifact_key]
                    path = info.get("path")
                    if path and Path(path).exists():
                        with open(path, encoding=info.get("encoding", "utf-8")) as f:
                            value = f.read() if info.get("format") == "text" \
                                else json.load(f)
                        self[item] = value
                        return value

                # Legacy fallback: field_path
                path_key = f"{item}_path"
                if path_key in self:
                    full_path = self[path_key]
                    if Path(full_path).exists():
                        with open(full_path, encoding="utf-8") as f:
                            value = f.read()
                        self[item] = value
                        del self[path_key]
                        return value

                return super().__getitem__(item)

        return LazyRecord(record)
