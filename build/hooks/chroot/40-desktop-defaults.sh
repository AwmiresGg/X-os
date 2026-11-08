#!/bin/sh
# System-wide desktop defaults (users can still change everything in System Settings).
set -eu
[ "${XOS_VARIANT}" = "desktop" ] || exit 0
k() { kwriteconfig6 --file /etc/xdg/kwinrc --group org.kde.kdecoration2 --key "$1" "$2"; }
# X-OS window controls: close, minimize, maximize on the left; nothing on the right.
k library org.kde.kwin.aurorae
k theme __aurorae__svg__XOS-Dark
k ButtonsOnLeft XIA
k ButtonsOnRight ""
test -f /usr/share/aurorae/themes/XOS-Dark/decoration.svg

# Soft, rounded windows (macOS-like): squircle corners, a faint light hairline instead of
# the effect's default solid black outline. Only when the effect was built (hook 30).
if ls /usr/lib/*/qt6/plugins/kwin/effects/plugins/kwin4_effect_shapecorners.so >/dev/null 2>&1; then
    kwriteconfig6 --file /etc/xdg/kwinrc --group Plugins --key kwin4_effect_shapecornersEnabled true
    r() { kwriteconfig6 --file /etc/xdg/kwinrc --group Round-Corners --key "$1" "$2"; }
    r Size 14
    r InactiveCornerRadius 14
    r UseSquircleShape true
    r OutlineColor "255,255,255"
    r InactiveOutlineColor "255,255,255"
    r ActiveOutlineAlpha 30
    r InactiveOutlineAlpha 18
    r SecondOutlineThickness 0
    r InactiveSecondOutlineThickness 0
fi

# X-OS login screen
mkdir -p /etc/sddm.conf.d
printf '[Theme]\nCurrent=xos\nCursorTheme=breeze_cursors\n' > /etc/sddm.conf.d/10-xos.conf
test -f /usr/share/sddm/themes/xos/Main.qml

# Lock screen uses the X-OS wallpaper
kwriteconfig6 --file /etc/xdg/kscreenlockerrc --group Greeter --group Wallpaper --group org.kde.image \
    --group General --key Image "file:///usr/share/wallpapers/X-OS/x-os-dark.svg"
