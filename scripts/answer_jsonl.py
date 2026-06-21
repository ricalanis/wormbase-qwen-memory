#!/usr/bin/env python3
"""Answer a JSONL of questions with Qwen-Plus (DashScope) — the generation half
of standard memory benchmarks (LongMemEval / PrefEval).

Input  JSONL rows: {"question_id": "...", "question": "...", "context": "..."?}
Output JSONL rows: {"question_id": "...", "hypothesis": "..."}

    export DASHSCOPE_API_KEY=sk-...
    uv run python scripts/answer_jsonl.py questions.jsonl hypotheses.jsonl

Then score with the benchmark's own (GPT-4o) judge per its repo instructions.
"""
from __future__ import annotations

import json
import sys

from wormbase_memory.inference import QwenCloudClient


def main(inp: str, outp: str) -> int:
    q = QwenCloudClient()
    if not q.available:
        print("✗ Set DASHSCOPE_API_KEY first.")
        return 1
    n = 0
    with open(inp) as fi, open(outp, "w") as fo:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            messages = []
            if row.get("context"):
                messages.append({"role": "system",
                                 "content": "Use this memory/context to answer:\n"
                                 + row["context"]})
            messages.append({"role": "user", "content": row["question"]})
            res = q.chat(messages, temperature=0.0, max_tokens=512)
            fo.write(json.dumps({"question_id": row.get("question_id", n),
                                 "hypothesis": res.text}) + "\n")
            n += 1
    print(f"✓ wrote {n} hypotheses -> {outp}  (model={q.model})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
