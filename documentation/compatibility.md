# Running Windows Applications on X-OS

1. Install the compatibility layer once: `sudo xos-compat-setup`.
2. Inspect an installer: `xos-compat plan ~/Downloads/setup.exe` — shows format,
   rating, prefix, dependencies and warnings. Nothing is executed.
3. Install: `xos-compat install ~/Downloads/setup.exe` — asks you to type `install`
   after showing the plan and the file's SHA-256.

Each app gets its own Wine prefix in `~/.local/share/xos/prefixes/<app>`.
Wine is **not** a security sandbox: Windows programs can read your home folder.

Ratings: platinum, gold, silver, bronze, unsupported, untested. Current database
ratings are starting points from public community reports and are marked
`verified_on_xos: false` until tested on X-OS.

Not supported: Windows drivers, kernel anti-cheat (Vanguard, some BattlEye/EAC
configurations), Microsoft Store licensing, Adobe Creative Cloud installers.
