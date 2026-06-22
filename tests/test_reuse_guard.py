"""Verifier-gate on plan reuse: reject stale plans, re-author correctly."""

from __future__ import annotations

import pandas as pd

from wormbase_memory import reuse_guard
from wormbase_memory.agent import DataOpsMemoryAgent

_COLS = ["region", "product", "amount"]


def _df(rows):
    return pd.DataFrame(rows, columns=_COLS)


# -- unit: the check itself --------------------------------------------------

def test_check_passes_on_clean_data():
    df = _df([("North", "Widget", 100), ("South", "Gadget", 200)])
    ops = [{"op": "dedup", "subset": None},
           {"op": "define_kpi", "id": "total_amount", "agg": "sum", "column": "amount"}]
    ok, why = reuse_guard.check(df, ops)
    assert ok, why


def test_check_detects_residual_variants():
    df = _df([("west", "Gadget", 150), ("West", "Gadget", 150)])
    ops = [{"op": "strip_whitespace", "columns": ["region"]}, {"op": "dedup", "subset": None}]
    ok, why = reuse_guard.check(df, ops)
    assert not ok and "variant" in why


def test_check_detects_missing_column():
    df = pd.DataFrame([("North", 100)], columns=["region", "amount"])
    ops = [{"op": "canonicalize", "column": "product", "mapping": {}}]
    ok, why = reuse_guard.check(df, ops)
    assert not ok and "missing" in why


# -- end-to-end: the gate prevents a stale-plan regression -------------------

def test_gate_rejects_stale_plan_and_reauthors_correctly():
    a = DataOpsMemoryAgent()
    # s1: West appears only once -> the authored canonicalize mapping never learns it
    s1 = _df([(" North", "Widget", 100), ("north ", "Widget", 100),
              ("South", "Gadget", 200), ("SOUTH", "Gadget", 200),
              ("West", "Gadget", 150)])
    a.ingest(s1, "s1")
    # s2: West now arrives as "west" + "West" -> the stale plan would leave them
    # unmerged (West region double-counted -> total 600 instead of 450)
    s2 = _df([("North", "Widget", 100), ("South", "Gadget", 200),
              ("west", "Gadget", 150), ("West", "Gadget", 150)])
    r2 = a.ingest(s2, "s2")

    assert r2.reused is False                      # gate blocked the stale reuse
    assert r2.reuse_rejected is True
    assert a.ledger.fetch("plan.reuse_rejected")   # auditable
    assert a.ledger.fetch("plan.deprecated")       # stale plan tombstoned
    assert r2.kpis["total_amount"] == 450.0        # re-authored plan merges west/West
    assert a.verify()[0] is True


def test_gate_allows_healthy_reuse():
    a = DataOpsMemoryAgent()
    base = _df([(" North", "Widget", 100), ("north ", "Widget", 100),
                ("South", "Gadget", 200), ("SOUTH", "Gadget", 200),
                ("West", "Gadget", 150), ("west", "Gadget", 150)])
    a.ingest(base, "s1")
    r2 = a.ingest(base, "s2")  # identical, well-covered plan
    assert r2.reused is True and r2.reuse_rejected is False
