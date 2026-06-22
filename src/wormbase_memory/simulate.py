"""A longer, richer, fully-deterministic simulation for the animated demo.

12 weeks of Maya's revenue review: a gentle uptrend (under the drift threshold,
so no false alarms), the plan authored once then reused, and two planted events —
a whale (week 6, drift up) and a churned account (week 10, drift down) — each of
which the agent flags and attributes. No randomness: replays byte-for-byte.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

COLS = ["region", "product", "amount"]
BASE = [("North", "Widget", 100), ("South", "Gadget", 200),
        ("East", "Widget", 150), ("West", "Gadget", 120)]
# tiny deterministic week-to-week wiggle (well under the 15% drift threshold)
_NOISE = [0, 3, -2, 4, -3, 2, -1, 3, -2, 1, 0, 2]


def _variants(region: str, week: int) -> list[str]:
    """Week 1 gives 2 case/whitespace variants per region (so the authored plan
    learns a canonicalization for each); later weeks use known variants."""
    if week == 1:
        return [f" {region}", region.lower() + " "]
    forms = [region, region.upper(), " " + region, region.lower() + " "]
    return [forms[week % len(forms)]]


def simulate_weeks(n: int = 12) -> list[dict]:
    t0 = datetime(2026, 1, 5, tzinfo=UTC)
    weeks: list[dict] = []
    for w in range(1, n + 1):
        g = 1 + 0.02 * (w - 1)                      # ~2%/week organic growth
        rows: list[tuple] = []
        for region, product, amt in BASE:
            if w >= 10 and region == "South":        # churn: lose South from wk10
                continue
            val = round(amt * g) + _NOISE[(w - 1) % len(_NOISE)]
            for rv in _variants(region, w):
                rows.append((rv, product, val))
        event = ""
        if w == 1:
            event = "first analysis — plan authored"
        if w == 6:                                   # whale lands
            whale = round(sum(round(a * g) for _, _, a in BASE) * 0.5)
            rows.append(("East", "Widget", whale))
            event = "🐳 new whale customer (East)"
        if w == 10:
            event = "📉 lost the South account"
        weeks.append({"week": w, "name": f"Week {w}",
                      "df": pd.DataFrame(rows, columns=COLS),
                      "ts": t0 + timedelta(days=7 * (w - 1)), "event": event})
    return weeks
