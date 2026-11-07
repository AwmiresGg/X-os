"""Window and application model for the X-OS dock and menu bar.

* ``parse_update`` reads the JSON the KWin tracker script sends over D-Bus.
* ``AppRegistry`` reads freedesktop ``.desktop`` files (name, icon, Exec).
* ``dock_items`` merges pinned apps with running windows (one dock item per app,
  windows grouped under it, Windows-11-taskbar style).
* ``kwin_command_script`` builds a one-shot KWin script that activates / minimizes /
  closes / maximizes one window. Window ids are validated as UUIDs, so no caller can
  inject script code.
"""

from __future__ import annotations

import configparser
import json
import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

UUID_RE = re.compile(r"^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$")

# Apps that have an X-OS icon (symbolic glyph name under icons/xos/symbolic/apps).
XOS_ICONS = {
    "org.kde.dolphin": "files", "org.kde.konsole": "terminal", "firefox-esr": "browser",
    "firefox": "browser", "google-chrome": "browser", "org.kde.kwrite": "text-editor",
    "org.kde.kate": "text-editor", "systemsettings": "settings", "org.kde.systemsettings": "settings",
    "org.kde.okular": "pdf-viewer", "org.kde.gwenview": "photos", "org.kde.haruna": "video",
    "org.kde.ark": "archive", "org.kde.spectacle": "screenshot", "org.kde.kcalc": "calculator",
    "org.kde.plasma-systemmonitor": "system-monitor", "org.kde.partitionmanager": "disk-manager",
    "org.kde.kinfocenter": "device-manager", "xos-setup": "install", "xos-store": "store",
    "calamares": "install",
}

# Window app ids that belong to another app's desktop entry (Calamares reports its reverse-DNS id).
APP_ALIASES = {"io.calamares.calamares": "calamares"}

# Names X-OS shows instead of the upstream desktop entry's (the entry itself is not edited).
XOS_NAMES = {"calamares": "Install X-OS", "xos-setup": "Install X-OS"}

DEFAULT_PINNED = ["org.kde.dolphin", "firefox-esr", "org.kde.konsole", "org.kde.kwrite",
                  "org.kde.gwenview", "org.kde.haruna", "org.kde.kcalc", "systemsettings"]


@dataclass
class Window:
    id: str
    caption: str
    app_id: str
    minimized: bool = False


@dataclass
class AppInfo:
    id: str
    name: str
    icon: str = ""
    exec: str = ""
    xos_icon: str = ""


@dataclass
class DockItem:
    app_id: str
    name: str
    icon: str
    xos_icon: str
    pinned: bool
    windows: list[Window] = field(default_factory=list)
    active: bool = False

    @property
    def running(self) -> bool:
        return bool(self.windows)

    def to_dict(self) -> dict:
        return {"appId": self.app_id, "name": self.name, "icon": self.icon, "xosIcon": self.xos_icon,
                "pinned": self.pinned, "running": self.running, "active": self.active,
                "windows": [{"id": w.id, "caption": w.caption, "minimized": w.minimized} for w in self.windows]}


def normalize_app_id(app_id: str) -> str:
    a = (app_id or "").strip()
    if a.endswith(".desktop"):
        a = a[: -len(".desktop")]
    return APP_ALIASES.get(a, a)


def parse_update(payload: str) -> tuple[list[Window], str]:
    """Tracker JSON -> (windows, active window id). Invalid input -> ([], "")."""
    try:
        data = json.loads(payload)
    except (ValueError, TypeError):
        return [], ""
    wins = []
    for w in data.get("windows", []):
        wid = str(w.get("id", ""))
        if not UUID_RE.match(wid):
            continue
        wins.append(Window(wid, str(w.get("caption", "")), normalize_app_id(str(w.get("appId", ""))),
                           bool(w.get("minimized", False))))
    active = str(data.get("active", ""))
    return wins, active if UUID_RE.match(active) else ""


# --------------------------------------------------------------------------- .desktop files
def _xdg_app_dirs() -> list[Path]:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    return [data_home / "applications"] + [Path(d) / "applications" for d in data_dirs if d]


class AppRegistry:
    def __init__(self, dirs: list[Path] | None = None):
        self.dirs = dirs if dirs is not None else _xdg_app_dirs()
        self._cache: dict[str, AppInfo | None] = {}

    def get(self, app_id: str) -> AppInfo:
        app_id = normalize_app_id(app_id)
        if app_id not in self._cache:
            self._cache[app_id] = self._load(app_id)
        info = self._cache[app_id]
        return info or AppInfo(app_id, XOS_NAMES.get(app_id) or app_id.split(".")[-1].replace("-", " ").title() or "Application",
                               icon="application-x-executable", xos_icon=XOS_ICONS.get(app_id, ""))

    def _load(self, app_id: str) -> AppInfo | None:
        for d in self.dirs:
            path = d / f"{app_id}.desktop"
            if path.is_file():
                cp = configparser.ConfigParser(interpolation=None, strict=False)
                try:
                    cp.read(path, encoding="utf-8")
                except (configparser.Error, UnicodeDecodeError):
                    continue
                if not cp.has_section("Desktop Entry"):
                    continue
                e = cp["Desktop Entry"]
                return AppInfo(app_id, XOS_NAMES.get(app_id, e.get("Name", app_id)), e.get("Icon", ""), e.get("Exec", ""),
                               XOS_ICONS.get(app_id, ""))
        return None


def launch_argv(exec_line: str) -> list[str]:
    """Desktop-entry Exec -> argv with field codes (%f %F %u %U %i %c %k ...) removed."""
    try:
        parts = shlex.split(exec_line)
    except ValueError:
        return []
    out = []
    for p in parts:
        if re.fullmatch(r"%[fFuUdDnNickvm]", p):
            continue
        out.append(p.replace("%%", "%"))
    return out


# --------------------------------------------------------------------------- dock
def dock_items(pinned: list[str], windows: list[Window], active_id: str, registry: AppRegistry) -> list[DockItem]:
    items: dict[str, DockItem] = {}
    order: list[str] = []

    def item_for(app_id: str, pinned_flag: bool) -> DockItem:
        if app_id not in items:
            info = registry.get(app_id)
            items[app_id] = DockItem(app_id, info.name, info.icon, info.xos_icon, pinned_flag)
            order.append(app_id)
        return items[app_id]

    for app_id in pinned:
        item_for(normalize_app_id(app_id), True)
    for w in windows:
        it = item_for(w.app_id or "unknown", False)
        it.windows.append(w)
        if w.id == active_id:
            it.active = True
    return [items[a] for a in order]


# --------------------------------------------------------------------------- KWin commands
_ACTIONS = {
    "activate": "workspace.activeWindow = w;",
    "minimize": "w.minimized = true;",
    "close": "w.closeWindow();",
    "toggle-maximize": "var m = (w.frameGeometry.width >= workspace.clientArea(KWin.MaximizeArea, w).width);"
                       " w.setMaximize(!m, !m);",
}


def kwin_command_script(window_id: str, action: str) -> str:
    if not UUID_RE.match(window_id):
        raise ValueError("invalid window id")
    if action not in _ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    wid = window_id.strip("{}").lower()
    return ("var all = workspace.windowList();\n"
            "for (var i = 0; i < all.length; ++i) {\n"
            "    var w = all[i];\n"
            f"    if (w.internalId.toString().replace(/[{{}}]/g, '').toLowerCase() === '{wid}') {{\n"
            f"        {_ACTIONS[action]}\n"
            "        break;\n"
            "    }\n"
            "}\n")
