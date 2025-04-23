import time
import logging
from graphviz import Digraph
from datetime import datetime
from typing import List, Callable, Dict, Any, Optional, Union, Type
from collections import defaultdict
from pydantic import BaseModel, Field
from ttd.utils.print import safe_pretty_print
from ttd.utils.git import get_git_metadata
from ttd.models.base_spec import ModelSpec


class StepRunRecord(BaseModel):
    table_name: str
    step_run_id: str
    step_name: str
    pipeline_name: Optional[str]
    pipeline_run_id: Optional[str]
    step_type: str
    model_id: Optional[str]
    started_at: datetime
    completed_at: datetime
    duration: float
    num_inputs: int
    num_outputs: int
    metrics: Optional[dict] = {}
    success: bool = True
    error: Optional[str] = None
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    git_repo: Optional[str] = None


class PredictionRecord(BaseModel):
    table_name: str
    doc_id: Optional[str] = None
    step_run_id: str
    model_id: str
    step_name: str
    pipeline_name: Optional[str]
    pipeline_run_id: Optional[str]
    created_at: str
    duration: int
    input_refs: Dict[str, Dict[str, Union[str, int]]]
    output: Union[str, dict]
    metadata: Optional[Dict[str, Union[int, float, str]]] = {}
    prediction_type: str


class PipelineRunRecord(BaseModel):
    table_name: str
    pipeline_name: str
    pipeline_run_id: str
    started_at: datetime
    completed_at: datetime
    duration: float
    num_steps: int
    success: bool = True
    error: Optional[str] = None
    params: Optional[Dict[str, Any]] = {}
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    git_repo: Optional[str] = None


class BaseStep:
    def __init__(
        self,
        step_name: str,
        input_loader: Callable[[Any], List[dict]],
        storage: Any,
        InputSchema: Optional[Type[BaseModel]] = None,
        OutputSchema: Optional[Type[BaseModel]] = None,
        depends_on: Optional[List[str]] = None,
        preprocessing: Optional[Callable[[dict], Any]] = None,
        postprocessing: Optional[Callable[[Any], Any]] = None
    ):
        self.step_name = step_name
        self.input_loader = input_loader
        self.storage = storage
        self.InputSchema = InputSchema
        self.OutputSchema = OutputSchema
        self.depends_on = depends_on or []
        self.input_dict: List[dict] = []
        self.context: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"Step::{self.step_name}")
        self.preprocessing = preprocessing or (lambda x: x)
        self.postprocessing = postprocessing or (lambda x: x)

    def update_context(self, context):
        self.context.update(context)
        
    def load_input(self):
        if callable(self.input_loader):
            try:
                # Prefer input_loader with context support
                self.input_dict = self.input_loader(self.storage, self.context)
            except TypeError:
                # Fallback to legacy signature
                self.input_dict = self.input_loader(self.storage)
        return self.input_dict

    def apply(self, item: dict, operation_fn: Callable[[dict], Any]) -> Any:
        data = self.preprocessing(item)
        result = operation_fn(data)
        return self.postprocessing(result)

    def execute(self, context: Optional[Dict] = None, **kwargs):
        self.context.update(context or {})
        raise NotImplementedError("Use specialized step classes like PredictStep or TransformStep.")


class PredictStep(BaseStep):
    def __init__(
        self,
        step_name: str,
        input_loader: Callable[[Any], List[dict]],
        model_spec: ModelSpec,
        storage: Any,
        InputSchema: Optional[Type[BaseModel]] = None,
        OutputSchema: Optional[Type[BaseModel]] = None,
        preprocessing: Optional[Callable[[dict], Any]] = None,
        postprocessing: Optional[Callable[[Any], Any]] = None
    ):
        super().__init__(
            step_name,
            input_loader,
            storage,
            InputSchema,
            OutputSchema,
            preprocessing=preprocessing,
            postprocessing=postprocessing
        )
        self.model_spec = model_spec
        self.metrics = defaultdict(float)
        self.total_predictions = 0

    def validate_model(self):
        instance = self.model_spec._loaded_model
        assert instance is not None
        assert hasattr(instance, "predict"), "Model must implement a .predict() method"
        return instance

    def extract_features(self, record: dict) -> dict:
        fields = self.model_spec.input_schema.split(",")
        features = {}
        for field in fields:
            obj = record
            for key in field.split("__")[:-1]:
                obj = obj[key]
            final_key = field.split("__")[-1]
            features[field] = obj[final_key]
        return features

    def execute(self, persist: bool = False, step_run_id: Optional[str] = None, pipeline_name: Optional[str] = None, pipeline_run_id: Optional[str] = None, context: Optional[Dict] = None):
        self.context.update(context or {})
        self.input_dict = self.load_input()
        predictor = self.validate_model()
        output_dict = []
        self.total_predictions = 0
        error = None

        start = datetime.utcnow()
        total_time = 0.0

        self.logger.info(f"Executing prediction step on {len(self.input_dict)} record(s)")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(safe_pretty_print(self.model_spec.dict()))

        try:
            for idx, record in enumerate(self.input_dict):
                features = self.extract_features(record)
                if self.InputSchema:
                    features = self.InputSchema(**features).dict()

                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"[{idx+1}] Features: \n{safe_pretty_print(features)}")

                t0 = time.time()
                result = self.apply(features, predictor.predict)
                duration = time.time() - t0
                total_time += duration

                if self.OutputSchema:
                    result_output = result.get("output") or result
                    result["output"] = self.OutputSchema(**result_output).dict() if isinstance(result_output, dict) else result_output

                output = PredictionRecord(
                    table_name="predictions",
                    step_run_id=step_run_id or f"{self.step_name}-{int(time.time())}",
                    model_id=self.model_spec.model_id,
                    step_name=self.step_name,
                    pipeline_name=pipeline_name,
                    pipeline_run_id=pipeline_run_id,
                    created_at=datetime.utcnow().isoformat(),
                    duration=int(duration),
                    input_refs={
                        key: {"table_name": value["table_name"], "doc_id": value["doc_id"]}
                        for key, value in record.items()
                        if isinstance(value, dict) and "table_name" in value
                    },
                    output=result.get("output") or result,
                    metadata=result.get("metadata", {}),
                    prediction_type=self.model_spec.output_schema
                )
                if "metadata" in result:
                    for k, v in result["metadata"].items():
                        self.metrics[k] += v

                output_dict.append(output)

                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"[{idx+1}] Output:\n{safe_pretty_print(output.model_dump())}")
                    if idx == 1:
                        break

        except Exception as e:
            error = str(e)
            self.logger.exception("Step failed")
        finally:
            self.total_predictions = len(output_dict)
            if output_dict:
                if persist:
                    doc_ids = self.storage.save(
                        "predictions",
                        [pred.model_dump(mode="json") for pred in output_dict]
                    )
                    for i, doc_id in enumerate(doc_ids):
                        output_dict[i].doc_id = doc_id
                else:
                    for i, pred in enumerate(output_dict):
                        output_dict[i].doc_id = f"fake_doc_id_{i}"

            git_info = get_git_metadata()
            log = StepRunRecord(
                table_name="step_runs",
                step_run_id=step_run_id or f"{self.step_name}-{int(time.time())}",
                step_name=self.step_name,
                pipeline_name=pipeline_name,
                pipeline_run_id=pipeline_run_id,
                step_type="predict",
                model_id=self.model_spec.model_id,
                started_at=start,
                completed_at=datetime.utcnow(),
                duration=(datetime.utcnow() - start).total_seconds(),
                num_inputs=len(self.input_dict),
                num_outputs=len(output_dict),
                metrics=dict(self.metrics),
                success=error is None,
                error=error,
                **git_info
            )
            if persist:
                self.storage.save("step_runs", log.model_dump(mode="json"))

        return [pred.model_dump(mode="json") for pred in output_dict]


class TransformStep(BaseStep):
    def __init__(
        self,
        step_name: str,
        input_loader: Callable[[Any], List[dict]],
        operation: Callable[[List[dict], Any], Optional[List[dict]]],
        storage: Any,
        InputSchema: Optional[Type[BaseModel]] = None,
        OutputSchema: Optional[Type[BaseModel]] = None,
        preprocessing: Optional[Callable[[dict], Any]] = None,
        postprocessing: Optional[Callable[[Any], Any]] = None
    ):
        super().__init__(
            step_name,
            input_loader,
            storage,
            InputSchema,
            OutputSchema,
            preprocessing=preprocessing,
            postprocessing=postprocessing
        )
        self.operation = operation

    def execute(self, persist: bool = False, step_run_id: Optional[str] = None, pipeline_name: Optional[str] = None, pipeline_run_id: Optional[str] = None, context: Optional[Dict] = None):
        self.context.update(context or {})
        start = datetime.utcnow()
        self.input_dict = self.load_input()
        output_dict = []
        error = None
        try:
            if self.InputSchema:
                self.input_dict = [self.InputSchema(**item).dict() for item in self.input_dict]
            output_dict = []
            for input in self.input_dict:
                output_dict.append(
                    self.apply(input, lambda x: self.operation(x, self.storage))
                )
        except Exception as e:
            error = str(e)
            self.logger.exception("Transform step failed")
        finally:
            self.total_predictions = len(output_dict)
            git_info = get_git_metadata()
            log = StepRunRecord(
                table_name="step_runs",
                step_run_id=step_run_id or f"{self.step_name}-{int(time.time())}",
                step_name=self.step_name,
                pipeline_name=pipeline_name,
                pipeline_run_id=pipeline_run_id,
                step_type="transform",
                model_id=None,
                started_at=start,
                completed_at=datetime.utcnow(),
                duration=(datetime.utcnow() - start).total_seconds(),
                num_inputs=len(self.input_dict),
                num_outputs=len(output_dict),
                metrics={},
                success=error is None,
                error=error,
                **git_info
            )
            if persist:
                self.storage.save("step_runs", log.model_dump(mode="json"))
            if output_dict:
                for i, output in enumerate(output_dict):
                    if output:
                        for k, v in output.items():
                            if persist and "doc_id" in v:
                                self.storage.update(v["table_name"], v)
                            elif persist:
                                doc_id = self.storage.save(v["table_name"], v)[0]
                                output_dict[i][k]["doc_id"] = doc_id
                            else:
                                output_dict[i][k]["doc_id"] = f"fake_doc_id_{k}_{i}"

        self.logger.info(f"Transform step '{self.step_name}' completed.")
        return output_dict


class Pipeline:
    def __init__(self, pipeline_name: str, steps: List[BaseStep], storage: Any):
        self.pipeline_name = pipeline_name
        self.steps = steps
        self.storage = storage
        self.logger = logging.getLogger(f"Pipeline::{self.pipeline_name}")
        self.context: Dict[str, Dict[str, Any]] = {}


    def trace_dataflow(self) -> Dict[str, Any]:
        """
        Builds a dataflow graph of actual inputs/outputs (by table_name and doc_id)
        as loaded by the step input loaders. No model execution happens.
        Simulates outputs for PredictStep and TransformStep using the first input.
        """
        context = {}
        object_registry = {}  # {step_name: {"inputs": {key: (table, id)}, "outputs": {key: (table, id)}}}
        object_to_step = defaultdict(set)  # {("table_name", "doc_id"): set(step_names)}

        for step in self.steps:
            step_name = step.step_name
            object_registry[step_name] = {"inputs": {}, "outputs": {}}
            context[step_name] = {"inputs": {}, "outputs": {}}

            # Load first input for dependency simulation
            step.update_context(context)
            inputs = step.load_input()
            first_input = inputs[0] if inputs else None

            if first_input:
                for key, obj in first_input.items():
                    doc_id = obj.get("doc_id")
                    table = obj.get("table_name")
                    if table and doc_id:
                        object_registry[step_name]["inputs"][key] = (table, doc_id)
                context[step_name]["inputs"] = [first_input]

            # PredictStep simulation
            if isinstance(step, PredictStep) and first_input:
                prediction_id = f"{step_name}-simulated-{int(time.time())}"
                simulated = PredictionRecord(
                    step_run_id=prediction_id,
                    model_id=step.model_spec.model_id,
                    step_name=step_name,
                    pipeline_name=self.pipeline_name,
                    pipeline_run_id="trace",
                    created_at=datetime.utcnow().isoformat(),
                    duration=0,
                    input_refs={
                        key: {"table_name": val["table_name"], "doc_id": val["doc_id"]}
                        for key, val in first_input.items()
                        if isinstance(val, dict) and "table_name" in val and "doc_id" in val
                    },
                    output="simulated",
                    metadata={},
                    prediction_type=step.model_spec.output_schema
                )
                key = ("predictions", prediction_id)
                object_registry[step_name]["outputs"]["output"] = key
                object_to_step[key].add(step_name)
                sim_dict = simulated.model_dump(mode="json")
                sim_dict["table_name"] = "predictions"
                sim_dict["doc_id"] = prediction_id
                context[step_name]["outputs"] = [sim_dict]

            # TransformStep simulation
            if isinstance(step, TransformStep) and first_input:
                simulated_output = step.apply(
                    first_input,
                    lambda x: step.operation(x, step.storage)
                )
                if simulated_output:
                    for key, obj in simulated_output.items():
                        table = obj.get("table_name")
                        doc_id = obj.get("doc_id") or f"{step_name}-simulated-{int(time.time())}"
                        obj["doc_id"] = doc_id
                        object_registry[step_name]["outputs"][key] = (table, doc_id)
                        object_to_step[(table, doc_id)].add(step_name)
                    context[step_name]["outputs"] = [simulated_output]

        # Link step dependencies
        links = []
        consumed_outputs = set()
        all_inputs = set()

        for step, io in object_registry.items():
            for key, table_doc_id in io["inputs"].items():
                all_inputs.add(table_doc_id)
                producers = object_to_step.get(table_doc_id)
                if not producers:  ## First inputs
                    links.append((key, step, table_doc_id))
                else:
                    for producer in producers:
                        if producer != step:
                            links.append((producer, step, table_doc_id))
                            consumed_outputs.add(table_doc_id)

        # Detect final outputs (not consumed by any downstream step)
        all_outputs = {
            (table, doc_id)
            for io in object_registry.values()
            for _, (table, doc_id) in io["outputs"].items()
        }
        first_inputs = all_inputs - all_outputs
        final_outputs = all_outputs - consumed_outputs

        return {
            "object_registry": object_registry,
            "object_to_step": object_to_step,
            "links": links,
            "first_inputs": first_inputs,
            "final_outputs": final_outputs,
            "context_keys": list(context.keys()),
            "context": context
        }

    def plot_dataflow_graph(
        self,
        trace_result: dict,
        format: str = "png",
        view: bool = True,
        output_file: Optional[str] = None
    ) -> Digraph:
        """
        Visualizes the dataflow graph from a trace result, including step dependencies,
        external first inputs, and final outputs.
        """
        dot = Digraph(name=self.pipeline_name, graph_attr={"rankdir": "TB"})

        # Step nodes
        for step_name in trace_result["context_keys"]:
            dot.node(step_name, shape="box", style="filled", fillcolor="lightgray")

        # Data flow edges
        for source, target, (table, doc_id) in trace_result["links"]:
            label = f"{table}:{doc_id}"
            dot.edge(source, target, label=label)

        # Final output nodes (grouped by table)
        tables = {}
        for table, doc_id in trace_result.get("final_outputs", []):
            if table not in tables:
                tables[table] = True
                dot.node(table, shape="oval", style="filled", fillcolor="white")
            producers = trace_result["object_to_step"].get((table, doc_id), set())
            for producer in producers:
                dot.edge(producer, table, label=doc_id)


        # Render if requested
        filename = output_file or f"{self.pipeline_name}_graph"
        dot.render(filename, format=format, view=view)

        return dot

    def run(self, pipeline_run_id: Optional[str] = None, persist: bool = False, params: Optional[Dict[str, Any]] = None):
        pipeline_run_id = pipeline_run_id or f"pipeline-{int(time.time())}"
        self.logger.info(f"Starting pipeline '{self.pipeline_name}' with run_id={pipeline_run_id}")

        pipeline_start = datetime.utcnow()
        error = None

        try:
            for step in self.steps:
                self.logger.info(f"Running step: {step.step_name}")
                output_dict = step.execute(
                    persist=persist,
                    step_run_id=pipeline_run_id,
                    pipeline_name=self.pipeline_name,
                    pipeline_run_id=pipeline_run_id,
                    context=self.context
                )
                self.context[step.step_name] = {
                    "inputs": step.input_dict,
                    "outputs": output_dict,
                }
        except Exception as e:
            error = str(e)
            self.logger.exception("Pipeline execution failed")
        finally:
            pipeline_end = datetime.utcnow()
            git_info = get_git_metadata()
            pipeline_log = PipelineRunRecord(
                table_name="pipeline_runs",
                pipeline_name=self.pipeline_name,
                pipeline_run_id=pipeline_run_id,
                started_at=pipeline_start,
                completed_at=pipeline_end,
                duration=(pipeline_end - pipeline_start).total_seconds(),
                num_steps=len(self.steps),
                success=error is None,
                error=error,
                params=params or {},
                **git_info
            )
            if persist:
                self.storage.save("pipeline_runs", pipeline_log.model_dump(mode="json"))

        self.logger.info(f"Pipeline '{self.pipeline_name}' completed.")
        return {
            "pipeline_name": self.pipeline_name,
            "pipeline_run_id": pipeline_run_id,
            "success": (error is None),
            "duration": (pipeline_end - pipeline_start).total_seconds(),
            "num_steps": len(self.steps),
            "error": error,
            "step_statuses": [
                {
                    "step_name": step_name,
                    "num_inputs": len(self.context.get(step_name, {}).get("inputs", [])),
                    "num_outputs": len(self.context.get(step_name, {}).get("outputs", [])),
                    "success": True  # if it reached here, it succeeded
                }
                for step_name in self.context.keys()
            ],
            "context": self.context
        }