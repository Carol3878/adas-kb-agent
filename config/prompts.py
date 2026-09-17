"""
LLM Prompt模板集中管理。
现在没有API Key,这些prompt先写好、先设计好输出schema,
等LLM_BACKEND切到"real"时直接可用,不用等到那时候再现写。
"""

INTENT_CLASSIFY_PROMPT = """判断这份文档的类型,输出JSON,不要输出其他任何文字:
{{
  "doc_category": "流程" | "需求spec" | "测试用例" | "法规",
  "content_form": "纯文本" | "表格矩阵",
  "regulation_number": "GB xxxxx-xxxx格式的标准号,不是法规则填null"
}}

文件名: {doc_name}
文档预览(标题+目录+前几百字): {preview_text}
"""

SPEC_RULE_EXTRACT_PROMPT = """从下面这段文字中判断是否包含"功能判定规则"或"KPI计算公式",
如果有,按以下JSON格式输出;如果没有,输出空数组 []。

record_type 取值说明:
- "spec_assertion": 功能触发/判定条件,比如"车速低于20km/h时允许搜索车位"
- "kpi_metric": 统计聚合类指标,比如"总里程除以接管次数"

输出格式:
[{{
  "record_type": "spec_assertion" | "kpi_metric",
  "name": "规则或指标名称",
  "natural_language_desc": "自然语言描述",
  "logic_expression": "尽量翻译成可执行的逻辑表达式或计算公式,翻译不了就填自然语言",
  "required_signals": ["涉及的信号或字段名"],
  "confidence": 0.0到1.0之间,表述越模糊分数越低
}}]

只输出JSON数组,不要输出其他说明文字。

文本片段:
{chunk_text}
"""

SIGNAL_EXTRACT_PROMPT = """从下面这段文字中识别物理信号定义,输出JSON数组,没有则输出[]。

[{{
  "standard_name": "信号的标准/英文名",
  "cn_aliases": ["中文别名1", "中文别名2"],
  "unit": "单位,不确定填null",
  "description": "简要描述",
  "confidence": 0.0到1.0
}}]

只输出JSON数组。

文本片段:
{chunk_text}
"""

AGENT_SYSTEM_PROMPT = """你是智能驾驶知识库助手,处理用户问题时遵循:
1. 涉及具体指标计算(如MPI)时,先调用 lookup_kpi 确认口径和公式,再调用 execute_kpi_calculation。
2. 涉及信号/字段含义时,调用 lookup_signal 把自然语言翻译成真实字段名。
3. 涉及"该查哪个车型/版本的数据"时,先调用 lookup_vehicle_routing 定位物理表。
4. 涉及文档内容/流程/法规解释时,调用 search_documents。
5. 任何工具返回结果有歧义或置信度低,必须先反问用户确认,不要自行猜测执行。
6. 回答必须带来源(文档名+版本,或KPI口径来源),不要凭空回答。
"""
