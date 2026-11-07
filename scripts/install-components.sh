#!/usr/bin/env bash
# Install X-OS components from this source tree into a target root filesystem.
#   scripts/install-components.sh <target-root>
# Used by build/build.sh (target = build chroot) and for development installs
# into a VM. Refuses to install into / unless XOS_ALLOW_HOST_INSTALL=1.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:?usage: install-components.sh <target-root>}"
DEST="$(cd "$DEST" && pwd)"
if [[ "$DEST" == "/" && "${XOS_ALLOW_HOST_INSTALL:-0}" != 1 ]]; then
    echo "refusing to install into the host system (/)" >&2; exit 1
fi

inst() { install -D -m "$1" "$2" "$DEST/$3"; }

# Python library (byte-compiled at first import; stdlib only).
rm -rf "$DEST/usr/lib/xos/python/xos"
mkdir -p "$DEST/usr/lib/xos/python"
cp -r "$SRC/lib/python/xos" "$DEST/usr/lib/xos/python/"
find "$DEST/usr/lib/xos/python" -name '__pycache__' -prune -exec rm -rf {} +

for t in "$SRC"/bin/xos-*; do inst 0755 "$t" "usr/bin/$(basename "$t")"; done
inst 0755 "$SRC/lib/xos-profile-boot"                  usr/lib/xos/profile-boot
inst 0755 "$SRC/lib/xos-live-session"                 usr/lib/xos/live-session
inst 0755 "$SRC/compatibility/wine/xos-compat-setup"   usr/sbin/xos-compat-setup
for u in "$SRC"/lib/systemd/*.service; do inst 0644 "$u" "lib/systemd/system/$(basename "$u")"; done

inst 0644 "$SRC/compatibility/database/apps.json"      usr/share/xos/compat/apps.json
for d in "$SRC"/documentation/*.md; do [[ -e "$d" ]] && inst 0644 "$d" "usr/share/doc/xos/$(basename "$d")"; done

# Branding assets (logo, wallpapers) - all variants.
inst 0644 "$SRC/icons/xos/brand/x-os-logo.svg" usr/share/xos/icons/xos/brand/x-os-logo.svg
for w in dark light; do
    inst 0644 "$SRC/themes/liquid-glass/wallpapers/x-os-$w.svg" "usr/share/wallpapers/X-OS/x-os-$w.svg"
done
# Design-system QML module (XOS.Theme) and the icon family.
rm -rf "$DEST/usr/share/xos/qml" "$DEST/usr/share/xos/icons/xos"
mkdir -p "$DEST/usr/share/xos/qml" "$DEST/usr/share/xos/icons/xos"
cp -r "$SRC/ui/qml/." "$DEST/usr/share/xos/qml/"
for d in symbolic apps brand; do
    [[ -d "$SRC/icons/xos/$d" ]] && cp -r "$SRC/icons/xos/$d" "$DEST/usr/share/xos/icons/xos/"
done
inst 0644 "$SRC/build/tmpfiles/xos.conf" usr/lib/tmpfiles.d/xos.conf

# Desktop variant: dock, setup wizard, installer.
if [[ "${XOS_VARIANT:-core}" == desktop ]]; then
    mkdir -p "$DEST/usr/share/xos/dock" "$DEST/usr/share/xos/setup"
    cp -r "$SRC/desktop/dock/." "$DEST/usr/share/xos/dock/"
    cp -r "$SRC/installer/xos-setup/." "$DEST/usr/share/xos/setup/"
    printf '#!/bin/sh\nexec /usr/bin/python3 /usr/share/xos/setup/xos_setup_app.py "$@"\n' > "$DEST/usr/bin/xos-setup-gui"
    chmod 0755 "$DEST/usr/bin/xos-setup-gui"
    inst 0644 "$SRC/installer/desktop/xos-setup.desktop"            usr/share/applications/xos-setup.desktop
    inst 0644 "$SRC/installer/desktop/xos-setup-live-autostart.desktop" etc/xdg/autostart/xos-setup-live.desktop
    inst 0644 "$SRC/desktop/autostart/xos-setup-user.desktop"        etc/xdg/autostart/xos-setup-user.desktop
    # X-OS shell (menu bar + dock) replaces the Plasma panel.
    rm -rf "$DEST/usr/share/xos/shell"
    mkdir -p "$DEST/usr/share/xos/shell"
    cp -r "$SRC/desktop/shell/." "$DEST/usr/share/xos/shell/"
    printf '#!/bin/sh\nexec /usr/bin/python3 /usr/share/xos/shell/xos_shell.py "$@"\n' > "$DEST/usr/bin/xos-shell"
    chmod 0755 "$DEST/usr/bin/xos-shell"
    inst 0644 "$SRC/desktop/autostart/xos-shell.desktop" etc/xdg/autostart/xos-shell.desktop
    # Window decoration (KWin Aurorae themes XOS-Dark / XOS-Light)
    for t in "$SRC"/themes/decoration/*/; do
        n="$(basename "$t")"
        rm -rf "$DEST/usr/share/aurorae/themes/$n"
        mkdir -p "$DEST/usr/share/aurorae/themes/$n"
        cp -r "$t". "$DEST/usr/share/aurorae/themes/$n/"
    done
    rm -rf "$DEST/usr/share/plasma/look-and-feel/org.xos.desktop"
    mkdir -p "$DEST/usr/share/plasma/look-and-feel"
    cp -r "$SRC/themes/plasma/look-and-feel/org.xos.desktop" "$DEST/usr/share/plasma/look-and-feel/"
    inst 0644 "$SRC/themes/plasma/kdeglobals" etc/xdg/kdeglobals
    # Native QML plugin sources; compiled inside the image by build/hooks/chroot/30-native.sh
    rm -rf "$DEST/usr/src/xos-native"
    mkdir -p "$DEST/usr/src/xos-native"
    cp -r "$SRC/desktop/native/." "$DEST/usr/src/xos-native/"
    rm -rf "$DEST/etc/calamares"
    mkdir -p "$DEST/etc/calamares/branding"
    cp "$SRC/installer/calamares/settings.conf" "$DEST/etc/calamares/"
    cp -r "$SRC/installer/calamares/modules" "$DEST/etc/calamares/"
    cp -r "$SRC/installer/calamares/branding/xos" "$DEST/etc/calamares/branding/"
fi
echo "X-OS components installed into $DEST"
