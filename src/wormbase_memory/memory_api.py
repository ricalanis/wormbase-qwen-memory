"""Read-only memory API — the folds the MCP server (and UI) expose.

Pure functions over a Ledger so they're testable without the MCP transport.
This is the institutional-knowledge surface: other AI clients query the agent's
verifiable memory instead of re-deriving it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .agent import DataOpsMemoryAgent
from .ledger import Ledger


def _agent(ledger: Ledger) -> DataOpsMemoryAgent:
    return DataOpsMemoryAgent(ledger=ledger)


def list_kpis(ledger: Ledger) -> list[str]:
    seen: list[str] = []
    for e in ledger.fetch("kpi.computed"):
        kid = e.payload.get("id")
        if kid and kid not in seen:
            seen.append(kid)
    return seen


def kpi_history(ledger: Ledger, kpi_id: str) -> list[dict[str, Any]]:
    return _agent(ledger).kpi_history(kpi_id)


def ask_kpi(ledger: Ledger, kpi_id: str) -> dict[str, Any]:
    """Receipts-backed answer: prose + cited ledger entries + grounded flag."""
    return _agent(ledger).answer(kpi_id)


def explain_change(ledger: Ledger, kpi_id: str) -> dict[str, Any] | None:
    expl = [e.payload for e in ledger.fetch("kpi.explained")
            if e.payload.get("id") == kpi_id]
    return expl[-1] if expl else None


def verify_memory(ledger: Ledger) -> dict[str, Any]:
    ok, broken = ledger.verify()
    entries = ledger.fetch()
    head = entries[-1].hash.hex() if entries else None
    return {"chain_ok": ok, "broken_at": broken,
            "entries": len(entries), "head_hash": head}


def replay_until(ledger: Ledger, ts_iso: str) -> list[dict[str, Any]]:
    ts = datetime.fromisoformat(ts_iso)
    return [{"seq": e.seq, "ts": e.ts.isoformat(), "kind": e.kind,
             "payload": e.payload} for e in ledger.replay_until(ts)]
