#!/usr/bin/env bash
# Run all fast X-OS checks (no root, no VM): unit tests + static checks.
#   scripts/run-tests.sh            # everything fast
#   scripts/run-tests.sh --vm ISO   # additionally boot-test an ISO (BIOS + UEFI)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
fail=0
step() { printf '\n== %s\n' "$*"; }

step "Python unit tests"
PYTHONPATH=lib/python python3 -m unittest discover -s testing/unit -t testing/unit || fail=1

step "Dock geometry tests (Node)"
if command -v node >/dev/null; then node --test testing/unit/*.test.mjs || fail=1; else echo "node missing: SKIPPED"; fi

step "Shell scripts (shellcheck, warnings and errors)"
if command -v shellcheck >/dev/null; then
    shellcheck -S warning -x build/build.sh scripts/*.sh build/hooks/chroot/*.sh lib/xos-profile-boot \
        compatibility/wine/xos-compat-setup || fail=1
else echo "shellcheck missing: SKIPPED"; fi

step "Data files"
python3 - <<'EOF' || fail=1
import json, glob, xml.dom.minidom
json.load(open("compatibility/database/apps.json"))
for f in glob.glob("icons/**/*.svg", recursive=True) + glob.glob("themes/**/*.svg", recursive=True):
    xml.dom.minidom.parse(f)
print("json + svg OK")
EOF

if [[ ${1:-} == --vm ]]; then
    iso="${2:?--vm needs an ISO path}"
    for fw in bios uefi; do
        step "VM boot test ($fw)"
        testing/vm/boot_test.py "$iso" --firmware "$fw" || fail=1
    done
fi

echo
if ((fail)); then echo "SOME CHECKS FAILED"; else echo "ALL CHECKS PASSED"; fi
exit $fail
