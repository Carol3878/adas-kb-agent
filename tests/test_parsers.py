"""
这些测试现在就能跑,不需要任何API Key或Milvus。
跑法: pytest tests/test_parsers.py -v
"""

from pipeline.classifiers.intent_classifier import extract_regulation_meta, classify_by_format


def test_extract_regulation_meta_current():
    result = extract_regulation_meta("GB 47955-2026 智能网联汽车 组合驾驶辅助系统安全要求")
    assert result["reg_number"] == "GB 47955-2026"
    assert result["status"] == "现行"


def test_extract_regulation_meta_draft():
    result = extract_regulation_meta("智能网联汽车 泊车组合驾驶辅助系统安全要求（征求意见）")
    assert result is None  # 文件名没有标准号格式,符合预期


def test_classify_by_format():
    assert classify_by_format("data.xlsx") == "表格矩阵"
    assert classify_by_format("signals.dbc") == "DBC协议"
    assert classify_by_format("spec.docx") == "纯文本"
