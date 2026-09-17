from agent.llm_client import get_llm_client
from config.prompts import SIGNAL_EXTRACT_PROMPT
from kb.modules.m1_signal_dict import upsert_signal


def extract_and_save_signals(chunk_text: str, source_doc: str):
    client = get_llm_client()
    candidates = client.chat_json(SIGNAL_EXTRACT_PROMPT.format(chunk_text=chunk_text))
    for c in candidates:
        upsert_signal(c, source=source_doc)
    return len(candidates)
