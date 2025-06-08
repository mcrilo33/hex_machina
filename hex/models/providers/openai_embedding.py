import json
from pathlib import Path
from typing import Optional, Tuple, List
from sklearn.metrics.pairwise import cosine_similarity
from pydantic import BaseModel
from openai import OpenAI
import numpy as np

from hex.utils.hash import sha256_key


def compute_tag_list_similarity(tags1: List[str],
                                tags2: List[str],
                                embedding_model) -> float:
    """
    Compute the average maximum cosine similarity between two tag lists
    using an OpenAIEmbedding model.

    Args:
        tags1 (List[str]): First list of tags (ground-truth).
        tags2 (List[str]): Second list of tags (predicted).
        embedding_model: An embedding model instance with `.predict()` method.

    Returns:
        float: Average of maximum cosine similarities.
    """
    if not tags1 or not tags2:
        return 0.0

    # Get embeddings for each tag individually
    embeddings1 = []
    embeddings2 = []

    for tag in tags1:
        result = embedding_model.predict(tag)
        embeddings1.append(result["output"])

    for tag in tags2:
        result = embedding_model.predict(tag)
        embeddings2.append(result["output"])

    embeddings1 = np.vstack(embeddings1)  # Shape: (len(tags1), embedding_dim)
    embeddings2 = np.vstack(embeddings2)  # Shape: (len(tags2), embedding_dim)

    # Compute cosine similarity matrix
    # Shape: (len(tags2), len(tags1))
    sim_matrix = cosine_similarity(embeddings2, embeddings1)

    # Take the maximum similarity for each tag2
    max_similarities = sim_matrix.max(axis=1)  # Shape: (len(tags2),)

    # Return the average
    return float(max_similarities.mean())


class EmbeddingMatrixCache:
    """
    A class to manage an embedding matrix cache.
    This class is used to store embeddings and their corresponding keys.
    """
    def __init__(self, dir_path: str, embedding_dim: int = 1536):
        self.dir = Path(dir_path)
        self.emb_path = self.dir / "embeddings.npy"
        self.keys_path = self.dir / "keys.json"
        self.meta_path = self.dir / "metadata.jsonl"
        self.embedding_dim = embedding_dim

        self._load()

    def _load(self):
        if self.emb_path.exists():
            self.embeddings = np.load(self.emb_path)
        else:
            self.embeddings = np.empty((0, self.embedding_dim))

        self.keys = json.load(
            open(self.keys_path, encoding='utf-8')
        ) if self.keys_path.exists() else []
        self.metadata = [
            json.loads(line) for line in open(
                self.meta_path, encoding='utf-8'
            )
        ] if self.meta_path.exists() else []

    def add(self, input_text: str, embedding: list, meta: dict):
        key = sha256_key(input_text)

        if key in self.keys:
            return  # Skip duplicate

        self.embeddings = np.vstack([self.embeddings, embedding])
        self.keys.append(key)
        self.metadata.append(meta)

        self._persist()

    def get_embedding(self, input_text: str) -> Optional[Tuple[np.ndarray, dict]]:
        key = sha256_key(input_text)
        if key not in self.keys:
            return None
        idx = self.keys.index(key)
        return self.embeddings[idx], self.metadata[idx]

    def _persist(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        np.save(self.emb_path, self.embeddings)
        with open(self.keys_path, "w", encoding='utf-8') as f:
            json.dump(self.keys, f)
        with open(self.meta_path, "w", encoding='utf-8') as f:
            for meta in self.metadata:
                f.write(json.dumps(meta) + "\n")


DEFAULT_EMBED_DIMS = {
    "text-embedding-ada-002": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


class OpenAIEmbedding():
    """ A class to represent an OpenAI embedding model. """
    def __init__(self, config: BaseModel):
        self.client = OpenAI(api_key=config.api_key)
        dim = DEFAULT_EMBED_DIMS.get(config.model_name, 3072)
        dim = config.dimensions if hasattr(config, "dimensions") else dim
        self.cache = EmbeddingMatrixCache(config.matrix_cache_dir, embedding_dim=dim)
        self.model_name = config.model_name

        embeddings_params = {}
        for k in ["dimensions"]:
            embeddings_params[k] = getattr(config, k)
        self.embeddings_params = embeddings_params

    def predict(self, input_text: str) -> dict:
        cached = self.cache.get_embedding(input_text)
        if cached:
            embedding, metadata = cached
            return {
                "output": embedding,
                "metadata": metadata
            }

        # Make API call
        response = self.client.embeddings.create(
            input=input_text,
            model=self.model_name,
            **self.embeddings_params
        )

        embedding = response.data[0].embedding
        metadata = {
            "model_name": response.model,
            "object": response.object,
            "usage": dict(response.usage) if hasattr(response, "usage") else {},
        }

        self.cache.add(input_text, embedding, metadata)

        return {
            "output": embedding,
            "metadata": metadata
        }
