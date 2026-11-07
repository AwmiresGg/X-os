#!/usr/bin/env bash
# Prepare (or with --check, only inspect) a Debian/Ubuntu x86_64 host for building X-OS.
set -euo pipefail
PKGS=(debootstrap xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin grub-common mtools
      dosfstools qemu-system-x86 qemu-utils ovmf shellcheck debian-archive-keyring python3)
echo "arch: $(uname -m)   cpus: $(nproc)   ram: $(free -g | awk '/Mem:/{print $2}') GiB"
echo "free disk (project): $(df -h --output=avail "$(dirname "$0")" | tail -1)"
if [[ -w /dev/kvm ]]; then echo "kvm: available"; else echo "kvm: NOT available (QEMU will use slow TCG emulation)"; fi
missing=()
for p in "${PKGS[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
if [[ ${1:-} == --check ]]; then
    echo "missing packages: ${missing[*]:-none}"; exit 0
fi
[[ $EUID -eq 0 ]] || { echo "run as root to install packages" >&2; exit 1; }
if ((${#missing[@]})); then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
fi
echo "build host ready"
