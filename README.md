# WormBase Qwen Memory

**A business-analyst MemoryAgent whose memory is a hash-chained ledger — so its
KPIs are reproducible byte-for-byte across sessions, it reuses prior analysis
plans to get cheaper over time, and when a metric moves it doesn't just flag it:
it explains *why* (attributes the change to the driving segment) and communicates
it in prose where every number traces back to the ledger.**

Built for the **Global AI Hackathon with Qwen Cloud** · **Track 1: MemoryAgent**.

Powered by **Qwen models on Alibaba Cloud Model Studio (DashScope)**:
- **Qwen-Plus** (cloud) — the planner/brain that authors data-operation plans.
- **A small self-hosted Qwen** (local, via Ollama) — the cheap recall/triage
  worker that recognizes previously-seen data and escalates to Qwen-Plus only
  on novel data or detected drift.

---

## The idea in one diagram

```
messy CSV ─▶ profiler(pandas) ─▶ TRIAGE (local small Qwen)
                                   │ "seen before? reuse the plan?"
                          reuse ◀──┤──▶ novel / drift ─▶ Qwen-Plus (DashScope)
                       (cached plan)│                     authors a new op-plan
                                    ▼
                       deterministic executor (closed op vocab, pandas/SQL)
                                    │ clean · dedup · join · aggregate · KPI
                                    ▼
                       verifier ─▶ LEDGER (append-only, SHA256 hash-chained)
                                    │  memory: plans · KPI defs · values · decisions
                                    ▼
                       projections: KPI tree + history ─▶ replay/verify ─▶ Streamlit UI
```

**Why this gives consistency over time:** the probabilistic step (planning) is
captured as a *deterministic, replayable artifact* (the plan). Re-running the
plan reproduces the KPI byte-for-byte; replaying the ledger to any past
timestamp reconstructs exactly the state as of then; the hash chain proves
nothing was altered.

## Quickstart

```bash
uv venv && uv pip install -e ".[dev,ui]"
uv run pytest -q                      # ledger + agent invariants, all green
uv run python scripts/run_demo.py     # 3-session demo (offline, no key needed)
```

To use Qwen Cloud, set your DashScope key and run the smoke test:

```bash
export DASHSCOPE_API_KEY=sk-...                      # from Alibaba Cloud Model Studio
export DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
uv run python scripts/smoke_dashscope.py            # 1-call connectivity check
```

The agent **degrades gracefully**: with no key it uses a deterministic rule-based
planner (so the demo and tests always run); with a key it routes planning to
Qwen-Plus and recall embeddings to Qwen.

### Local triage worker (the small-Qwen cameo)

A small local Qwen is the cheap recall gatekeeper: exact matches reuse for free,
only *gray-zone* candidates (similar-but-not-identical schema) spend the local
worker, and only genuinely novel data escalates to Qwen-Plus — the
orchestrator-worker cascade.

```bash
export WBM_USE_LOCAL_QWEN=1
export OLLAMA_MODEL=qwen3:1.7b            # or any model you already have pulled
uv run python scripts/triage_demo.py     # shows exact / gray-zone / escalate decisions
```

Runs fully on local hardware — no API spend. The cascade is also the **cost
strategy**: local-first, escalate to Qwen-Plus only when genuinely novel, so
DashScope usage stays inside the free quota.

Without it, the triage gray zone falls back to a deterministic similarity
threshold, so everything still runs.

## Verify it yourself

```bash
uv run python scripts/prove_it.py              # same hash twice → tamper breaks the chain
uv run --extra viz python scripts/plot_curve.py  # smarter+cheaper-over-sessions → results/
```

## Query the memory from other AI (MCP)

The agent's memory is exposed over MCP, so Claude Desktop / Cursor can query it as
institutional knowledge — receipts-backed answers, change explanations, and a
chain-verify tool (all read-only folds over the ledger).

```bash
WBM_LEDGER_DB=./wbm_ledger.db uv run python scripts/seed_ledger.py        # persist a ledger
WBM_LEDGER_DB=./wbm_ledger.db uv run --extra mcp python -m wormbase_memory.mcp_server
```
Tools: `ask_kpi`, `explain_change`, `verify_memory`, `list_kpis`. Resources:
`memory://kpi/{id}/history`, `memory://ledger/verify`. See
[`infra/claude_desktop_config.json`](infra/claude_desktop_config.json).

## Memory model (ledger entry kinds)

| Kind | Meaning |
|---|---|
| `triage.decided` | Reuse-vs-escalate verdict (backend: exact / local-qwen / rules) |
| `plan.authored` | A new op-plan written by Qwen-Plus for a novel data profile |
| `plan.reused` | A prior plan recalled and reused (with similarity + provenance) |
| `clean.{propose,execute,verify,resolve}` | PEVR cycle for a data-op execution |
| `kpi.defined` | A KPI definition (formula, source columns) |
| `kpi.computed` | A KPI value with `value_hash` + `input_hash` + per-dim `breakdown` |
| `kpi.drift_flagged` | A KPI moved beyond threshold — flagged, **not** silently changed |
| `kpi.explained` | Attribution of the move to driving segments (Σ contributions = ΔKPI) |
| `insight.generated` | Grounded narrative of the change (every number cites the ledger) |
| `pref.set` / `pref.superseded` | Remembered user preferences (last-writer-wins, auditable) |
| `plan.deprecated` | Tombstone — forgotten for recall, still replayable (timely forgetting) |
| `policy.tuned` | Self-improvement: a parameter the agent tuned to raise a metric |
| `plan.deprecated` / `kpi.deprecated` | Tombstone: timely forgetting, excluded on replay |

## Evaluation

Two-pronged (see `docs/` and the project plan):
- **Standard memory benchmarks** for Track-1 credibility: LongMemEval, PrefEval.
- **Custom cross-session consistency harness** (the contribution): same data-ops
  tasks across N sessions with perturbations + injected drift, reporting
  reproducibility rate, plan-reuse rate / planner-tokens-per-session, and
  drift-detection precision — scored on deterministic ground truth
  (InfiAgent-DABench scorer + Raha/Baran clean datasets).

## Lineage & credits

A drastically simplified extract of [WormBase](https://github.com/ricalanis/wormbase-oss)'s
continuous-lake idea: an append-only, hash-chained ledger that every projection
folds from. The hash-chain semantics here are a clean-room port of WormBase's
ledger. The cleaning-plan pattern is inspired by
[`scrubdata-qwen3-4b`](https://huggingface.co/ricalanis/scrubdata-qwen3-4b).

## License

Apache-2.0 — see [LICENSE](LICENSE).
