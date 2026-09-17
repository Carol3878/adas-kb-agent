from kb.storage.postgres_client import get_pg_connection


def register_vehicle_route(car_model: str, version_range: list[str],
                             dbc_file_name: str, ck_table_name: str, es_index_name: str = ""):
    """新车型/新版本上线时,项目管理人工登记调用这个"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO vehicle_routing
            (car_model, version_min, version_max, dbc_file_name, ck_table_name, es_index_name)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (car_model, version_range[0], version_range[1], dbc_file_name, ck_table_name, es_index_name),
    )
    conn.commit()


def lookup_routing(car_model: str, software_version: str) -> dict | None:
    """Agent检索链路第一步:定位该查哪张CK表"""
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM vehicle_routing
        WHERE car_model = %s AND %s BETWEEN version_min AND version_max
        LIMIT 1
        """,
        (car_model, software_version),
    )
    return cur.fetchone()
