"""
双层查重:
第一层(粗筛)对原始文件字节算sha256,能识别"完全一样的文件被重复上传"。
第二层(精筛)对清洗后的规范化文本算sha256,能识别
"同一份内容,但文件格式或文件名不一样"(比如一份导出成Word,一份导出成PDF)。
"""

import hashlib
import re

from kb.storage.postgres_client import get_pg_connection


def compute_raw_hash(file_path: str) -> str:
    return hashlib.sha256(open(file_path, "rb").read()).hexdigest()


def compute_normalized_text_hash(raw_text: str) -> str:
    """规范化:去空白、去标点差异,减少"格式不同但内容相同"被漏判的情况"""
    normalized = re.sub(r"\s+", "", raw_text)
    normalized = re.sub(r"[，。、；：]", "", normalized)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def check_duplicate(raw_hash: str, text_hash: str | None = None) -> dict | None:
    """
    返回None表示不是重复文档,可以继续处理。
    返回已有记录表示重复,调用方应该走DUPLICATE分支,不重新处理,
    或者判断为"内容相同但需要触发版本更新"(text_hash相同,raw_hash不同)。
    """
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM documents WHERE raw_hash = %s", (raw_hash,))
    row = cur.fetchone()
    if row:
        return {"match_level": "exact_file", "record": row}

    if text_hash:
        cur.execute("SELECT * FROM documents WHERE text_hash = %s ORDER BY version DESC LIMIT 1", (text_hash,))
        row = cur.fetchone()
        if row:
            return {"match_level": "same_content_diff_file", "record": row}

    return None
