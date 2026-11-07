# Release State

| Build | State | Date | Evidence |
|---|---|---|---|
| 0.1.0-dev core (sha256 `bc14a68b…`) | **INTERNAL TESTING** | 2026-11-07 | `testing/results/` — 4/4 VM boot tests PASS (BIOS/UEFI × 2/4 GiB) |

Why not VIRTUAL MACHINE VERIFIED yet: that gate also requires the desktop session
and Control Center smoke tests, which do not exist yet.

**Ready for installation: NO.** There is no installer, no physical hardware has
been tested, and Secure Boot is not supported. Use only in a VM or as a live USB.
