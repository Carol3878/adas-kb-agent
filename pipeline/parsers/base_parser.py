from abc import ABC, abstractmethod


class ParsedResult:
    """所有parser统一返回这个结构,下游不用关心具体是哪种文件格式解析出来的"""

    def __init__(self, raw_text: str = "", structured_records: list[dict] | None = None,
                 heading_chunks: list[dict] | None = None):
        self.raw_text = raw_text
        # 表格类文件解析出的行记录(Excel/CSV/DBC/CK schema用这个)
        self.structured_records = structured_records or []
        # 文本类文件按标题路径切出的段落(Word/PDF用这个)
        self.heading_chunks = heading_chunks or []


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> ParsedResult:
        ...

    @abstractmethod
    def supports(self, file_path: str) -> bool:
        ...
