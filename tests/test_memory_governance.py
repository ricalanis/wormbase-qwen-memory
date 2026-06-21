"""Track-1 governance: timely forgetting (tombstones + decay) and preference memory."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from wormbase_memory import preferences
from wormbase_memory.agent import DataOpsMemoryAgent


def _df():
    return pd.DataFrame(
        [("North", "Widget", 100), ("South", "Gadget", 200), ("West", "Gadget", 150)],
        columns=["region", "product", "amount"],
    )


# -- forgetting -------------------------------------------------------------

def test_deprecated_plan_is_excluded_from_recall():
    a = DataOpsMemoryAgent()
    a.ingest(_df(), "s1")
    plan_id = a.ledger.fetch("plan.authored")[0].payload["plan_id"]
    a.deprecate_plan(plan_id, reason="manual")
    r = a.ingest(_df(), "s2")  # same schema, but the only plan is tombstoned
    assert r.reused is False  # forgotten -> must re-author
    assert len(a.ledger.fetch("plan.authored")) == 2


def test_decay_auto_deprecates_stale_plan():
    a = DataOpsMemoryAgent(staleness_days=30)
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    a.ingest(_df(), "s1", ts=t0)
    r = a.ingest(_df(), "s2", ts=t0 + timedelta(days=40))  # 40d > 30d -> stale
    assert r.reused is False
    assert a.ledger.fetch("plan.deprecated"), "stale plan must be tombstoned"


def test_forgetting_is_tombstoned_not_destroyed():
    a = DataOpsMemoryAgent()
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    a.ingest(_df(), "s1", ts=t0)
    plan_id = a.ledger.fetch("plan.authored")[0].payload["plan_id"]
    a.deprecate_plan(plan_id, reason="x", ts=t0 + timedelta(days=2))
    # replaying to before the tombstone still shows the original world
    before = a.ledger.replay_until(t0 + timedelta(days=1))
    assert any(e.kind == "plan.authored" for e in before)
    assert not any(e.kind == "plan.deprecated" for e in before)
    assert a.verify()[0] is True


# -- preferences ------------------------------------------------------------

def test_preference_persists_and_supersedes():
    a = DataOpsMemoryAgent()
    a.set_preference("drift_threshold", 0.25)
    a.set_preference("drift_threshold", 0.30)  # conflict -> supersede
    assert preferences.current(a.ledger)["drift_threshold"] == 0.30
    assert a.ledger.fetch("pref.superseded"), "conflict must record a supersede"


def test_preference_drift_threshold_changes_behavior_cross_session():
    a = DataOpsMemoryAgent()
    a.ingest(_df(), "s1")
    a.set_preference("drift_threshold", 0.25)  # only alert on >25% moves
    # +20% move: would flag at default 0.15, must NOT flag at the remembered 0.25
    bumped = pd.DataFrame(
        [("North", "Widget", 100), ("South", "Gadget", 200), ("West", "Gadget", 240)],
        columns=["region", "product", "amount"],
    )  # total 450 -> 540 = +20%
    r = a.ingest(bumped, "s2")
    assert "total_amount" not in r.drift
