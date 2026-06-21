"""Receipts-backed Q&A: grounded prose + citations to ledger entries."""

from __future__ import annotations

import pandas as pd

from wormbase_memory.agent import DataOpsMemoryAgent


def _df(west=150):
    return pd.DataFrame(
        [("North", "Widget", 100), ("South", "Gadget", 200), ("West", "Gadget", west)],
        columns=["region", "product", "amount"],
    )


def test_answer_grounded_with_receipts_after_drift():
    a = DataOpsMemoryAgent()
    a.ingest(_df(), "s1")
    a.ingest(_df(west=5000), "s2-whale")  # drift -> explained
    ans = a.answer("total_amount")
    assert ans["grounded"] is True
    assert ans["receipts"], "must cite ledger entries"
    assert all("hash" in r and "seq" in r for r in ans["receipts"])
    assert "West" in ans["prose"]  # the driver


def test_answer_for_stable_kpi_is_grounded():
    a = DataOpsMemoryAgent()
    a.ingest(_df(), "s1")
    ans = a.answer("total_amount")
    assert ans["grounded"] is True
    assert "450" in ans["prose"]


def test_answer_unknown_kpi():
    a = DataOpsMemoryAgent()
    ans = a.answer("nonexistent")
    assert ans["receipts"] == []
