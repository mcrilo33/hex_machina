import importlib.util
from pathlib import Path

from hex.models.base_spec import ModelSpec


SPEC_DIR = Path(__file__).parent / "specs"
MODEL_SPECS = {}


def load_model_specs_from_directory():
    """
    Load all model specs from the specs directory.
    """
    for py_file in SPEC_DIR.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        module_name = f"hex.models.specs.{py_file.stem}"
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


def load_model_spec(name: str) -> ModelSpec:
    """ Load a ModelSpec from the model registry. """
    if name not in MODEL_SPECS:
        raise ValueError(f"Model named '{name}' not found in registry.")

    spec = MODEL_SPECS[name]
    spec.load_model()

    return spec
