"""
【需要真实飞书应用凭证才能运行,但代码现在就可以写完】

飞书文档跟本地文件不一样,不是读文件路径,而是拿"文档token"去调
飞书开放平台的API取内容。这里用的是最简单的raw_content接口
(只返回纯文本,不带标题层级块信息),先够用验证链路能不能跑通;
以后如果要精确保留标题层级,可以换成更细的blocks接口,
按block_type区分标题级别(1~9对应H1~H9),但接口调用方式类似,
不影响下游代码。
"""

import re

import requests

from config.settings import FEISHU_APP_ID, FEISHU_APP_SECRET
from .base_parser import BaseParser, ParsedResult

TENANT_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
RAW_CONTENT_URL = "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/raw_content"


class FeishuParser(BaseParser):
    def supports(self, file_path: str) -> bool:
        # 飞书文档不是本地路径,而是一个飞书文档链接,用这个特征判断
        return "feishu.cn" in file_path or file_path.startswith("feishu:")

    def _get_tenant_access_token(self) -> str:
        resp = requests.post(TENANT_TOKEN_URL, json={
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET,
        })
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取飞书tenant_access_token失败: {data}")
        return data["tenant_access_token"]

    def _extract_document_id(self, doc_url: str) -> str:
        """飞书文档链接形如 https://xxx.feishu.cn/docx/<document_id>,把id抠出来"""
        match = re.search(r"/docx/([a-zA-Z0-9]+)", doc_url)
        if not match:
            raise ValueError(f"无法从链接中解析出飞书document_id: {doc_url}")
        return match.group(1)

    def parse(self, file_path: str) -> ParsedResult:
        document_id = self._extract_document_id(file_path)
        token = self._get_tenant_access_token()

        resp = requests.get(
            RAW_CONTENT_URL.format(document_id=document_id),
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取飞书文档内容失败: {data}")

        raw_text = data["data"]["content"]

        # raw_content接口不返回标题层级结构,先整篇当一个chunk,
        # 具体的token级切分交给下游chunk_extractor.py处理
        heading_chunks = [{"heading_path": "(飞书文档,无层级信息)", "text": raw_text}]
        return ParsedResult(raw_text=raw_text, heading_chunks=heading_chunks)
