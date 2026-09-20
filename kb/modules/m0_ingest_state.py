"""
状态机: PENDING -> PARSING -> CLASSIFY -> CHUNKING -> EMBEDDING -> INDEXED
分支状态: FAILED / DUPLICATE / NEEDS_REVIEW
对应documents表,一份文档一行记录,任何时候能查"现在卡在哪一步"。
"""

from kb.storage.postgres_client import get_pg_connection

VALID_STATES = ["PENDING", "PARSING", "CLASSIFY", "CHUNKING", "EMBEDDING",
                 "INDEXED", "FAILED", "DUPLICATE", "NEEDS_REVIEW"]


def create_document_record(doc_name: str, raw_hash: str, object_key: str, version: int = 1) -> int:
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO documents (doc_name, raw_hash, object_key, version, status)
        VALUES (%s, %s, %s, %s, 'PENDING')
        RETURNING id
        """,
        (doc_name, raw_hash, object_key, version),
    )
    doc_id = cur.fetchone()["id"]
    conn.commit()
    return doc_id


def update_status(doc_id: int, status: str, text_hash: str | None = None, error: str | None = None):
    assert status in VALID_STATES, f"非法状态: {status}"
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE documents
        SET status = %s, text_hash = COALESCE(%s, text_hash),
            last_error = %s, updated_at = now()
        WHERE id = %s
        """,
        (status, text_hash, error, doc_id),
    )
    conn.commit()


def get_document_status(doc_id: int) -> dict | None:
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
    return cur.fetchone()


def list_by_status(status: str) -> list[dict]:
    """运维排查用:查所有卡在某个状态的文档,比如查所有FAILED的"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE status = %s", (status,))
    return cur.fetchall()
