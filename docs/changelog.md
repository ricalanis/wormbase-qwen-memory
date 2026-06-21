# Changelog

## 2026-06-20 — P0+P1+P2: core agent end-to-end (offline)
- Scaffolded `wormbase-qwen-memory` (new repo, Apache-2.0). Track 1: MemoryAgent.
- Clean-room minimal hash-chained ledger (`hashchain.py`, `ledger.py`) on SQLite:
  append-only, PEVR write, `replay_until(T)`, `verify()`. Ported WormBase's
  canonical-JSON + SHA256 chain semantics.
- Data-ops layer: `profiler.py` (fingerprint), `executor.py` (closed op vocab,
  deterministic pandas, `compute_kpi` with value/input hashes), `planner.py`
  (Qwen-Plus via DashScope OR deterministic rules fallback), `recall.py`
  (fingerprint/Jaccard reuse), `agent.py` (the loop + drift detection).
- `inference.py`: DashScope `QwenCloudClient` + local-Qwen client, both
  OpenAI-compatible, graceful degradation with no key.
- Streamlit UI (`ui/app.py`): KPI-over-time, verify badge, replay slider,
  memory-recall panel, raw ledger trace.
- Alibaba Cloud deploy artifacts: `infra/aliyun/{Dockerfile,deploy.sh,README.md}`.
- 11 tests green; offline 3-session demo green:
  S1 authored → S2 reused & stable (450) → S3 reused & drift-flagged (2450);
  reproducibility 100%; hash-chain GREEN.

## 2026-06-20 — published + P5 eval harness
- Published public repo: https://github.com/ricalanis/wormbase-qwen-memory (Apache-2.0).
- Prong A (our contribution): cross-session consistency harness
  (`eval/datasets.py`, `eval/consistency.py`, `scripts/eval_consistency.py`).
  Results: reproducibility 100% · reuse 100% · planner-cost −83% · drift P/R/F1
  1.00/1.00/1.00 · run-to-run identical · chain GREEN → `results/consistency.json`.
- Fixed drift detector to anchor on last non-flagged baseline (kills false
  positive when a KPI returns to normal after a one-off anomaly).
- Prong B: `scripts/answer_jsonl.py` Qwen-Plus generation adapter for
  LongMemEval / PrefEval; `docs/eval.md` documents both prongs.
- 13 tests green.

## 2026-06-20 — local Qwen triage worker cameo
- Added `triage.py` (local-Qwen reuse-vs-escalate gatekeeper, FrugalGPT-style
  cascade) + refactored `recall.py` to `best_candidate()` (no threshold; triage
  owns the decision). Exact match = free reuse; gray zone = local Qwen decides;
  novel = escalate to Qwen-Plus. New `triage.decided` ledger entry (auditable).
- Wired into agent (triage_backend/triage_tokens on report); UI recall panel now
  shows the triage decision; `scripts/triage_demo.py` showcases it.
- 19 tests green (6 new triage tests using a fake local client — no network).
  Enable real worker: `ollama pull qwen3:1.7b && export WBM_USE_LOCAL_QWEN=1`.

### Next
- P1 finish: live DashScope smoke test once key is set; route planning to Qwen-Plus.
- P3: deploy to ECS + record proof. P4: polish UI.
- P5 finish: wire InfiAgent-DABench + Raha scorers; run LongMemEval/PrefEval with key.
- Submission: architecture diagram (have mermaid) + 3-min video + text description.
