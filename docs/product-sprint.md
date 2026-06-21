# Product Design Sprint — aiming to win

Synthesis of a 5-lens sprint (winning-strategy, WormBase-spirit, Track-1
maximizer, demo designer, scoping lead). 2026-06-21.

## Judging rubric (verbatim from Devpost)
- **Technical Depth & Engineering 30%** — sophisticated QwenCloud use, **MCP
  integrations** (named explicitly), engineering innovation, perf.
- **Innovation & AI Creativity 30%** — architecture quality, clean code,
  non-trivial logic, error handling.
- **Problem Value & Impact 25%** — authentic pain, OSS adoption potential.
- **Presentation & Documentation 15%** — clear demo with **key logic visualized**.

Prize: $7K + $3K credits/track; blog award ($500×). **Verify deadline (page says
Jul 8, notes say Jul 9). Build to Jul 8.**

## Win thesis
**"Memory you can verify, not memory you have to trust."** Generic Track-1
entries = vector-DB-over-chat memory you must trust. Ours = hash-chained,
replayable, tamper-evident memory + a deterministic analyst that explains *why*
metrics move with receipt-backed numbers, gets cheaper each session, and exposes
its memory to other AI via MCP.

## Demo WOW (anchor the 3-min video)
**"Prove it, then break it":** re-run an analysis in a fresh session → identical
SHA256 hash on screen → edit one stored number → chain breaks, flagged red. Then
"every number has a receipt" — click a figure → jump to its ledger entry.

## Persona / scenario (judge-legible)
**Maya, Head of Ops at "Brewly" (12-person DTC coffee).** Every Monday she dumps
last week's messy order CSV and asks "how did we do, and what changed?" — needs a
Slack-ready exec summary she can defend to founders. Recurring ritual = the
literal case for compounding memory; "defend to founders" = reproducibility.

## Prioritized roadmap (each tagged to the rubric)

### P0 — Deliverables + proof (MUST; mostly required artifacts)
- **Validate Qwen Cloud credits + 1 live Qwen-Plus run** (de-risk the long pole NOW). [30/30]
- **Alibaba Cloud deploy proof at $0** — free-tier ECS, billing alert, record, tear down. [required]
- **3-min video** (Brewly story; WOW = replay + matching-hash + tamper-break). [15]
- **Final text description + architecture diagram check.** [15]

### P1 — Make memory visible + verifiable (the WOW + credibility)
- **Receipts-backed Q&A** — `answer(kpi)` → prose + clickable ledger-entry
  citations; gate with `narrative.is_grounded` (refuse ungrounded numbers). [30/15]
- **"Prove it then break it"** — matching-hash on re-run + tamper detection,
  visualized in UI. [30/15]
- **Smarter-over-sessions curve** — PNG from the eval harness: planner-cost↓ and
  drift-decision-accuracy→1.0 vs a memory-OFF control line. [30/25]

### P2 — Close Track-1 gaps (fix doc-vs-code; rubric coverage)
- **Real forgetting** — `plan.deprecated`/`kpi.deprecated` actually filter
  `recall.best_candidate`; `created`/`last_verified` + decay (30d/14d);
  `replay_until` still shows the pre-deprecation world. Demo: "deprecated rule"
  scenario. [Track-1 "timely forgetting"]
- **Preference memory** — `pref.set`/`pref.superseded` folded last-writer-wins;
  wire 2 prefs: drift-threshold override + narrative style. Persists
  cross-session. [Track-1 "preferences"; PrefEval]

### P3 — Differentiator (SHOULD; MCP is named in the 30% criterion)
- **MCP server** (FastMCP, ~80 lines, pure reads over the ledger): resources
  `memory://kpi/{id}/history`, `memory://ledger/verify`; tools `ask_kpi`,
  `explain_change`, `replay_until`. Ship `claude_desktop_config.json`. [30 + Impact]

### P4 — Credibility footnote (only if time + credits)
- One **PrefEval** number (preferences) + one **LongMemEval-S** number
  (limited-context recall + knowledge-update) via `scripts/answer_jsonl.py`. [25]

### WON'T (this cycle — explicit anti-scope)
Metric-governed self-improvement loop · forecast/regression/cohort/what-if
modelling tier · full InsightBench wiring · WormBase lake/8-loops · connectors/
SurfaceDriver · multi-tenant identity/roles · chat/voice/OpenClaw · Postgres stack.

## Minimum Lovable Product (smallest set that still wins)
Everything already built + (1) one live Qwen-Plus cloud run captured, (2)
receipts-backed Q&A, (3) the three deliverables. Story: messy CSV → Qwen-Plus
authors a plan on Alibaba Cloud → next session reuses it free → a metric moves →
agent explains why in prose with every number traceable to a tamper-evident hash
→ replay to prove it.

## 3-week sequence (→ Jul 8)
- **W1 (Jun 21–27):** validate credits + live run (D1–2); receipts Q&A (D2–3);
  LLM narration gated by `is_grounded` (D4); stand up ECS (D5); keep tests green;
  tag a submittable `v1`.
- **W2 (Jun 28–Jul 4):** record cloud proof + tear down (D8–9); real forgetting +
  preferences (D10); MCP server (D11); UI polish on demo path only (D12); lock
  video script + text (D13–14).
- **W3 (Jul 5–8):** record video offline (deterministic spine + spliced cloud
  clip) (D15–16); edit/upload, finalize SUBMISSION.md (D17); **submit Jul 8**.

## Top risks
1. **Credits don't validate** → resolve D1–2; project already runs $0; a single
   laptop DashScope call satisfies "live Qwen-Plus" decoupled from ECS.
2. **Demo fragility** → record offline (deterministic, never hits network);
   splice pre-captured cloud clip.
3. **Scope creep** → this MoSCoW is the guardrail; keep a permanently-submittable tag.
4. **$0 blown by deploy** → free-tier ECS + billing alert + immediate teardown.
5. **Time/single-operator** → front-load deliverables; submit a day early.

## UI polish (low effort, high demo impact)
Preference chip ("📌 report in $K · lead with biggest mover — learned wk1");
cost-drop `st.metric` (0 ▼ from 1); attribution mini-bar (East +$2.0K ▶ others $0).
