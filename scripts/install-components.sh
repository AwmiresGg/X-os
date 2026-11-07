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
inst 0755 "$SRC/compatibility/wine/xos-compat-setup"   usr/sbin/xos-compat-setup
for u in "$SRC"/lib/systemd/*.service; do inst 0644 "$u" "lib/systemd/system/$(basename "$u")"; done

inst 0644 "$SRC/compatibility/database/apps.json"      usr/share/xos/compat/apps.json
for d in "$SRC"/documentation/*.md; do [[ -e "$d" ]] && inst 0644 "$d" "usr/share/doc/xos/$(basename "$d")"; done

# Desktop shell (QML) - only meaningful in the desktop variant.
if [[ "${XOS_VARIANT:-core}" == desktop && -d "$SRC/desktop/shell" ]]; then
    mkdir -p "$DEST/usr/share/xos/shell"
    cp -r "$SRC/desktop/shell/." "$DEST/usr/share/xos/shell/"
fi
echo "X-OS components installed into $DEST"
