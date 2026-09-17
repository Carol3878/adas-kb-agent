from kb.storage.postgres_client import get_pg_connection


def upsert_signal(record: dict, source: str = "dbc_parser"):
    """record来自dbc_parser的解析结果或LLM抽取的候选(带confidence字段)"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO signal_dictionary
            (standard_name, dbc_message_name, dbc_signal_name, unit,
             valid_min, valid_max, ck_column_name, description, source, review_status)
        VALUES (%(standard_name)s, %(dbc_message_name)s, %(dbc_signal_name)s, %(unit)s,
                %(valid_min)s, %(valid_max)s, %(ck_column_name)s, %(description)s,
                %(source)s, %(review_status)s)
        ON CONFLICT (dbc_message_name, dbc_signal_name) DO UPDATE
            SET unit = EXCLUDED.unit, valid_min = EXCLUDED.valid_min,
                valid_max = EXCLUDED.valid_max
        """,
        {
            "standard_name": record.get("standard_name", record.get("dbc_signal_name")),
            "dbc_message_name": record.get("dbc_message_name"),
            "dbc_signal_name": record.get("dbc_signal_name"),
            "unit": record.get("unit"),
            "valid_min": record.get("min_value"),
            "valid_max": record.get("max_value"),
            "ck_column_name": record.get("ck_column_name"),
            "description": record.get("description"),
            "source": source,
            "review_status": "auto_from_dbc" if source == "dbc_parser" else "needs_review",
        },
    )
    conn.commit()


def lookup_signal(query: str) -> dict | None:
    """给Agent用:把自然语言词翻译成真实字段名"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM signal_dictionary
        WHERE standard_name ILIKE %s
           OR %s = ANY(cn_aliases)
           OR dbc_signal_name ILIKE %s
        LIMIT 1
        """,
        (f"%{query}%", query, f"%{query}%"),
    )
    return cur.fetchone()
