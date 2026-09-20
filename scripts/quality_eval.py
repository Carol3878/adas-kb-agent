"""
准备一批"问题-期望关键词"样本,定期跑一遍,
看检索回答里有没有命中期望内容——用来发现"改了某个环节后,
整体效果悄悄变差了"这种问题。

用法: python scripts/quality_eval.py
"""

import json

from agent.tools.rag_search_tool import search_documents

# 先放几条示例,实际使用时补充到50-100条真实场景问题
EVAL_SET = [
    {"query": "MPI的计算口径是什么", "expect_keywords": ["接管", "里程"]},
    {"query": "ADAS数据需求开发流程", "expect_keywords": ["流程", "验收"]},
]


def run_eval():
    results = []
    for case in EVAL_SET:
        hits = search_documents(case["query"], top_k=3)
        hit_text = " ".join(h["text"] for h in hits)
        matched = [kw for kw in case["expect_keywords"] if kw in hit_text]
        results.append({
            "query": case["query"],
            "expect_keywords": case["expect_keywords"],
            "matched_keywords": matched,
            "pass": len(matched) == len(case["expect_keywords"]),
        })

    pass_rate = sum(r["pass"] for r in results) / len(results)
    print(json.dumps({"pass_rate": pass_rate, "details": results}, ensure_ascii=False, indent=2))
    return pass_rate


if __name__ == "__main__":
    run_eval()
