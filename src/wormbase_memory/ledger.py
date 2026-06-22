"""Minimal append-only, hash-chained ledger on SQLite — the agent's memory.

This is the load-bearing substrate: every plan, KPI definition, computed value,
reuse decision, and drift flag is an append-only entry. Memory is therefore
*deterministically replayable* (``replay_until``) and *tamper-evident*
(``verify``). Forgetting is a recorded tombstone, never a silent delete.

PEVR (propose -> execute -> verify -> resolve) is the write discipline: the
probabilistic step (a plan) is captured as four chained entries so the outcome
is auditable and replayable rather than a black box.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .hashchain import GENESIS_PREV_HASH, compute_entry_hash, verify_chain


@dataclass(frozen=True)
class Entry:
    entry_id: str
    seq: int
    ts: datetime
    kind: str
    payload: dict[str, Any]
    prev_hash: bytes
    hash: bytes

    def hashable(self) -> dict[str, Any]:
        """Dict view used for hashing/verification (includes stored hash)."""
        return {
            "entry_id": self.entry_id,
            "seq": self.seq,
            "ts": self.ts,
            "kind": self.kind,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


class Ledger:
    """Append-only hash-chained event log backed by SQLite."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        # check_same_thread=False: Streamlit runs each rerun on a new thread and
        # reuses one connection from session_state. A lock serializes writes so
        # seq/hash-chain stays consistent without the per-thread guard.
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger (
                seq        INTEGER PRIMARY KEY,
                entry_id   TEXT NOT NULL,
                ts         TEXT NOT NULL,
                kind       TEXT NOT NULL,
                payload    TEXT NOT NULL,
                prev_hash  TEXT NOT NULL,
                hash       TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    # -- write ---------------------------------------------------------------

    def _head(self) -> tuple[int, bytes]:
        row = self._conn.execute(
            "SELECT seq, hash FROM ledger ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return 0, GENESIS_PREV_HASH
        return int(row[0]), bytes.fromhex(row[1])

    def append(
        self, kind: str, payload: dict[str, Any], ts: datetime | None = None
    ) -> Entry:
        """Append one entry, chaining it to the current head."""
        ts = ts or datetime.now(UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        entry_id = str(uuid4())
        with self._lock:  # serialize read-head -> insert so seq/chain stay consistent
            last_seq, prev_hash = self._head()
            seq = last_seq + 1
            body = {
                "entry_id": entry_id,
                "seq": seq,
                "ts": ts,
                "kind": kind,
                "payload": payload,
                "prev_hash": prev_hash,
            }
            h = compute_entry_hash(body)
            self._conn.execute(
                "INSERT INTO ledger (seq, entry_id, ts, kind, payload, prev_hash, hash) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    seq,
                    entry_id,
                    ts.isoformat(),
                    kind,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    prev_hash.hex(),
                    h.hex(),
                ),
            )
            self._conn.commit()
        return Entry(entry_id, seq, ts, kind, payload, prev_hash, h)

    def write_pevr(
        self,
        base_kind: str,
        propose: dict[str, Any],
        execute_fn: Callable[[], Any],
        verify_fn: Callable[[Any], bool],
        ts: datetime | None = None,
    ) -> tuple[Any, bool]:
        """Propose -> Execute -> Verify -> Resolve, as four chained entries.

        Returns ``(execute_result, verified)``. A failed verify still records
        the full attempt (auditable), resolving with ``status="aborted"``.
        """
        self.append(f"{base_kind}.propose", propose, ts=ts)
        result = execute_fn()
        self.append(f"{base_kind}.execute", {"result": result}, ts=ts)
        ok = bool(verify_fn(result))
        self.append(f"{base_kind}.verify", {"passed": ok}, ts=ts)
        self.append(
            f"{base_kind}.resolve",
            {"status": "committed" if ok else "aborted"},
            ts=ts,
        )
        return result, ok

    # -- read ----------------------------------------------------------------

    def _row_to_entry(self, row: tuple) -> Entry:
        seq, entry_id, ts, kind, payload, prev_hash, h = row
        return Entry(
            entry_id=entry_id,
            seq=int(seq),
            ts=datetime.fromisoformat(ts),
            kind=kind,
            payload=json.loads(payload),
            prev_hash=bytes.fromhex(prev_hash),
            hash=bytes.fromhex(h),
        )

    def fetch(self, kind_prefix: str | None = None) -> list[Entry]:
        rows = self._conn.execute(
            "SELECT seq, entry_id, ts, kind, payload, prev_hash, hash "
            "FROM ledger ORDER BY seq ASC"
        ).fetchall()
        entries = [self._row_to_entry(r) for r in rows]
        if kind_prefix is not None:
            entries = [e for e in entries if e.kind.startswith(kind_prefix)]
        return entries

    def replay_until(self, ts: datetime) -> list[Entry]:
        """All entries with ``entry.ts <= ts`` — the lake's state as of ``ts``."""
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return [e for e in self.fetch() if e.ts <= ts]

    def verify(self) -> tuple[bool, int | None]:
        """Verify the full hash chain. Returns ``(ok, broken_at_index)``."""
        return verify_chain([e.hashable() for e in self.fetch()])

    def close(self) -> None:
        self._conn.close()
