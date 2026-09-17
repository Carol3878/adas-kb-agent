import pandas as pd

from .base_parser import BaseParser, ParsedResult


class ExcelParser(BaseParser):
    """
    对应DATA需求Matrix / FOS需求Matrix 这类表格文件。
    直接按行转成Key-Value的字典记录,不做任何语义判断——
    "这张表更像KPI记录还是信号记录",这个判断留给classifiers层做,
    parser只负责忠实地把表格转成结构化数据,不掺杂业务逻辑。
    """

    def supports(self, file_path: str) -> bool:
        return file_path.lower().endswith((".xlsx", ".xls", ".csv"))

    def parse(self, file_path: str) -> ParsedResult:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df = df.dropna(how="all")  # 去掉全空行
        records = df.to_dict(orient="records")

        # 清洗:NaN转None,列名去空格,方便后续统一处理
        cleaned = []
        for row in records:
            cleaned.append({
                str(k).strip(): (None if pd.isna(v) else v)
                for k, v in row.items()
            })

        return ParsedResult(structured_records=cleaned)
