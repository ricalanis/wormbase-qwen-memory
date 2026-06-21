"""Lock the headline consistency numbers."""

from __future__ import annotations

from wormbase_memory.eval.consistency import evaluate


def test_consistency_headline_numbers():
    r = evaluate(n_sessions=6, drift_at=(4,), k=5)
    assert r["reproducibility_rate"] == 1.0
    assert r["plan_reuse_rate"] == 1.0
    assert r["planner_cost_reduction"] > 0.5      # reuse meaningfully cheaper
    assert r["drift"]["f1"] == 1.0                # perfect drift detection on this set
    assert r["stability"]["all_identical"] is True
    assert r["hash_chain_ok"] is True


def test_no_false_drift_on_return_to_baseline():
    # session after a whale returns to normal -> must NOT be flagged
    r = evaluate(n_sessions=6, drift_at=(4,), k=1)
    after_whale = next(row for row in r["rows"] if row["session"] == "s5")
    assert after_whale["drift_flagged"] is False
