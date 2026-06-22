#!/usr/bin/env python3
"""Reliability-over-horizon curve -> results/reliability_curve.png.  (backlog #1)

    uv run --extra viz python scripts/plot_reliability.py
"""
from __future__ import annotations

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from wormbase_memory.eval.reliability import reliability_curve  # noqa: E402


def main() -> None:
    rows = reliability_curve()
    h = [r["horizon"] for r in rows]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.plot(h, [r["decision_acc_on"] for r in rows], "o-", label="memory ON")
    ax1.plot(h, [r["decision_acc_off"] for r in rows], "s--", label="memory OFF")
    ax1.set_title("Decision reliability vs horizon"); ax1.set_ylim(0, 1.05)
    ax1.set_xlabel("sessions (horizon)"); ax1.set_ylabel("decision accuracy"); ax1.legend()
    ax2.plot(h, [r["cost_on"] for r in rows], "o-", label="memory ON")
    ax2.plot(h, [r["cost_off"] for r in rows], "s--", label="memory OFF")
    ax2.set_title("Cumulative planner tokens vs horizon")
    ax2.set_xlabel("sessions (horizon)"); ax2.set_ylabel("planner tokens"); ax2.legend()
    out = pathlib.Path("results"); out.mkdir(exist_ok=True)
    fig.tight_layout(); fig.savefig(out / "reliability_curve.png", dpi=120)
    print("on:  ", [(r["horizon"], r["decision_acc_on"]) for r in rows])
    print("off: ", [(r["horizon"], r["decision_acc_off"]) for r in rows])
    print("saved -> results/reliability_curve.png")


if __name__ == "__main__":
    main()
