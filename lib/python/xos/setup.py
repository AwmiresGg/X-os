"""X-OS Setup backend: the choices made in the Windows-style setup wizard.

The wizard (installer/xos-setup) runs in the live session before installation:
language, keyboard layouts, Wi-Fi, appearance, apps. Choices are stored as JSON in
/run/xos/setup-choices.json; the installer copies them into the new system, where
``apply_to_target`` and the first-boot service (xos-firstboot) apply them.

Wi-Fi passwords are never written to this file or passed on a command line: the
connection is created through NetworkManager's D-Bus API, which stores the secret
in its root-only keyfile; the installer's networkcfg module copies it over.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

CHOICES_PATH = Path("/run/xos/setup-choices.json")
TARGET_CHOICES_PATH = Path("/etc/xos/setup-choices.json")

LANGUAGES = [  # (locale, native name)
    ("en_US.UTF-8", "English"),
    ("fa_IR.UTF-8", "فارسی"),
    ("ar_EG.UTF-8", "العربية"),
    ("tr_TR.UTF-8", "Türkçe"),
    ("de_DE.UTF-8", "Deutsch"),
    ("fr_FR.UTF-8", "Français"),
    ("es_ES.UTF-8", "Español"),
    ("ru_RU.UTF-8", "Русский"),
]
RTL_LOCALES = {"fa_IR.UTF-8", "ar_EG.UTF-8"}

KEYBOARDS = [  # (xkb layout, xkb variant, label)
    ("us", "", "English (US)"),
    ("ir", "", "Persian (فارسی)"),
    ("ir", "pes_keypad", "Persian, with Persian keypad"),
    ("gb", "", "English (UK)"),
    ("ara", "", "Arabic"),
    ("tr", "", "Turkish Q"),
    ("de", "", "German"),
    ("fr", "", "French"),
    ("es", "", "Spanish"),
    ("ru", "", "Russian"),
]

WALLPAPERS = {
    "x-os-dark": "/usr/share/wallpapers/X-OS/x-os-dark.svg",
    "x-os-light": "/usr/share/wallpapers/X-OS/x-os-light.svg",
}

_LAYOUT_RE = re.compile(r"^[a-z]{2,8}$")
_VARIANT_RE = re.compile(r"^[a-z0-9_]{0,32}$")


@dataclass
class Choices:
    locale: str = "en_US.UTF-8"
    keyboard: list[list[str]] = field(default_factory=lambda: [["us", ""]])   # [[layout, variant], ...]
    theme: str = "dark"                    # dark | light | auto
    wallpaper: str = "x-os-dark"
    browsers: list[str] = field(default_factory=lambda: ["firefox"])
    wifi_ssid: str | None = None           # informational only, never a password

    def validate(self) -> "Choices":
        from .browsers import BROWSERS
        if self.locale not in {l for l, _ in LANGUAGES}:
            raise ValueError(f"unsupported locale {self.locale!r}")
        if not 1 <= len(self.keyboard) <= 4:
            raise ValueError("choose between 1 and 4 keyboard layouts")
        for layout, variant in self.keyboard:
            if not _LAYOUT_RE.match(layout) or not _VARIANT_RE.match(variant):
                raise ValueError(f"invalid keyboard layout {layout!r}/{variant!r}")
        if self.theme not in ("dark", "light", "auto"):
            raise ValueError("theme must be dark, light or auto")
        if self.wallpaper not in WALLPAPERS:
            raise ValueError(f"unknown wallpaper {self.wallpaper!r}")
        unknown = set(self.browsers) - set(BROWSERS)
        if unknown:
            raise ValueError(f"unknown browsers {sorted(unknown)}")
        return self

    @property
    def rtl(self) -> bool:
        return self.locale in RTL_LOCALES

    def xkb(self) -> tuple[str, str]:
        """XKB layout and variant strings, e.g. ('us,ir', ',')."""
        return ",".join(l for l, _ in self.keyboard), ",".join(v for _, v in self.keyboard)


def save(c: Choices, path: Path = CHOICES_PATH) -> None:
    c.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(c), indent=2, ensure_ascii=False) + "\n")


def load(path: Path) -> Choices:
    data = json.loads(path.read_text())
    known = Choices.__dataclass_fields__
    return Choices(**{k: v for k, v in data.items() if k in known}).validate()


# --------------------------------------------------------------------------- live session actions
def keyboard_session_commands(c: Choices) -> list[list[str]]:
    """Switch the running session's layouts (Plasma reads kxkbrc; X11/console via localectl)."""
    layouts, variants = c.xkb()
    cmds = [
        ["kwriteconfig6", "--file", "kxkbrc", "--group", "Layout", "--key", "Use", "true"],
        ["kwriteconfig6", "--file", "kxkbrc", "--group", "Layout", "--key", "LayoutList", layouts],
        ["kwriteconfig6", "--file", "kxkbrc", "--group", "Layout", "--key", "VariantList", variants],
        # Alt+Shift switches layouts, as on Windows.
        ["kwriteconfig6", "--file", "kxkbrc", "--group", "Layout", "--key", "Options", "grp:alt_shift_toggle"],
        # Plasma only applies Options when ResetOldOptions is set.
        ["kwriteconfig6", "--file", "kxkbrc", "--group", "Layout", "--key", "ResetOldOptions", "true"],
        # Same signal System Settings sends; KWin reloads the layouts on it.
        ["dbus-send", "--session", "--type=signal", "/Layouts", "org.kde.keyboard.reloadConfig"],
    ]
    return cmds


def appearance_commands(c: Choices) -> list[list[str]]:
    """Per-user commands that apply theme + wallpaper in a Plasma session."""
    scheme = {"dark": "BreezeDark", "light": "BreezeLight", "auto": "BreezeDark"}[c.theme]
    deco = "__aurorae__svg__XOS-Light" if c.theme == "light" else "__aurorae__svg__XOS-Dark"
    return [
        ["plasma-apply-colorscheme", scheme],
        ["plasma-apply-wallpaperimage", WALLPAPERS[c.wallpaper]],
        ["kwriteconfig6", "--file", "kwinrc", "--group", "org.kde.kdecoration2", "--key", "theme", deco],
        ["dbus-send", "--session", "--type=method_call", "--dest=org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
    ]


def target_system_commands(c: Choices) -> list[list[str]]:
    """System-wide settings for the installed system (run as root inside the target)."""
    layouts, variants = c.xkb()
    return [
        ["sed", "-i", f"s/^# *{re.escape(c.locale.split('.')[0])}\\.UTF-8 UTF-8/{c.locale} UTF-8/", "/etc/locale.gen"],
        ["locale-gen"],
        ["update-locale", f"LANG={c.locale}"],
        ["sh", "-c", "cat > /etc/default/keyboard <<EOF\nXKBMODEL=pc105\n"
                     f"XKBLAYOUT={layouts}\nXKBVARIANT={variants}\nXKBOPTIONS=grp:alt_shift_toggle\nBACKSPACE=guess\nEOF"],
        ["setupcon", "--save-only"],
    ]


def run_all(cmds: list[list[str]]) -> list[str]:
    log = []
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            log.append(f"{'ok ' if r.returncode == 0 else 'ERR'} {' '.join(cmd[:3])}")
        except (OSError, subprocess.TimeoutExpired) as e:
            log.append(f"ERR {' '.join(cmd[:3])}: {e}")
    return log


# --------------------------------------------------------------------------- Wi-Fi
def wifi_networks() -> list[dict]:
    """Visible Wi-Fi networks, strongest first (SSID, signal %, security, in-use)."""
    r = subprocess.run(["nmcli", "-t", "-e", "yes", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi",
                        "list", "--rescan", "auto"], capture_output=True, text=True, timeout=30)
    return parse_wifi_list(r.stdout)


def parse_wifi_list(text: str) -> list[dict]:
    best: dict[str, dict] = {}
    for line in text.splitlines():
        parts = re.split(r"(?<!\\):", line)
        if len(parts) < 4:
            continue
        in_use, ssid, signal, security = (p.replace("\\:", ":").replace("\\\\", "\\") for p in parts[:4])
        if not ssid:
            continue                                   # hidden networks are joined by name, not listed
        net = {"ssid": ssid, "signal": int(signal or 0), "security": security or "open",
               "secure": bool(security and security != "--"), "connected": in_use == "*"}
        if ssid not in best or net["signal"] > best[ssid]["signal"] or net["connected"]:
            best[ssid] = net
    return sorted(best.values(), key=lambda n: (not n["connected"], -n["signal"]))


def wifi_connection_settings(ssid: str, password: str | None) -> dict:
    """NetworkManager connection settings (plain Python types) for AddAndActivateConnection."""
    s: dict = {
        "connection": {"id": ssid, "type": "802-11-wireless", "autoconnect": True},
        "802-11-wireless": {"ssid": list(ssid.encode()), "mode": "infrastructure"},
        "ipv4": {"method": "auto"},
        "ipv6": {"method": "auto"},
    }
    if password:
        if not 8 <= len(password) <= 63:
            raise ValueError("Wi-Fi passwords (WPA) are 8 to 63 characters long")
        s["802-11-wireless"]["security"] = "802-11-wireless-security"
        s["802-11-wireless-security"] = {"key-mgmt": "wpa-psk", "psk": password}
    return s


def wifi_connect(ssid: str, password: str | None) -> None:
    """Create and activate a Wi-Fi connection via NetworkManager D-Bus (secret never on argv)."""
    import dbus  # python3-dbus, present on the ISO
    bus = dbus.SystemBus()
    nm = dbus.Interface(bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager"),
                        "org.freedesktop.NetworkManager")
    devices = [d for d in nm.GetDevices()
               if bus.get_object("org.freedesktop.NetworkManager", d).Get(
                   "org.freedesktop.NetworkManager.Device", "DeviceType",
                   dbus_interface="org.freedesktop.DBus.Properties") == 2]   # NM_DEVICE_TYPE_WIFI
    if not devices:
        raise RuntimeError("no Wi-Fi adapter found")
    settings = wifi_connection_settings(ssid, password)
    settings["802-11-wireless"]["ssid"] = dbus.ByteArray(ssid.encode())
    nm.AddAndActivateConnection(settings, devices[0], "/")
