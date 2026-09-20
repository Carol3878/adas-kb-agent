"""
没有RabbitMQ/Kafka时用这个。用SQLite的一张表模拟队列:
一行代表一个任务,status字段记录"pending/processing/done/failed"。
入队就是插一行,取任务就是查一条pending的改成processing。
本地开发和小规模场景完全够用,以后真的需要高吞吐再换真实MQ,
调用方只认QueueBase这几个方法,不用改业务代码。
"""

import sqlite3
import json
import uuid
from datetime import datetime

from config.settings import LOCAL_QUEUE_DB_PATH
from .mq_base import QueueBase


class LocalSqliteQueue(QueueBase):
    def __init__(self, db_path: str = LOCAL_QUEUE_DB_PATH):
        self.db_path = db_path
        self._init_table()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        conn = self._conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queue_tasks (
                task_id TEXT PRIMARY KEY,
                queue_name TEXT,
                payload TEXT,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def enqueue(self, queue_name: str, payload: dict) -> str:
        task_id = str(uuid.uuid4())
        conn = self._conn()
        conn.execute(
            "INSERT INTO queue_tasks (task_id, queue_name, payload, created_at) VALUES (?,?,?,?)",
            (task_id, queue_name, json.dumps(payload), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return task_id

    def dequeue(self, queue_name: str) -> dict | None:
        conn = self._conn()
        cur = conn.execute(
            "SELECT task_id, payload FROM queue_tasks WHERE queue_name=? AND status='pending' LIMIT 1",
            (queue_name,),
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return None

        task_id, payload = row
        conn.execute("UPDATE queue_tasks SET status='processing' WHERE task_id=?", (task_id,))
        conn.commit()
        conn.close()
        return {"task_id": task_id, "payload": json.loads(payload)}

    def mark_done(self, task_id: str) -> None:
        conn = self._conn()
        conn.execute("UPDATE queue_tasks SET status='done' WHERE task_id=?", (task_id,))
        conn.commit()
        conn.close()

    def mark_failed(self, task_id: str, error: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE queue_tasks SET status='failed', attempts=attempts+1, last_error=? WHERE task_id=?",
            (error, task_id),
        )
        conn.commit()
        conn.close()


def get_queue() -> QueueBase:
    return LocalSqliteQueue()
