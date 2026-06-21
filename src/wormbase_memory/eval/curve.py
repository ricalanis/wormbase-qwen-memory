"""'Gets smarter + cheaper over sessions' — the Track-1 learning curve.

Compares memory-ON (one agent accumulating a ledger) vs memory-OFF (a fresh
agent each session). Memory-ON reuses plans (cost -> 0) and has a baseline to
judge drift correctly; memory-OFF re-authors every time and cannot detect
cross-session drift. The two curves make 'increasingly accurate decisions across
sessions' visible.
"""

from __future__ import annotations

from typing import Any

from ..agent import DataOpsMemoryAgent
from .datasets import Session, make_run


def _decision_correct(flagged: bool, is_drift: bool) -> bool:
    return flagged == is_drift


def series(sessions: list[Session]) -> dict[str, list[dict[str, Any]]]:
    # memory ON — one agent accumulates experience
    on: list[dict[str, Any]] = []
    agent = DataOpsMemoryAgent()
    correct = 0
    for i, s in enumerate(sessions):
        r = agent.ingest(s.df, s.name)
        correct += _decision_correct("total_amount" in r.drift, s.is_drift)
        on.append({"session": i + 1, "cost": r.planner_cost_units,
                   "cum_accuracy": round(correct / (i + 1), 4)})

    # memory OFF — fresh agent each session, no accumulation
    off: list[dict[str, Any]] = []
    correct = 0
    for i, s in enumerate(sessions):
        a = DataOpsMemoryAgent()
        r = a.ingest(s.df, s.name)  # no prior -> always authors, never detects drift
        correct += _decision_correct("total_amount" in r.drift, s.is_drift)
        off.append({"session": i + 1, "cost": r.planner_cost_units,
                    "cum_accuracy": round(correct / (i + 1), 4)})
    return {"on": on, "off": off}


def evaluate(n_sessions: int = 8, drift_at: tuple[int, ...] = (4, 7)) -> dict[str, Any]:
    return series(make_run(n_sessions, drift_at))
