from sentence_transformers import SentenceTransformer

from config.settings import EMBED_MODEL_NAME
from kb.storage.milvus_client import get_vector_store

_embed_model = None


def get_embed_model():
    """BGE-M3是开源本地模型,不需要API Key,首次运行会自动从HuggingFace下载权重"""
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


def store_chunk(chunk_id: str, text: str, metadata: dict):
    vector = get_embed_model().encode(text, normalize_embeddings=True).tolist()
    get_vector_store().upsert(chunk_id, vector, text, metadata)


def retrieve(query: str, top_k: int = 20, filters: dict | None = None) -> list[dict]:
    vector = get_embed_model().encode(query, normalize_embeddings=True).tolist()
    return get_vector_store().search(vector, top_k=top_k, filters=filters)
