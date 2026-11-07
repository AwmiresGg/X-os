"""Hardware discovery from kernel interfaces (sysfs, procfs).

Backend for the X-OS Device Manager and the hardware compatibility report.
Reads only; never writes to sysfs. Device enable/disable lives in a separate,
polkit-guarded helper.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

# PCI base class -> Device Manager category (PCI Code and ID Assignment spec).
_PCI_CLASS = {
    0x01: "Storage controllers",
    0x02: "Network adapters",
    0x03: "Graphics adapters",
    0x04: "Audio devices",
    0x05: "Memory controllers",
    0x06: "Bridges",
    0x07: "Communication controllers",
    0x08: "System peripherals",
    0x09: "Input devices",
    0x0C: "USB controllers",
    0x0D: "Wireless controllers",
    0x10: "Encryption controllers",
    0x11: "Signal processing",
    0x12: "Processing accelerators",
}
_PCI_SUBCLASS = {
    (0x02, 0x80): "Network adapters",
    (0x04, 0x03): "Audio devices",
    (0x0C, 0x03): "USB controllers",
    (0x0C, 0x05): "Other hardware",   # SMBus
    (0x0D, 0x11): "Bluetooth adapters",
}
# Classes where "no driver bound" is normal and must not be reported as a problem.
_DRIVERLESS_OK = {0x05, 0x06, 0x08, 0x11, 0xFF}


@dataclass
class Device:
    bus: str
    address: str
    category: str
    vendor_id: str = ""
    device_id: str = ""
    vendor: str = ""
    name: str = ""
    driver: str | None = None
    driver_version: str | None = None
    modalias: str = ""
    status: str = "ok"          # ok | no-driver | disabled | error
    problem: str | None = None
    properties: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _read(path: Path, default: str = "") -> str:
    try:
        return path.read_text(errors="replace").strip()
    except OSError:
        return default


def _driver_of(dev: Path) -> str | None:
    link = dev / "driver"
    if link.is_symlink():
        return os.path.basename(os.readlink(link))
    return None


def _module_version(sys_root: Path, driver: str | None) -> str | None:
    if not driver:
        return None
    for name in (driver, driver.replace("-", "_")):
        v = _read(sys_root / "module" / name / "version")
        if v:
            return v
    return None


# --------------------------------------------------------------------------- id db
class IdDatabase:
    """Minimal parser for pci.ids / usb.ids (shipped by pciutils / usbutils)."""

    def __init__(self, path: Path | None):
        self.vendors: dict[str, str] = {}
        self.devices: dict[tuple[str, str], str] = {}
        if path and path.exists():
            self._load(path)

    def _load(self, path: Path) -> None:
        vendor = None
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or line.startswith("#"):
                    continue
                if line.startswith("C "):        # device-class section: stop
                    break
                if not line.startswith("\t"):
                    vid, _, name = line.partition("  ")
                    vendor = vid.strip().lower()
                    self.vendors[vendor] = name.strip()
                elif vendor and not line.startswith("\t\t"):
                    did, _, name = line.strip().partition("  ")
                    self.devices[(vendor, did.lower())] = name.strip()

    def vendor(self, vid: str) -> str:
        return self.vendors.get(vid.lower(), "")

    def device(self, vid: str, did: str) -> str:
        return self.devices.get((vid.lower(), did.lower()), "")


def _find_ids(root: Path, name: str) -> Path | None:
    for d in ("usr/share/misc", "usr/share/hwdata", "usr/share"):
        p = root / d / name
        if p.exists():
            return p
    return None


# --------------------------------------------------------------------------- probes
def pci_devices(root: Path = Path("/"), ids: IdDatabase | None = None) -> list[Device]:
    sys_root = root / "sys"
    base = sys_root / "bus/pci/devices"
    ids = ids or IdDatabase(_find_ids(root, "pci.ids"))
    out = []
    for dev in sorted(base.iterdir()) if base.is_dir() else []:
        cls = int(_read(dev / "class", "0x000000"), 16)
        base_cls, sub_cls = cls >> 16, (cls >> 8) & 0xFF
        vid = _read(dev / "vendor").removeprefix("0x")
        did = _read(dev / "device").removeprefix("0x")
        category = _PCI_SUBCLASS.get((base_cls, sub_cls)) or _PCI_CLASS.get(base_cls, "Other hardware")
        if base_cls == 0x02 and (dev / "net").is_dir():
            if any((n / "wireless").exists() or (n / "phy80211").exists() for n in (dev / "net").iterdir()):
                category = "Wi-Fi adapters"
        driver = _driver_of(dev)
        d = Device(
            bus="pci", address=dev.name, category=category,
            vendor_id=vid, device_id=did,
            vendor=ids.vendor(vid), name=ids.device(vid, did) or f"PCI device {vid}:{did}",
            driver=driver, driver_version=_module_version(sys_root, driver),
            modalias=_read(dev / "modalias"),
            properties={"class": f"0x{cls:06x}", "revision": _read(dev / "revision")},
        )
        if _read(dev / "enable", "1") == "0" and driver:
            d.status = "disabled"
        if driver is None and base_cls not in _DRIVERLESS_OK:
            d.status, d.problem = "no-driver", "No kernel driver is bound to this device."
        out.append(d)
    return out


def _usb_category(ifclasses: set[str], name: str) -> str:
    if "e0" in ifclasses:
        return "Bluetooth adapters"
    if "0e" in ifclasses:
        return "Cameras"
    if "03" in ifclasses:
        return "Input devices"
    if "08" in ifclasses:
        return "Disk drives"
    if "01" in ifclasses:
        return "Audio devices"
    if "07" in ifclasses:
        return "Printers"
    if "09" in ifclasses:
        return "USB controllers"
    if ifclasses & {"02", "0a"} or "ethernet" in name.lower():
        return "Network adapters"
    return "USB devices"


def usb_devices(root: Path = Path("/"), ids: IdDatabase | None = None) -> list[Device]:
    sys_root = root / "sys"
    base = sys_root / "bus/usb/devices"
    ids = ids or IdDatabase(_find_ids(root, "usb.ids"))
    out = []
    for dev in sorted(base.iterdir()) if base.is_dir() else []:
        if ":" in dev.name or not (dev / "idVendor").exists():
            continue                                  # interfaces are folded into devices
        vid, did = _read(dev / "idVendor"), _read(dev / "idProduct")
        ifaces = [p for p in base.iterdir() if p.name.startswith(dev.name + ":")]
        ifclasses = {_read(i / "bInterfaceClass") for i in ifaces}
        drivers = sorted({d for i in ifaces if (d := _driver_of(i)) and d != "usbfs"})
        name = _read(dev / "product") or ids.device(vid, did) or f"USB device {vid}:{did}"
        d = Device(
            bus="usb", address=dev.name, category=_usb_category(ifclasses, name),
            vendor_id=vid, device_id=did,
            vendor=_read(dev / "manufacturer") or ids.vendor(vid), name=name,
            driver=",".join(drivers) or None,
            properties={"speed_mbps": _read(dev / "speed"), "usb_version": _read(dev / "version")},
        )
        if vid == "1d6b":                             # Linux Foundation root hubs
            d.category = "USB controllers"
        elif not drivers and ifclasses - {"09"}:
            d.status, d.problem = "no-driver", "No kernel driver claimed any interface."
        out.append(d)
    return out


def input_devices(root: Path = Path("/")) -> list[Device]:
    """Classify input devices from /proc/bus/input/devices."""
    text = _read(root / "proc/bus/input/devices")
    out = []
    for block in text.split("\n\n"):
        info = {}
        for line in block.splitlines():
            if len(line) > 3 and line[1] == ":":
                key, val = line[0], line[3:]
                info.setdefault(key, []).append(val)
        if "N" not in info:
            continue
        name = info["N"][0].split("=", 1)[-1].strip('"')
        handlers = " ".join(v for v in info.get("H", []))
        props = " ".join(info.get("B", []))
        lname = name.lower()
        if "touchpad" in lname or "trackpad" in lname or ("synaptics" in lname and "mouse" not in lname):
            cat = "Touchpads"
        elif "mouse" in handlers or re.search(r"\bmouse\b", lname):
            cat = "Mice"
        elif "kbd" in handlers and "EV=12001" in props.replace(" ", "") or "keyboard" in lname:
            cat = "Keyboards"
        else:
            continue
        sysfs = info.get("S", [""])[0].split("=", 1)[-1]
        out.append(Device(bus="input", address=sysfs, category=cat, name=name, driver="evdev"))
    return out


def block_devices(root: Path = Path("/")) -> list[dict]:
    base = root / "sys/block"
    out = []
    for dev in sorted(base.iterdir()) if base.is_dir() else []:
        if dev.name.startswith(("loop", "ram", "zram", "dm-", "sr", "md")):
            continue
        sectors = int(_read(dev / "size", "0") or 0)
        if sectors == 0:                     # empty card readers, unattached virtual disks
            continue
        rotational = _read(dev / "queue/rotational", "0") == "1"
        removable = _read(dev / "removable", "0") == "1"
        transport = "nvme" if dev.name.startswith("nvme") else (
            "usb" if "/usb" in os.path.realpath(dev) else ("virtio" if dev.name.startswith("vd") else "sata/scsi"))
        kind = "NVMe SSD" if transport == "nvme" else ("HDD" if rotational else "SSD")
        if removable or transport == "usb":
            kind = "Removable storage"
        if transport == "virtio":
            kind = "Virtual disk"
        out.append({
            "name": dev.name, "size_bytes": sectors * 512, "kind": kind, "transport": transport,
            "model": _read(dev / "device/model"), "removable": removable,
            "partitions": sorted(p.name for p in dev.iterdir() if p.name.startswith(dev.name)),
        })
    return out


def network_interfaces(root: Path = Path("/")) -> list[dict]:
    base = root / "sys/class/net"
    out = []
    for dev in sorted(base.iterdir()) if base.is_dir() else []:
        if dev.name == "lo":
            continue
        wireless = (dev / "wireless").exists() or (dev / "phy80211").exists()
        physical = (dev / "device").exists()
        speed = _read(dev / "speed")
        out.append({
            "name": dev.name,
            "type": "wifi" if wireless else ("ethernet" if physical else "virtual"),
            "mac": _read(dev / "address"),
            "state": _read(dev / "operstate"),
            "carrier": _read(dev / "carrier") == "1",
            "speed_mbps": int(speed) if speed.lstrip("-").isdigit() and int(speed) > 0 else None,
            "driver": _driver_of(dev / "device") if physical else None,
        })
    return out


def batteries(root: Path = Path("/")) -> list[dict]:
    base = root / "sys/class/power_supply"
    out = []
    for dev in sorted(base.iterdir()) if base.is_dir() else []:
        if _read(dev / "type") != "Battery":
            continue
        full = _read(dev / "energy_full") or _read(dev / "charge_full")
        design = _read(dev / "energy_full_design") or _read(dev / "charge_full_design")
        health = round(100 * int(full) / int(design)) if full.isdigit() and design.isdigit() and int(design) else None
        out.append({
            "name": dev.name, "status": _read(dev / "status"),
            "capacity_percent": int(c) if (c := _read(dev / "capacity")).isdigit() else None,
            "health_percent": health,
            "manufacturer": _read(dev / "manufacturer"), "model": _read(dev / "model_name"),
        })
    return out


def cpu_info(root: Path = Path("/")) -> dict:
    text = _read(root / "proc/cpuinfo")
    model, vendor, flags, threads = "", "", set(), 0
    for line in text.splitlines():
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key == "processor":
            threads += 1
        elif key == "model name" and not model:
            model = val
        elif key == "vendor_id" and not vendor:
            vendor = val
        elif key == "flags" and not flags:
            flags = set(val.split())
    return {
        "model": model, "vendor": {"GenuineIntel": "Intel", "AuthenticAMD": "AMD"}.get(vendor, vendor),
        "threads": threads, "x86_64": "lm" in flags,
        "virtualization": "vmx" in flags or "svm" in flags,
        "hypervisor": "hypervisor" in flags,
        "x86_64_level": _x86_level(flags),
    }


def _x86_level(flags: set[str]) -> int:
    v2 = {"cx16", "lahf_lm", "popcnt", "sse4_1", "sse4_2", "ssse3"}
    v3 = {"avx", "avx2", "bmi1", "bmi2", "f16c", "fma", "abm", "movbe", "xsave"}
    v4 = {"avx512f", "avx512bw", "avx512cd", "avx512dq", "avx512vl"}
    if "lm" not in flags:
        return 0
    if not v2 <= flags:
        return 1
    if not v3 <= flags:
        return 2
    return 4 if v4 <= flags else 3


def memory_info(root: Path = Path("/")) -> dict:
    vals = {}
    for line in _read(root / "proc/meminfo").splitlines():
        k, _, v = line.partition(":")
        parts = v.split()
        if parts and parts[0].isdigit():
            vals[k] = int(parts[0]) * 1024
    return {"total_bytes": vals.get("MemTotal", 0), "available_bytes": vals.get("MemAvailable", 0),
            "swap_total_bytes": vals.get("SwapTotal", 0)}


def gpus(devices: list[Device]) -> list[dict]:
    vendors = {"1002": "AMD", "8086": "Intel", "10de": "NVIDIA", "1af4": "Virtio", "1234": "QEMU",
               "15ad": "VMware", "80ee": "VirtualBox", "1b36": "Red Hat (QXL)"}
    return [{"address": d.address, "vendor": vendors.get(d.vendor_id, d.vendor or d.vendor_id),
             "name": d.name, "driver": d.driver,
             "integrated": d.address.startswith("0000:00:")}
            for d in devices if d.category == "Graphics adapters"]


def probe(root: Path = Path("/")) -> dict:
    """Full hardware snapshot used by the Device Manager and the HCL report."""
    pci = pci_devices(root)
    devices = pci + usb_devices(root) + input_devices(root)
    problems = [d.to_dict() for d in devices if d.status != "ok"]
    return {
        "cpu": cpu_info(root),
        "memory": memory_info(root),
        "gpus": gpus(pci),
        "disks": block_devices(root),
        "network": network_interfaces(root),
        "batteries": batteries(root),
        "firmware": "uefi" if (root / "sys/firmware/efi").is_dir() else "bios",
        "devices": [d.to_dict() for d in devices],
        "problems": problems,
    }
