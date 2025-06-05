""" Is AI articles step. """
import logging
import time

from ttd.utils.print import safe_pretty_print
from ttd.storage.ttd_storage import TTDStorage
from ttd.models.loader import load_model_spec
from ttd.flows.predict import predict

logger = logging.getLogger(__name__)


def execute(flow):
    """ Classify if articles are AI-related. """
    logger.info("Classifying articles as AI-related...")
    step_name = "is_ai_articles"
    model_spec_name = "article_is_ai_classifier_spec"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    flow.metrics.setdefault("models_spec_names", {})[step_name] = model_spec_name
    flow.metrics.setdefault("models_io", {})[model_spec_name] = {
        "inputs": [],
        "outputs": [],
        "errors": []
    }

    # Reload storage and lazy load articles
    storage = TTDStorage(flow.config.get("db_path"))
    articles = storage.lazy_load(flow.articles)

    (flow.metrics["models_io"][model_spec_name]["inputs"],
     flow.metrics["models_io"][model_spec_name]["outputs"],
     flow.metrics["models_io"][model_spec_name]["errors"]) = \
         predict(model_spec_name, articles)

    flow.articles = [dict(article) for article in articles]
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
