# Research: from data-ops to business-analyst agent (arXiv-grounded)

Pivot the agent's depth from *cleaning* to the full analyst lifecycle —
**explore → model/analyze → communicate** — keeping the hash-chained,
reproducible-memory thesis. (arXiv research, 2026-06-21.)

## Keystone finding
The capability separating a real analyst agent from a chart-bot is **causal
attribution of a metric change**: *why did the KPI move, and which lever caused
it* (`metric_tree → contribution_to_change → root_cause_drilldown`). It slots
onto what we already do — we detect KPI **drift**; the analyst move is to
**explain** it, **recommend**, and **remember** the explanation.

## Pipeline stages (union across Data Interpreter, AutoKaggle, surveys)
understand → profile → clean → **explore** → feature → **model/analyze** →
validate → **communicate**. We cover clean + KPI; expand the bold stages.

## Closed-vocab ops to add (all deterministic pandas/sklearn/statsmodels)
- **Explore:** `distribution`, `correlation`, `top_segments_by_metric`,
  `trend` (Mann-Kendall + Sen slope), `distribution_diff` (JS-divergence),
  `simpsons_check`, `outlier_scan`, `crosstab`.
- **Analyze/model:** `decompose_kpi_change` (mix/rate, additive — Σ = ΔKPI),
  `segment_contribution`, `shapley_change_attribution` (CF-Shapley upgrade),
  `fit_regression`, `feature_importance` (perm/SHAP), `forecast`
  (ETS/ARIMA/Chronos/TimesFM), `cohort_retention`, `ab_test`, `anomaly_detect`.
- **Communicate:** `extract_data_facts` (DataScout 10-type taxonomy),
  `rank_insights_by_importance` (impact × significance), `summarize_findings`,
  `recommend_actions`, `caption_chart`, `compose_report`.
- **BA processes:** `metric_tree`, `funnel_analysis`, `benchmark_vs_target`,
  `what_if_scenario`.

## Determinism / reproducibility (maps to the ledger)
Deterministic and ledger-storable: all statistical detectors (Mann-Kendall,
JS-divergence, IQR/z, Cramér's V), subspace beam search, impact×significance
ranking, mix/rate decomposition, Shapley (efficiency axiom: Σ = ΔKPI). Stochastic
(record the chosen op-plan + seed + lib versions): LLM op selection, model
fitting (seed everything), narration. Foundation forecasters: pin checkpoint hash,
store output array.

## The novel contribution our hash chain enables
**Citation-per-clause grounded narrative:** the LLM narrates only from fact
tuples that carry their producing ledger entry's hash; a *deterministic*
post-check extracts every data number from the prose and asserts it appears in a
cited entry. Faithfulness becomes a chain-of-custody proof, not an LLM judge.

## Evaluation
- **InsightBench** (2407.06423) — planted-insight scoring for business-analytics
  agents; best fit. Endpoint-compatible (DashScope).
- **CORGI** (2510.07309) — descriptive→explanatory→predictive→recommendational
  tiers map 1:1 to our op tiers.
- **DSBench** (2409.07703), **InfiAgent-DABench** (2401.05507) — execution-graded.

## Key citations (arXiv IDs confirmed unless flagged)
Agents: Data Interpreter 2402.18679 · DS-Agent 2402.17453 (CBR retrieve/reuse/
revise/retain — our ledger is the case base) · AutoKaggle 2410.20424 (concrete op
toolkit) · Agent K 2411.03562 · survey 2509.23988.
EDA/insights: QUIS 2410.10270 · InsightBench 2407.06423 · 2503.11664 ·
InsightEval 2511.22884 · Simpson's 1805.03094. (QuickInsights/MetaInsight/Top-K
Insights are SIGMOD, not arXiv.)
Modeling/RCA/forecast: CF-Shapley 2208.08399 · multiply-robust 2404.08839 ·
CMMD 2203.16280 · BALANCE 2301.13572 · Chronos 2403.07815 · TimesFM 2310.10688 ·
TimeGPT 2310.03589. (Adtributor/HotSpot/Squeeze are conference, not arXiv.)
Communication: DataNarrative 2408.05346 · Hybrid LLM/Rule 2404.15604 · DataScout
2504.17334 · faithfulness review 2501.00269 · Narrative Player 2410.03268 ·
Chart-to-Text 2203.06486 · VisText 2307.05356.
Unconfirmed (verify before citing): survey 2510.04023; Mind2Report 2601.04879;
DAComp 2512.04324; several 26xx 2026 IDs.
