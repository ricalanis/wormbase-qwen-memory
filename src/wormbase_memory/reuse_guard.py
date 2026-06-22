"""Deterministic verifier-gate on plan reuse.

Before a stored plan is reused, check it still *works* on the current data — a
cheap, LLM-free rule check. The decisive failure mode for any plan-reuse memory
agent is replaying a stale plan under drift (e.g. a canonicalization mapping that
no longer covers new value-variants), silently producing a wrong KPI. This gate
catches that and forces a re-author instead. (Loop-engineering backlog #2; RLVR
discipline: only reuse what verifiably still passes.)
"""

from __future__ import annotations

import pandas as pd

from . import executor

CATEGORICAL_MAX_UNIQUE = 50  # match profiler: only guard low-cardinality text cols


def _referenced_columns(ops: list[dict]) -> set[str]:
    cols: set[str] = set()
    for op in ops:
        if "column" in op:
            cols.add(op["column"])
        for c in op.get("columns", []):
            cols.add(c)
    return cols


def check(df: pd.DataFrame, ops: list[dict]) -> tuple[bool, str]:
    """Return (ok, reason). ok=True means the plan is safe to reuse on ``df``."""
    missing = [c for c in _referenced_columns(ops) if c not in df.columns]
    if missing:
        return False, f"plan references missing columns {sorted(missing)}"

    try:
        cleaned = executor.apply_transforms(df, ops)
    except Exception as e:  # malformed/incompatible op for this data
        return False, f"executor error: {type(e).__name__}"
    if len(cleaned) == 0:
        return False, "cleaning emptied the table"

    # residual unmerged case/whitespace variants = stale canonicalization coverage
    for col in cleaned.columns:
        s = cleaned[col]
        if pd.api.types.is_numeric_dtype(s):
            continue
        vals = list(s.dropna().unique())
        if len(vals) > CATEGORICAL_MAX_UNIQUE:
            continue  # free-text column, not a categorical to canonicalize
        norm: dict[str, set[str]] = {}
        for v in vals:
            k = executor._collapse_ws(str(v)).lower()
            norm.setdefault(k, set()).add(str(v))
        collided = next((g for g in norm.values() if len(g) > 1), None)
        if collided:
            return False, f"residual unmerged variants in '{col}': {sorted(collided)}"

    # KPI measure columns must still be computable
    for kdef in executor.kpi_defs(ops):
        col, agg = kdef.get("column"), kdef.get("agg")
        if col in cleaned and agg in ("sum", "mean", "min", "max"):
            if pd.to_numeric(cleaned[col], errors="coerce").notna().sum() == 0:
                return False, f"KPI '{kdef.get('id')}' column '{col}' is not numeric"

    return True, "ok"
