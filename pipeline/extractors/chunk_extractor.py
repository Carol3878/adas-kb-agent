from langchain.text_splitter import RecursiveCharacterTextSplitter

from config.settings import CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_RATIO

# 中文场景1个token约等于1.5-2个字符,这里用字符数近似,
# 后续如果对token数精度有要求,可以换成tiktoken精确计数
_CHARS_PER_TOKEN = 1.7


def chunk_heading_sections(heading_chunks: list[dict]) -> list[dict]:
    """
    输入是docx_parser按标题切出来的段落(可能还是太长),
    这里在每个标题段落内部再按token数二次细分,
    同时保留heading_path,确保切出来的每一片都带着完整的章节上下文。
    """
    chunk_size_chars = int(CHUNK_SIZE_TOKENS * _CHARS_PER_TOKEN)
    overlap_chars = int(chunk_size_chars * CHUNK_OVERLAP_RATIO)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_chars,
        chunk_overlap=overlap_chars,
        separators=["\n\n", "。", "\n"],
    )

    result = []
    for section in heading_chunks:
        pieces = splitter.split_text(section["text"])
        for piece in pieces:
            result.append({"heading_path": section["heading_path"], "text": piece})
    return result
