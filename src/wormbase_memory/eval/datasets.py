"""Deterministic, labeled multi-session generator for the consistency harness.

Each "stable" session is the same true sales rendered with different dirt (so a
correct agent reproduces the same KPI); each "drift" session injects a whale row
(so a correct agent flags drift). Ground-truth drift labels let us score
drift-detection precision/recall. No randomness — reproducibility is the point.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

COLS = ["region", "product", "amount"]
# The true sales every stable session cleans down to: total = 750, rows = 4.
TRUE_SALES = [
    ("North", "Widget", 100),
    ("South", "Gadget", 200),
    ("East", "Widget", 300),
    ("West", "Gadget", 150),
]


@dataclass
class Session:
    name: str
    df: pd.DataFrame
    is_drift: bool


def _messy(sales: list[tuple], dirt: int) -> list[tuple]:
    """Render each true sale as >=2 case/whitespace variants (+ optional null)."""
    rows: list[tuple] = []
    for region, product, amount in sales:
        rows.append((f" {region}", product, amount))           # leading ws
        rows.append((region.lower() + " ", product, amount))   # lower + trailing ws
        if dirt > 1:
            rows.append((region.upper(), product, amount))     # upper variant
    if dirt > 0:
        rows.append(("East", "Widget", None))                  # null measure -> dropped
    return rows


def make_run(n_sessions: int = 6, drift_at: tuple[int, ...] = (4,)) -> list[Session]:
    """n_sessions, with drift injected at the given 1-based session indices."""
    sessions: list[Session] = []
    for i in range(1, n_sessions + 1):
        is_drift = i in drift_at
        # session 1 uses full variant coverage so the authored plan learns every region
        dirt = 2 if i == 1 else (i % 2) + 1
        rows = _messy(TRUE_SALES, dirt)
        if is_drift:
            rows.append(("East", "Widget", 5000))  # the whale -> KPI jumps
        sessions.append(
            Session(name=f"s{i}{'*drift' if is_drift else ''}",
                    df=pd.DataFrame(rows, columns=COLS), is_drift=is_drift)
        )
    return sessions
