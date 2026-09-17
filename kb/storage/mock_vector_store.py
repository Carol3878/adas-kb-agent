"""
没有Milvus实例时用这个。用最朴素的方式算余弦相似度,
数据量小(开发阶段几百条chunk)完全够用,能验证整条检索链路逻辑对不对。
不要在生产环境用这个,只用于本地开发和单元测试。
"""

import math

from .vector_store_base import VectorStoreBase


class MockVectorStore(VectorStoreBase):
    def __init__(self):
        self._data: dict[str, dict] = {}

    def upsert(self, chunk_id, vector, text, metadata):
        self._data[chunk_id] = {"vector": vector, "text": text, "metadata": metadata}

    def search(self, query_vector, top_k=20, filters=None):
        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(y * y for y in b))
            return dot / (norm_a * norm_b + 1e-8)

        candidates = []
        for chunk_id, item in self._data.items():
            if filters:
                if any(item["metadata"].get(k) != v for k, v in filters.items()):
                    continue
            score = cosine(query_vector, item["vector"])
            candidates.append({
                "chunk_id": chunk_id, "text": item["text"],
                "metadata": item["metadata"], "score": score,
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]
