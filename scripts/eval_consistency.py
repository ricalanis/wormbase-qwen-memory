#!/usr/bin/env python3
"""Run the cross-session consistency harness and print + save the report.

    uv run python scripts/eval_consistency.py
"""
from __future__ import annotations

import json
import pathlib

from wormbase_memory.eval.consistency import evaluate


def main() -> None:
    r = evaluate(n_sessions=6, drift_at=(4,), k=5)
    print("WormBase Qwen Memory — cross-session consistency eval")
    print("=" * 70)
    print(f"{'session':10s} {'reused':>7s} {'cost':>5s} {'total':>8s} "
          f"{'flagged':>8s} {'is_drift':>9s}")
    for row in r["rows"]:
        print(f"{row['session']:10s} {str(row['reused']):>7s} {row['cost']:>5d} "
              f"{str(row['total_amount']):>8s} {str(row['drift_flagged']):>8s} "
              f"{str(row['is_drift']):>9s}")
    print("-" * 70)
    print(f"reproducibility_rate    : {r['reproducibility_rate']:.0%}")
    print(f"plan_reuse_rate         : {r['plan_reuse_rate']:.0%}")
    print(f"planner_cost_reduction  : {r['planner_cost_reduction']:.0%}  "
          f"({r['planner_cost_units_actual']} vs {r['planner_cost_units_would_be']} units)")
    print(f"drift  P/R/F1           : {r['drift']['precision']:.2f} / "
          f"{r['drift']['recall']:.2f} / {r['drift']['f1']:.2f}")
    print(f"run-to-run stability    : {'IDENTICAL ✓' if r['stability']['all_identical'] else 'VARIES ✗'} "
          f"({r['stability']['runs']} runs)")
    print(f"hash-chain              : {'GREEN ✓' if r['hash_chain_ok'] else 'BROKEN ✗'}")

    out = pathlib.Path("results")
    out.mkdir(exist_ok=True)
    (out / "consistency.json").write_text(json.dumps(r, indent=2))
    print(f"\nsaved -> results/consistency.json")


if __name__ == "__main__":
    main()
