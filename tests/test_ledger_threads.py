"""Streamlit reruns on new threads — the ledger must survive cross-thread +
concurrent writes with the hash chain intact."""

from __future__ import annotations

import threading

from wormbase_memory.ledger import Ledger


def test_append_from_another_thread():
    led = Ledger()  # created on the main thread
    led.append("kpi.computed", {"v": 1})
    out = {}

    def rerun():
        out["entry"] = led.append("kpi.computed", {"v": 2})  # different thread

    t = threading.Thread(target=rerun)
    t.start()
    t.join()
    assert out["entry"].seq == 2
    assert led.verify()[0] is True


def test_concurrent_appends_keep_chain_intact():
    led = Ledger()
    n = 40

    def worker(i: int):
        led.append("kpi.computed", {"i": i})

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    entries = led.fetch()
    assert len(entries) == n
    assert [e.seq for e in entries] == list(range(1, n + 1))  # monotonic, no gaps
    assert led.verify()[0] is True  # chain verifies despite concurrency
