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


def check_duplicate(raw_hash: str, text_hash: str | None = None,
                     exclude_doc_id: int | None = None) -> dict | None:
    """
    返回None表示不是重复文档,可以继续处理。
    返回已有记录表示重复,调用方应该走DUPLICATE分支,不重新处理,
    或者判断为"内容相同但需要触发版本更新"(text_hash相同,raw_hash不同)。

    exclude_doc_id: 【修复bug用】排除某个doc_id不参与匹配。
    背景:route_document流程里,create_document_record会先把当前文档
    自己的记录插入documents表,插入之后如果再用同一个raw_hash查重,
    会把"刚插入的自己"当成重复记录匹配上,导致第一次投喂就被误判DUPLICATE。
    第二次查重(_process_text_content里那次)必须传入exclude_doc_id=当前doc_id,
    把自己排除在查询范围外。
    """
    conn = get_pg_connection()
    cur = conn.cursor()

    sql = "SELECT * FROM documents WHERE raw_hash = %s"
    params = [raw_hash]
    if exclude_doc_id is not None:
        sql += " AND id != %s"
        params.append(exclude_doc_id)
    cur.execute(sql, params)
    row = cur.fetchone()
    if row:
        return {"match_level": "exact_file", "record": row}

    if text_hash:
        sql = "SELECT * FROM documents WHERE text_hash = %s"
        params = [text_hash]
        if exclude_doc_id is not None:
            sql += " AND id != %s"
            params.append(exclude_doc_id)
        sql += " ORDER BY version DESC LIMIT 1"
        cur.execute(sql, params)
        row = cur.fetchone()
        if row:
            return {"match_level": "same_content_diff_file", "record": row}

    return None
