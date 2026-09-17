import cantools

from .base_parser import BaseParser, ParsedResult


class DbcParser(BaseParser):
    """
    直接对CAN协议DBC文件做语法树解析,零LLM依赖、零外部账号依赖。
    这是整个项目里"确定性最高"的一个parser,现在就能写完并测试通过。
    """

    def supports(self, file_path: str) -> bool:
        return file_path.lower().endswith(".dbc")

    def parse(self, file_path: str) -> ParsedResult:
        db = cantools.database.load_file(file_path)

        records = []
        for message in db.messages:
            for signal in message.signals:
                records.append({
                    "dbc_message_name": message.name,
                    "dbc_signal_name": signal.name,
                    "message_id": message.frame_id,
                    "dlc": message.length,
                    "start_bit": signal.start,
                    "bit_length": signal.length,
                    "byte_order": signal.byte_order,
                    "factor": signal.scale,
                    "offset": signal.offset,
                    "unit": signal.unit,
                    "min_value": signal.minimum,
                    "max_value": signal.maximum,
                    "choices": dict(signal.choices) if signal.choices else None,
                })

        return ParsedResult(structured_records=records)
