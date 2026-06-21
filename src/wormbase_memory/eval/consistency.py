"""Cross-session consistency harness — the project's headline contribution.

Runs labeled multi-session data-ops and reports the four submission KPIs:
  1. reproducibility_rate  — identical value_hash for identical input (target 1.0)
  2. plan_reuse_rate       — fraction of post-first sessions that reused a plan
  3. planner_cost_reduction— cost saved by reuse vs authoring every session
  4. drift precision/recall— vs ground-truth injected drift
plus run-to-run stability (K fresh runs -> identical value_hash sequences) and
hash-chain integrity. Scoring is deterministic, so any variance is the agent's.
"""

from __future__ import annotations

from typing import Any

from .. import profiler
from ..agent import DataOpsMemoryAgent
from ..planner import _estimate_cost_units
from .datasets import Session, make_run


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}


def run_once(sessions: list[Session],
             drift_threshold: float | None = None) -> dict[str, Any]:
    agent = DataOpsMemoryAgent()
    if drift_threshold is not None:
        agent.set_preference("drift_threshold", drift_threshold)
    rows, would_be, actual = [], 0, 0
    tp = fp = fn = 0
    for i, s in enumerate(sessions):
        rep = agent.ingest(s.df, s.name)
        wb = _estimate_cost_units(profiler.profile(s.df))  # cost if it HAD to author
        would_be += wb
        actual += rep.planner_cost_units
        flagged = "total_amount" in rep.drift
        if i > 0:  # session 1 has no prior, cannot drift
            if s.is_drift and flagged:
                tp += 1
            elif s.is_drift and not flagged:
                fn += 1
            elif not s.is_drift and flagged:
                fp += 1
        rows.append({"session": s.name, "reused": rep.reused,
                     "cost": rep.planner_cost_units, "total_amount": rep.kpis.get("total_amount"),
                     "drift_flagged": flagged, "is_drift": s.is_drift})

    reused_n = sum(1 for r in rows[1:] if r["reused"])
    return {
        "n_sessions": len(sessions),
        "reproducibility_rate": round(agent.reproducibility_rate(), 4),
        "plan_reuse_rate": round(reused_n / max(1, len(rows) - 1), 4),
        "planner_cost_reduction": round(1 - actual / would_be, 4) if would_be else 0.0,
        "planner_cost_units_actual": actual,
        "planner_cost_units_would_be": would_be,
        "drift": _prf(tp, fp, fn),
        "hash_chain_ok": agent.verify()[0],
        "ledger_entries": len(agent.ledger.fetch()),
        "rows": rows,
    }


def run_stability(sessions: list[Session], k: int = 5) -> dict[str, Any]:
    """K independent fresh runs must yield identical value_hash sequences."""
    seqs = []
    for _ in range(k):
        agent = DataOpsMemoryAgent()
        for s in sessions:
            agent.ingest(s.df, s.name)
        seqs.append(tuple(h["value_hash"] for h in agent.kpi_history("total_amount")))
    return {"runs": k, "all_identical": len(set(seqs)) == 1,
            "distinct_sequences": len(set(seqs))}


def evaluate(n_sessions: int = 6, drift_at: tuple[int, ...] = (4,),
             k: int = 5) -> dict[str, Any]:
    sessions = make_run(n_sessions, drift_at)
    report = run_once(sessions)
    report["stability"] = run_stability(sessions, k)
    return report
