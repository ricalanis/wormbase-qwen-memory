# Evaluation

Two complementary prongs. The key finding from the literature survey: **no
existing benchmark tests cross-session memory *for data operations*** — that gap
is our contribution (Prong A). Prong B borrows standard memory benchmarks for
Track-1 credibility.

## Prong A — cross-session consistency harness (our contribution)

Fully runnable offline (deterministic ground truth — no LLM judge):

```bash
uv run python scripts/eval_consistency.py        # -> results/consistency.json
```

Latest run (6 sessions, drift injected at s4, 5 stability runs):

| Metric | Result |
|---|---|
| reproducibility_rate | **100%** (identical `value_hash` for identical input) |
| plan_reuse_rate | **100%** (every post-first session reused its plan) |
| planner_cost_reduction | **83%** (185 vs 1075 units — reuse is free) |
| drift precision / recall / F1 | **1.00 / 1.00 / 1.00** |
| run-to-run stability | **identical** across 5 fresh runs |
| hash-chain | **GREEN** |

Why trustworthy: scoring is deterministic, so any variance would be the agent's.
The harness anchors drift to the last *non-flagged* value, so a one-off anomaly
(the whale at s4) does not become the new baseline (s5 returns to normal,
correctly unflagged).

Grounding: DAComp-style repeated-run reproducibility protocol; AutoDCWorkflow
(arXiv 2412.06724) plan-vs-gold scoring; "Failing Loudly" (1810.11953) drift.

## Prong B — standard memory benchmarks (Track-1 credibility)

Run against Qwen-Plus on DashScope. We own the *generation* half; each benchmark
ships its own judge.

```bash
export DASHSCOPE_API_KEY=sk-...
# 1. produce hypotheses with Qwen-Plus
uv run python scripts/answer_jsonl.py longmemeval_s.jsonl hyps.jsonl
# 2. score with the benchmark's own judge (per its repo)
```

- **LongMemEval** (arXiv 2410.10813, github.com/xiaowu0162/longmemeval) — fact
  recall in limited context, multi-session reasoning, knowledge-updates,
  abstention. JSONL hypotheses + GPT-4o judge; point generation at DashScope.
- **PrefEval** (arXiv 2502.09597, github.com/amazon-science/PrefEval) —
  preference retention / cross-session consistency.
- Backup: **MemoryAgentBench** (2507.05257) — conflict-resolution = forgetting.

## Data-ops execution environment (planned wiring)

- **InfiAgent-DABench** (2401.05507) — CSV, deterministic regex scoring,
  `openai.api_base` editable → DashScope-ready. Primary plan-execute scorer.
- **BIRD-SQL Mini-Dev** (2305.03111) — SQLite execution accuracy (SQL path).
- **Raha/Baran** (github.com/BigDaMa/raha) — dirty+clean ground truth for repair
  precision/recall + byte-for-byte reproducibility. Report on held-out (Rayyan /
  ER-Magellan) to avoid scrubdata-qwen3-4b's Raha training overlap.
