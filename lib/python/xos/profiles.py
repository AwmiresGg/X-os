"""X-OS performance profiles: LITE, BALANCED, PERFORMANCE.

A profile is a declarative set of settings. ``recommend()`` chooses one from a
hardware snapshot; ``plan()`` turns a profile into concrete, reviewable actions;
``apply()`` executes them. Security services are never touched by any profile.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

GiB = 1024 ** 3

# Never disabled by a profile, whatever the profile file says.
PROTECTED_SERVICES = frozenset({
    "ufw.service", "apparmor.service", "systemd-journald.service", "systemd-logind.service",
    "systemd-udevd.service", "NetworkManager.service", "dbus.service", "polkit.service",
    "systemd-timesyncd.service", "unattended-upgrades.service",
})


@dataclass(frozen=True)
class Profile:
    id: str
    title: str
    description: str
    animations: bool
    blur: bool
    animation_speed: float          # KWin AnimationDurationFactor (higher = slower; 0 = off)
    dock_effects: str               # full | reduced | static
    optional_services_off: tuple[str, ...]
    swappiness: int
    zram_percent: int               # compressed RAM swap, % of RAM
    cpu_governor_hint: str          # passed to power-profiles-daemon when present


PROFILES = {
    "lite": Profile(
        "lite", "X-OS Lite", "Minimal effects and background services for 2-4 GB RAM PCs.",
        animations=False, blur=False, animation_speed=0.0, dock_effects="static",
        optional_services_off=("baloo-file.service", "packagekit.service", "cups-browsed.service",
                               "ModemManager.service"),
        swappiness=100, zram_percent=75, cpu_governor_hint="balanced"),
    "balanced": Profile(
        "balanced", "X-OS Balanced", "Normal desktop experience with moderate animations.",
        animations=True, blur=True, animation_speed=1.0, dock_effects="reduced",
        optional_services_off=(), swappiness=60, zram_percent=50, cpu_governor_hint="balanced"),
    "performance": Profile(
        "performance", "X-OS Performance", "Full Liquid Glass effects and gaming optimizations.",
        animations=True, blur=True, animation_speed=0.85, dock_effects="full",
        optional_services_off=(), swappiness=20, zram_percent=25, cpu_governor_hint="performance"),
}


def recommend(hw: dict) -> tuple[str, list[str]]:
    """Return (profile_id, reasons) for a hardware snapshot from xos.hardware.probe()."""
    ram = hw.get("memory", {}).get("total_bytes", 0)
    threads = hw.get("cpu", {}).get("threads", 1)
    gpus = hw.get("gpus", [])
    has_accel = any(g.get("driver") in {"amdgpu", "radeon", "i915", "xe", "nouveau", "nvidia"} for g in gpus)
    reasons = [f"{ram / GiB:.1f} GiB RAM", f"{threads} CPU threads",
               "hardware-accelerated GPU" if has_accel else "no accelerated GPU driver"]
    if ram < 3.5 * GiB or threads <= 2:
        return "lite", reasons + ["below 4 GB RAM or <=2 threads: Lite keeps the desktop responsive"]
    if not has_accel:
        return "lite", reasons + ["software rendering: blur and animations would load the CPU"]
    if ram >= 15 * GiB and threads >= 8:
        return "performance", reasons + ["16 GB+ RAM and 8+ threads: full effects"]
    return "balanced", reasons


def plan(profile_id: str, live: bool = False) -> list[dict]:
    """Concrete actions for a profile. Pure function: nothing is executed."""
    p = PROFILES[profile_id]
    actions = [
        {"kind": "write-state", "path": "/etc/xos/profile", "value": p.id},
        {"kind": "sysctl", "key": "vm.swappiness", "value": p.swappiness},
        {"kind": "zram", "percent": p.zram_percent},
        {"kind": "kwin", "group": "Compositing", "key": "AnimationDurationFactor",
         "value": p.animation_speed if p.animations else 0},
        {"kind": "kwin", "group": "Plugins", "key": "blurEnabled", "value": p.blur},
        {"kind": "xos-shell", "key": "dockEffects", "value": p.dock_effects},
        {"kind": "power-profile", "value": p.cpu_governor_hint},
    ]
    for svc in p.optional_services_off:
        if svc in PROTECTED_SERVICES:           # defence in depth
            continue
        actions.append({"kind": "service-disable", "unit": svc, "runtime_only": live})
    return actions


def apply(profile_id: str, root: Path = Path("/"), live: bool = False, dry_run: bool = False) -> list[str]:
    """Execute plan(); returns a log of what was done. Requires root unless dry_run."""
    log = []
    for a in plan(profile_id, live):
        kind = a["kind"]
        if dry_run:
            log.append(f"would {kind}: {json.dumps(a)}")
            continue
        if kind == "write-state":
            target = root / a["path"].lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(a["value"] + "\n")
            log.append(f"profile set to {a['value']}")
        elif kind == "sysctl":
            conf = root / "etc/sysctl.d/60-xos-profile.conf"
            conf.parent.mkdir(parents=True, exist_ok=True)
            conf.write_text(f"{a['key']} = {a['value']}\n")
            if root == Path("/"):
                _run(["sysctl", "-q", f"{a['key']}={a['value']}"], log)
        elif kind == "zram":
            conf = root / "etc/default/zramswap"
            if conf.exists():
                conf.write_text(f"ALGO=zstd\nPERCENT={a['percent']}\n")
                log.append(f"zram {a['percent']}%")
        elif kind == "kwin":
            # System-wide default; users' own kwinrc still wins (no settings are overridden).
            kw = root / "etc/xdg/kwinrc"
            _ini_set(kw, a["group"], a["key"], str(a["value"]).lower() if isinstance(a["value"], bool) else str(a["value"]))
            log.append(f"kwinrc [{a['group']}] {a['key']}={a['value']}")
        elif kind == "xos-shell":
            _ini_set(root / "etc/xdg/xos-shellrc", "Dock", a["key"], str(a["value"]))
            log.append(f"shell {a['key']}={a['value']}")
        elif kind == "power-profile":
            if root == Path("/") and shutil.which("powerprofilesctl"):
                _run(["powerprofilesctl", "set", "performance" if a["value"] == "performance" else "balanced"], log)
        elif kind == "service-disable":
            if root == Path("/") and shutil.which("systemctl"):
                cmd = ["systemctl", "disable", "--now"] + (["--runtime"] if a["runtime_only"] else []) + [a["unit"]]
                _run(cmd, log, ok_missing=True)
    return log


def current(root: Path = Path("/")) -> str | None:
    for p in (root / "run/xos/profile", root / "etc/xos/profile"):
        try:
            v = p.read_text().strip()
            if v in PROFILES:
                return v
        except OSError:
            pass
    return None


def _ini_set(path: Path, group: str, key: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text().splitlines() if path.exists() else []
    out, in_group, done = [], False, False
    for line in lines:
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            if in_group and not done:
                out.append(f"{key}={value}")
                done = True
            in_group = s == f"[{group}]"
        elif in_group and s.split("=", 1)[0] == key:
            if not done:
                out.append(f"{key}={value}")
                done = True
            continue
        out.append(line)
    if not done:
        if not in_group:
            out.append(f"[{group}]")
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n")


def _run(cmd: list[str], log: list[str], ok_missing: bool = False) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        log.append("ran: " + " ".join(cmd))
    elif not ok_missing:
        log.append(f"failed ({r.returncode}): {' '.join(cmd)}: {r.stderr.strip()}")
