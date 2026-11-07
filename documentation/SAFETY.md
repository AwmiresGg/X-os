# Installation and Disk Safety Policy

This policy is binding for every X-OS component that touches storage, boot
configuration or firmware: the build system, Disk Manager, installer, recovery
tools and the AI assistant.

## During development

* All builds run inside the project tree (`build/work/`, `releases/out/`). The build
  script refuses any other work directory and never opens block devices.
* All testing of installation and partitioning uses **virtual disks** (qcow2 files).
* X-OS is never installed onto a developer's or user's primary disk as part of
  development.
* EFI boot entries and host bootloaders are never modified.

## Disk Manager and installer rules

1. Never format, partition, resize or wipe without explicit confirmation.
2. The confirmation dialog always shows: device path (`/dev/nvme0n1`), model, serial,
   size, partition table and every partition's label, filesystem and size.
3. Destructive operations require a second confirmation that names the device
   (type-to-confirm for whole-disk wipes).
4. The disk holding the running system (`/`, `/boot`, `/boot/efi`, the live medium)
   is protected: destructive actions on it are disabled, not just warned about.
5. Partitions recognised as Windows (NTFS with `Windows\System32`, BitLocker, the
   Microsoft Reserved partition, the Windows recovery partition), macOS (APFS/HFS+)
   and other Linux systems are never modified implicitly. Resizing an NTFS partition
   requires a clean-shutdown check (no hibernation / Fast Startup) and BitLocker
   being suspended.
6. The EFI System Partition is never formatted when it contains another OS's
   bootloader; X-OS adds its own directory only.
7. Operations go through UDisks2 / polkit; the UI never runs as root.
8. Every destructive operation is logged (without secrets) to the journal.

## Before installing X-OS on a real computer

Pre-installation checklist (shown by the installer and in `documentation/INSTALL.md`):

- [ ] Your files are backed up to an external drive or cloud, and you checked the backup opens.
- [ ] You booted X-OS live from USB on this exact computer and Wi-Fi, display, keyboard,
      touchpad, audio and sleep worked.
- [ ] If keeping Windows: BitLocker recovery key saved; Fast Startup disabled; Windows shut down fully.
- [ ] You have a Windows recovery USB (or vendor recovery media) if this is your only computer.
- [ ] The X-OS build state is at least INSTALLER VERIFIED (see RELEASE-GATES.md).

**Current builds are DEVELOPMENT builds. Do not install them on a computer you depend on.**
