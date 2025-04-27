""" Extract tags from dense summaries of AI articles. """
import logging

from ttd.models.loader import load_model_spec

# Initialize logger
logger = logging.getLogger(__name__)


def execute(flow):
    """Extract tags from dense summaries of AI articles."""
    logger.info("Loading tagger model...")

    flow.tagger_spec_name = "tagger_spec"
    tagger_spec = load_model_spec(flow.tagger_spec_name)

    tags_preds = []

    logger.info("Extracting tags from dense summaries...")
    for idx, (is_ai_pred, dense_summary_pred) in enumerate(
        zip(flow.is_ai_preds, flow.dense_summaries_preds)
    ):
        if is_ai_pred["is_ai"]:
            input_data = {
                "dense_summarizer__output": dense_summary_pred["output"],
            }
            # Validate input format
            tagger_spec.input_schema.model_validate(input_data)

            # Predict tags
            pred = tagger_spec._loaded_model.predict(input_data)

            # Validate output format
            output_data = {"tags": pred["output"]}
            tagger_spec.output_schema.model_validate(output_data)

            # Clean tags
            pred["tags"] = [
                tag.strip() for tag in pred["output"].split(",") if tag.strip()
            ]
            tags_preds.append(pred)
            logger.info(
                f"✅ Tags generated for article {idx+1}/{len(flow.articles)}."
            )
        else:
            tags_preds.append(None)
            logger.info(
                f"⚡ Skipped tagging for article {idx+1}/{len(flow.articles)} (Non-AI)."
            )

    # Save extracted tags to flow
    flow.tags_preds = tags_preds
    count_tags = sum(p is not None for p in tags_preds)
    logger.info(f"✅ Extracted tags for {count_tags} AI articles.")
