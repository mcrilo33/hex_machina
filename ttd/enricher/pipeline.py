import time
import logging
import csv
import os
from datetime import datetime
from typing import Any, List, Dict, DefaultDict, Callable
from collections import defaultdict
from ttd.utils import safe_pretty_print


class Pipe:
    def __init__(self, name: str, query: Callable[[Any], List[dict]], model: Dict, storage_service: Any, debug: bool = False):
        self.name = name
        self.query_func = query
        self.model = model
        self.storage = storage_service
        self.debug = debug
        self.logger = logging.getLogger(f"Pipe.{self.name}")
        self.usage_summary: DefaultDict[str, float] = defaultdict(float)
        self.total_predictions: int = 0
        self.items: List[dict] = []

        if debug:
            openai_logger = logging.getLogger("openai")
            openai_logger.setLevel(logging.WARNING)

    def validate_model(self):
        assert "model_instance" in self.model, "Missing 'model_instance' in model"
        assert "input_format" in self.model, "Missing 'input_format' in model"
        instance = self.model["model_instance"]
        assert hasattr(instance, "predict"), f"Model '{instance}' must implement .predict()"
        return instance

    def get_inputs_from_item(self, item: Any, input_format: str):
        fields = input_format.split(",")
        inputs = []

        input_data = {}
        for field in fields:
            obj = item
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

    def run(self, save: bool = False, pipeline_name: str = None):
        self.items = self.query_func(self.storage)
        instance = self.validate_model()
        predictions = []

        self.usage_summary.clear()
        self.total_predictions = 0

        total_time = 0.0
        self.logger.info("==============================")
        self.logger.info(f"Running model: {instance.__class__.__name__} on {len(self.items)} item(s)")

        if self.debug:
            self.logger.debug(f"Model Configuration:\n{safe_pretty_print(self.model)}")

        for idx, item in enumerate(self.items):
            inputs = self.get_inputs_from_item(item, self.model["input_format"])
            if self.debug:
                self.logger.debug(f"[{idx+1}/{len(self.items)}]\nInputs: \n{safe_pretty_print(inputs)}\n")
            start_time = time.time()
            output = instance.predict(inputs)
            elapsed_time = time.time() - start_time
            total_time += elapsed_time
            self.logger.info(f"[{idx+1}/{len(self.items)}] Prediction done in {elapsed_time:.2f}s")

            metadata = output.get("metadata", {})
            for key, value in metadata.items():
                if isinstance(value, (int, float)):
                    self.usage_summary[key] += value
                    if self.debug:
                        self.logger.info(f"[{idx+1}/{len(self.items)}] {key}: {value}")
            input_refs = {}
            for key, value in item.items():
                import ipdb; ipdb.set_trace()
                if "table_name" in value:
                    input_refs[key] = {
                        "table_name": value["table_name"],
                        "doc_id": value.doc_id
                    } 
                else:
                    raise ValueError(f"{key} outside of the storage.")

            prediction = {
                "model_id": self.model.doc_id,
                "task_type": self.model.get("output_format"),
                "created_at": datetime.utcnow().isoformat(),
                "execution_time": int(elapsed_time),
                "input_refs": input_refs,
                "pipe_name": self.name,
                "pipeline_name": pipeline_name
            }
            for key, value in output.items():
                prediction[key] = value
            predictions.append(prediction)

            if self.debug:
                self.logger.debug(f"[{idx+1}/{len(self.items)}] Prediction:\n{safe_pretty_print(prediction)}\n")
                self.logger.debug(f"DEBUG MODE !!!  Stop Pipeline {self.name}")
                break

        self.total_predictions = len(predictions)

        if predictions:
            avg_time = total_time / len(predictions)
            self.logger.info(f"Pipe '{self.name}' average execution time: {avg_time:.2f}s per prediction")
            for key, total in self.usage_summary.items():
                avg_value = total / len(predictions)
                self.logger.info(f"Pipe '{self.name}' total {key}: {total}, avg: {avg_value:.2f} per prediction")

        if save:
            self.logger.info(f"Saving {len(predictions)} predictions to storage...")
            self.storage.save("predictions", predictions)

        self.logger.info("==============================")
        return predictions


class Pipeline:
    def __init__(self, name: str, pipes: List[Pipe], debug: bool = False):
        self.name = name
        self.pipes = pipes
        self.debug = debug
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(f"Pipeline.{self.name}")
        self.usage_summary: DefaultDict[str, float] = defaultdict(float)
        self.total_predictions: int = 0

    def run(self, **kwargs):
        self.logger.info("==============================")
        self.logger.info(f"Starting pipeline '{self.name}' with {len(self.pipes)} pipe(s)...")
        all_predictions = {}
        self.usage_summary.clear()
        self.total_predictions = 0
        total_time = time.time()

        for i, pipe in enumerate(self.pipes):
            self.logger.info("------------------------------")
            self.logger.info(f"Running pipe {i + 1}/{len(self.pipes)}: {pipe.name} ({pipe.model.get('model_instance').__class__.__name__})")
            predictions = pipe.run(**kwargs, pipeline_name=self.name)
            for key, val in pipe.usage_summary.items():
                self.usage_summary[key] += val
            self.total_predictions += pipe.total_predictions
            all_predictions[pipe.name] = predictions

        elapsed_pipeline_time = time.time() - total_time
        self.logger.info("==============================")
        self.logger.info(f"Pipeline '{self.name}' completed in {elapsed_pipeline_time:.2f}s.")
        if self.total_predictions:
            for key, total in self.usage_summary.items():
                avg_value = total / self.total_predictions
                self.logger.info(f"Pipeline total {key}: {total}, avg: {avg_value:.2f} per prediction")
        self.logger.info("==============================")

        return all_predictions

    def export_usage_summary(self, base_dir: str):
        if not self.usage_summary:
            self.logger.warning("No usage summary to export.")
            return

        os.makedirs(base_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_usage_summary_{timestamp}.csv"
        full_path = os.path.join(base_dir, filename)

        with open(full_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Scope", "Metric", "Total", "Average per Prediction"])

            for pipe in self.pipes:
                for key, total in pipe.usage_summary.items():
                    avg = total / pipe.total_predictions if pipe.total_predictions else 0
                    writer.writerow([pipe.name, key, total, round(avg, 2)])

            for key, total in self.usage_summary.items():
                avg = total / self.total_predictions if self.total_predictions else 0
                writer.writerow(["Pipeline", key, total, round(avg, 2)])

        self.logger.info(f"Usage summary exported to {full_path}")
