import os
from datetime import datetime
from ttd.storage.ttd_storage import TTDStorage
from ttd.enricher import get_alpha_pipeline
from ttd.config import load_config_and_dotenv, update_config

config = load_config_and_dotenv()
DB_PATH = os.path.abspath(config["db_path"])
LAST_ENRICH_DATE = config.get("last_enrich")
DEBUG = config.get("debug", False)

if LAST_ENRICH_DATE and not DEBUG:
    LAST_ENRICH_DATE = datetime.fromisoformat(LAST_ENRICH_DATE)

def update_enrich_time():
    update_config({
        "last_enrich": datetime.isoformat(datetime.now())
    })

def run_enricher_routine():
    # Initialize storage service
    storage = TTDStorage(DB_PATH)

    # Get the enrichment pipeline (you must define get_enrichment_pipeline somewhere)
    pipeline = get_alpha_pipeline(storage, debug=DEBUG)

    # Run the pipeline
    predictions = pipeline.run(save=False)

    # Update enrichment timestamp
    if not DEBUG:
        update_enrich_time()
    else:
        import ipdb; ipdb.set_trace()

if __name__ == "__main__":
    run_enricher_routine()