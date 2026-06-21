"""User-preference memory — folded from the ledger, last-writer-wins.

Preferences are remembered across sessions and supersede on conflict (a
`pref.superseded` entry records the change, so forgetting an old preference is
itself auditable — mirrors the project's tombstone discipline). Two preferences
are wired into behavior: `drift_threshold` (sensitivity) and `narrative_style`
(terse/verbose).
"""

from __future__ import annotations

from typing import Any

from .ledger import Ledger

DEFAULTS: dict[str, Any] = {
    "drift_threshold": 0.15,
    "narrative_style": "verbose",  # "verbose" | "terse"
}


def current(ledger: Ledger) -> dict[str, Any]:
    """Fold pref.set entries into the current preference set (last wins)."""
    prefs = dict(DEFAULTS)
    for e in ledger.fetch("pref.set"):
        prefs[e.payload["key"]] = e.payload["value"]
    return prefs
