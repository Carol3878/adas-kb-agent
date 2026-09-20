"""
用法:
  python main.py ingest <file_path>        # 投喂本地文档
  python main.py ingest-feishu <doc_url>   # 【新增】投喂飞书文档,需要配置FEISHU_APP_ID/SECRET
  python main.py ask "<问题>"               # 问Agent(mock模式下只返回提示语)
"""

import sys

from pipeline.dispatcher import route_document, ingest_feishu_document
from agent.core import run_agent


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == "ingest":
        file_path = sys.argv[2]
        doc_name = file_path.split("/")[-1]
        result = route_document(file_path, doc_name)
        print(result)

    elif command == "ingest-feishu":
        doc_url = sys.argv[2]
        doc_name = sys.argv[3] if len(sys.argv) > 3 else "飞书文档"
        result = ingest_feishu_document(doc_url, doc_name)
        print(result)

    elif command == "ask":
        query = sys.argv[2]
        answer = run_agent(query)
        print(answer)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
