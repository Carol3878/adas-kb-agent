from kb.storage.postgres_client import get_pg_connection


def save_regulation(meta: dict, applicable_level: str, source_chunk_ids: list[str]):
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO regulation_index
            (reg_number, reg_name, status, applicable_level, source_chunk_ids)
        VALUES (%(reg_number)s, %(reg_name)s, %(status)s, %(applicable_level)s, %(source_chunk_ids)s)
        ON CONFLICT (reg_number) DO UPDATE SET status = EXCLUDED.status
        """,
        {**meta, "applicable_level": applicable_level, "source_chunk_ids": source_chunk_ids},
    )
    conn.commit()


def list_regulations(status: str | None = None, applicable_level: str | None = None) -> list[dict]:
    """支持"列出所有现行L3法规"这类精确枚举查询,这是纯向量检索做不到的"""
    conn = get_pg_connection()
    cur = conn.cursor()
    query = "SELECT * FROM regulation_index WHERE 1=1"
    params = []
    if status:
        query += " AND status = %s"
        params.append(status)
    if applicable_level:
        query += " AND applicable_level = %s"
        params.append(applicable_level)
    cur.execute(query, params)
    return cur.fetchall()
