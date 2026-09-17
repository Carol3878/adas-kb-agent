from kb.storage.postgres_client import get_pg_connection


def save_draft_rule(record: dict, source_doc: str):
    """
    LLM抽取的候选先落草稿表,不管LLM_BACKEND是mock还是real都走这个函数,
    mock模式下extractor会返回空列表,不会有脏数据写进来,这个函数本身不用区分环境。
    """
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO business_rules_draft
            (record_type, name, natural_language_desc, logic_expression,
             required_signals, confidence, source_doc, review_status)
        VALUES (%(record_type)s, %(name)s, %(natural_language_desc)s, %(logic_expression)s,
                %(required_signals)s, %(confidence)s, %(source_doc)s, %(review_status)s)
        """,
        {
            **record,
            "source_doc": source_doc,
            "review_status": "needs_review" if record.get("confidence", 0) < 0.7 else "auto_approved_pending",
        },
    )
    conn.commit()


def promote_to_production(draft_id: int):
    """人工审核通过后,从草稿表转正到正式表"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO business_rules (record_type, name, natural_language_desc,
                                     logic_expression, required_signals, source_doc)
        SELECT record_type, name, natural_language_desc, logic_expression,
               required_signals, source_doc
        FROM business_rules_draft WHERE id = %s
        """,
        (draft_id,),
    )
    cur.execute("UPDATE business_rules_draft SET review_status = 'promoted' WHERE id = %s", (draft_id,))
    conn.commit()


def lookup_rule(name_query: str) -> dict | None:
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM business_rules WHERE name ILIKE %s LIMIT 1",
        (f"%{name_query}%",),
    )
    return cur.fetchone()
