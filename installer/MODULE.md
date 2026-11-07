# installer

**Status:** In progress — X-OS Setup wizard + Calamares installer run end-to-end in a VM
(see "Tested" below). Not released: installation stays gated by RELEASE-GATES.md (gate E).

## Pieces

| Piece | Where | What it does |
|---|---|---|
| X-OS Setup (wizard) | `installer/xos-setup/` | First screen of the live USB: language, keyboard layouts, Wi-Fi, theme + wallpaper, browsers, Try / Install. English + Persian (RTL); 8 languages listed |
| Setup backend | `lib/python/xos/setup.py` | Validated choices → `/run/xos/setup-choices.json`; Wi-Fi via NetworkManager D-Bus (password never on argv/in files); keyboard + appearance for the session; locale/keyboard for the target |
| Browser installer | `lib/python/xos/browsers.py` | Firefox (packages.mozilla.org) and Chrome (dl.google.com) from the vendors' signed repos; keys pinned by fingerprint; `Signed-By` scoping |
| Calamares config | `installer/calamares/` | X-OS branding + slideshow; no preselected partitioning; summary + "Install now?" confirmation; EFI + BIOS GRUB; os-prober on (dual boot); LUKS option |
| Post-install | `shellprocess@xos-prepare/xos-apply`, `xos-setup apply-target`, `xos-firstboot.service` | Copy choices into target, set locale/keyboard, download browsers; retry on first boot when offline |
| Live session | `lib/xos-live-session` | Auto-login, empty live password, no screen lock, no dim/blank/suspend |

## Tested

| What | Level | Evidence |
|---|---|---|
| Choices validation, Wi-Fi parsing/settings, key pinning (real Google + Mozilla keys accepted, wrong/extra/garbage keys rejected), keyboard commands | Unit | `testing/unit/test_setup.py` |
| Wizard renders (EN/FA, dark/light, RTL) | Rendered offscreen | `documentation/images/setup-*.png` |
| Live USB auto-logs into Plasma and opens X-OS Setup | VM (UEFI, 4 GiB, Westmere CPU) | `testing/vm/install_flow.sh` screenshots |
| Language switch to Persian (live RTL), keyboard layouts applied (tray shows us/ir; switching via tray types Persian) | VM | same |
| Light theme + X-OS wallpaper applied to the real desktop | VM | same |
| Wi-Fi page with no adapter ("use Ethernet") | VM | same |
| Installer starts in the chosen language (Persian) with X-OS branding | VM | same |
| Partition page: nothing preselected, exact device shown, summary lists every operation, final confirmation | VM | same |

## Not tested / known issues

- **Physical hardware: not tested at all** (Wi-Fi connect, real disks, dual boot with real Windows).
- Alt+Shift layout switching: configured (`grp:alt_shift_toggle`) but QEMU's synthetic key chord did not
  trigger it; switching through the tray works. Must be verified on a real keyboard.
- Browser downloads after install not exercised end-to-end (test VM network is isolated by design);
  offline → first-boot retry path is the one exercised in the VM.
- Dual boot / "Install alongside" not yet tested (needs a VM disk with Windows installed).
- Calamares' own Persian translation shows raw `%1` / `TextLabel` in two strings (upstream).
- Calamares window does not mirror to RTL (upstream behaviour).
- Secure Boot on the **installed** system (grub-install with shim-signed) not yet tested in the VM.

## Acceptance criteria (gate E)
- [ ] Automatic, manual and alongside install on virtual disks, each booting afterwards
- [ ] Alongside install leaves an existing Windows partition byte-identical (checksummed in VM)
- [ ] BIOS + UEFI
- [ ] LUKS option boots with passphrase
- [ ] Browsers installed when online during install; installed on first boot when offline
- [ ] Physical machines: see documentation/HARDWARE-TESTING.md
