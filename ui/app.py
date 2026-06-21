"""Streamlit UI — the demo surface for the 3-minute video.

Shows: KPI-over-time, hash-chain verify badge, replay-to-timestamp slider,
memory-recall panel (authored vs reused + planner cost), and the raw ledger.
Run: uv run streamlit run ui/app.py
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.demo import sessions
from wormbase_memory.inference import QwenCloudClient

st.set_page_config(page_title="WormBase Qwen Memory", layout="wide")


@st.cache_resource
def build_agent() -> DataOpsMemoryAgent:
    a = DataOpsMemoryAgent()
    for name, df, ts in sessions():
        a.ingest(df, name, ts=ts)
    return a


agent = build_agent()
q = QwenCloudClient()

st.title("🪱 WormBase Qwen Memory")
st.caption(
    "A data-operations MemoryAgent whose memory is a hash-chained ledger — "
    "reproducible KPIs across sessions, powered by Qwen Cloud."
)

ok, broken = agent.verify()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Hash-chain", "GREEN ✓" if ok else f"BROKEN @{broken}")
c2.metric("Reproducibility", f"{agent.reproducibility_rate():.0%}")
c3.metric("Ledger entries", len(agent.ledger.fetch()))
c4.metric("Planner", "Qwen-Plus" if q.available else "rules (offline)")

st.divider()
left, right = st.columns([3, 2])

with left:
    st.subheader("KPI over time")
    hist = agent.kpi_history("total_amount")
    if hist:
        chart_df = pd.DataFrame(
            {"ts": [h["ts"][:10] for h in hist],
             "total_amount": [h["value"] for h in hist]}
        ).set_index("ts")
        st.line_chart(chart_df)
    drift = [e.payload for e in agent.ledger.fetch("kpi.drift_flagged")]
    if drift:
        st.warning(
            "⚠ Drift flagged (not silently applied): "
            + ", ".join(f"{d['id']} {d['prev']}→{d['new']} ({d['rel_change']:+.0%})"
                        for d in drift)
        )

with right:
    st.subheader("Memory recall + triage")
    rows = []
    for e in agent.ledger.fetch("triage.decided"):
        p = e.payload
        rows.append({"session": p["dataset"],
                     "decision": p["decision"].upper(),
                     "triage": p["backend"], "sim": p["similarity"],
                     "worker_tokens": p["tokens"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(
        "Exact matches reuse for free; only gray-zone cases spend the local Qwen "
        "worker; novel data escalates to Qwen-Plus. Reuse costs 0 planner units."
    )

st.divider()
st.subheader("Replay to timestamp")
all_ts = sorted({e.ts for e in agent.ledger.fetch()})
labels = [t.isoformat()[:19] for t in all_ts]
idx = st.slider("As of", 0, len(labels) - 1, len(labels) - 1,
                format="%d") if len(labels) > 1 else 0
as_of = all_ts[idx]
st.caption(f"Ledger state as of **{as_of.isoformat()[:19]}**")
replayed = [e for e in agent.ledger.replay_until(as_of)
            if e.kind == "kpi.computed"]
latest: dict[str, float] = {}
for e in replayed:
    latest[e.payload["id"]] = e.payload["value"]
st.write({k: v for k, v in latest.items()})

with st.expander("Raw ledger (hash-chained trace)"):
    trace = [{"seq": e.seq, "ts": e.ts.isoformat()[:19], "kind": e.kind,
              "hash": e.hash.hex()[:12], "payload": str(e.payload)[:90]}
             for e in agent.ledger.fetch()]
    st.dataframe(pd.DataFrame(trace), hide_index=True, use_container_width=True)
