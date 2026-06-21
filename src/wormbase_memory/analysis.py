"""Deterministic business-analysis ops — the 'why did it move?' keystone.

`explain_change` decomposes a KPI change across dimensions by diffing two
sessions' stored breakdowns. For additive metrics each dimension's value-deltas
sum exactly to ΔKPI (efficiency axiom), so the attribution is auditable — the
property that makes contribution analysis trustworthy in a ledger
(cf. mix/rate decomposition; Counterfactual-Shapley arXiv:2208.08399).
"""

from __future__ import annotations

from typing import Any

Breakdown = dict[str, dict[str, float]]  # {dim: {value: metric}}


def explain_change(baseline: Breakdown, current: Breakdown) -> dict[str, Any] | None:
    """Attribute a KPI change to dimension values.

    Picks the dimension whose top driver most concentrates the move, and returns
    that dimension's value-level contributions (each summing to the total change).
    Returns None if there is nothing to explain.
    """
    best: dict[str, Any] | None = None
    best_share = -1.0
    for dim, cur in current.items():
        base = baseline.get(dim, {})
        values = set(base) | set(cur)
        drivers = []
        for v in values:
            delta = round(cur.get(v, 0.0) - base.get(v, 0.0), 6)
            if delta != 0:
                drivers.append((v, delta))
        if not drivers:
            continue
        total = round(sum(d for _, d in drivers), 6)
        drivers.sort(key=lambda x: abs(x[1]), reverse=True)
        share = abs(drivers[0][1]) / abs(total) if total else 0.0
        if share > best_share:
            best_share = share
            best = {
                "dim": dim,
                "total_change": total,
                "drivers": [
                    {"value": v, "delta": d,
                     "pct_of_change": round(d / total, 4) if total else 0.0}
                    for v, d in drivers
                ],
            }
    return best
