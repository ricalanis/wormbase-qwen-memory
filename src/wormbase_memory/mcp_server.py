"""MCP server — exposes the agent's verifiable memory to external AI clients.

Makes WormBase Qwen Memory institutional knowledge that Claude Desktop / Cursor
can query: receipts-backed KPI answers, change explanations, and a chain-verify
tool. Every response is a read over the hash-chained ledger.

Run:  WBM_LEDGER_DB=./wbm_ledger.db uv run --extra mcp python -m wormbase_memory.mcp_server
(FastMCP is imported lazily so the rest of the package needs no MCP dependency.)
"""

from __future__ import annotations

import os

from . import memory_api
from .ledger import Ledger


def _ledger() -> Ledger:
    return Ledger(os.environ.get("WBM_LEDGER_DB", "./wbm_ledger.db"))


def build_server():  # pragma: no cover - requires fastmcp + a transport
    from fastmcp import FastMCP

    mcp = FastMCP("wormbase-memory")

    @mcp.tool()
    def list_kpis() -> list[str]:
        """List KPI ids the agent remembers."""
        return memory_api.list_kpis(_ledger())

    @mcp.tool()
    def ask_kpi(kpi_id: str) -> dict:
        """Receipts-backed answer for a KPI: prose + cited ledger entries."""
        return memory_api.ask_kpi(_ledger(), kpi_id)

    @mcp.tool()
    def explain_change(kpi_id: str) -> dict | None:
        """Attribution of a KPI's last move to driving segments."""
        return memory_api.explain_change(_ledger(), kpi_id)

    @mcp.tool()
    def verify_memory() -> dict:
        """Verify the memory's hash chain (tamper-evidence)."""
        return memory_api.verify_memory(_ledger())

    @mcp.resource("memory://kpi/{kpi_id}/history")
    def kpi_history(kpi_id: str) -> list:
        return memory_api.kpi_history(_ledger(), kpi_id)

    @mcp.resource("memory://ledger/verify")
    def ledger_verify() -> dict:
        return memory_api.verify_memory(_ledger())

    return mcp


def main() -> None:  # pragma: no cover
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
