"""
【修改说明】这是对原dispatcher.py的重写,主要加了这几件事:
1. 落对象存储留底(A区①)
2. 双层查重,查到重复直接返回DUPLICATE,不再处理(A区①)
3. 用documents表维护状态机,每一步都更新状态(贯穿全流程)
4. 分类改成两次时机:格式路由阶段先preliminary,拿到中间态内容后走confirm(C区⑤)
5. 低置信度分类结果推进review_queue,不再是"分类完就算完"(C区⑤)
6. store_chunk现在需要doc_id参数,对应SQL权威源那次重写
"""

import hashlib

from pipeline.parsers.excel_parser import ExcelParser
from pipeline.parsers.docx_parser import DocxParser
from pipeline.parsers.dbc_parser import DbcParser
from pipeline.classifiers.intent_classifier import (
    classify_by_format, extract_regulation_meta, scan_chunk_for_extraction_hints,
    resolve_document_category,
)
from pipeline.extractors.chunk_extractor import chunk_heading_sections
from pipeline.extractors.rule_extractor import extract_and_save_rules
from pipeline.extractors.signal_extractor import extract_and_save_signals
from pipeline.dedup import compute_raw_hash, compute_normalized_text_hash, check_duplicate
from kb.modules.m5_rag_vector import store_chunk
from kb.modules.m6_regulation_index import save_regulation
from kb.modules.m1_signal_dict import upsert_signal
from kb.modules.m0_ingest_state import create_document_record, update_status
from kb.modules.review_queue import push_to_review_queue
from kb.storage.local_object_store import get_object_store

PARSERS = [ExcelParser(), DocxParser(), DbcParser()]

CONFIDENCE_THRESHOLD = 0.6  # 低于这个值,分类结果不直接采用,推进人工审核队列


def route_document(file_path: str, doc_name: str):
    """整条链路的入口,对应图里A->B->C->D四个分区依次执行"""

    # ===== A区:受理 =====
    raw_hash = compute_raw_hash(file_path)
    existing = check_duplicate(raw_hash)
    if existing:
        return {"status": "DUPLICATE", "match_level": existing["match_level"]}

    object_key = f"raw/{raw_hash}_{doc_name}"
    get_object_store().put_object(object_key, file_path)

    doc_id = create_document_record(doc_name, raw_hash, object_key)

    # 预分类(便宜、不调LLM),挂个候选身份
    preliminary = resolve_document_category(doc_name, preview_text="", stage="preliminary")

    content_form = classify_by_format(file_path)

    if content_form == "DBC协议":
        update_status(doc_id, "PARSING")
        result = DbcParser().parse(file_path)
        for record in result.structured_records:
            upsert_signal(record, source="dbc_file")
        update_status(doc_id, "INDEXED")
        return {"doc_id": doc_id, "routed_to": "signal_dictionary", "count": len(result.structured_records)}

    if content_form == "表格矩阵":
        update_status(doc_id, "PARSING")
        result = ExcelParser().parse(file_path)
        update_status(doc_id, "INDEXED")
        return {"doc_id": doc_id, "routed_to": "kpi_registry(待表头识别细化)",
                "count": len(result.structured_records)}

    # ===== B区:解析 =====
    update_status(doc_id, "PARSING")
    result = DocxParser().parse(file_path)
    text_hash = compute_normalized_text_hash(result.raw_text)

    # 用文本指纹再查一次重(第二层查重,发现"格式不同但内容相同")
    dup_check = check_duplicate(raw_hash, text_hash)
    if dup_check:
        update_status(doc_id, "DUPLICATE")
        return {"doc_id": doc_id, "status": "DUPLICATE", "match_level": dup_check["match_level"]}

    # ===== C区:判定 =====
    update_status(doc_id, "CLASSIFY", text_hash=text_hash)
    confirmed = resolve_document_category(
        doc_name, preview_text=result.raw_text[:1000], stage="confirm",
    )
    doc_category = confirmed["doc_category"]

    if confirmed.get("confidence", 0) < CONFIDENCE_THRESHOLD:
        update_status(doc_id, "NEEDS_REVIEW")
        push_to_review_queue(doc_id, reason="分类置信度低", review_type="classification",
                              payload={"preliminary": preliminary, "confirmed": confirmed})
        return {"doc_id": doc_id, "status": "NEEDS_REVIEW", "reason": "分类置信度低"}

    # ===== D区:入库 =====
    update_status(doc_id, "CHUNKING")
    reg_meta = extract_regulation_meta(doc_name)
    chunks = chunk_heading_sections(result.heading_chunks)

    update_status(doc_id, "EMBEDDING")
    signal_hits, rule_hits = 0, 0
    for i, chunk in enumerate(chunks):
        chunk_id = f"{raw_hash}_{i}"
        store_chunk(chunk_id, doc_id, chunk["text"], metadata={
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
                         source_chunk_ids=[f"{raw_hash}_{i}" for i in range(len(chunks))])

    update_status(doc_id, "INDEXED")

    return {
        "doc_id": doc_id,
        "status": "INDEXED",
        "doc_category": doc_category,
        "classification_source": confirmed.get("source"),
        "chunk_count": len(chunks),
        "signal_extraction_hits": signal_hits,
        "rule_extraction_hits": rule_hits,
        "regulation_detected": reg_meta is not None,
    }
