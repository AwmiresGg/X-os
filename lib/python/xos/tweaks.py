"""X-OS Tweaks: configure the whole system for what you are doing right now.

A mode is a declarative, reviewable set of settings, applied in two halves:

* system half (root, through the polkit-guarded helper ``xos-admin``): kernel tunables in
  /etc/sysctl.d/60-xos-tweaks.conf, applied immediately;
* session half (the user, no password): power profile via power-profiles-daemon, KWin
  animation speed and blur, X-OS dock motion.

Nothing here touches security services (firewall, AppArmor, updates) or disables anything
permanently; switching back to Balanced restores the defaults.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

SYSCTL_FILE = Path("/etc/sysctl.d/60-xos-tweaks.conf")
STATE_FILE = Path("/etc/xos/tweaks-mode")

# Kernel keys a mode may set (the helper refuses anything else).
ALLOWED_SYSCTL = frozenset({
    "vm.swappiness", "vm.vfs_cache_pressure", "vm.dirty_ratio", "vm.dirty_background_ratio",
    "vm.max_map_count", "fs.inotify.max_user_watches", "fs.inotify.max_user_instances",
    "kernel.nmi_watchdog",
})


@dataclass(frozen=True)
class Mode:
    id: str
    title: str
    subtitle: str
    glyph: str                         # X-OS symbolic icon name
    power: str                         # power-profiles-daemon: performance | balanced | power-saver
    animation_factor: float            # KWin AnimationDurationFactor (0 = off, 1 = normal)
    blur: bool
    dock_effects: str                  # full | reduced | static
    sysctl: dict = field(default_factory=dict)
    notes: tuple[str, ...] = ()


BASE_SYSCTL = {"vm.swappiness": 60, "vm.vfs_cache_pressure": 100, "vm.max_map_count": 1048576,
               "fs.inotify.max_user_watches": 524288}

MODES: dict[str, Mode] = {m.id: m for m in (
    Mode("balanced", "Balanced", "Everyday use: smooth effects, sensible power use.", "settings",
         "balanced", 0.85, True, "full", dict(BASE_SYSCTL)),
    Mode("gaming", "Gaming", "Maximum frame rate: CPU and GPU at full speed, effects out of the way.",
         "windows-apps", "performance", 0.5, False, "reduced",
         dict(BASE_SYSCTL, **{"vm.swappiness": 10, "vm.max_map_count": 2147483642,
                              "kernel.nmi_watchdog": 0}),
         ("vm.max_map_count is raised for games run through Wine/Proton.",)),
    Mode("creative", "Creative", "Video, photo and 3D work: full speed, more file cache.", "photos",
         "performance", 0.85, True, "full",
         dict(BASE_SYSCTL, **{"vm.swappiness": 10, "vm.vfs_cache_pressure": 50,
                              "vm.dirty_ratio": 30, "vm.dirty_background_ratio": 10})),
    Mode("development", "Development", "Code, builds and virtual machines.", "terminal",
         "performance", 0.7, True, "full",
         dict(BASE_SYSCTL, **{"vm.swappiness": 20, "fs.inotify.max_user_watches": 1048576,
                              "fs.inotify.max_user_instances": 1024})),
    Mode("study", "Office & Study", "Documents, browsing, calls: quiet and cool.", "text-editor",
         "balanced", 1.0, True, "full", dict(BASE_SYSCTL)),
    Mode("battery", "Battery Saver", "Longest battery life: lower power, lighter effects.", "battery-low",
         "power-saver", 0.0, False, "static", dict(BASE_SYSCTL, **{"kernel.nmi_watchdog": 0})),
)}


def sysctl_text(mode_id: str) -> str:
    m = MODES[mode_id]
    lines = [f"# X-OS Tweaks mode: {m.id} (written by xos-admin; switch modes in X-OS Settings)"]
    for k, v in sorted(m.sysctl.items()):
        if k not in ALLOWED_SYSCTL:
            raise ValueError(f"sysctl {k} not allowed")
        lines.append(f"{k} = {int(v)}")
    return "\n".join(lines) + "\n"


def apply_system(mode_id: str, root: Path = Path("/"), run: bool = True) -> list[str]:
    """Root half: write the sysctl file and the state, load it. Called by xos-admin."""
    if mode_id not in MODES:
        raise ValueError(f"unknown mode {mode_id!r}")
    f = root / str(SYSCTL_FILE).lstrip("/")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(sysctl_text(mode_id))
    st = root / str(STATE_FILE).lstrip("/")
    st.parent.mkdir(parents=True, exist_ok=True)
    st.write_text(mode_id + "\n")
    log = [f"wrote {SYSCTL_FILE}"]
    if run and root == Path("/"):
        r = subprocess.run(["sysctl", "-q", "-p", str(f)], capture_output=True, text=True)
        log.append("kernel settings applied" if r.returncode == 0 else f"sysctl: {r.stderr.strip()}")
    return log


def session_commands(mode_id: str) -> list[list[str]]:
    """User half: commands run in the user's session (no privileges)."""
    m = MODES[mode_id]
    cmds = []
    if shutil.which("powerprofilesctl"):
        cmds.append(["powerprofilesctl", "set", m.power])
    cmds += [
        ["kwriteconfig6", "--file", "kdeglobals", "--group", "KDE", "--key", "AnimationDurationFactor",
         str(m.animation_factor)],
        ["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins", "--key", "blurEnabled",
         "true" if m.blur else "false"],
        ["kwriteconfig6", "--file", "xos-shellrc", "--group", "Dock", "--key", "dockEffects", m.dock_effects],
        ["dbus-send", "--session", "--type=method_call", "--dest=org.kde.KWin", "/KWin",
         "org.kde.KWin.reconfigure"],
    ]
    return cmds


def current(root: Path = Path("/")) -> str:
    try:
        v = (root / str(STATE_FILE).lstrip("/")).read_text().strip()
        return v if v in MODES else "balanced"
    except OSError:
        return "balanced"


def power_profiles() -> list[str]:
    """Profiles this machine supports (power-saver/balanced always; performance only on
    CPUs/firmware that offer it)."""
    if not shutil.which("powerprofilesctl"):
        return []
    r = subprocess.run(["powerprofilesctl", "list"], capture_output=True, text=True)
    return re.findall(r"^\s*\*?\s*([a-z-]+):", r.stdout, re.M)
