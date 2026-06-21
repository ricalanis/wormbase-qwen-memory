# Decisions

## 2026-06-20
- **Track 1: MemoryAgent.** The hash-chained ledger = verifiable persistent
  memory; cross-session plan reuse = increasingly accurate/cheaper decisions.
- **Clean-room minimal ledger, not a lift.** WormBase's `packages/ledger` is ~8K
  lines + pydantic/sqlalchemy/alembic. We reimplemented the load-bearing
  properties (append-only, SHA256 chain, PEVR, replay, verify) in ~250 lines of
  stdlib `sqlite3`+`hashlib`. Truer to "extremely simplified"; trivial to deploy.
- **Qwen-Plus (DashScope) as default planner + deterministic-rules fallback.**
  The agent must run offline (tests/demo) and route to Qwen Cloud when a key is
  present. Same plan output shape both ways, so reuse compares apples-to-apples.
- **Small local Qwen = cameo triage worker**, not the spine. Demonstrates the
  cloud-brain/cheap-worker cascade (FrugalGPT-style) and an edge angle.
- **Streamlit UI**, new public repo, Apache-2.0.
- **Closed op vocabulary** is the key design constraint: it makes every plan a
  deterministic, replayable artifact (the source of KPI reproducibility).
