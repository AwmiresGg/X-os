#!/usr/bin/python3
"""X-OS Setup - the first screen after booting the X-OS USB stick.

Steps: language -> keyboard -> Wi-Fi -> appearance -> apps -> Try / Install.
"Install" saves the choices and starts the Calamares installer (disk + account).

    xos-setup-gui                 # normal (live session)
    xos-setup-gui --demo          # fake Wi-Fi data, no system changes (development)
    xos-setup-gui --demo --page 2 --screenshot out.png
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

for p in ("/usr/lib/xos/python", str(Path(__file__).resolve().parents[2] / "lib/python")):
    if Path(p, "xos").is_dir():
        sys.path.insert(0, p)
        break

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot  # noqa: E402
from PySide6.QtGui import QGuiApplication, QIcon  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402,F401  (registers the window type)

from xos import browsers, setup  # noqa: E402

HERE = Path(__file__).resolve().parent
DEMO_WIFI = [
    {"ssid": "Home-5G", "signal": 92, "security": "WPA2 WPA3", "secure": True, "connected": False},
    {"ssid": "Office", "signal": 71, "security": "WPA2", "secure": True, "connected": False},
    {"ssid": "Cafe Guest", "signal": 48, "security": "--", "secure": False, "connected": False},
    {"ssid": "Neighbor", "signal": 22, "security": "WPA2", "secure": True, "connected": False},
]


def _asset(rel: str) -> str:
    for base in (Path("/usr/share/xos"), HERE.parents[1]):
        p = base / rel
        if p.exists():
            return QUrl.fromLocalFile(str(p)).toString()
    return ""


class Backend(QObject):
    wifiChanged = Signal()
    busyChanged = Signal()

    def __init__(self, demo: bool):
        super().__init__()
        self._demo = demo
        self._wifi: list[dict] = []
        self._busy = False

    # ---- static data for the UI
    @Property("QVariantList", constant=True)
    def languages(self):
        return [{"locale": l, "name": n, "rtl": l in setup.RTL_LOCALES} for l, n in setup.LANGUAGES]

    @Property("QVariantList", constant=True)
    def keyboards(self):
        return [{"layout": l, "variant": v, "label": t} for l, v, t in setup.KEYBOARDS]

    @Property("QVariantList", constant=True)
    def wallpapers(self):
        out = []
        for k, installed in setup.WALLPAPERS.items():
            src = installed if Path(installed).exists() else str(HERE.parents[1] / f"themes/liquid-glass/wallpapers/x-os-{k}.svg")
            out.append({"id": k, "url": QUrl.fromLocalFile(src).toString()})
        return out

    @Property("QVariantList", constant=True)
    def browserList(self):
        return [{"id": b.id, "name": b.name, "source": b.repo_uri.split("/")[2],
                 "preinstalled": b.preinstalled_fallback or ""} for b in browsers.BROWSERS.values()]

    @Property(str, constant=True)
    def logo(self):
        return _asset("icons/xos/brand/x-os-logo.svg") or _asset("brand/x-os-logo.svg")

    @Property(bool, constant=True)
    def demo(self):
        return self._demo

    # ---- Wi-Fi
    @Property("QVariantList", notify=wifiChanged)
    def wifi(self):
        return self._wifi

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    def _set_busy(self, v):
        self._busy = v
        self.busyChanged.emit()

    @Slot()
    def scanWifi(self):
        if self._demo:
            self._wifi = DEMO_WIFI
        else:
            try:
                self._wifi = setup.wifi_networks()
            except (OSError, subprocess.SubprocessError):
                self._wifi = []
        self.wifiChanged.emit()

    @Slot(str, str, result=str)
    def connectWifi(self, ssid, password):
        """Returns "" on success or an error message."""
        try:
            if not self._demo:
                setup.wifi_connect(ssid, password or None)
            else:
                setup.wifi_connection_settings(ssid, password or None)   # validates the password length
            self._wifi = [dict(n, connected=n["ssid"] == ssid) for n in self._wifi]
            self.wifiChanged.emit()
            return ""
        except Exception as e:  # shown to the user, never contains the password
            return str(e)

    # ---- live changes
    @Slot("QVariantList")
    def applyKeyboard(self, layouts):
        if self._demo:
            return
        c = setup.Choices(keyboard=[[k["layout"], k["variant"]] for k in layouts])
        setup.run_all(setup.keyboard_session_commands(c))

    @Slot(str, str)
    def applyAppearance(self, theme, wallpaper):
        if self._demo:
            return
        setup.run_all(setup.appearance_commands(setup.Choices(theme=theme, wallpaper=wallpaper)))

    # ---- finish
    @Slot("QVariantMap", result=str)
    def save(self, data):
        try:
            c = setup.Choices(
                locale=data["locale"],
                keyboard=[[k["layout"], k["variant"]] for k in data["keyboard"]],
                theme=data["theme"], wallpaper=data["wallpaper"],
                browsers=list(data["browsers"]), wifi_ssid=data.get("wifiSsid") or None)
            if not self._demo:
                setup.save(c)
            return ""
        except (ValueError, KeyError, OSError) as e:
            return str(e)

    @Slot(result=str)
    def startInstaller(self):
        if self._demo:
            return "demo mode: the installer is not started"
        exe = shutil.which("calamares")
        if not exe:
            return "installer (calamares) is not available on this medium"
        # Live session: live-config grants the live user passwordless sudo, and the live
        # user's password cannot be typed reliably (pkexec would prompt for it).
        # Elsewhere fall back to pkexec, which asks for an administrator password.
        live = Path("/run/live/medium").is_dir()
        if live and subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0:
            cmd = ["sudo", "-n", "-E", exe]
        else:
            cmd = ["pkexec", exe]
        subprocess.Popen(cmd, start_new_session=True)
        QTimer.singleShot(1500, QGuiApplication.quit)
        return ""

    @Slot()
    def tryXos(self):
        QGuiApplication.quit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--locale", default="")
    ap.add_argument("--screenshot", default="")
    a = ap.parse_args()

    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("X-OS Setup")
    app.setDesktopFileName("xos-setup")
    backend = Backend(a.demo)
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"backend": backend, "startPage": a.page, "startLocale": a.locale})
    engine.load(QUrl.fromLocalFile(str(HERE / "qml/Setup.qml")))
    if not engine.rootObjects():
        return 1
    if backend.logo:
        app.setWindowIcon(QIcon(QUrl(backend.logo).toLocalFile()))
    if a.screenshot:
        win = engine.rootObjects()[0]

        def grab():
            try:
                win.grabWindow().save(a.screenshot)
            finally:
                app.quit()
        QTimer.singleShot(1800, grab)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
