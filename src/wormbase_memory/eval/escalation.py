"""Escalation-threshold tuning for the recall→reuse cascade (backlog #5).

Sweeps the reuse-similarity threshold and reports the cost-accuracy trade-off:
a lower threshold reuses more aggressively (fewer escalations → fewer tokens),
which is now SAFE because the verifier-gate (reuse_guard) rejects any stale reuse.
Recommends the lowest threshold that preserves full correctness — the
success@cost-optimal operating point — and can persist it as a preference.
"""

from __future__ import annotations

from typing import Any

from ..agent import DataOpsMemoryAgent
from .datasets import make_schema_drift_run

DEFAULT_THRESHOLDS = (0.5, 0.75, 0.9, 1.01)  # 1.01 = reuse only on exact match


def sweep(thresholds=DEFAULT_THRESHOLDS) -> dict[str, Any]:
    sessions = make_schema_drift_run(9)
    rows = []
    for thr in thresholds:
        agent = DataOpsMemoryAgent()
        agent.set_preference("reuse_threshold", thr)
        tokens = escalations = rejects = 0
        for i, s in enumerate(sessions):
            r = agent.ingest(s.df, s.name)
            tokens += r.planner_cost_units
            escalations += int(not r.reused)
            rejects += int(r.reuse_rejected)
        rows.append({
            "threshold": thr,
            "tokens": tokens,
            "escalation_rate": round(escalations / len(sessions), 4),
            "reuse_rejected": rejects,
            "chain_ok": agent.verify()[0],
            "reproducibility": round(agent.reproducibility_rate(), 4),
        })
    # success@cost: cheapest threshold that keeps full correctness
    valid = [r for r in rows if r["chain_ok"] and r["reproducibility"] == 1.0]
    best = min(valid, key=lambda r: r["tokens"]) if valid else None
    return {"rows": rows, "recommended": best["threshold"] if best else None,
            "min_tokens": best["tokens"] if best else None}


def tune(agent: DataOpsMemoryAgent, thresholds=DEFAULT_THRESHOLDS) -> dict[str, Any]:
    """Find the success@cost-optimal threshold and remember it as a preference
    (auditable PEVR commit + policy.tuned), mirroring autoresearch."""
    def _execute() -> dict[str, Any]:
        return sweep(thresholds)

    result, ok = agent.ledger.write_pevr(
        "escalation_tune",
        propose={"param": "reuse_threshold", "candidates": list(thresholds)},
        execute_fn=_execute,
        verify_fn=lambda r: r["recommended"] is not None,
    )
    if ok and result["recommended"] is not None:
        agent.set_preference("reuse_threshold", result["recommended"])
        agent.ledger.append("policy.tuned",
                            {"param": "reuse_threshold", "to": result["recommended"],
                             "min_tokens": result["min_tokens"]})
    return result
