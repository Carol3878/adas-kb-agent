"""
【SQL生成逻辑现在能写完,但execute_kpi_calculation需要真实CK连接才能跑】
"""

import clickhouse_connect

from config.settings import CK_QUERY_CONFIG
from kb.modules.m3_business_rules import lookup_rule
from kb.modules.m4_routing_config import lookup_routing
from kb.modules.m2_db_schema import get_table_schema


def build_kpi_query_context(kpi_name: str, car_model: str, software_version: str) -> dict:
    """组装Agent生成SQL需要的全部上下文,这一步不需要CK连接,现在就能写完测试"""
    rule = lookup_rule(kpi_name)
    routing = lookup_routing(car_model, software_version)
    if not rule or not routing:
        return {"error": "未找到对应的KPI定义或车型版本路由,请先确认"}

    schema = get_table_schema(routing["ck_table_name"])
    return {"rule": rule, "routing": routing, "schema": schema}


def execute_readonly_query(sql: str) -> dict:
    """【需要真实CK连接】只读执行,带超时和行数限制"""
    client = clickhouse_connect.get_client(
        host=CK_QUERY_CONFIG["host"],
        username=CK_QUERY_CONFIG["user"],
        password=CK_QUERY_CONFIG["password"],
    )
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("只允许SELECT查询")

    result = client.query(sql, settings={"max_execution_time": CK_QUERY_CONFIG["query_timeout_seconds"]})
    return {"columns": result.column_names, "rows": result.result_rows[:CK_QUERY_CONFIG["max_rows"]]}
