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


def make_noisy_run(n_sessions: int = 8, drift_at: tuple[int, ...] = (5,)) -> list[Session]:
    """Stable sessions carry small deterministic noise (~±8%); drift sessions jump
    ~+50%. A too-sensitive drift threshold false-alarms on the noise, a too-loose
    one misses the drift — so there's a real optimum to tune toward.
    """
    # alternating West amount -> stable total alternates 750 / 810 (~8% swing)
    wiggle = [0, 60, 0, 60, 0, 60, 0, 60]
    sessions: list[Session] = []
    for i in range(1, n_sessions + 1):
        is_drift = i in drift_at
        sales = [("North", "Widget", 100), ("South", "Gadget", 200),
                 ("East", "Widget", 300), ("West", "Gadget", 150 + wiggle[(i - 1) % 8])]
        rows = _messy(sales, dirt=2 if i == 1 else (i % 2) + 1)
        if is_drift:
            rows.append(("East", "Widget", 380))  # ~+50% on a 750 base
        sessions.append(
            Session(name=f"s{i}{'*drift' if is_drift else ''}",
                    df=pd.DataFrame(rows, columns=COLS), is_drift=is_drift)
        )
    return sessions


def make_schema_drift_run(n_sessions: int = 9) -> list[Session]:
    """Sessions whose *column set* varies (every 3rd week adds a cosmetic 'note'
    column) → non-exact recall, so the cascade's reuse-threshold actually gates.
    Used to tune the escalation threshold. No KPI drift (is_drift=False)."""
    sessions: list[Session] = []
    sales = [("North", "Widget", 100), ("South", "Gadget", 200), ("West", "Gadget", 150)]
    for i in range(1, n_sessions + 1):
        rows = _messy(sales, dirt=2 if i == 1 else 1)
        if i % 3 == 0:  # gray-zone: extra column shifts the schema fingerprint
            df = pd.DataFrame([(r[0], r[1], r[2], "vip") for r in rows],
                              columns=COLS + ["note"])
        else:
            df = pd.DataFrame(rows, columns=COLS)
        sessions.append(Session(name=f"s{i}", df=df, is_drift=False))
    return sessions


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
