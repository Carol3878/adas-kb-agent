"""
【修改说明】这是对原m5_rag_vector.py的重写。
原来的store_chunk只把文本存进了Milvus,没有独立的SQL权威源——
如果Milvus数据损坏或者要换向量库,没有地方能重新拿到原文重建索引。

现在改成对应⑨双写+回写的顺序:
1. 先写SQL的chunks表(这才是权威版本)
2. 再把向量upsert进Milvus
3. 回写chunks表的indexed字段为true
任何一步失败,chunks表里能看出indexed=false,后续可以重跑第2、3步补齐,
不需要重新解析原始文档。
"""

from sentence_transformers import SentenceTransformer

from config.settings import EMBED_MODEL_NAME
from kb.storage.milvus_client import get_vector_store
from kb.storage.postgres_client import get_pg_connection

_embed_model = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


def store_chunk(chunk_id: str, doc_id: int, text: str, metadata: dict):
    conn = get_pg_connection()
    cur = conn.cursor()

    # 第一步:SQL权威源先写成功
    cur.execute(
        """
        INSERT INTO chunks (chunk_id, doc_id, text, heading_path, doc_category, indexed)
        VALUES (%s, %s, %s, %s, %s, false)
        ON CONFLICT (chunk_id) DO UPDATE SET text = EXCLUDED.text, indexed = false
        """,
        (chunk_id, doc_id, text, metadata.get("heading_path"), metadata.get("doc_category")),
    )
    conn.commit()

    # 第二步:向量化并写入Milvus(或mock)
    vector = get_embed_model().encode(text, normalize_embeddings=True).tolist()
    get_vector_store().upsert(chunk_id, vector, text, metadata)

    # 第三步:回写INDEXED状态
    cur.execute("UPDATE chunks SET indexed = true WHERE chunk_id = %s", (chunk_id,))
    conn.commit()


def retrieve(query: str, top_k: int = 20, filters: dict | None = None) -> list[dict]:
    vector = get_embed_model().encode(query, normalize_embeddings=True).tolist()
    return get_vector_store().search(vector, top_k=top_k, filters=filters)


def rebuild_index_from_sql(doc_id: int | None = None):
    """
    灾难恢复用:Milvus数据丢了/换了新的向量库,从SQL的chunks表重新灌一遍。
    不传doc_id就是全量重建,传了就是只重建这一份文档的索引。
    """
    conn = get_pg_connection()
    cur = conn.cursor()
    if doc_id:
        cur.execute("SELECT * FROM chunks WHERE doc_id = %s", (doc_id,))
    else:
        cur.execute("SELECT * FROM chunks")

    rows = cur.fetchall()
    for row in rows:
        vector = get_embed_model().encode(row["text"], normalize_embeddings=True).tolist()
        get_vector_store().upsert(row["chunk_id"], vector, row["text"], {
            "doc_name": "", "doc_category": row["doc_category"],
            "heading_path": row["heading_path"], "is_active": True,
        })
        cur.execute("UPDATE chunks SET indexed = true WHERE chunk_id = %s", (row["chunk_id"],))
    conn.commit()
    return len(rows)
