"""This PC: the drives and partitions a person cares about, like Windows' "This PC".

Reads ``lsblk --json`` (no root). Hides what is not user storage: EFI/boot partitions,
swap, the live medium's own squashfs, loop devices and partitions without a filesystem.
Mounting goes through udisks (``udisksctl mount``), which asks for a password only when
policy requires it.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass

LSBLK_COLS = "NAME,PATH,TYPE,LABEL,PARTLABEL,FSTYPE,SIZE,FSUSED,FSAVAIL,MOUNTPOINTS,RM,HOTPLUG,TRAN,MODEL,PARTTYPENAME"
HIDDEN_FS = {"swap", "squashfs", "iso9660_live", "crypto_LUKS", "LVM2_member", "linux_raid_member", ""}
HIDDEN_MOUNTS = ("/boot", "/boot/efi", "/efi", "/run/live/medium", "/usr/lib/live/mount")
WINDOWS_FS = {"ntfs", "ntfs3", "exfat", "vfat"}


@dataclass
class Drive:
    path: str
    name: str            # what the user sees
    kind: str            # system | windows | data | removable | optical
    fstype: str
    size: int
    used: int | None
    free: int | None
    mountpoint: str
    removable: bool

    def to_dict(self) -> dict:
        d = asdict(self)
        d["percent"] = round(100 * self.used / self.size) if self.used is not None and self.size else None
        return d


def _first_mount(dev: dict) -> str:
    mps = [m for m in (dev.get("mountpoints") or []) if m]
    return mps[0] if mps else ""


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_lsblk(text: str) -> list[Drive]:
    data = json.loads(text)
    out: list[Drive] = []

    def visit(dev: dict, disk: dict):
        for child in dev.get("children") or []:
            visit(child, disk if dev.get("type") != "disk" else dev)
        if dev.get("type") not in ("part", "disk", "rom", "crypt", "lvm"):
            return
        if dev.get("type") == "disk" and dev.get("children"):
            return                                   # the partitions are listed instead
        fs = (dev.get("fstype") or "").lower()
        mp = _first_mount(dev)
        ptype = (dev.get("parttypename") or "").lower()
        if dev.get("type") == "rom":
            if fs in ("iso9660", "udf") and mp not in HIDDEN_MOUNTS:
                out.append(Drive(dev["path"], dev.get("label") or "DVD Drive", "optical", fs,
                                 _int(dev.get("size")) or 0, None, None, mp, True))
            return
        if fs in HIDDEN_FS or mp in HIDDEN_MOUNTS or mp.startswith("/run/live"):
            return
        if "efi system" in ptype or "microsoft reserved" in ptype or "bios boot" in ptype:
            return
        if "windows recovery" in ptype or (dev.get("label") or "").lower() in ("recovery", "winre_drv"):
            return
        removable = bool(dev.get("rm")) or bool(dev.get("hotplug")) or (disk or {}).get("tran") == "usb"
        if mp == "/":
            kind, name = "system", "X-OS"
        elif removable:
            kind, name = "removable", dev.get("label") or (disk or {}).get("model") or "USB Drive"
        elif fs in WINDOWS_FS and ("basic data" in ptype or fs.startswith("ntfs")):
            kind, name = "windows", dev.get("label") or "Windows"
        else:
            kind, name = "data", dev.get("label") or dev.get("partlabel") or "Local Disk"
        size = _int(dev.get("size")) or 0
        out.append(Drive(dev["path"], name.strip(), kind, fs, size, _int(dev.get("fsused")),
                         _int(dev.get("fsavail")), mp, removable))

    for dev in data.get("blockdevices", []):
        visit(dev, None)
    order = {"system": 0, "windows": 1, "data": 2, "removable": 3, "optical": 4}
    return sorted(out, key=lambda d: (order[d.kind], d.name.lower()))


def drives() -> list[dict]:
    if not shutil.which("lsblk"):
        return []
    r = subprocess.run(["lsblk", "--json", "--bytes", "-o", LSBLK_COLS], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [d.to_dict() for d in parse_lsblk(r.stdout)]


def human(n: int | None) -> str:
    if n is None:
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1000 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}".replace(".0 ", " ")
        n /= 1000
    return ""


def mount(path: str) -> tuple[bool, str]:
    """Mount through udisks; returns (ok, mountpoint or error)."""
    if not path.startswith("/dev/"):
        return False, "not a device"
    r = subprocess.run(["udisksctl", "mount", "--no-user-interaction", "-b", path], capture_output=True, text=True)
    if r.returncode != 0 and "NotAuthorized" in r.stderr:
        r = subprocess.run(["udisksctl", "mount", "-b", path], capture_output=True, text=True)
    if r.returncode == 0:
        # "Mounted /dev/sdb1 at /media/user/LABEL"
        return True, r.stdout.strip().rsplit(" at ", 1)[-1].rstrip(".")
    return False, r.stderr.strip() or r.stdout.strip()


def eject(path: str) -> tuple[bool, str]:
    if not path.startswith("/dev/"):
        return False, "not a device"
    subprocess.run(["udisksctl", "unmount", "-b", path], capture_output=True, text=True)
    pk = subprocess.run(["lsblk", "-no", "PKNAME", path], capture_output=True, text=True).stdout.strip()
    disk = f"/dev/{pk.splitlines()[0]}" if pk else path      # power off the whole drive
    r = subprocess.run(["udisksctl", "power-off", "-b", disk], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr.strip() or "ejected")
