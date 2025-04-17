import time
import logging
import csv
import os
from datetime import datetime
from typing import Any, List, Dict, DefaultDict, Callable, Union
from collections import defaultdict
from ttd.utils import safe_pretty_print


class Pipe:
    def __init__(self, name: str, query: Callable[Any, List[dict]], storage_service: Any, debug: bool = False):
        self.name = name
        self.query_func = query
        self.storage = storage_service
        self.debug = debug
        self.logger = logging.getLogger(f"Pipe.{self.name}")

    def run(self, **kwargs):
        raise NotImplementedError("Pipe is an abstract base class. Use PredictPipe or TransformPipe.")


class PredictPipe(Pipe):
    def __init__(self, name: str, query: Callable[Any, List[dict]], model: Dict, storage_service: Any, debug: bool = False, post_process: Callable[Any, List[dict]] = None):
        super().__init__(name, query, storage_service, debug)
        self.model = model
        self.usage_summary: DefaultDict[str, float] = defaultdict(float)
        self.total_predictions: int = 0
        self.post_process = post_process

        if debug:
            openai_logger = logging.getLogger("openai")
            openai_logger.setLevel(logging.WARNING)

    def validate_model(self):
        assert "model_instance" in self.model, "Missing 'model_instance' in model"
        assert "input_format" in self.model, "Missing 'input_format' in model"
        assert "output_format" in self.model, "Missing 'ouput_format' in model"
        instance = self.model["model_instance"]
        assert hasattr(instance, "predict"), f"Model '{instance}' must implement .predict()"
        return instance

    def get_inputs_from_item(self, item: Any, input_format: str):
        fields = input_format.split(",")
        inputs = []

        input_data = {}
        for field in fields:
            obj = item
            try:
                nested_fields = field.split("__")

                for nested_field in nested_fields[:-1]:
                    obj = obj[nested_field]

                final_field = nested_fields[-1]
                if final_field in obj:
                    input_data[field] = obj[final_field]
            except:
                error_msg = f"\nITEM:\n{safe_pretty_print(item)}\n" + \
                    f"INPUT_FORMAT: '{input_format}'\n" + \
                    f"Invalid input field: '{field}' for obj:\n{safe_pretty_print(obj)}"
                raise ValueError(error_msg)
        inputs.append(input_data)

        return inputs[0] if len(inputs) == 1 else inputs

    def run(self, save: bool = False, pipeline_name: str = None):
        items = self.query_func(self.storage)
        instance = self.validate_model()
        predictions = []

        self.usage_summary.clear()
        self.total_predictions = 0

        total_time = 0.0
        self.logger.info("==============================")
        self.logger.info(f"Running model: {instance.__class__.__name__} on {len(items)} item(s)")

        if self.debug:
            self.logger.debug(f"Model Configuration:\n{safe_pretty_print(self.model)}")

        for idx, item in enumerate(items):
            inputs = self.get_inputs_from_item(item, self.model["input_format"])
            if self.debug:
                self.logger.debug(f"[{idx+1}/{len(items)}]\nInputs: \n{safe_pretty_print(inputs)}\n")
            start_time = time.time()
            output = instance.predict(inputs)
            elapsed_time = time.time() - start_time
            total_time += elapsed_time
            self.logger.info(f"[{idx+1}/{len(items)}] Prediction done in {elapsed_time:.2f}s")

            if self.post_process:
                output["output"] = self.post_process(output["output"])
            instance.validate_output(output)
            metadata = output.get("metadata", {})
            for key, value in metadata.items():
                if isinstance(value, (int, float)):
                    self.usage_summary[key] += value
                    if self.debug:
                        self.logger.info(f"[{idx+1}/{len(items)}] {key}: {value}")
            input_refs = {}
            for key, value in item.items():
                if isinstance(value, dict) and "table_name" in value:
                    input_refs[key] = {
                        "table_name": value["table_name"],
                        "doc_id": value.doc_id
                    }

            if instance.expect_one_output():
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
            else:  # Multiple outputs
                raw_output = output["output"]
                del output["output"]
                for value in raw_output:
                    prediction = {
                        "model_id": self.model.doc_id,
                        "task_type": value.get("task_type"),
                        "created_at": datetime.utcnow().isoformat(),
                        "execution_time": int(elapsed_time),
                        "input_refs": input_refs,
                        "pipe_name": self.name,
                        "pipeline_name": pipeline_name,
                        "value": value.get("value")
                    }
                    for key, value in output.items():
                        prediction[key] = value
                    predictions.append(prediction)

            if self.debug:
                self.logger.debug(f"[{idx+1}/{len(items)}] Prediction:\n{safe_pretty_print(prediction)}\n")
                self.logger.debug(f"DEBUG MODE !!!  Stop Pipe {self.name}")
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


class TransformPipe(Pipe):
    def __init__(self, name: str, query: Callable[[Any], List[dict]], transform: Callable[[List[dict], Any], Any], storage_service: Any, debug: bool = False):
        super().__init__(name, query, storage_service, debug)
        self.transform = transform

    def run(self, save: bool = False, pipeline_name: str = None, **kwargs):
        items = self.query_func(self.storage)
        transformations = []
        
        self.logger.info("==============================")
        self.logger.info(f"Running transform pipe '{self.name}' on {len(items)} item(s)")

        if self.debug:
            self.logger.debug(f"Transform function: {self.transform.__name__ if hasattr(self.transform, '__name__') else str(self.transform)}")

        transformed_items = map(lambda x: self.transform(x, self.storage), items)

        for idx, item in enumerate(transformed_items):
            input_refs = {
                "table_name": items[idx]["table_name"],
                "doc_id": items[idx].doc_id
            }
            output_refs = {}
            if save:
                if hasattr(item, "doc_id"):
                    self.storage.update(item["table_name"], item)
                    doc_id = item.doc_id
                else:
                    doc_id = self.storage.save(item["table_name"], item)
                output_refs = {
                    "table_name": item["table_name"],
                    "doc_id": doc_id
                }
            else:
                output_refs = {
                    "table_name": item["table_name"]
                }
            transformation = {
                "created_at": datetime.utcnow().isoformat(),
                "input_refs": input_refs,
                "output_refs": output_refs,
                "pipe_name": self.name,
                "pipeline_name": pipeline_name,
            }
            transformations.append(transformation)

            if self.debug:
                self.logger.debug(f"[{idx+1}/{len(items)}] transformation:\n{safe_pretty_print(transformation)}\n")
                self.logger.debug(f"DEBUG MODE !!!  Stop Pipe {self.name}")
                break

        if save:
            self.logger.info(f"Saving {len(transformations)} transformations to storage...")
            self.storage.save("transformations", transformations)

        self.logger.info("==============================")
        import ipdb; ipdb.set_trace()
        return transformations


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
            self.logger.info(f"Running pipe {i + 1}/{len(self.pipes)}: {pipe.name}")
            predictions = pipe.run(pipeline_name=self.name, **kwargs)
            if isinstance(pipe, PredictPipe):
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
                if isinstance(pipe, PredictPipe):
                    for key, total in pipe.usage_summary.items():
                        avg = total / pipe.total_predictions if pipe.total_predictions else 0
                        writer.writerow([pipe.name, key, total, round(avg, 2)])

            for key, total in self.usage_summary.items():
                avg = total / self.total_predictions if self.total_predictions else 0
                writer.writerow(["Pipeline", key, total, round(avg, 2)])

        self.logger.info(f"Usage summary exported to {full_path}")
