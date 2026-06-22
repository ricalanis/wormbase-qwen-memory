"""Analyst slice: metric-change attribution (efficiency axiom) + grounded narrative."""

from __future__ import annotations

import pandas as pd

from wormbase_memory import analysis, narrative
from wormbase_memory.agent import DataOpsMemoryAgent


def test_explain_change_efficiency_axiom():
    base = {"region": {"North": 100.0, "South": 200.0, "West": 150.0}}
    cur = {"region": {"North": 100.0, "South": 200.0, "West": 150.0, "East": 2000.0}}
    expl = analysis.explain_change(base, cur)
    assert expl["dim"] == "region"
    # contributions sum exactly to the total change (450 -> 2450 = +2000)
    assert round(sum(d["delta"] for d in expl["drivers"]), 6) == 2000.0
    assert expl["drivers"][0]["value"] == "East"
    assert expl["drivers"][0]["delta"] == 2000.0
    assert expl["drivers"][0]["pct_of_change"] == 1.0


def test_narrative_is_grounded_and_rejects_fabrication():
    expl = {"dim": "region", "total_change": 2000.0,
            "drivers": [{"value": "East", "delta": 2000.0, "pct_of_change": 1.0}]}
    text = narrative.render_change_narrative("total_amount", 450, 2450, expl)
    allowed = narrative.allowed_numbers(450, 2450, 2000)
    assert narrative.is_grounded(text, allowed) is True
    # a fabricated magnitude must be caught
    assert narrative.is_grounded("total_amount hit 9999.", allowed) is False


def _df(rows):
    return pd.DataFrame(rows, columns=["region", "product", "amount"])


def test_transient_spike_vs_sustained_shift():
    """A one-off spike flags once then returns quietly; a sustained shift flags
    once then is accepted as the new normal (re-baselined)."""
    a = DataOpsMemoryAgent()

    def rev(west):  # total = 100 + 200 + west
        return _df([("North", "Widget", 100), ("South", "Gadget", 200),
                    ("West", "Gadget", west)])

    a.ingest(rev(150), "w1")          # baseline 450
    r2 = a.ingest(rev(155), "w2")     # 455, ~+1% -> no drift
    r3 = a.ingest(rev(2000), "w3-spike")   # 2300, spike -> DRIFT
    r4 = a.ingest(rev(150), "w4-back")     # 450 again -> NOT flagged (transient)
    assert "total_amount" in r3.drift
    assert "total_amount" not in r4.drift

    a2 = DataOpsMemoryAgent()
    a2.ingest(rev(150), "s1")         # 450
    s2 = a2.ingest(rev(700), "s2-shift")   # 1000, +122% -> DRIFT
    s3 = a2.ingest(rev(705), "s3-newnormal")  # 1005, stayed -> accepted, NOT flagged
    s4 = a2.ingest(rev(710), "s4")    # 1010 -> still fine vs new baseline
    assert "total_amount" in s2.drift
    assert "total_amount" not in s3.drift   # sustained shift re-baselined
    assert "total_amount" not in s4.drift


def test_agent_explains_drift_end_to_end():
    a = DataOpsMemoryAgent()
    base = _df([("North", "Widget", 100), ("South", "Gadget", 200),
                ("West", "Gadget", 150)])
    whale = _df([("North", "Widget", 100), ("South", "Gadget", 200),
                 ("West", "Gadget", 150), ("East", "Widget", 2000)])
    a.ingest(base, "s1")
    r = a.ingest(whale, "s2-drift")
    assert "total_amount" in r.drift
    assert r.explanations, "drift must produce an explanation"
    assert "East" in r.explanations[0]
    # the explanation + insight are auditable ledger entries
    assert a.ledger.fetch("kpi.explained")
    ins = [e.payload for e in a.ledger.fetch("insight.generated")
           if e.payload["id"] == "total_amount"]
    assert ins and "East" in ins[-1]["narrative"]
    # narrative is grounded in ledger numbers
    allowed = narrative.allowed_numbers(450, 2450, 2000, 100, 200, 150)
    assert narrative.is_grounded(ins[-1]["narrative"], allowed)
    assert a.verify()[0] is True
