""" Replicate articles with enriched fields and predictions. """
import logging
from tinydb import Query
from evaluate import load as load_metric

from ttd.storage.ttd_storage import TTDStorage
from ttd.models.providers.openai_embedding import compute_tag_list_similarity
from ttd.models.loader import load_model_spec

logger = logging.getLogger(__name__)


def execute(flow):
    """Replicate articles with enriched fields and predictions."""
    logger.info("Replicating articles with enrichment data...")

    storage = TTDStorage(flow.config.get("db_path"))
    flow.tag_embedding_spec_name = "tag_embedding_spec"
    tag_embedding_spec = load_model_spec(flow.tag_embedding_spec_name)

    replicated_articles = []

    for idx, article in enumerate(flow.articles):
        print(len(flow.articles))
        record = {
            "table_name": flow.replicates_table
        }

        # Copy article basic fields
        for key, value in article.items():
            if key == "doc_id":
                record["original_doc_id"] = value
            elif key != "table_name":
                record[key] = value

        # Prediction results
        record["is_ai_pred_added"] = flow.is_ai_preds[idx]["output"]
        if record["is_ai_pred_added"]:
            dense_pred = flow.dense_summaries_preds[idx]
            core_line_pred = flow.core_line_summaries_preds[idx]
            tags_pred = flow.tags_preds[idx]

            if dense_pred:
                record["dense_summary_added"] = dense_pred["output"]
                record["length_dense_summary_added"] = len(dense_pred["output"])

            if core_line_pred:
                record["core_line_summary_added"] = core_line_pred["output"]
                record["length_core_line_summary_added"] = len(core_line_pred["output"])

            if tags_pred:
                record["tags_pred_added"] = tags_pred["tags"]
                record["length_tags_pred_added"] = len(tags_pred["tags"])
                record["clusters_names_in_order_added"] = []

                TagWord = Query()
                cluster_table = storage.get_table("tag_clusters")

                for tag_name in record["tags_pred_added"]:
                    tag = storage.search("tags", TagWord.name == tag_name)
                    if tag:
                        tag = tag[0]
                        cluster = cluster_table.get(doc_id=int(tag["tag_cluster_id"]))
                        if cluster:
                            record["clusters_names_in_order_added"].append(
                                cluster["name"]
                            )

        # Compute quality metrics
        rouge = load_metric("rouge")
        bert_score = load_metric("bertscore")

        if "dense_summary_added" in record and "core_line_summary_added" in record:
            rouge_result = rouge.compute(
                predictions=[record["dense_summary_added"]],
                references=[record["core_line_summary_added"]],
                rouge_types=["rougeL"]
            )
            record["dense_vs_core_rouge_eval"] = rouge_result["rougeL"]

        if "summary" in record and "dense_summary_added" in record:
            bert_result = 0
            # TO DELETE takes too much time
            # bert_result = bert_score.compute(
            #     predictions=[record["dense_summary_added"]],
            #     references=[record["summary"]],
            #     lang="en"
            # )
            # record["bert_score_summary_vs_dense_eval"] = float(bert_result["f1"][0])

        if "tags" in record and "tags_pred_added" in record:
            tags = record["tags"]
            tags_pred = record["tags_pred_added"]
            avg_sim = compute_tag_list_similarity(
                tags,
                tags_pred,
                tag_embedding_spec._loaded_model
            )
            record["tag_similarity_eval"] = avg_sim
        # Save replicated article
        logger.info(f"✅ Replicated {idx+1}/{len(flow.articles)} articles.")
        # TODO Fix ArtifactManager_lazy_load SHOUlD OFFLOAD LARGE FIELDS
        del record["text_content"]
        storage.save(flow.replicates_table, storage.lazy_load(record))
        replicated_articles.append(record)
        logger.info(f"✅ Replicated {idx+1}/{len(flow.articles)} articles.")

    # Save results in flow object
    flow.replicated_articles = replicated_articles
    logger.info(f"✅ Replicated {len(flow.replicated_articles)} articles.")
