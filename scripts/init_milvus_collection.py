"""
【需要真实Milvus endpoint才能执行,现在先把schema定义写好】
跑法: python scripts/init_milvus_collection.py
"""

from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection

from config.settings import MILVUS_CONFIG, EMBED_DIM


def main():
    connections.connect(host=MILVUS_CONFIG["host"], port=MILVUS_CONFIG["port"])

    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=EMBED_DIM),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
        FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="doc_category", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="is_active", dtype=DataType.BOOL),
    ]
    schema = CollectionSchema(fields, description="RAG向量库-模块五")

    collection = Collection(MILVUS_CONFIG["collection_name"], schema)
    collection.create_index(
        field_name="vector",
        index_params={"index_type": "HNSW", "metric_type": "COSINE",
                      "params": {"M": 16, "efConstruction": 200}},
    )
    print(f"Milvus collection '{MILVUS_CONFIG['collection_name']}' 创建完成")


if __name__ == "__main__":
    main()
