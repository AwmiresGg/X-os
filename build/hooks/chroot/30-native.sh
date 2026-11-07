#!/bin/sh
# Compile X-OS native QML plugins against the image's own Qt/KF6, install them, then remove
# the compilers and -dev packages again so the image carries no build tools.
set -eu
[ "${XOS_VARIANT}" = "desktop" ] || exit 0
[ -d /usr/src/xos-native ] || exit 0
BUILD_DEPS="g++ make cmake extra-cmake-modules qt6-base-dev qt6-declarative-dev libkf6windowsystem-dev"
apt-mark showmanual > /tmp/xos-manual-before
# shellcheck disable=SC2086
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $BUILD_DEPS
cmake -S /usr/src/xos-native/xos-effects -B /tmp/xos-effects-build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/xos-effects-build -j"$(nproc)"
install -d /usr/share/xos/qml/XOS/Effects
install -m 0644 /tmp/xos-effects-build/libxoseffects.so /tmp/xos-effects-build/qmldir \
    /tmp/xos-effects-build/xoseffects.qmltypes /usr/share/xos/qml/XOS/Effects/
# Remove only what this hook added.
for p in $BUILD_DEPS; do
    grep -qx "$p" /tmp/xos-manual-before || apt-mark auto "$p" >/dev/null 2>&1 || true
done
DEBIAN_FRONTEND=noninteractive apt-get -y autoremove --purge
rm -rf /tmp/xos-effects-build /tmp/xos-manual-before /usr/src/xos-native
test -f /usr/share/xos/qml/XOS/Effects/libxoseffects.so
