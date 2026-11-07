# X-OS Architecture

X-OS is a Debian-based desktop operating system. It does not fork the kernel or
rewrite proven subsystems. Its value is the **integration layer**: a coherent
shell, one Control Center, a Windows compatibility engine, a unified store and
safe install/recovery, under the original *Liquid Glass* design language.

## 1. Layer model

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Experience   X-OS Shell (QML on KWin/Plasma): top bar, Signature Dock,   │
│              launcher, search, notifications, quick settings, Mission    │
│              Control  ·  Liquid Glass theme (Kvantum/Plasma/QML tokens)  │
├──────────────────────────────────────────────────────────────────────────┤
│ Applications Control Center · Device/Disk/Network/Bluetooth/VPN managers │
│              X-Store · Compatibility Engine UI · Task Manager · AI       │
├──────────────────────────────────────────────────────────────────────────┤
│ X-OS services  xos-* backends (lib/python/xos): hardware, profiles,      │
│              compat, selftest; D-Bus service org.xos.System1 (planned)   │
│              privileged actions only through polkit-checked helpers      │
├──────────────────────────────────────────────────────────────────────────┤
│ Platform     KDE Frameworks 6 · Qt 6 · KWin (Wayland) · Xwayland ·       │
│              NetworkManager · BlueZ · PipeWire/WirePlumber · UDisks2 ·   │
│              power-profiles-daemon · Flatpak · APT/dpkg · Wine/Proton    │
├──────────────────────────────────────────────────────────────────────────┤
│ Base         Debian 13 "trixie" · systemd · udev · polkit · ufw/nftables │
│              AppArmor · Mesa · linux-image-amd64 · GRUB (BIOS + UEFI)    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Design rules
1. **No fake controls.** Every Control Center control calls a real platform API
   (NetworkManager D-Bus, BlueZ D-Bus, UDisks2, PipeWire, KScreen, systemd, polkit).
   A setting that cannot yet be implemented is not shown.
2. **Reuse, then integrate.** KDE components (Dolphin, Konsole, Partition Manager,
   plasma-nm, bluedevil, KScreen) are used where they are excellent. X-OS adds the
   unified surface and theme instead of rewriting them.
3. **Unprivileged UI, privileged helpers.** UIs never run as root. Destructive or
   system-wide operations go through small helpers authorized by polkit actions in
   `security/polkit/` (`org.xos.*`).
4. **Testable backends.** Backends take a filesystem `root` and are unit-tested
   against fixture trees. UIs are thin.
5. **Low-end first.** Stdlib-only Python for backends, QML shell with a static
   rendering path; profiles decide effects, never security.

## 2. Component decisions

| Area | Choice | Why / alternatives considered |
|---|---|---|
| Base | Debian 13 stable | Long support, huge archive, signed repos, non-free-firmware component. Ubuntu adds snaps; Arch is not stable enough for a "never fail" release target. |
| Kernel | Debian `linux-image-amd64` | Signed for Secure Boot, broad driver coverage. trixie-backports kernel offered for very new hardware. No custom kernel without a measured reason. |
| Desktop foundation | KDE Plasma 6 (Wayland) + KWin | Most capable Wayland compositor with effect/scripting APIs and QML-native shell. GNOME Shell is less customizable for a custom dock/top bar. |
| Shell UI | QML (Qt 6) running in Plasma shell / as layer-shell surfaces | GPU-accelerated scene graph, Shapes for the dock geometry, software fallback via `QT_QUICK_BACKEND=software`. |
| Display | Wayland default, X11 session kept | Some Wine/legacy apps and NVIDIA setups still need X11. |
| Network | NetworkManager (+ plasma-nm), WireGuard/OpenVPN/L2TP plugins | Standard D-Bus API, VPN plugins, hotspot, connectivity check. |
| Firewall | ufw (nftables backend) | Simple model, used by Plasma's firewall module; default deny-incoming. |
| Bluetooth | BlueZ + bluedevil | Only maintained stack. |
| Audio | PipeWire + WirePlumber | Per-app volume, Bluetooth codecs, pro-audio, Flatpak portals. |
| Storage | UDisks2, parted, smartmontools, cryptsetup | D-Bus API usable without root; KDE Partition Manager for advanced edits. |
| Packages | APT/dpkg + Flatpak (Flathub) | DEB for system, Flatpak for sandboxed desktop apps and vendors that publish there. AppImage supported as a file type. |
| Windows apps | Wine (Debian) + winetricks; Proton via Steam; DXVK/VKD3D-Proton; Bottles via Flatpak for advanced users | See `compatibility/MODULE.md`. |
| Installer | Calamares (Debian settings), X-OS branded | Mature, handles dual-boot/OS-prober, LUKS, BIOS+UEFI. Writing a new installer would add risk to the most dangerous step. |
| Live system | live-boot + live-config | Debian's maintained live stack; `toram`, persistence. |
| Snapshots | Btrfs root + Snapper (default install), Timeshift rsync mode for ext4 | Transactional-ish rollback with GRUB boot entries (grub-btrfs). |

## 3. Build pipeline

`build/build.sh` (see `documentation/BUILDING.md`):

```
debootstrap (minbase, trixie) ─► chroot: apt install package-lists/*.list
  ─► scripts/install-components.sh (X-OS code)  ─► build/overlay  ─► hooks/chroot/*.sh
  ─► mksquashfs (zstd) ─► staging: live/{vmlinuz,initrd.img,filesystem.squashfs}
  ─► grub-mkrescue: hybrid ISO (El Torito BIOS + EFI ESP; dd-able to USB)
```
Variants: `core` (CLI, for fast boot verification) and `desktop`.
All work happens inside `build/work/` (git-ignored). The script refuses work
directories outside the project and never touches block devices.

## 4. Boot and live session

GRUB menu: *Try without installing* (default), LITE profile, safe graphics
(`nomodeset`), load-to-RAM, hardware self-test. The live session never mounts
internal disks read-write automatically (udisks2 default policy requires the user
to mount). `xos-profile-boot.service` picks a performance profile from the kernel
command line or the hardware. `xos-selftest.service` runs only when explicitly
requested.

## 5. Security model

* No root login; the first user is in `sudo`. Live user `xos` has no password.
* ufw enabled: incoming DROP, outgoing ACCEPT.
* AppArmor (Debian default) enforced; Flatpak sandboxes desktop apps; each Windows
  application gets its own Wine prefix (separate `C:` drive and registry) — *Wine is
  not a security sandbox* and the UI says so.
* Signed APT repositories only; third-party vendor repos (Google, Spotify,
  Windscribe…) are added only on explicit user action with their published key.
* No telemetry. No cloud account. AI assistant is local-only and optional.

## 6. Module map

Code lives in the module directories listed in the master spec; shared Python
backends live in `lib/python/xos` (one importable, testable package — a justified
addition to the spec's tree) with thin launchers in `bin/`. Each module has a
`MODULE.md` stating status, dependencies, tests, known issues and acceptance
criteria. The central matrix is `documentation/STATUS.md`.
