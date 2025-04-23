import json
import copy
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List
from openai import OpenAI
from sentence_transformers import SentenceTransformer, util
from ttd.utils.hash_utils import sha256_key
from ttd.models.base_model import BaseModel

def compute_tag_list_similarity(tags1: List[str], tags2: List[str], embedding_model) -> float:
    """
    Compute the average maximum cosine similarity between tags in two lists.
    
    Args:
        tags1 (List[str]): First list of tags (e.g., ground-truth).
        tags2 (List[str]): Second list of tags (e.g., predicted).
        embedding_model: A sentence embedding model with .encode() method.
    
    Returns:
        float: Average of maximum cosine similarities per tag in tags2.
    """
    if not tags1 or not tags2:
        return 0.0

    # Embed both tag lists
    vecs1 = embedding_model.encode(tags1, convert_to_tensor=True)
    vecs2 = embedding_model.encode(tags2, convert_to_tensor=True)

    # Compute cosine similarity matrix
    sim_matrix = util.pytorch_cos_sim(vecs2, vecs1)  # shape: [len(tags2), len(tags1)]

    # For each tag in tags2, take the max similarity to any tag in tags1
    max_similarities = sim_matrix.max(dim=1).values

    # Average over all
    return float(max_similarities.mean())


class EmbeddingMatrixCache:
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

        self.keys = json.load(open(self.keys_path)) if self.keys_path.exists() else []
        self.metadata = [
            json.loads(line) for line in open(self.meta_path)
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
        with open(self.keys_path, "w") as f:
            json.dump(self.keys, f)
        with open(self.meta_path, "w") as f:
            for meta in self.metadata:
                f.write(json.dumps(meta) + "\n")       


DEFAULT_EMBED_DIMS = {
    "text-embedding-ada-002": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}

class OpenAIEmbedding(BaseModel):
    def __init__(self, config: dict):
        super().__init__(config)
        for key in ["api_key", "model_name", "matrix_cache_dir"]:
            if key not in config:
                raise ValueError(f"Missing required key: {key}")
        api_key = config["api_key"]
        self.client = OpenAI(api_key=api_key)
        self.model_name = config["model_name"]
        dim = DEFAULT_EMBED_DIMS.get(config["model_name"], 1536)
        dim = config["dimensions"] if "dimensions" in config else dim
        self.cache = EmbeddingMatrixCache(config["matrix_cache_dir"], embedding_dim=dim)

        embeddings_params = copy.deepcopy(config)
        for k in ["api_key", "model_name"]:
            del embeddings_params[k]
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
            model=self.model_name
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