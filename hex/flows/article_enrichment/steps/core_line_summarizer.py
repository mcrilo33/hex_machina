""" Core line summarizer step. """
import logging
import time

from hex.flows.predict import predict

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

    dense_summaries = flow.metrics["models_io"]["dense_summarizer_spec"]["outputs"]
    for idx, dense_summary in enumerate(dense_summaries):
        logger.info(f"✅ Article {idx+1}/{len(dense_summaries)} ")
        if dense_summary: 
            inputs, outputs, errors = predict(model_spec_name, [dense_summary])
            flow.metrics["models_io"][model_spec_name]["inputs"] += inputs
            flow.metrics["models_io"][model_spec_name]["outputs"] += outputs
            flow.metrics["models_io"][model_spec_name]["errors"] += errors
        else:
            flow.metrics["models_io"][model_spec_name]["inputs"].append(None)
            flow.metrics["models_io"][model_spec_name]["outputs"].append(None)

    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
