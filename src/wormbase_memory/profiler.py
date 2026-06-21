"""Deterministic column profiling -> a compact, hashable data fingerprint.

The profile is what the planner reasons over (never the raw rows), and its
``fingerprint`` is the recall key: "have we seen data shaped like this before?"
Keeping profiling deterministic is what lets recall — and therefore plan reuse —
be reproducible.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .hashchain import content_hash

# columns with this few distinct values are treated as categorical (canonicalizable)
CATEGORICAL_MAX_UNIQUE = 50


def profile(df: pd.DataFrame) -> dict[str, Any]:
    cols: dict[str, Any] = {}
    for name in df.columns:
        s = df[name]
        dtype = str(s.dtype)
        n_null = int(s.isna().sum())
        n_unique = int(s.nunique(dropna=True))
        col: dict[str, Any] = {
            "dtype": dtype,
            "n_null": n_null,
            "n_unique": n_unique,
            "is_numeric": bool(pd.api.types.is_numeric_dtype(s)),
            "is_categorical": bool(
                not pd.api.types.is_numeric_dtype(s)
                and n_unique <= CATEGORICAL_MAX_UNIQUE
            ),
        }
        if col["is_categorical"]:
            vc = s.dropna().astype(str).value_counts()
            col["values"] = {str(k): int(v) for k, v in vc.items()}
        cols[str(name)] = col

    schema = {name: cols[name]["dtype"] for name in cols}
    fingerprint = content_hash({"schema": schema, "columns": sorted(cols)})
    return {
        "n_rows": int(len(df)),
        "columns": cols,
        "column_names": sorted(cols),
        "schema": schema,
        "fingerprint": fingerprint,
    }
