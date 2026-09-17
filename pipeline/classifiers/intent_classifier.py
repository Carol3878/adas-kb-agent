import re

from config.settings import SIGNAL_LIST_HINTS, KPI_RULE_HINTS, REGULATION_PATTERN
from agent.llm_client import get_llm_client  # 走LLM_BACKEND开关,mock/real自动切换
from config.prompts import INTENT_CLASSIFY_PROMPT


def classify_by_format(file_path: str) -> str:
    """第0层:格式判断,纯规则,不需要任何外部资源"""
    if file_path.lower().endswith((".xlsx", ".xls", ".csv")):
        return "表格矩阵"
    if file_path.lower().endswith(".dbc"):
        return "DBC协议"
    return "纯文本"


def extract_regulation_meta(doc_name: str) -> dict | None:
    """法规元数据用正则提取,不需要LLM,现在就能写完并跑对"""
    match = re.match(REGULATION_PATTERN, doc_name)
    if not match:
        return None

    status = "现行"
    if "征求意见" in doc_name:
        status = "征求意见稿"
    elif "起草组讨论" in doc_name:
        status = "起草组讨论稿"

    return {
        "reg_number": match.group(1),
        "reg_name": match.group(2).strip(),
        "status": status,
    }


def scan_chunk_for_extraction_hints(chunk_text: str) -> dict:
    """章节级关键词粗筛,决定要不要触发定向抽取。纯规则,现在就能用"""
    return {
        "hit_signal_list": any(h in chunk_text for h in SIGNAL_LIST_HINTS),
        "hit_kpi_rule": any(h in chunk_text for h in KPI_RULE_HINTS),
    }


def classify_document_intent_llm(doc_name: str, preview_text: str) -> dict:
    """
    第一层整篇文档判断,调用LLM。
    LLM_BACKEND=mock时(默认),get_llm_client()返回一个假实现,
    会按写死的规则返回一个"看起来合理"的结果,保证整条pipeline能跑通、能测试,
    等真的接上API Key,把.env里的LLM_BACKEND改成real即可,这个函数不用改一个字。
    """
    client = get_llm_client()
    prompt = INTENT_CLASSIFY_PROMPT.format(doc_name=doc_name, preview_text=preview_text)
    return client.chat_json(prompt)
