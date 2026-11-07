# Release States and Quality Gates

An X-OS build carries exactly one release state, recorded in `/etc/os-release`
(`XOS_RELEASE_STATE`) and in `releases/STATE.md`. A build moves up only when the
gate's evidence is committed under `testing/results/`. **No build may be called
READY FOR INSTALLATION before reaching INSTALLER VERIFIED and passing Gate E.**

| State | Gate evidence required |
|---|---|
| DEVELOPMENT | Builds from a clean checkout. Unit tests pass. |
| INTERNAL TESTING | Automated VM boot test runs end-to-end (may have known failures, all listed). |
| VIRTUAL MACHINE VERIFIED | VM boot test PASS on BIOS **and** UEFI, at 2 GiB and 4 GiB RAM; desktop session starts; Control Center smoke tests pass; clean shutdown and reboot. |
| LIVE USB VERIFIED | ISO written to USB (`dd`/Ventoy-free raw write) boots on ≥ 3 physical machines (one ≥ 8 years old, one AMD, one Intel) **without modifying internal disks** (verified by comparing partition tables before/after). |
| PHYSICAL HARDWARE VERIFIED | Hardware checklist (HARDWARE-TESTING.md) completed per machine: Wi-Fi, Ethernet, Bluetooth, audio, graphics, keyboard, touchpad, storage, USB, sleep/wake, battery, brightness. Results recorded in the HCL. |
| INSTALLER VERIFIED | Gate E below, on virtual disks and on a **spare** physical disk. |
| RELEASE CANDIDATE | All above + no open critical/high bugs + documentation complete + upgrade path tested. |
| STABLE RELEASE | RC used for ≥ 2 weeks by testers with no critical regressions. |

## Gate E — installation readiness

All must pass, each with evidence:

1. ISO integrity: SHA-256 published and verified; `md5sum.txt` check passes in live session.
2. Bootloader: installed system boots on BIOS and UEFI; GRUB menu lists other detected OSes.
3. Installer integrity: Calamares completes auto, manual, and "alongside" modes on virtual disks.
4. Partition safety: installer never writes to a disk other than the one selected; existing
   Windows/macOS/Linux partitions are byte-identical after an "alongside" install
   (verified by checksumming them before/after in VM).
5. Disk detection: NVMe, SATA, virtio, USB disks listed with model + size + existing partitions.
6. Dual boot: Windows Boot Manager entry preserved; both OSes boot.
7. Recovery: live medium can repair GRUB (`xos-recovery boot-repair`) on a deliberately broken install.
8. Rollback strategy: Btrfs snapshot before first update; rollback entry boots.

## Gate F — user approval

Installation on a user's internal disk happens only after the user reviews the
test results and explicitly approves. Development builds display
"Development build — not ready for installation" in the installer's welcome page.

## Current state

See `releases/STATE.md`.
