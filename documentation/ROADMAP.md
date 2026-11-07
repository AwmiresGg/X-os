# X-OS Roadmap and Milestones

Each milestone has exit criteria that must be demonstrated with recorded evidence
(`testing/results/`) before the next milestone starts. Critical bugs block progress.

| # | Milestone | Phase | Exit criteria | State |
|---|---|---|---|---|
| M0 | Environment + architecture | 1 | Environment report, architecture, roadmap, repo structure, module docs | **Done** |
| M1 | **First bootable core ISO** | 2 | Reproducible build from clean checkout; hybrid ISO boots in QEMU on **BIOS and UEFI** at 2 GiB RAM; self-test PASS (systemd running, NetworkManager online, firewall active, disk tools present); clean power-off | In progress (see STATUS.md) |
| M2 | Desktop ISO | 2-3 | Plasma Wayland session auto-starts in live mode; X-OS Liquid Glass theme; SDDM themed; VM screenshot evidence; LITE profile boots at 2 GiB | Next |
| M3 | Signature Dock + top bar | 3 | QML dock with concave liquid geometry, persistent active state, running indicators, grouping, auto-hide, settings; 60 FPS target on GPU, static path on software rendering; geometry unit tests | Prototype in `desktop/dock` |
| M4 | Control Center v1 | 4 | Overview, Network/Wi-Fi/Ethernet/VPN, Bluetooth, Display, Sound, Power, Device Manager, Disk Manager (read-only first), Services, Startup, Users — all wired to real D-Bus APIs; integration tests in VM |  |
| M5 | Disk Manager write operations | 4 | Partition/format/resize/LUKS via UDisks2 + polkit with the safety rules in SAFETY.md; destructive-path tests on virtual disks only |  |
| M6 | Files + built-in apps | 5 | Themed Dolphin, Konsole, Kate/KWrite, Ark, Gwenview, Okular, Haruna, Spectacle, KCalc, Task Manager; archive formats verified |  |
| M7 | Windows Compatibility Engine | 6 | Double-click EXE/MSI → detection → plan → consent → per-app prefix → launcher entry; uninstall/repair; diagnostics; ≥10 apps tested in VM with recorded results |  |
| M8 | X-Store | 7 | Catalog (DEB, Flatpak, vendor repos, PWAs, Windows apps); install/update/remove with progress; signature verification; PWA installer for Google/AI web apps |  |
| M9 | Security + recovery | 8 | Security Center (firewall, AppArmor, updates, LUKS status); Btrfs snapshots + rollback entries; recovery boot entry; backup tool |  |
| M10 | Performance | 9 | Boot time and idle RAM measured **on physical hardware** for LITE/BALANCED/PERFORMANCE; budgets met |  |
| M11 | Installer | 10 | Calamares X-OS edition: auto/manual partitioning, dual boot with OS detection, LUKS, BIOS+UEFI; tested only on virtual disks until gate E |  |
| M12 | Release candidate | 10 | All release gates in RELEASE-GATES.md passed with evidence |  |

## Size and performance budgets (to be validated on hardware, M10)

| Profile | Target hardware | Idle RAM budget (desktop) |
|---|---|---|
| LITE | 2-4 GiB RAM, any x86-64 GPU | ≤ 700 MiB |
| BALANCED | 8 GiB, Intel/AMD iGPU | ≤ 1.2 GiB |
| PERFORMANCE | 16 GiB+, dedicated or modern iGPU | no hard cap, ≤ 1.6 GiB idle |
