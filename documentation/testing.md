# X-OS Testing

Test levels used in every status report (never mixed up):

| Level | Meaning |
|---|---|
| Unit tested | Logic tested against fixtures/mocks (`scripts/run-tests.sh`) |
| Integration tested | Real services exercised together on a running X-OS system |
| VM tested | Booted and checked in QEMU (`testing/vm/boot_test.py`); evidence in `testing/results/` |
| Physical hardware tested | Done by a person on a real machine per HARDWARE-TESTING.md; recorded in `testing/hcl/` |
| Not tested | Everything else |

## Boot self-test

`xos-selftest` checks os-release, systemd state, live medium, NetworkManager,
connectivity, firewall, hardware detection, disk tools, Wi-Fi and Bluetooth (SKIP
when absent). Run it any time with `sudo xos-selftest`, or boot the
"Hardware self-test" menu entry. Report: `/var/log/xos-selftest.json`.

The VM harness triggers it through QEMU fw_cfg (`opt/org.x-os.selftest=poweroff`)
so the default boot entry — the one users get — is the one tested.
