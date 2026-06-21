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

## 2026-06-21 — provider switch (local-now / cloud-later) + submission map
- Added `WBM_PROVIDER` planner switch (`resolve_planner_client`): auto / dashscope
  / rules / local — same code, one env var. Cloud path == local path, only env
  differs. Triage gate (`WBM_USE_LOCAL_QWEN`) decoupled from planner provider.
- Confirmed: small local models (MiniCPM3-4B) are unreliable at structured plan
  authoring (malformed ops) → local planner auto-falls back to rules. Design:
  planner = Qwen-Plus (cloud) / rules (local); local small model = triage only
  (which it does reliably). Shared `loads_lenient` parser.
- `OLLAMA_MODEL` documented; `.env.example` updated with provider modes.
- Added `SUBMISSION.md`: requirements checklist + text description + run modes +
  Alibaba Cloud deployment-proof plan (pending Qwen Cloud credit validation).
- 19 tests green; local triage verified $0 on MiniCPM3-4B.

## 2026-06-21 — analyst pivot: explain WHY a KPI moved (keystone slice)
- arXiv research (5-thread fan-out) → `docs/research-analyst.md`: pipeline stages,
  op vocab, the keystone (causal attribution of metric change), eval (InsightBench
  2407.06423, CORGI 2510.07309), and the chain-of-custody faithfulness idea.
- New deterministic analyst layer wired onto existing drift detection:
  - `executor.kpi_breakdown` — per-dimension breakdown stored in `kpi.computed`.
  - `analysis.explain_change` — attributes ΔKPI to driving segments; contributions
    sum exactly to the change (efficiency axiom).
  - `narrative.render_change_narrative` + `is_grounded` — grounded prose; every
    data number must trace to the ledger (deterministic faithfulness check).
  - agent: on drift, writes `kpi.explained` + `insight.generated` and reports the
    narrative. Demo now prints "total_amount changed +444% … driver region=East
    (+100%)". UI shows an Explained-insights panel.
- README/ARCHITECTURE reframed: data-ops → business-analyst MemoryAgent.
- 22 tests green (3 new analyst tests incl. efficiency axiom + faithfulness).

## 2026-06-21 — product sprint build-out (Max scope)
- 5-lens design sprint → `docs/product-sprint.md` (confirmed Devpost rubric:
  Tech 30% [names MCP] / Innovation 30% / Impact 25% / Presentation 15%).
  Thesis: "memory you can verify, not memory you have to trust."
- Receipts-backed Q&A (`agent.answer`) + `scripts/prove_it.py` (identical hash
  across runs; tamper caught) — the WOW.
- Real forgetting: tombstones filter recall + decay (`recall`, `agent`); preference
  memory (`preferences.py`, pref.set/superseded) wired to drift threshold + style.
- Learning curve (`eval/curve.py`, `scripts/plot_curve.py`) memory ON vs OFF.
- Metric-governed self-improvement (`autoresearch.py`) tunes drift threshold,
  remembers it, writes `policy.tuned`.
- MCP server (`mcp_server.py` + `memory_api.py` + `infra/claude_desktop_config.json`)
  exposes memory to Claude Desktop/Cursor; `scripts/seed_ledger.py` persists a ledger.
- New ledger kinds: pref.set/superseded, plan.deprecated, policy.tuned.
- 35 tests green (+13). `docs/benchmarks.md` added.

## 2026-06-21 — demo-experience sprint (marketer + product + UX)
- 5-lens sprint → `docs/demo-spec.md` (persona, message hierarchy, video script,
  thumbnail, blog angle, shooting checklist).
- Rebuilt `ui/app.py`: audit-grade dark theme (`.streamlit/config.toml` + CSS),
  single-column guided scroll, answer-first headline + trust strip, sessions gated
  behind "Run Week N" (live arc), revenue-over-time with drift annotation,
  attribution **waterfall** (Σ=ΔKPI), grounded receipts with hash-chip popovers,
  cost-per-week economics, **prove-it/tamper** chain rows + verify badge,
  time-travel replay. Fixed waterfall to bind to total_amount (was grabbing
  row_count). Booted headless (HTTP 200, no errors); bindings validated.
- Brewly persona reskin of demo session labels (Week 1/2/3). 35 tests green.

## 2026-06-21 — Ollama Cloud planner (real Qwen, locally driven, $0)
- Added `OllamaCloudClient` + `WBM_PROVIDER=ollama_cloud`: a flagship Qwen on
  Ollama Cloud (`qwen3-coder:480b`, OpenAI-compatible at ollama.com) authors real
  plans through the local toolchain. Key auto-read from the OpenCode auth store
  (provider `ollama-cloud`) or `OLLAMA_API_KEY`.
- Fixed the planner SYSTEM_PROMPT: explicit JSON-object op schema + worked example
  (the model had emitted DSL strings → invalid → rules fallback). Now Qwen3-Coder
  authors a valid plan end-to-end (verified: backend `ollama-cloud:qwen3-coder:480b`,
  chain GREEN). Plans authored once then reused free (only week 1 is slow).
- UI planner label shows the resolved backend. Submission path unchanged:
  `WBM_PROVIDER=dashscope` → Qwen-Plus on Alibaba Cloud (same code).
- 35 offline tests green; UI boots in cloud mode.

## 2026-06-21 — Ollama Cloud model choice + 3-week dry run
- Evaluated qwen3.5:397b as planner: it's a heavy REASONING model — burns 15k+
  reasoning tokens deliberating about JSON and truncates before emitting content
  (empty `content`, answer stuck in `reasoning`). Unsuitable for direct
  structured output. Default stays **qwen3-coder:480b** (emits valid plan-JSON in
  ~640 tokens; 3.5 kept selectable via OLLAMA_CLOUD_MODEL).
- Full 3-week dry run (WBM_PROVIDER=ollama_cloud, qwen3-coder:480b): Week 1
  AUTHORED by the cloud Qwen (~2s), Weeks 2–3 REUSED free (0.0s), drift detected
  + explained, reproducibility 100%, chain GREEN, receipts grounded. Total ~2s —
  only Week 1 hits the cloud; reuse covers the rest. Video-ready timing.

### Next
- Extend ops: forecast / regression / cohort_retention / what_if (modelling tier).
- LLM narration (Qwen-Plus) gated by `is_grounded`; full `compose_report`.
- Wire InsightBench eval against DashScope when credits land.
- P1 finish: live DashScope smoke test once key is set; route planning to Qwen-Plus.
- P3: deploy to ECS + record proof. P4: polish UI.
- P5 finish: wire InfiAgent-DABench + Raha scorers; run LongMemEval/PrefEval with key.
- Submission: architecture diagram (have mermaid) + 3-min video + text description.
