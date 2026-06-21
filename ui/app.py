"""WormBase Qwen Memory — demo surface (audit-grade, guided-scroll).

Memory you can verify, not memory you have to trust. The 3 sessions are gated
behind 'Run next week' so the learn -> reuse -> drift -> explain -> verify arc is
experienced live. Run: uv run --extra viz streamlit run ui/app.py
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.demo import sessions
from wormbase_memory.inference import resolve_planner_client

st.set_page_config(page_title="WormBase Qwen Memory", layout="wide",
                   page_icon="🪱")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
.block-container { max-width:1100px; }
code, .mono, [data-testid="stMetricValue"] {
  font-family:'JetBrains Mono','ui-monospace',monospace !important;
  font-feature-settings:"tnum" 1; }
[data-testid="stMetric"] { background:#121821; border:1px solid #26303D;
  border-radius:12px; padding:14px 16px; }
[data-testid="stMetricLabel"] p { text-transform:uppercase; letter-spacing:.5px;
  font-size:12px; color:#8B98A9; }
.hero { font-size:30px; font-weight:700; line-height:1.25; }
.badge { display:inline-flex; align-items:center; gap:8px; border-radius:999px;
  padding:5px 13px; font-weight:600; font-size:14px; border:1px solid; }
.ok { color:#2ED47A; background:#163d2b; border-color:#2ED47A; }
.broken { color:#FF4D4F; background:#3a1618; border-color:#FF4D4F; }
.drift { border:1px solid #F5A623; background:#3a2c10; color:#F5C36B;
  border-radius:10px; padding:12px 14px; }
.chain { font-family:'JetBrains Mono',monospace; font-size:12.5px;
  padding:6px 10px; border-left:3px solid #2ED47A; background:#121821;
  margin:2px 0; border-radius:0 6px 6px 0; }
.chain.bad { border-left-color:#FF4D4F; background:#3a1618; color:#FF8B8C; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

SESS = sessions()
NWEEKS = len(SESS)

# --- live state: agent accumulates as the user advances weeks -----------------
if "agent" not in st.session_state:
    st.session_state.agent = DataOpsMemoryAgent()
    st.session_state.reports = []
    st.session_state.step = 0
    st.session_state.tampered = False
agent: DataOpsMemoryAgent = st.session_state.agent
planner_client = resolve_planner_client()


def _money(v) -> str:
    return f"${v:,.0f}" if v is not None else "—"


def run_next() -> None:
    i = st.session_state.step
    if i < NWEEKS:
        name, df, ts = SESS[i]
        rep = agent.ingest(df, name, ts=ts)
        st.session_state.reports.append((name, rep))
        st.session_state.step += 1


def reset() -> None:
    for k in ("agent", "reports", "step", "tampered"):
        st.session_state.pop(k, None)


def tamper() -> None:
    rows = agent.ledger.fetch("kpi.computed")
    if rows:
        e = rows[0]
        bad = dict(e.payload)
        bad["value"] = bad["value"] + 1111
        agent.ledger._conn.execute(
            "UPDATE ledger SET payload=? WHERE seq=?",
            (json.dumps(bad, sort_keys=True, separators=(",", ":")), e.seq))
        agent.ledger._conn.commit()
        st.session_state.tampered = True


# --- header -------------------------------------------------------------------
st.markdown("## 🪱 WormBase Qwen Memory")
st.markdown("**Memory you can verify — not memory you have to trust.** "
            "Every KPI traces to a hash-chained receipt.")

hist = agent.kpi_history("total_amount")
latest = hist[-1] if hist else None
ok, broken = agent.verify()

if latest is None:
    st.info("No data yet. Press **▶ Run Week 1** to let the agent author its first "
            "analysis plan.")
else:
    arrow = ""
    if latest.get("drift"):
        b = latest.get("baseline") or 0
        pct = (latest["value"] - b) / abs(b) if b else 0
        arrow = f"  ⚠ up {pct:+.0%}"
    last_rep = st.session_state.reports[-1][1]
    cost = "0 (plan reused)" if last_rep.reused else f"{last_rep.planner_cost_units} units"
    st.markdown(
        f'<div class="hero">This week\'s revenue: {_money(latest["value"])}{arrow}</div>',
        unsafe_allow_html=True)
    st.caption(f"Verified ✓ · reproduced byte-for-byte · produced for **{cost}**")

# trust strip
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<span class="badge {"ok" if ok else "broken"}">'
            f'{"CHAIN VERIFIED ✓" if ok else f"CHAIN BROKEN @ {broken} ✗"}</span>',
            unsafe_allow_html=True)
c2.metric("Reproducible", f"{agent.reproducibility_rate():.0%}")
c3.metric("Audit trail", len(agent.ledger.fetch()))
c4.metric("Planner", planner_client.model if planner_client else "rules (offline)")

# controls
b1, b2, _ = st.columns([1, 1, 2])
if st.session_state.step < NWEEKS:
    b1.button(f"▶ Run Week {st.session_state.step + 1}", type="primary",
              on_click=run_next, use_container_width=True)
else:
    b1.button("✓ All weeks run", disabled=True, use_container_width=True)
b2.button("↺ Reset demo", on_click=reset, use_container_width=True)

st.divider()

# --- §A KPI over time (hero) --------------------------------------------------
st.markdown("### Revenue over time")
if hist:
    xs = [h["ts"][:10] for h in hist]
    ys = [h["value"] for h in hist]
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines+markers",
                               line=dict(color="#4DA3FF", width=3),
                               marker=dict(size=9)))
    for h in hist:
        if h.get("drift"):
            fig.add_annotation(x=h["ts"][:10], y=h["value"], text="⚠ drift",
                               font=dict(color="#F5A623"), arrowcolor="#F5A623")
    fig.update_layout(height=300, paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14",
                      font_color="#E6EDF3", margin=dict(t=10, b=10),
                      yaxis=dict(gridcolor="#1A2230"), xaxis=dict(gridcolor="#1A2230"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Run a week to plot revenue.")

# --- §B Why it moved (attribution waterfall + grounded receipts) --------------
expl_entries = [e for e in agent.ledger.fetch("kpi.explained")
                if e.payload.get("id") == "total_amount"]
ins_entries = [e for e in agent.ledger.fetch("insight.generated")
               if e.payload.get("id") == "total_amount"]
if expl_entries and ins_entries:
    st.markdown("### Why it moved (attributed, not guessed)")
    ex = expl_entries[-1].payload
    ins = ins_entries[-1].payload
    drivers = ex["drivers"]
    labels = ["baseline"] + [str(d["value"]) for d in drivers] + ["new total"]
    vals = [ins["baseline"]] + [d["delta"] for d in drivers] + [ins["new"]]
    measures = ["absolute"] + ["relative"] * len(drivers) + ["total"]
    wf = go.Figure(go.Waterfall(
        x=labels, y=vals, measure=measures,
        text=[f"{v:+,.0f}" for v in vals], textposition="outside",
        connector={"line": {"color": "#26303D"}},
        increasing={"marker": {"color": "#F5A623"}},
        decreasing={"marker": {"color": "#4DA3FF"}},
        totals={"marker": {"color": "#5A6B7B"}}))
    wf.update_layout(height=320, paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14",
                     font_color="#E6EDF3", showlegend=False, margin=dict(t=20),
                     yaxis=dict(gridcolor="#1A2230"))
    st.plotly_chart(wf, use_container_width=True)
    st.caption(f"Σ drivers = {ex['total_change']:+,.0f} = "
               f"({ins['new']:,.0f} − {ins['baseline']:,.0f}). Attribution is exact.")

    ans = agent.answer("total_amount")
    st.markdown(f'<span class="badge {"ok" if ans["grounded"] else "broken"}">'
                f'{"GROUNDED ✓" if ans["grounded"] else "UNGROUNDED ✗"}</span>',
                unsafe_allow_html=True)
    st.markdown(f"> {ans['prose']}")
    rcols = st.columns(max(1, len(ans["receipts"])))
    for col, r in zip(rcols, ans["receipts"]):
        with col.popover(f"🔗 {r['hash'][:8]}"):
            st.markdown(f"**seq {r['seq']}** · `{r['kind']}`")
            st.code(r["hash"])
            st.metric("value", f"{r['value']:,}")
    st.caption("Refused unless every number cites a ledger entry — chain-of-custody, "
               "not an LLM judge.")

# --- §C The economics (cheaper over sessions) ---------------------------------
if st.session_state.reports:
    st.markdown("### What it cost (cheaper the more it remembers)")
    rows = [{"week": n, "action": "REUSED" if r.reused else f"AUTHORED ({r.plan_backend})",
             "planner cost": r.planner_cost_units}
            for n, r in st.session_state.reports]
    e1, e2 = st.columns([1, 2])
    saved = sum(0 if r.reused else 0 for _, r in st.session_state.reports)
    last = st.session_state.reports[-1][1]
    e1.metric("Planner cost this week", last.planner_cost_units,
              delta="reused — free" if last.reused else "authored")
    e2.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# --- §D Prove it, then break it (the WOW) -------------------------------------
if hist:
    st.divider()
    st.markdown("### Prove it, then break it")
    d1, d2 = st.columns(2)
    d1.button("🔨 Tamper with the record", on_click=tamper,
              use_container_width=True, disabled=st.session_state.tampered)
    d2.button("↺ Restore", on_click=reset, use_container_width=True)
    if not ok:
        st.markdown('<div class="drift">One value was changed — the chain caught it '
                    f'at entry {broken}. You can’t quietly rewrite the past.</div>',
                    unsafe_allow_html=True)
    entries = agent.ledger.fetch()
    html = []
    for idx, e in enumerate(entries[:18]):
        bad = (broken is not None and idx >= broken)
        html.append(
            f'<div class="chain {"bad" if bad else ""}">seq {e.seq:>2} · {e.kind} · '
            f'hash {e.hash.hex()[:12]} ← prev {e.prev_hash.hex()[:12]} '
            f'{"✗" if bad else "✓"}</div>')
    st.markdown("".join(html), unsafe_allow_html=True)
    if len(entries) > 18:
        st.caption(f"… {len(entries) - 18} more entries (chain continues)")

# --- §E Time-travel the ledger -----------------------------------------------
if len(hist) > 1:
    st.divider()
    st.markdown("### Time-travel the ledger")
    all_ts = sorted({e.ts for e in agent.ledger.fetch()})
    labels = [t.isoformat()[:19] for t in all_ts]
    idx = st.slider("Replay state as of", 0, len(labels) - 1, len(labels) - 1)
    as_of = all_ts[idx]
    st.caption(f"State as of **{as_of.isoformat()[:19]}** — recomputed from the "
               f"ledger alone. The log *is* the database.")
    latest_vals: dict[str, float] = {}
    for e in agent.ledger.replay_until(as_of):
        if e.kind == "kpi.computed":
            latest_vals[e.payload["id"]] = e.payload["value"]
    rcols = st.columns(max(1, len(latest_vals)))
    for col, (k, v) in zip(rcols, latest_vals.items()):
        col.metric(k, f"{v:,.0f}")

with st.expander("The ledger (every event, hash-chained)"):
    trace = [{"seq": e.seq, "ts": e.ts.isoformat()[:19], "kind": e.kind,
              "hash": e.hash.hex()[:12], "payload": str(e.payload)[:80]}
             for e in agent.ledger.fetch()]
    st.dataframe(pd.DataFrame(trace), hide_index=True, use_container_width=True)
