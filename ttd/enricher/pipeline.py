import time
from datetime import datetime
from dataclasses import dataclass
from typing import Any, List, Dict

@dataclass
class QueryInput:
    source: str   # e.g., "ARTICLES"
    alias: str    # e.g., "article"
    data: list    # e.g., list of documents

class Pipe:
    def __init__(self, queries: List[QueryInput], model: dict, storage_service: Any):
        self.queries = queries
        self.model = model
        self.storage = storage_service

    def validate_model(self):
        assert "model_instance" in self.model, "Missing 'model_instance' in model"
        assert "input_format" in self.model, "Missing 'input_format' in model"
        instance = self.model["model_instance"]
        assert hasattr(instance, "predict"), f"Model '{instance}' must implement .predict()"
        return instance

    def get_items_from_queries(self):
        if len(self.queries) == 1:
            return self.queries[0].data

        length = len(self.queries[0].data)
        return [
            {query.alias: query.data[i] for query in self.queries}
            for i in range(length)
        ]

    def get_inputs_from_item(self, item: Any, input_format: str):
        fields = input_format.split(",")
        item = item if isinstance(item, list) else [item]
        inputs = []

        for sub_item in item:
            input_data = {}
            for field in fields:
                obj = sub_item
                nested_fields = field.split("__")

                for nested_field in nested_fields[:-1]:
                    obj = obj[nested_field]

                final_field = nested_fields[-1]
                if final_field in obj:
                    input_data[field] = obj[final_field]
                else:
                    raise ValueError(f"Invalid input field: '{field}' not in {obj}")
            inputs.append(input_data)

        return inputs[0] if len(inputs) == 1 else inputs

    def build_input_refs(self, item):
        input_refs = {}

        for query in self.queries:
            value = item[query.alias] if len(self.queries) > 1 else item
            if isinstance(value, dict) and "doc_id" in value:
                input_refs[query.alias] = {
                    "table_name": query.source,
                    "doc_id": value["doc_id"]
                }
            else:
                raise ValueError(f"Invalid input object (no doc_id): {value}")

        return input_refs

    def run(self, save: bool = False):
        instance = self.validate_model()
        items = self.get_items_from_queries()
        predictions = []

        for item in items:
            inputs = self.get_inputs_from_item(item, self.model["input_format"])
            start_time = time.time()
            output = instance.predict(inputs)
            elapsed_time = time.time() - start_time

            prediction = {
                ""
                "model_id": self.model.get("doc_id"),
                "task_type": self.model.get("output_format"),
                "created_at": datetime.utcnow().isoformat(),
                "execution_time": int(elapsed_time),
                "input_refs": self.build_input_refs(item)
            }
            for key,value in output.items():
                prediction[key] = value
            predictions.append(prediction)

        if save:
            self.storage.save("predictions", predictions)

        return predictions

    def build_input_refs(self, item):
        input_refs = {}

        for query in self.queries:
            value = item[query.alias] if len(self.queries) > 1 else item
            if isinstance(value, dict):
                input_refs[query.alias] = {
                    "table_name": query.source,
                    "doc_id": value.doc_id
                }
            else:
                raise ValueError(f"Invalid input object for query: {query.alias}")

        return input_refs
