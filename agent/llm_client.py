"""
LLM客户端抽象层。

没有API Key时,LLM_BACKEND=mock(默认),所有调用LLM的地方
(意图分类、结构化抽取、Agent对话)都能跑,只是返回的是
写死的、结构合法但内容简单的假数据——目的是让你在没有Key的时候,
依然能测试"整条pipeline有没有跑通"这件事,而不是卡在第一步。

等API Key到位,只需要:
1. .env里配置 ANTHROPIC_API_KEY
2. .env里把 LLM_BACKEND 改成 real
不需要改动任何调用方代码。
"""

import json
from abc import ABC, abstractmethod

from config.settings import LLM_BACKEND, LLM_PROVIDER, ANTHROPIC_API_KEY, LLM_MODEL, GEMINI_API_KEY, GEMINI_MODEL

class LLMClientBase(ABC):
    @abstractmethod
    def chat_json(self, prompt: str) -> dict | list:
        """要求模型只返回JSON,自动parse好返回"""
        ...

    @abstractmethod
    def chat_with_tools(self, messages: list[dict], tools: list[dict], system: str = ""):
        """Agent对话循环用,返回完整response对象"""
        ...


class MockLLMClient(LLMClientBase):
    """
    没有API Key时的假实现。
    刻意返回"低置信度"的结果,而不是编造一个看起来很对的答案——
    这样即使忘了切换成real,下游的人工审核环节也会因为置信度低而拦截,
    不会有假数据被误当成真实抽取结果流入生产库。
    """

    def chat_json(self, prompt: str):
        if "signal_dictionary" in prompt.lower() or "standard_name" in prompt:
            return []
        if "spec_assertion" in prompt or "kpi_metric" in prompt:
            return []
        # 意图分类类的prompt,给一个保守的默认分类
        return {
            "doc_category": "需求spec",
            "content_form": "纯文本",
            "regulation_number": None,
            "_mock_warning": "LLM_BACKEND=mock,这是假数据,请勿用于生产判断",
        }

    def chat_with_tools(self, messages, tools, system=""):
        class MockResponse:
            stop_reason = "end_turn"
            content = "[MOCK模式] 尚未配置真实LLM,无法进行Agent推理。请配置ANTHROPIC_API_KEY并将LLM_BACKEND设为real。"
            tool_calls = []

        return MockResponse()


class AnthropicClient(LLMClientBase):
    """真实实现,需要ANTHROPIC_API_KEY才能用"""

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def chat_json(self, prompt: str):
        response = self.client.messages.create(
            model=LLM_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        text = text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(text)

    def chat_with_tools(self, messages, tools, system=""):
        return self.client.messages.create(
            model=LLM_MODEL,
            max_tokens=2000,
            system=system,
            messages=messages,
            tools=tools,
        )

class GeminiClient(LLMClientBase):
    """
    【修改说明】google.generativeai已停止维护,改用新包google.genai。
    调用方式变化比较大:不再是先configure再拿GenerativeModel,
    而是直接建一个Client对象,每次调用时传入model名字。
    """

    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def chat_json(self, prompt: str):
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)

    def chat_with_tools(self, messages, tools, system=""):
        """
        新SDK的工具调用schema和消息格式跟旧包、跟Anthropic都不一样,
        这里同样是简化实现,实际跑通之前建议先单独测chat_json这部分,
        chat_with_tools大概率需要根据实际返回结构再调整。
        """
        full_prompt = f"{system}\n\n{messages[-1]['content']}" if system else messages[-1]["content"]
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
        )

        class GeminiResponse:
            stop_reason = "end_turn"
            content = response.text
            tool_calls = []

        return GeminiResponse()

def get_llm_client() -> LLMClientBase:
    if LLM_BACKEND == "real":
        if LLM_PROVIDER == "anthropic":
            return AnthropicClient()
        if LLM_PROVIDER == "gemini":
                return GeminiClient()
    return MockLLMClient()