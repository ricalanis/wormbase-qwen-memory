# Benchmarks

Two layers: our own deterministic harness (runnable now, $0) and standard memory
benchmarks (pending Qwen Cloud credit validation).

## Runnable now (deterministic, offline)
- **Cross-session consistency** — `scripts/eval_consistency.py` → reproducibility,
  plan-reuse, planner-cost reduction, drift P/R/F1, run-to-run stability.
- **Learning curve** — `scripts/plot_curve.py` → memory-ON vs OFF (cost↓, accuracy↑).
- **Self-improvement** — `autoresearch.tune` → drift-F1 before/after tuning.

## Standard memory benchmarks (pending credits)
Generate hypotheses with Qwen-Plus, score with the benchmark's own judge.
```bash
export DASHSCOPE_API_KEY=sk-...
uv run python scripts/answer_jsonl.py questions.jsonl hyps.jsonl
```
- **PrefEval** (arXiv 2502.09597) — preference adherence. Best showcases the new
  preference memory. Run the explicit-preference 1–2 session slice; report adherence %.
- **LongMemEval-S** (arXiv 2410.10813) — limited-context recall + knowledge-update
  (= forgetting). Report accuracy on those two question types.
- **InsightBench** (arXiv 2407.06423) — business-analytics insight generation
  (planted-insight scoring). Maps to the analyst/attribution layer. Future work.

Leakage note: report data-cleaning generalization on held-out sets (Rayyan /
ER-Magellan), not Raha's Hospital/Beers (scrubdata-qwen3-4b trained partly on Raha).
