from abc import ABC, abstractmethod


class VectorStoreBase(ABC):
    @abstractmethod
    def upsert(self, chunk_id: str, vector: list[float], text: str, metadata: dict) -> None:
        ...

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int = 20,
               filters: dict | None = None) -> list[dict]:
        """返回 [{"chunk_id","text","metadata","score"}, ...]"""
        ...
