#!/usr/bin/env python3
"""One-call connectivity check against Alibaba Cloud DashScope (Qwen-Plus).

    export DASHSCOPE_API_KEY=sk-...
    uv run python scripts/smoke_dashscope.py
"""
from __future__ import annotations

import sys

from wormbase_memory.inference import QwenCloudClient


def main() -> int:
    q = QwenCloudClient()
    if not q.available:
        print("✗ No DASHSCOPE_API_KEY (or openai SDK missing). Set the key and retry.")
        return 1
    print(f"→ base_url: {q.base_url}\n→ model:   {q.model}")
    res = q.chat(
        [
            {"role": "system", "content": "Reply with exactly: OK"},
            {"role": "user", "content": "ping"},
        ],
        max_tokens=8,
    )
    print(f"✓ reply: {res.text!r}  (tokens={res.tokens}, backend={res.backend})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
