#!/usr/bin/env python3
"""Plot the 'smarter + cheaper over sessions' curve -> results/smarter_curve.png.

    uv run --extra viz python scripts/plot_curve.py
"""
from __future__ import annotations

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from wormbase_memory.eval.curve import evaluate  # noqa: E402


def main() -> None:
    data = evaluate(n_sessions=8, drift_at=(4, 7))
    on, off = data["on"], data["off"]
    x = [r["session"] for r in on]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.plot(x, [r["cost"] for r in on], "o-", label="memory ON")
    ax1.plot(x, [r["cost"] for r in off], "s--", label="memory OFF")
    ax1.set_title("Planner cost per session (cheaper over time)")
    ax1.set_xlabel("session"); ax1.set_ylabel("planner cost units"); ax1.legend()

    ax2.plot(x, [r["cum_accuracy"] for r in on], "o-", label="memory ON")
    ax2.plot(x, [r["cum_accuracy"] for r in off], "s--", label="memory OFF")
    ax2.set_title("Cumulative drift-decision accuracy (smarter over time)")
    ax2.set_xlabel("session"); ax2.set_ylabel("accuracy"); ax2.set_ylim(0, 1.05); ax2.legend()

    out = pathlib.Path("results"); out.mkdir(exist_ok=True)
    fig.tight_layout(); fig.savefig(out / "smarter_curve.png", dpi=120)
    print(f"on  final: cost={on[-1]['cost']} acc={on[-1]['cum_accuracy']}")
    print(f"off final: cost={off[-1]['cost']} acc={off[-1]['cum_accuracy']}")
    print("saved -> results/smarter_curve.png")


if __name__ == "__main__":
    main()
