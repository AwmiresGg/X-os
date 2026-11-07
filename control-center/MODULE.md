# control-center

**Status:** Not started (UI). Backends: hardware discovery done (lib/python/xos/hardware.py)

**Dependencies:** NetworkManager, BlueZ, UDisks2, PipeWire, KScreen, systemd, polkit (D-Bus)

**Tests:** testing/unit/test_hardware.py (Device Manager backend)

**Known issues / limitations:**
- Device enable/disable, driver management UI not implemented.

**Acceptance criteria:**
- [ ] Every visible control changes real system state via a platform API
- [ ] No decorative controls

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
