# Known issues / lessons

## 2026-06-20 — Reused plans can be stale (canonicalization coverage)
**Symptom:** A reused cleaning plan only knows the value-variants it saw when
authored. If a later session introduces a *new* case/whitespace variant of a
value that was singular when the plan was authored, dedup misses it and the KPI
shifts — surfacing as spurious "drift".
**Cause:** `canonicalize` mappings are learned from the authoring session's
profile only.
**Why it's actually the point:** this is exactly the stale-memory / forgetting
problem Track 1 cares about. The right fix is *plan revision on drift* (escalate
to Qwen-Plus to re-author when drift fires), not silent re-cleaning.
**Current handling:** demo data authors with full variant coverage; drift is
flagged so a stale plan is visible rather than silent. **TODO (P2/P5):** on
`kpi.drift_flagged`, trigger re-authoring + `plan.deprecated` of the stale plan.

## Watch-list
- DashScope JSON-mode: confirm `response_format={"type":"json_object"}` is honored
  by `qwen-plus` on the compatible endpoint; if not, fall back to prompt-enforced
  JSON + a parse-retry.
- Raha leakage: `scrubdata-qwen3-4b` trained partly on Raha — report generalization
  numbers on held-out sets (Rayyan / ER-Magellan), not Hospital/Beers.
