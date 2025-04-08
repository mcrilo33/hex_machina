import os
from urllib.parse import quote, unquote
from datetime import datetime

class TextFileManager:
    def __init__(self, base_dir: str):
        """
        Handles storing and reading raw HTML and extracted text for articles.
        
        Args:
            base_dir (str): Base directory for storage (usually from db_path)
        """
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(base_dir), "raw"))

    def _build_paths(self, table_name: str, filename: str):
        filename = f"{filename}.txt"
        dt = datetime.utcnow()
        year = str(dt.year)
        month = f"{dt.month:02d}"

        base_path = os.path.join(self.base_dir, table_name, year, month)
        os.makedirs(base_path, exist_ok=True)
        filepath = os.path.join(base_path, filename)
        return filepath

    def save(self, table_name: str, field_name: str, obj: dict) -> dict:
        assert field_name in obj

        filepath = self._build_paths(
            table_name,
            str(article["doc_id"]) + '_' + field_name
        )

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(obj[field_name])
        except OSError as e:
            logger.error(f"Failed writing HTML to {filepath}: {e}")
            return None

        obj[field_name + '_path'] = filepath
        del obj[field_name]

        return obj

    def load(self, field_name: str, obj: dict) -> str:
        full_path = os.path.abspath(obj[field_name])

        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()