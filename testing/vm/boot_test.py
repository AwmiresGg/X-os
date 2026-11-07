#!/usr/bin/env python3
"""Automated X-OS VM boot test.

Boots an ISO in QEMU (BIOS or UEFI), lets the default GRUB entry boot, waits for
the in-image self-test (triggered via fw_cfg, so the boot path is exactly what a
user gets) and records the serial log as test evidence.

    testing/vm/boot_test.py releases/out/x-os-...iso --firmware uefi --memory 2048

Network: the guest is isolated (slirp restrict=on). A single local HTTP endpoint
is forwarded in so DHCP, routing and NetworkManager are exercised without the VM
reaching the internet. Internet access from a VM is therefore NOT tested here.

Exit status: 0 = self-test PASS, 1 = self-test FAIL, 2 = timeout / no result.
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVMF_CODE = Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
OVMF_VARS = Path("/usr/share/OVMF/OVMF_VARS_4M.fd")
# Secure Boot: SMM-protected firmware + variables with Microsoft's keys enrolled (SB enforced)
OVMF_CODE_SB = Path("/usr/share/OVMF/OVMF_CODE_4M.secboot.fd")
OVMF_VARS_SB = Path("/usr/share/OVMF/OVMF_VARS_4M.ms.fd")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_http() -> tuple[http.server.ThreadingHTTPServer, int]:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("iso")
    ap.add_argument("--firmware", choices=["bios", "uefi", "uefi-sb"], default="bios")
    ap.add_argument("--memory", type=int, default=2048, help="MiB")
    ap.add_argument("--cpus", type=int, default=2)
    ap.add_argument("--cpu-model", default="max",
                    help="QEMU CPU model under TCG. Desktop images need one without AVX2 (e.g. Westmere): "
                         "QEMU 8.2's TCG mis-emulates the AVX2 gathers Mesa llvmpipe generates.")
    ap.add_argument("--timeout", type=int, default=1500, help="seconds")
    ap.add_argument("--disk-gb", type=int, default=8, help="blank virtual disk (0 = none)")
    ap.add_argument("--evidence", default=str(ROOT / "testing/results"))
    a = ap.parse_args()

    iso = Path(a.iso).resolve()
    if not iso.exists():
        print(f"ISO not found: {iso}", file=sys.stderr)
        return 2
    accel = "kvm" if os.access("/dev/kvm", os.W_OK) else "tcg"
    tmp = Path(tempfile.mkdtemp(prefix="xos-vm-"))
    log_dir = ROOT / "testing/vm/logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    serial_log = log_dir / f"{iso.stem}-{a.firmware}-{a.memory}M-{stamp}.serial.log"

    srv, port = start_http()
    machine = "q35,smm=on" if a.firmware == "uefi-sb" else "q35"
    cmd = ["qemu-system-x86_64", "-machine", machine, "-accel", accel,
           "-cpu", a.cpu_model if accel == "tcg" else "host",
           "-smp", str(a.cpus), "-m", str(a.memory),
           "-display", "none", "-serial", f"file:{serial_log}", "-monitor", "none",
           "-no-reboot",
           "-drive", f"file={iso},media=cdrom,readonly=on,if=none,id=cd0",
           "-device", "ahci,id=ahci0", "-device", "ide-cd,drive=cd0,bus=ahci0.0,bootindex=0",
           "-nic", f"user,model=virtio-net-pci,restrict=on,guestfwd=tcp:10.0.2.100:80-tcp:127.0.0.1:{port}",
           "-fw_cfg", "name=opt/org.x-os.selftest,string=poweroff",
           "-fw_cfg", "name=opt/org.x-os.selftest-url,string=http://10.0.2.100/",
           "-device", "virtio-rng-pci"]
    if a.disk_gb:
        disk = tmp / "disk.qcow2"
        subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", str(disk), f"{a.disk_gb}G"], check=True)
        cmd += ["-drive", f"file={disk},if=virtio,format=qcow2"]
    if a.firmware in ("uefi", "uefi-sb"):
        sb = a.firmware == "uefi-sb"
        vars_copy = tmp / "OVMF_VARS.fd"
        shutil.copy(OVMF_VARS_SB if sb else OVMF_VARS, vars_copy)
        if sb:
            cmd += ["-global", "driver=cfi.pflash01,property=secure,value=on"]
        cmd += ["-drive", f"if=pflash,format=raw,readonly=on,file={OVMF_CODE_SB if sb else OVMF_CODE}",
                "-drive", f"if=pflash,format=raw,file={vars_copy}"]

    print(f"[boot-test] {iso.name} firmware={a.firmware} mem={a.memory}M accel={accel} log={serial_log}")
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd)
    result, lines = None, []
    try:
        while time.monotonic() - t0 < a.timeout:
            if serial_log.exists():
                text = serial_log.read_text(errors="replace")
                if "XOS-SELFTEST-RESULT:" in text:
                    result = text.split("XOS-SELFTEST-RESULT:")[1].split()[0]
                    lines = [ln.strip() for ln in text.splitlines() if ln.startswith("XOS-SELFTEST")]
                    break
            if proc.poll() is not None:
                break
            time.sleep(3)
        # Allow the guest to power itself off (tests shutdown); force after 120 s.
        try:
            proc.wait(timeout=120 if result else 1)
            clean_shutdown = bool(result) and proc.returncode == 0
        except subprocess.TimeoutExpired:
            clean_shutdown = False
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    elapsed = round(time.monotonic() - t0)
    for ln in lines:
        print(ln)
    print(f"[boot-test] result={result or 'TIMEOUT'} clean_poweroff={clean_shutdown} elapsed={elapsed}s")

    Path(a.evidence).mkdir(parents=True, exist_ok=True)
    evidence = {
        "iso": iso.name, "iso_sha256": _sha256(iso), "firmware": a.firmware, "memory_mib": a.memory,
        "cpus": a.cpus, "cpu_model": a.cpu_model if accel == "tcg" else "host", "accelerator": accel, "date_utc": stamp, "elapsed_seconds": elapsed,
        "selftest_result": result or "TIMEOUT", "clean_poweroff": clean_shutdown,
        "selftest_lines": lines, "test_level": "VM tested (QEMU, emulated hardware)",
        "network_note": "guest network isolated; internet access not tested",
    }
    out = Path(a.evidence) / f"{iso.stem}-{a.firmware}-{a.memory}M.json"
    out.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"[boot-test] evidence written to {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    if result == "PASS" and clean_shutdown:
        return 0
    return 1 if result else 2


def _sha256(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    sys.exit(main())
