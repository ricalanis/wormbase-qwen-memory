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
from datetime import datetime
from typing import Any

import pandas as pd

from . import analysis, executor, narrative, profiler, recall
from .ledger import Ledger
from .planner import Planner
from .triage import Triage

DRIFT_REL_THRESHOLD = 0.15  # >15% relative move flags drift


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
    verified: bool = True


class DataOpsMemoryAgent:
    def __init__(self, ledger: Ledger | None = None, planner: Planner | None = None,
                 triage: Triage | None = None):
        self.ledger = ledger or Ledger()
        self.planner = planner or Planner()
        self.triage = triage or Triage()

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

        # --- recall + triage: reuse a prior plan or escalate to author one ---
        candidate = recall.best_candidate(self.ledger, prof)
        decision = self.triage.decide(prof, candidate)
        self.ledger.append(
            "triage.decided",
            {"decision": "reuse" if decision.reuse else "escalate",
             "similarity": round(decision.similarity, 4),
             "backend": decision.backend, "tokens": decision.tokens,
             "reason": decision.reason, "dataset": dataset},
            ts=ts,
        )
        if decision.reuse and candidate is not None:
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
                 "backend": backend, "cost_units": cost, "dataset": dataset},
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
            baseline = base_entry["value"] if base_entry else None
            is_drift = False
            if baseline is not None and baseline != 0:
                rel = abs(res["value"] - baseline) / abs(baseline)
                if rel > DRIFT_REL_THRESHOLD:
                    is_drift = True
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
                            res["id"], baseline, res["value"], expl)
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
