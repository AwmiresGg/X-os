# boot

**Status:** Implemented: GRUB live menu (try, LITE, safe graphics, toram, self-test, UEFI setup)

**Dependencies:** GRUB 2.12, live-boot

**Tests:** VM boot test (BIOS/UEFI)

**Known issues / limitations:**
- Menu is text-only; graphical GRUB theme and Plymouth boot animation not started.

**Acceptance criteria:**
- [ ] Default entry boots to a live session without touching internal disks
- [ ] Themed menu and boot splash

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
