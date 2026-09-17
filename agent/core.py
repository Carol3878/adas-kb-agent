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
]

DISPATCH_MAP = {
    "search_documents": lambda i: search_documents(**i),
    "lookup_kpi": lambda i: lookup_kpi(**i),
    "lookup_signal_field": lambda i: lookup_signal_field(**i),
}


def run_agent(user_query: str, history: list[dict] | None = None):
    """
    LLM_BACKEND=mock时,这个函数能跑,但会直接返回mock提示语,
    不会真的做多轮工具调用推理——用来验证调用链路搭得对不对。
    """
    client = get_llm_client()
    messages = (history or []) + [{"role": "user", "content": user_query}]

    while True:
        response = client.chat_with_tools(messages, TOOLS_SCHEMA, system=AGENT_SYSTEM_PROMPT)
        if response.stop_reason != "tool_use":
            return response.content

        # 真实实现下需要解析response.content里的tool_use块并调用DISPATCH_MAP
        # mock模式下不会走到这里
        break

    return response.content
