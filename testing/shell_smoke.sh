#!/usr/bin/env bash
# Start the real X-OS shell (not the preview) for a few seconds under a virtual X server and
# a private D-Bus session; fail on any Python exception or QML error. Catches startup crashes
# that preview renders cannot (KWin missing, window lookup, D-Bus registration...).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log="$(mktemp)"
QT_QPA_PLATFORM=xcb HOME="$(mktemp -d)" xvfb-run -a -s "-screen 0 1440x900x24" \
    dbus-run-session -- python3 "$ROOT/desktop/shell/xos_shell.py" --smoke 6 >"$log" 2>&1
rc=$?
if [[ $rc -ne 0 ]] || grep -qE 'Traceback|TypeError|ReferenceError|qml: |\.qml:[0-9]+' "$log"; then
    echo "shell smoke test FAILED (exit $rc):"; cat "$log"; exit 1
fi
echo "shell smoke test passed"

# X-OS Settings: every page loads (demo data) without QML errors.
for page in tweaks updates security this-pc about; do
    QT_QPA_PLATFORM=xcb HOME="$(mktemp -d)" xvfb-run -a -s "-screen 0 1280x800x24" \
        python3 "$ROOT/desktop/settings/xos_settings.py" --page "$page" --preview "$(mktemp --suffix=.png)" >"$log" 2>&1
    rc=$?
    if [[ $rc -ne 0 ]] || grep -qE 'Traceback|TypeError|ReferenceError|qml: |\.qml:[0-9]+' "$log"; then
        echo "settings page $page FAILED (exit $rc):"; cat "$log"; exit 1
    fi
done
echo "settings smoke test passed"
