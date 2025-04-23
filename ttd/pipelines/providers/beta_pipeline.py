import numpy as np
from ttd.pipelines.core import Pipeline, PredictStep, TransformStep
from ttd.storage.ttd_storage import TTDStorage
from ttd.models.registry import load_model_spec
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from datetime import datetime, timezone
from ttd.models.providers.openai_embedding import compute_tag_list_similarity
from tinydb import Query
from evaluate import load as load_metric


def get_articles_after_date(storage):
    date_threshold = parse_date('Thu, 03 Apr 2025 18:00:00 +0000')
    Article = Query()

    # Get all articles after the given date
    articles = storage.search(
        "articles",
        Article.published_date.test(lambda d: parse_date(d) >= date_threshold)
    )
    articles = articles[:2]
    # Caching
    replicated_table = storage.get_table("replicated_articles") 
    to_process = []
    for article in articles:
        replicated_article = replicated_table.get(doc_id=article["doc_id"])
        if not replicated_article:
            to_process.append(article)
    # Example: return first 10 articles
    return [{"article": article} for article in to_process]

def str_to_bool(value: str) -> bool:
        return value.lower() in ("true", "1", "yes", "y", "t")
def get_articles_for_summary(storage, context):
    inputs = context["is_ai_step"]["inputs"]
    outputs = context["is_ai_step"]["outputs"]

    ai_articles = []
    for i, pred in enumerate(outputs):
        if str_to_bool(pred["output"]):
            ai_articles.append({
                "article": inputs[i]["article"],
            })
    return ai_articles


def get_dense_summary(storage, context):
    outputs = context["dense_summary_step"]["outputs"]

    dense_summaries = []
    for i, pred in enumerate(outputs):
        dense_summaries.append({
            "dense_summarizer": outputs[i],
        })
    return dense_summaries

def get_tags_with_article_id_and_merge(storage, context):
    inputs = context["dense_summary_step"]["inputs"]
    outputs = context["tagger_step"]["outputs"]

    tags = {}
    for i, pred in enumerate(outputs):
        for tag in [t.strip() for t in pred["output"].split(",")]:
            tag = tag.strip()
            if tag not in tags:
                tags[tag] = {
                    "table_name": pred["table_name"],
                    "doc_id": pred["doc_id"],
                    "output": tag,
                    "history": [inputs[i]["article"]["published_date"]]
                }
            else:
                tags[tag]["history"].append(inputs[i]["article"]["published_date"])
    return [{"tagger": k} for k in tags.values()]

def get_unique_tags(storage, context):
    outputs = context["transform_tags_step"]["outputs"]
    return outputs

def count_since_last(history: list, delta: relativedelta) -> int:
    threshold = datetime.now(timezone.utc) - delta
    return sum(1 for d in history if parse_date(d) > threshold)

def update_cluster(cluster, storage):
    print("update_cluster", cluster)
    tag_table = storage.get_table("tags")
    max_count = 0
    period = relativedelta(months=6)
    for id in cluster["tag_synonyms"].keys():
        synonym = tag_table.get(doc_id=id)
        synonym_count = count_since_last(synonym["history"], period)
        if synonym_count > max_count:
            max_count = synonym_count
            cluster_name = synonym["name"]
    cluster["name"] = cluster_name

    return cluster


def assign_cluster_to(tag, storage, embedding_model):
    print("assign_cluster_to", tag)
    tag_cluster_table = storage.get_table("tag_clusters")
    for cluster in tag_cluster_table:
        if tag_is_similar_to(tag, cluster, storage, embedding_model):
            tag["tag_cluster_id"] = str(cluster.doc_id)
            cluster["tag_synonyms"][tag["doc_id"]] = tag["name"]
            return {"tag": tag, "cluster": update_cluster(cluster, storage)}
    # If we are still here it means that no cluster was found
    # We create a new cluster with this tag
    new_cluster = {
        "table_name": "tag_clusters",
        "name": tag["name"],
        "tag_synonyms": {
            tag["doc_id"]: tag["name"]
        }
    }
    tag_cluster_id = storage.save("tag_clusters", new_cluster)[0]
    tag["tag_cluster_id"] = tag_cluster_id
    return {"tag": tag}


def tag_is_similar_to(tag, cluster, storage, embedding_model):
    print("tag_is_similar_to", tag, cluster)
    from numpy import array
    from sklearn.metrics.pairwise import cosine_similarity
    tag_embedding = embedding_model.predict(tag["name"])["output"]
    for id, synonym in cluster["tag_synonyms"].items():
        synonym_embedding = embedding_model.predict(synonym)["output"]
        sim_matrix = cosine_similarity(
            array([tag_embedding]),
            array([synonym_embedding])
        )
        THRESHOLD = 0.6
        if max(sim_matrix[0] > THRESHOLD):
            return True
    return False


def transform_tag(pred, storage):
    TagWord = Query()
    tag = storage.search("tags", TagWord.name == pred["tagger"]["output"])
    if len(tag):
        tag = tag[0]
        tag["history"] += pred["tagger"]["history"]
    else:
        tag = {
            "table_name": "tags",
            "name": pred["tagger"]["output"],
            "history": pred["tagger"]["history"]
        }
    return {"tag": tag}


def transform_cluster(tag, storage, embedding_model):
    print("transform_cluster", tag)
    tag = tag["tag"]
    if "tag_cluster_id" in tag:
        tag_cluster_table = storage.get_table("tag_clusters")
        cluster = tag_cluster_table.get(doc_id=int(tag["tag_cluster_id"]))
        output = {"cluster": update_cluster(cluster, storage)}
    else:
        output = assign_cluster_to(tag, storage, embedding_model)
    for k, v in output.items():
        try:
            v["doc_id"] = v.doc_id
        except:
            pass
        if "doc_id" in v:
            storage.update(v["table_name"], v)
        else:
            storage.save(v["table_name"], v)
    return

def get_articles_preds(storage, context):
    """
    Collect article IDs and flags for fields computed in previous steps.
    """
    # Original inputs to AI classification step
    articles_inputs = context["is_ai_step"]["inputs"]
    is_ai_preds = context["is_ai_step"]["outputs"]
    # Outputs presence flags
    dense_summary_preds = context["dense_summary_step"]["outputs"]
    core_line_summary_preds = context["core_line_summary_step"]["outputs"]
    tags_preds = context["tagger_step"]["outputs"]

    objs = []
    j = 0
    for i, inp in enumerate(articles_inputs):
        objs.append({
            "article": inp["article"],
            "is_ai_pred": is_ai_preds[i],
        })
        if str_to_bool(is_ai_preds[i]["output"]):
            objs[-1]["dense_summary_pred"] = dense_summary_preds[j]
            objs[-1]["core_line_summary_pred"] = core_line_summary_preds[j]
            objs[-1]["tags_pred"] = tags_preds[j]
            j += 1
    return objs

def replicate_article(objs, storage, embedding_model):
    record = {
        "table_name": "replicated_articles__beta_enrichment_pipeline"
    }
    article = objs["article"]
    for key, value in article.items():
        if key == "doc_id":
            record["original_doc_id"] = value
        elif key != "table_name":
            record[key] = value
    record["is_ai_pred_added"] = str_to_bool(objs["is_ai_pred"]["output"])
    if "dense_summary_pred" in objs:
        record["dense_summary_added"] = objs["dense_summary_pred"]["output"]
        record["length_dense_summary_added"] = len(record["dense_summary_added"])
    if "core_line_summary_pred" in objs:
        record["core_line_summary_added"] = objs["core_line_summary_pred"]["output"]
        record["length_core_line_summary_added"] = len(record["core_line_summary_added"])
    if "tags_pred" in objs:
        record["tags_pred_added"] = \
            [t.strip() for t in objs["tags_pred"]["output"].split(",")]
        record["clusters_names_in_order_added"] = []
        TagWord = Query()
        cluster_table = storage.get_table("tag_clusters")
        for t in record["tags_pred_added"]:
            tag = storage.search("tags", TagWord.name == t)
            if len(tag):
                tag = tag[0]
                cluster = cluster_table.get(doc_id=int(tag["tag_cluster_id"]))
                record["clusters_names_in_order_added"].append(cluster["name"])
    
    # --- Compute newsletter quality metrics ---
    rouge = load_metric("rouge")
    bert_score = load_metric("bertscore")

    # ROUGE between dense and core summaries
    if "dense_summary_added" in record and "core_line_summary_added" in record:
        rouge_result = rouge.compute(
            predictions=[record["dense_summary_added"]],
            references=[record["core_line_summary_added"]],
            rouge_types=["rougeL"]
        )
        record["dense_vs_core_rouge_eval"] = rouge_result["rougeL"]

    # BERTScore between summary and dense summary
    if "summary" in record and "dense_summary_added" in record:
        bert_result = bert_score.compute(
            predictions=[record["dense_summary_added"]],
            references=[record["summary"]],
            lang="en"
        )
        record["bert_score_summary_vs_dense_eval"] = float(bert_result["f1"][0])

    # Embedding similarity between original tags and predicted tags
    if "tags" in record and "tags_pred_added" in record:
        tags = record["tags"]
        tags_pred = record["tags_pred_added"]
        avg_mx_cosine_similarity = compute_tag_list_similarity(
            tags,
            tags_pred,
            embedding_model
        )
        record["tag_similarity_eval"] = avg_mx_cosine_similarity

    return {"record": record}

def get_beta_pipeline(storage: TTDStorage) -> Pipeline:
    """
    Returns a beta pipeline containing a single AI classification step.

    Args:
        storage (TTDStorage): The storage service instance.
        debug (bool): Whether to enable debug logging.

    Returns:
        Pipeline: Configured pipeline instance with AI classification step.
    """
    ai_classifier_spec = load_model_spec(
        "article_is_ai_classifier_spec", storage)
    dense_summary_spec = load_model_spec("dense_summarizer_spec", storage)
    core_line_summary_spec = load_model_spec(
        "core_line_summarizer_spec", storage)
    tagger_spec = load_model_spec("tagger_spec", storage)
    tag_to_embedding_spec = load_model_spec("tag_embedding_spec", storage)

    ai_classifier_step = PredictStep(
        step_name="is_ai_step",
        model_spec=ai_classifier_spec,
        input_loader=get_articles_after_date,
        storage=storage
    )

    dense_summary_step = PredictStep(
        step_name="dense_summary_step",
        model_spec=dense_summary_spec,
        storage=storage,
        input_loader=get_articles_for_summary,
    )

    core_line_summary_step = PredictStep(
        step_name="core_line_summary_step",
        model_spec=core_line_summary_spec,
        storage=storage,
        input_loader=get_dense_summary,
    )

    tagger_step = PredictStep(
        step_name="tagger_step",
        model_spec=tagger_spec,
        storage=storage,
        input_loader=get_dense_summary,
    )

    transform_tags_step = TransformStep(
        step_name="transform_tags_step",
        storage=storage,
        input_loader=get_tags_with_article_id_and_merge,
        operation=transform_tag
    )

    transform_clusters_step = TransformStep(
        step_name="transform_clusters_step",
        storage=storage,
        input_loader=get_unique_tags,
        operation=lambda tag, storage:
            transform_cluster(
                tag,
                storage,
                tag_to_embedding_spec._loaded_model
            )
    )

    replicate_articles_step = TransformStep(
        step_name="replicate_articles_step",
        storage=storage,
        input_loader=get_articles_preds,
        operation=lambda article, storage: replicate_article(
            article,
            storage,
            tag_to_embedding_spec._loaded_model
        )
    )

    pipeline = Pipeline(
        pipeline_name="beta_enrichment_pipeline",
        steps=[
            ai_classifier_step,
            dense_summary_step,
            core_line_summary_step,
            tagger_step,
            transform_tags_step,
            transform_clusters_step,
            replicate_articles_step
        ],
        storage=storage
    )

    storage.db.drop_table("predictions")
    storage.db.drop_table("tags")
    storage.db.drop_table("tag_clusters")
    storage.db.drop_table("replicated_articles__beta_enrichment_pipeline")
    storage.db.drop_table("step_runs")
    storage.db.drop_table("pipeline_runs")
    #trace = pipeline.trace_dataflow()
    #pipeline.plot_dataflow_graph(trace)

    return pipeline
