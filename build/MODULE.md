# build

**Status:** Implemented (core variant); desktop variant untested

**Dependencies:** debootstrap, squashfs-tools, xorriso, grub-pc-bin, grub-efi-amd64-bin, mtools (host)

**Tests:** shellcheck (warnings gate); end-to-end build of core ISO; VM boot test

**Known issues / limitations:**
- Build is not bit-reproducible (timestamps, package versions float with the mirror). Plan: snapshot.debian.org pinning + SOURCE_DATE_EPOCH.

**Acceptance criteria:**
- [ ] `sudo build/build.sh` builds an ISO from a clean checkout
- [ ] ISO boots on BIOS and UEFI in QEMU
- [ ] No writes outside the project tree

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
