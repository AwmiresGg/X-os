"""Boot, login and installer artwork: every referenced file exists and the critical
behaviours (encrypted-disk password prompt, theme selection) are wired."""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class GrubThemeTests(unittest.TestCase):
    def test_theme_references_resolve(self):
        d = ROOT / "themes/boot/grub/xos"
        theme = (d / "theme.txt").read_text()
        for img in re.findall(r'(?:desktop-image|file)\s*[:=]\s*"([^"]+)"', theme):
            self.assertTrue((d / img).exists(), img)
        for k in ("nw", "n", "ne", "w", "c", "e", "sw", "s", "se"):
            self.assertTrue((d / f"select_{k}.png").exists(), k)
        fonts = set(re.findall(r'font\s*[:=]\s*"([^"]+)"', theme))
        cfg = (ROOT / "build/grub/grub.cfg.in").read_text()
        loaded = re.findall(r"loadfont \$xos_theme/([\w.-]+\.pf2)", cfg)
        for f in loaded:
            self.assertTrue((d / f).exists(), f)
        names = {"Inter Regular 18": "inter-18.pf2", "Inter Regular 13": "inter-13.pf2",
                 "Inter SemiBold 28": "inter-semibold-28.pf2"}
        for f in fonts:
            self.assertIn(names[f], loaded, f"font {f} is used but not loaded")

    def test_installed_systems_use_the_theme(self):
        g = yaml.safe_load((ROOT / "installer/calamares/modules/grubcfg.conf").read_text())["defaults"]
        self.assertEqual(g["GRUB_THEME"], "/usr/share/grub/themes/xos/theme.txt")
        self.assertIn("splash", g["GRUB_CMDLINE_LINUX_DEFAULT"])


class PlymouthTests(unittest.TestCase):
    def test_splash_handles_encrypted_disk_password(self):
        d = ROOT / "themes/boot/plymouth/xos"
        script = (d / "xos.script").read_text()
        self.assertIn("Plymouth.SetDisplayPasswordFunction", script)
        self.assertIn("Plymouth.SetDisplayNormalFunction", script)
        for img in re.findall(r'Image\("([^"]+)"\)', script):
            self.assertTrue((d / img).exists(), img)
        self.assertIn("plymouth-label", (ROOT / "build/package-lists/core.list").read_text())
        self.assertIn("plymouth-set-default-theme xos", (ROOT / "build/hooks/chroot/15-plymouth.sh").read_text())


class LoginAndInstallerTests(unittest.TestCase):
    def test_sddm_theme_complete_and_selected(self):
        d = ROOT / "themes/sddm/xos"
        meta = (d / "metadata.desktop").read_text()
        self.assertIn("QtVersion=6", meta)
        self.assertIn("MainScript=Main.qml", meta)
        qml = (d / "Main.qml").read_text()
        self.assertIn("sddm.login(", qml)
        self.assertIn("onLoginFailed", qml)
        for icon in re.findall(r'icon: "([^"]+)"', qml):
            self.assertTrue((d / icon).exists(), icon)
        self.assertIn("Current=xos", (ROOT / "build/hooks/chroot/40-desktop-defaults.sh").read_text())

    def test_calamares_branding_files_exist(self):
        d = ROOT / "installer/calamares/branding/xos"
        b = yaml.safe_load((d / "branding.desc").read_text())
        for key in ("productLogo", "productIcon", "productWelcome"):
            self.assertTrue((d / b["images"][key]).exists(), key)
        self.assertTrue((d / b["stylesheet"]).exists())
        self.assertTrue((d / b["slideshow"]).exists())
        # QML sidebar / navigation: Calamares loads calamares-<panel>.qml from the branding dir
        for panel in ("sidebar", "navigation"):
            self.assertEqual(b[panel], "qml")
            qml = (d / f"calamares-{panel}.qml").read_text()
            self.assertIn("ViewManager", qml)
        nav = (d / "calamares-navigation.qml").read_text()
        for call in ("ViewManager.back()", "ViewManager.next()", "ViewManager.quit()"):
            self.assertIn(call, nav)
        # offline installs are supported, so a missing connection is not a requirement
        welcome = yaml.safe_load((ROOT / "installer/calamares/modules/welcome.conf").read_text())
        self.assertNotIn("internet", welcome["requirements"]["required"])


if __name__ == "__main__":
    unittest.main()
