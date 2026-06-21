# Submission — WormBase Qwen Memory

**Track 1: MemoryAgent.**

## Requirements checklist

| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Public repo + detectable OSS license | ✅ done | [github.com/ricalanis/wormbase-qwen-memory](https://github.com/ricalanis/wormbase-qwen-memory) · Apache-2.0 `LICENSE` (shown in About) |
| 2 | Proof of Alibaba Cloud deployment — code file using Alibaba Cloud APIs | ✅ code file | [`src/wormbase_memory/inference.py`](src/wormbase_memory/inference.py) — `QwenCloudClient` → DashScope (Model Studio) |
| 2b | …+ short recording of backend running on Alibaba Cloud | ⏳ pending credits | plan below — deploy via [`infra/aliyun/deploy.sh`](infra/aliyun/deploy.sh) once Qwen Cloud credits validate |
| 3 | Architecture diagram (Qwen Cloud ↔ backend ↔ db ↔ frontend) | ✅ done | [`ARCHITECTURE.md`](ARCHITECTURE.md) (mermaid, renders on GitHub) |
| 4 | ~3-min demo video (YouTube/Vimeo) | ⏳ to record | script = offline demo + consistency eval (runnable today); add cloud run after credits |
| 5 | Text description | ✅ draft below | this file |
| 6 | Identify track | ✅ | Track 1: MemoryAgent |
| 7 | Optional blog/social post | ⬜ optional | — |

## Text description (draft)

**WormBase Qwen Memory** is a data-operations MemoryAgent whose long-term memory
is an append-only, SHA256 **hash-chained ledger**. Because every cleaning plan,
KPI definition, and computed value is an append-only entry, the agent's outputs
are **deterministically replayable** and **tamper-evident** — its KPIs reproduce
byte-for-byte across sessions, and you can verify nothing was altered.

The agent gets cheaper and more consistent the more it remembers:
- A **profiler** turns each incoming table into a hashable fingerprint.
- A **triage worker** (a small local Qwen) recognizes data it has seen before and
  **reuses the cached plan for free**; only genuinely novel data **escalates to
  Qwen-Plus on Alibaba Cloud** to author a new plan — an orchestrator-worker
  cascade that is also the cost-control mechanism.
- A **deterministic executor** runs a closed operation vocabulary (clean, dedup,
  filter, join, aggregate, define/compute KPI) so a plan is a replayable artifact.
- Drift is **flagged, never silently applied**: when a KPI moves beyond threshold
  vs. the last established-normal value, the agent surfaces it for review.

Measured on our cross-session consistency harness: reproducibility **100%**, plan
reuse **100%**, planner-cost reduction **83%**, drift detection **F1 1.00**,
run-to-run **identical**, hash-chain **green**.

Qwen models do the reasoning: **Qwen-Plus on Alibaba Cloud Model Studio
(DashScope)** authors plans; a small local Qwen handles recall/triage. Track-1
fit: persistent verifiable memory, increasingly accurate cross-session decisions,
efficient recall, timely forgetting (deprecation + `replay_until(T)`).

## Run modes (same code; one switch)

| Mode | Planner | Triage | Cost | Set |
|---|---|---|---|---|
| **Local dev (now)** | deterministic rules | local Qwen (Ollama) | $0 | `WBM_USE_LOCAL_QWEN=1 OLLAMA_MODEL=…` |
| **Cloud (after credits)** | Qwen-Plus (DashScope) | local Qwen or rules | free quota | `WBM_PROVIDER=dashscope DASHSCOPE_API_KEY=…` |
| **Pure offline (CI/tests)** | rules | rules | $0 | *(defaults)* |

The cloud path is the **same code** as local — only env vars change — so what we
test locally is what runs on Alibaba Cloud.

## Plan for the Alibaba Cloud deployment proof (when credits validate)

1. Set Model Studio API key (Singapore/intl region — free quota is region-locked).
2. `WBM_PROVIDER=dashscope` → `uv run python scripts/smoke_dashscope.py` (live Qwen-Plus reply).
3. Deploy to a **free-tier ECS** (1c/1GB, 12-month free): `bash infra/aliyun/deploy.sh`.
4. Record (separate from demo): the ECS shell running `smoke_dashscope.py` + the UI
   at `http://<ecs-ip>:8501`. Set a billing alert; tear down after recording.

Cost posture: **$0** — local Ollama is free, DashScope within the ~70M-token free
quota + hackathon coupon, ECS within the individual free tier.
