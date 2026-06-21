"""A deterministic 3-session demo that tells the whole story:

S1  novel data        -> plan AUTHORED, KPIs computed
S2  same shape, dirtier-but-equivalent sales -> plan REUSED (0 planner cost),
                         KPI STABLE
S3  a big new customer -> plan REUSED, KPI DRIFT FLAGGED (not silently changed)
+   re-ingest S1 -> identical value_hash (REPRODUCIBILITY)

No randomness anywhere — the point is byte-for-byte reproducibility.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from .agent import DataOpsMemoryAgent

_COLS = ["region", "product", "amount"]


def _df(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=_COLS)


def sessions() -> list[tuple[str, pd.DataFrame, datetime]]:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    # The TRUE sales each session cleans down to: North 100, South 200, West 150.
    # Every region appears with >=2 case/whitespace variants so the authored plan
    # learns a canonicalization for each one.
    s1 = _df([
        (" North", "Widget", 100),
        ("north ", "Widget", 100),     # whitespace-dup of the same sale
        ("South", "Gadget", 200),
        ("SOUTH", "Gadget", 200),       # case-dup
        ("West", "Gadget", 150),
        ("west", "Gadget", 150),        # case-dup
        ("East", "Widget", None),       # null measure -> dropped
    ])
    # Same real sales, messier formatting -> reused plan cleans to the same total.
    s2 = _df([
        ("NORTH", "Widget", 100),
        ("  north", "Widget", 100),
        ("south ", "Gadget", 200),
        ("South", "Gadget", 200),
        ("West ", "Gadget", 150),
        ("west", "Gadget", 150),
    ])
    # Drift: a big new customer lands -> revenue jumps well beyond threshold.
    s3 = _df([
        ("North", "Widget", 100),
        ("South", "Gadget", 200),
        ("West", "Gadget", 150),
        ("East", "Widget", 2000),       # the new whale
    ])
    return [
        ("Week 1 · first Monday", s1, t0),
        ("Week 2 · same shape", s2, t0 + timedelta(days=7)),
        ("Week 3 · new customer", s3, t0 + timedelta(days=14)),
    ]


def run(agent: DataOpsMemoryAgent | None = None) -> DataOpsMemoryAgent:
    agent = agent or DataOpsMemoryAgent()
    for name, df, ts in sessions():
        r = agent.ingest(df, dataset=name, ts=ts)
        tag = "REUSED " if r.reused else f"AUTHORED({r.plan_backend})"
        drift = f"  ⚠ DRIFT {r.drift}" if r.drift else ""
        print(
            f"{name:26s} | plan={tag:18s} cost={r.planner_cost_units:4d} "
            f"| rows {r.rows_in}->{r.rows_out} | KPIs={r.kpis}{drift}"
        )
        for narr in r.explanations:  # analyst layer: explain WHY it moved
            print(f"    ↳ {narr}")

    # Reproducibility: re-ingest session-1's exact data; value_hash must match.
    s1_name, s1_df, s1_ts = sessions()[0]
    before = {h["input_hash"]: h["value_hash"] for h in agent.kpi_history("total_amount")}
    agent.ingest(s1_df, dataset="session-1 (replay)", ts=s1_ts + timedelta(days=3))
    after = agent.kpi_history("total_amount")[-1]
    repro_ok = after["value_hash"] == before.get(after["input_hash"])

    ok, broken = agent.verify()
    print("-" * 78)
    print(f"hash-chain verify : {'GREEN ✓' if ok else f'BROKEN at {broken}'}")
    print(f"reproducibility   : {agent.reproducibility_rate():.0%}  "
          f"(S1 replay value_hash match: {'YES ✓' if repro_ok else 'NO ✗'})")
    print(f"ledger entries    : {len(agent.ledger.fetch())}")
    return agent
