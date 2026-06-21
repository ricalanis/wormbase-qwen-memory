"""Authors a data-operation plan from a profile.

Two paths, identical output shape (a list of closed-vocab ops):
- Qwen-Plus (DashScope) when a key is present — the brain.
- A deterministic rule engine otherwise — so tests/offline demo always work and
  so a reused plan can be compared against a fresh one apples-to-apples.

``planner_cost_units`` is the cost signal the consistency story tracks: real
total tokens when Qwen authored the plan, an estimate from profile size when the
rules engine did. Reuse costs 0 — that is the "cheaper over time" effect.
"""

from __future__ import annotations

import json
from typing import Any

from . import executor
from .inference import QwenCloudClient, loads_lenient, resolve_planner_client

SYSTEM_PROMPT = (
    "You are a data-cleaning planner. Read the column profile and output ONLY a "
    'JSON object: {"ops": [ ... ]}. Each element of "ops" MUST be a JSON OBJECT '
    'with an "op" field — never a string. Allowed ops and their exact fields:\n'
    '  {"op":"strip_whitespace","columns":["..."]}\n'
    '  {"op":"lowercase","column":"..."}\n'
    '  {"op":"titlecase","column":"..."}\n'
    '  {"op":"canonicalize","column":"...","mapping":{"variant":"canonical"}}\n'
    '  {"op":"fillna","column":"...","value":0}\n'
    '  {"op":"drop_null_rows","columns":["..."]}\n'
    '  {"op":"dedup","subset":null}\n'
    '  {"op":"define_kpi","id":"...","agg":"sum","column":"..."}  '
    "(agg in [sum,mean,count,nunique,min,max])\n"
    "Example:\n"
    '{"ops":[{"op":"strip_whitespace","columns":["region"]},'
    '{"op":"canonicalize","column":"region","mapping":{"na":"North America"}},'
    '{"op":"drop_null_rows","columns":["amount"]},{"op":"dedup","subset":null},'
    '{"op":"define_kpi","id":"total_amount","agg":"sum","column":"amount"}]}\n'
    "Do not invent ops. Prefer canonicalize for near-duplicate categorical values. "
    "Output JSON only, no prose."
)

REVENUE_HINTS = ("amount", "revenue", "total", "price", "sales", "value")


def _rule_based_plan(profile: dict[str, Any]) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    cols = profile["columns"]

    text_cols = [c for c, m in cols.items() if not m["is_numeric"]]
    if text_cols:
        ops.append({"op": "strip_whitespace", "columns": sorted(text_cols)})

    # Canonicalize near-duplicate categorical values (case/whitespace variants).
    for c, m in cols.items():
        if m.get("is_categorical") and m.get("values"):
            mapping = _canonical_mapping(m["values"])
            if mapping:
                ops.append({"op": "canonicalize", "column": c, "mapping": mapping})

    # Drop rows fully missing a numeric measure; dedup whole rows.
    measure = _pick_measure(cols)
    if measure:
        ops.append({"op": "drop_null_rows", "columns": [measure]})
    ops.append({"op": "dedup", "subset": None})

    if measure:
        ops.append(
            {"op": "define_kpi", "id": f"total_{measure}", "agg": "sum", "column": measure}
        )
    ops.append({"op": "define_kpi", "id": "row_count", "agg": "count",
                "column": profile["column_names"][0]})
    return ops


def _canonical_mapping(values: dict[str, int]) -> dict[str, str]:
    """Group values by case/whitespace-normalized key; map variants -> canonical."""
    import re

    clusters: dict[str, list[tuple[str, int]]] = {}
    for raw, count in values.items():
        key = re.sub(r"\s+", " ", raw).strip().lower()
        clusters.setdefault(key, []).append((raw, count))
    mapping: dict[str, str] = {}
    for members in clusters.values():
        if len(members) <= 1:
            continue
        canonical = max(members, key=lambda x: x[1])[0]  # most frequent variant
        canonical = re.sub(r"\s+", " ", canonical).strip().title()
        for raw, _ in members:
            mapping[raw] = canonical
    return mapping


def _pick_measure(cols: dict[str, Any]) -> str | None:
    numeric = [c for c, m in cols.items() if m["is_numeric"]]
    for c in numeric:
        if any(h in c.lower() for h in REVENUE_HINTS):
            return c
    return numeric[0] if numeric else None


def _estimate_cost_units(profile: dict[str, Any]) -> int:
    # Rough analog of prompt size: bytes of the profile the brain would read.
    return len(json.dumps(profile)) // 4


class Planner:
    def __init__(self, client: QwenCloudClient | None = None) -> None:
        # cloud (Qwen-Plus) or local (Ollama) — same code, chosen by WBM_PROVIDER
        self.client = client if client is not None else resolve_planner_client()

    def author(self, profile: dict[str, Any]) -> dict[str, Any]:
        if self.client is not None:
            try:
                return self._author_with_client(profile)
            except Exception:
                pass  # fall through to deterministic rules
        ops = _rule_based_plan(profile)
        executor.validate_plan(ops)
        return {"ops": ops, "backend": "rules",
                "cost_units": _estimate_cost_units(profile)}

    def _author_with_client(self, profile: dict[str, Any]) -> dict[str, Any]:
        msg = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Column profile:\n" + json.dumps(profile)},
        ]
        # JSON mode only on DashScope; local Ollama relies on prompt + lenient parse
        rf = ({"type": "json_object"}
              if getattr(self.client, "backend_label", "") == "dashscope" else None)
        res = self.client.chat(msg, temperature=0.0, max_tokens=1024,
                               response_format=rf)
        data = loads_lenient(res.text)
        ops = data.get("ops", data) if isinstance(data, dict) else data
        executor.validate_plan(ops)
        return {"ops": ops, "backend": res.backend, "cost_units": res.tokens}
