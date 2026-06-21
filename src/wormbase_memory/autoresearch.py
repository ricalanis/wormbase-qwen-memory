"""Metric-governed self-improvement loop (WormBase autoresearch, Track-1 honest).

The agent tunes its own drift-sensitivity to maximize drift-detection F1 on a
labeled session set, then *remembers* the better setting as a preference. The
whole loop is a PEVR cycle written to the ledger, so the self-improvement is
itself auditable and replayable. No API spend — it replays deterministic ops.
"""

from __future__ import annotations

from typing import Any

from .agent import DataOpsMemoryAgent
from .eval import consistency
from .eval.datasets import Session

DEFAULT_CANDIDATES = (0.05, 0.10, 0.15, 0.20, 0.30, 0.50)


def score_thresholds(
    sessions: list[Session], candidates=DEFAULT_CANDIDATES
) -> list[dict[str, Any]]:
    """F1 of drift detection at each candidate threshold (deterministic)."""
    trials = []
    for c in candidates:
        f1 = consistency.run_once(sessions, drift_threshold=c)["drift"]["f1"]
        trials.append({"threshold": c, "f1": f1})
    return trials


def tune(
    agent: DataOpsMemoryAgent, sessions: list[Session],
    current_threshold: float = 0.05, candidates=DEFAULT_CANDIDATES,
) -> dict[str, Any]:
    """Find the best drift threshold, and if it beats the current one, remember it.

    Written as propose -> execute -> verify -> resolve on the agent's ledger.
    """
    baseline_f1 = consistency.run_once(
        sessions, drift_threshold=current_threshold)["drift"]["f1"]

    def _execute() -> dict[str, Any]:
        trials = score_thresholds(sessions, candidates)
        best = max(trials, key=lambda t: t["f1"])
        return {"trials": trials, "best": best, "baseline_f1": baseline_f1,
                "current_threshold": current_threshold}

    def _verify(result: dict[str, Any]) -> bool:
        # only adopt a strictly better setting
        return result["best"]["f1"] > result["baseline_f1"]

    result, improved = agent.ledger.write_pevr(
        "autoresearch",
        propose={"metric": "drift_f1", "candidates": list(candidates),
                 "current_threshold": current_threshold},
        execute_fn=_execute,
        verify_fn=_verify,
    )
    if improved:
        best_t = result["best"]["threshold"]
        agent.set_preference("drift_threshold", best_t)
        agent.ledger.append("policy.tuned",
                            {"param": "drift_threshold",
                             "from": current_threshold, "to": best_t,
                             "f1_from": result["baseline_f1"],
                             "f1_to": result["best"]["f1"]})
    return {**result, "improved": improved}
