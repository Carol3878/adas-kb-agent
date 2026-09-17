from kb.modules.m5_rag_vector import retrieve


def search_documents(query: str, top_k: int = 5, doc_category: str | None = None):
    filters = {"doc_category": doc_category} if doc_category else None
    return retrieve(query, top_k=top_k, filters=filters)
