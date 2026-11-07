# Development Environment Report

Inspected 2026-11-06 at the start of development (Phase 1). Re-run
`scripts/setup-build-host.sh --check` to inspect a new build host.

| Item | Finding |
|---|---|
| CPU | Intel Xeon @ 2.10 GHz, 4 vCPU, x86-64-v4 (AVX-512), running under a KVM hypervisor |
| RAM | 15.7 GiB, no swap |
| Disk | 31 GB writable allowance for the session |
| Host OS | Ubuntu 24.04.5 LTS (container), x86_64, running as root |
| Nested virtualization | **Not available**: no `/dev/kvm`, no `vmx`/`svm` flag exposed |
| Network | Outbound HTTPS through a proxy; Debian mirrors (deb.debian.org) reachable |
| Build tools | gcc/g++, cmake, Python 3.13, Node 22, Rust, Docker CLI; installed: debootstrap 1.0.134, squashfs-tools 4.6, xorriso 1.5.6, GRUB 2.12 (BIOS + EFI), mtools, QEMU 8.2, OVMF (UEFI firmware), shellcheck |
| Physical hardware access | **None.** This is a remote cloud container. No USB, no real GPU, Wi-Fi or Bluetooth |

## What this means

* **Bootable ISO images can be built here.** debootstrap + chroot + mksquashfs +
  grub-mkrescue all run as root inside the container.
* **VM testing works, slowly.** Without KVM, QEMU runs under TCG software emulation
  (very roughly 10-30x slower than hardware). Boots to a CLI self-test take minutes; a
  full Plasma desktop is usable for screenshots but not for performance measurement.
  **No performance numbers from this environment are meaningful.**
* **Physical hardware testing is impossible here.** Release states `LIVE USB VERIFIED`
  and `PHYSICAL HARDWARE VERIFIED` require a person to boot the ISO on real machines
  (see `documentation/HARDWARE-TESTING.md`). No hardware compatibility claim will be
  made from VM results.
* **The VM's network is isolated during tests** (QEMU `restrict=on`), with one local
  endpoint forwarded in. DHCP, routing and NetworkManager are exercised; real internet
  access from the guest, Wi-Fi and Bluetooth are not.
* Ubuntu's `live-build` package (3.0~a57) is too old to target Debian 13, so X-OS uses
  its own small, auditable pipeline in `build/build.sh` instead.
