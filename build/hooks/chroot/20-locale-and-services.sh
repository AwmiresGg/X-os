#!/bin/sh
# Locale, services and live-session defaults. Runs inside the build chroot.
set -eu

sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
update-locale LANG=en_US.UTF-8

# Essential services. Security services (firewall) are on in every profile.
systemctl enable NetworkManager.service || true
systemctl enable systemd-resolved.service
systemctl enable systemd-timesyncd.service || true
systemctl enable bluetooth.service 2>/dev/null || true
systemctl enable xos-selftest.service
systemctl enable xos-profile-boot.service
systemctl enable xos-live-session.service

# Firewall: deny incoming, allow outgoing. Enabled on first boot by ufw.service.
if command -v ufw >/dev/null; then
    sed -i 's/^ENABLED=no/ENABLED=yes/' /etc/ufw/ufw.conf
    sed -i 's/^DEFAULT_INPUT_POLICY=.*/DEFAULT_INPUT_POLICY="DROP"/' /etc/default/ufw
    sed -i 's/^DEFAULT_OUTPUT_POLICY=.*/DEFAULT_OUTPUT_POLICY="ACCEPT"/' /etc/default/ufw
    systemctl enable ufw.service || true
fi

# NetworkManager owns all interfaces (ifupdown is not installed).
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/10-xos.conf <<'EOF'
[main]
plugins=keyfile

[device]
wifi.scan-rand-mac-address=yes

[connection]
# Stable per-network MAC randomization for privacy on Wi-Fi.
wifi.cloned-mac-address=stable
EOF

# Desktop variant: graphical login.
if [ "${XOS_VARIANT}" = "desktop" ]; then
    systemctl enable sddm.service || true
    systemctl set-default graphical.target
else
    systemctl set-default multi-user.target
fi

# Rebuild the initramfs so live-boot hooks are included.
update-initramfs -u -k all
