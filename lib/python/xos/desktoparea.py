"""Space the X-OS shell keeps free of desktop icons.

The menu bar and dock are layer-shell surfaces: KWin keeps *windows* clear of the menu bar
(exclusion zone), but plasmashell, which draws the desktop icons, does not read other
clients' zones, so icons were placed under the menu bar. plasmashell offers a D-Bus hook
for exactly this (org.kde.PlasmaShell.StrutManager, used by third-party docks): a client
reports the *available* rectangle per screen, and plasmashell drops it again when that
client leaves the bus.
"""
from __future__ import annotations

import json
from pathlib import Path

SERVICE, PATH, IFACE = "org.kde.plasmashell", "/StrutManager", "org.kde.PlasmaShell.StrutManager"

_TOKENS = Path(__file__).resolve().parents[3] / "ui/theme/tokens.json"


def bar_sizes(tokens: dict | None = None) -> tuple[int, int]:
    """(top, bottom) in logical pixels: the menu bar, and the floating dock with its margins."""
    if tokens is None:
        for p in (_TOKENS, Path("/usr/share/xos/theme/tokens.json")):
            if p.is_file():
                tokens = json.loads(p.read_text())
                break
        else:
            tokens = {"bar": {"menuBarHeight": 34, "dockHeight": 64, "edgeMargin": 8}}
    b = tokens["bar"]
    top = int(b["menuBarHeight"])
    bottom = int(b["dockHeight"] + 2 * b["edgeMargin"])
    return top, bottom


def available_rect(x: int, y: int, w: int, h: int, top: int, bottom: int) -> tuple[int, int, int, int]:
    """Screen geometry minus the menu bar (top) and dock area (bottom), never negative."""
    top, bottom = max(0, top), max(0, bottom)
    if top + bottom >= h:
        return x, y, w, h
    return x, y + top, w, h - top - bottom
