""" Core line summarizer step. """
import logging

from ttd.models.loader import load_model_spec

logger = logging.getLogger(__name__)


def execute(flow):
    """Generate core line summaries based on dense summaries."""
    logger.info("Loading core line summarizer model...")

    # Load model spec
    flow.core_line_summarizer_spec_name = "core_line_summarizer_spec"
    core_line_summarizer_spec = load_model_spec(flow.core_line_summarizer_spec_name)

    logger.info("Generating core line summaries...")
    core_line_summaries_preds = []

    for idx, (is_ai_pred, dense_summary_pred) \
            in enumerate(zip(flow.is_ai_preds, flow.dense_summaries_preds)):
        if is_ai_pred["is_ai"]:
            input_data = {
                "dense_summarizer__output": dense_summary_pred["output"],
            }
            core_line_summarizer_spec.input_schema.model_validate(input_data)
            pred = core_line_summarizer_spec._loaded_model.predict(input_data)
            output_data = {"core_line_summary": pred["output"]}
            core_line_summarizer_spec.output_schema.model_validate(output_data)
            core_line_summaries_preds.append(pred)
            logger.info(
                f"✅ Core line summary generated {idx+1}/{len(flow.articles)}."
            )
        else:
            core_line_summaries_preds.append(None)
            logger.info(
                f"⚡ Skipped core line summary {idx+1}/{len(flow.articles)} (Non-AI)."
            )

    flow.core_line_summaries_preds = core_line_summaries_preds
    count = sum(p is not None for p in core_line_summaries_preds)
    total = len(core_line_summaries_preds)
    logger.info(f"✅ Generated {count} core summaries out of {total} articles.")
