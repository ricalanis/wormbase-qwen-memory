"""Learning curve + metric-governed self-improvement loop."""

from __future__ import annotations

from wormbase_memory import autoresearch
from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.eval import curve
from wormbase_memory.eval.datasets import make_noisy_run
from wormbase_memory.preferences import current


def test_curve_memory_on_beats_off():
    data = curve.evaluate(n_sessions=8, drift_at=(4, 7))
    on, off = data["on"], data["off"]
    # cheaper: memory-ON pays once then reuses (cost 0); memory-OFF re-authors each time
    assert on[-1]["cost"] == 0
    assert off[-1]["cost"] > 0
    # smarter: memory-ON ends more accurate (it can detect cross-session drift)
    assert on[-1]["cum_accuracy"] > off[-1]["cum_accuracy"]


def test_autoresearch_tunes_and_remembers():
    sessions = make_noisy_run(8, drift_at=(5,))
    trials = autoresearch.score_thresholds(sessions)
    # a too-sensitive threshold scores worse than a balanced one
    by_t = {t["threshold"]: t["f1"] for t in trials}
    assert by_t[0.05] < by_t[0.10]

    agent = DataOpsMemoryAgent()
    res = autoresearch.tune(agent, sessions, current_threshold=0.05)
    assert res["improved"] is True
    assert res["best"]["f1"] > res["baseline_f1"]
    # it remembered the better setting as a preference + recorded the policy change
    assert current(agent.ledger)["drift_threshold"] == res["best"]["threshold"]
    assert agent.ledger.fetch("policy.tuned")
    assert agent.verify()[0] is True
