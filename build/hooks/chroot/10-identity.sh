#!/bin/sh
# X-OS system identity: os-release, issue, motd. Runs inside the build chroot.
set -eu

cat > /usr/lib/os-release <<EOF
PRETTY_NAME="X-OS ${XOS_VERSION} (${XOS_CODENAME})"
NAME="X-OS"
VERSION_ID="${XOS_VERSION}"
VERSION="${XOS_VERSION} (${XOS_CODENAME})"
VERSION_CODENAME=${XOS_CODENAME}
ID=x-os
ID_LIKE=debian
HOME_URL="https://github.com/AwmiresGg/X-os"
SUPPORT_URL="https://github.com/AwmiresGg/X-os/issues"
BUG_REPORT_URL="https://github.com/AwmiresGg/X-os/issues"
LOGO=x-os
ANSI_COLOR="38;2;124;140;255"
XOS_VARIANT=${XOS_VARIANT}
XOS_RELEASE_STATE=DEVELOPMENT
EOF
ln -sf ../usr/lib/os-release /etc/os-release
# Debian tooling (apt, dpkg-vendor, reportbug) keeps working: /etc/debian_version is untouched.

printf 'X-OS %s \\n \\l\n\n' "${XOS_VERSION}" > /etc/issue
printf 'X-OS %s\n' "${XOS_VERSION}" > /etc/issue.net
cat > /etc/motd <<'EOF'

  X-OS  -  BEYOND WINDOWS. BEYOND macOS.
  Development build. Not ready for installation on a computer you depend on.
  Hardware report:  xos-hwprobe        Performance profile:  xos-profile status

EOF
