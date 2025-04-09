from abc import ABC, abstractmethod
from tinydb import TinyDB, Query


class StorageService(ABC):
    """
    Base storage interface with generic table operations.
    """

    @abstractmethod
    def get_table(self, table_name):
        pass

    @abstractmethod
    def insert(self, table_name, data):
        pass

    @abstractmethod
    def update(self, table_name, data, query_field, query_value):
        pass

    @abstractmethod
    def delete(self, table_name, query_field, query_value):
        pass

    @abstractmethod
    def get_all(self, table_name):
        pass

    @abstractmethod
    def count_records(self, table_name):
        pass


class TinyDBStorageService(StorageService):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = TinyDB(db_path)

    def get_table(self, table_name: str):
        return self.db.table(table_name)
    
    def get_by_field(self, table_name: str, field_name: str, field_value: str):
        table = self.get_table(table_name)
        q = Query()
        result = table.get(q[field_name] == field_value)
        return result

    def insert(self, table_name, data):
        table = self.get_table(table_name)
        if isinstance(data, list):
            table.insert_multiple(data)
        else:
            table.insert(data)

    def update_single(self, table_name, data):

        doc_id = data.doc_id
        table = self.get_table(table_name)
        existing_doc = table.get(doc_id=doc_id)

        if not existing_doc:
            raise ValueError(f"No document found in '{table_name}' with doc_id {doc_id}")

        # Compute keys to remove
        keys_to_remove = set(existing_doc.keys()) - set(data.keys())
        # Update fields and remove obsolete ones
        def update_doc(doc):
            # Remove fields
            for key in keys_to_remove:
                doc.pop(key, None)
            # Set new values
            for key, value in data.items():
                if key != "doc_id":  # Skip doc_id
                    doc[key] = value

        table.update(update_doc, doc_ids=[doc_id])

    def delete(self, table_name, query_field, query_value):
        table = self.get_table(table_name)
        q = Query()
        table.remove(q[query_field] == query_value)

    def get_all(self, table_name):
        return self.get_table(table_name).all()

    def count_records(self, table_name):
        return len(self.get_table(table_name))
