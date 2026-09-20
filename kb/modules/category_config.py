"""
对应⑥策略路由:确定业务分类后,查这张配置表决定
用哪种chunker策略、进Milvus哪个集合、给哪个权限组。
以后新增一类文档或调整策略,改配置表就行,不用改代码。
"""

from kb.storage.postgres_client import get_pg_connection


def get_category_config(doc_category: str) -> dict | None:
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM category_config WHERE doc_category = %s", (doc_category,))
    return cur.fetchone()


def register_category_config(doc_category: str, chunk_strategy: str,
                               milvus_collection: str, permission_group: str):
    """初始化或更新一类文档的处理策略,通常是运维/开发手工调用,不是自动触发的"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO category_config (doc_category, chunk_strategy, milvus_collection, permission_group)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (doc_category) DO UPDATE
            SET chunk_strategy = EXCLUDED.chunk_strategy,
                milvus_collection = EXCLUDED.milvus_collection,
                permission_group = EXCLUDED.permission_group
        """,
        (doc_category, chunk_strategy, milvus_collection, permission_group),
    )
    conn.commit()
