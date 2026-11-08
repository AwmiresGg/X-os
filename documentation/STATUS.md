# X-OS Implementation Status

Last updated: 2026-11-07 · Build: `x-os-0.1.0-dev-desktop-amd64.iso` (1.5 GB,
sha256 `d571878df693b573f61c36d8ad30ca464841326e56b6418116ed9ab79fc1a18d`, built locally;
CI builds the same recipe as the `x-os-desktop-iso` artifact) ·
Release state: **INTERNAL TESTING** (see `releases/STATE.md`, `RELEASE-GATES.md`)

Test levels: **U** unit tested · **R** rendered offscreen with the image's own Qt ·
**VM** tested in a virtual machine (QEMU, software emulation) · **HW** physical hardware ·
**—** not tested.

## End-to-end install (VM, Secure Boot enforced)

Run on 2026-11-07 with OVMF + Microsoft keys, Secure Boot **on** for every step, 30 GiB
blank virtual disk, no network:

| Step | Result | Evidence |
|---|---|---|
| Live boot menu (signed GRUB in lockdown, X-OS theme with GRUB's built-in font) | pass | `images/vm-boot-menu-secure-boot.png` |
| Same menu without Secure Boot (Inter fonts) | pass | `images/vm-boot-menu.png` |
| Live session → X-OS Setup (language, keyboard + Persian, Wi-Fi page, appearance, apps) | pass | — |
| Installer: welcome, location, keyboard, erase disk, user, summary, confirmation dialog | pass | `images/vm-installer-welcome.png`, `images/vm-installer-partitions.png` |
| Installation (unpack, bootloader with shim + signed GRUB, users) + slideshow | pass (~12 min under emulation) | `images/vm-installer-slides.png` |
| Finish page with "Restart now" | pass | — |
| Installed system: X-OS boot menu under Secure Boot | pass | `images/vm-installed-boot-menu-secure-boot.png` |
| Installed system: X-OS splash (Plymouth) | pass | `images/vm-installed-splash.png` |
| Installed system: X-OS login screen, session "X-OS", password login | pass | `images/vm-installed-login.png` |
| Installed system: X-OS desktop (menu bar + dock), terminal works, user has sudo | pass | `images/vm-installed-desktop.png` |

The installer sidebar/navigation QML is also rendered offscreen against mock Calamares
objects (`testing/installer/render_calamares_panels.py`, `images/installer-panels-render.png`).

## Works today

| Feature | Level | Evidence |
|---|---|---|
| Reproducible ISO build pipeline (Debian 13, core + desktop variants), re-runnable stages | VM | `build/build.sh`; CI workflow `build-iso.yml` |
| Hybrid ISO boots on UEFI, BIOS and UEFI with Secure Boot enforced | VM | `testing/results/*-{bios,uefi,uefi-sb}-*.json` |
| Live session (Plasma 6 Wayland + X-OS shell: menu bar, dock, Control Center) | VM | `images/vm-live-session-shell.png`, `images/vm-control-center.png` |
| Dock launch "droplet" animation and floating active circle | U, VM | `testing/unit/dock.test.mjs` (18 tests), `images/vm-dock-launch-konsole.png` |
| Window controls (X-OS Aurorae decoration) | VM | `images/vm-window-controls.png` |
| X-OS Setup wizard (language, keyboard, Wi-Fi, appearance, browsers) | U, VM | `testing/unit/test_setup.py` |
| Installer (Calamares with X-OS branding, QML sidebar/navigation, slides) | R, VM | section above |
| Boot menu theme (live + installed), Plymouth splash, login screen | U, VM | `testing/unit/test_boot_experience.py`, section above |
| Windows apps: detection, rating, plan; real 7-Zip `.exe` and `.msi` installs | U, VM | `testing/unit/test_compat.py`; VM run with Wine 10 |
| Hardware discovery `xos-hwprobe`, performance profiles `xos-profile` | U, VM | `test_hardware.py`, `test_profiles` |
| Boot self-test `xos-selftest` (systemd, network, firewall, live user, desktop session, Secure Boot) | U, VM | `test_selftest.py` |
| Firewall (ufw) on by default, deny incoming | VM | self-test `firewall` |

## Implemented but NOT yet tested end-to-end

* Installing next to Windows (dual boot, "Install alongside" / os-prober entry): the
  installer offers it, but only blank virtual disks were used. **Back up first.**
* Disk encryption option in the installer.
* Downloading Chrome during/after install (needs network; fingerprints are pinned).
* GRUB entries other than the default (Lite, safe graphics, from memory, self-test).
* `xos-profile apply` effects on a desktop system.

## Never tested (needs a person with hardware)

Everything at level **HW**: Wi-Fi, Bluetooth, audio, real GPUs, touchpads,
sleep/wake, batteries, brightness, booting from a real USB stick, real firmware
Secure Boot implementations. The development environment has no physical hardware
and no KVM (see `ENVIRONMENT.md`).

## Known issues

| Severity | Issue |
|---|---|
| Medium | Builds are not bit-reproducible (mirror moves; no SOURCE_DATE_EPOCH). |
| Low | Between the splash and the login screen the screen is briefly black with a text cursor (long under emulation). Handing the splash to SDDM (`plymouth quit --retain-splash` + `Conflicts=plymouth-quit`) hung the boot in a VM test, so it is not used. |
| Low | Under Secure Boot the boot menu uses GRUB's built-in font instead of Inter (lockdown refuses to load fonts from disk). |
| Low | The installer's time-zone map and keyboard preview are Calamares' own widgets and do not follow the dark theme. |
| Low | Calamares paints partition names in black, so the partition legend sits on a light strip. |
| Info | VM timings come from software emulation (TCG) and are not performance data. |
