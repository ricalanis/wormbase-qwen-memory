# Data governance & consistency of analysis over time

The demo deliberately changes *who asks* and *how they phrase it* every week
("How did we do?", "What's revenue looking like?", "Confirm last week's
top-line."). The agent always resolves these to **one governed query**, not a
fresh ad-hoc interpretation. That is the governance thesis.

## Why a hash-chained, plan-reusing MemoryAgent is a governance tool

| Governance need | How this system provides it |
|---|---|
| **Single source of metric truth** | "Revenue" = `SUM(amount)` over canonicalized, de-duplicated orders — defined once (`kpi.defined`), stored in the ledger, and **reused** every week. No drift from each analyst re-deriving it. |
| **Comparability over time** | Because the question (however phrased) maps to the *same* query, week-over-week numbers are genuinely comparable — no semantic drift from who ran the report. |
| **Reproducibility** | Same inputs → identical `value_hash`, byte-for-byte. The metric is a deterministic, replayable artifact, not a one-off. |
| **Auditability / lineage** | Every figure carries a receipt: the exact ledger entries (with hashes) that produced it (`agent.answer`). Replay state as of any past timestamp. |
| **Tamper-evidence** | The SHA256 hash chain detects any silent edit to historical numbers — the number is defensible in a board/audit setting. |
| **Change management** | Genuine moves are **flagged and attributed** (whale, churn) and a *sustained* shift is accepted as a new governed baseline; transient noise and rephrasing never move the number. |
| **Controlled evolution** | When the metric definition must change, that is a new authored plan recorded in the ledger (versioned), and old plans are tombstoned — forgetting is auditable, not silent. |

## The contrast it replaces
Typical weekly reporting: a spreadsheet or a chat-with-your-data tool re-computes
"revenue" from a slightly different filter/dedup each time, by whoever is asking,
with no record of how. Numbers quietly disagree week to week and can't be
reproduced or defended. Here, the *probabilistic* step (interpreting the
question, authoring the plan) is captured once as a *deterministic, governed,
replayable* artifact — so the analysis is consistent and auditable over time.
