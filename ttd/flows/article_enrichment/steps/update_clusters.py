""" Update clusters with new tags. """
import logging
import time
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from numpy import array
from sklearn.metrics.pairwise import cosine_similarity

from ttd.storage.ttd_storage import TTDStorage
from ttd.models.loader import load_model_spec

logger = logging.getLogger(__name__)


def _count_since_last(history, delta):
    threshold = datetime.now(timezone.utc) - delta
    return sum(1 for d in history if parse_date(d) > threshold)


def _update_cluster(cluster, storage):
    tag_table = storage.get_table("tags")
    max_count = 0
    period = relativedelta(months=6)

    for id in cluster["tag_synonyms"].keys():
        synonym = tag_table.get(doc_id=id)
        if synonym is None:
            continue
        synonym_count = _count_since_last(synonym["history"], period)
        if synonym_count > max_count:
            max_count = synonym_count
            cluster_name = synonym["name"]

    cluster["name"] = cluster_name
    return cluster


def _tag_is_similar_to(tag, cluster, embedding_model):
    tag_embedding = embedding_model.predict(tag["name"])["output"]

    for _, synonym_name in cluster["tag_synonyms"].items():
        synonym_embedding = embedding_model.predict(synonym_name)["output"]
        sim_matrix = cosine_similarity(
            array([tag_embedding]),
            array([synonym_embedding])
        )
        THRESHOLD = 0.6
        if max(sim_matrix[0] > THRESHOLD):
            return True
    return False


def _assign_cluster_to(tag, storage, embedding_model):
    tag_cluster_table = storage.get_table("tag_clusters")

    for cluster in tag_cluster_table:
        if _tag_is_similar_to(tag, cluster, embedding_model):
            tag["tag_cluster_id"] = str(cluster.doc_id)
            cluster["tag_synonyms"][tag["doc_id"]] = tag["name"]
            return {"tag": tag, "cluster": _update_cluster(cluster, storage)}

    # No cluster found -> create new
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


def _transform_cluster(tag, storage, embedding_model):
    if "tag_cluster_id" in tag:
        tag_cluster_table = storage.get_table("tag_clusters")
        cluster = tag_cluster_table.get(doc_id=int(tag["tag_cluster_id"]))
        output = {"cluster": _update_cluster(cluster, storage)}
    else:
        output = _assign_cluster_to(tag, storage, embedding_model)

    for _, v in output.items():
        if isinstance(v, dict) and "doc_id" in v:
            storage.update(v["table_name"], v)
        else:
            storage.save(v["table_name"], v)
    return output


def execute(flow):
    """Cluster similar tags based on embeddings."""
    logger.info("Clustering tags...")
    step_name = "cluster_tags"

    # Init metrics
    flow.metrics.setdefault("step_start_times", {})[step_name] = time.time()
    flow.errors.setdefault(step_name, [])
    flow.prediction_times.setdefault(step_name, [])

    storage = TTDStorage(flow.config.get("db_path"))
    flow.tag_embedding_spec_name = "tag_embedding_spec"
    tag_embedding_spec = load_model_spec(flow.tag_embedding_spec_name)

    flow.clusters = []

    for idx, tag in enumerate(flow.tags):
        try:
            start_time = time.time()

            logger.info(f"Processing tag {idx+1}/{len(flow.tags)}: {tag['name']}")
            result = _transform_cluster(tag, storage, tag_embedding_spec._loaded_model)

            duration = time.time() - start_time
            flow.prediction_times[step_name].append(duration)

            if result and "cluster" in result:
                flow.clusters.append(result["cluster"])

            logger.info(f"✅ Updated/created cluster for tag {tag['name']} "
                        f"(took {duration:.4f}s)")

        except Exception as e:
            logger.error(f"❌ Error clustering tag {idx}: {str(e)}")
            flow.errors[step_name].append({
                "index": idx,
                "error_message": str(e),
                "tag_name": tag.get("name", None)
            })
            flow.prediction_times[step_name].append(0.0)

    # Finalize metrics
    total_time = time.time() - flow.metrics["step_start_times"][step_name]
    flow.metrics.setdefault("processing_times", {})[step_name] = total_time
    flow.metrics.setdefault("avg_prediction_times", {})[step_name] = (
        sum(flow.prediction_times[step_name]) / len(flow.prediction_times[step_name])
        if flow.prediction_times[step_name] else 0.0
    )

    count_clusters = len(flow.clusters)
    avg_time = flow.metrics["avg_prediction_times"][step_name]
    error_count = len(flow.errors[step_name])

    logger.info(
        f"✅ Step {step_name} completed in {total_time:.2f}s, "
        f"{count_clusters} clusters created "
        f"(avg clustering time: {avg_time:.4f}s, errors: {error_count})."
    )
