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

# 【新增】内容级规则字典,覆盖四大类,不再只判断"需求spec"这一类。
# 之前的版本只检查KPI_RULE_HINTS这几个词,命中就统一归成"需求spec",
# 法规/流程/测试用例这三类文档,只要文件名没命中命名规则,
# 就会直接跳过内容判断,白白送去LLM(或者mock模式下必然置信度不够)。
# 这里给每一类都配一组内容特征词,按命中数量打分,谁命中得多算谁。
_CONTENT_RULE_HINTS = {
    "流程": ["验收标准", "责任人", "审批流程", "流程图", "里程碑", "评审", "分工"],
    "法规": ["强制性国家标准", "本标准规定", "适用范围", "规范性引用文件", "术语和定义", "实施日期", "GB/T"],
    "测试用例": ["测试步骤", "预期结果", "测试用例编号", "前置条件", "测试环境", "Pass", "Fail"],
    "需求spec": ["计算规则", "判定标准", "触发条件", "校验方法", "口径", "阈值", "需求编号", "功能描述"],
}

_CONTENT_MATCH_MIN_SCORE = 1  # 至少命中1个特征词才采信,命中0个说明内容特征不明显,交给LLM判断更合适


def classify_by_content(preview_text: str) -> dict | None:
    """
    内容级规则分类,按命中特征词数量给各类别打分,取分数最高的。
    命中数量太少(0个)时返回None,让调用方转去LLM判断,
    不要硬凑一个低置信度的规则结果出来,那样反而可能挡住更准的LLM判断。
    """
    scores = {
        category: sum(1 for hint in hints if hint in preview_text)
        for category, hints in _CONTENT_RULE_HINTS.items()
    }
    best_category, best_score = max(scores.items(), key=lambda item: item[1])

    if best_score < _CONTENT_MATCH_MIN_SCORE:
        return None

    # 命中越多置信度越高,但封顶0.75——毕竟这只是关键词匹配,
    # 不是真的理解了语义,置信度不该给得比命名规则(0.85)还高
    confidence = min(0.5 + best_score * 0.08, 0.75)
    return {"doc_category": best_category, "confidence": round(confidence, 2), "source": "content_rule_classifier"}


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

    content_result = classify_by_content(preview_text)
    if content_result:
        return content_result

    llm_result = classify_document_intent_llm(doc_name, preview_text)
    llm_result["source"] = "llm"
    return llm_result

    # 第五级"反问用户"由调用方(dispatcher)根据confidence判断是否push_to_review_queue