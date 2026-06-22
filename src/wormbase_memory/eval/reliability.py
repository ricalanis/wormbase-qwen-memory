"""Reliability-over-horizon instrumentation (loop-engineering backlog #1).

Beyond-pass@1 (arXiv 2603.29231) shows agent reliability decays as the task
horizon grows. This measures decision reliability vs the number of sessions, for
memory-ON vs memory-OFF, so any loop change is measurable per release. The
governed-memory claim: ON stays flat/high across horizons; OFF (no cross-session
baseline) plateaus lower because it cannot detect drift.
"""

from __future__ import annotations

from typing import Any

from ..agent import DataOpsMemoryAgent
from .curve import series
from .datasets import make_run


def _fully_correct(sessions) -> bool:
    """A run is fully correct iff every drift decision is right AND the chain
    verifies AND KPIs are reproducible (memory-ON)."""
    a = DataOpsMemoryAgent()
    ok = True
    for i, s in enumerate(sessions):
        r = a.ingest(s.df, s.name)
        if i > 0 and (("total_amount" in r.drift) != s.is_drift):
            ok = False
    return ok and a.verify()[0] and a.reproducibility_rate() == 1.0


def reliability_curve(horizons=(3, 5, 7, 9, 12), k: int = 5) -> list[dict[str, Any]]:
    rows = []
    for H in horizons:
        drift_at = tuple(range(4, H + 1, 4))  # a drift roughly every 4 weeks
        sessions = make_run(H, drift_at)
        s = series(sessions)
        # pass^k: repeat the ON run k times — deterministic governance → expect 1.0
        passk = sum(_fully_correct(sessions) for _ in range(k)) / k
        rows.append({
            "horizon": H,
            "decision_acc_on": s["on"][-1]["cum_accuracy"],
            "decision_acc_off": s["off"][-1]["cum_accuracy"],
            "cost_on": sum(r["cost"] for r in s["on"]),
            "cost_off": sum(r["cost"] for r in s["off"]),
            "passk_on": round(passk, 4),
        })
    return rows


def evaluate(horizons=(3, 5, 7, 9, 12), k: int = 5) -> dict[str, Any]:
    rows = reliability_curve(horizons, k)
    return {
        "rows": rows,
        "on_min_accuracy": min(r["decision_acc_on"] for r in rows),
        "off_min_accuracy": min(r["decision_acc_off"] for r in rows),
        "on_graceful": all(r["decision_acc_on"] >= 0.99 for r in rows),  # no decay
        "passk_on": min(r["passk_on"] for r in rows),
    }
