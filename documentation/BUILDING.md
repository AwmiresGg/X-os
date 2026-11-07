# Building and Testing X-OS

Requirements: an x86_64 Debian or Ubuntu machine (or VM/container) with root,
~25 GB free disk, network access to deb.debian.org. KVM makes VM tests ~20x faster
but is optional.

```bash
git clone https://github.com/AwmiresGg/X-os && cd X-os
sudo scripts/setup-build-host.sh            # installs debootstrap, xorriso, grub, qemu, ovmf...
scripts/run-tests.sh                        # unit tests + static checks (no root)

sudo build/build.sh                         # core ISO   -> releases/out/x-os-<ver>-core-amd64.iso
sudo XOS_VARIANT=desktop build/build.sh     # desktop ISO
sudo testing/vm/boot_test.py releases/out/x-os-0.1.0-dev-core-amd64.iso --firmware uefi
```

Individual stages: `sudo build/build.sh bootstrap|configure|squash|iso|clean`.
The configure stage is re-runnable; rerun it after editing package lists, hooks,
overlay or X-OS components, then `squash iso`.

All build output stays inside the project: `build/work/<variant>/` (chroot,
staging) and `releases/out/` (ISO + `.sha256`). Neither is committed.

## Trying an ISO

* **VM (recommended first):** `qemu-system-x86_64 -m 4096 -enable-kvm -cdrom <iso>`,
  or import into VirtualBox/GNOME Boxes/virt-manager as a live CD.
* **USB, live only:** write the ISO with `dd if=<iso> of=/dev/sdX bs=4M conv=fsync`
  (double-check `sdX` with `lsblk` — it is erased) or GNOME Disks / balenaEtcher.
  Choose *Try without installing*. Nothing is written to internal disks.
  **Development builds must not be installed on a computer you depend on.**

## Layout of an X-OS ISO

```
/boot/grub/grub.cfg          live boot menu
/live/vmlinuz, initrd.img    Debian kernel + live-boot initramfs
/live/filesystem.squashfs    root filesystem (zstd)
/live/filesystem.packages    exact package list (for license/audit)
/md5sum.txt, /.disk/info     integrity + identification
```
