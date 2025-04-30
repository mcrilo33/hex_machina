""" Extract tags from dense summaries of AI articles. """
import logging
import time

from ttd.flows.utils import predict

# Initialize logger
logger = logging.getLogger(__name__)


def execute(flow):
    """Extract tags from dense summaries of AI articles."""
    logger.info("Extracting tags from dense summaries...")
    step_name = "tagger"
    model_spec_name = "tagger_spec"
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
        # TODO REMOVE TRUE
        if True or dense_summary: 
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
