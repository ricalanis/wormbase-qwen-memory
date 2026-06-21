"""The local small-Qwen triage worker — the cheap recall gatekeeper.

Decides reuse-vs-escalate for a candidate prior plan:
- exact schema fingerprint        -> REUSE, free (no model call)
- no candidate                    -> ESCALATE (nothing to reuse)
- gray zone (similar, not exact)  -> ask the small LOCAL Qwen: "same kind of
                                     data? reuse the plan?" — and only escalate
                                     to Qwen-Plus (the expensive brain) if it says
                                     novel/drifted.

This is the orchestrator-worker cascade (FrugalGPT-style, arXiv 2305.05176):
a small cheap model triages, the big model is invoked only when needed. Every
decision is auditable. Degrades to a deterministic threshold when no local Qwen
is available, so tests and the offline demo always run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .inference import LocalQwenClient, loads_lenient
from .recall import Match

# In the gray zone with no local model, reuse iff column-set similarity >= this.
DETERMINISTIC_REUSE_THRESHOLD = 0.9

TRIAGE_SYSTEM = (
    "You are a fast data-triage worker. You are shown the COLUMNS of a new table "
    "and the COLUMNS of a previously-cleaned table whose cleaning plan we cached. "
    "Decide if the new table is the SAME KIND of data, so we can safely reuse the "
    "cached plan instead of re-planning. Reply ONLY with JSON: "
    '{"reuse": true|false, "reason": "<short>"}.'
)


@dataclass
class Decision:
    reuse: bool
    similarity: float
    backend: str       # "exact" | "none" | "local-qwen:<model>" | "rules"
    tokens: int
    reason: str
    candidate: Match | None


class Triage:
    def __init__(self, local_client: Any | None = None) -> None:
        # duck-typed: needs .available and .chat(messages, **kw) -> ChatResult
        self.local = local_client if local_client is not None else LocalQwenClient()

    def decide(self, profile: dict[str, Any], candidate: Match | None) -> Decision:
        if candidate is None:
            return Decision(False, 0.0, "none", 0, "no prior plan to reuse", None)
        if candidate.similarity >= 1.0:
            return Decision(True, 1.0, "exact", 0,
                            "exact schema fingerprint match", candidate)
        # gray zone
        if getattr(self.local, "available", False):
            try:
                return self._decide_with_local(profile, candidate)
            except Exception:
                pass  # fall through to deterministic rule
        reuse = candidate.similarity >= DETERMINISTIC_REUSE_THRESHOLD
        op = ">=" if reuse else "<"
        return Decision(reuse, candidate.similarity, "rules", 0,
                        f"similarity {candidate.similarity:.2f} {op} "
                        f"{DETERMINISTIC_REUSE_THRESHOLD}", candidate)

    def _decide_with_local(self, profile: dict[str, Any], candidate: Match) -> Decision:
        user = (
            f"NEW columns: {profile['column_names']}\n"
            f"CACHED columns: {candidate.column_names}\n"
            f"Column-set similarity: {candidate.similarity:.2f}"
        )
        res = self.local.chat(
            [{"role": "system", "content": TRIAGE_SYSTEM},
             {"role": "user", "content": user}],
            temperature=0.0, max_tokens=128,
            response_format={"type": "json_object"},
        )
        data = loads_lenient(res.text)
        return Decision(
            reuse=bool(data.get("reuse")),
            similarity=candidate.similarity,
            backend=res.backend,
            tokens=res.tokens,
            reason=str(data.get("reason", ""))[:200],
            candidate=candidate,
        )
