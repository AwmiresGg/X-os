#!/bin/sh
# Compile X-OS native plugins against the image's own Qt/KF6/KWin, install them, then remove
# the compilers and -dev packages again so the image carries no build tools.
set -eu
[ "${XOS_VARIANT}" = "desktop" ] || exit 0
[ -d /usr/src/xos-native ] || exit 0
BUILD_DEPS="g++ make cmake extra-cmake-modules qt6-base-dev qt6-declarative-dev libkf6windowsystem-dev
 git gettext qt6-base-private-dev qt6-base-dev-tools libkf6configwidgets-dev libkf6kcmutils-dev kwin-dev"
# Rounded window corners (squircle) + soft outline: "KDE Rounded Corners" KWin effect,
# GPL-3.0, https://github.com/matinlotfali/KDE-Rounded-Corners - pinned to v0.11.0.
KRC_URL=https://github.com/matinlotfali/KDE-Rounded-Corners
KRC_COMMIT=66d7ce91a4f26062bba91bc7274ba85b6211391f
apt-mark showmanual > /tmp/xos-manual-before
# shellcheck disable=SC2086
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $BUILD_DEPS
cmake -S /usr/src/xos-native/xos-effects -B /tmp/xos-effects-build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/xos-effects-build -j"$(nproc)"
install -d /usr/share/xos/qml/XOS/Effects
install -m 0644 /tmp/xos-effects-build/libxoseffects.so /tmp/xos-effects-build/qmldir \
    /tmp/xos-effects-build/xoseffects.qmltypes /usr/share/xos/qml/XOS/Effects/

# The rounded-corners effect is cosmetic: if fetching or building it fails, the image is still
# built (windows keep KWin's normal corners) and the log says so.
if git clone -q "$KRC_URL" /tmp/krc && git -C /tmp/krc checkout -q "$KRC_COMMIT" \
   && cmake -S /tmp/krc -B /tmp/krc/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr \
   && cmake --build /tmp/krc/build -j"$(nproc)" && cmake --install /tmp/krc/build; then
    echo "x-os: rounded window corners effect installed ($KRC_COMMIT)"
else
    echo "x-os: WARNING rounded window corners effect not built; windows keep square corners" >&2
fi
rm -rf /tmp/krc

# Remove only what this hook added.
for p in $BUILD_DEPS; do
    grep -qx "$p" /tmp/xos-manual-before || apt-mark auto "$p" >/dev/null 2>&1 || true
done
DEBIAN_FRONTEND=noninteractive apt-get -y autoremove --purge
rm -rf /tmp/xos-effects-build /tmp/xos-manual-before /usr/src/xos-native
test -f /usr/share/xos/qml/XOS/Effects/libxoseffects.so
