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
    created: str = ""  # ISO ts the plan was authored — used for decay/staleness


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def deprecated_plan_ids(ledger: Ledger) -> set[str]:
    """Plan ids that have been tombstoned (timely forgetting)."""
    return {e.payload["plan_id"] for e in ledger.fetch("plan.deprecated")}


def best_candidate(ledger: Ledger, profile: dict[str, Any]) -> Match | None:
    """Best reusable, **non-deprecated** prior plan for this profile.

    Deprecated plans are excluded (forgetting bites at recall, not just in
    storage). Exact schema fingerprint short-circuits to similarity 1.0;
    otherwise the best Jaccard over column sets. The reuse-vs-escalate *decision*
    is left to the triage worker (see ``triage.py``).
    """
    dead = deprecated_plan_ids(ledger)
    best: Match | None = None
    cur_cols = set(profile["column_names"])
    for e in ledger.fetch("plan.authored"):
        p = e.payload
        if p["plan_id"] in dead:
            continue  # tombstoned -> forgotten for recall purposes
        cols = p.get("column_names", [])
        created = p.get("created", e.ts.isoformat())
        if p.get("fingerprint") == profile["fingerprint"]:
            return Match(p["plan_id"], p["ops"], 1.0, p["fingerprint"], cols, created)
        sim = _jaccard(cur_cols, set(cols))
        if best is None or sim > best.similarity:
            best = Match(p["plan_id"], p["ops"], sim, p.get("fingerprint", ""),
                         cols, created)
    return best
