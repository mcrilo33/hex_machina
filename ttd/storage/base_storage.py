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

    def get_table(self, table_name):
        return self.db.table(table_name)

    def get_by_name(self, table_name, name: str):
        table = self.get_table(table_name)
        q = Query()
        result = table.get(q.name == name)
        return result

    def insert(self, table_name, data):
        table = self.get_table(table_name)
        if isinstance(data, list):
            table.insert_multiple(data)
        else:
            table.insert(data)

    def update(self, table_name, data, query_field, query_value):
        table = self.get_table(table_name)
        q = Query()
        table.update(data, q[query_field] == query_value)

    def delete_field_from_table(self, table_name: str, field_to_delete: str):
        table = self.get_table(table_name)

        def remove_field(doc):
            if field_to_delete in doc:
                del doc[field_to_delete]

        table.update(remove_field)

    def delete(self, table_name, query_field, query_value):
        table = self.get_table(table_name)
        q = Query()
        table.remove(q[query_field] == query_value)

    def get_all(self, table_name):
        return self.get_table(table_name).all()

    def count_records(self, table_name):
        return len(self.get_table(table_name))
