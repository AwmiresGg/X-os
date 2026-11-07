"""Browser installation from the vendors' official, signed APT repositories.

Used by the installer (inside the freshly installed system) and by the first-boot
service when the installer had no network. Chrome cannot be redistributed on the
ISO under Google's terms, so it is downloaded from Google with the user's consent.

Trust model: the vendor's signing key is downloaded over HTTPS and accepted only if
its primary-key fingerprint equals the one pinned here (checked against the
vendors' published fingerprints on 2026-11-07). The repository is then limited to
that key with ``Signed-By`` so it cannot sign packages for other repositories.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Browser:
    id: str
    name: str
    package: str
    key_url: str
    fingerprint: str          # primary key, 40 hex chars, no spaces
    repo_uri: str
    suite: str
    components: str
    arch: str = "amd64"
    preinstalled_fallback: str | None = None   # package already on the ISO
    pin: str | None = None                     # extra apt preferences


BROWSERS = {
    "firefox": Browser(
        id="firefox", name="Mozilla Firefox", package="firefox",
        key_url="https://packages.mozilla.org/apt/repo-signing-key.gpg",
        fingerprint="35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3",
        repo_uri="https://packages.mozilla.org/apt", suite="mozilla", components="main",
        preinstalled_fallback="firefox-esr",
        # Only take the "firefox" packages from Mozilla's repository.
        pin="Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 100\n\n"
            "Package: firefox*\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n"),
    "chrome": Browser(
        id="chrome", name="Google Chrome", package="google-chrome-stable",
        key_url="https://dl.google.com/linux/linux_signing_key.pub",
        fingerprint="EB4C1BFD4F042F6DDDCCEC917721F63BD38B4796",
        repo_uri="https://dl.google.com/linux/chrome/deb", suite="stable", components="main"),
}


class KeyMismatch(Exception):
    pass


def primary_fingerprints(colons: str) -> list[str]:
    """Primary-key fingerprints from `gpg --show-keys --with-colons` output.

    A `fpr` record belongs to the `pub`/`sub` record before it; only those that
    follow a `pub` are primary keys.
    """
    out, last = [], None
    for line in colons.splitlines():
        f = line.split(":")
        if f[0] in ("pub", "sub"):
            last = f[0]
        elif f[0] == "fpr" and last == "pub":
            out.append(f[9].upper())
            last = None
    return out


def verify_key(key_data: bytes, expected: str) -> None:
    with tempfile.NamedTemporaryFile() as tmp, tempfile.TemporaryDirectory() as home:
        tmp.write(key_data)
        tmp.flush()
        r = subprocess.run(["gpg", "--homedir", home, "--batch", "--show-keys", "--with-colons", tmp.name],
                           capture_output=True, text=True)
    fprs = primary_fingerprints(r.stdout)
    if fprs != [expected.upper()]:
        raise KeyMismatch(f"expected exactly key {expected}, got {fprs or 'no valid key'}")


def sources_entry(b: Browser) -> str:
    return (f"Types: deb\nURIs: {b.repo_uri}\nSuites: {b.suite}\nComponents: {b.components}\n"
            f"Architectures: {b.arch}\nSigned-By: /usr/share/keyrings/xos-{b.id}.gpg\n")


def _run(cmd: list[str], log: list[str]) -> bool:
    r = subprocess.run(cmd, capture_output=True, text=True)
    log.append(f"$ {' '.join(cmd)} -> {r.returncode}")
    if r.returncode:
        log.append(r.stderr.strip()[-600:])
    return r.returncode == 0


def install(ids: list[str], root: Path = Path("/")) -> tuple[list[str], list[str], list[str]]:
    """Install the chosen browsers into the running system (run inside the target).

    Returns (installed, failed, log). Never raises for network errors: failures are
    reported so the first-boot service can retry.
    """
    installed, failed, log = [], [], []
    added = []
    for bid in ids:
        b = BROWSERS[bid]
        try:
            r = subprocess.run(["curl", "-fsSL", "--max-time", "60", b.key_url], capture_output=True)
            if r.returncode:
                raise OSError(f"download of {b.key_url} failed (no internet?)")
            verify_key(r.stdout, b.fingerprint)
            keyring = root / f"usr/share/keyrings/xos-{b.id}.gpg"
            keyring.parent.mkdir(parents=True, exist_ok=True)
            d = subprocess.run(["gpg", "--batch", "--yes", "--dearmor", "-o", str(keyring)], input=r.stdout,
                               capture_output=True)
            if d.returncode:
                raise OSError("could not store signing key")
            keyring.chmod(0o644)
            (root / f"etc/apt/sources.list.d/xos-{b.id}.sources").write_text(sources_entry(b))
            if b.pin:
                pref = root / f"etc/apt/preferences.d/xos-{b.id}"
                pref.parent.mkdir(parents=True, exist_ok=True)
                pref.write_text(b.pin)
            added.append(b)
        except (OSError, KeyMismatch) as e:
            log.append(f"{b.name}: {e}")
            failed.append(bid)
    if added and _run(["apt-get", "update"], log):
        for b in added:
            env_cmd = ["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", b.package]
            ok = _run(env_cmd, log)
            (installed if ok else failed).append(b.id)
            # Chrome's postinst writes its own google-chrome.list (and keeps it updated);
            # drop ours then, so APT does not see the repository twice.
            if ok and b.id == "chrome" and (root / "etc/apt/sources.list.d/google-chrome.list").exists():
                (root / f"etc/apt/sources.list.d/xos-{b.id}.sources").unlink(missing_ok=True)
    else:
        failed.extend(b.id for b in added)
    return installed, failed, log
