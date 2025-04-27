""" Dense summarizer step. """
import logging

from ttd.models.loader import load_model_spec

logger = logging.getLogger(__name__)


def execute(flow):
    """ Generate dense summaries for AI-related articles. """
    logger.info("Generating dense summaries for AI-related articles...")

    # Load dense summarizer model
    flow.dense_summarizer_spec_name = "dense_summarizer_spec"
    dense_summarizer_spec = load_model_spec(flow.dense_summarizer_spec_name)

    # Initialize prediction list
    flow.dense_summaries_preds = []

    # Process articles
    for idx, (article, is_ai_pred) in enumerate(zip(flow.articles, flow.is_ai_preds)):
        if is_ai_pred["is_ai"]:
            input_data = {
                "article__title": article["title"],
                "article__text_content": article["text_content"]
            }
            dense_summarizer_spec.input_schema.model_validate(input_data)
            pred = dense_summarizer_spec._loaded_model.predict(input_data)
            output = {"dense_summary": pred["output"]}
            dense_summarizer_spec.output_schema.model_validate(output)

            flow.dense_summaries_preds.append(pred)
            logger.info(
                f"✅ Dense summary generated {idx+1}/{len(flow.articles)}."
            )
        else:
            flow.dense_summaries_preds.append(None)
            logger.info(
                f"⚡ Skipped dense summary {idx+1}/{len(flow.articles)} (Non-AI)."
            )

    count_dense_summaries = sum(1 for p in flow.dense_summaries_preds if p is not None)
    logger.info(
        f"✅ Dense summaries generated for {count_dense_summaries} AI-related articles."
    )
