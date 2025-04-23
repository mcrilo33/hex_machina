from ttd.models.providers.openai_model import OpenAIModel
from ttd.models.providers.openai_embedding import OpenAIEmbedding
from ttd.models.base_spec import ModelSpec


def load_model_from_spec(model_spec: ModelSpec):
    """
    Load the model instance based on the given ModelSpec.

    Args:
        model_spec (ModelSpec): A validated model specification.

    Returns:
        object: The model instance (e.g., OpenAIModel, HuggingFaceModel, etc.)

    Raises:
        NotImplementedError: If no compatible provider is found in config.
    """
    if model_spec.provider=="openai":
        return OpenAIModel(model_spec.config)

    elif model_spec.provider=="openai_embedding":
        return OpenAIEmbedding(model_spec.config)

    raise NotImplementedError(
        f"No model provider found for config: {list(model_spec.config.keys())}"
    )