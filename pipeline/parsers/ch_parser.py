"""
【需要真实ClickHouse连接才能实际运行,但代码现在就可以写完】

这个parser不解析文件,而是定期连接CK执行元数据查询,
把结果转换成和其他parser一致的ParsedResult,交给下游统一处理。
"""

import clickhouse_connect

from config.settings import CK_INTROSPECT_CONFIG
from .base_parser import BaseParser, ParsedResult


class ClickHouseSchemaParser(BaseParser):
    def supports(self, file_path: str) -> bool:
        # 这个parser不是按文件触发的,而是定时任务主动调用parse()
        return False

    def parse(self, file_path: str = "") -> ParsedResult:
        client = clickhouse_connect.get_client(
            host=CK_INTROSPECT_CONFIG["host"],
            username=CK_INTROSPECT_CONFIG["user"],
            password=CK_INTROSPECT_CONFIG["password"],
        )

        rows = client.query(
            """
            SELECT database, table, name, type, comment,
                   is_in_partition_key, is_in_sorting_key, is_in_primary_key
            FROM system.columns
            WHERE database NOT IN ('system', 'information_schema')
            """
        ).result_rows

        records = [
            {
                "database_name": r[0],
                "table_name": r[1],
                "column_name": r[2],
                "data_type": r[3],
                "comment": r[4],
                "is_partition_key": bool(r[5]),
                "is_sorting_key": bool(r[6]),
                "is_primary_key": bool(r[7]),
            }
            for r in rows
        ]
        return ParsedResult(structured_records=records)
