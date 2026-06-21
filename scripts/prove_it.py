#!/usr/bin/env python3
"""The 'prove it, then break it' demo — memory you can verify.

1. Run the same analysis in TWO fresh agents -> identical value_hash (reproducible).
2. Ask a receipts-backed question -> prose + ledger citations.
3. Tamper with one stored number -> the hash chain breaks, flagged.
"""
from __future__ import annotations

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.demo import sessions


def _run() -> DataOpsMemoryAgent:
    a = DataOpsMemoryAgent()
    for name, df, ts in sessions():
        a.ingest(df, name, ts=ts)
    return a


def main() -> None:
    print("WormBase Qwen Memory — prove it, then break it")
    print("=" * 70)

    # 1. Reproducibility: two independent runs, same hash.
    a1, a2 = _run(), _run()
    h1 = a1.kpi_history("total_amount")[0]["value_hash"]
    h2 = a2.kpi_history("total_amount")[0]["value_hash"]
    print("1) REPRODUCIBLE  two fresh runs -> same value_hash:")
    print(f"     run A: {h1[:32]}…")
    print(f"     run B: {h2[:32]}…  -> {'IDENTICAL ✓' if h1 == h2 else 'DIFFER ✗'}")

    # 2. Receipts-backed answer.
    ans = a1.answer("total_amount")
    print("\n2) RECEIPTS-BACKED ANSWER  'why did total_amount move?'")
    print(f"     {ans['prose']}")
    print(f"     grounded: {ans['grounded']}  (every number cites a ledger entry)")
    for r in ans["receipts"]:
        print(f"       ↳ seq {r['seq']:>2} {r['kind']:<16} hash {r['hash']}… value {r['value']}")

    # 3. Tamper-evidence: corrupt one stored value -> chain breaks.
    ok_before, _ = a1.verify()
    a1.ledger._conn.execute(
        "UPDATE ledger SET payload = REPLACE(payload, '2450', '9999') "
        "WHERE kind = 'kpi.computed'")
    a1.ledger._conn.commit()
    ok_after, broken = a1.verify()
    print("\n3) TAMPER-EVIDENT  edit one stored number:")
    print(f"     chain before: {'GREEN ✓' if ok_before else 'BROKEN'}")
    print(f"     chain after : {'GREEN' if ok_after else f'BROKEN at entry {broken} ✓ (tamper caught)'}")


if __name__ == "__main__":
    main()
