""" Utility functions for the TTD pipeline. """
import logging
import time
from pathlib import Path
from collections import Counter

from ttd.ingestion.parser import extract_domain
from ttd.utils.print import safe_pretty_print
from ttd.models.loader import load_model_spec

logger = logging.getLogger(__name__)

def get_articles_with_no_error(articles):
    articles_with_no_error = []
    for article in articles:
        if not article.get("metadata", {}).get("error"):
            articles_with_no_error.append(article)

    return articles_with_no_error

def print_domain_matches(rss_file_path: Path, domain_counts: Counter, label: str = ""):
    print(f"\n📄 Checking {label or rss_file_path.name}:")
    with rss_file_path.open("r") as file:
        for line in file:
            url = line.strip()
            if not url:
                continue
            domain = extract_domain(url)
            count = domain_counts.get(domain, 0)
            if count > 0:
                print(f"[✅] Found: {domain} ({count} article(s))")
            else:
                print(f"[❌] Not found: {domain}")

def predict(model_spec_name, data):
    """Predict using the model specified by model_spec_name."""
    model_spec = load_model_spec(model_spec_name)
    model_inputs = []
    model_outputs = []
    errors = []
    logger.info(f"✅ Loading model spec: {model_spec_name}")
    logger.info(safe_pretty_print(model_spec))

    for idx, input in enumerate(data):
        validated_input = model_spec.extract_and_validate_input(input)
        logger.info(f"✅ Provider '{model_spec.provider}'"
                    f"  Model '{model_spec.config.model_name}' ")
        logger.info(f"✅ Predict {idx+1}/{len(data)} ")
        logger.info(f"✅ Inputs:")
        logger.info(safe_pretty_print(validated_input))
        # TODO CHANGE THIS LINE BUT WORKS FOR NOW
        # model_inputs.append(validated_input)
        model_inputs.append({"article_id": input["doc_id"]})
        pred_start_time = time.time()
        try:
            pred_success = True
            pred = model_spec._loaded_model.predict(validated_input)
        except Exception as e:
            logger.error(f"❌ Error on article {idx}: {str(e)}")
            errors.append({
                "index": idx,
                "error_message": str(e),
                "article_id": input["doc_id"]
            })
            pred_success = False
        if pred_success:
            pred_duration = time.time() - pred_start_time
            pred["metadata"]["duration"] = pred_duration
            validated_output = model_spec.validate_output(pred)
            logger.info(f"✅ Outputs:")
            logger.info(safe_pretty_print(validated_output))
            model_outputs.append(validated_output)
        else:
            model_outputs.append(None)
    return model_inputs, model_outputs, errors
