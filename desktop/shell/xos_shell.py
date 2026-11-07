#!/usr/bin/python3
"""X-OS shell: the top menu bar and the floating dock.

    xos-shell                       # in a Plasma (Wayland) session
    xos-shell --preview OUT.png     # render menu bar + dock + popovers over the wallpaper
                                    # with demo data (no system access) and exit

One lightweight process. Status is polled on a worker thread (never on the UI thread),
windows come from the KWin tracker script over D-Bus, and every action calls a real
system interface (see lib/python/xos/shellstatus.py and windows.py).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in ("/usr/lib/xos/python", str(HERE.parents[1] / "lib/python")):
    if Path(p, "xos").is_dir():
        sys.path.insert(0, p)
        break

from PySide6.QtCore import (ClassInfo, Property, QObject, QProcess, QSize, QTimer, QUrl, Qt,  # noqa: E402
                            Signal, Slot)
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickImageProvider, QQuickWindow  # noqa: E402,F401
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

from xos import shellstatus as ss  # noqa: E402
from xos import windows as W  # noqa: E402

ICON_DIRS = [Path("/usr/share/xos/icons/xos"), HERE.parents[1] / "icons/xos"]
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "xos/shell.json"
DEFAULT_SETTINGS = {
    "dockOpacity": 0.6, "menuBarOpacity": 0.8, "dockIconSize": 46, "dockAutoHide": False,
    "showLabels": False, "theme": "dark", "reducedMotion": False, "lowResource": False,
    "pinned": W.DEFAULT_PINNED,
}


# --------------------------------------------------------------------------- icons
def find_glyph(name: str) -> Path | None:
    for base in ICON_DIRS:
        hits = list((base / "symbolic").glob(f"*/{name}.svg")) if (base / "symbolic").is_dir() else []
        if hits:
            return hits[0]
    return None


class IconProvider(QQuickImageProvider):
    """image://xicon/<glyph>?color=<#rrggbb>  — X-OS glyph tinted on the CPU (works without GPU).
    image://appicon/<theme-icon-name>         — application icon from the icon theme."""

    def __init__(self, kind: str):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.kind = kind
        self.cache: dict[tuple, QImage] = {}

    def requestImage(self, ident, size, requested):  # noqa: N802 (Qt API)
        w = requested.width() if requested.width() > 0 else 48
        h = requested.height() if requested.height() > 0 else w
        key = (ident, w, h)
        if key in self.cache:
            return self.cache[key]
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        if self.kind == "xicon":
            name, _, query = ident.partition("?")
            color = query.removeprefix("color=") or "#ECEEF1"
            path = find_glyph(name)
            if path:
                svg = path.read_text().replace("currentColor", color)
                r = QSvgRenderer(svg.encode())
                p = QPainter(img)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                r.render(p)
                p.end()
        else:
            icon = QIcon.fromTheme(ident) if not ident.startswith("/") else QIcon(ident)
            if icon.isNull():
                icon = QIcon.fromTheme("application-x-executable")
            pm = icon.pixmap(QSize(w, h))
            if not pm.isNull():
                img = pm.toImage()                   # else: stay transparent, never an error
        self.cache[key] = img
        return img


# --------------------------------------------------------------------------- settings
class Settings(QObject):
    changed = Signal()

    def __init__(self, path: Path = CONFIG, persist: bool = True):
        super().__init__()
        self.path, self.persist = path, persist
        self._d = dict(DEFAULT_SETTINGS)
        try:
            self._d.update({k: v for k, v in json.loads(path.read_text()).items() if k in DEFAULT_SETTINGS})
        except (OSError, ValueError):
            pass

    @Property("QVariantMap", notify=changed)
    def values(self):
        return self._d

    @Slot(str, "QVariant")
    def set(self, key, value):
        if key not in DEFAULT_SETTINGS or self._d.get(key) == value:
            return
        if key in ("dockOpacity", "menuBarOpacity"):
            value = max(0.15, min(1.0, float(value)))       # always readable
        if key == "dockIconSize":
            value = int(max(32, min(72, int(value))))
        self._d[key] = value
        self.changed.emit()
        if self.persist:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._d, indent=2))


# --------------------------------------------------------------------------- status
class Status(QObject):
    """System status, refreshed on a worker thread at a modest rate."""
    changed = Signal()
    _arrived = Signal("QVariantMap")

    INTERVALS = {"battery": 30, "network": 4, "bluetooth": 10, "audio": 2, "brightness": 10, "trash": 10}
    READERS = {
        "battery": lambda: ss.read_battery(), "network": lambda: ss.read_network(),
        "bluetooth": lambda: ss.read_bluetooth(), "audio": lambda: ss.read_audio(),
        "brightness": lambda: ss.read_brightness(), "trash": lambda: ss.read_trash(),
    }

    def __init__(self, demo: dict | None = None):
        super().__init__()
        self._data: dict = {}
        self._arrived.connect(self._merge)
        self._kick = threading.Event()
        if demo is not None:
            self._data = demo
        else:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        due = {k: 0.0 for k in self.INTERVALS}
        while True:
            now = time.monotonic()
            update = {}
            for k, interval in self.INTERVALS.items():
                if now >= due[k]:
                    obj = self.READERS[k]()
                    d = obj.__dict__.copy()
                    if hasattr(obj, "icon"):
                        d["icon"] = obj.icon()
                    update[k] = d
                    due[k] = now + interval
            if update:
                self._arrived.emit(update)
            self._kick.wait(1.0)
            if self._kick.is_set():
                self._kick.clear()
                due = {k: 0.0 for k in due}

    @Slot("QVariantMap")
    def _merge(self, update):
        self._data = {**self._data, **update}
        self.changed.emit()

    @Property("QVariantMap", notify=changed)
    def data(self):
        return self._data

    def _act(self, fn, *args):
        def run():
            fn(*args)
            self._kick.set()                                  # refresh right after an action
        threading.Thread(target=run, daemon=True).start()

    @Slot(bool)
    def setWifi(self, on):
        self._act(ss.set_wifi, on)

    @Slot(bool)
    def setBluetooth(self, on):
        self._act(ss.set_bluetooth, on)

    @Slot(int)
    def setVolume(self, pct):
        self._act(ss.set_volume, pct)

    @Slot(bool)
    def setMuted(self, m):
        self._act(ss.set_muted, m)

    @Slot(int)
    def setBrightness(self, pct):
        self._act(ss.set_brightness, pct)

    @Slot(bool)
    def setDark(self, dark):
        self._act(ss.set_appearance, dark)

    @Slot(str)
    def power(self, action):
        if action in ss.POWER_ACTIONS:
            self._act(ss.power_action, action)


# --------------------------------------------------------------------------- windows (D-Bus)
@ClassInfo({"D-Bus Interface": "org.xos.Shell.Windows"})
class WindowsEndpoint(QObject):
    """Receives updates from the KWin tracker script (callDBus → update(json))."""

    def __init__(self, model: "Windows"):
        super().__init__()
        self.model = model

    @Slot(str)
    def update(self, payload):
        self.model.apply(payload)


class Windows(QObject):
    changed = Signal()

    def __init__(self, settings: Settings, demo: dict | None = None):
        super().__init__()
        self.settings = settings
        self.registry = W.AppRegistry()
        self._windows: list[W.Window] = []
        self._active = ""
        self._seq = 0
        settings.changed.connect(self.changed)
        if demo:
            self.apply(json.dumps(demo))
        else:
            self._connect_kwin()

    # D-Bus wiring
    def _connect_kwin(self):
        from PySide6.QtDBus import QDBusConnection, QDBusInterface
        self.bus = QDBusConnection.sessionBus()
        self.endpoint = WindowsEndpoint(self)
        if not self.bus.registerService("org.xos.Shell"):
            print("xos-shell: another instance owns org.xos.Shell", file=sys.stderr)
        self.bus.registerObject("/Windows", self.endpoint, QDBusConnection.RegisterOption.ExportAllSlots)
        self.scripting = QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", self.bus)
        tracker = next((p for p in (Path("/usr/share/xos/shell/kwin/xos-windows/contents/code/main.js"),
                                    HERE / "kwin/xos-windows/contents/code/main.js") if p.exists()), None)
        self._tracker = str(tracker) if tracker else ""
        self._retry = QTimer(self)
        self._retry.setInterval(5000)
        self._retry.timeout.connect(self._start_tracker)
        self._start_tracker()

    def _start_tracker(self):
        """KWin may start after us or restart: keep trying until the tracker is loaded."""
        if self._tracker and self._run_kwin_script(self._tracker, "xos-windows"):
            self._retry.stop()
        else:
            if not self._retry.isActive():
                print("xos-shell: KWin scripting not available yet; retrying", file=sys.stderr)
            self._retry.start()

    def _run_kwin_script(self, path: str, name: str) -> bool:
        """Load and run a KWin script. Returns False (never raises) if KWin is unavailable."""
        from PySide6.QtDBus import QDBusInterface, QDBusMessage
        self.scripting.call("unloadScript", name)
        reply = self.scripting.call("loadScript", path, name)
        args = reply.arguments()
        if reply.type() == QDBusMessage.MessageType.ErrorMessage or not args \
                or not isinstance(args[0], int) or args[0] < 0:
            return False
        script = QDBusInterface("org.kde.KWin", f"/Scripting/Script{args[0]}", "org.kde.kwin.Script", self.bus)
        script.call("run")
        return True

    def apply(self, payload: str):
        self._windows, self._active = W.parse_update(payload)
        self.changed.emit()

    # model for QML
    @Property("QVariantList", notify=changed)
    def items(self):
        pinned = self.settings.values.get("pinned", [])
        out = []
        for item in W.dock_items(pinned, self._windows, self._active, self.registry):
            d = item.to_dict()
            d["glyph"] = item.xos_icon if item.xos_icon and find_glyph(item.xos_icon) else ""
            out.append(d)
        return out

    @Property("QVariantMap", notify=changed)
    def active(self):
        for w in self._windows:
            if w.id == self._active:
                info = self.registry.get(w.app_id)
                return {"id": w.id, "caption": w.caption, "appId": w.app_id, "name": info.name}
        return {"id": "", "caption": "", "appId": "", "name": "Desktop"}

    # actions
    @Slot(str, str)
    def windowAction(self, window_id, action):
        if not hasattr(self, "scripting"):
            return
        try:
            js = W.kwin_command_script(window_id, action)
        except ValueError:
            return
        self._seq += 1
        name = f"xos-cmd-{os.getpid()}-{self._seq}"
        fd, path = tempfile.mkstemp(prefix="xos-cmd-", suffix=".js", dir=os.environ.get("XDG_RUNTIME_DIR"))
        with os.fdopen(fd, "w") as fh:
            fh.write(js)
        self._run_kwin_script(path, name)
        QTimer.singleShot(1500, lambda: (self.scripting.call("unloadScript", name), Path(path).unlink(missing_ok=True)))

    @Slot(str)
    def activateApp(self, app_id):
        """Dock click: launch if not running, focus if in background, minimize if focused."""
        items = {i.app_id: i for i in W.dock_items([], self._windows, self._active, self.registry)}
        item = items.get(W.normalize_app_id(app_id))
        if not item or not item.windows:
            self.launch(app_id)
        elif item.active:
            for w in item.windows:
                self.windowAction(w.id, "minimize")
        else:
            self.windowAction(item.windows[-1].id, "activate")

    @Slot(str)
    def launch(self, app_id):
        argv = W.launch_argv(self.registry.get(app_id).exec)
        if argv:
            QProcess.startDetached(argv[0], argv[1:])

    @Slot(str)
    def openUrl(self, target):
        """Open a settings module / folder / URL with the desktop's handler."""
        allowed = target.startswith(("systemsettings", "kcm_", "trash:/", "file://", "https://"))
        if not allowed:
            return
        if target.startswith(("systemsettings", "kcm_")):
            QProcess.startDetached("systemsettings", [target.split(":", 1)[1]] if ":" in target else [])
        else:
            QProcess.startDetached("xdg-open", [target])

    @Slot()
    def search(self):
        """Global search: Plasma's KRunner (apps, files, settings, calculator)."""
        QProcess.startDetached("dbus-send", ["--session", "--type=method_call", "--dest=org.kde.krunner",
                                             "/App", "org.kde.krunner.App.display"])

    @Slot()
    def forceQuit(self):
        """KWin's kill mode: the next window clicked is force-quit (like xkill)."""
        QProcess.startDetached("dbus-send", ["--session", "--type=method_call", "--dest=org.kde.KWin",
                                             "/KWin", "org.kde.KWin.killWindow"])

    @Slot(str)
    def togglePin(self, app_id):
        pinned = list(self.settings.values.get("pinned", []))
        app_id = W.normalize_app_id(app_id)
        pinned.remove(app_id) if app_id in pinned else pinned.append(app_id)
        self.settings.set("pinned", pinned)


# --------------------------------------------------------------------------- main
DEMO_STATUS = {
    "battery": {"present": True, "percent": 97, "charging": False, "on_ac": False, "source": "Battery", "icon": "battery-full"},
    "network": {"state": "connected", "kind": "wifi", "name": "Home-5G", "signal": 82, "wifi_enabled": True, "vpn": False, "icon": "wifi-3"},
    "bluetooth": {"present": True, "powered": True},
    "audio": {"available": True, "volume": 62, "muted": False, "icon": "volume-medium"},
    "brightness": {"available": True, "device": "intel_backlight", "percent": 70, "maximum": 1000},
    "trash": {"full": False},
}
DEMO_WINDOWS = {"windows": [
    {"id": "0b5c7e1a-1111-4a2b-9c3d-aaaaaaaaaaaa", "caption": "Home — Dolphin", "appId": "org.kde.dolphin"},
    {"id": "0b5c7e1a-2222-4a2b-9c3d-bbbbbbbbbbbb", "caption": "X-OS — Mozilla Firefox", "appId": "firefox-esr"},
    {"id": "0b5c7e1a-3333-4a2b-9c3d-cccccccccccc", "caption": "~ : bash — Konsole", "appId": "org.kde.konsole"},
], "active": "0b5c7e1a-2222-4a2b-9c3d-bbbbbbbbbbbb"}


def _keep_dock_input_region(app) -> None:
    """Limit the dock surface's input region to the visible dock (the window is taller to
    leave room for the launch droplet; the transparent band must not swallow clicks).
    Best effort: a failure here must never take the shell down."""
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QRegion
    try:
        dock_win = bar = None
        for w in app.topLevelWindows():
            if isinstance(w, QQuickWindow):
                bar = w.findChild(QObject, "dockBar") or w.contentItem().findChild(QObject, "dockBar")
                if bar is not None:
                    dock_win = w
                    break
        if bar is None:
            print("xos-shell: dock not found; input region not limited", file=sys.stderr)
            return
        last = {"r": None}

        def update():
            try:
                r = bar.property("inputRect").toRect()
                if r != last["r"]:
                    last["r"] = r
                    dock_win.setMask(QRegion(QRect(r)))
            except Exception as e:      # noqa: BLE001
                print(f"xos-shell: input region update failed: {e}", file=sys.stderr)
        timer = QTimer(dock_win)
        timer.timeout.connect(update)
        timer.start(500)
        update()
    except Exception as e:              # noqa: BLE001
        print(f"xos-shell: input region disabled: {e}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", metavar="PNG", help="render a preview with demo data and exit")
    ap.add_argument("--open", default="", help="preview: popover to show (system, battery, control)")
    ap.add_argument("--theme", default="", help="preview: dark | light")
    ap.add_argument("--opacity", type=float, default=None, help="preview: dock/menu bar opacity")
    ap.add_argument("--smoke", type=float, default=0, help="real mode: run N seconds, then exit 0 (tests)")
    ap.add_argument("--launch-p", type=float, default=-1, help="preview: freeze the launch droplet at p (0..1)")
    ap.add_argument("--simulate-launch", metavar="DIR", help="preview: open a new app window after 0.8 s and "
                                                               "save frames of the live animation to DIR")
    a = ap.parse_args()

    if not a.preview:
        QQuickWindow.setDefaultAlphaBuffer(True)
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("xos-shell")
    app.setDesktopFileName("xos-shell")
    app.setQuitOnLastWindowClosed(False)

    settings = Settings(persist=not a.preview)
    if a.theme:
        settings._d["theme"] = a.theme
    if a.opacity is not None:
        settings._d["dockOpacity"] = settings._d["menuBarOpacity"] = a.opacity
    status = Status(DEMO_STATUS if a.preview else None)
    wins = Windows(settings, DEMO_WINDOWS if a.preview else None)

    engine = QQmlApplicationEngine()
    engine.addImageProvider("xicon", IconProvider("xicon"))
    engine.addImageProvider("appicon", IconProvider("appicon"))
    qml = HERE / "qml"
    engine.addImportPath(str(HERE.parents[1] / "ui/qml"))
    engine.addImportPath("/usr/share/xos/qml")
    wayland = QGuiApplication.platformName() == "wayland"
    engine.addImportPath(str(qml / "platform" / ("wayland" if wayland and not a.preview else "fallback")))
    engine.setInitialProperties({"settings": settings, "status": status, "windows": wins,
                                 "previewOpen": a.open, "previewLaunch": a.launch_p})
    engine.load(QUrl.fromLocalFile(str(qml / ("Preview.qml" if a.preview else "Shell.qml"))))
    if not engine.rootObjects():
        return 1
    if not a.preview:
        _keep_dock_input_region(app)
    if a.smoke and not a.preview:
        QTimer.singleShot(int(a.smoke * 1000), app.quit)
    if a.preview:
        win = engine.rootObjects()[0]

        def grab():
            try:
                win.grabWindow().save(a.preview)
            finally:
                app.quit()
        if a.simulate_launch:
            out = Path(a.simulate_launch)
            out.mkdir(parents=True, exist_ok=True)
            launched = dict(DEMO_WINDOWS, windows=DEMO_WINDOWS["windows"] + [
                {"id": "0b5c7e1a-4444-4a2b-9c3d-dddddddddddd", "caption": "Untitled — KWrite", "appId": "org.kde.kwrite"}],
                active="0b5c7e1a-4444-4a2b-9c3d-dddddddddddd")
            QTimer.singleShot(800, lambda: wins.apply(json.dumps(launched)))
            frame = {"n": 0}

            def snap():
                win.grabWindow().copy(400, 680, 640, 220).save(str(out / f"f{frame['n']:03d}.png"))
                frame["n"] += 1
            t = QTimer(win)
            t.timeout.connect(snap)
            QTimer.singleShot(760, lambda: t.start(30))
            QTimer.singleShot(1600, app.quit)
        else:
            QTimer.singleShot(2500, grab)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
