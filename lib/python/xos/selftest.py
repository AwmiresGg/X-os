"""X-OS boot self-test.

Runs at boot when requested (kernel parameter ``xos.selftest=1`` or the QEMU
fw_cfg entry ``opt/org.x-os.selftest`` used by the automated VM tests), checks
that the core system came up correctly, writes a JSON report and prints a
machine-readable summary to the serial console.

Each check returns (status, detail) with status in PASS | FAIL | SKIP.
SKIP is used when a check does not apply to the hardware (no Wi-Fi adapter,
no battery); it is never used to hide a failure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from . import hardware, profiles

FWCFG = Path("/sys/firmware/qemu_fw_cfg/by_name/opt/org.x-os.selftest/raw")


def _sh(*cmd: str, timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def requested() -> str | None:
    """Return the requested mode ('report' or 'poweroff') or None."""
    cmdline = Path("/proc/cmdline").read_text().split()
    if "xos.selftest=1" in cmdline:
        return "report"
    subprocess.run(["modprobe", "-q", "qemu_fw_cfg"], check=False)
    if FWCFG.exists():
        v = FWCFG.read_text().strip()
        return "poweroff" if v == "poweroff" else "report"
    return None


def check_os_release():
    data = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    ok = data.get("ID") == "x-os" and data.get("ID_LIKE") == "debian"
    return ("PASS" if ok else "FAIL"), data.get("PRETTY_NAME", "?").strip('"')


def check_systemd(own_unit: str = "xos-selftest.service", timeout: int = 300):
    # This check runs inside a boot-time oneshot unit, so `is-system-running --wait`
    # would wait for this very unit (deadlock). Instead wait until the only queued
    # job left is our own, then inspect the state.
    deadline = time.monotonic() + timeout
    state = "unknown"
    while time.monotonic() < deadline:
        _, state = _sh("systemctl", "is-system-running")
        state = state.splitlines()[-1] if state else "unknown"
        if state != "starting":
            break
        _, jobs = _sh("systemctl", "list-jobs", "--no-legend", "--plain")
        others = [ln.split()[1] for ln in jobs.splitlines() if len(ln.split()) > 1 and ln.split()[1] != own_unit]
        if not others:
            state = "running"
            break
        time.sleep(2)
    if state == "running":
        return "PASS", "running (all units started)"
    _, failed = _sh("systemctl", "--failed", "--no-legend", "--plain")
    units = [ln.split()[0] for ln in failed.splitlines() if ln.strip()]
    return "FAIL", f"{state}; failed units: {', '.join(units) or 'none listed'}"


def check_live_medium():
    mounts = Path("/proc/mounts").read_text()
    if "/run/live/medium" in mounts:
        return "PASS", "live medium mounted at /run/live/medium"
    if Path("/run/live").exists():
        return "FAIL", "/run/live exists but medium is not mounted"
    return "SKIP", "installed system (not a live session)"


def check_live_user():
    """Live sessions must have the live user (created by live-config + user-setup)."""
    if not Path("/run/live/medium").exists():
        return "SKIP", "installed system"
    import pwd
    cmdline = Path("/proc/cmdline").read_text().split()
    name = next((a.split("=", 1)[1] for a in cmdline if a.startswith("live-config.username=")), "xos")
    try:
        u = pwd.getpwnam(name)
    except KeyError:
        return "FAIL", f"live user {name!r} does not exist (is user-setup installed?)"
    return "PASS", f"{name} (uid {u.pw_uid})"


def check_network_manager():
    rc, out = _sh("systemctl", "is-active", "NetworkManager.service")
    if out != "active":
        return "FAIL", f"NetworkManager is {out}"
    rc, _ = _sh("nm-online", "-s", "-q", "-t", "45", timeout=60)
    _, devs = _sh("nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device")
    if rc == 0:
        return "PASS", "online: " + "; ".join(devs.splitlines())
    return "FAIL", "NetworkManager running but not online: " + "; ".join(devs.splitlines())


def check_dns_config(resolv: Path = Path("/etc/resolv.conf")):
    """Name resolution is configured: /etc/resolv.conf exists (a symlink must not dangle) and
    lists a nameserver. A dangling link to systemd-resolved's stub once left installed
    systems online by IP but unable to resolve any name ("Server Not Found")."""
    if not resolv.exists():
        target = os.readlink(resolv) if resolv.is_symlink() else "missing"
        return "FAIL", f"{resolv} -> {target} does not exist: no DNS"
    servers = [l.split()[1] for l in resolv.read_text().splitlines()
               if l.startswith("nameserver") and len(l.split()) > 1]
    if not servers:
        return "FAIL", f"{resolv} lists no nameserver"
    if "127.0.0.53" in servers:
        rc, out = _sh("systemctl", "is-active", "systemd-resolved.service")
        if out != "active":
            return "FAIL", f"resolv.conf points at systemd-resolved, which is {out}"
    return "PASS", "nameservers: " + ", ".join(servers)


URL_FWCFG = Path("/sys/firmware/qemu_fw_cfg/by_name/opt/org.x-os.selftest-url/raw")


def check_connectivity():
    # The automated VM test runs with an isolated guest network and passes a local
    # endpoint via fw_cfg; elsewhere the public Debian mirror is used.
    url = URL_FWCFG.read_text().strip() if URL_FWCFG.exists() else "https://deb.debian.org/debian/"
    rc, out = _sh("curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "20", url, timeout=30)
    return ("PASS", f"{url} -> HTTP {out}") if rc == 0 and out.startswith(("2", "3")) else ("FAIL", f"{url}: {out[-200:]}")


def check_desktop_session(timeout: int = 420):
    """Desktop images: a graphical (Wayland/X11) user session must come up.

    Waits because a cold Plasma start is slow on old PCs and in emulation. On
    failure the display manager's log is attached so the cause is visible on the
    serial console.
    """
    if not Path("/usr/lib/systemd/system/sddm.service").exists():
        return "SKIP", "no display manager (core image)"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _, out = _sh("loginctl", "list-sessions", "--no-legend")
        for line in out.splitlines():
            sid = line.split()[0] if line.split() else ""
            if not sid:
                continue
            _, props = _sh("loginctl", "show-session", sid, "-p", "Type", "-p", "Class", "-p", "State", "-p", "Name")
            p = dict(kv.split("=", 1) for kv in props.splitlines() if "=" in kv)
            if p.get("Type") in ("wayland", "x11") and p.get("Class") == "user":
                return "PASS", f"{p['Type']} session for {p.get('Name')} ({p.get('State')})"
        time.sleep(5)
    _, log = _sh("journalctl", "-b", "-u", "sddm", "--no-pager", "-o", "cat", "-n", "12")
    return "FAIL", "no graphical user session; sddm log: " + " | ".join(log.splitlines()[-12:])


SB_VAR = Path("/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c")


def check_secure_boot():
    """Informational: reports the firmware's Secure Boot state (never a failure by itself)."""
    if not Path("/sys/firmware/efi").is_dir():
        return "SKIP", "BIOS boot (no Secure Boot)"
    try:
        data = SB_VAR.read_bytes()
    except OSError:
        return "SKIP", "Secure Boot variable not available"
    return "PASS", "enabled (booted through signed shim + GRUB + kernel)" if data[-1:] == b"\x01" else "disabled"


def check_firewall():
    if not shutil.which("ufw"):
        return "FAIL", "ufw not installed"
    rc, out = _sh("ufw", "status")
    return ("PASS", out.splitlines()[0]) if "Status: active" in out else ("FAIL", out[:200])


def check_hardware(hw):
    issues = []
    if not hw["cpu"]["x86_64"]:
        issues.append("CPU is not x86_64")
    if not hw["disks"]:
        issues.append("no disks detected")
    detail = (f"{hw['cpu']['model']} ({hw['cpu']['threads']} threads), "
              f"{hw['memory']['total_bytes'] / 2**30:.1f} GiB RAM, firmware={hw['firmware']}, "
              f"{len(hw['devices'])} devices, {len(hw['problems'])} without driver")
    return ("FAIL" if issues else "PASS"), "; ".join(issues) or detail


def check_disk_tools():
    rc, out = _sh("lsblk", "-J", "-o", "NAME,SIZE,TYPE,FSTYPE")
    if rc != 0:
        return "FAIL", out
    n = len(json.loads(out).get("blockdevices", []))
    missing = [t for t in ("parted", "mkfs.ext4", "mkfs.ntfs", "mkfs.exfat", "mkfs.btrfs", "mkfs.xfs",
                           "mkfs.vfat", "cryptsetup", "smartctl", "udisksctl") if not shutil.which(t)]
    return ("FAIL", "missing: " + ", ".join(missing)) if missing else ("PASS", f"{n} block devices; all tools present")


def check_wifi(hw):
    wifi = [n for n in hw["network"] if n["type"] == "wifi"]
    if not wifi:
        return "SKIP", "no Wi-Fi adapter present"
    rc, out = _sh("nmcli", "-t", "-f", "SSID", "device", "wifi", "list", "--rescan", "yes", timeout=40)
    return ("PASS", f"{len(out.splitlines())} networks visible") if rc == 0 else ("FAIL", out[:200])


def check_bluetooth():
    if not Path("/sys/class/bluetooth").exists() or not any(Path("/sys/class/bluetooth").iterdir()):
        return "SKIP", "no Bluetooth adapter present"
    rc, out = _sh("systemctl", "is-active", "bluetooth.service")
    return ("PASS", "bluetoothd active") if out == "active" else ("FAIL", f"bluetooth.service {out}")


def run(mode: str = "report", out_dir: Path = Path("/var/log")) -> dict:
    t0 = time.monotonic()
    hw = hardware.probe()
    prof, reasons = profiles.recommend(hw)
    checks = {
        "os-release": check_os_release,
        "systemd": check_systemd,
        "live-medium": check_live_medium,
        "live-user": check_live_user,
        "network-manager": check_network_manager,
        "dns": check_dns_config,
        "connectivity": check_connectivity,
        "firewall": check_firewall,
        "secure-boot": check_secure_boot,
        "desktop-session": check_desktop_session,
        "hardware": lambda: check_hardware(hw),
        "disk-tools": check_disk_tools,
        "wifi": lambda: check_wifi(hw),
        "bluetooth": check_bluetooth,
    }
    results = {}
    for name, fn in checks.items():
        try:
            status, detail = fn()
        except Exception as e:  # a crashing check is a failing check
            status, detail = "FAIL", f"{type(e).__name__}: {e}"
        results[name] = {"status": status, "detail": detail}
    overall = "FAIL" if any(r["status"] == "FAIL" for r in results.values()) else "PASS"
    report = {
        "overall": overall, "mode": mode, "seconds": round(time.monotonic() - t0, 1),
        "uptime_seconds": float(Path("/proc/uptime").read_text().split()[0]),
        "recommended_profile": prof, "profile_reasons": reasons,
        "checks": results, "hardware": hw,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "xos-selftest.json").write_text(json.dumps(report, indent=2))
    return report


def format_summary(report: dict) -> str:
    lines = ["XOS-SELFTEST-BEGIN"]
    for name, r in report["checks"].items():
        lines.append(f"XOS-SELFTEST {r['status']:4} {name}: {r['detail']}")
    for d in report["hardware"].get("problems", []):
        lines.append(f"XOS-SELFTEST device {d['status']}: {d['category']} | {d['vendor']} {d['name']} "
                     f"[{d['bus']} {d['address']} {d['vendor_id']}:{d['device_id']}]")
    lines.append(f"XOS-SELFTEST profile: {report['recommended_profile']} ({'; '.join(report['profile_reasons'])})")
    lines.append(f"XOS-SELFTEST uptime at report: {report['uptime_seconds']:.0f}s")
    lines.append(f"XOS-SELFTEST-RESULT: {report['overall']}")
    return "\n".join(lines)


def console_write(text: str) -> None:
    for dev in ("/dev/ttyS0", "/dev/console"):
        try:
            fd = os.open(dev, os.O_WRONLY | os.O_NOCTTY | os.O_NONBLOCK)
        except OSError:
            continue
        try:
            os.write(fd, (text.replace("\n", "\r\n") + "\r\n").encode())
        finally:
            os.close(fd)
        return
