"""X-OS Updates: system packages (Debian, through PackageKit) and Flatpak apps.

* check: refresh package lists (PackageKit lets the logged-in user do this without a
  password), then list upgradable Debian packages and Flatpak updates.
* install: ``pkcon update`` (PackageKit asks for the administrator password through polkit)
  and ``flatpak update``.
* A daily user timer runs ``xos-updates check --notify`` and shows a notification when
  updates are available. Updates are never installed without the user.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, asdict

APT_LINE = re.compile(r"^(?P<name>[^/\s]+)/(?P<origin>\S+)\s+(?P<new>\S+)\s+(?P<arch>\S+)"
                      r"(?:\s+\[upgradable from: (?P<old>[^\]]+)\])?")
SECURITY_HINT = re.compile(r"security", re.I)


@dataclass
class Update:
    kind: str           # system | app
    name: str
    new: str
    old: str = ""
    origin: str = ""
    security: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def parse_apt_upgradable(text: str) -> list[Update]:
    out = []
    for line in text.splitlines():
        m = APT_LINE.match(line.strip())
        if not m:
            continue                      # "Listing..." and warnings
        out.append(Update("system", m["name"], m["new"], m["old"] or "", m["origin"],
                          bool(SECURITY_HINT.search(m["origin"]))))
    return out


def parse_flatpak_updates(text: str) -> list[Update]:
    """`flatpak remote-ls --updates --columns=application,version` output (tab separated)."""
    out = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split("\t")]
        if not parts or not parts[0] or parts[0].lower() == "application id" or "." not in parts[0]:
            continue
        out.append(Update("app", parts[0], parts[1] if len(parts) > 1 else ""))
    return out


def _run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def check(refresh: bool = True) -> dict:
    """Returns {"updates": [...], "errors": [...]}; never raises."""
    errors, ups = [], []
    if refresh and shutil.which("pkcon"):
        rc, out = _run(["pkcon", "refresh", "--noninteractive"])
        if rc not in (0, 5):                        # 5 = nothing useful to do
            errors.append("Could not refresh the package lists (offline?)")
    rc, out = _run(["apt", "list", "--upgradable"], timeout=120)
    if rc == 0:
        ups += parse_apt_upgradable(out)
    if shutil.which("flatpak"):
        rc, out = _run(["flatpak", "remote-ls", "--updates", "--columns=application,version"], timeout=300)
        if rc == 0:
            ups += parse_flatpak_updates(out)
    return {"updates": [u.to_dict() for u in ups], "errors": errors}


def install_commands(system: bool = True, apps: bool = True) -> list[list[str]]:
    cmds = []
    if system and shutil.which("pkcon"):
        cmds.append(["pkcon", "update", "--noninteractive", "-y"])
    if apps and shutil.which("flatpak"):
        cmds.append(["flatpak", "update", "-y", "--noninteractive"])
    return cmds


def summary(updates: list[dict]) -> str:
    n = len(updates)
    if n == 0:
        return "X-OS is up to date."
    sec = sum(1 for u in updates if u.get("security"))
    s = f"{n} update{'s' if n != 1 else ''} available"
    return s + (f", including {sec} security update{'s' if sec != 1 else ''}." if sec else ".")
