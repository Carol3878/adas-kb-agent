"""
【修改说明】加入两处:
1. 接入rerank——之前直接返回粗排结果,现在先扩大粗排召回数量(RETRIEVE_TOP_K),
   再用reranker精排取真正相关的top_k。
2. 加permission_group过滤参数,对应⑥策略路由里"权限组"的概念,
   之前完全没有权限过滤。
"""

from config.settings import RETRIEVE_TOP_K
from kb.modules.m5_rag_vector import retrieve
from pipeline.reranker import rerank


def search_documents(query: str, top_k: int = 5, doc_category: str | None = None,
                      permission_group: str | None = None):
    filters = {}
    if doc_category:
        filters["doc_category"] = doc_category
    if permission_group:
        filters["permission_group"] = permission_group

    candidates = retrieve(query, top_k=RETRIEVE_TOP_K, filters=filters or None)
    return rerank(query, candidates, top_k=top_k)
