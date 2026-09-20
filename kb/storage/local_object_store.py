"""
没有COS/NAS账号时用这个,把"对象存储"模拟成本地一个文件夹。
方法签名跟真实COS client保持一致,以后接了真实账号,
只需要新写一个 TencentCosStore(ObjectStoreBase) 之类的类,
调用方(pipeline/dispatcher.py)一行都不用改。
"""

import os
import shutil

from .object_store_base import ObjectStoreBase


class LocalObjectStore(ObjectStoreBase):
    def __init__(self, root_dir: str = "./local_object_store"):
        self.root_dir = root_dir
        os.makedirs(root_dir, exist_ok=True)

    def put_object(self, object_key: str, file_path: str) -> str:
        dest = os.path.join(self.root_dir, object_key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(file_path, dest)
        return object_key

    def get_object(self, object_key: str, dest_path: str) -> str:
        src = os.path.join(self.root_dir, object_key)
        shutil.copy2(src, dest_path)
        return dest_path

    def exists(self, object_key: str) -> bool:
        return os.path.exists(os.path.join(self.root_dir, object_key))


def get_object_store() -> ObjectStoreBase:
    """以后接了真实COS,在这里加分支判断走真实实现还是本地实现,跟Milvus/LLM那两个开关是同一个思路"""
    from config.settings import OBJECT_STORE_ROOT
    return LocalObjectStore(OBJECT_STORE_ROOT)
