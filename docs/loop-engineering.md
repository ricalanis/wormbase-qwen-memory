# Loop engineering → consistency + token savings (arXiv-grounded)

**Loop engineering** = deliberately designing the agent's control loop
(generate → act → observe → verify → continue/stop): its body, **halting rule**,
the **verification signal** that gates each iteration, the **memory** carried
between iterations, and **which steps are stochastic vs deterministic**.
"An agent = an LLM + tools + a loop." Context engineering (which tokens enter each
iteration) is the sister discipline. (Survey: Context Engineering 2507.13334; CoALA
2309.02427.)

## Two load-bearing principles

**For CONSISTENCY:** *Gate every iteration on an external, lower-variance
verification signal, and capture each accepted probabilistic output once as a
frozen, replayable artifact — so the loop consumes verified state instead of
re-rolling it.* Self-consistency (2203.11171), process reward models
(2305.20050; ThinkPRM 2504.16828), verifier reranking, and tool-grounded
execution (PAL/PoT) all work because the **check is more stable than the
generation**. Intrinsic self-correction WITHOUT an external signal degrades
(LLMs Cannot Self-Correct Yet 2310.01798); hallucinations snowball (2305.13534);
memory scaffolds can *hurt* long-horizon reliability (Beyond pass@1 2603.29231).

**For TOKEN SAVINGS:** *Make the plan cache the primary cost lever — a
profile-fingerprinted semantic plan cache with confidence-gated, freshness-stamped
recall: replay on hit (0 planner tokens), escalate to the big model only on
cache-miss OR drift.* This applies cascade logic (FrugalGPT 2305.05176 up to ~98%
cut; AutoMix 2310.12963; RouteLLM 2406.18665) to the *planner* — the most
expensive token stream. Plan reuse is the order-of-magnitude prize (DS-Agent
2402.17453 ≈12× cheaper/run; AWM 2409.07429 and Memp 2508.06433 "fewer steps +
tokens"). **The decisive risk across every reuse paper: stale/mismatched recall
under drift.** The recall gate (similarity threshold + `last_verified` decay +
triage confidence) is load-bearing.

## Our four loops, mapped + incremental improvements

| Loop | Literature pattern | Incremental improvements (toward consistency + tokens) |
|---|---|---|
| **recall → triage → reuse/escalate** | LLM cascade/router (FrugalGPT, AutoMix, RouteLLM) + memory recall (MemGPT 2310.08560) | (1) reuse-vs-escalate = **verifier score + fixed threshold**, not free-form judgment; (2) **deterministic recall** (fixed embedder, top-k, tie-break); (3) **semantic plan cache** keyed by profile fingerprint; (4) **confidence/consistency-gated** escalation (AutoMix) |
| **PEVR write (propose→execute→verify→resolve)** | generate-verify + process verification + provenance (CRITIC 2305.11738; CoVe 2309.11495; PRM 2305.20050) | (1) **verify each step**, not just the final write; (2) persist the proposal as a **frozen hash-addressed artifact**, then execute/verify deterministically; (3) **independent verifier** (tool/diff), never self-grade (2310.01798) |
| **drift → re-baseline** | reflection/consolidation (Generative Agents 2304.03442; A-MEM 2502.12110) | (1) **deterministic golden-set + threshold** trigger; (2) re-baseline from **oracle-verified anchors only** (avoid self-consumption collapse 2305.17493); (3) **version + hash** each baseline (auditable, reversible) |
| **metric-governed self-improvement** | metric-gated self-training / RLVR (STaR 2203.14465; Self-Rewarding 2401.10020; Tulu3 2411.15124; DeepSeek-R1 2501.12948) | (1) **gate promotion on an external frozen metric**, accept only strict improvement; (2) keep a **fresh real-data fraction**; (3) promotion = **deterministic logged commit** (bisectable/rollback) |

We already do the highest-leverage moves: closed-vocab plan = the probabilistic
step **captured once as a deterministic replayable artifact**; reuse = 0 planner
tokens; cascade triage; `last_verified` decay; hash-chained provenance. Loop
engineering *validates the architecture* and gives the backlog + eval below.

## Loop evaluation metrics
- **Consistency:** consistency@k (agreement over k repeats); **pass^k** (all k
  succeed — the production number, 2603.29231); Reliability Decay Curve / Graceful
  Degradation by horizon (2603.29231).
- **Efficiency:** cost-per-**solved**-task; tokens/session (split input/output);
  **success@cost**; **cost-accuracy Pareto frontier** (Inference Scaling Laws
  2408.00724); escalation/deferral rate + curve.
- **Loop mechanics:** iterations-to-converge (+ tail); **marginal value per
  iteration** (the stop signal); **regression rate** (fraction made *worse*);
  escalation precision/recall; verification-cost-per-error-caught (ThinkPRM);
  **plan-reuse hit rate + positive-hit-rate** (never hit-rate alone).

## Incremental-improvement methodology
1. **Ablate one loop knob at a time** — a component earns its place only if removing
   it moves you *off* the cost-accuracy Pareto frontier.
2. **Build cost-accuracy curves, not single numbers** — sweep the compute/quality
   knob (max PEVR iters, vote-k, escalation threshold); a change that only slides
   *along* the frontier is a budget choice, not an improvement.
3. **A/B memory on/off, paired per task** (high variance → pair, don't compare means).
4. **Net-negative test** — never add an iteration unless marginal value > its cost
   AND regression rate stays flat (the 2310.01798 trap).
5. **Hygiene** — fixed seeds, CIs over repeats, frozen versioned eval set, dev/holdout split.

## Prioritized backlog (order: instrument → consistency gates → token cutters)
1. **Reliability-curve instrumentation** by task length/horizon (enabler). `proof: Decay Curve per release` ✅ **IMPLEMENTED** (`eval/reliability.py`, `scripts/plot_reliability.py`): memory-ON holds decision-accuracy 1.0 at flat cost across horizons 3→12; memory-OFF decays 1.0→0.75 with cost ballooning 543→2151; pass^k=1.0.
2. **Deterministic verifier gate on plan reuse** — reuse only if the stored plan still passes a cheap rule-check. `C:++ T:+ proof: regression rate ↓, reuse-success ↑` ✅ **IMPLEMENTED** (`reuse_guard.py`): column presence + executor-applies + residual case/whitespace variant collision + KPI computability; on fail → `plan.reuse_rejected` + tombstone + re-author. Prevents the stale-canonicalize regression (450 vs wrong 600); 0 false-rejects across the 12-week sim.
3. **Marginal-value early-stop in PEVR** — stop when verify-pass Δ/iter ≤ threshold. `C:0/+ T:++ proof: iters ↓, acc flat`
4. **Staleness check before reuse** (we have decay governance) — re-verify past-TTL plans. `C:++ T:− proof: aged-memory regression ↓`
5. **Escalation threshold tuning** on the cascade. `C:+ T:++ proof: escalation precision ↑, success@cost ↑` ✅ **IMPLEMENTED** (`eval/escalation.py`, `scripts/tune_escalation.py`): sweeps the reuse-similarity threshold; lowering 0.9→0.5 cuts tokens 380→177 (~53%) with full correctness (chain ✓, repro 1.0, 0 rejects) — safe *because* the verifier-gate (#2) guards stale reuse. `tune()` persists the success@cost-optimal threshold as a preference (policy.tuned).
6. **Small CoT verifier instead of full re-solve** as the catch-gate (ThinkPRM). `C:+ T:++ proof: verify-cost-per-error-caught ↓`
7. **consistency@k vote only on low-confidence queries** (not blanket sampling). `C:++ T:+ proof: consistency@k ↑ at small token delta`

## The single eval test for any loop change
**Did it move the cost-accuracy Pareto frontier outward — measured as success@cost
on a frozen, repeated, held-out set with regression rate held flat — rather than
just sliding along the existing frontier?**

## Tie-in
Loop engineering is the *strategy* (raise consistency, cut tokens); **BMC-T**
(`docs/vision-bmc-eval.md`) is the *eval* that scores it over time — the
cost-accuracy + consistency-over-time + governance numbers that prove a loop
change is real. Our `eval/consistency.py` + `eval/curve.py` are v0 of this harness.
