# X-OS Implementation Status

Last updated: 2026-11-07 · Build: `x-os-0.1.0-dev-core-amd64.iso`
(sha256 `bc14a68bf9747d35f6e6d5b2db27ce9a19e1a5332ecd5542e349de1fc6bba10b`) ·
Release state: **INTERNAL TESTING** (see `releases/STATE.md`)

Test levels: **U** unit tested · **I** integration tested · **VM** VM tested ·
**HW** physical hardware tested · **—** not tested.

## Works today

| Feature | Level | Evidence |
|---|---|---|
| Reproducible ISO build pipeline (Debian 13, core variant), re-runnable stages | VM | `build/build.sh`; built 3× this session |
| Hybrid ISO boots on **UEFI** (OVMF) and **BIOS** (SeaBIOS) | VM | `testing/results/*-{bios,uefi}-*.json` |
| Live session at **2 GiB** and **4 GiB** RAM | VM | same |
| systemd reaches `running`, no failed units | VM | self-test `systemd` |
| NetworkManager: wired DHCP, online | VM | self-test `network-manager`, `connectivity` (isolated network) |
| Firewall (ufw) active by default, deny incoming | VM | self-test `firewall` |
| Disk tools present: parted, mkfs.{ext4,ntfs,exfat,btrfs,xfs,vfat}, cryptsetup, smartctl, udisks2 | VM | self-test `disk-tools` |
| Clean shutdown (`systemctl poweroff`) | VM | `clean_poweroff: true` |
| Hardware discovery `xos-hwprobe` (PCI/USB/input/disk/net/battery, missing driver detection) | U, VM | `testing/unit/test_hardware.py`; 11 devices found in VM, 0 false problems |
| Performance profiles `xos-profile` (recommend/apply) | U, VM (recommend) | `ProfileTests`; live boot applies LITE in VM |
| Windows installer detection + plan `xos-compat detect/plan` | U | `testing/unit/test_compat.py` (synthetic files) |
| Boot self-test `xos-selftest` | U, VM | `test_selftest.py`; runs in every VM test |
| Signature Dock geometry engine | U | `testing/unit/dock.test.mjs` (9 tests) |
| Signature Dock QML component (GPU + software render paths) | rendered offscreen | `documentation/images/dock-preview-*.png` |

## Implemented but NOT yet tested end-to-end

* `xos-compat install` (runs Wine, winetricks, installer) — needs Wine in a VM with real installers.
* `xos-compat-setup` (installs Wine from Debian).
* `xos-profile apply` effects on KWin/zram on a desktop system.
* GRUB entries other than the default (LITE, safe graphics, toram, self-test, UEFI setup).

## Not started

Desktop ISO, top bar, launcher, notifications, Control Center UI, Disk Manager
write operations, Bluetooth/VPN/Audio/Display managers, File Manager theming,
X-Store, Gaming, Security Center, snapshots/recovery, AI assistant, installer,
Plymouth/GRUB theme, Secure Boot signing. See `ROADMAP.md`.

## Never tested (needs a person with hardware)

Everything at level **HW**: Wi-Fi, Bluetooth, audio, real GPUs, touchpads,
sleep/wake, batteries, brightness, USB boot. The development environment has
no physical hardware and no KVM (see `ENVIRONMENT.md`).

## Known issues

| Severity | Issue |
|---|---|
| High (blocks Secure Boot PCs) | GRUB on the ISO is unsigned; machines with Secure Boot enabled will refuse to boot it. Workaround: disable Secure Boot. Fix planned: Debian shim-signed + signed GRUB. |
| Medium | Dock hand-over: rising circle overlaps the notch shoulder by a few px for ~100 ms. |
| Medium | Builds are not bit-reproducible (mirror moves; no SOURCE_DATE_EPOCH). |
| Low | Boot menu is text-only; no boot splash. |
| Info | VM timings come from software emulation (TCG) and are not performance data. |
