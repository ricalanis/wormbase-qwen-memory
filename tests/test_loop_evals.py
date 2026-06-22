"""Loop-engineering evals: reliability-over-horizon (#1) + escalation tuning (#5)."""

from __future__ import annotations

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.eval import escalation, reliability
from wormbase_memory.preferences import current


# -- #1 reliability over horizon --------------------------------------------

def test_reliability_memory_on_holds_over_horizon():
    r = reliability.evaluate(horizons=(3, 5, 9, 12), k=3)
    # governed memory: accuracy stays ~1.0 across all horizons (no decay)
    assert r["on_graceful"] is True
    assert r["on_min_accuracy"] == 1.0
    assert r["passk_on"] == 1.0
    for row in r["rows"]:
        assert row["decision_acc_on"] >= row["decision_acc_off"]   # ON >= OFF always
        assert row["cost_on"] <= row["cost_off"]                    # cheaper too


def test_reliability_off_degrades_at_long_horizon():
    r = reliability.evaluate(horizons=(3, 12), k=1)
    long_on = r["rows"][-1]["decision_acc_on"]
    long_off = r["rows"][-1]["decision_acc_off"]
    assert long_on > long_off    # the baseline can't keep up over a long horizon


# -- #5 escalation-threshold tuning -----------------------------------------

def test_escalation_lower_threshold_saves_tokens_safely():
    s = escalation.sweep((0.5, 0.9, 1.01))
    by_thr = {r["threshold"]: r for r in s["rows"]}
    # aggressive reuse (low threshold) costs <= conservative, and stays correct
    assert by_thr[0.5]["tokens"] <= by_thr[0.9]["tokens"]
    for r in s["rows"]:
        assert r["chain_ok"] and r["reproducibility"] == 1.0   # gate keeps it correct
    # recommends the cheapest fully-correct threshold
    assert s["recommended"] == 0.5


def test_escalation_tune_persists_preference():
    a = DataOpsMemoryAgent()
    res = escalation.tune(a, (0.5, 0.9))
    assert res["recommended"] == 0.5
    assert current(a.ledger)["reuse_threshold"] == 0.5
    assert a.ledger.fetch("policy.tuned")
    assert a.verify()[0] is True
