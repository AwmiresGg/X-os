#!/usr/bin/env python3
"""X-OS Settings: Tweaks, Updates, Security, This PC, About.

    xos-settings [--page tweaks|updates|security|this-pc|about] [--preview PNG]

Long work (scans, updates, password prompts) runs in QProcess so the window never freezes.
Privileged steps go through ``pkexec /usr/libexec/xos/xos-admin`` (polkit asks for the
password); package updates through PackageKit, which asks itself.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (str(HERE.parents[1] / "lib/python"), "/usr/lib/xos/python"):     # source tree first
    if Path(p, "xos").is_dir():
        sys.path.insert(0, p)
        break

from PySide6.QtCore import Property, QObject, QProcess, QSize, QTimer, QUrl, Qt, Signal, Slot  # noqa: E402
from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPainter  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickImageProvider  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

from xos import security, thispc, tweaks, updates  # noqa: E402

ADMIN = "/usr/libexec/xos/xos-admin"
GLYPH_DIRS = [HERE.parents[1] / "icons/xos/symbolic", Path("/usr/share/xos/icons/xos/symbolic")]
PAGES = ("tweaks", "updates", "security", "this-pc", "about")
APP_IDS = {"tweaks": "xos-settings", "updates": "xos-updates", "security": "xos-security",
           "this-pc": "xos-this-pc", "about": "xos-settings"}


def find_glyph(name: str) -> Path | None:
    for d in GLYPH_DIRS:
        hits = list(d.glob(f"*/{name}.svg")) if d.is_dir() else []
        if hits:
            return hits[0]
    return None


class GlyphProvider(QQuickImageProvider):
    """image://glyph/<name>?color=#rrggbb - monochrome X-OS symbol, tinted."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, ident, size, requested):  # noqa: N802 (Qt API)
        w = requested.width() if requested.width() > 0 else 32
        name, _, q = ident.partition("?")
        img = QImage(w, w, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        path = find_glyph(name)
        if path:
            svg = path.read_text().replace("currentColor", q.removeprefix("color=") or "#EDEEF0")
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            QSvgRenderer(svg.encode()).render(p)
            p.end()
        return img


class Backend(QObject):
    changed = Signal()
    toast = Signal(str)

    def __init__(self, page: str, preview: bool = False):
        super().__init__()
        self._page = page
        self.preview = preview
        self._mode = tweaks.current()
        self._busy = ""                 # what is running right now ("" = idle)
        self._log = ""
        self._sec = {} if preview else security.status()
        self._scan = {"running": False, "found": [], "result": "", "started": 0, "elapsed": 0, "target": ""}
        self._updates = {"checked": False, "updates": [], "errors": [], "summary": ""}
        self._drives = [] if preview else thispc.drives()
        self._auto_updates = self._timer_enabled()
        self.proc: QProcess | None = None
        self.queue: list[tuple[list[str], str]] = []
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(3000)
        if preview:
            self._demo()

    # ------------------------------------------------------------------ properties
    @Property(str, notify=changed)
    def page(self):
        return self._page

    @page.setter
    def page(self, v):
        if v in PAGES and v != self._page:
            self._page = v
            self.changed.emit()
            if v == "this-pc" and not self.preview:
                self.refreshDrives()

    @Property("QVariantList", constant=True)
    def modes(self):
        return [{"id": m.id, "title": m.title, "subtitle": m.subtitle, "glyph": m.glyph, "power": m.power,
                 "effects": "Off" if m.animation_factor == 0 else ("Reduced" if not m.blur else "Full"),
                 "sysctl": [f"{k} = {v}" for k, v in sorted(m.sysctl.items())], "notes": list(m.notes)}
                for m in tweaks.MODES.values()]

    @Property(str, notify=changed)
    def mode(self):
        return self._mode

    @Property(str, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def log(self):
        return self._log

    @Property("QVariantMap", notify=changed)
    def sec(self):
        return self._sec

    @Property("QVariantMap", notify=changed)
    def scan(self):
        s = dict(self._scan)
        s["found"] = [dict(f) for f in s["found"]]
        return s

    @Property("QVariantMap", notify=changed)
    def upd(self):
        return self._updates

    @Property(bool, notify=changed)
    def autoUpdates(self):
        return self._auto_updates

    @Property("QVariantList", notify=changed)
    def drives(self):
        out = []
        for d in self._drives:
            d = dict(d)
            d["sizeText"] = thispc.human(d["size"])
            d["freeText"] = thispc.human(d["free"]) if d["free"] is not None else ""
            out.append(d)
        return out

    @Property(str, constant=True)
    def logo(self):
        for p in (HERE.parents[1] / "icons/xos/brand/x-os-logo.svg", Path("/usr/share/xos/icons/xos/brand/x-os-logo.svg")):
            if p.is_file():
                return QUrl.fromLocalFile(str(p)).toString()
        return ""

    @Property("QVariantMap", constant=True)
    def about(self):
        info = {"version": "", "kernel": platform.release(), "cpu": "", "memory": "", "host": platform.node()}
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    info["version"] = line.split("=", 1)[1].strip('"')
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    info["cpu"] = line.split(":", 1)[1].strip()
                    break
            kb = int(next(l.split()[1] for l in Path("/proc/meminfo").read_text().splitlines() if l.startswith("MemTotal")))
            info["memory"] = f"{kb / 1024 / 1024:.1f} GB"
        except (OSError, StopIteration, ValueError):
            pass
        return info

    # ------------------------------------------------------------------ process runner
    def _run_queue(self, steps: list[tuple[list[str], str]], done=None, stop_on_error: bool = True):
        """Run commands one after another; stream output into log; call done(ok, output).
        stop_on_error=False: later steps still run (e.g. app updates after a failed system update)."""
        if self.proc is not None:
            self.toast.emit("Please wait for the current task to finish.")
            return
        self.queue = list(steps)
        self._stop_on_error = stop_on_error
        self._done = done
        self._out = ""
        self._ok = True
        self._next()

    def _next(self):
        if not self.queue:
            self.proc = None
            self._busy = ""
            if self._done:
                self._done(self._ok, self._out)
            self.changed.emit()
            return
        cmd, label = self.queue.pop(0)
        self._busy = label
        self.changed.emit()
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self._read(p))
        p.finished.connect(lambda code, _st: self._finished(code))
        self.proc = p
        p.start(cmd[0], cmd[1:])

    def _read(self, p):
        text = bytes(p.readAllStandardOutput()).decode(errors="replace")
        self._out += text
        self._log = (self._log + text)[-6000:]
        self.changed.emit()

    def _finished(self, code):
        self._last_code = code
        if code != 0:
            self._ok = False
            if self._stop_on_error:
                self.queue = []
        self.proc = None
        self._next()

    @Slot()
    def cancel(self):
        if self.proc is not None:
            self.queue = []
            self.proc.terminate()

    # ------------------------------------------------------------------ tweaks
    @Slot(str)
    def applyMode(self, mode_id):
        if mode_id not in tweaks.MODES or self.preview:
            return
        steps = [([shutil.which("pkexec") or "pkexec", ADMIN, "tweaks", mode_id], "Applying " + tweaks.MODES[mode_id].title)]
        steps += [(c, "") for c in tweaks.session_commands(mode_id)]

        def done(ok, out):
            if ok:
                self._mode = mode_id
                self.toast.emit(f"{tweaks.MODES[mode_id].title} mode is on.")
            else:
                self.toast.emit("The mode was not changed." if "dismissed" in out.lower() or not out.strip()
                                else "Could not apply the mode: " + out.strip().splitlines()[-1])
        self._run_queue(steps, done)

    # ------------------------------------------------------------------ security
    @Slot(str)
    def startScan(self, target):
        if self.preview:
            return
        if target == "quick":
            paths, label = security.quick_scan_paths(), "Quick scan"
        elif target == "full":
            paths, label = [str(Path.home())], "Full scan"
        else:
            path = QUrl(target).toLocalFile() if target.startswith("file:") else target
            paths, label = [path], "Scan of " + Path(path).name
        if not shutil.which("clamscan"):
            self.toast.emit("The virus scanner is not installed.")
            return
        security.QUARANTINE.mkdir(parents=True, exist_ok=True)
        self._scan = {"running": True, "found": [], "result": "", "started": time.time(), "elapsed": 0,
                      "target": label}

        def done(ok, out):
            found = security.parse_scan_output(out)
            meaning = security.scan_exit_meaning(getattr(self, "_last_code", 2))
            if meaning == "error" and not security.definitions()["installed"]:
                result = "No virus definitions yet. Update them first."
            elif found:
                result = f"{len(found)} threat{'s' if len(found) != 1 else ''} found and moved to quarantine."
            elif meaning == "error":
                result = "Scan finished. Some files could not be read (not yours, or in use)."
            else:
                result = "No threats found."
            self._scan.update(running=False, found=[f.__dict__ for f in found], result=result,
                              elapsed=int(time.time() - self._scan["started"]))
            self._sec = security.status()
        self._run_queue([(security.scan_command(paths), label)], done, stop_on_error=False)

    @Slot()
    def updateDefinitions(self):
        if self.preview:
            return
        def done(ok, out):
            self._sec = security.status()
            self.toast.emit(out.strip().splitlines()[-1] if out.strip() else ("Done." if ok else "Failed."))
        self._run_queue([(["pkexec", ADMIN, "definitions"], "Updating virus definitions")], done)

    @Slot(bool)
    def setRealtime(self, on):
        if self.preview:
            return
        def done(ok, out):
            self._sec = security.status()
            self.toast.emit("Real-time protection is " + ("on." if self._sec.get("realtime") else "off."))
        self._run_queue([(["pkexec", ADMIN, "realtime", "on" if on else "off"],
                          "Turning real-time protection " + ("on" if on else "off"))], done)

    @Slot(bool)
    def setFirewall(self, on):
        if self.preview:
            return
        def done(ok, out):
            self._sec = security.status()
        self._run_queue([(["pkexec", ADMIN, "firewall", "on" if on else "off"], "Firewall")], done)

    @Slot()
    def openQuarantine(self):
        security.QUARANTINE.mkdir(parents=True, exist_ok=True)
        QProcess.startDetached("xdg-open", [str(security.QUARANTINE)])

    # ------------------------------------------------------------------ updates
    @Slot()
    def checkUpdates(self):
        if self.preview:
            return
        exe = shutil.which("xos-updates") or str(HERE.parents[1] / "bin/xos-updates")

        def done(ok, out):
            try:
                res = json.loads(out[out.index("{"):])
            except ValueError:
                res = {"updates": [], "errors": ["Could not check for updates."]}
            self._updates = {"checked": True, "updates": res["updates"], "errors": res["errors"],
                             "summary": updates.summary(res["updates"]), "when": time.strftime("%H:%M")}
        self._run_queue([([exe, "check", "--json"], "Checking for updates")], done)

    @Slot()
    def installUpdates(self):
        if self.preview:
            return
        cmds = updates.install_commands()
        if not cmds:
            self.toast.emit("No update tool found.")
            return

        def done(ok, out):
            self.toast.emit("Updates installed." if ok else "Some updates could not be installed. See details.")
            self._updates = dict(self._updates, checked=False)
            QTimer.singleShot(500, self.checkUpdates)
        self._run_queue([(c, "Installing system updates" if c[0] == "pkcon" else "Updating apps") for c in cmds],
                        done, stop_on_error=False)

    def _timer_enabled(self) -> bool:
        if self.preview or not shutil.which("systemctl"):
            return True
        r = subprocess.run(["systemctl", "--user", "is-enabled", "xos-update-check.timer"],
                           capture_output=True, text=True)
        return r.stdout.strip() in ("enabled", "static", "enabled-runtime")

    @Slot(bool)
    def setAutoUpdates(self, on):
        if not self.preview:
            subprocess.run(["systemctl", "--user", "enable" if on else "disable", "--now", "xos-update-check.timer"],
                           capture_output=True)
        self._auto_updates = self._timer_enabled()
        self.changed.emit()

    # ------------------------------------------------------------------ this pc
    @Slot()
    def refreshDrives(self):
        if not self.preview:
            self._drives = thispc.drives()
            self.changed.emit()

    @Slot(str, str)
    def openDrive(self, path, mountpoint):
        if self.preview:
            return
        if not mountpoint:
            ok, res = thispc.mount(path)
            if not ok:
                self.toast.emit("Could not open the drive: " + res)
                return
            mountpoint = res
            self.refreshDrives()
        QProcess.startDetached("xdg-open", [mountpoint])

    @Slot(str)
    def ejectDrive(self, path):
        if self.preview:
            return
        ok, msg = thispc.eject(path)
        self.toast.emit("You can remove the drive now." if ok else "Could not eject: " + msg)
        self.refreshDrives()

    @Slot()
    def moreSettings(self):
        QProcess.startDetached("systemsettings", [])

    def _tick(self):
        if self._scan.get("running"):
            self._scan["elapsed"] = int(time.time() - self._scan["started"])
            self.changed.emit()
        elif self._page == "this-pc" and not self.preview and self.proc is None:
            new = thispc.drives()
            if new != self._drives:
                self._drives = new
                self.changed.emit()

    # ------------------------------------------------------------------ preview data
    def _demo(self):
        now = time.time()
        self._sec = {"antivirus": True, "definitions": {"installed": True, "updated": int(now - 86400), "age_days": 1},
                     "realtime": False, "firewall": True, "secureBoot": True, "quarantine": 0}
        self._updates = {"checked": True, "summary": "3 updates available, including 2 security updates.",
                         "errors": [], "when": "09:41", "updates": [
                             {"kind": "system", "name": "firefox-esr", "new": "140.5.0esr-1", "old": "140.4.0esr-1", "security": True},
                             {"kind": "system", "name": "linux-image-amd64", "new": "6.12.57-1", "old": "6.12.48-1", "security": True},
                             {"kind": "app", "name": "org.telegram.desktop", "new": "5.8.3", "old": "", "security": False}]}
        self._drives = [
            {"path": "/dev/nvme0n1p5", "name": "X-OS", "kind": "system", "fstype": "ext4", "size": 260e9,
             "used": 18e9, "free": 230e9, "mountpoint": "/", "removable": False, "percent": 7},
            {"path": "/dev/nvme0n1p3", "name": "Windows", "kind": "windows", "fstype": "ntfs", "size": 250e9,
             "used": 141e9, "free": 109e9, "mountpoint": "/media/u/Windows", "removable": False, "percent": 56},
            {"path": "/dev/sda1", "name": "XOS_amir", "kind": "removable", "fstype": "exfat", "size": 32e9,
             "used": 4e9, "free": 28e9, "mountpoint": "/media/u/XOS_amir", "removable": True, "percent": 13},
            {"path": "/dev/sr0", "name": "VENUSDVD", "kind": "optical", "fstype": "iso9660", "size": 4e9,
             "used": None, "free": None, "mountpoint": "", "removable": True, "percent": None}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="tweaks", choices=PAGES)
    ap.add_argument("--preview", metavar="PNG", help="render with demo data and exit")
    ap.add_argument("--theme", default="dark", choices=("dark", "light"))
    a = ap.parse_args()
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("X-OS Settings")
    app.setDesktopFileName(APP_IDS[a.page])          # the dock shows the matching X-OS icon
    if not QIcon.themeName() or QIcon.themeName() == "hicolor":
        QIcon.setThemeName("breeze-dark")
    engine = QQmlApplicationEngine()
    engine.addImageProvider("glyph", GlyphProvider())
    engine.addImportPath("/usr/share/xos/qml")
    engine.addImportPath(str(HERE.parents[1] / "ui/qml"))
    backend = Backend(a.page, preview=bool(a.preview))
    engine.setInitialProperties({"backend": backend, "themeMode": a.theme})
    engine.load(QUrl.fromLocalFile(str(HERE / "qml/Settings.qml")))
    if not engine.rootObjects():
        return 1
    if a.preview:
        win = engine.rootObjects()[0]
        QTimer.singleShot(1200, lambda: (win.grabWindow().save(a.preview), app.quit()))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
