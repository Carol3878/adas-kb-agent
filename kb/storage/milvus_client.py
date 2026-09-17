"""
【需要真实Milvus endpoint才能运行,但代码现在就可以写完】

实现和MockVectorStore一样的接口,所以kb/modules/m5_rag_vector.py
不需要知道自己在跟谁对话,由 get_vector_store() 统一分发。
"""

from pymilvus import connections, Collection

from config.settings import MILVUS_CONFIG
from .vector_store_base import VectorStoreBase


class MilvusVectorStore(VectorStoreBase):
    def __init__(self):
        connections.connect(host=MILVUS_CONFIG["host"], port=MILVUS_CONFIG["port"])
        self.collection = Collection(MILVUS_CONFIG["collection_name"])

    def upsert(self, chunk_id, vector, text, metadata):
        self.collection.upsert([{
            "chunk_id": chunk_id,
            "vector": vector,
            "text": text,
            "doc_name": metadata.get("doc_name", ""),
            "doc_category": metadata.get("doc_category", ""),
            "is_active": metadata.get("is_active", True),
        }])

    def search(self, query_vector, top_k=20, filters=None):
        expr = None
        if filters:
            expr = " and ".join(f'{k} == "{v}"' for k, v in filters.items())

        results = self.collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"ef": 64}},
            limit=top_k,
            expr=expr,
            output_fields=["chunk_id", "text", "doc_name", "doc_category"],
        )
        return [
            {
                "chunk_id": hit.entity.get("chunk_id"),
                "text": hit.entity.get("text"),
                "metadata": {
                    "doc_name": hit.entity.get("doc_name"),
                    "doc_category": hit.entity.get("doc_category"),
                },
                "score": hit.score,
            }
            for hit in results[0]
        ]


def get_vector_store() -> VectorStoreBase:
    from config.settings import VECTOR_BACKEND
    if VECTOR_BACKEND == "real":
        return MilvusVectorStore()
    from .mock_vector_store import MockVectorStore
    return MockVectorStore()
