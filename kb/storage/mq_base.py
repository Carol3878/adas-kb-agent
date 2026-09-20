from abc import ABC, abstractmethod


class QueueBase(ABC):
    @abstractmethod
    def enqueue(self, queue_name: str, payload: dict) -> str:
        """返回task_id"""
        ...

    @abstractmethod
    def dequeue(self, queue_name: str) -> dict | None:
        """取一条待处理任务并标记为处理中,没有任务返回None"""
        ...

    @abstractmethod
    def mark_done(self, task_id: str) -> None:
        ...

    @abstractmethod
    def mark_failed(self, task_id: str, error: str) -> None:
        """失败次数超过阈值时,调用方负责转入死信"""
        ...
