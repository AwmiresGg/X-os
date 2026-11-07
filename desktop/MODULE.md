# desktop

X-OS shell: **thin top menu bar** + **floating bottom dock**, drawn by `xos-shell`
(`desktop/shell/`), replacing the Plasma panel. Design: `documentation/design/`.

**Status:** In progress — runs in the live X-OS session (VM, Plasma 6.3 Wayland, 2026-11-07):
Plasma panel absent, menu bar shows real network/volume/clock state and the active app name from
the KWin tracker, dock shows the running app in the cradled circle
(`documentation/images/vm-live-session-shell.png`). Interactions (menus, dock clicks,
blur) inside the VM not yet exercised.

## Architecture

| Part | File | Notes |
|---|---|---|
| Host process | `shell/xos_shell.py` | PySide6; one process; status polled on a worker thread (battery 30 s, network 4 s, Bluetooth 10 s, audio 2 s, brightness/trash 10 s) |
| Shell surfaces | `shell/qml/Shell.qml` + `XOS.Platform.ShellWindow` | Wayland: `org.kde.layershell` (Debian `qml6-module-org-kde-layershell`). Menu bar anchored top, reserves 30 px. Dock anchored bottom with an 8 px margin (floating), reserves its height. Popovers on one overlay surface (click outside / Esc closes). X11 fallback: frameless always-on-top windows |
| Menu bar | `shell/qml/MenuBar.qml` | X-OS menu · active app name · Window menu · battery % · network · Bluetooth · volume · search (KRunner) · Control Center · date/time |
| Dock | `shell/qml/DockBar.qml` | pinned + running apps grouped per app; one accent circle in a concave cradle over the active app; running dots; Trash; right-click menu; tooltips; keyboard focus |
| Popovers | `shell/qml/Popovers.qml` | X-OS menu (with Restart/Shut Down confirmation), Window, battery, network, Bluetooth, sound, Control Center, calendar, dock context menu |
| Status / actions | `lib/python/xos/shellstatus.py` | sysfs battery/backlight, `nmcli`, `rfkill`, `wpctl`, logind `SetBrightness`, `systemctl`/`loginctl`, Plasma logout |
| Windows | `lib/python/xos/windows.py`, `shell/kwin/xos-windows` | KWin tracker script → D-Bus `org.xos.Shell /Windows update(json)`; commands via one-shot KWin scripts (UUID-validated ids) |
| Default layout | `themes/plasma/look-and-feel/org.xos.desktop` | Plasma layout with no panel, X-OS wallpaper, dark scheme |

## Settings (Control Center › Dock & Menu bar)

Dock transparency, menu-bar transparency (clamped so content stays readable), dock icon size,
Dark Mode, Less Motion. Stored in `~/.config/xos/shell.json`.

## Tests

| What | Level |
|---|---|
| Status parsing (battery incl. peripheral batteries ignored, nmcli, rfkill, wpctl, backlight, power commands) | Unit — `testing/unit/test_shellstatus.py` |
| Window model, grouping, .desktop parsing, KWin command injection rejected | Unit — `testing/unit/test_windows.py` |
| Cradle geometry | Unit — `testing/unit/dock.test.mjs` |
| Design tokens (contrast, single accent, motion rules) | Unit — `testing/unit/test_design_tokens.py` |
| Menu bar, dock, X-OS menu, Control Center | Rendered offscreen (`xos-shell --preview`) |
| Starts in Plasma Wayland live session, shows real status + active window | VM (screenshot) |
| Menu/dock interactions, blur, window actions in a real session | **Not yet tested** |

## Not implemented yet (not shown in the UI either)

- **Background blur** ("frosted" glass): implemented (`desktop/native/xos-effects`, KWin blur
  protocol, cradle-shaped region; compiled into the image) but **not yet visually confirmed**: the
  test VM renders with software OpenGL, where KWin may disable its blur effect.
- **Global application menus** (File/Edit/View…): need apps to export menus (KDE appmenu/DBusMenu).
  The bar shows the active app's name and a working Window menu instead of fake menus.
- Launch "droplet" animation from the reference video (only the cradle slide is implemented).
- Dock auto-hide, drag-and-drop reordering, notification badges, live window thumbnails.
- Calendar events (the calendar shows dates only).
- The Plasma panel is removed only for **new** user profiles (the look-and-feel layout applies
  on first login); existing profiles keep their panel.
