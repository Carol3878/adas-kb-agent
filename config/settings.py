"""
全局配置中心。

关键设计:VECTOR_BACKEND 和 LLM_BACKEND 这两个开关,
决定了系统用"假实现(mock)"还是"真实现"跑起来。
没有API Key / 没有Milvus时,全部保持默认值(mock),
其余所有代码不用改一行,资源到位后只改这两个值+.env里的连接信息。
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ============ 后端切换开关 ============
# "mock": 用内存/本地假实现,不需要任何外部资源,用于开发和联调
# "real": 用真实的 Milvus / Anthropic API
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "mock")
LLM_BACKEND = os.getenv("LLM_BACKEND", "mock")


# ============ Postgres(模块一/二/三/四 + 法规索引表) ============
PG_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": os.getenv("PG_PORT", "5432"),
    "dbname": os.getenv("PG_DB", "kb_structured"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", ""),
}

# ============ Milvus(模块五 RAG向量库) ============
MILVUS_CONFIG = {
    "host": os.getenv("MILVUS_HOST", ""),
    "port": os.getenv("MILVUS_PORT", "19530"),
    "collection_name": "rag_chunks",
}

# ============ ClickHouse(生产车辆数据,注意区分两种用途) ============
# 场景A: 离线内省元数据(填充模块二),建议用只读的system库权限账号
CK_INTROSPECT_CONFIG = {
    "host": os.getenv("CK_HOST", ""),
    "user": os.getenv("CK_INTROSPECT_USER", ""),
    "password": os.getenv("CK_INTROSPECT_PASSWORD", ""),
}
# 场景B: 在线查询业务数据(Agent执行KPI计算),必须严格只读+限定库表
CK_QUERY_CONFIG = {
    "host": os.getenv("CK_HOST", ""),
    "user": os.getenv("CK_QUERY_USER", ""),
    "password": os.getenv("CK_QUERY_PASSWORD", ""),
    "query_timeout_seconds": 30,
    "max_rows": 10000,
}

# ============ LLM ============
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = "claude-sonnet-4-6"

# ============ Embedding(本地开源模型,不需要API Key) ============
EMBED_MODEL_NAME = "BAAI/bge-m3"
EMBED_DIM = 1024

# ============ 分块参数(对应图里的chunk策略) ============
CHUNK_SIZE_TOKENS = 400          # 300-500 token区间取中值
CHUNK_OVERLAP_RATIO = 0.18       # 15%-20%区间取中值

# ============ Rerank ============
RERANK_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
RERANK_TOP_K = 5
RETRIEVE_TOP_K = 20              # 粗排召回数量,rerank前的候选池大小

# ============ 【新增】对象存储(A区受理:落COS/NAS留底) ============
# 没有真实COS账号时,用本地文件夹模拟,以后接了真实账号只加一个OBJECT_STORE_BACKEND开关即可
OBJECT_STORE_ROOT = os.getenv("OBJECT_STORE_ROOT", "./local_object_store")

# ============ 【新增】本地队列(B区解析:MQ解析任务) ============
# 没有真实MQ时,用SQLite模拟队列
LOCAL_QUEUE_DB_PATH = os.getenv("LOCAL_QUEUE_DB_PATH", "./local_queue.db")

# ============ 意图分类关键词(规则粗筛,不调LLM) ============
SIGNAL_LIST_HINTS = ["信号清单", "Signal", "DBC", "报文", "落盘路径", "文件命名"]
KPI_RULE_HINTS = ["计算规则", "判定标准", "触发条件", "校验方法", "口径", "阈值"]
REGULATION_PATTERN = r"(GB\s?\d+-\d{4})\s*(.+)"
