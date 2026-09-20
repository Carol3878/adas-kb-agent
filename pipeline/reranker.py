"""
之前只在config/settings.py里配置了RERANK_MODEL_NAME和RERANK_TOP_K,
但从来没写这个文件——rag_search_tool.py一直是直接返回粗排结果,
没有真正过rerank。这个文件补齐这个缺口。
"""

from sentence_transformers import CrossEncoder

from config.settings import RERANK_MODEL_NAME, RERANK_TOP_K

_rerank_model = None


def get_rerank_model():
    global _rerank_model
    if _rerank_model is None:
        _rerank_model = CrossEncoder(RERANK_MODEL_NAME)
    return _rerank_model


def rerank(query: str, candidates: list[dict], top_k: int = RERANK_TOP_K) -> list[dict]:
    """
    candidates是retrieve()粗排召回的结果(比如top20),
    这里用更精细的cross-encoder模型重新算相关性,取真正最相关的前几条。
    """
    if not candidates:
        return []

    pairs = [(query, c["text"]) for c in candidates]
    scores = get_rerank_model().predict(pairs)

    for c, score in zip(candidates, scores):
        c["rerank_score"] = float(score)

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates[:top_k]
