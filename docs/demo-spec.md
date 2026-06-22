# Demo Experience Spec

Output of a marketer + product-designer + UX-designer sprint. The demo's one job:
make **"memory you can verify, not memory you have to trust"** obvious in seconds.

## Persona & narrative
**Maya, Head of Ops at Brewly (DTC coffee).** Every Monday she dumps last week's
messy order CSV and must answer the founders: *"How did we do, and what changed?"*
— a number she has to defend. Arc: **learn once → reuse free → drift flagged →
explained → verifiable.**

## Message hierarchy
- **Hook:** "Memory you can verify, not memory you have to trust."
- **Pillar 1 — provable, not plausible:** hash-chained ledger; re-run → identical
  SHA256; tamper → chain breaks; every number is a receipt.
- **Pillar 2 — cheaper the more you use it:** plan reuse; cost → 0 over sessions;
  local-Qwen triage, escalate to Qwen-Plus only on novel data.
- **Pillar 3 — explains why:** attribution where Σ(contributions) = ΔKPI; MCP
  exposes it to other AI.
- **Soundbite (at the WOW):** *"I changed one digit — and the memory caught me."*
- **Governance soundbite (consistency beat):** *"Different people, different words —
  one governed query. The number means the same thing every week."*
- **Precision guard (avoid overclaim):** we verify *reproducibility +
  tamper-evidence + grounding*, not model infallibility. Say "every number traces
  to a receipt," never "every number is right."

## UI (implemented in `ui/app.py` + `.streamlit/config.toml`)
Audit-grade dark theme; monospace for verifiable numbers; green=verified /
amber=flagged / red=tamper / blue=interactive. Single-column guided scroll,
**answer-first**, plumbing demoted to a trust strip. **Sessions gated behind
"Run Week N"** so the arc is experienced live (empty → loaded → aha).
Sections: headline + trust strip → revenue-over-time (drift annotated) →
why-it-moved (attribution **waterfall** + grounded receipts popovers) →
economics (cost per week) → **prove-it/tamper** chain rows + verify badge →
time-travel replay → ledger expander.

## 3-minute video script (director cut)
- **00:00–00:08 COLD OPEN** — close-up of a hash; edit one digit; chain snaps red.
  VO: *"This number changed. Watch what the memory does about it. Most AI agents
  would never notice. This one makes it impossible to hide."*
- **00:08–00:18** — title + tagline; cut to Maya, Monday 9am.
- **00:18–00:35** — upload CSV; Qwen-Plus (Alibaba Cloud) authors the plan; steps
  stream into the ledger.
- **00:35–00:50** — zoom the `prev_hash → hash` column. *"Memory here isn't a
  summary you trust — it's a hash-chained ledger."*
- **00:50–01:05** — next week: **REUSED · 0 tokens**; the token chart shows "with
  memory" flat while "without memory" climbs. *"It reuses the plan it already made —
  cheaper over time, not more expensive."*
- **01:05–01:28 GOVERNANCE BEAT** — weeks fast-forward; the question card changes
  asker + wording each week (Maya → Founder → Board: *"how'd we do?"*, *"what's the
  top-line?"*, *"confirm the number"*) while the **same governed query**
  (`total_amount = SUM(amount)`) stays pinned and the line stays comparable. Cut to
  the data-governance panel for a beat. VO: *"Here's what makes it trustworthy.
  Every week a different person asks in different words — but it always answers from
  the same governed query. One definition of revenue, reused and auditable. So the
  number means the same thing every week — that's data governance, not guesswork."*
- **01:28–01:45 DRIFT** — a week spikes: **DRIFT flagged, not applied**; the
  attribution waterfall resolves to one driver (East), Σ = ΔKPI. *"When the number
  really moves, it doesn't hide it — it shows which lever moved it, exactly."*
- **01:45–02:05** — grounded narrative; click a figure → its ledger receipt
  ("grounded ✓"). *"Every number traces to a receipt. If it can't, it isn't said."*
- **02:05–02:20** — replay-to-timestamp: scrub back; the state reconstructs from the
  ledger alone.
- **02:20–02:42 THE WOW** — split RUN 1 / RUN 2 → identical SHA256 → edit a stored
  value → chain cascades red. VO: *"Re-run it — same hash, every time. Change one
  stored number… and the whole chain turns red. You can't quietly rewrite the past."*
- **02:42–02:50** — *"Memory you can verify — not memory you have to trust."*
- **02:50–03:00 END CARD** — "Powered by Qwen-Plus on Alibaba Cloud · Track 1 ·
  github.com/ricalanis/wormbase-qwen-memory · Apache-2.0."

## Shooting checklist ($0, fragility-proof)
Pre-seed `scripts/seed_ledger.py`; confirm `results/consistency.json` numbers;
**record the Qwen-Plus call offline and splice** (never a live network round-trip
in the master take); the tamper + matching-hash must be the *real* verifier
(`scripts/prove_it.py`). Tools: OBS + Kdenlive/Shotcut; captions via YouTube auto
or Whisper; VO via Audacity; host unlisted YouTube 1080p.

## Title / thumbnail
Title: *"Memory You Can Verify — a MemoryAgent that dares you to check its work
(Qwen / Track 1)."* Thumbnail: split frame — same hash twice (green ✓) | one digit
edited, chain snapped (red ✗) — overlay **"PROVE IT. THEN BREAK IT."**

## Blog angle (secondary prize)
Headline: *"Your AI's memory is a vibe. Mine is a hash chain."* Beats: the unnamed
problem (vector memory you can't check) → the flip (recall becomes reproduction) →
the compounding payoff (cheaper + explainable).
