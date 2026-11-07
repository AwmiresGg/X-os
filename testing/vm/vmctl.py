#!/usr/bin/env python3
"""Interactive control of a running X-OS test VM (for exploratory GUI testing).

    vmctl.py start ISO [--disk-gb 30] [--memory 4096] [--name main]
    vmctl.py shot OUT.png            screenshot
    vmctl.py click X Y               left click at screen pixel (1280x800 default)
    vmctl.py key ctrl+alt+f2         key chord (QEMU qcodes)
    vmctl.py type "text\\n"          type text (US layout)
    vmctl.py serial "text\\n"        write to serial console (needs --serial-console at start)
    vmctl.py stop

State lives in build/work/vm-<name>/ (QMP socket, serial log, disk image).
The guest network is isolated (restrict=on); the virtual disk is a scratch qcow2.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("shots", Path(__file__).with_name("desktop_shots.py"))
shots = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shots)


def state(name: str) -> Path:
    d = ROOT / "build/work" / f"vm-{name}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def qmp(name: str) -> "shots.QMP":
    return shots.QMP(str(state(name) / "qmp.sock"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="main")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("iso")
    s.add_argument("--memory", type=int, default=4096)
    s.add_argument("--cpus", type=int, default=4)
    s.add_argument("--disk-gb", type=int, default=30)
    s.add_argument("--keep-disk", action="store_true", help="reuse the existing disk image (boot an install)")
    s.add_argument("--boot-disk", action="store_true", help="boot from the virtual disk instead of the ISO")
    sub.add_parser("shot").add_argument("out")
    c = sub.add_parser("click")
    c.add_argument("x", type=int)
    c.add_argument("y", type=int)
    c.add_argument("--screen", default="1280x800")
    sub.add_parser("key").add_argument("chord")
    sub.add_parser("type").add_argument("text")
    sub.add_parser("stop")
    a = ap.parse_args()
    st = state(a.name)

    if a.cmd == "start":
        disk = st / "disk.qcow2"
        if not (a.keep_disk and disk.exists()):
            subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", str(disk), f"{a.disk_gb}G"], check=True)
        vars_fd = st / "OVMF_VARS.fd"
        if not (a.keep_disk and vars_fd.exists()):
            shutil.copy(shots.OVMF_VARS, vars_fd)
        accel = "kvm" if os.access("/dev/kvm", os.W_OK) else "tcg"
        cmd = ["qemu-system-x86_64", "-machine", "q35", "-accel", accel,
               "-cpu", "Westmere" if accel == "tcg" else "host", "-smp", str(a.cpus), "-m", str(a.memory),
               "-display", "none", "-vga", "none", "-device", "virtio-vga",
               "-qmp", f"unix:{st / 'qmp.sock'},server=on,wait=off",
               "-drive", f"if=pflash,format=raw,readonly=on,file={shots.OVMF_CODE}",
               "-drive", f"if=pflash,format=raw,file={vars_fd}",
               "-drive", f"file={disk},if=none,id=hd0,format=qcow2", "-device", "virtio-blk-pci,drive=hd0,bootindex=1",
               "-nic", "user,model=virtio-net-pci,restrict=on", "-device", "virtio-rng-pci",
               "-usb", "-device", "usb-tablet", "-serial", f"file:{st / 'serial.log'}",
               "-pidfile", str(st / "qemu.pid"), "-daemonize"]
        if not a.boot_disk:
            cmd += ["-drive", f"file={Path(a.iso).resolve()},media=cdrom,readonly=on,if=none,id=cd0",
                    "-device", "ahci,id=ahci0", "-device", "ide-cd,drive=cd0,bus=ahci0.0,bootindex=0"]
        subprocess.run(cmd, check=True)
        (st / "started").write_text(str(time.time()))
        print(f"started ({accel}); state in {st}")
        return 0

    if a.cmd == "stop":
        pid = st / "qemu.pid"
        if pid.exists():
            try:
                os.kill(int(pid.read_text()), 15)
            except ProcessLookupError:
                pass
            pid.unlink()
        print("stopped")
        return 0

    q = qmp(a.name)
    if a.cmd == "shot":
        ppm = st / "shot.ppm"
        r = q.cmd("screendump", filename=str(ppm))
        if "error" in r:
            print(r["error"])
            return 1
        shots.ppm_to_png(ppm, Path(a.out))
        up = time.time() - float((st / "started").read_text())
        print(f"{a.out} (vm uptime {up:.0f}s)")
    elif a.cmd == "click":
        sw, sh = (int(v) for v in a.screen.split("x"))
        q.cmd("input-send-event", events=[
            {"type": "abs", "data": {"axis": "x", "value": int(a.x * 32767 / (sw - 1))}},
            {"type": "abs", "data": {"axis": "y", "value": int(a.y * 32767 / (sh - 1))}}])
        time.sleep(0.3)
        for down in (True, False):
            q.cmd("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": "left"}}])
            time.sleep(0.1)
        print(f"clicked {a.x},{a.y}")
    elif a.cmd in ("key", "type"):
        chords = [a.chord] if a.cmd == "key" else shots.text_to_keys(a.text.replace("\\n", "\n"))
        for ch in chords:
            q.cmd("send-key", keys=[{"type": "qcode", "data": k} for k in ch.split("+")])
            time.sleep(0.12)
        print(f"sent {len(chords)} key(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
