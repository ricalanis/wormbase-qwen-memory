# Vision: BMC-T — Business Memory Consistency over Time (an eval)

Grow the prototype into a **benchmark** for the thing no one measures:
*does governed memory keep business analytical answers consistent across
rephrasings and over time — reproducibly and auditably?* (arXiv-grounded, 2026-06-21.)

## The gap (5-lens deep research)
The ingredients exist separately; nobody joins them for business metrics over time:
- **Memory benchmarks** — personal chat facts, text-answer matching;
  "knowledge-update" rewards adopting the NEW value (the dual of governance).
  LongMemEval 2410.10813 · LoCoMo 2402.17753 · MemoryAgentBench 2507.05257 ·
  BEAM 2510.27246 · Memora/FAMA 2604.20006.
- **Text-to-SQL** — deterministic execution oracle, but single-shot/stateless.
  Spider 1809.08887 · BIRD 2305.03111 · Dr.Spider 2301.08881.
- **Paraphrase robustness** — same-moment, no time/memory. RoParQ/XParaCon
  2511.21568 · semantic entropy 2302.09664.
- **Semantic layer** — governed-metric determinism, within-run only. Cube
  benchmark 2604.25149 · ETM equivalence 2407.07313 · FLEX judge 2409.19014.
- **Drift / governance** — beliefs/world-facts, not KPIs. Chronos (drift-vs-genuine
  change) 2604.05096 · BeliefShift 2603.23848 · SSGM (names re-baselining as
  under-evaluated) 2603.11768 · Merkle-log integrity 2605.00065 · StreamingQA
  (dated checkpoints) 2205.11388. Caution to engage: Beyond-pass@1 2603.29231
  found memory scaffolds *hurt* long-horizon reliability — governed memory is the fix.

**Novel claim:** existing work scores whether an agent *absorbs* change; BMC-T
scores whether it *resists ungoverned change while staying auditably reproducible.*

## The benchmark
A dated stream of recurring business questions (paraphrased, varied askers)
against an **evolving** synthetic database, with a **governed deterministic oracle**.

### Validity principle (the load-bearing design choice)
**The LLM authors the world, never the answer key.** A large model (Qwen)
generates a *structured* world — fact-store rows, a timeline, events, and question
paraphrases — and **code computes every gold answer by executing the governed
query** (Spider/BIRD execution-accuracy + RLVR 2411.15124 verifiable rewards). No
LLM-judge in the scoring path → sidesteps the documented self-bias / judge-bias
stack (LLM-made-benchmarks lose ranking fidelity 2505.22830; multi-generator
mitigation 2409.11968; contamination survey 2406.04244; dynamic/fresh worlds
2502.17521).

### Injected events (each with a documented cause)
1. **Noise / fluctuation** → agent should HOLD the baseline.
2. **Sustained genuine shift** → agent should RE-BASELINE (governed).
3. **Stale plan / definition change** → agent should TOMBSTONE + supersede.

### Scoring — three deterministic layers
1. **Consistency / routing** — do paraphrase variants resolve to the *same governed
   query*? (cluster purity / XParaCon dispersion) × **numeric comparability**
   (execution match w/ tolerance) × **definition match** (ETM/AST equivalence, not
   raw EX — EX has ~23% false positives).
2. **Governance correctness** — the **drift-vs-genuine-change confusion matrix**
   (re-baselining precision/recall), **tombstone correctness** (no resurrection),
   contradiction resolution, **staleness abstention** (AbstentionBench 2506.09038),
   **FAMA-style** penalty for relying on superseded memory (2604.20006).
3. **Auditability** — deterministic **replay** to the same result + **tamper-evidence**
   (single-entry verify vs hash-chain/Merkle root, 2605.00065 / FG-Trac 2601.14971).

### Headline result
**Memory-ON vs memory-OFF**, identical deterministic scorer — the clean A/B
(ConvoMem 2511.10523 / Mem0 2504.19413 style) showing governed memory raises
consistency + cuts tokens while keeping the audit trail.

## How large models generate the validation data (deterministic-safe recipe)
1. LLM emits a **structured fact-store** (customers/orders/subscriptions, timestamps) —
   multiple generator models to avoid self-bias.
2. Each question authored once as a **canonical query** bound to its gold SQL/fn;
   gold = that query executed on the period's data.
3. LLM produces **N paraphrases × different askers** (diversity incentives 2401.06643,
   ParaFusion 2404.12010); **self-consistency filter** — keep only paraphrases that
   execute to the same gold answer.
4. **Drift = a structured mutation at timestamp T with a cause record**; gold
   recomputed from the mutated store.
5. **Receipts** = the exact rows/event-ids the query touched, emitted by the harness.

## Tooling
Build on **Inspect** (UK AISI — stateful multi-session solvers + pure-Python
deterministic `@scorer`) or **DeepEval** (Pytest ergonomics, ConversationalTestCase).
Avoid LLM-judge scoring; avoid OpenAI Evals (sunsetting). Governance scored on a
DCAM-style 1–5 rubric over {single-source-of-truth, lineage, reproducibility,
tamper-evidence, controlled evolution, drift observability}.

## Why the prototype is already the reference harness
- Ledger = governed, hash-chained memory (replay + verify already implemented).
- Closed-vocab plan = the governed query; reuse = the consistency mechanism.
- Drift detection + **re-baselining** (transient vs sustained) already built.
- Tombstones/decay = forgetting; receipts = auditability.
What's missing to become BMC-T: (a) the synthetic-world generator (Qwen),
(b) the 3-layer deterministic scorer, (c) the memory-OFF baseline mode, (d) an
Inspect/DeepEval harness + report.

## Incremental roadmap
1. **v0 (have):** cross-session consistency harness + reproducibility/drift metrics.
2. **v1:** Qwen world-generator → structured businesses + timelines + paraphrase
   sets + labeled events; execution-computed gold + receipts.
3. **v2:** 3-layer deterministic scorer; memory-ON/OFF A/B; cost-accuracy report.
4. **v3:** governance rubric + tamper-evidence/replay certification; leaderboard.
5. **v4:** publish BMC-T as an OSS benchmark (Impact: community adoption).

This is both a research contribution and a hackathon multiplier (a benchmark =
defensible novelty + OSS-adoption potential, scoring the Impact/Innovation rubric).
