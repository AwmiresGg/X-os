# testing

**Status:** Implemented: unit tests (Python unittest, Node test), VM boot test harness (BIOS/UEFI, QEMU)

**Dependencies:** python3, node, qemu-system-x86, ovmf

**Tests:** scripts/run-tests.sh

**Known issues / limitations:**
- No KVM on the dev host: VM tests use TCG emulation and are slow; timings are not performance data.

**Acceptance criteria:**
- [ ] CI runs unit tests on every push

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
