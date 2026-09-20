from abc import ABC, abstractmethod


class ObjectStoreBase(ABC):
    @abstractmethod
    def put_object(self, object_key: str, file_path: str) -> str:
        """把本地文件存进对象存储,返回存储后的object_key"""
        ...

    @abstractmethod
    def get_object(self, object_key: str, dest_path: str) -> str:
        """把对象存储里的文件取回本地,返回本地路径"""
        ...

    @abstractmethod
    def exists(self, object_key: str) -> bool:
        ...
