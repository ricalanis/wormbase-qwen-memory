"""Recall: "have we cleaned data shaped like this before?"

Reads prior ``plan.authored`` entries from the ledger and finds the best match
for the current profile. Exact schema fingerprint -> similarity 1.0 (cheap,
deterministic reuse); otherwise Jaccard over column sets. This is the
small/local-model's job conceptually — here it is deterministic so reuse is
reproducible; a local Qwen can refine the similarity score when enabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ledger import Ledger


@dataclass
class Match:
    plan_id: str
    ops: list[dict[str, Any]]
    similarity: float
    fingerprint: str
    column_names: list[str]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def best_candidate(ledger: Ledger, profile: dict[str, Any]) -> Match | None:
    """Best reusable prior plan for this profile — no threshold applied.

    Exact schema fingerprint short-circuits to similarity 1.0; otherwise the best
    Jaccard over column sets. The reuse-vs-escalate *decision* is left to the
    triage worker (see ``triage.py``), which is where the local Qwen earns its keep.
    """
    best: Match | None = None
    cur_cols = set(profile["column_names"])
    for e in ledger.fetch("plan.authored"):
        p = e.payload
        cols = p.get("column_names", [])
        if p.get("fingerprint") == profile["fingerprint"]:
            return Match(p["plan_id"], p["ops"], 1.0, p["fingerprint"], cols)
        sim = _jaccard(cur_cols, set(cols))
        if best is None or sim > best.similarity:
            best = Match(p["plan_id"], p["ops"], sim, p.get("fingerprint", ""), cols)
    return best
