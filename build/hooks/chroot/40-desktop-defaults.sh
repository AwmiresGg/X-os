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

# X-OS login screen
mkdir -p /etc/sddm.conf.d
printf '[Theme]\nCurrent=xos\nCursorTheme=breeze_cursors\n' > /etc/sddm.conf.d/10-xos.conf
test -f /usr/share/sddm/themes/xos/Main.qml

# Lock screen uses the X-OS wallpaper
kwriteconfig6 --file /etc/xdg/kscreenlockerrc --group Greeter --group Wallpaper --group org.kde.image \
    --group General --key Image "file:///usr/share/wallpapers/X-OS/x-os-dark.svg"
