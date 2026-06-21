#!/usr/bin/env python3
"""Showcase the local-Qwen triage worker on a gray-zone decision.

S1 establishes a cached plan. S2 is the SAME data shape (exact -> free reuse).
S3 adds a column (gray zone) -> the triage worker decides reuse vs escalate.

Offline it uses the deterministic rule; enable the real local Qwen with:
    ollama pull qwen3:1.7b
    export WBM_USE_LOCAL_QWEN=1
    uv run python scripts/triage_demo.py
"""
from __future__ import annotations

import pandas as pd

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.inference import LocalQwenClient

BASE = pd.DataFrame(
    [(" North", "Widget", 100), ("north ", "Widget", 100),
     ("South", "Gadget", 200), ("West", "Gadget", 150)],
    columns=["region", "product", "amount"],
)
GRAY = BASE.assign(note=["", "", "vip", ""])  # extra column -> not an exact match


def main() -> None:
    local = LocalQwenClient()
    print("WormBase Qwen Memory — local triage worker cameo")
    print(f"local Qwen worker : {'ENABLED ('+local.model+')' if local.available else 'offline -> deterministic rule'}")
    print("=" * 72)
    agent = DataOpsMemoryAgent()
    for name, df in [("s1 (new)", BASE), ("s2 (same shape)", BASE), ("s3 (extra col)", GRAY)]:
        r = agent.ingest(df, name)
        decided = agent.ledger.fetch("triage.decided")[-1].payload
        verb = "REUSE" if r.reused else "ESCALATE->author"
        print(f"{name:16s} | triage={decided['backend']:16s} sim={decided['similarity']:.2f} "
              f"tok={r.triage_tokens:>2d} -> {verb:16s} | {decided['reason']}")
    print("-" * 72)
    print(f"hash-chain verify : {'GREEN' if agent.verify()[0] else 'BROKEN'}")


if __name__ == "__main__":
    main()
