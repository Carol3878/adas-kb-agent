import hashlib

from pipeline.parsers.excel_parser import ExcelParser
from pipeline.parsers.docx_parser import DocxParser
from pipeline.parsers.dbc_parser import DbcParser
from pipeline.classifiers.intent_classifier import (
    classify_by_format, extract_regulation_meta, scan_chunk_for_extraction_hints,
)
from pipeline.extractors.chunk_extractor import chunk_heading_sections
from pipeline.extractors.rule_extractor import extract_and_save_rules
from pipeline.extractors.signal_extractor import extract_and_save_signals
from kb.modules.m5_rag_vector import store_chunk
from kb.modules.m6_regulation_index import save_regulation
from kb.modules.m1_signal_dict import upsert_signal

PARSERS = [ExcelParser(), DocxParser(), DbcParser()]


def route_document(file_path: str, doc_name: str, doc_category: str = "需求spec"):
    """
    整条链路的入口。这个函数不依赖真实LLM/Milvus也能跑完整流程——
    用mock后端时,向量会写入内存假存储、抽取结果永远是空列表,
    但"文件有没有被正确解析、路由逻辑对不对"这件事,现在就能验证。
    """
    content_form = classify_by_format(file_path)
    doc_hash = hashlib.md5(open(file_path, "rb").read()).hexdigest()

    if content_form == "DBC协议":
        parser = DbcParser()
        result = parser.parse(file_path)
        for record in result.structured_records:
            upsert_signal(record, source="dbc_file")
        return {"routed_to": "signal_dictionary", "count": len(result.structured_records)}

    if content_form == "表格矩阵":
        parser = ExcelParser()
        result = parser.parse(file_path)
        # 表头具体路由到哪张结构化表,由更细的table_header_classifier判断,
        # 这里先简化处理,实际项目里这一步要接一个表头识别函数
        return {"routed_to": "kpi_registry(待表头识别细化)", "count": len(result.structured_records)}

    # 纯文本路径
    reg_meta = extract_regulation_meta(doc_name)
    parser = DocxParser()
    result = parser.parse(file_path)
    chunks = chunk_heading_sections(result.heading_chunks)

    signal_hits, rule_hits = 0, 0
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_hash}_{i}"
        store_chunk(chunk_id, chunk["text"], metadata={
            "doc_name": doc_name, "doc_category": doc_category,
            "heading_path": chunk["heading_path"], "is_active": True,
        })

        hints = scan_chunk_for_extraction_hints(chunk["text"])
        if hints["hit_signal_list"]:
            signal_hits += extract_and_save_signals(chunk["text"], doc_name)
        if hints["hit_kpi_rule"]:
            rule_hits += extract_and_save_rules(chunk["text"], doc_name)

    if reg_meta:
        save_regulation(reg_meta, applicable_level="未分类",
                         source_chunk_ids=[f"{doc_hash}_{i}" for i in range(len(chunks))])

    return {
        "routed_to": "rag_vector_store",
        "chunk_count": len(chunks),
        "signal_extraction_hits": signal_hits,
        "rule_extraction_hits": rule_hits,
        "regulation_detected": reg_meta is not None,
    }
