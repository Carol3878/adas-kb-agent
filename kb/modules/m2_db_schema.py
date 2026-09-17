from kb.storage.postgres_client import get_pg_connection
from pipeline.parsers.ch_parser import ClickHouseSchemaParser


def sync_schema_from_clickhouse():
    """
    【需要真实CK连接才能跑,但函数逻辑现在就能写完】
    建议做成定时任务(如每天凌晨),保证模块二和CK真实结构不会漂移。
    """
    parser = ClickHouseSchemaParser()
    result = parser.parse()

    conn = get_pg_connection()
    cur = conn.cursor()
    for record in result.structured_records:
        cur.execute(
            """
            INSERT INTO db_schema
                (database_name, table_name, column_name, data_type, comment,
                 is_partition_key, is_sorting_key, is_primary_key)
            VALUES (%(database_name)s, %(table_name)s, %(column_name)s, %(data_type)s,
                    %(comment)s, %(is_partition_key)s, %(is_sorting_key)s, %(is_primary_key)s)
            ON CONFLICT (database_name, table_name, column_name) DO UPDATE
                SET data_type = EXCLUDED.data_type, comment = EXCLUDED.comment
            """,
            record,
        )
    conn.commit()
    return len(result.structured_records)


def get_table_schema(table_name: str) -> list[dict]:
    """给Agent生成SQL用:拿到某张表的完整列定义"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM db_schema WHERE table_name = %s", (table_name,))
    return cur.fetchall()
