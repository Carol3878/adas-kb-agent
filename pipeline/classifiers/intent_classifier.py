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


# ============ 【新增】分类优先级链 ============
# 对应设计决策①:显式元数据 > 命名规则 > 规则分类器 > LLM > 反问用户
# 能用便宜确定的方法判断,就不往下一级走,省成本也更准确。

_NAME_RULE_HINTS = {
    "流程": ["流程", "验收", "CRB"],
    "法规": ["GB", "国标", "征求意见", "标准"],
    "测试用例": ["测试用例", "TP", "校验"],
}


def resolve_document_category(doc_name: str, preview_text: str,
                                explicit_metadata: dict | None = None,
                                stage: str = "preliminary") -> dict:
    """
    统一分类入口,替代之前"规则和LLM平级调用"的方式。
    stage="preliminary": 对应②格式路由阶段的预分类,只用便宜的前两级,不调LLM,
                          目的是低成本挂一个候选身份。
    stage="confirm":     对应⑤分类决策阶段,读取清洗后的中间态内容,
                          前面几级都判断不了才轮到LLM,结果会覆盖预分类。
    返回结果里的 confidence 和 source 用来决定要不要进人工审核队列。
    """
    if explicit_metadata and explicit_metadata.get("doc_category"):
        return {"doc_category": explicit_metadata["doc_category"], "confidence": 1.0, "source": "explicit_metadata"}

    for category, hints in _NAME_RULE_HINTS.items():
        if any(h in doc_name for h in hints):
            return {"doc_category": category, "confidence": 0.85, "source": "naming_rule"}

    if stage == "preliminary":
        return {"doc_category": "需求spec", "confidence": 0.3, "source": "default_placeholder"}

    hints = scan_chunk_for_extraction_hints(preview_text)
    if hints["hit_kpi_rule"]:
        return {"doc_category": "需求spec", "confidence": 0.7, "source": "rule_classifier"}

    llm_result = classify_document_intent_llm(doc_name, preview_text)
    llm_result["source"] = "llm"
    return llm_result

    # 第五级"反问用户"由调用方(dispatcher)根据confidence判断是否push_to_review_queue
