""" Is AI articles step. """
import logging

from ttd.storage.ttd_storage import TTDStorage
from ttd.models.loader import load_model_spec

logger = logging.getLogger(__name__)


def execute(flow):
    """ Classify if articles are AI-related. """
    logger.info("Classifying articles as AI-related...")

    # Reload storage and lazy load articles
    storage = TTDStorage(flow.config.get("db_path"))
    articles = storage.lazy_load(flow.articles)

    # Load classifier model
    flow.is_ai_classifier_spec_name = "article_is_ai_classifier_spec"
    is_ai_classifier_spec = load_model_spec(flow.is_ai_classifier_spec_name)

    flow.is_ai_preds = []

    for i, article in enumerate(articles):
        input = {
            "article__title": article["title"],
            "article__text_content": article["text_content"]
        }
        is_ai_classifier_spec.input_schema.model_validate(input)
        pred = is_ai_classifier_spec._loaded_model.predict(input)
        output = {"is_ai": pred["output"]}
        is_ai_classifier_spec.output_schema.model_validate(output)

        pred["is_ai"] = output["is_ai"]
        flow.is_ai_preds.append(pred)
        flow.articles = [dict(articles) for articles in articles]

        article_type = 'AI' if pred['is_ai'] else 'Non-AI'
        logger.info(
            f"✅ Article {i+1}/{len(flow.articles)} classified as {article_type}.")

    logger.info(f"✅ Classification completed for {len(flow.articles)} articles.")
