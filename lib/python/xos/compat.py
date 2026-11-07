"""X-OS Windows Compatibility Engine - installer detection and planning.

Identifies Windows installer formats by their content (not just the extension),
looks up the compatibility database, and produces an installation plan
(prefix, Windows version, dependencies, runner). The plan is shown to the user
for consent before anything is executed; see xos-compat(1).

Nothing here claims universal compatibility: unknown applications are rated
"untested" and kernel-driver, anti-cheat and most DRM-dependent software is
rated "unsupported".
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

RATINGS = ("platinum", "gold", "silver", "bronze", "unsupported", "untested")

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"   # Compound File Binary (MSI)

# Signatures of common installer frameworks found inside PE files.
_INSTALLER_MARKERS = [
    (b"Nullsoft.NSIS", "nsis", "/S"),
    (b"NullsoftInst", "nsis", "/S"),
    (b"Inno Setup", "inno", "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART"),
    (b"InstallShield", "installshield", "/s"),
    (b"WiX Toolset", "wix-burn", "/quiet /norestart"),
    (b".wixburn", "wix-burn", "/quiet /norestart"),
    (b"Squirrel", "squirrel", "--silent"),
    (b"7-Zip SFX", "7z-sfx", None),
    (b"7zS.sfx", "7z-sfx", None),
]
# Markers that make an application impossible to run under Wine.
_BLOCKERS = [
    (b"ntoskrnl.exe", "kernel-mode driver (ntoskrnl.exe import)"),
    (b"EasyAntiCheat", "kernel anti-cheat (EasyAntiCheat) - works only if the game enables Proton support"),
    (b"BEDaisy", "kernel anti-cheat (BattlEye)"),
    (b"vgk.sys", "kernel anti-cheat (Riot Vanguard)"),
]


@dataclass
class Detection:
    path: str
    format: str                       # exe | msi | msix | msixbundle | appx | bat | cmd | com | unknown
    arch: str | None = None           # x86 | x64 | arm64
    subsystem: str | None = None      # gui | console
    framework: str | None = None      # nsis | inno | ...
    silent_args: str | None = None
    dotnet: bool = False
    blockers: list[str] = field(default_factory=list)
    sha256: str = ""
    size: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_pe(data: bytes, det: Detection) -> bool:
    if len(data) < 0x40 or data[:2] != b"MZ":
        return False
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_off + 24 > len(data) or data[pe_off:pe_off + 4] != b"PE\0\0":
        return False                                   # plain DOS MZ executable
    machine = struct.unpack_from("<H", data, pe_off + 4)[0]
    det.arch = {0x14C: "x86", 0x8664: "x64", 0xAA64: "arm64"}.get(machine, f"0x{machine:04x}")
    opt = pe_off + 24
    if opt + 70 <= len(data):
        magic = struct.unpack_from("<H", data, opt)[0]
        subsystem = struct.unpack_from("<H", data, opt + 68)[0]
        det.subsystem = {2: "gui", 3: "console", 1: "native"}.get(subsystem, str(subsystem))
        if subsystem == 1:
            det.blockers.append("native subsystem: this is a Windows driver or boot-time program")
        # CLR runtime header data directory -> .NET assembly
        dd = opt + (96 if magic == 0x10B else 112)
        if dd + 15 * 8 + 8 <= len(data):
            rva, size = struct.unpack_from("<II", data, dd + 14 * 8)
            det.dotnet = rva != 0 and size != 0
    return True


def detect(path: str | Path) -> Detection:
    p = Path(path)
    det = Detection(path=str(p), format="unknown", size=p.stat().st_size, sha256=_sha256(p))
    ext = p.suffix.lower()
    with p.open("rb") as fh:
        head = fh.read(4 << 20)                        # 4 MiB is enough for markers

    if head.startswith(OLE_MAGIC):
        # Office 97-2003 documents share the container format; rely on the extension there.
        if ext not in {".doc", ".xls", ".ppt", ".msg"}:
            det.format, det.silent_args = "msi", "/qn /norestart"
        return det
    if head[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(p) as z:
                names = set(z.namelist())
        except zipfile.BadZipFile:
            return det
        if "AppxMetadata/AppxBundleManifest.xml" in names:
            det.format = "msixbundle" if ext != ".appxbundle" else "appxbundle"
        elif "AppxManifest.xml" in names:
            det.format = "msix" if ext != ".appx" else "appx"
        if det.format != "unknown":
            det.notes.append("MSIX/APPX packages are unpacked and their executable run in a prefix; "
                             "packages relying on Store licensing or UWP APIs are not supported.")
        return det
    if _parse_pe(head, det):
        det.format = "exe"
        for marker, fw, args in _INSTALLER_MARKERS:
            if marker in head:
                det.framework, det.silent_args = fw, args
                break
        for marker, why in _BLOCKERS:
            if marker in head:
                det.blockers.append(why)
        if det.arch == "arm64":
            det.blockers.append("ARM64 Windows binary: X-OS runs x86/x64 Windows programs only")
        return det
    if ext == ".com" or (head[:2] == b"MZ"):
        det.format = "com" if ext == ".com" else "exe"
        det.arch = "x86-16"
        det.notes.append("16-bit DOS program: runs in DOSBox, not Wine, on 64-bit systems.")
        return det
    if ext in {".bat", ".cmd"}:
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            try:
                head.decode("cp1252")
            except UnicodeDecodeError:
                return det
        det.format = ext[1:]
        det.notes.append("Batch scripts run with Wine's cmd.exe inside the chosen prefix.")
        return det
    return det


# --------------------------------------------------------------------------- database
def load_db(path: Path) -> list[dict]:
    with path.open() as fh:
        data = json.load(fh)
    apps = data["apps"]
    for a in apps:
        if a["rating"] not in RATINGS:
            raise ValueError(f"{a['id']}: invalid rating {a['rating']!r}")
    return apps


def match(apps: list[dict], filename: str, sha256: str = "") -> dict | None:
    base = Path(filename).name.lower()
    for a in apps:
        if sha256 and sha256 in a.get("sha256", []):
            return a
    for a in apps:
        if a.get("match_requires_hash"):      # generic names like setup.exe
            continue
        for pattern in a.get("installer_patterns", []):
            if re.fullmatch(pattern, base, re.IGNORECASE):
                return a
    return None


def default_db_path() -> Path:
    for p in (Path("/usr/share/xos/compat/apps.json"),
              Path(__file__).resolve().parents[3] / "compatibility/database/apps.json"):
        if p.exists():
            return p
    raise FileNotFoundError("compatibility database not found")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "app"


def plan(det: Detection, entry: dict | None, home: Path) -> dict:
    """Installation plan shown to the user before anything runs."""
    rating = entry["rating"] if entry else "untested"
    if det.blockers:
        rating = "unsupported"
    app_id = entry["id"] if entry else _slug(Path(det.path).stem)
    # 64-bit prefixes run both 32- and 64-bit programs, and installers are often 32-bit
    # stubs that install 64-bit apps (e.g. 7-Zip x64). A 32-bit prefix only on request.
    win_arch = "win32" if (entry or {}).get("win32") else "win64"
    deps = list((entry or {}).get("dependencies", []))
    if det.dotnet and not any(d.startswith("dotnet") for d in deps):
        deps.append("dotnet48")
    runner = (entry or {}).get("runner", "wine")
    if det.format in {"com"} or det.arch == "x86-16":
        runner = "dosbox"
    can_install = rating != "unsupported" and det.format != "unknown"
    return {
        "app_id": app_id,
        "name": (entry or {}).get("name", Path(det.path).stem),
        "rating": rating,
        "can_install": can_install,
        "format": det.format,
        "runner": runner,
        "prefix": str(home / ".local/share/xos/prefixes" / app_id),
        "prefix_arch": win_arch,
        "windows_version": (entry or {}).get("windows_version", "win10"),
        "dependencies": deps,
        "dxvk": (entry or {}).get("dxvk", True),
        "vkd3d": (entry or {}).get("vkd3d", False),
        # MSI always uses msiexec's own switches; database switches are for .exe installers
        "silent_args": det.silent_args if det.format == "msi" else ((entry or {}).get("silent_args") or det.silent_args),
        "warnings": det.blockers + (entry or {}).get("known_issues", []) + det.notes
                    + ([] if entry else ["This application is not in the X-OS compatibility database. "
                                         "It may or may not work."]),
        "sha256": det.sha256,
    }


def install_steps(pl: dict, installer: str, wine: str = "wine", winetricks: str | None = "winetricks",
                  silent: bool = False) -> list[list[str]]:
    """The exact commands that install an app into its prefix (pure: nothing is executed).

    Run them in order with WINEPREFIX/WINEARCH from env_for(pl). Raises ValueError when
    the plan cannot be installed by this engine.
    """
    if not pl["can_install"]:
        raise ValueError("this installer is rated unsupported or is not a Windows installer")
    if pl["runner"] == "dosbox":
        raise ValueError("16-bit programs run in DOSBox, not Wine")
    if pl["format"] in ("msix", "msixbundle", "appx", "appxbundle"):
        raise ValueError("MSIX/APPX packages are not supported yet")
    steps = [[wine, "wineboot", "--init"]]
    if pl["windows_version"] and pl["windows_version"] != "win10":    # win10 is Wine's default
        steps.append([wine, "winecfg", "/v", pl["windows_version"]])
    if pl["dependencies"]:
        if not winetricks:
            raise ValueError("winetricks is required for: " + ", ".join(pl["dependencies"]))
        steps.append([winetricks, "-q", *pl["dependencies"]])
    if pl["dxvk"] and winetricks:
        steps.append([winetricks, "-q", "dxvk"])
    args = (pl.get("silent_args") or "").split() if silent else []
    if pl["format"] == "msi":
        steps.append([wine, "msiexec", "/i", installer, *(args or [])])
    elif pl["format"] in ("bat", "cmd"):
        steps.append([wine, "cmd", "/c", installer])
    else:
        steps.append([wine, installer, *args])
    return steps


def env_for(pl: dict, base: dict) -> dict:
    return dict(base, WINEPREFIX=pl["prefix"], WINEARCH=pl["prefix_arch"], WINEDEBUG="-all")
