""" Dense summarizer step. notebook. """
import logging
import time

from ttd.flows.utils import predict

logger = logging.getLogger(__name__)


def execute(flow):
    """Generate dense summaries for AI-related articles."""
    logger.info("Generating dense summaries for AI-related articles...")
    step_name = "dense_summarizer"
    model_spec_name = "dense_summarizer_spec"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    flow.metrics.setdefault("models_spec_names", {})[step_name] = model_spec_name
    flow.metrics.setdefault("models_io", {})[model_spec_name] = {
        "inputs": [],
        "outputs": [],
        "errors": []
    }

    for idx, article in enumerate(flow.articles):
        # TODO REMOVE TRUE
        if True or flow.metrics["models_io"]["article_is_ai_classifier_spec"]["outputs"][idx]["output"]:
            inputs, outputs, errors = predict(model_spec_name, [article])
            flow.metrics["models_io"][model_spec_name]["inputs"] += inputs
            outputs[0]["doc_id"] = flow.articles[idx]["doc_id"]
            flow.metrics["models_io"][model_spec_name]["outputs"] += outputs
            flow.metrics["models_io"][model_spec_name]["errors"] += errors
        else:
            flow.metrics["models_io"][model_spec_name]["inputs"].append(None)
            flow.metrics["models_io"][model_spec_name]["outputs"].append(None)

    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
