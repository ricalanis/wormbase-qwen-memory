"""The Data-Operations MemoryAgent loop.

ingest = profile -> recall (reuse-or-author) -> PEVR execute -> compute KPIs
         -> drift-check -> append to ledger.

Every decision is an append-only ledger entry, so the whole session history is
replayable and verifiable. KPI values carry a ``value_hash`` so reproducibility
is checkable; drift is *flagged*, never silently applied.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from . import analysis, executor, narrative, preferences, profiler, recall, reuse_guard
from .ledger import Ledger
from .planner import Planner
from .triage import Triage

DRIFT_REL_THRESHOLD = 0.15  # >15% relative move flags drift (default; pref can override)
STALENESS_DAYS = 30          # plans older than this are auto-deprecated on recall


@dataclass
class SessionReport:
    dataset: str
    reused: bool
    plan_backend: str
    planner_cost_units: int
    rows_in: int
    rows_out: int
    triage_backend: str = "none"
    triage_tokens: int = 0
    kpis: dict[str, float] = field(default_factory=dict)
    drift: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    reuse_rejected: bool = False
    verified: bool = True


class DataOpsMemoryAgent:
    def __init__(self, ledger: Ledger | None = None, planner: Planner | None = None,
                 triage: Triage | None = None, staleness_days: int = STALENESS_DAYS):
        self.ledger = ledger or Ledger()
        self.planner = planner or Planner()
        self.triage = triage or Triage()
        self.staleness_days = staleness_days

    # -- memory governance ---------------------------------------------------

    def set_preference(self, key: str, value: Any, ts: datetime | None = None) -> None:
        """Remember a user preference (supersede-on-conflict, auditable)."""
        prev = preferences.current(self.ledger).get(key)
        if prev is not None and prev != value:
            self.ledger.append("pref.superseded",
                               {"key": key, "old_value": prev, "new_value": value},
                               ts=ts)
        self.ledger.append("pref.set", {"key": key, "value": value}, ts=ts)

    def deprecate_plan(self, plan_id: str, reason: str,
                       superseded_by: str | None = None,
                       ts: datetime | None = None) -> None:
        """Tombstone a plan — excluded from recall, but still in history (replayable)."""
        self.ledger.append("plan.deprecated",
                           {"plan_id": plan_id, "reason": reason,
                            "superseded_by": superseded_by}, ts=ts)

    def _last_kpi_entry(self, kpi_id: str) -> dict | None:
        """Most recent computed entry for a KPI (flagged or not)."""
        entry = None
        for e in self.ledger.fetch("kpi.computed"):
            if e.payload.get("id") == kpi_id:
                entry = e.payload
        return entry

    def _baseline_kpi_entry(self, kpi_id: str) -> dict | None:
        """Last accepted-normal computed entry for a KPI — ignores prior
        drift-flagged readings so a one-off anomaly never becomes the new
        reference. Carries the breakdown used to explain the next move."""
        entry = None
        for e in self.ledger.fetch("kpi.computed"):
            if e.payload.get("id") == kpi_id and not e.payload.get("drift"):
                entry = e.payload
        return entry

    def ingest(
        self, df: pd.DataFrame, dataset: str, ts: datetime | None = None
    ) -> SessionReport:
        prof = profiler.profile(df)
        eff_ts = ts or datetime.now(UTC)
        prefs = preferences.current(self.ledger)
        drift_threshold = float(prefs.get("drift_threshold", DRIFT_REL_THRESHOLD))

        # --- recall + triage: reuse a prior plan or escalate to author one ---
        candidate = recall.best_candidate(self.ledger, prof)
        # decay: a stale plan is tombstoned and re-authored (timely forgetting)
        if candidate is not None and candidate.created:
            age_days = (eff_ts - datetime.fromisoformat(candidate.created)).days
            if age_days > self.staleness_days:
                self.deprecate_plan(candidate.plan_id,
                                    reason=f"stale ({age_days}d > {self.staleness_days}d)",
                                    ts=ts)
                candidate = None  # force re-author
        decision = self.triage.decide(prof, candidate,
                                      reuse_threshold=prefs.get("reuse_threshold"))

        # verifier-gate: only reuse a plan that still verifiably works on this data
        do_reuse = decision.reuse and candidate is not None
        reuse_rejected = False
        if do_reuse:
            ok, why = reuse_guard.check(df, candidate.ops)
            if not ok:
                do_reuse = False
                reuse_rejected = True
                self.ledger.append(
                    "plan.reuse_rejected",
                    {"plan_id": candidate.plan_id, "reason": why, "dataset": dataset},
                    ts=ts)
                # the plan is stale for this data -> tombstone it (timely forgetting)
                self.deprecate_plan(candidate.plan_id,
                                    reason=f"reuse verification failed: {why}", ts=ts)

        self.ledger.append(
            "triage.decided",
            {"decision": "reuse" if decision.reuse else "escalate",
             "similarity": round(decision.similarity, 4),
             "backend": decision.backend, "tokens": decision.tokens,
             "reason": decision.reason, "gate": "rejected" if reuse_rejected else "ok",
             "dataset": dataset},
            ts=ts,
        )
        if do_reuse:
            ops = candidate.ops
            backend, cost = "reused", 0
            self.ledger.append(
                "plan.reused",
                {"plan_id": candidate.plan_id,
                 "similarity": round(decision.similarity, 4),
                 "triage_backend": decision.backend,
                 "fingerprint": prof["fingerprint"], "dataset": dataset},
                ts=ts,
            )
            reused = True
        else:
            authored = self.planner.author(prof)
            ops = authored["ops"]
            backend, cost = authored["backend"], authored["cost_units"]
            plan_id = str(uuid.uuid4())
            self.ledger.append(
                "plan.authored",
                {"plan_id": plan_id, "fingerprint": prof["fingerprint"],
                 "column_names": prof["column_names"], "ops": ops,
                 "backend": backend, "cost_units": cost,
                 "created": eff_ts.isoformat(), "dataset": dataset},
                ts=ts,
            )
            reused = False

        # --- PEVR execute the transforms ------------------------------------
        cleaned, ok = self.ledger.write_pevr(
            "clean",
            propose={"dataset": dataset, "n_ops": len(ops)},
            execute_fn=lambda: int(len(executor.apply_transforms(df, ops))),
            verify_fn=lambda rows_out: rows_out > 0,
            ts=ts,
        )
        cleaned_df = executor.apply_transforms(df, ops)

        report = SessionReport(
            dataset=dataset, reused=reused, plan_backend=backend,
            planner_cost_units=cost, rows_in=len(df), rows_out=len(cleaned_df),
            triage_backend=decision.backend, triage_tokens=decision.tokens,
            reuse_rejected=reuse_rejected,
        )

        # --- compute KPIs -> on drift, EXPLAIN the move + narrate -----------
        cat_dims = [c for c, m in prof["columns"].items() if m.get("is_categorical")]
        for kdef in executor.kpi_defs(ops):
            res = executor.compute_kpi(cleaned_df, kdef)
            breakdown = executor.kpi_breakdown(cleaned_df, kdef, cat_dims)
            self.ledger.append("kpi.defined",
                               {"id": kdef["id"], "agg": kdef["agg"],
                                "column": kdef["column"]}, ts=ts)
            base_entry = self._baseline_kpi_entry(res["id"])
            prev_entry = self._last_kpi_entry(res["id"])
            baseline = base_entry["value"] if base_entry else None
            is_drift = False
            if baseline is not None and baseline != 0:
                rel = abs(res["value"] - baseline) / abs(baseline)
                if rel > drift_threshold:
                    # A *sustained* shift becomes the new normal: if the previous
                    # reading already drifted the same way and we've stabilized
                    # near it, accept it (re-baseline) rather than flag forever.
                    # A one-off spike doesn't stabilize, so it still anchors to the
                    # last accepted value.
                    confirmed_shift = False
                    if prev_entry and prev_entry.get("drift") and prev_entry["value"]:
                        same_dir = ((res["value"] - baseline)
                                    * (prev_entry["value"] - baseline) > 0)
                        stabilized = (abs(res["value"] - prev_entry["value"])
                                      / abs(prev_entry["value"]) <= drift_threshold)
                        confirmed_shift = same_dir and stabilized
                    is_drift = not confirmed_shift
                if is_drift:
                    self.ledger.append(
                        "kpi.drift_flagged",
                        {"id": res["id"], "baseline": baseline, "new": res["value"],
                         "rel_change": round(rel, 4), "dataset": dataset},
                        ts=ts,
                    )
                    report.drift.append(res["id"])
                    expl = analysis.explain_change(
                        base_entry.get("breakdown", {}), breakdown)
                    if expl:
                        narr = narrative.render_change_narrative(
                            res["id"], baseline, res["value"], expl,
                            style=prefs.get("narrative_style", "verbose"))
                        self.ledger.append(
                            "kpi.explained",
                            {"id": res["id"], "dim": expl["dim"],
                             "drivers": expl["drivers"][:5],
                             "total_change": expl["total_change"],
                             "dataset": dataset}, ts=ts)
                        self.ledger.append(
                            "insight.generated",
                            {"id": res["id"], "narrative": narr, "dim": expl["dim"],
                             "baseline": baseline, "new": res["value"],
                             "dataset": dataset}, ts=ts)
                        report.explanations.append(narr)
            self.ledger.append("kpi.computed",
                               {**res, "drift": is_drift, "baseline": baseline,
                                "breakdown": breakdown, "dataset": dataset}, ts=ts)
            report.kpis[res["id"]] = res["value"]

        report.verified = self.ledger.verify()[0]
        return report

    # -- projections ---------------------------------------------------------

    def kpi_history(self, kpi_id: str) -> list[dict[str, Any]]:
        return [
            {"ts": e.ts.isoformat(), **e.payload}
            for e in self.ledger.fetch("kpi.computed")
            if e.payload.get("id") == kpi_id
        ]

    def answer(self, kpi_id: str) -> dict[str, Any]:
        """Receipts-backed answer: prose + the exact ledger entries it cites.

        The prose is refused (``grounded=False``) unless every data number in it
        appears in a cited entry — a deterministic chain-of-custody check, not an
        LLM judge. This is 'memory you can verify' made queryable.
        """
        computed = [e for e in self.ledger.fetch("kpi.computed")
                    if e.payload.get("id") == kpi_id]
        if not computed:
            return {"prose": f"No memory of KPI '{kpi_id}'.",
                    "receipts": [], "grounded": True}
        last = computed[-1]

        def _receipt(e: Any, value: Any) -> dict[str, Any]:
            return {"seq": e.seq, "kind": e.kind,
                    "hash": e.hash.hex()[:16], "value": value}

        receipts = [_receipt(last, last.payload["value"])]
        insights = [e for e in self.ledger.fetch("insight.generated")
                    if e.payload.get("id") == kpi_id]
        if insights:
            ins = insights[-1]
            prose = ins.payload["narrative"]
            nums = [last.payload["value"], ins.payload["baseline"], ins.payload["new"]]
            receipts.append(_receipt(ins, ins.payload["new"]))
            expl = [e for e in self.ledger.fetch("kpi.explained")
                    if e.payload.get("id") == kpi_id]
            if expl:
                ex = expl[-1]
                receipts.append(_receipt(ex, ex.payload["total_change"]))
                nums += [d["delta"] for d in ex.payload["drivers"]]
                nums.append(ex.payload["total_change"])
            allowed = narrative.allowed_numbers(*nums)
        else:
            prose = f"{kpi_id} is currently {narrative._g(last.payload['value'])}."
            allowed = narrative.allowed_numbers(last.payload["value"])

        return {"prose": prose, "receipts": receipts,
                "grounded": narrative.is_grounded(prose, allowed)}

    def reproducibility_rate(self) -> float:
        """Fraction of (id, input_hash) pairs whose value_hash is consistent."""
        seen: dict[tuple, str] = {}
        total = consistent = 0
        for e in self.ledger.fetch("kpi.computed"):
            p = e.payload
            key = (p.get("id"), p.get("input_hash"))
            total += 1
            if key in seen:
                consistent += int(seen[key] == p.get("value_hash"))
            else:
                seen[key] = p.get("value_hash")
                consistent += 1
        return consistent / total if total else 1.0

    def verify(self) -> tuple[bool, int | None]:
        return self.ledger.verify()
