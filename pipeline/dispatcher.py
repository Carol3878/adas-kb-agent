"""
【修改说明】这是对原dispatcher.py的重写,主要加了这几件事:
1. 落对象存储留底(A区①)
2. 双层查重,查到重复直接返回DUPLICATE,不再处理(A区①)
3. 用documents表维护状态机,每一步都更新状态(贯穿全流程)
4. 分类改成两次时机:格式路由阶段先preliminary,拿到中间态内容后走confirm(C区⑤)
5. 低置信度分类结果推进review_queue,不再是"分类完就算完"(C区⑤)
6. store_chunk现在需要doc_id参数,对应SQL权威源那次重写
"""
"""
【修改说明】这次改动:把原来route_document里B/C/D区那段处理逻辑
抽成了公共函数 _process_text_content,因为飞书文档也要走同样的
B(解析后处理)/C(判定)/D(入库)流程,只是A区(怎么拿到原始内容)不一样——
本地文件是读字节算hash,飞书文档是调API拿内容后对内容本身算hash。
抽出来之后,route_document(本地文件)和ingest_feishu_document(飞书链接)
两个入口共用同一段核心逻辑,不用维护两份重复代码。
"""

import hashlib

from pipeline.parsers.excel_parser import ExcelParser
from pipeline.parsers.docx_parser import DocxParser
from pipeline.parsers.dbc_parser import DbcParser
from pipeline.parsers.feishu_parser import FeishuParser
from pipeline.parsers.base_parser import ParsedResult
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

PARSERS = [ExcelParser(), DocxParser(), DbcParser(), FeishuParser()]

CONFIDENCE_THRESHOLD = 0.6


def route_document(file_path: str, doc_name: str):
    """本地文件入口,对应图里A->B->C->D四个分区依次执行"""

    # ===== A区:受理(本地文件版本,有原始字节可以算hash) =====
    raw_hash = compute_raw_hash(file_path)
    existing = check_duplicate(raw_hash)
    if existing:
        return {"status": "DUPLICATE", "match_level": existing["match_level"]}

    object_key = f"raw/{raw_hash}_{doc_name}"
    get_object_store().put_object(object_key, file_path)
    doc_id = create_document_record(doc_name, raw_hash, object_key)

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

    update_status(doc_id, "PARSING")
    result = DocxParser().parse(file_path)
    return _process_text_content(doc_id, doc_name, raw_hash, result, preliminary)


def ingest_feishu_document(doc_url: str, doc_name: str):
    """
    【新增】飞书文档入口,对应B区里"飞书API"这个数据源。
    跟route_document的区别只在A区:没有本地文件字节,
    改成先调API拿到内容,再对内容文本本身算hash来查重。
    B/C/D区逻辑跟本地文件完全共用_process_text_content。
    """
    parser = FeishuParser()
    result = parser.parse(doc_url)  # 这一步需要真实FEISHU_APP_ID/SECRET才能成功

    # 没有本地文件字节,改用内容文本算hash当作raw_hash
    raw_hash = hashlib.sha256(result.raw_text.encode("utf-8")).hexdigest()
    existing = check_duplicate(raw_hash)
    if existing:
        return {"status": "DUPLICATE", "match_level": existing["match_level"]}

    # 把飞书文档内容做一份文本快照存进对象存储,留底逻辑跟本地文件一致
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(result.raw_text)
        tmp_path = f.name
    object_key = f"raw/{raw_hash}_{doc_name}.txt"
    get_object_store().put_object(object_key, tmp_path)

    doc_id = create_document_record(doc_name, raw_hash, object_key)
    preliminary = resolve_document_category(doc_name, preview_text="", stage="preliminary")

    update_status(doc_id, "PARSING")
    return _process_text_content(doc_id, doc_name, raw_hash, result, preliminary)


def _process_text_content(doc_id: int, doc_name: str, raw_hash: str,
                            result: ParsedResult, preliminary: dict):
    """B(解析后处理)/C(判定)/D(入库)公共逻辑,本地文件和飞书文档共用这一段"""

    text_hash = compute_normalized_text_hash(result.raw_text)
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
