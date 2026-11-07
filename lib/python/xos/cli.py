"""Command-line entry points for X-OS tools."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import compat, hardware, profiles, selftest

GiB = 1024 ** 3


# --------------------------------------------------------------------------- xos-hwprobe
def hwprobe(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="xos-hwprobe", description="X-OS hardware report")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--root", default="/", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    hw = hardware.probe(Path(a.root))
    if a.json:
        print(json.dumps(hw, indent=2))
        return 0
    c, m = hw["cpu"], hw["memory"]
    print(f"CPU       {c['model']}  ({c['vendor']}, {c['threads']} threads, x86-64-v{c['x86_64_level']}"
          f"{', VM' if c['hypervisor'] else ''})")
    print(f"Memory    {m['total_bytes'] / GiB:.1f} GiB  (available {m['available_bytes'] / GiB:.1f} GiB)")
    print(f"Firmware  {hw['firmware'].upper()}")
    for g in hw["gpus"]:
        print(f"GPU       {g['vendor']} {g['name']}  driver={g['driver'] or 'NONE'}")
    for d in hw["disks"]:
        print(f"Disk      /dev/{d['name']}  {d['size_bytes'] / 1e9:.1f} GB  {d['kind']}  {d['model']}")
    for n in hw["network"]:
        print(f"Network   {n['name']}  {n['type']}  {n['state']}  driver={n['driver'] or '-'}")
    for b in hw["batteries"]:
        print(f"Battery   {b['name']}  {b['capacity_percent']}%  {b['status']}  health={b['health_percent']}%")
    by_cat: dict[str, list] = {}
    for d in hw["devices"]:
        by_cat.setdefault(d["category"], []).append(d)
    print("\nDevices")
    for cat in sorted(by_cat):
        print(f"  {cat}")
        for d in by_cat[cat]:
            flag = "" if d["status"] == "ok" else f"   [{d['status'].upper()}]"
            print(f"    {d['vendor'][:28]:28} {d['name'][:44]:44} {d['driver'] or '-'}{flag}")
    if hw["problems"]:
        print(f"\n{len(hw['problems'])} device(s) need attention (see [NO-DRIVER] above).")
    return 0


# --------------------------------------------------------------------------- xos-profile
def profile(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="xos-profile", description="X-OS performance profiles")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("recommend")
    sub.add_parser("list")
    p_apply = sub.add_parser("apply")
    p_apply.add_argument("profile", choices=sorted(profiles.PROFILES) + ["auto"])
    p_apply.add_argument("--dry-run", action="store_true")
    p_apply.add_argument("--live", action="store_true", help="runtime-only changes (live session)")
    a = ap.parse_args(argv)

    if a.cmd == "list":
        for p in profiles.PROFILES.values():
            print(f"{p.id:12} {p.title:18} {p.description}")
        return 0
    if a.cmd in ("status", "recommend"):
        rec, reasons = profiles.recommend(hardware.probe())
        if a.cmd == "status":
            print(f"current:     {profiles.current() or 'not set'}")
        print(f"recommended: {rec}  ({'; '.join(reasons)})")
        return 0
    target = a.profile
    if target == "auto":
        target, _ = profiles.recommend(hardware.probe())
    if not a.dry_run and os.geteuid() != 0:
        print("xos-profile apply needs administrator rights: run with sudo or pkexec", file=sys.stderr)
        return 1
    for line in profiles.apply(target, live=a.live, dry_run=a.dry_run):
        print(line)
    return 0


# --------------------------------------------------------------------------- xos-compat
def compat_main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="xos-compat", description="X-OS Windows Compatibility Engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("detect", "plan", "install"):
        sp = sub.add_parser(name)
        sp.add_argument("file")
        sp.add_argument("--json", action="store_true")
        if name == "install":
            sp.add_argument("--yes", action="store_true", help="skip the consent prompt")
    a = ap.parse_args(argv)

    det = compat.detect(a.file)
    if a.cmd == "detect":
        print(json.dumps(det.to_dict(), indent=2) if a.json else
              f"{det.format} arch={det.arch} subsystem={det.subsystem} framework={det.framework} "
              f".NET={det.dotnet} sha256={det.sha256[:16]}…"
              + "".join(f"\n  blocker: {b}" for b in det.blockers))
        return 0 if det.format != "unknown" else 2

    apps = compat.load_db(compat.default_db_path())
    entry = compat.match(apps, a.file, det.sha256)
    pl = compat.plan(det, entry, Path.home())
    if a.cmd == "plan" or a.json:
        print(json.dumps(pl, indent=2) if a.json else _format_plan(pl, entry))
        if a.cmd == "plan":
            return 0
    else:
        print(_format_plan(pl, entry))
    if not pl["can_install"]:
        print("\nX-OS will not run this installer: it is rated unsupported or not a Windows installer.")
        return 3
    alt = (entry or {}).get("native_alternative")
    if alt:
        print(f"\nRecommended instead: {alt['note']}")
    if not a.yes:
        print(f"\nThis will run '{Path(a.file).name}' (sha256 {pl['sha256'][:16]}…) inside an isolated Wine prefix.\n"
              "Windows programs can read your home folder. Only run installers from sources you trust.")
        if input("Type 'install' to continue: ").strip() != "install":
            print("Cancelled.")
            return 1
    return _install(a.file, pl)


def _format_plan(pl: dict, entry: dict | None) -> str:
    out = [f"Application:  {pl['name']}",
           f"Rating:       {pl['rating'].upper()}{'' if entry and entry.get('verified_on_xos') else ' (not yet verified on X-OS)'}",
           f"Format:       {pl['format']}    Runner: {pl['runner']}",
           f"Prefix:       {pl['prefix']} ({pl['prefix_arch']}, {pl['windows_version']})",
           f"Dependencies: {', '.join(pl['dependencies']) or 'none'}",
           f"DXVK: {pl['dxvk']}  VKD3D-Proton: {pl['vkd3d']}"]
    out += [f"Warning:      {w}" for w in pl["warnings"]]
    return "\n".join(out)


def _install(installer: str, pl: dict) -> int:
    if pl["runner"] == "dosbox":
        print("16-bit programs are run with DOSBox: sudo apt install dosbox")
        return 4
    wine = shutil.which("wine")
    if not wine:
        print("Wine is not installed. Install the compatibility layer first:\n"
              "  sudo xos-compat-setup        (installs wine, wine32, winetricks, fonts)")
        return 4
    env = dict(os.environ, WINEPREFIX=pl["prefix"], WINEARCH=pl["prefix_arch"], WINEDEBUG="-all")
    Path(pl["prefix"]).mkdir(parents=True, exist_ok=True)
    steps = [[wine, "wineboot", "--init"],
             [wine, "winecfg", "-v", pl["windows_version"]]]
    if pl["dependencies"]:
        if not shutil.which("winetricks"):
            print("winetricks is required for dependencies: sudo apt install winetricks")
            return 4
        steps.append(["winetricks", "-q", *pl["dependencies"]])
    if pl["dxvk"] and shutil.which("winetricks"):
        steps.append(["winetricks", "-q", "dxvk"])
    if pl["format"] == "msi":
        steps.append([wine, "msiexec", "/i", installer])
    elif pl["format"] in ("bat", "cmd"):
        steps.append([wine, "cmd", "/c", installer])
    elif pl["format"] in ("msix", "msixbundle", "appx", "appxbundle"):
        print("MSIX unpacking is not implemented yet (tracked in compatibility/MODULE.md).")
        return 5
    else:
        steps.append([wine, installer])
    for cmd in steps:
        print("→", " ".join(cmd))
        r = subprocess.run(cmd, env=env)
        if r.returncode != 0:
            print(f"Step failed with exit code {r.returncode}. Run 'xos-compat plan' and see "
                  "/usr/share/doc/xos/compatibility.md for troubleshooting.")
            return r.returncode
    meta = Path(pl["prefix"]) / "xos-app.json"
    meta.write_text(json.dumps(pl, indent=2))
    print(f"Installed into {pl['prefix']}. Wine creates launcher entries in ~/.local/share/applications/wine/.")
    return 0


# --------------------------------------------------------------------------- xos-selftest
def selftest_main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="xos-selftest", description="X-OS system self-test")
    ap.add_argument("--boot", action="store_true", help="boot mode: run only if requested, report to console")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    mode = "report"
    if a.boot:
        mode = selftest.requested()
        if mode is None:
            return 0
    report = selftest.run(mode)
    summary = selftest.format_summary(report)
    print(json.dumps(report, indent=2) if a.json else summary)
    if a.boot:
        selftest.console_write(summary)
        if mode == "poweroff":
            subprocess.run(["systemctl", "--no-block", "poweroff"], check=False)
    return 0 if report["overall"] == "PASS" else 1
