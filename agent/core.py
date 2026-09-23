"""
【修改说明】run_agent之前那个while循环写了个break,没有真正实现
"解析tool_use块->执行工具->把结果喂回去->再问一次"这个多轮循环,
这次把它补完整。同时给lookup_vehicle_routing也补上了工具声明
(之前DISPATCH_MAP里漏了这一个,只声明了三个工具)。
"""

from agent.llm_client import get_llm_client
from config.prompts import AGENT_SYSTEM_PROMPT
from agent.tools.rag_search_tool import search_documents
from agent.tools.rule_check_tool import lookup_kpi, lookup_signal_field, lookup_vehicle_routing

TOOLS_SCHEMA = [
    {"name": "search_documents", "description": "语义检索文档",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "lookup_kpi", "description": "查询KPI/规则定义",
     "input_schema": {"type": "object", "properties": {"kpi_query": {"type": "string"}}, "required": ["kpi_query"]}},
    {"name": "lookup_signal_field", "description": "把自然语言翻译成真实字段名",
     "input_schema": {"type": "object", "properties": {"signal_query": {"type": "string"}}, "required": ["signal_query"]}},
    {"name": "lookup_vehicle_routing", "description": "根据车型和软件版本定位该查哪张CK表",
     "input_schema": {
         "type": "object",
         "properties": {
             "car_model": {"type": "string"},
             "software_version": {"type": "string"},
         },
         "required": ["car_model", "software_version"],
     }},
]

DISPATCH_MAP = {
    "search_documents": lambda i: search_documents(**i),
    "lookup_kpi": lambda i: lookup_kpi(**i),
    "lookup_signal_field": lambda i: lookup_signal_field(**i),
    "lookup_vehicle_routing": lambda i: lookup_vehicle_routing(**i),
}

MAX_TOOL_ROUNDS = 8  # 防止模型陷入死循环一直调工具不给答案,超过这个轮数强制停止


def _extract_text(content_blocks) -> str:
    """从一堆content block里把纯文字部分拼出来,忽略tool_use块"""
    texts = [b.text for b in content_blocks if getattr(b, "type", None) == "text"]
    return "\n".join(texts)


def run_agent(user_query: str, history: list[dict] | None = None) -> str:
    """
    LLM_BACKEND=mock时,MockLLMClient的chat_with_tools直接返回
    stop_reason="end_turn"的假响应,不会进入下面的工具调用循环,
    一轮就结束,行为跟之前一致,不会报错。

    LLM_BACKEND=real时,才会真正执行多轮"调用工具->喂结果->再问"的循环。
    """
    client = get_llm_client()
    messages = (history or []) + [{"role": "user", "content": user_query}]

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat_with_tools(messages, TOOLS_SCHEMA, system=AGENT_SYSTEM_PROMPT)

        if response.stop_reason != "tool_use":
            return _extract_text(response.content) if not isinstance(response.content, str) else response.content

        messages.append({"role": "assistant", "content": response.content})

        tool_result_blocks = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input
            tool_use_id = block.id

            try:
                if tool_name not in DISPATCH_MAP:
                    raise ValueError(f"未知工具: {tool_name}")
                result = DISPATCH_MAP[tool_name](tool_input)
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(result),
                })
            except Exception as e:
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": f"工具执行出错: {e}",
                    "is_error": True,
                })

        messages.append({"role": "user", "content": tool_result_blocks})

    return "已达到最大工具调用轮数,仍未得出最终答案,建议换个问法或缩小问题范围。"