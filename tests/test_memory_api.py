"""The MCP-exposed memory API (transport-independent)."""

from __future__ import annotations

import pandas as pd

from wormbase_memory import memory_api
from wormbase_memory.agent import DataOpsMemoryAgent


def _seed() -> DataOpsMemoryAgent:
    a = DataOpsMemoryAgent()
    base = pd.DataFrame([("North", "Widget", 100), ("South", "Gadget", 200),
                         ("West", "Gadget", 150)], columns=["region", "product", "amount"])
    whale = pd.DataFrame([("North", "Widget", 100), ("South", "Gadget", 200),
                          ("West", "Gadget", 150), ("East", "Widget", 2000)],
                         columns=["region", "product", "amount"])
    a.ingest(base, "s1")
    a.ingest(whale, "s2-drift")
    return a


def test_list_and_ask():
    a = _seed()
    assert "total_amount" in memory_api.list_kpis(a.ledger)
    ans = memory_api.ask_kpi(a.ledger, "total_amount")
    assert ans["grounded"] and ans["receipts"]


def test_explain_and_verify():
    a = _seed()
    expl = memory_api.explain_change(a.ledger, "total_amount")
    assert expl and expl["dim"] == "region"
    v = memory_api.verify_memory(a.ledger)
    assert v["chain_ok"] is True and v["head_hash"]


def test_replay_until():
    a = _seed()
    snap = memory_api.replay_until(a.ledger, a.ledger.fetch()[-1].ts.isoformat())
    assert len(snap) == len(a.ledger.fetch())
