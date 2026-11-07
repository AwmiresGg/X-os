#!/usr/bin/env bash
# End-to-end installer test in a VM (scratch qcow2 disk only):
#   live boot -> X-OS Setup (Persian, +Persian keyboard, Light, +Chrome) -> Calamares
#   start (continue interactively: Tehran, erase the blank virtual disk, user, install).
# Screenshots of every step go to build/work/vm-<name>/flow/. Coordinates assume
# the 1280x800 virtio-vga screen. Timings are generous because QEMU without KVM is slow.
#
#   testing/vm/install_flow.sh releases/out/x-os-<ver>-desktop-amd64.iso
set -euo pipefail
ISO="${1:?ISO}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
V="$ROOT/testing/vm/vmctl.py --name flow"
SB="${XOS_SECURE_BOOT:+--secure-boot}"
OUT="$ROOT/build/work/vm-flow/flow"
mkdir -p "$OUT"
n=0
shot() { n=$((n + 1)); $V shot "$OUT/$(printf '%02d' $n)-$1.png" >/dev/null; echo "[$(date +%T)] $n $1"; }
wait_s() { sleep "$1"; }

$V stop >/dev/null 2>&1 || true
$V start $SB "$ISO"
wait_s 480;  shot live-desktop-setup
$V click 1000 240;  wait_s 15; shot setup-persian
$V click 224 670;   wait_s 15; shot setup-keyboard
$V click 600 300;   wait_s 10
$V click 500 607;   wait_s 3
$V type "salam ";   $V key alt+shift_l; wait_s 5; $V type "salam"; wait_s 8; shot keyboard-switch-test
$V key ctrl+a; $V key backspace
$V click 224 670;   wait_s 15; shot setup-wifi
$V click 224 670;   wait_s 15; shot setup-appearance
$V click 523 295;   wait_s 45; shot setup-light-applied
$V click 224 670;   wait_s 15; shot setup-apps
$V click 520 305;   wait_s 8
$V click 224 670;   wait_s 15; shot setup-ready
$V click 668 670;   wait_s 100; shot calamares-welcome
# Calamares now starts in the language chosen in X-OS Setup (right-to-left for
# Persian), so its pages are driven interactively from here with vmctl.py.
echo "screenshots in $OUT"
