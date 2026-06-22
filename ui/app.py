"""WormBase Qwen Memory — animated simulation demo (audit-grade, guided-scroll).

Memory you can verify, not memory you have to trust. Press ▶ Play to watch 12
weeks of Maya's revenue review unfold: the plan is authored once then reused for
free, the revenue line grows, and drift events (a whale, then a churn) are
flagged and explained as they happen. Run: make ui
"""

from __future__ import annotations

import json
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.inference import resolve_planner_client
from wormbase_memory.simulate import simulate_weeks

st.set_page_config(page_title="WormBase Qwen Memory", layout="wide", page_icon="🪱")

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
.event { border:1px solid #26303D; background:#121821; border-radius:10px;
  padding:10px 14px; font-size:15px; }
.chain { font-family:'JetBrains Mono',monospace; font-size:12.5px;
  padding:6px 10px; border-left:3px solid #2ED47A; background:#121821;
  margin:2px 0; border-radius:0 6px 6px 0; }
.chain.bad { border-left-color:#FF4D4F; background:#3a1618; color:#FF8B8C; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

SESS = simulate_weeks(12)
NWEEKS = len(SESS)

if "agent" not in st.session_state:
    # high staleness: weekly cadence over 12 weeks shouldn't trigger decay
    st.session_state.agent = DataOpsMemoryAgent(staleness_days=3650)
    st.session_state.reports = []
    st.session_state.step = 0
    st.session_state.tampered = False
    st.session_state.playing = False
agent: DataOpsMemoryAgent = st.session_state.agent
planner_client = resolve_planner_client()


def _money(v) -> str:
    return f"${v:,.0f}" if v is not None else "—"


def run_next() -> None:
    i = st.session_state.step
    if i < NWEEKS:
        wk = SESS[i]
        rep = agent.ingest(wk["df"], wk["name"], ts=wk["ts"])
        st.session_state.reports.append((wk, rep))
        st.session_state.step += 1


def reset() -> None:
    for k in ("agent", "reports", "step", "tampered", "playing"):
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
            "12 weeks of Maya's revenue review — the agent learns once, reuses for "
            "free, and explains every move. Each number traces to a hash-chained receipt.")

# --- controls -----------------------------------------------------------------
co1, co2, co3, co4 = st.columns([1.1, 1, 1, 2])
play_clicked = co1.button("▶ Play simulation", type="primary", width="stretch",
                          disabled=st.session_state.step >= NWEEKS)
co2.button("⏭ Step a week", on_click=run_next, width="stretch",
           disabled=st.session_state.step >= NWEEKS)
co3.button("↺ Reset", on_click=reset, width="stretch")
speed = co4.slider("seconds per week", 0.2, 1.5, 0.6, 0.1)


def render_window(container) -> None:
    """Draw the live simulation window (metrics + chart + current event)."""
    with container.container():
        hist = agent.kpi_history("total_amount")
        ok, broken = agent.verify()
        reports = st.session_state.reports

        # trust strip
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<span class="badge {"ok" if ok else "broken"}">'
                    f'{"CHAIN VERIFIED ✓" if ok else f"CHAIN BROKEN @ {broken} ✗"}</span>',
                    unsafe_allow_html=True)
        c2.metric("Reproducible", f"{agent.reproducibility_rate():.0%}")
        last_rep = reports[-1][1] if reports else None
        c3.metric("Planner cost / wk", 0 if (last_rep and last_rep.reused)
                  else (last_rep.planner_cost_units if last_rep else 0),
                  delta="reused — free" if (last_rep and last_rep.reused) else None)
        c4.metric("Planner", planner_client.model if planner_client else "rules (offline)")

        # current week + event
        if reports:
            wk, rep = reports[-1]
            week_no = wk["week"]
            rev = rep.kpis.get("total_amount")
            tag = "reused (free)" if rep.reused else f"authored · {rep.planner_cost_units} units"
            st.markdown(f'<div class="hero">{wk["name"]}: {_money(rev)} '
                        f'<span style="font-size:15px;color:#8B98A9">· {tag}</span></div>',
                        unsafe_allow_html=True)
            if rep.explanations:
                st.markdown(f'<div class="drift">⚠ {rep.explanations[0]}</div>',
                            unsafe_allow_html=True)
            elif wk["event"]:
                st.markdown(f'<div class="event">{wk["event"]}</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="event">stable — plan reused, no surprises</div>',
                            unsafe_allow_html=True)
        else:
            st.info("Press **▶ Play simulation** (or **⏭ Step a week**) to begin.")

        # growing revenue chart with drift markers
        if hist:
            xs = list(range(1, len(hist) + 1))
            ys = [h["value"] for h in hist]
            colors = ["#F5A623" if h.get("drift") else "#4DA3FF" for h in hist]
            sizes = [16 if h.get("drift") else 8 for h in hist]
            fig = go.Figure(go.Scatter(
                x=xs, y=ys, mode="lines+markers", line=dict(color="#4DA3FF", width=3),
                marker=dict(color=colors, size=sizes, line=dict(color="#0B0F14", width=1))))
            fig.update_layout(height=300, paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14",
                              font_color="#E6EDF3", margin=dict(t=10, b=10),
                              xaxis=dict(title="week", gridcolor="#1A2230",
                                         range=[0.5, NWEEKS + 0.5]),
                              yaxis=dict(title="revenue", gridcolor="#1A2230"))
            container_chart = st.plotly_chart(fig, width="stretch")
        st.progress(st.session_state.step / NWEEKS,
                    text=f"week {st.session_state.step} / {NWEEKS}")


window = st.empty()

# --- animation loop -----------------------------------------------------------
if play_clicked:
    st.session_state.playing = True
if st.session_state.playing:
    while st.session_state.step < NWEEKS:
        run_next()
        render_window(window)
        time.sleep(speed)
    st.session_state.playing = False
    st.rerun()
else:
    render_window(window)

# --- detail sections (current state) -----------------------------------------
st.divider()
expl = [e for e in agent.ledger.fetch("kpi.explained")
        if e.payload.get("id") == "total_amount"]
ins = [e for e in agent.ledger.fetch("insight.generated")
       if e.payload.get("id") == "total_amount"]
if expl and ins:
    st.markdown("### Why the last move happened (attributed, not guessed)")
    ex, inp = expl[-1].payload, ins[-1].payload
    drivers = ex["drivers"]
    labels = ["baseline"] + [str(d["value"]) for d in drivers] + ["new total"]
    vals = [inp["baseline"]] + [d["delta"] for d in drivers] + [inp["new"]]
    wf = go.Figure(go.Waterfall(
        x=labels, y=vals, measure=["absolute"] + ["relative"] * len(drivers) + ["total"],
        text=[f"{v:+,.0f}" for v in vals], textposition="outside",
        connector={"line": {"color": "#26303D"}},
        increasing={"marker": {"color": "#F5A623"}},
        decreasing={"marker": {"color": "#4DA3FF"}},
        totals={"marker": {"color": "#5A6B7B"}}))
    wf.update_layout(height=300, paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14",
                     font_color="#E6EDF3", showlegend=False, margin=dict(t=20),
                     yaxis=dict(gridcolor="#1A2230"))
    st.plotly_chart(wf, width="stretch")
    st.caption(f"Σ drivers = {ex['total_change']:+,.0f} = "
               f"({inp['new']:,.0f} − {inp['baseline']:,.0f}). Attribution is exact.")
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

# --- prove it / break it ------------------------------------------------------
if agent.ledger.fetch("kpi.computed"):
    st.divider()
    st.markdown("### Prove it, then break it")
    d1, d2 = st.columns(2)
    d1.button("🔨 Tamper with the record", on_click=tamper, width="stretch",
              disabled=st.session_state.tampered)
    d2.button("↺ Restore", on_click=reset, width="stretch")
    ok, broken = agent.verify()
    if not ok:
        st.markdown('<div class="drift">One value was changed — the chain caught it '
                    f'at entry {broken}. You can’t quietly rewrite the past.</div>',
                    unsafe_allow_html=True)
    entries = agent.ledger.fetch()
    html = []
    for idx, e in enumerate(entries[:14]):
        bad = (broken is not None and idx >= broken)
        html.append(f'<div class="chain {"bad" if bad else ""}">seq {e.seq:>2} · '
                    f'{e.kind} · hash {e.hash.hex()[:12]} ← prev '
                    f'{e.prev_hash.hex()[:12]} {"✗" if bad else "✓"}</div>')
    st.markdown("".join(html), unsafe_allow_html=True)
    if len(entries) > 14:
        st.caption(f"… {len(entries) - 14} more entries (chain continues)")

with st.expander("The ledger (every event, hash-chained)"):
    trace = [{"seq": e.seq, "ts": e.ts.isoformat()[:19], "kind": e.kind,
              "hash": e.hash.hex()[:12], "payload": str(e.payload)[:80]}
             for e in agent.ledger.fetch()]
    st.dataframe(pd.DataFrame(trace), hide_index=True, width="stretch")
