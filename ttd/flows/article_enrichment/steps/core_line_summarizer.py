""" Core line summarizer step. """
import logging
import time

from ttd.flows.utils import predict

logger = logging.getLogger(__name__)


def execute(flow):
    """Generate core line summaries based on dense summaries."""
    logger.info("Generating core line summaries for AI-related articles...")
    step_name = "core_line_summarizer"
    model_spec_name = "core_line_summarizer_spec"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    flow.metrics.setdefault("models_spec_names", {})[step_name] = model_spec_name
    flow.metrics.setdefault("models_io", {})[model_spec_name] = {
        "inputs": [],
        "outputs": [],
        "errors": []
    }

    for idx in range(len(flow.articles)):
        # TODO REMOVE TRUE
        if True or flow.metrics["models_io"]["article_is_ai_classifier_spec"]["outputs"][idx]["output"]:
            dense_summary = flow.metrics["models_io"]["dense_summarizer_spec"]["outputs"][idx]
            inputs, outputs, errors = predict(model_spec_name, [dense_summary])
            flow.metrics["models_io"][model_spec_name]["inputs"] += inputs
            flow.metrics["models_io"][model_spec_name]["outputs"] += outputs
            flow.metrics["models_io"][model_spec_name]["errors"] += errors

    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
