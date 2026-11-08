#!/bin/sh
# Installed-system GRUB defaults. Debian creates /etc/default/grub in the postinst of the
# grub-efi-amd64 / grub-pc meta packages, which the image does not carry (it ships the
# signed binaries only), so create it from Debian's own template. Without it Calamares
# writes /etc/default/grub.d/00calamares, a name grub-mkconfig ignores (it reads *.cfg).
set -eu
[ -f /usr/share/grub/default/grub ] || exit 0
[ -f /etc/default/grub ] || install -m 0644 /usr/share/grub/default/grub /etc/default/grub
test -f /etc/default/grub.d/10-xos.cfg
