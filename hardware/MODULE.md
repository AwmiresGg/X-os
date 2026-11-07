# hardware

**Status:** Implemented backend: xos-hwprobe (PCI/USB/input/disk/net/battery/CPU/RAM, missing-driver detection)

**Dependencies:** sysfs, procfs, pci.ids/usb.ids

**Tests:** testing/unit/test_hardware.py; runs in VM self-test

**Known issues / limitations:**
- No physical hardware tested. HCL is empty.

**Acceptance criteria:**
- [ ] Hardware report on ≥3 physical machines recorded in the HCL

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
