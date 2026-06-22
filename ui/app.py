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

from wormbase_memory import profiler
from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.inference import resolve_planner_client
from wormbase_memory.planner import _estimate_cost_units
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
    st.session_state.telemetry = []   # per-week tokens + plan provenance
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
        would_be = _estimate_cost_units(profiler.profile(wk["df"]))  # cost if no memory
        rep = agent.ingest(wk["df"], wk["name"], ts=wk["ts"])
        st.session_state.reports.append((wk, rep))
        st.session_state.telemetry.append({
            "week": wk["week"], "actual": rep.planner_cost_units,
            "would_be": would_be, "reused": rep.reused, "backend": rep.plan_backend,
        })
        st.session_state.step += 1


def reset() -> None:
    for k in ("agent", "reports", "telemetry", "step", "tampered", "playing"):
        st.session_state.pop(k, None)


_OP_LABEL = {"strip_whitespace": "strip whitespace", "drop_null_rows": "drop null rows",
             "dedup": "dedup rows", "canonicalize": "canonicalize",
             "lowercase": "lowercase", "titlecase": "titlecase", "fillna": "fill nulls"}


def _fmt_op(op: dict) -> str:
    k = op.get("op")
    if k == "define_kpi":
        return f"KPI {op['id']} = {op['agg'].upper()}({op['column']})"
    if k == "dedup":
        return "dedup rows"
    if "columns" in op:
        return f"{_OP_LABEL.get(k, k)}({', '.join(op['columns'])})"
    if "column" in op:
        return f"{_OP_LABEL.get(k, k)}({op['column']})"
    return k


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
speed = co4.slider("seconds per week", 0.5, 5.0, 2.0, 0.5,
                   help="drift weeks linger a bit longer so you can read the explanation")


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

        # --- use-case card: the QUESTION, the QUERY, the OUTPUT METRIC -------
        if reports:
            wk, rep = reports[-1]
            rev = rep.kpis.get("total_amount")
            prev = hist[-2]["value"] if len(hist) >= 2 else None
            wow = (rev - prev) / prev if prev else None
            authored = agent.ledger.fetch("plan.authored")
            active = authored[-1].payload if authored else {"ops": [], "dataset": "—"}
            kpis = [o for o in active["ops"] if o.get("op") == "define_kpi"]
            main = next((k for k in kpis if k["id"] == "total_amount"),
                        kpis[0] if kpis else None)
            metric_q = (f"{main['id']} = {main['agg'].upper()}({main['column']})"
                        if main else "—")
            cleaning = [_fmt_op(o) for o in active["ops"] if o.get("op") != "define_kpi"]
            prov = ("🧠 authored this week · " + rep.plan_backend) if not rep.reused \
                else f"♻️ reused from {active['dataset']} · 0 tokens"

            qcol, acol = st.columns([3, 2])
            with qcol:
                st.markdown(f"🗣️ **{wk['asker']} asks:** *“{wk['question']}”*")
                st.markdown(f"**Resolves to the same governed query** &nbsp;"
                            f"<span style='color:#8B98A9'>· {prov}</span>",
                            unsafe_allow_html=True)
                st.code(f"{metric_q}\n  over orders cleaned by: "
                        + " · ".join(cleaning[:3]) + (" · …" if len(cleaning) > 3 else ""),
                        language=None)
                st.caption("Different people, different words — **one** governed query, "
                           "so the number stays comparable week over week.")
            with acol:
                st.metric("➜ OUTPUT METRIC · weekly revenue", _money(rev),
                          delta=(f"{wow:+.0%} vs last week" if wow is not None else None))
                if rep.explanations:
                    st.markdown(f'<div class="drift">⚠ {rep.explanations[0]}</div>',
                                unsafe_allow_html=True)
                elif wk["event"]:
                    st.markdown(f'<div class="event">{wk["event"]}</div>',
                                unsafe_allow_html=True)
        else:
            st.info("Press **▶ Play simulation** (or **⏭ Step a week**) to begin.")

        # two evolving charts: revenue (left) + token usage (right)
        gleft, gright = st.columns(2)
        if hist:
            xs = list(range(1, len(hist) + 1))
            ys = [h["value"] for h in hist]
            colors = ["#F5A623" if h.get("drift") else "#4DA3FF" for h in hist]
            sizes = [16 if h.get("drift") else 8 for h in hist]
            rev = go.Figure(go.Scatter(
                x=xs, y=ys, mode="lines+markers", line=dict(color="#4DA3FF", width=3),
                marker=dict(color=colors, size=sizes, line=dict(color="#0B0F14", width=1))))
            rev.update_layout(height=280, paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14",
                              font_color="#E6EDF3", margin=dict(t=28, b=10), title="revenue",
                              xaxis=dict(title="week", gridcolor="#1A2230",
                                         range=[0.5, NWEEKS + 0.5]),
                              yaxis=dict(gridcolor="#1A2230"))
            gleft.plotly_chart(rev, width="stretch")

        tel = st.session_state.telemetry
        if tel:
            wks = [t["week"] for t in tel]
            cum_actual, cum_naive, a, n = [], [], 0, 0
            for t in tel:
                a += t["actual"]; n += t["would_be"]
                cum_actual.append(a); cum_naive.append(n)
            tok = go.Figure()
            tok.add_trace(go.Scatter(x=wks, y=cum_naive, mode="lines", name="without memory",
                                     line=dict(color="#FF4D4F", width=2, dash="dash")))
            tok.add_trace(go.Scatter(x=wks, y=cum_actual, mode="lines+markers",
                                     name="with memory", line=dict(color="#2ED47A", width=3),
                                     fill="tozeroy", fillcolor="rgba(46,212,122,0.12)"))
            tok.update_layout(height=280, paper_bgcolor="#0B0F14", plot_bgcolor="#0B0F14",
                              font_color="#E6EDF3", margin=dict(t=28, b=10),
                              title="planner tokens (cumulative)",
                              legend=dict(orientation="h", y=1.15, font=dict(size=11)),
                              xaxis=dict(title="week", gridcolor="#1A2230",
                                         range=[0.5, NWEEKS + 0.5]),
                              yaxis=dict(gridcolor="#1A2230"))
            gright.plotly_chart(tok, width="stretch")
            saved = cum_naive[-1] - cum_actual[-1]
            pct = saved / cum_naive[-1] if cum_naive[-1] else 0
            gright.caption(f"**{cum_actual[-1]:,} tokens** used vs **{cum_naive[-1]:,}** "
                           f"if it re-planned every week — **{pct:.0%} saved** by reuse.")

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
        # linger longer on drift weeks so the answer + explanation can be read
        last_rep = st.session_state.reports[-1][1]
        time.sleep(speed + 2.5 if last_rep.drift else speed)
    st.session_state.playing = False
    st.rerun()
else:
    render_window(window)

# --- why this matters: data governance & consistency over time ----------------
st.divider()
with st.container(border=True):
    st.markdown("### 🏛️ Why this matters — data governance & consistency over time")
    st.markdown(
        "Notice the question changes every week — different people, different "
        "wording — but the agent answers from **one governed query**, not a fresh "
        "ad-hoc interpretation. That is the whole point:\n\n"
        "- **One governed definition of the metric.** *Revenue* = `SUM(amount)` over "
        "canonicalized, de-duplicated orders — defined once, stored in the ledger, "
        "and reused. No analyst silently re-derives it a little differently each week.\n"
        "- **Phrasing-independent → comparable over time.** However it's asked, it "
        "maps to the same query, so week-over-week numbers are truly comparable "
        "(no semantic drift from who happened to run the report).\n"
        "- **Reproducible & auditable.** Same inputs → identical `value_hash`, "
        "byte-for-byte; every figure traces to a ledger receipt; replay the state "
        "as of any past week.\n"
        "- **Tamper-evident.** The hash chain catches any silent edit to history — "
        "you can take the number to a board meeting and prove it wasn't changed.\n"
        "- **Real change is surfaced, not hidden.** Genuine moves are flagged and "
        "attributed (whale, churn); noise and rephrasing never move the number.\n\n"
        "_The governance payoff: a single, versioned, auditable source of metric "
        "truth — so analysis stays consistent and defensible over time._")

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
