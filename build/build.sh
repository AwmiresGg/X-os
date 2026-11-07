#!/usr/bin/env bash
# X-OS image build pipeline.
#
#   sudo build/build.sh [stage...]
#
# Stages (default: all, in order):
#   bootstrap  debootstrap a Debian base into $XOS_WORK/chroot
#   configure  install package lists, X-OS components, overlay, run chroot hooks
#   squash     build live/filesystem.squashfs
#   iso        build a hybrid BIOS+UEFI ISO with GRUB
#   clean      unmount and delete $XOS_WORK
#
# Safety: this script only writes inside the project tree ($XOS_ROOT/build/work and
# $XOS_ROOT/releases/out). It never touches block devices, partitions or the host
# bootloader. Chroot bind-mounts are always unmounted on exit.

set -euo pipefail

XOS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export XOS_ROOT
# shellcheck source=config/xos.conf
source "$XOS_ROOT/build/config/xos.conf"

CHROOT="$XOS_WORK/chroot"
STAGING="$XOS_WORK/iso"
LOG_PREFIX="[x-os build]"

log() { printf '%s %s\n' "$LOG_PREFIX" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# --------------------------------------------------------------------------- safety
check_paths() {
    case "$XOS_WORK" in
        "$XOS_ROOT"/build/work/*) ;;
        *) die "XOS_WORK ($XOS_WORK) must be inside $XOS_ROOT/build/work" ;;
    esac
    [[ "$CHROOT" != "/" && -n "$CHROOT" ]] || die "refusing to use / as chroot"
}

check_host() {
    [[ $EUID -eq 0 ]] || die "must run as root (debootstrap and chroot need it)"
    local missing=()
    for t in debootstrap mksquashfs xorriso grub-mkrescue chroot mountpoint; do
        command -v "$t" >/dev/null || missing+=("$t")
    done
    [[ -d /usr/lib/grub/i386-pc ]] || missing+=("grub-pc-bin")
    [[ -d /usr/lib/grub/x86_64-efi ]] || missing+=("grub-efi-amd64-bin")
    command -v mformat >/dev/null || missing+=("mtools")
    ((${#missing[@]} == 0)) || die "missing host tools: ${missing[*]} (see scripts/setup-build-host.sh)"
}

# --------------------------------------------------------------------------- mounts
mount_chroot() {
    local m
    for m in proc sys dev dev/pts run; do mkdir -p "$CHROOT/$m"; done
    mountpoint -q "$CHROOT/proc"    || mount -t proc proc "$CHROOT/proc"
    mountpoint -q "$CHROOT/sys"     || mount -t sysfs sysfs "$CHROOT/sys"
    mountpoint -q "$CHROOT/dev"     || { mount --bind /dev "$CHROOT/dev"; mount --make-rslave "$CHROOT/dev"; }
    mountpoint -q "$CHROOT/dev/pts" || mount -t devpts devpts "$CHROOT/dev/pts"
    mountpoint -q "$CHROOT/run"     || mount -t tmpfs tmpfs "$CHROOT/run"
}

umount_chroot() {
    [[ -d "$CHROOT" ]] || return 0
    local m
    for m in run dev/pts dev sys proc; do
        if mountpoint -q "$CHROOT/$m"; then umount -l "$CHROOT/$m" || true; fi
    done
}
trap umount_chroot EXIT

in_chroot() {
    LC_ALL=C DEBIAN_FRONTEND=noninteractive chroot "$CHROOT" /usr/bin/env \
        HOME=/root PATH=/usr/sbin:/usr/bin:/sbin:/bin "$@"
}

read_list() { grep -hv '^\s*#' "$@" | awk 'NF {print $1}' | sort -u; }

# --------------------------------------------------------------------------- stages
stage_bootstrap() {
    if [[ -x "$CHROOT/bin/bash" && -f "$XOS_WORK/.bootstrap-done" ]]; then
        log "bootstrap: already done ($CHROOT)"; return
    fi
    log "bootstrap: debootstrap $XOS_SUITE -> $CHROOT"
    mkdir -p "$CHROOT"
    debootstrap --arch="$XOS_ARCH" --variant=minbase \
        --components="${XOS_COMPONENTS// /,}" \
        --keyring=/usr/share/keyrings/debian-archive-keyring.gpg \
        "$XOS_SUITE" "$CHROOT" "$XOS_MIRROR"
    touch "$XOS_WORK/.bootstrap-done"
}

write_apt_sources() {
    cat > "$CHROOT/etc/apt/sources.list.d/debian.sources" <<EOF
Types: deb
URIs: $XOS_MIRROR
Suites: $XOS_SUITE $XOS_SUITE-updates
Components: $XOS_COMPONENTS
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: $XOS_SECURITY_MIRROR
Suites: $XOS_SUITE-security
Components: $XOS_COMPONENTS
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF
    rm -f "$CHROOT/etc/apt/sources.list"
}

stage_configure() {
    [[ -f "$XOS_WORK/.bootstrap-done" ]] || die "run the bootstrap stage first"
    mount_chroot
    write_apt_sources
    # Never start services inside the build chroot.
    printf '#!/bin/sh\nexit 101\n' > "$CHROOT/usr/sbin/policy-rc.d"
    chmod +x "$CHROOT/usr/sbin/policy-rc.d"
    echo "$XOS_HOSTNAME" > "$CHROOT/etc/hostname"
    rm -f "$CHROOT/etc/resolv.conf"
    cp /etc/resolv.conf "$CHROOT/etc/resolv.conf"

    local lists=("$XOS_ROOT/build/package-lists/core.list")
    [[ "$XOS_VARIANT" == "desktop" ]] && lists+=("$XOS_ROOT/build/package-lists/desktop.list")
    mapfile -t pkgs < <(read_list "${lists[@]}")
    log "configure: installing ${#pkgs[@]} packages (${XOS_VARIANT})"
    in_chroot apt-get update
    # keyboard-configuration/console-setup ask questions; preseed sane defaults.
    in_chroot debconf-set-selections <<'EOF'
keyboard-configuration keyboard-configuration/layoutcode string us
keyboard-configuration keyboard-configuration/modelcode string pc105
locales locales/default_environment_locale select en_US.UTF-8
locales locales/locales_to_be_generated multiselect en_US.UTF-8 UTF-8
EOF
    in_chroot apt-get install -y --no-install-recommends "${pkgs[@]}"
    in_chroot apt-get -y full-upgrade

    log "configure: installing X-OS components"
    XOS_VARIANT="$XOS_VARIANT" "$XOS_ROOT/scripts/install-components.sh" "$CHROOT"

    if [[ -d "$XOS_ROOT/build/overlay" ]] && [[ -n "$(ls -A "$XOS_ROOT/build/overlay")" ]]; then
        log "configure: applying overlay"
        cp -a "$XOS_ROOT/build/overlay/." "$CHROOT/"
    fi

    local hook
    for hook in "$XOS_ROOT"/build/hooks/chroot/*.sh; do
        [[ -e "$hook" ]] || continue
        log "configure: hook $(basename "$hook")"
        install -m 0755 "$hook" "$CHROOT/tmp/xos-hook.sh"
        in_chroot env XOS_VARIANT="$XOS_VARIANT" XOS_VERSION="$XOS_VERSION" \
            XOS_CODENAME="$XOS_CODENAME" XOS_LIVE_USER="$XOS_LIVE_USER" /tmp/xos-hook.sh
        rm -f "$CHROOT/tmp/xos-hook.sh"
    done

    log "configure: cleanup"
    in_chroot apt-get clean
    rm -rf "$CHROOT"/var/lib/apt/lists/* "$CHROOT"/tmp/* "$CHROOT"/var/tmp/*
    rm -f "$CHROOT/usr/sbin/policy-rc.d" "$CHROOT/etc/resolv.conf"
    ln -sf ../run/systemd/resolve/stub-resolv.conf "$CHROOT/etc/resolv.conf" 2>/dev/null || true
    # Machine identity must be generated per boot / per install, never shipped.
    : > "$CHROOT/etc/machine-id"
    rm -f "$CHROOT/var/lib/dbus/machine-id" "$CHROOT"/etc/ssh/ssh_host_*
    umount_chroot
    touch "$XOS_WORK/.configure-done"
}

stage_squash() {
    [[ -f "$XOS_WORK/.configure-done" ]] || die "run the configure stage first"
    umount_chroot
    mkdir -p "$STAGING/live"
    rm -f "$STAGING/live/filesystem.squashfs"
    log "squash: compressing root filesystem ($XOS_SQUASHFS_COMP)"
    # shellcheck disable=SC2086
    mksquashfs "$CHROOT" "$STAGING/live/filesystem.squashfs" -noappend \
        -comp "$XOS_SQUASHFS_COMP" $XOS_SQUASHFS_OPTS -e boot/efi -wildcards \
        -e 'proc/*' -e 'sys/*' -e 'dev/*' -e 'run/*' -e 'tmp/*'
    local kver
    kver="$(basename "$(ls -1 "$CHROOT"/boot/vmlinuz-* | sort -V | tail -1)")"
    kver="${kver#vmlinuz-}"
    cp "$CHROOT/boot/vmlinuz-$kver" "$STAGING/live/vmlinuz"
    cp "$CHROOT/boot/initrd.img-$kver" "$STAGING/live/initrd.img"
    du -sx --block-size=1 "$CHROOT" | cut -f1 > "$STAGING/live/filesystem.size"
    in_chroot_pkglist > "$STAGING/live/filesystem.packages"
    echo "$kver" > "$XOS_WORK/kernel-version"
}

in_chroot_pkglist() {
    chroot "$CHROOT" dpkg-query -W -f='${Package} ${Version}\n'
}

stage_iso() {
    [[ -f "$STAGING/live/filesystem.squashfs" ]] || die "run the squash stage first"
    mkdir -p "$STAGING/boot/grub" "$STAGING/.disk" "$XOS_OUT"
    sed -e "s/@VERSION@/$XOS_VERSION/g" -e "s/@VARIANT@/$XOS_VARIANT/g" \
        "$XOS_ROOT/build/grub/grub.cfg.in" > "$STAGING/boot/grub/grub.cfg"
    cp "$XOS_ROOT/boot/grub-theme/background.png" "$STAGING/boot/grub/background.png" 2>/dev/null || true
    echo "$XOS_NAME $XOS_VERSION ($XOS_CODENAME) $XOS_VARIANT amd64 $(date -u +%Y%m%d)" > "$STAGING/.disk/info"
    touch "$STAGING/.disk/xos-live"
    (cd "$STAGING" && find live boot .disk -type f ! -name md5sum.txt -print0 | sort -z \
        | xargs -0 md5sum > md5sum.txt)

    local iso="$XOS_OUT/x-os-$XOS_VERSION-$XOS_VARIANT-amd64.iso"
    log "iso: building $iso"
    # grub-mkrescue produces a hybrid image: El Torito BIOS + EFI system partition,
    # bootable from optical media and from USB sticks (isohybrid MBR/GPT).
    grub-mkrescue -o "$iso" "$STAGING" -- -volid "XOS_$(echo "$XOS_VERSION" | tr -c 'A-Za-z0-9\n' '_' | cut -c1-20)"
    (cd "$XOS_OUT" && sha256sum "$(basename "$iso")" > "$(basename "$iso").sha256")
    log "iso: done -> $iso ($(du -h "$iso" | cut -f1))"
}

stage_clean() {
    umount_chroot
    if [[ -d "$XOS_WORK" ]]; then
        # Refuse to delete if anything is still mounted beneath the work dir.
        if grep -q " $XOS_WORK/" /proc/mounts; then die "mounts still active under $XOS_WORK"; fi
        rm -rf --one-file-system "$XOS_WORK"
    fi
    log "clean: removed $XOS_WORK"
}

main() {
    check_paths
    local stages=("$@")
    ((${#stages[@]})) || stages=(bootstrap configure squash iso)
    [[ " ${stages[*]} " == *" clean "* ]] || check_host
    mkdir -p "$XOS_WORK"
    local s
    for s in "${stages[@]}"; do
        case "$s" in
            bootstrap|configure|squash|iso|clean) "stage_$s" ;;
            *) die "unknown stage: $s" ;;
        esac
    done
}

main "$@"
