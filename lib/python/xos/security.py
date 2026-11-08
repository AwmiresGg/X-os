"""X-OS Security: antivirus (ClamAV), firewall and protection status.

* Scans run as the user with ``clamscan`` (no root needed for your own files). Infected files
  are moved to a private quarantine folder, never deleted silently.
* Virus definitions are updated by ``freshclam`` (the clamav-freshclam service). Note: the
  ClamAV update servers refuse some countries; then definitions stay at the version that came
  with X-OS until an update succeeds (a VPN helps) - the page says so instead of hiding it.
* Real-time protection (clamd + clamonacc) is optional and off by default: it keeps the whole
  signature database in memory (about 1 GB of RAM).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

CLAM_DB = Path("/var/lib/clamav")
QUARANTINE = Path.home() / ".local/share/xos/quarantine"
UFW_CONF = Path("/etc/ufw/ufw.conf")
ONACC_UNITS = ("clamav-daemon.service", "clamav-clamonacc.service")
# Where real-time protection watches (user data, not the whole system: keeps it light).
ONACC_PATHS = ("/home",)

FOUND_RE = re.compile(r"^(?P<path>.+): (?P<sig>\S+) FOUND$")
MOVED_RE = re.compile(r"^(?P<path>.+): moved to '(?P<dest>.+)'$")


@dataclass
class Detection:
    path: str
    signature: str
    quarantined_to: str = ""


def quick_scan_paths(home: Path | None = None) -> list[str]:
    """Where malware usually lands: downloads, desktop, documents, temp folders."""
    home = home or Path.home()
    cands = [home / "Downloads", home / "Desktop", home / "Documents", Path("/tmp"), home / ".local/share/applications"]
    return [str(p) for p in cands if p.is_dir()]


def scan_command(paths: list[str], quarantine: Path = QUARANTINE) -> list[str]:
    if not paths:
        raise ValueError("nothing to scan")
    return ["clamscan", "--recursive", "--infected", "--stdout", "--no-summary",
            "--exclude-dir=^/proc", "--exclude-dir=^/sys", "--exclude-dir=^/dev",
            f"--exclude-dir={re.escape(str(quarantine))}",
            f"--move={quarantine}", "--", *paths]


def parse_scan_output(text: str) -> list[Detection]:
    found: dict[str, Detection] = {}
    for line in text.splitlines():
        line = line.rstrip()
        if m := FOUND_RE.match(line):
            found[m["path"]] = Detection(m["path"], m["sig"])
        elif m := MOVED_RE.match(line):
            if m["path"] in found:
                found[m["path"]].quarantined_to = m["dest"]
    return list(found.values())


def scan_exit_meaning(code: int) -> str:
    """clamscan: 0 clean, 1 virus found, 2 error (some files unreadable, or no database)."""
    return {0: "clean", 1: "threats"}.get(code, "error")


def definitions(db: Path = CLAM_DB) -> dict:
    """Installed signature databases and how old they are."""
    files = [p for p in db.glob("*.c[lv]d")] if db.is_dir() else []
    if not files:
        return {"installed": False, "updated": 0, "age_days": None, "files": []}
    newest = max(p.stat().st_mtime for p in files)
    return {"installed": True, "updated": int(newest), "age_days": int((time.time() - newest) // 86400),
            "files": sorted(p.name for p in files)}


def firewall_enabled(conf: Path = UFW_CONF) -> bool | None:
    """Readable without root: ENABLED=yes in ufw.conf (None when ufw is not installed)."""
    try:
        for line in conf.read_text().splitlines():
            if line.strip().startswith("ENABLED="):
                return line.split("=", 1)[1].strip().strip('"').lower() == "yes"
    except OSError:
        return None
    return False


def _active(unit: str) -> bool:
    if not shutil.which("systemctl"):
        return False
    return subprocess.run(["systemctl", "is-active", "--quiet", unit]).returncode == 0


def realtime_enabled() -> bool:
    return all(_active(u) for u in ONACC_UNITS)


def secure_boot() -> bool | None:
    efi = Path("/sys/firmware/efi/efivars")
    if not efi.is_dir():
        return None
    for f in efi.glob("SecureBoot-*"):
        try:
            return f.read_bytes()[-1] == 1
        except OSError:
            return None
    return None


def status() -> dict:
    d = definitions()
    return {
        "antivirus": shutil.which("clamscan") is not None,
        "definitions": d,
        "realtime": realtime_enabled(),
        "firewall": firewall_enabled(),
        "secureBoot": secure_boot(),
        "quarantine": len(list(QUARANTINE.glob("*"))) if QUARANTINE.is_dir() else 0,
    }


# ----------------------------------------------------------------- root half (xos-admin)
CLAMD_CONF = Path("/etc/clamav/clamd.conf")
MARK_BEGIN, MARK_END = "# >>> X-OS real-time protection", "# <<< X-OS real-time protection"


def onaccess_conf(text: str, enable: bool) -> str:
    """clamd.conf with the X-OS on-access block added or removed (idempotent)."""
    out, skip = [], False
    for line in text.splitlines():
        if line.strip() == MARK_BEGIN:
            skip = True
            continue
        if line.strip() == MARK_END:
            skip = False
            continue
        if not skip:
            out.append(line)
    if enable:
        out += [MARK_BEGIN, "OnAccessPrevention no", "OnAccessExcludeUname clamav",
                "OnAccessExcludeRootUID yes"]
        out += [f"OnAccessIncludePath {p}" for p in ONACC_PATHS]
        out.append(MARK_END)
    return "\n".join(out) + "\n"


def set_realtime(enable: bool, conf: Path = CLAMD_CONF, run: bool = True) -> list[str]:
    log = []
    if conf.exists():
        conf.write_text(onaccess_conf(conf.read_text(), enable))
        log.append(f"{conf}: on-access {'enabled' if enable else 'removed'}")
    if run:
        verb = ["enable", "--now"] if enable else ["disable", "--now"]
        for unit in ONACC_UNITS:
            r = subprocess.run(["systemctl", *verb, unit], capture_output=True, text=True)
            log.append(f"{' '.join(verb)} {unit}: {'ok' if r.returncode == 0 else r.stderr.strip()}")
    return log


def update_definitions() -> tuple[bool, str]:
    """Run freshclam once (the service normally does it hourly). Root."""
    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "stop", "clamav-freshclam.service"], capture_output=True)
    r = subprocess.run(["freshclam", "--stdout"], capture_output=True, text=True, timeout=1800)
    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "start", "clamav-freshclam.service"], capture_output=True)
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0:
        return True, "Virus definitions are up to date."
    if re.search(r"403|blocked|forbidden", out, re.I):
        return False, ("The ClamAV update server refused this connection (it blocks some countries). "
                       "Try again with a VPN connected.")
    return False, "Could not update virus definitions: " + (out.splitlines()[-1] if out else f"exit {r.returncode}")


def restore_from_quarantine(name: str, dest_dir: Path) -> Path:
    src = QUARANTINE / os.path.basename(name)
    if not src.is_file():
        raise FileNotFoundError(name)
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / src.name
    shutil.move(str(src), target)
    return target
