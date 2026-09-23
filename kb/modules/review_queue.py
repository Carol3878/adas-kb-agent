"""
之前模块一/三的review_status只是"记录级别"的字段,查不到一个统一列表。
这个文件提供一个真正能查、能处理的NEEDS_REVIEW队列。
"""

from psycopg2.extras import Json

from kb.storage.postgres_client import get_pg_connection


def push_to_review_queue(doc_id: int, reason: str, review_type: str, payload: dict | None = None):
    """
    review_type: "classification"(分类置信度低) | "extraction"(抽取置信度低) | "dead_letter"(处理失败)

    【修复bug】payload是Python字典,但数据库里对应的review_queue.payload字段
    是JSONB类型,psycopg2不会自动把dict转成JSON格式,直接传会报
    "can't adapt type 'dict'"。要用psycopg2.extras.Json(...)包一层,
    告诉psycopg2"这个值请按JSON格式序列化后再写入"。
    """
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO review_queue (doc_id, reason, review_type, payload, status)
        VALUES (%s, %s, %s, %s, 'pending')
        """,
        (doc_id, reason, review_type, Json(payload) if payload is not None else None),
    )
    conn.commit()


def list_pending_reviews(review_type: str | None = None) -> list[dict]:
    conn = get_pg_connection()
    cur = conn.cursor()
    if review_type:
        cur.execute("SELECT * FROM review_queue WHERE status='pending' AND review_type=%s", (review_type,))
    else:
        cur.execute("SELECT * FROM review_queue WHERE status='pending'")
    return cur.fetchall()


def resolve_review(review_id: int, decision: str):
    """decision: "approved" | "rejected",人工看完之后调用"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("UPDATE review_queue SET status=%s, resolved_at=now() WHERE id=%s", (decision, review_id))
    conn.commit()
