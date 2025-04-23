import os
from datetime import datetime
from ttd.storage.ttd_storage import TTDStorage
from ttd.pipelines import get_beta_pipeline
from ttd.utils.config import load_config, update_config
from pprint import pprint


def update_enrich_time():
    update_config({
        "last_enrich": datetime.utcnow().isoformat()
    })

def run_enricher_routine():
    config = load_config()
    persist = config.get("persist", False)
    db_path = os.path.abspath(config["db_path"])
    last_enrich_date = config.get("last_enrich")

    if last_enrich_date and persist:
        last_enrich_date = datetime.fromisoformat(last_enrich_date)

    # Initialize storage
    storage = TTDStorage(db_path)

    # Load the enrichment pipeline
    pipeline = get_beta_pipeline(storage=storage)

    # Run the pipeline
    run_summary = pipeline.run(persist=persist, params={"last_enrich_date": last_enrich_date})
    import ipdb; ipdb.set_trace()

    # Update enrichment timestamp if in persist mode
    if persist:
        update_enrich_time()

if __name__ == "__main__":
    run_enricher_routine()
