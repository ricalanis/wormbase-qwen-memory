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

from . import executor, profiler, recall
from .ledger import Ledger
from .planner import Planner

DRIFT_REL_THRESHOLD = 0.15  # >15% relative move flags drift


@dataclass
class SessionReport:
    dataset: str
    reused: bool
    plan_backend: str
    planner_cost_units: int
    rows_in: int
    rows_out: int
    kpis: dict[str, float] = field(default_factory=dict)
    drift: list[str] = field(default_factory=list)
    verified: bool = True


class DataOpsMemoryAgent:
    def __init__(self, ledger: Ledger | None = None, planner: Planner | None = None):
        self.ledger = ledger or Ledger()
        self.planner = planner or Planner()

    def _last_kpi_value(self, kpi_id: str) -> float | None:
        last = None
        for e in self.ledger.fetch("kpi.computed"):
            if e.payload.get("id") == kpi_id:
                last = e.payload.get("value")
        return last

    def ingest(
        self, df: pd.DataFrame, dataset: str, ts: datetime | None = None
    ) -> SessionReport:
        prof = profiler.profile(df)

        # --- recall: reuse a prior plan or author a new one ------------------
        match = recall.find(self.ledger, prof)
        if match is not None:
            ops = match.ops
            backend, cost = "reused", 0
            self.ledger.append(
                "plan.reused",
                {"plan_id": match.plan_id, "similarity": round(match.similarity, 4),
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
        )

        # --- compute KPIs + drift check -------------------------------------
        for kdef in executor.kpi_defs(ops):
            res = executor.compute_kpi(cleaned_df, kdef)
            self.ledger.append("kpi.defined",
                               {"id": kdef["id"], "agg": kdef["agg"],
                                "column": kdef["column"]}, ts=ts)
            prev = self._last_kpi_value(res["id"])
            if prev is not None and prev != 0:
                rel = abs(res["value"] - prev) / abs(prev)
                if rel > DRIFT_REL_THRESHOLD:
                    self.ledger.append(
                        "kpi.drift_flagged",
                        {"id": res["id"], "prev": prev, "new": res["value"],
                         "rel_change": round(rel, 4), "dataset": dataset},
                        ts=ts,
                    )
                    report.drift.append(res["id"])
            self.ledger.append("kpi.computed",
                               {**res, "dataset": dataset}, ts=ts)
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
