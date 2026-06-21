# Architecture

WormBase Qwen Memory is a **Track-1 MemoryAgent**: its long-term memory is an
append-only, SHA256 hash-chained ledger, so its outputs (cleaned tables, KPIs)
are *deterministically replayable* and *tamper-evident*. The agent reuses prior
operation-plans across sessions (getting cheaper and more consistent) and flags
drift instead of silently changing answers.

## System diagram

```mermaid
flowchart TB
    CSV[messy CSV / table] --> PROF[profiler<br/>pandas · deterministic]
    PROF --> TRIAGE{recall / triage<br/>seen this shape before?}

    TRIAGE -- "match ≥ threshold" --> REUSE[reuse cached plan<br/>cost = 0]
    TRIAGE -- "novel / drift" --> BRAIN[Qwen-Plus<br/>DashScope · authors op-plan]

    REUSE --> EXEC
    BRAIN --> EXEC[deterministic executor<br/>closed op vocab · pandas]
    EXEC --> VERIFY[verifier<br/>rows&gt;0 · no null keys]
    VERIFY --> LEDGER[(LEDGER<br/>append-only · hash-chained · SQLite)]

    LEDGER --> PROJ[projections<br/>KPI tree · history]
    PROJ --> REPLAY[replay-to-T · verify]
    REPLAY --> UI[Streamlit UI]

    LOCAL[small local Qwen<br/>Ollama · triage worker] -. refines .-> TRIAGE
    BRAIN -. inference.served audit .-> LEDGER

    subgraph AC[Alibaba Cloud]
        BRAIN
        ECS[ECS: API + UI + ledger]
    end
```

## The spine

```
Cloud LLM plans  →  deterministic local executor runs  →  verifier gates  →  ledger remembers
   (Qwen-Plus)         (pandas, closed vocab)               (checks)          (hash-chained)
```

The probabilistic step (planning) is captured as a **deterministic, replayable
artifact** — the plan, a list of closed-vocabulary ops. Re-running the plan
reproduces the KPI byte-for-byte; that is the whole reason KPIs stay stable.

## Components

| Module | Role |
|---|---|
| `hashchain.py` | Canonical-JSON + SHA256 chain (clean-room port of WormBase ledger semantics) |
| `ledger.py` | Append-only SQLite ledger; `append`, `write_pevr`, `replay_until`, `verify` |
| `profiler.py` | Deterministic column profile → hashable fingerprint (the recall key) |
| `executor.py` | Closed op vocabulary executed by pandas; `compute_kpi` with value/input hashes |
| `planner.py` | Authors a plan from a profile — Qwen-Plus (DashScope) or deterministic rules |
| `recall.py` | Finds the best reusable prior plan by fingerprint / column-set similarity |
| `triage.py` | Local-Qwen worker: reuse-vs-escalate verdict for gray-zone candidates |
| `analysis.py` | Deterministic metric-change attribution (Σ contributions = ΔKPI) |
| `narrative.py` | Grounded narration + `is_grounded` chain-of-custody faithfulness check |
| `preferences.py` | User-preference memory folded from the ledger (last-writer-wins) |
| `autoresearch.py` | Metric-governed self-improvement (PEVR loop tunes a parameter) |
| `memory_api.py` | Read-only folds (ask/explain/verify/replay) — the MCP surface |
| `mcp_server.py` | FastMCP server exposing memory to external AI clients |
| `eval/curve.py` | Smarter+cheaper-over-sessions learning curve (memory ON vs OFF) |
| `inference.py` | DashScope (Qwen-Plus) + local-Qwen OpenAI-compatible clients |
| `agent.py` | The loop: profile → recall → PEVR execute → KPI → drift-check → ledger |

## Memory model (ledger entry kinds)

`triage.decided` · `plan.authored` · `plan.reused` · `clean.{propose,execute,verify,resolve}` ·
`kpi.explained` · `insight.generated` · `pref.set` · `pref.superseded` ·
`plan.deprecated` · `policy.tuned` ·
`kpi.defined` · `kpi.computed` (carries `value_hash` + `input_hash`) ·
`kpi.drift_flagged` · `plan.deprecated` / `kpi.deprecated` (tombstones = timely
forgetting; excluded on `replay_until`).

## Track-1 mapping

| Requirement | Mechanism |
|---|---|
| Persistent memory, accumulates experience | Ledger of plans, KPI defs, values |
| Increasingly accurate decisions across sessions | Recall reuses prior plans; only novel data / drift escalates to Qwen-Plus |
| Efficient storage & retrieval | Append + compact fingerprint recall; never replay raw log to the model |
| Timely forgetting | Deprecation tombstones + decay + `replay_until(T)` |
| Recall within limited context | Plan/profile recall, not whole-history prompting |

## Alibaba Cloud footprint

- **DashScope (Qwen Cloud)** — Qwen-Plus authors plans (and Qwen embeddings for
  recall when enabled). See `inference.py` (`QwenCloudClient`) — the file that
  demonstrates use of Alibaba Cloud APIs.
- **ECS** — hosts the agent API, the Streamlit UI, the local-Qwen triage worker
  (Ollama), and the SQLite ledger. See `infra/aliyun/`.
- **Proof of deployment** — `infra/aliyun/Dockerfile` + `deploy.sh` + a short
  recording of the backend on ECS calling DashScope.

## Evaluation

- **Standard memory benchmarks** (Track-1 credibility, run vs DashScope Qwen-Plus):
  LongMemEval (arXiv 2410.10813), PrefEval (2502.09597).
- **Custom cross-session consistency harness** (the contribution): same data-ops
  tasks across N sessions with perturbations + injected drift → reproducibility
  rate, plan-reuse rate / planner-tokens-per-session, drift-detection precision,
  scored on deterministic ground truth (InfiAgent-DABench scorer + Raha/Baran).

Selected grounding: AutoDCWorkflow (2412.06724, planner→executable-workflow);
MemGPT (2310.08560); MemoryBank decay (2305.10250); Zep bi-temporal (2501.13956);
determinism (2408.04667); drift "fail loudly" (1810.11953); FrugalGPT cascade
(2305.05176); execution-verified ORPS (2412.15118).
