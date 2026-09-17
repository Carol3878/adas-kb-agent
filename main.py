"""
用法:
  python main.py ingest <file_path>   # 投喂单个文档
  python main.py ask "<问题>"          # 问Agent(mock模式下只返回提示语)
"""

import sys

from pipeline.dispatcher import route_document
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

    elif command == "ask":
        query = sys.argv[2]
        answer = run_agent(query)
        print(answer)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
