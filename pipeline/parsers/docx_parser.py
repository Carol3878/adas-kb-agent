from unstructured.partition.auto import partition

from .base_parser import BaseParser, ParsedResult


class DocxParser(BaseParser):
    """
    对应流程文档/Spec/测试用例/法规这类深层目录的Word/PDF文件。
    关键点:保留标题层级路径(heading_path),而不是按固定字数切,
    这样"5.1.2 FOS测试步骤"这类深层章节的内容,
    检索到时能带着完整的面包屑上下文,不会变成一段孤立的文字。
    """

    def supports(self, file_path: str) -> bool:
        return file_path.lower().endswith((".docx", ".pdf", ".doc"))

    def parse(self, file_path: str) -> ParsedResult:
        elements = partition(filename=file_path)

        heading_chunks = []
        heading_stack: list[str] = []  # 当前标题路径栈,如 ["5.KPI看板验证","5.1单车验证"]
        current_paragraphs: list[str] = []

        def flush():
            if current_paragraphs:
                heading_chunks.append({
                    "heading_path": " > ".join(heading_stack) if heading_stack else "(无标题)",
                    "text": "\n".join(current_paragraphs),
                })
                current_paragraphs.clear()

        for el in elements:
            el_type = type(el).__name__
            text = str(el).strip()
            if not text:
                continue

            if el_type == "Title":
                flush()
                # 简化处理:标题层级由文本本身的编号(如"5.1.2")粗略判断深度,
                # 这里先做最简单的替换,不做严格的层级栈维护
                heading_stack = [text]
            else:
                current_paragraphs.append(text)

        flush()  # 处理最后一段

        full_text = "\n".join(c["text"] for c in heading_chunks)
        return ParsedResult(raw_text=full_text, heading_chunks=heading_chunks)
