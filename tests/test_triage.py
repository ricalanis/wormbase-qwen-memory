"""Triage worker: exact short-circuit, gray-zone local-Qwen, deterministic fallback."""

from __future__ import annotations

import pandas as pd

from wormbase_memory.agent import DataOpsMemoryAgent
from wormbase_memory.inference import ChatResult
from wormbase_memory.recall import Match
from wormbase_memory.triage import Decision, Triage


class FakeLocal:
    """Stand-in for a local Qwen via Ollama — no network."""

    def __init__(self, reuse: bool, available: bool = True, tokens: int = 11):
        self._reuse, self._available, self._tokens = reuse, available, tokens
        self.calls = 0

    @property
    def available(self) -> bool:
        return self._available

    def chat(self, messages, **kw) -> ChatResult:
        self.calls += 1
        import json
        return ChatResult(
            text=json.dumps({"reuse": self._reuse, "reason": "fake"}),
            tokens=self._tokens, backend="local-qwen:fake",
        )


def _df(cols):
    rows = [tuple(range(len(cols)))]
    return pd.DataFrame(rows, columns=cols)


_CAND = Match("p1", [{"op": "dedup", "subset": None}], 0.75, "fp", ["a", "b", "c"])


def test_exact_match_reuses_without_calling_local():
    fake = FakeLocal(reuse=False)  # would say no — but exact must short-circuit
    t = Triage(local_client=fake)
    d = t.decide({"column_names": ["a", "b", "c"]},
                 Match("p1", [], 1.0, "fp", ["a", "b", "c"]))
    assert d.reuse is True and d.backend == "exact" and fake.calls == 0


def test_no_candidate_escalates():
    d = Triage(local_client=FakeLocal(True)).decide({"column_names": ["a"]}, None)
    assert d.reuse is False and d.backend == "none"


def test_gray_zone_uses_local_qwen():
    fake = FakeLocal(reuse=True, tokens=9)
    d = Triage(local_client=fake).decide({"column_names": ["a", "b", "x"]}, _CAND)
    assert d.reuse is True
    assert d.backend == "local-qwen:fake" and d.tokens == 9 and fake.calls == 1


def test_gray_zone_local_can_escalate():
    d = Triage(local_client=FakeLocal(reuse=False)).decide(
        {"column_names": ["a", "b", "x"]}, _CAND)
    assert d.reuse is False and d.backend == "local-qwen:fake"


def test_gray_zone_falls_back_to_rules_when_local_unavailable():
    d = Triage(local_client=FakeLocal(True, available=False)).decide(
        {"column_names": ["a", "b", "x"]}, _CAND)  # sim 0.75 < 0.9 -> escalate
    assert d.reuse is False and d.backend == "rules"


def test_agent_records_triage_decision_and_local_drives_reuse():
    # base table establishes a cached plan
    a = DataOpsMemoryAgent(triage=Triage(local_client=FakeLocal(reuse=True)))
    a.ingest(_df(["region", "product", "amount"]), "base")
    # gray-zone table (extra column) -> local says reuse
    r = a.ingest(_df(["region", "product", "amount", "note"]), "gray")
    assert r.reused is True
    assert r.triage_backend == "local-qwen:fake"
    decided = [e for e in a.ledger.fetch("triage.decided")]
    assert decided[-1].payload["decision"] == "reuse"
    assert a.verify()[0] is True
