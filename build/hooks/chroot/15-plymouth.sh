#!/bin/sh
# X-OS boot splash as the default Plymouth theme (the initramfs is rebuilt by hook 20).
set -eu
command -v plymouth-set-default-theme >/dev/null || exit 0
plymouth-set-default-theme xos
grep -q 'Theme=xos' /etc/plymouth/plymouthd.conf
