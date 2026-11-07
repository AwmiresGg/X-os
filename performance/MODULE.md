# performance

**Status:** Implemented: profiles LITE/BALANCED/PERFORMANCE, hardware recommendation, apply (sysctl, zram, KWin, shell, power profile, optional services)

**Dependencies:** zram-tools, power-profiles-daemon (desktop)

**Tests:** testing/unit/test_hardware.py::ProfileTests

**Known issues / limitations:**
- Effects of profiles not yet measured; meaningful numbers need physical hardware.

**Acceptance criteria:**
- [ ] Idle RAM budgets in ROADMAP.md met on hardware

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
