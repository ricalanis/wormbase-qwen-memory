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

### Next
- P1 finish: live DashScope smoke test once key is set; route planning to Qwen-Plus.
- P3: deploy to ECS + record proof. P4: polish UI. P5: eval harness (LongMemEval +
  custom consistency harness on InfiAgent-DABench/Raha) + 3-min video + diagram.
