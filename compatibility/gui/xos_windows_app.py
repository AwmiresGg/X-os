#!/usr/bin/python3
"""X-OS "Windows app" dialog — opened by double-clicking a .exe/.msi/.bat/.msix file.

    xos-windows-app FILE
    xos-windows-app FILE --preview OUT.png [--state ready|working|done|nowine]   (screenshots)

Shows what the file is and how well it is expected to run (compatibility database), asks for
consent, sets up Wine if needed (pkexec xos-compat-setup --yes), then installs into a
per-application prefix with live progress and offers to open the installed app.
All logic comes from xos.compat (unit-tested); this file only drives the steps.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in ("/usr/lib/xos/python", str(HERE.parents[1] / "lib/python")):
    if Path(p, "xos").is_dir():
        sys.path.insert(0, p)
        break

from PySide6.QtCore import Property, QObject, QProcess, QProcessEnvironment, QTimer, QUrl, Signal, Slot  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402,F401

from xos import compat  # noqa: E402

LAUNCHERS = Path.home() / ".local/share/applications/wine"


class Backend(QObject):
    changed = Signal()

    def __init__(self, path: str, preview_state: str = ""):
        super().__init__()
        self.path = str(Path(path).resolve())
        self._state = "ready"          # ready | setup | working | done | failed
        self._log: list[str] = []
        self._step = ""
        self._launchers: list[dict] = []
        self._error = ""
        self.det = compat.detect(self.path)
        apps = compat.load_db(compat.default_db_path())
        self.entry = compat.match(apps, self.path, self.det.sha256)
        self.plan = compat.plan(self.det, self.entry, Path.home())
        self._wine = bool(shutil.which("wine"))
        self._queue: list[list[str]] = []
        self._before: set[str] = set()
        self.proc: QProcess | None = None
        self.silent = False             # the dialog runs installers interactively; tests use silent
        if preview_state:
            self._preview(preview_state)

    # ------------------------------------------------------------------ properties for QML
    @Property("QVariantMap", constant=True)
    def info(self):
        p, alt = self.plan, (self.entry or {}).get("native_alternative")
        return {
            "name": p["name"], "file": Path(self.path).name, "format": p["format"].upper(),
            "arch": self.det.arch or "", "size": f"{self.det.size / 1e6:.1f} MB",
            "sha": self.det.sha256[:16], "rating": p["rating"], "canInstall": p["can_install"],
            "verified": bool((self.entry or {}).get("verified_on_xos")),
            "warnings": p["warnings"], "alternative": alt["note"] if alt else "",
            "prefix": p["prefix"].replace(str(Path.home()), "~"),
        }

    @Property(str, constant=True)
    def iconUrl(self):
        """X-OS 'windows-apps' glyph, tinted for the dark theme, as a data URL."""
        for base in (Path("/usr/share/xos/icons/xos"), HERE.parents[1] / "icons/xos"):
            f = base / "symbolic/apps/windows-apps.svg"
            if f.exists():
                from urllib.parse import quote
                return "data:image/svg+xml;utf8," + quote(f.read_text().replace("currentColor", "#ECEEF1"))
        return ""

    @Property(str, notify=changed)
    def state(self):
        return self._state

    @Property(bool, notify=changed)
    def wineReady(self):
        return self._wine

    @Property(str, notify=changed)
    def step(self):
        return self._step

    @Property(str, notify=changed)
    def log(self):
        return "\n".join(self._log[-200:])

    @Property("QVariantList", notify=changed)
    def launchers(self):
        return self._launchers

    @Property(str, notify=changed)
    def error(self):
        return self._error

    # ------------------------------------------------------------------ actions
    @Slot()
    def install(self):
        if self._state not in ("ready", "failed") or not self.plan["can_install"]:
            return
        self._error = ""
        if not self._wine:
            self._state, self._step = "setup", "Setting up Windows support (Wine)…"
            self.changed.emit()
            self._queue = [["pkexec", "/usr/sbin/xos-compat-setup", "--yes"]]
            self._run_next(after=self._start_install)
            return
        self._start_install()

    def _start_install(self):
        self._wine = bool(shutil.which("wine"))
        try:
            self._queue = compat.install_steps(self.plan, self.path, shutil.which("wine") or "wine",
                                               shutil.which("winetricks"), silent=self.silent)
        except ValueError as e:
            return self._fail(str(e))
        Path(self.plan["prefix"]).mkdir(parents=True, exist_ok=True)
        self._before = {str(p) for p in LAUNCHERS.rglob("*.desktop")} if LAUNCHERS.exists() else set()
        self._state = "working"
        self.changed.emit()
        self._run_next(after=self._finish)

    def _run_next(self, after):
        if not self._queue:
            return after()
        cmd = self._queue.pop(0)
        self._step = self._describe(cmd)
        self._log.append("$ " + " ".join(shlex.quote(c) for c in cmd))
        self.changed.emit()
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        if cmd[0] != "pkexec":
            for k, v in compat.env_for(self.plan, {}).items():
                env.insert(k, v)
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)

        def done(code, _status):
            if code != 0:
                return self._fail(f"“{self._step}” failed (exit code {code}).")
            self._run_next(after)
        self.proc.finished.connect(done)
        self.proc.errorOccurred.connect(lambda e: self._fail(f"could not start {cmd[0]}") if e == QProcess.ProcessError.FailedToStart else None)
        self.proc.start(cmd[0], cmd[1:])

    def _read(self):
        text = bytes(self.proc.readAllStandardOutput()).decode(errors="replace")
        self._log += [ln for ln in text.splitlines() if ln.strip() and "fixme:" not in ln]
        self.changed.emit()

    def _describe(self, cmd):
        joined = " ".join(cmd)
        if "xos-compat-setup" in joined:
            return "Setting up Windows support (Wine)…"
        if "wineboot" in joined:
            return "Preparing a private Windows environment for this app…"
        if "winetricks" in joined:
            return "Installing required Windows components…"
        if "winecfg" in joined:
            return "Configuring the Windows version…"
        return f"Running {Path(self.path).name}… (follow the installer's own window)"

    def _finish(self):
        (Path(self.plan["prefix"]) / "xos-app.json").write_text(__import__("json").dumps(self.plan, indent=2))
        QTimer.singleShot(1500, self._collect_launchers)

    def _collect_launchers(self):
        now = {str(p) for p in LAUNCHERS.rglob("*.desktop")} if LAUNCHERS.exists() else set()
        found = []
        for f in sorted(now - self._before):
            name = Path(f).stem
            if any(w in name.lower() for w in ("uninstall", "help", "readme", "website")):
                continue
            found.append({"name": name, "file": f})
        self._launchers = found
        self._state, self._step = "done", ""
        self.changed.emit()

    def _fail(self, msg):
        self._state, self._error = "failed", msg
        self.changed.emit()

    @Slot(str)
    def openLauncher(self, desktop_file):
        if desktop_file.startswith(str(LAUNCHERS)):
            QProcess.startDetached("kioclient", ["exec", desktop_file])

    @Slot()
    def quit(self):
        if self.proc and self.proc.state() != QProcess.ProcessState.NotRunning:
            return                      # never abandon a running installer
        QGuiApplication.quit()

    # ------------------------------------------------------------------ previews
    def _preview(self, st):
        if st == "nowine":
            self._wine = False
        elif st == "working":
            self._wine, self._state = True, "working"
            self._step = "Running 7z2409-x64.exe… (follow the installer's own window)"
            self._log = ["$ wine wineboot --init", "wine: created the configuration directory",
                         "$ wine /home/xos/Downloads/7z2409-x64.exe"]
        elif st == "done":
            self._wine, self._state = True, "done"
            self._launchers = [{"name": "7-Zip File Manager", "file": ""}]
        else:
            self._wine = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--preview", metavar="PNG")
    ap.add_argument("--state", default="ready")
    ap.add_argument("--test-install", metavar="PNG", help="tests: consent + silent install, screenshot when done")
    a = ap.parse_args()
    if not Path(a.file).is_file():
        print(f"not a file: {a.file}", file=sys.stderr)
        return 2
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("X-OS Windows App Installer")
    app.setDesktopFileName("xos-windows-app")
    backend = Backend(a.file, a.state if a.preview else "")
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(HERE.parents[1] / "ui/qml"))
    engine.addImportPath("/usr/share/xos/qml")
    engine.setInitialProperties({"backend": backend})
    engine.load(QUrl.fromLocalFile(str(HERE / "WindowsApp.qml")))   # same dir when installed
    if not engine.rootObjects():
        return 1
    if a.test_install:
        win = engine.rootObjects()[0]
        backend.silent = True
        QTimer.singleShot(500, backend.install)

        def check():
            if backend.state in ("done", "failed"):
                win.grabWindow().save(a.test_install)
                print("TEST-RESULT", backend.state, backend.error, [x["name"] for x in backend.launchers])
                app.exit(0 if backend.state == "done" else 1)
        poll = QTimer()
        poll.timeout.connect(check)
        poll.start(1000)
        return app.exec()
    if a.preview:
        win = engine.rootObjects()[0]

        def grab():
            try:
                win.grabWindow().save(a.preview)
            finally:
                app.quit()
        QTimer.singleShot(1500, grab)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
