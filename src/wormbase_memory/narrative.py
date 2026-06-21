"""Communication layer — grounded narration of analysis results.

The default renderer is deterministic (templated), so it is faithful by
construction and free. `is_grounded` is the chain-of-custody check that also
applies when an LLM does the narration: every data magnitude in the prose must
appear in the ledger-derived allowed set (percentages, which are derived
deterministically from those magnitudes, are exempt). This turns faithfulness
into a deterministic test rather than an LLM judge
(cf. Hybrid LLM/Rule arXiv:2404.15604; DataNarrative arXiv:2408.05346).
"""

from __future__ import annotations

import re
from typing import Any


def _g(x: float) -> str:
    """Compact number format: 450 not 450.0, 2450 not 2450.0."""
    return f"{x:g}"


def render_change_narrative(
    kpi_id: str, baseline: float, new: float, explanation: dict[str, Any]
) -> str:
    pct = (new - baseline) / abs(baseline) if baseline else float("inf")
    top = explanation["drivers"][0]
    parts = [
        f"{kpi_id} changed {pct:+.0%} ({_g(baseline)} → {_g(new)}).",
        f"Largest driver: {explanation['dim']}={top['value']} "
        f"({_g(top['delta'])}, {top['pct_of_change']:+.0%} of the move).",
    ]
    others = explanation["drivers"][1:3]
    if others:
        parts.append(
            "Also: "
            + ", ".join(f"{d['value']} ({_g(d['delta'])})" for d in others)
            + "."
        )
    return " ".join(parts)


def allowed_numbers(*values: float) -> set[str]:
    return {_g(round(float(v), 6)) for v in values}


# a number, optionally with a trailing '%' (percentages are derived, exempt)
_NUM = re.compile(r"-?\d+(?:\.\d+)?%?")


def is_grounded(text: str, allowed: set[str]) -> bool:
    """Every non-percentage data magnitude in `text` must be in `allowed`."""
    for tok in _NUM.findall(text):
        if tok.endswith("%"):
            continue  # derived deterministically from grounded magnitudes
        if _g(float(tok)) not in allowed:  # normalize e.g. '450.0' -> '450'
            return False
    return True
