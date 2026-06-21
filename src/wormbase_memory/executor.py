"""Deterministic local executor over a closed operation vocabulary.

The planner (Qwen or rules) only ever emits ops from ``TRANSFORM_VOCAB`` /
``KPI_VOCAB``. A closed vocabulary executed by deterministic pandas is what makes
a plan a *replayable artifact*: the same (data, plan) always yields the same
cleaned table and the same KPI value — byte-for-byte.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .hashchain import content_hash

TRANSFORM_VOCAB = {
    "strip_whitespace",  # {columns: [..]}  trim + collapse internal whitespace
    "lowercase",         # {column}
    "titlecase",         # {column}
    "canonicalize",      # {column, mapping: {variant: canonical}}
    "fillna",            # {column, value}
    "drop_null_rows",    # {columns: [..]}
    "dedup",             # {subset: [..] | null}
    "filter",            # {column, op: ==|!=|>|>=|<|<=, value}
}
KPI_VOCAB = {"define_kpi"}  # {id, agg, column, filter?}
AGGS = {"sum", "mean", "count", "nunique", "min", "max"}


class PlanError(ValueError):
    """A plan op is malformed or outside the closed vocabulary."""


def _collapse_ws(x: Any) -> Any:
    if isinstance(x, str):
        return re.sub(r"\s+", " ", x).strip()
    return x


def _apply_one(df: pd.DataFrame, op: dict[str, Any]) -> pd.DataFrame:
    kind = op.get("op")
    if kind == "strip_whitespace":
        for c in op["columns"]:
            if c in df:
                df[c] = df[c].map(_collapse_ws)
    elif kind == "lowercase":
        c = op["column"]
        if c in df:
            df[c] = df[c].map(lambda v: v.lower() if isinstance(v, str) else v)
    elif kind == "titlecase":
        c = op["column"]
        if c in df:
            df[c] = df[c].map(lambda v: v.title() if isinstance(v, str) else v)
    elif kind == "canonicalize":
        c, mapping = op["column"], op["mapping"]
        if c in df:
            # case-insensitive, whitespace-insensitive key matching
            norm = {_collapse_ws(str(k)).lower(): v for k, v in mapping.items()}
            df[c] = df[c].map(
                lambda v: norm.get(_collapse_ws(str(v)).lower(), v)
                if isinstance(v, str)
                else v
            )
    elif kind == "fillna":
        c = op["column"]
        if c in df:
            df[c] = df[c].fillna(op["value"])
    elif kind == "drop_null_rows":
        cols = [c for c in op["columns"] if c in df]
        if cols:
            df = df.dropna(subset=cols)
    elif kind == "dedup":
        subset = op.get("subset")
        df = df.drop_duplicates(subset=subset, keep="first")
    elif kind == "filter":
        c, o, val = op["column"], op["op"], op["value"]
        if c in df:
            ops = {
                "==": df[c] == val, "!=": df[c] != val,
                ">": df[c] > val, ">=": df[c] >= val,
                "<": df[c] < val, "<=": df[c] <= val,
            }
            if o not in ops:
                raise PlanError(f"bad filter op: {o}")
            df = df[ops[o]]
    else:
        raise PlanError(f"unknown transform op: {kind!r}")
    return df


def validate_plan(ops: list[dict[str, Any]]) -> None:
    for op in ops:
        kind = op.get("op")
        if kind not in TRANSFORM_VOCAB and kind not in KPI_VOCAB:
            raise PlanError(f"op {kind!r} not in closed vocabulary")
        if kind == "define_kpi" and op.get("agg") not in AGGS:
            raise PlanError(f"define_kpi agg must be one of {AGGS}")


def apply_transforms(df: pd.DataFrame, ops: list[dict[str, Any]]) -> pd.DataFrame:
    """Apply every transform op in order; ignore KPI-definition ops."""
    out = df.copy()
    for op in ops:
        if op.get("op") in TRANSFORM_VOCAB:
            out = _apply_one(out, op)
    return out.reset_index(drop=True)


def kpi_defs(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [op for op in ops if op.get("op") == "define_kpi"]


def input_hash(df: pd.DataFrame) -> str:
    """Order-independent content identity of a dataframe (the KPI's input)."""
    rows = ["\t".join(map(str, r)) for r in df.itertuples(index=False, name=None)]
    return content_hash({"columns": list(map(str, df.columns)), "rows": sorted(rows)})


def kpi_breakdown(
    df: pd.DataFrame, kpi: dict[str, Any], dim_cols: list[str]
) -> dict[str, dict[str, float]]:
    """Per-dimension breakdown of an additive KPI, stored alongside its value.

    For additive aggregations (sum/count/nunique) each dimension partitions the
    metric, so diffing two sessions' breakdowns explains a KPI change exactly
    (contributions sum to ΔKPI). Computed from the ledger-resident table — no raw
    data needs to be retained to later explain a move.
    """
    col, agg = kpi["column"], kpi["agg"]
    out: dict[str, dict[str, float]] = {}
    for d in dim_cols:
        if d not in df or d == col:
            continue
        if agg == "sum":
            g = df.groupby(d)[col].apply(
                lambda s: float(pd.to_numeric(s, errors="coerce").sum()))
        elif agg == "count":
            g = df.groupby(d)[col].size().astype(float)
        elif agg == "nunique":
            g = df.groupby(d)[col].nunique().astype(float)
        else:
            continue  # mean/min/max are not additively decomposable
        out[str(d)] = {str(k): float(v) for k, v in g.items()}
    return out


def compute_kpi(df: pd.DataFrame, kpi: dict[str, Any]) -> dict[str, Any]:
    """Compute a single KPI deterministically. Returns value + reproducibility hashes."""
    work = df
    if kpi.get("filter"):
        work = _apply_one(df.copy(), {"op": "filter", **kpi["filter"]})
    col = kpi["column"]
    agg = kpi["agg"]
    series = work[col] if col in work else work.iloc[:, 0]
    if agg == "sum":
        value = float(pd.to_numeric(series, errors="coerce").sum())
    elif agg == "mean":
        value = float(pd.to_numeric(series, errors="coerce").mean())
    elif agg == "min":
        value = float(pd.to_numeric(series, errors="coerce").min())
    elif agg == "max":
        value = float(pd.to_numeric(series, errors="coerce").max())
    elif agg == "count":
        value = int(series.count())
    elif agg == "nunique":
        value = int(series.nunique(dropna=True))
    else:
        raise PlanError(f"bad agg {agg!r}")
    ih = input_hash(work)
    vh = content_hash(
        {"id": kpi["id"], "agg": agg, "column": col, "value": value, "input_hash": ih}
    )
    return {"id": kpi["id"], "value": value, "input_hash": ih, "value_hash": vh}
