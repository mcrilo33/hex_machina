# ttd/models/registry.py

import importlib.util
from pathlib import Path
from ttd.models.base_spec import ModelSpec
from ttd.models.loader import load_model_from_spec
from ttd.storage.ttd_storage import TTDStorage
from ttd.utils.git import get_git_metadata
from ttd.models.base_spec import validate_input_prompt_compatibility


SPEC_DIR = Path(__file__).parent / "specs"
MODEL_SPECS = {}

def load_model_specs_from_directory():
    for py_file in SPEC_DIR.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        module_name = f"ttd.models.specs.{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if not spec or not spec.loader:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, ModelSpec):
                MODEL_SPECS[attr.name] = attr

# Load specs at import
load_model_specs_from_directory()

def sync_model_spec_to_registry(model_spec: ModelSpec, storage: TTDStorage) -> str:
    """
    Ensure a ModelSpec is registered in the model registry table.
    This enables tracking of model configurations, schemas, and versioning.

    If the model (name + version) already exists, it is reused.
    Otherwise, it is added to the registry.
    """
    existing = storage.get_by_field("models", "name", model_spec.name)

    if existing and existing.get("version") == model_spec.version:
        return existing["doc_id"]

    registry_entry = model_spec.dict(exclude={"_runtime_model"})
    registry_entry["table_name"] = "models"
    registry_entry["git_metadata"] = get_git_metadata()
    registry_entry["created_at"] = registry_entry["last_updated"] = model_spec.config.get(
        "timestamp", None
    )

    doc_id = storage.save("models", registry_entry)
    return doc_id

def load_model_spec(name: str, storage: TTDStorage) -> ModelSpec:
    """
    Load a ModelSpec from the model registry.

    Args:
        name (str): The registered name of the model.

    Returns:
        ModelSpec: Instantiated model spec object.

    Raises:
        ValueError: If model name is not registered.
    """
    if name not in MODEL_SPECS:
        raise ValueError(f"Model named '{name}' not found in registry.")

    spec = MODEL_SPECS[name]

    # Ensure input/output compatibility
    validate_input_prompt_compatibility(spec)

    # Sync spec to database for tracking/versioning
    model_doc_id = sync_model_spec_to_registry(spec, storage)
    spec.model_id = model_doc_id

    # Attach loaded model instance
    spec._loaded_model = load_model_from_spec(spec)

    return spec