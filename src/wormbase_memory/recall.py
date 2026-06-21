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

REUSE_THRESHOLD = 0.9


@dataclass
class Match:
    plan_id: str
    ops: list[dict[str, Any]]
    similarity: float
    fingerprint: str


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def find(ledger: Ledger, profile: dict[str, Any]) -> Match | None:
    best: Match | None = None
    cur_cols = set(profile["column_names"])
    for e in ledger.fetch("plan.authored"):
        p = e.payload
        if p.get("fingerprint") == profile["fingerprint"]:
            return Match(p["plan_id"], p["ops"], 1.0, p["fingerprint"])
        sim = _jaccard(cur_cols, set(p.get("column_names", [])))
        if best is None or sim > best.similarity:
            best = Match(p["plan_id"], p["ops"], sim, p.get("fingerprint", ""))
    if best and best.similarity >= REUSE_THRESHOLD:
        return best
    return None
