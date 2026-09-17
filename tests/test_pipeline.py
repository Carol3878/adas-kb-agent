from kb.storage.mock_vector_store import MockVectorStore


def test_mock_vector_store_search_ranks_correctly():
    store = MockVectorStore()
    store.upsert("c1", [1.0, 0.0], "关于MPI的定义", {"doc_category": "需求spec"})
    store.upsert("c2", [0.0, 1.0], "关于流程的说明", {"doc_category": "流程"})

    results = store.search([0.9, 0.1], top_k=2)
    assert results[0]["chunk_id"] == "c1"  # 更接近[1,0],应该排第一


def test_mock_vector_store_filter():
    store = MockVectorStore()
    store.upsert("c1", [1.0, 0.0], "text1", {"doc_category": "法规"})
    store.upsert("c2", [1.0, 0.0], "text2", {"doc_category": "流程"})

    results = store.search([1.0, 0.0], top_k=10, filters={"doc_category": "法规"})
    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"
