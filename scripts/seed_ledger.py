#!/usr/bin/env python3
"""Seed a persistent ledger DB (so the MCP server / UI can read it).

    WBM_LEDGER_DB=./wbm_ledger.db uv run python scripts/seed_ledger.py
"""
from __future__ import annotations

import os

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.ledger import Ledger
from wormbase_memory.demo import sessions


def main() -> None:
    path = os.environ.get("WBM_LEDGER_DB", "./wbm_ledger.db")
    agent = DataOpsMemoryAgent(ledger=Ledger(path))
    for name, df, ts in sessions():
        agent.ingest(df, name, ts=ts)
    ok, _ = agent.verify()
    print(f"seeded {len(agent.ledger.fetch())} entries -> {path} (chain {'GREEN' if ok else 'BROKEN'})")


if __name__ == "__main__":
    main()
