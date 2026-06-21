"""Agent invariants: authoring, reuse, reproducibility, drift, replay."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.demo import sessions


def _toy(amount_west: int = 150) -> pd.DataFrame:
    return pd.DataFrame(
        [(" North", "Widget", 100), ("north ", "Widget", 100),
         ("South", "Gadget", 200), ("West", "Gadget", amount_west)],
        columns=["region", "product", "amount"],
    )


def test_first_session_authors_then_second_reuses():
    a = DataOpsMemoryAgent()
    r1 = a.ingest(_toy(), "s1")
    r2 = a.ingest(_toy(), "s2")
    assert r1.reused is False
    assert r2.reused is True
    assert r2.planner_cost_units == 0  # reuse is free -> cheaper over time
    assert a.verify()[0] is True


def test_cleaning_dedups_and_drops_nulls():
    a = DataOpsMemoryAgent()
    r = a.ingest(_toy(), "s1")
    # North dup collapses; all rows have amounts -> 3 unique sales
    assert r.rows_out == 3
    assert r.kpis["total_amount"] == 450.0


def test_reproducibility_identical_value_hash():
    a = DataOpsMemoryAgent()
    a.ingest(_toy(), "s1")
    a.ingest(_toy(), "s1-again")
    hist = a.kpi_history("total_amount")
    assert hist[0]["value_hash"] == hist[1]["value_hash"]
    assert a.reproducibility_rate() == 1.0


def test_drift_is_flagged_not_silent():
    a = DataOpsMemoryAgent()
    a.ingest(_toy(), "s1")
    r = a.ingest(_toy(amount_west=5000), "s2-whale")  # revenue jumps
    assert "total_amount" in r.drift
    flags = [e for e in a.ledger.fetch("kpi.drift_flagged")]
    assert len(flags) >= 1
    # the new value is still recorded (flagged, not suppressed)
    assert a.kpi_history("total_amount")[-1]["value"] == 5300.0


def test_replay_reconstructs_past_kpis():
    a = DataOpsMemoryAgent()
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    a.ingest(_toy(), "s1", ts=t0)
    a.ingest(_toy(amount_west=5000), "s2", ts=t0 + timedelta(days=1))
    as_of_day1 = a.ledger.replay_until(t0)
    computed = [e for e in as_of_day1 if e.kind == "kpi.computed"
                and e.payload["id"] == "total_amount"]
    assert [c.payload["value"] for c in computed] == [450.0]


def test_full_demo_runs_green():
    a = DataOpsMemoryAgent()
    for name, df, ts in sessions():
        a.ingest(df, name, ts=ts)
    assert a.verify()[0] is True
    assert a.reproducibility_rate() == 1.0
