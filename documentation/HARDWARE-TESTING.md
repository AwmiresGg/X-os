# Physical Hardware Test Protocol

Required for release states LIVE USB VERIFIED and PHYSICAL HARDWARE VERIFIED.
Nothing in this file can be done from the cloud development environment; it
needs a person with the machine in front of them.

## Before you start (protects your computer)

1. Boot only the **live** entry. Do not run any installer.
2. In the live session run `sudo lsblk -o NAME,SIZE,FSTYPE,PARTUUID,MOUNTPOINTS > before.txt`
   and save `before.txt` to the USB stick or another machine.

## Checklist (record PASS / FAIL / N/A and notes)

| Area | How to test |
|---|---|
| Boot (UEFI) | Boots to live session with Secure Boot **off**; note model and firmware version |
| Boot (BIOS/CSM) | Same, legacy mode, if the machine supports it |
| Self-test | Boot the *Hardware self-test* entry; photograph or save `/var/log/xos-selftest.json` |
| Graphics | Native resolution, no tearing in a scrolling page; `xos-hwprobe` shows the GPU driver (amdgpu/i915/xe/nouveau) |
| Displays | External monitor detected, arrangement and scaling work |
| Wi-Fi | Scan, connect WPA2/WPA3, browse, reconnect after suspend |
| Ethernet | Link up, DHCP address, speed shown |
| Bluetooth | Pair a headset (audio) and a mouse/keyboard |
| Audio | Speakers, headphone jack switching, microphone, HDMI audio |
| Keyboard / touchpad | All keys, brightness/volume keys, two-finger scroll, tap-to-click |
| USB | Mount a USB stick read/write, unplug safely |
| Storage | `xos-hwprobe` lists internal disks correctly (model, size) — **do not modify them** |
| Sleep / wake | Suspend via lid and menu, wake within 5 s, Wi-Fi back |
| Battery | Percentage, charging state, time estimate |
| Brightness | Keys and slider |

## After testing

Run `sudo lsblk -o NAME,SIZE,FSTYPE,PARTUUID,MOUNTPOINTS > after.txt` and confirm
it is identical to `before.txt` (apart from the USB stick). Submit the results with
`xos-hwprobe --json` output as a file in `testing/hcl/<vendor>-<model>.json` plus the
filled checklist.
