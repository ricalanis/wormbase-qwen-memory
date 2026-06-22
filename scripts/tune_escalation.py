#!/usr/bin/env python3
"""Tune the cascade's escalation (reuse) threshold for success@cost.  (backlog #5)

    uv run python scripts/tune_escalation.py
"""
from __future__ import annotations

from wormbase_memory.eval.escalation import sweep


def main() -> None:
    s = sweep()
    print("Escalation-threshold sweep (gray-zone schema-drift dataset)")
    print("=" * 64)
    print(f"{'threshold':>9} {'tokens':>7} {'escal_rate':>11} {'rejects':>8} "
          f"{'chain':>6} {'repro':>6}")
    for r in s["rows"]:
        print(f"{r['threshold']:>9.2f} {r['tokens']:>7d} {r['escalation_rate']:>11.2f} "
              f"{r['reuse_rejected']:>8d} {str(r['chain_ok']):>6} {r['reproducibility']:>6.0%}")
    print("-" * 64)
    print(f"recommended threshold: {s['recommended']}  (min tokens: {s['min_tokens']})")
    print("Lower is safe because the verifier-gate rejects any stale reuse.")


if __name__ == "__main__":
    main()
