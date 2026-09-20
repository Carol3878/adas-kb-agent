"""
这些测试现在就能跑,验证A/B区新增的三个组件。
跑法: pytest tests/test_reliability.py -v
"""

import os
import tempfile

from kb.storage.local_object_store import LocalObjectStore
from kb.storage.local_queue import LocalSqliteQueue
from pipeline.dedup import compute_raw_hash, compute_normalized_text_hash


def test_local_object_store_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalObjectStore(root_dir=os.path.join(tmp, "store"))

        src = os.path.join(tmp, "test.txt")
        open(src, "w").write("hello adas")

        store.put_object("docs/test.txt", src)
        assert store.exists("docs/test.txt")

        dest = os.path.join(tmp, "restored.txt")
        store.get_object("docs/test.txt", dest)
        assert open(dest).read() == "hello adas"


def test_local_queue_enqueue_dequeue():
    with tempfile.TemporaryDirectory() as tmp:
        queue = LocalSqliteQueue(db_path=os.path.join(tmp, "queue.db"))

        task_id = queue.enqueue("parse_tasks", {"file": "a.docx"})
        task = queue.dequeue("parse_tasks")

        assert task["task_id"] == task_id
        assert task["payload"]["file"] == "a.docx"

        # 已经取走的任务,再取应该拿不到了
        assert queue.dequeue("parse_tasks") is None

        queue.mark_done(task_id)


def test_dedup_normalized_text_hash_ignores_whitespace():
    hash1 = compute_normalized_text_hash("这是一份 测试文档。")
    hash2 = compute_normalized_text_hash("这是一份测试文档")
    assert hash1 == hash2  # 空白和标点差异不应该影响判重结果
