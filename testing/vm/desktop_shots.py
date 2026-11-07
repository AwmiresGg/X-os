#!/usr/bin/env python3
"""Boot an X-OS desktop ISO in QEMU and capture screenshots of the live session.

    testing/vm/desktop_shots.py releases/out/x-os-...-desktop-amd64.iso --out DIR \
        --at 240 420 600 [--keys-at 600:tab,ret]

Screenshots are taken through QMP `screendump` (PPM) and converted to PNG with
only the standard library. Guest network is isolated (restrict=on).
This is visual evidence for a person to review; it does not assert anything.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path

OVMF_CODE = Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
OVMF_VARS = Path("/usr/share/OVMF/OVMF_VARS_4M.fd")


def ppm_to_png(ppm: Path, png: Path) -> None:
    data = ppm.read_bytes()
    parts, pos = [], 0
    while len(parts) < 4:                      # magic, width, height, maxval
        while data[pos:pos + 1].isspace():
            pos += 1
        start = pos
        while not data[pos:pos + 1].isspace():
            pos += 1
        parts.append(data[start:pos])
    pos += 1
    w, h = int(parts[1]), int(parts[2])
    pixels = data[pos:pos + w * h * 3]
    raw = b"".join(b"\x00" + pixels[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


class QMP:
    def __init__(self, path: str):
        for _ in range(100):
            try:
                self.s = socket.socket(socket.AF_UNIX)
                self.s.connect(path)
                break
            except OSError:
                time.sleep(0.2)
        self.f = self.s.makefile("rw")
        self.f.readline()
        self.cmd("qmp_capabilities")

    def cmd(self, name, **args):
        self.f.write(json.dumps({"execute": name, "arguments": args}) + "\n")
        self.f.flush()
        while True:
            msg = json.loads(self.f.readline())
            if "return" in msg or "error" in msg:
                return msg


_SHIFTED = {"|": "backslash", "_": "minus", ":": "semicolon", '"': "apostrophe", ">": "dot", "<": "comma",
            "*": "8", "&": "7", "(": "9", ")": "0", "+": "equal", "?": "slash", "~": "grave_accent", "$": "4",
            "^": "6", "!": "1", "@": "2", "#": "3", "%": "5", "{": "bracket_left", "}": "bracket_right"}
_PLAIN = {" ": "spc", "-": "minus", "/": "slash", ".": "dot", "=": "equal", ",": "comma", ";": "semicolon",
          "'": "apostrophe", "\\": "backslash", "\n": "ret", "[": "bracket_left", "]": "bracket_right"}


def text_to_keys(text: str) -> list[str]:
    """Convert text to QEMU qcode chords (US layout), e.g. 'A|' -> ['shift+a', 'shift+backslash']."""
    out = []
    for ch in text:
        if ch.isalpha() and ch.isascii():
            out.append(("shift+" if ch.isupper() else "") + ch.lower())
        elif ch.isdigit():
            out.append(ch)
        elif ch in _PLAIN:
            out.append(_PLAIN[ch])
        elif ch in _SHIFTED:
            out.append("shift+" + _SHIFTED[ch])
        else:
            raise ValueError(f"cannot type {ch!r}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("iso")
    ap.add_argument("--out", required=True)
    ap.add_argument("--at", type=int, nargs="+", action="extend", default=None, help="seconds after start")
    ap.add_argument("--keys-at", action="append", default=[], help="SECONDS:key,key (QEMU qcode names)")
    ap.add_argument("--type-at", action="append", default=[], help="SECONDS:text to type (\\n = Enter)")
    ap.add_argument("--memory", type=int, default=4096)
    ap.add_argument("--cpus", type=int, default=4)
    ap.add_argument("--cpu-model", default="", help="QEMU CPU model (TCG default: Westmere; 'max' exposes AVX2/AVX-512)")
    ap.add_argument("--firmware", choices=["bios", "uefi"], default="uefi")
    ap.add_argument("--click-at", action="append", default=[], help="SECONDS:x,y left click (screen pixels)")
    ap.add_argument("--screen", default="1280x800", help="guest screen size for click scaling")
    ap.add_argument("--grub-entry", type=int, default=0, help="menu entry index to boot (sent as Down keys)")
    ap.add_argument("--serial-at", action="append", default=[], help="SECONDS:text to write to the serial console")
    ap.add_argument("--selftest", action="store_true", help="run xos-selftest (report mode) and log to serial")
    a = ap.parse_args()

    a.at = a.at or [300, 480, 660]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="xos-shots-"))
    qmp_path = str(tmp / "qmp.sock")
    accel = "kvm" if os.access("/dev/kvm", os.W_OK) else "tcg"
    disk = tmp / "disk.qcow2"
    subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", str(disk), "30G"], check=True)
    cmd = ["qemu-system-x86_64", "-machine", "q35", "-accel", accel, "-cpu", a.cpu_model or ("Westmere" if accel == "tcg" else "host"),
           "-smp", str(a.cpus), "-m", str(a.memory), "-display", "none", "-vga", "none",
           "-device", "virtio-vga", "-qmp", f"unix:{qmp_path},server=on,wait=off",
           "-drive", f"file={Path(a.iso).resolve()},media=cdrom,readonly=on,if=none,id=cd0",
           "-device", "ahci,id=ahci0", "-device", "ide-cd,drive=cd0,bus=ahci0.0,bootindex=0",
           "-drive", f"file={disk},if=virtio,format=qcow2",
           "-nic", "user,model=virtio-net-pci,restrict=on", "-device", "virtio-rng-pci",
           "-usb", "-device", "usb-tablet", "-serial", f"unix:{tmp / 'serial.sock'},server=on,wait=off"]
    if a.selftest:
        cmd += ["-fw_cfg", "name=opt/org.x-os.selftest,string=report"]
    if a.firmware == "uefi":
        shutil.copy(OVMF_VARS, tmp / "vars.fd")
        cmd += ["-drive", f"if=pflash,format=raw,readonly=on,file={OVMF_CODE}",
                "-drive", f"if=pflash,format=raw,file={tmp / 'vars.fd'}"]
    proc = subprocess.Popen(cmd)
    t0 = time.monotonic()
    serial_log = (out / "serial.log").open("ab")
    ser = socket.socket(socket.AF_UNIX)
    for _ in range(100):
        try:
            ser.connect(str(tmp / "serial.sock"))
            break
        except OSError:
            time.sleep(0.2)
    seen = bytearray()

    def pump():
        while True:
            try:
                chunk = ser.recv(4096)
            except OSError:
                return
            if not chunk:
                return
            seen.extend(chunk)
            serial_log.write(chunk)
            serial_log.flush()
    import threading
    threading.Thread(target=pump, daemon=True).start()
    try:
        q = QMP(qmp_path)
        if a.grub_entry:
            while b"automatically in" not in seen and time.monotonic() - t0 < 300:
                time.sleep(0.5)
            for _ in range(a.grub_entry):
                q.cmd("send-key", keys=[{"type": "qcode", "data": "down"}])
                time.sleep(0.3)
            q.cmd("send-key", keys=[{"type": "qcode", "data": "ret"}])
            print(f"[{int(time.monotonic() - t0):5d}s] selected GRUB entry {a.grub_entry}")
        events = sorted([(t, "shot", None) for t in a.at] +
                        [(int(k.split(":")[0]), "keys", k.split(":")[1].split(",")) for k in a.keys_at] +
                        [(int(k.split(":", 1)[0]), "keys", text_to_keys(k.split(":", 1)[1].replace("\\n", "\n")))
                         for k in a.type_at] +
                        [(int(k.split(":", 1)[0]), "serial", k.split(":", 1)[1].replace("\\n", "\n"))
                         for k in a.serial_at] +
                        [(int(k.split(":")[0]), "click", tuple(int(v) for v in k.split(":")[1].split(",")))
                         for k in a.click_at])
        for when, kind, payload in events:
            while time.monotonic() - t0 < when:
                if proc.poll() is not None:
                    print("VM exited early", file=sys.stderr)
                    return 2
                time.sleep(2)
            if kind == "click":
                sw, sh = (int(v) for v in a.screen.split("x"))
                x, y = payload
                q.cmd("input-send-event", events=[
                    {"type": "abs", "data": {"axis": "x", "value": int(x * 32767 / (sw - 1))}},
                    {"type": "abs", "data": {"axis": "y", "value": int(y * 32767 / (sh - 1))}}])
                time.sleep(0.3)
                for down in (True, False):
                    q.cmd("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": "left"}}])
                    time.sleep(0.1)
                print(f"[{when:5d}s] click {x},{y}")
                continue
            if kind == "serial":
                ser.sendall(payload.encode())
                print(f"[{when:5d}s] wrote {len(payload)} bytes to serial")
                continue
            if kind == "keys":
                for k in payload:
                    q.cmd("send-key", keys=[{"type": "qcode", "data": x} for x in k.split("+")])
                    time.sleep(0.15)
                print(f"[{when:5d}s] sent {len(payload)} keys")
            else:
                ppm = tmp / "shot.ppm"
                r = q.cmd("screendump", filename=str(ppm))
                if "error" in r:
                    print(f"[{when:5d}s] screendump failed: {r['error']}")
                    continue
                png = out / f"shot-{when:05d}s.png"
                ppm_to_png(ppm, png)
                print(f"[{when:5d}s] {png}")
    finally:
        proc.kill()
        proc.wait()
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
