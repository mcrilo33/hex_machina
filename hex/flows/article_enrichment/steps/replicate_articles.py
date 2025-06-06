""" Replicate articles with enriched fields and predictions. """
import logging
import time
from tinydb import Query
from evaluate import load as load_metric

from hex.storage.hex_storage import HexStorage
from hex.models.providers.openai_embedding import compute_tag_list_similarity
from hex.models.loader import load_model_spec

logger = logging.getLogger(__name__)


def execute(flow):
    """Replicate articles with enriched fields and predictions."""
    logger.info("Replicating articles with enrichment data...")
    step_name = "replicate_articles"
    model_spec_name = "tag_embedding_spec"
    start_time = time.time()
    flow.metrics.setdefault("step_start_times", {})[step_name] = start_time
    flow.metrics.setdefault("models_spec_names", {})[step_name] = model_spec_name
    flow.metrics.setdefault("models_io", {})[model_spec_name] = {
        "inputs": [],
        "outputs": [],
        "errors": []
    }

    storage = HexStorage(flow.config.get("db_path"))
    flow.tag_embedding_spec_name = "tag_embedding_spec"
    tag_embedding_spec = load_model_spec(flow.tag_embedding_spec_name)
    TagWord = Query()
    cluster_table = storage.get_table("tag_clusters")

    replicated_articles = []

    data = flow.articles
    for idx, article in enumerate(data):
        pred_start_time = time.time()
        record = {
            "table_name": flow.replicates_table
        }
        # Copy article basic fields
        for key, value in article.items():
            if key == "doc_id":
                record["original_doc_id"] = value
            elif key == "table_name":
                record["original_table_name"] = value
            else:
                record[key] = value

        # Prediction results
        record["is_ai_added"] = \
            flow.metrics["models_io"]["article_is_ai_classifier_spec"]["outputs"][idx]["output"]
        dense_pred = flow.metrics["models_io"]["dense_summarizer_spec"]["outputs"][idx]
        if dense_pred:
            record["dense_summary_added"] = dense_pred["output"]
            record["dense_summary_length_added"] = len(dense_pred["output"])
        core_line_pred = flow.metrics["models_io"]["core_line_summarizer_spec"]["outputs"][idx]
        if core_line_pred:
            record["core_line_summary_added"] = core_line_pred["output"]
            record["core_line_summary_length_added"] = len(core_line_pred["output"])
        tags_pred = flow.metrics["models_io"]["tagger_spec"]["outputs"][idx]
        if tags_pred:
            record["tags_pred_added"] = tags_pred["output"]
            record["tags_pred_length_added"] = len(tags_pred["output"])
            record["clusters_names_in_order_added"] = []
            cluster_inserted = {}
            for tag_name in record["tags_pred_added"]:
                tag = storage.search("tags", TagWord.name == tag_name)
                if tag:
                    tag = tag[0]
                    cluster = cluster_table.get(doc_id=int(tag["tag_cluster_id"]))
                    if cluster and cluster["name"] not in cluster_inserted:
                        record["clusters_names_in_order_added"].append(
                            cluster["name"]
                        )
                        cluster_inserted[cluster["name"]] = True

        # Compute quality metrics
        rouge = load_metric("rouge")
        # TO DELETE takes too much time
        # bert_score = load_metric("bertscore")

        if "dense_summary_added" in record and "title" in record:
            rouge_result = rouge.compute(
                predictions=[record["dense_summary_added"]],
                references=[record["title"]],
                rouge_types=["rougeL"]
            )
            record["title_vs_core_rouge_eval"] = rouge_result["rougeL"]

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
        # TODO Fix ArtifactManager_lazy_load SHOUlD OFFLOAD LARGE FIELDS
        del record["text_content"]
        storage.save(flow.replicates_table, storage.lazy_load(record))
        replicated_articles.append(record)
        logger.info(f"✅ Replicate {idx+1}/{len(data)} ")
        pred_duration = time.time() - pred_start_time
        flow.metrics["models_io"][model_spec_name]["outputs"].append({
            "metadata": {"duration": pred_duration}
        })

    # Save results in flow object
    flow.replicated_articles = replicated_articles
    total_time = time.time() - start_time
    flow.metrics.setdefault("step_duration", {})[step_name] = total_time
    logger.info(f"✅ Step {step_name} done in {total_time:.2f}s")
