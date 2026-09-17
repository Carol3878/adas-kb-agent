from agent.llm_client import get_llm_client
from config.prompts import SPEC_RULE_EXTRACT_PROMPT
from kb.modules.m3_business_rules import save_draft_rule


def extract_and_save_rules(chunk_text: str, source_doc: str):
    """
    LLM_BACKEND=mock时,get_llm_client().chat_json()固定返回[],
    这个函数照常执行不报错,只是不会真的抽出规则——
    这样可以先跑通"这一步会不会被正确触发"的逻辑,等有Key了自然就有真实产出。
    """
    client = get_llm_client()
    candidates = client.chat_json(SPEC_RULE_EXTRACT_PROMPT.format(chunk_text=chunk_text))
    for c in candidates:
        save_draft_rule(c, source_doc)
    return len(candidates)
