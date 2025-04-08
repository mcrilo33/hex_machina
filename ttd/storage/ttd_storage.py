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

    def save(self, table_name: str, objects):
        if not isinstance(objects, list):
            objects = [objects]
        result = []
        for obj in objects:
            obj["created_at"] = datetime.utcnow().isoformat()
            if table_name == "articles":
                obj = self.file_manager.save(
                    "articles",
                    "text_content",
                    obj
                )
                obj = self.file_manager.save(
                    "articles",
                    "html_content",
                    obj
                )
            if table_name == "models":
                self.model_manager.save(model)
                obj['last_updated'] = obj['created_at']
            result.append(obj)
        self.insert(table_name, result)
    
    def load(self, field_name: str, objects):
        if field_name not in [
            "html_content",
            "text_content",
            "model_instance"
        ]:
            return objects
        if not isinstance(objects, list):
            objects = [objects]
        result = []
        for obj in objects:
            if field_name=="html_content" or field_name=="text_content":
                obj[field_name] = self.file_manager.load(field_name + '_path', obj)
            if field_name=="model_instance":
                obj[field_name] = self.model_manager.load_model(obj)
            result.append(obj)
        if len(result)==1:
            return result[0]
        return result

    def update(self, table_name: str, objects):
        if not isinstance(objects, list):
            objects = [objects]
        for obj in objects:
            obj['last_updated'] = datetime.utcnow().isoformat()
            table.update(update_doc, obc)
    