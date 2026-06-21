"""The ledger's two non-negotiable properties: tamper-evidence + deterministic replay."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from wormbase_memory.ledger import Ledger


def test_append_and_verify_intact_chain():
    led = Ledger()
    led.append("plan.authored", {"id": "p1", "ops": ["dedup"]})
    led.append("kpi.computed", {"id": "revenue", "value": 100, "value_hash": "abc"})
    ok, broken = led.verify()
    assert ok is True
    assert broken is None


def test_tamper_breaks_chain():
    led = Ledger()
    led.append("kpi.computed", {"id": "revenue", "value": 100})
    led.append("kpi.computed", {"id": "revenue", "value": 100})
    # Tamper with the payload of seq=1 directly in storage.
    led._conn.execute(
        "UPDATE ledger SET payload = ? WHERE seq = 1",
        ('{"id":"revenue","value":999}',),
    )
    led._conn.commit()
    ok, broken = led.verify()
    assert ok is False
    assert broken == 0  # first entry now fails its recomputed hash


def test_replay_until_reconstructs_past_state():
    led = Ledger()
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    led.append("kpi.computed", {"id": "rev", "value": 1}, ts=t0)
    led.append("kpi.computed", {"id": "rev", "value": 2}, ts=t0 + timedelta(days=1))
    led.append("kpi.computed", {"id": "rev", "value": 3}, ts=t0 + timedelta(days=2))

    as_of = led.replay_until(t0 + timedelta(days=1))
    values = [e.payload["value"] for e in as_of]
    assert values == [1, 2]  # day-2 entry excluded


def test_pevr_records_four_entries_and_commits():
    led = Ledger()
    result, ok = led.write_pevr(
        "clean",
        propose={"plan": ["dedup", "canonicalize"]},
        execute_fn=lambda: {"rows_out": 42},
        verify_fn=lambda r: r["rows_out"] > 0,
    )
    assert ok is True
    assert result == {"rows_out": 42}
    kinds = [e.kind for e in led.fetch()]
    assert kinds == ["clean.propose", "clean.execute", "clean.verify", "clean.resolve"]
    assert led.fetch()[-1].payload["status"] == "committed"


def test_pevr_aborts_on_failed_verify_but_stays_auditable():
    led = Ledger()
    _, ok = led.write_pevr(
        "clean",
        propose={"plan": ["drop_all"]},
        execute_fn=lambda: {"rows_out": 0},
        verify_fn=lambda r: r["rows_out"] > 0,
    )
    assert ok is False
    assert led.fetch()[-1].payload["status"] == "aborted"
    # The failed attempt is still fully chained and verifiable.
    assert led.verify()[0] is True
