"""System status and actions for the X-OS menu bar, Control Center and dock.

Every value comes from a real system interface; every action calls a real one:

| Area        | Read                                   | Write / action                                |
|-------------|----------------------------------------|-----------------------------------------------|
| Battery     | /sys/class/power_supply                | -                                             |
| Network     | nmcli (NetworkManager)                 | nmcli radio wifi on/off                       |
| Bluetooth   | /sys/class/bluetooth + rfkill          | rfkill block/unblock bluetooth                |
| Volume      | wpctl (PipeWire)                       | wpctl set-volume / set-mute                   |
| Brightness  | /sys/class/backlight                   | logind Session.SetBrightness (no root needed) |
| Appearance  | kdeglobals                             | plasma-apply-colorscheme                      |
| Power       | -                                      | systemctl suspend/reboot/poweroff, loginctl lock-session, Plasma logout |

Parsing is kept in pure functions so it can be unit-tested with recorded output.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


def _run(cmd: list[str], timeout: float = 5) -> tuple[int, str]:
    if not shutil.which(cmd[0]):
        return 127, ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


# --------------------------------------------------------------------------- battery
@dataclass
class Battery:
    present: bool = False
    percent: int = 0
    charging: bool = False
    on_ac: bool = True
    source: str = "AC"               # "Battery" | "AC"

    def icon(self) -> str:
        if not self.present:
            return "power"
        if self.charging:
            return "battery-charging"
        if self.percent <= 10:
            return "battery-empty"
        if self.percent <= 30:
            return "battery-low"
        if self.percent <= 75:
            return "battery-medium"
        return "battery-full"


def read_battery(root: Path = Path("/")) -> Battery:
    base = root / "sys/class/power_supply"
    b = Battery()
    if not base.is_dir():
        return b
    total_now = total_full = 0
    statuses = []
    ac_online = None
    for dev in sorted(base.iterdir()):
        typ = _read(dev / "type")
        if typ == "Mains":
            ac_online = _read(dev / "online") == "1"
        elif typ == "Battery" and _read(dev / "scope") != "Device":    # skip mouse/keyboard batteries
            now = _int(_read(dev / "energy_now") or _read(dev / "charge_now"))
            full = _int(_read(dev / "energy_full") or _read(dev / "charge_full"))
            if full:
                total_now += now
                total_full += full
            elif (cap := _int(_read(dev / "capacity"))) is not None:
                total_now += cap
                total_full += 100
            statuses.append(_read(dev / "status"))
    if total_full:
        b.present = True
        b.percent = max(0, min(100, round(100 * total_now / total_full)))
        b.charging = "Charging" in statuses
        b.on_ac = ac_online if ac_online is not None else (b.charging or "Full" in statuses)
        b.source = "AC" if b.on_ac else "Battery"
    return b


def _read(p: Path) -> str:
    try:
        return p.read_text().strip()
    except OSError:
        return ""


def _int(s: str):
    return int(s) if s.lstrip("-").isdigit() else None


# --------------------------------------------------------------------------- network
@dataclass
class Network:
    state: str = "unknown"           # connected | connecting | disconnected | asleep | unknown
    kind: str = "none"               # wifi | ethernet | vpn | none
    name: str = ""                   # connection name / SSID
    signal: int = 0                  # Wi-Fi signal 0-100
    wifi_enabled: bool = False
    wifi_present: bool = False       # a Wi-Fi adapter exists (radio state alone says nothing)
    vpn: bool = False

    def icon(self) -> str:
        if self.state != "connected":
            return "wifi-off" if not self.wifi_enabled and self.kind != "ethernet" else "network-off"
        if self.kind == "ethernet":
            return "ethernet"
        level = 0 if self.signal < 25 else 1 if self.signal < 50 else 2 if self.signal < 75 else 3
        return f"wifi-{level}"


def parse_nmcli_general(text: str) -> tuple[str, bool]:
    """`nmcli -t -f STATE,WIFI general` -> (state, wifi_enabled)."""
    line = text.strip().splitlines()[0] if text.strip() else ""
    parts = line.split(":")
    state = parts[0] if parts else "unknown"
    if state.startswith("connected"):
        state = "connected"
    return state or "unknown", len(parts) > 1 and parts[1] == "enabled"


def parse_nmcli_active(text: str) -> tuple[str, str, bool]:
    """`nmcli -t -f NAME,TYPE connection show --active` -> (kind, name, vpn_active)."""
    kind, name, vpn = "none", "", False
    for line in text.splitlines():
        parts = re.split(r"(?<!\\):", line)
        if len(parts) < 2:
            continue
        cname, ctype = parts[0].replace("\\:", ":"), parts[1]
        if ctype in ("vpn", "wireguard"):
            vpn = True
        elif ctype == "802-11-wireless" and kind != "ethernet":
            kind, name = "wifi", cname
        elif ctype == "802-3-ethernet":
            kind, name = "ethernet", cname
    return kind, name, vpn


def parse_wifi_signal(text: str) -> int:
    """`nmcli -t -f IN-USE,SIGNAL device wifi list --rescan no` -> signal of the active AP."""
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[0] == "*" and parts[1].isdigit():
            return int(parts[1])
    return 0


def parse_has_wifi(text: str) -> bool:
    """`nmcli -t -f TYPE device` -> whether any Wi-Fi device exists."""
    return any(line.strip() == "wifi" for line in text.splitlines())


def read_network() -> Network:
    n = Network()
    rc, out = _run(["nmcli", "-t", "-f", "STATE,WIFI", "general"])
    if rc != 0:
        return n
    n.state, n.wifi_enabled = parse_nmcli_general(out)
    _, devs = _run(["nmcli", "-t", "-f", "TYPE", "device"])
    n.wifi_present = parse_has_wifi(devs)
    _, act = _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"])
    n.kind, n.name, n.vpn = parse_nmcli_active(act)
    if n.kind == "wifi":
        _, wl = _run(["nmcli", "-t", "-f", "IN-USE,SIGNAL", "device", "wifi", "list", "--rescan", "no"])
        n.signal = parse_wifi_signal(wl)
    return n


def set_wifi(enabled: bool) -> bool:
    return _run(["nmcli", "radio", "wifi", "on" if enabled else "off"])[0] == 0


# --------------------------------------------------------------------------- bluetooth
@dataclass
class Bluetooth:
    present: bool = False
    powered: bool = False


def parse_rfkill_bluetooth(text: str) -> bool | None:
    """`rfkill -rn -o TYPE,SOFT,HARD` -> True if any bluetooth radio is unblocked."""
    seen = None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "bluetooth":
            unblocked = parts[1] == "unblocked" and parts[2] == "unblocked"
            seen = bool(seen) or unblocked
    return seen


def read_bluetooth(root: Path = Path("/")) -> Bluetooth:
    base = root / "sys/class/bluetooth"
    present = base.is_dir() and any(p.name.startswith("hci") for p in base.iterdir())
    if not present:
        return Bluetooth()
    _, out = _run(["rfkill", "-rn", "-o", "TYPE,SOFT,HARD"])
    powered = parse_rfkill_bluetooth(out)
    return Bluetooth(present=True, powered=bool(powered))


def set_bluetooth(enabled: bool) -> bool:
    return _run(["rfkill", "unblock" if enabled else "block", "bluetooth"])[0] == 0


# --------------------------------------------------------------------------- audio
@dataclass
class Audio:
    available: bool = False
    volume: int = 0          # percent
    muted: bool = False

    def icon(self) -> str:
        if not self.available or self.muted or self.volume == 0:
            return "volume-mute"
        return "volume-low" if self.volume < 34 else "volume-medium" if self.volume < 67 else "volume-high"


def parse_wpctl_volume(text: str) -> tuple[int, bool] | None:
    """`wpctl get-volume @DEFAULT_AUDIO_SINK@` -> "Volume: 0.45 [MUTED]"."""
    m = re.search(r"Volume:\s*([0-9.]+)", text)
    if not m:
        return None
    return round(float(m.group(1)) * 100), "[MUTED]" in text


def read_audio() -> Audio:
    rc, out = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    parsed = parse_wpctl_volume(out) if rc == 0 else None
    if not parsed:
        return Audio()
    return Audio(True, *parsed)


def set_volume(percent: int) -> bool:
    percent = max(0, min(100, int(percent)))
    ok = _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent / 100:.2f}"])[0] == 0
    if ok and percent > 0:
        _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"])
    return ok


def set_muted(muted: bool) -> bool:
    return _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0"])[0] == 0


# --------------------------------------------------------------------------- brightness
@dataclass
class Brightness:
    available: bool = False
    device: str = ""
    percent: int = 100
    maximum: int = 0


def read_brightness(root: Path = Path("/")) -> Brightness:
    base = root / "sys/class/backlight"
    if not base.is_dir():
        return Brightness()
    devs = sorted(base.iterdir(), key=lambda d: (_read(d / "type") != "firmware", d.name))
    for d in devs:
        mx, cur = _int(_read(d / "max_brightness")), _int(_read(d / "brightness"))
        if mx and cur is not None:
            return Brightness(True, d.name, round(100 * cur / mx), mx)
    return Brightness()


def set_brightness(percent: int, b: Brightness | None = None) -> bool:
    """Through logind, which lets the active session change its backlight without root."""
    b = b or read_brightness()
    if not b.available:
        return False
    value = max(1, round(b.maximum * max(1, min(100, int(percent))) / 100))
    return _run(["busctl", "call", "org.freedesktop.login1", "/org/freedesktop/login1/session/auto",
                 "org.freedesktop.login1.Session", "SetBrightness", "ssu", "backlight", b.device,
                 str(value)])[0] == 0


# --------------------------------------------------------------------------- trash
@dataclass
class Trash:
    full: bool = False


def read_trash(home: Path | None = None) -> Trash:
    files = (home or Path.home()) / ".local/share/Trash/files"
    try:
        return Trash(any(True for _ in files.iterdir()))
    except OSError:
        return Trash(False)


# --------------------------------------------------------------------------- appearance + power
DECORATION = {True: "__aurorae__svg__XOS-Dark", False: "__aurorae__svg__XOS-Light"}


def set_appearance(dark: bool) -> bool:
    """Colour scheme + matching X-OS window decoration, applied live."""
    ok = _run(["plasma-apply-colorscheme", "XOSDark" if dark else "XOSLight"], timeout=15)[0] == 0
    _run(["kwriteconfig6", "--file", "kwinrc", "--group", "org.kde.kdecoration2", "--key", "theme", DECORATION[dark]])
    _run(["dbus-send", "--session", "--type=method_call", "--dest=org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"])
    return ok


POWER_ACTIONS = {
    "lock": ["loginctl", "lock-session"],
    "sleep": ["systemctl", "suspend"],
    "restart": ["systemctl", "reboot"],
    "shutdown": ["systemctl", "poweroff"],
    # Plasma's own logout (saves the session); falls back to terminating the session.
    "logout": ["dbus-send", "--session", "--type=method_call", "--dest=org.kde.LogoutPrompt",
               "/LogoutPrompt", "org.kde.LogoutPrompt.promptLogout"],
}


def power_action(name: str) -> bool:
    cmd = POWER_ACTIONS[name]
    return _run(cmd, timeout=10)[0] == 0


def snapshot() -> dict:
    bat, net, aud = read_battery(), read_network(), read_audio()
    return {
        "battery": asdict(bat) | {"icon": bat.icon()},
        "network": asdict(net) | {"icon": net.icon()},
        "bluetooth": asdict(read_bluetooth()),
        "audio": asdict(aud) | {"icon": aud.icon()},
        "brightness": asdict(read_brightness()),
    }
