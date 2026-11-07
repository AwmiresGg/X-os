# compatibility

**Status:** Partial: installer detection (EXE/MSI/MSIX/MSIXBUNDLE/APPX/BAT/CMD/COM), compatibility DB, install planner, CLI installer (xos-compat); Wine not in the image yet

**Dependencies:** wine, wine32, winetricks (installed on demand by xos-compat-setup); Proton via Steam; DXVK/VKD3D-Proton

**Tests:** testing/unit/test_compat.py (detection on synthetic PE/OLE/ZIP files, DB validation, planning)

**Known issues / limitations:**
- `xos-compat install` has not been integration-tested with real installers (needs Wine in a VM).
- MSIX unpacking not implemented.
- No file-manager double-click integration (MIME handler) yet.
- All DB ratings are unverified starting points (verified_on_xos=false).

**Acceptance criteria:**
- [ ] Double-click EXE/MSI in Files -> plan -> consent -> per-app prefix -> launcher entry
- [ ] ≥10 apps tested with recorded results
- [ ] Uninstall/repair

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
