import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from xos import browsers, setup



def make_key(name: str, home: str) -> tuple[bytes, str]:
    """Generate a throwaway OpenPGP key and return (armored public key, fingerprint)."""
    subprocess.run(["gpg", "--homedir", home, "--batch", "--passphrase", "", "--quick-gen-key",
                    f"{name} <{name}@example.invalid>", "ed25519", "sign", "never"],
                   check=True, capture_output=True)
    out = subprocess.run(["gpg", "--homedir", home, "--batch", "--with-colons", "--list-keys", name],
                         check=True, capture_output=True, text=True).stdout
    fpr = browsers.primary_fingerprints(out)[0]
    pub = subprocess.run(["gpg", "--homedir", home, "--batch", "--armor", "--export", name],
                         check=True, capture_output=True).stdout
    return pub, fpr


@unittest.skipUnless(shutil.which("gpg"), "gpg not installed")
class KeyVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp()
        cls.good, cls.good_fpr = make_key("vendor", cls.home)
        cls.evil, cls.evil_fpr = make_key("attacker", cls.home)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.home, ignore_errors=True)

    def test_accepts_pinned_key(self):
        browsers.verify_key(self.good, self.good_fpr)

    def test_rejects_other_key(self):
        with self.assertRaises(browsers.KeyMismatch):
            browsers.verify_key(self.evil, self.good_fpr)

    def test_rejects_key_bundle_with_extra_key(self):
        with self.assertRaises(browsers.KeyMismatch):
            browsers.verify_key(self.good + self.evil, self.good_fpr)

    def test_rejects_garbage(self):
        with self.assertRaises(browsers.KeyMismatch):
            browsers.verify_key(b"<html>captive portal</html>", self.good_fpr)


class BrowserCatalogTests(unittest.TestCase):
    def test_pinned_fingerprints_are_the_vendors(self):
        # Checked against the keys published at the vendors' URLs on 2026-11-07.
        self.assertEqual(browsers.BROWSERS["chrome"].fingerprint, "EB4C1BFD4F042F6DDDCCEC917721F63BD38B4796")
        self.assertEqual(browsers.BROWSERS["firefox"].fingerprint, "35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3")
        for b in browsers.BROWSERS.values():
            self.assertTrue(b.key_url.startswith("https://"))
            self.assertTrue(b.repo_uri.startswith("https://"))

    def test_sources_entry_is_restricted_to_its_key(self):
        s = browsers.sources_entry(browsers.BROWSERS["chrome"])
        self.assertIn("Signed-By: /usr/share/keyrings/xos-chrome.gpg", s)
        self.assertIn("URIs: https://dl.google.com/linux/chrome/deb", s)

    def test_offline_install_reports_failure_without_raising(self):
        with tempfile.TemporaryDirectory() as t, \
             mock.patch.object(browsers.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 6, b"", b"no network")):
            installed, failed, log = browsers.install(["firefox", "chrome"], root=Path(t))
        self.assertEqual((installed, sorted(failed)), ([], ["chrome", "firefox"]))
        self.assertTrue(any("no internet" in line for line in log))


class ChoicesTests(unittest.TestCase):
    def test_roundtrip_persian(self):
        c = setup.Choices(locale="fa_IR.UTF-8", keyboard=[["us", ""], ["ir", ""]], theme="dark",
                          wallpaper="x-os-dark", browsers=["firefox", "chrome"], wifi_ssid="خانه")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.json"
            setup.save(c, p)
            self.assertIn("خانه", p.read_text(encoding="utf-8"))
            back = setup.load(p)
        self.assertEqual(back, c)
        self.assertTrue(back.rtl)
        self.assertEqual(back.xkb(), ("us,ir", ","))

    def test_validation(self):
        bad = [dict(locale="xx_XX.UTF-8"), dict(keyboard=[]), dict(keyboard=[["us", ""]] * 5),
               dict(keyboard=[["us; rm -rf /", ""]]), dict(theme="neon"), dict(wallpaper="../../etc/passwd"),
               dict(browsers=["netscape"])]
        for kw in bad:
            with self.assertRaises(ValueError, msg=str(kw)):
                setup.Choices(**kw).validate()

    def test_choices_file_never_contains_a_password(self):
        self.assertNotIn("password", setup.Choices.__dataclass_fields__)
        self.assertNotIn("psk", setup.Choices.__dataclass_fields__)

    def test_target_commands_set_locale_and_alt_shift(self):
        c = setup.Choices(locale="fa_IR.UTF-8", keyboard=[["us", ""], ["ir", ""]])
        cmds = setup.target_system_commands(c)
        flat = json.dumps(cmds)
        self.assertIn("LANG=fa_IR.UTF-8", flat)
        self.assertIn("XKBLAYOUT=us,ir", flat)
        self.assertIn("grp:alt_shift_toggle", flat)


class WifiTests(unittest.TestCase):
    def test_parse_nmcli_terse_output(self):
        text = ("*:Home\\:5G:92:WPA2 WPA3\n"
                " :Office:71:WPA2\n"
                " :Office:40:WPA2\n"        # same SSID on another access point: keep strongest
                " :Cafe:48:\n"
                " ::30:WPA2\n")              # hidden network
        nets = setup.parse_wifi_list(text)
        self.assertEqual([n["ssid"] for n in nets], ["Home:5G", "Office", "Cafe"])
        self.assertTrue(nets[0]["connected"])
        self.assertEqual(nets[1]["signal"], 71)
        self.assertFalse(nets[2]["secure"])

    def test_connection_settings(self):
        s = setup.wifi_connection_settings("Home", "correct horse")
        self.assertEqual(s["802-11-wireless-security"]["key-mgmt"], "wpa-psk")
        self.assertEqual(bytes(s["802-11-wireless"]["ssid"]), b"Home")
        self.assertNotIn("802-11-wireless-security", setup.wifi_connection_settings("Cafe", None))
        with self.assertRaises(ValueError):
            setup.wifi_connection_settings("Home", "short")


if __name__ == "__main__":
    unittest.main()


class KeyboardCommandTests(unittest.TestCase):
    def test_session_commands_are_valid_and_reload_plasma(self):
        cmds = setup.keyboard_session_commands(setup.Choices(keyboard=[["us", ""], ["ir", ""]]))
        dbus = [c for c in cmds if c[0] == "dbus-send"]
        self.assertEqual(dbus, [["dbus-send", "--session", "--type=signal", "/Layouts",
                                 "org.kde.keyboard.reloadConfig"]])
        flat = [" ".join(c) for c in cmds]
        self.assertTrue(any("LayoutList us,ir" in f for f in flat))
        self.assertTrue(any("ResetOldOptions true" in f for f in flat))
        if shutil.which("dbus-send"):
            # The real binary must accept every option we pass (it rejected "--reload").
            r = subprocess.run(["dbus-send", "--help"], capture_output=True, text=True)
            for opt in dbus[0][1:3]:
                self.assertIn(opt.split("=")[0], r.stdout + r.stderr)
