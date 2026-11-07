import json
import tempfile
import unittest
from pathlib import Path

from xos import windows as W

A = "0b5c7e1a-1111-4a2b-9c3d-aaaaaaaaaaaa"
B = "{0b5c7e1a-2222-4a2b-9c3d-bbbbbbbbbbbb}"
C = "0b5c7e1a-3333-4a2b-9c3d-cccccccccccc"


class ParseTests(unittest.TestCase):
    def test_parse_update(self):
        payload = json.dumps({"windows": [
            {"id": A, "caption": "Home — Dolphin", "appId": "org.kde.dolphin", "minimized": False},
            {"id": B, "caption": "~ : bash", "appId": "org.kde.konsole.desktop"},
            {"id": "not-a-uuid", "caption": "x", "appId": "evil"},
        ], "active": B})
        wins, active = W.parse_update(payload)
        self.assertEqual([w.app_id for w in wins], ["org.kde.dolphin", "org.kde.konsole"])
        self.assertEqual(active, B)

    def test_garbage(self):
        self.assertEqual(W.parse_update("{nope"), ([], ""))
        self.assertEqual(W.parse_update(json.dumps({"windows": [], "active": "'); evil()"}))[1], "")


class RegistryAndDockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        (d / "org.kde.dolphin.desktop").write_text(
            "[Desktop Entry]\nName=Dolphin\nIcon=system-file-manager\nExec=dolphin %u\n")
        (d / "firefox-esr.desktop").write_text(
            "[Desktop Entry]\nName=Firefox ESR\nIcon=firefox-esr\nExec=/usr/lib/firefox-esr/firefox-esr %u\n")
        self.reg = W.AppRegistry([d])

    def tearDown(self):
        self.tmp.cleanup()

    def test_registry(self):
        a = self.reg.get("org.kde.dolphin.desktop")
        self.assertEqual((a.name, a.icon, a.xos_icon), ("Dolphin", "system-file-manager", "files"))
        unknown = self.reg.get("com.example.thing")
        self.assertEqual(unknown.name, "Thing")

    def test_installer_is_named_and_iconed_as_x_os(self):
        (Path(self.tmp.name) / "calamares.desktop").write_text(
            "[Desktop Entry]\nName=Install System\nIcon=calamares\nExec=pkexec calamares\n")
        reg = W.AppRegistry([Path(self.tmp.name)])
        a = reg.get(W.normalize_app_id("io.calamares.calamares"))
        self.assertEqual((a.id, a.name, a.xos_icon), ("calamares", "Install X-OS", "install"))

    def test_dock_groups_windows_per_app_and_keeps_pinned_order(self):
        wins = [W.Window(A, "Home", "org.kde.dolphin"), W.Window(C, "Docs", "org.kde.dolphin"),
                W.Window(B, "bash", "org.kde.konsole")]
        items = W.dock_items(["firefox-esr", "org.kde.dolphin"], wins, C, self.reg)
        self.assertEqual([i.app_id for i in items], ["firefox-esr", "org.kde.dolphin", "org.kde.konsole"])
        self.assertFalse(items[0].running)
        self.assertEqual(len(items[1].windows), 2)
        self.assertTrue(items[1].active)
        self.assertFalse(items[2].pinned)
        self.assertEqual(sum(i.active for i in items), 1)

    def test_launch_argv(self):
        self.assertEqual(W.launch_argv("dolphin %u"), ["dolphin"])
        self.assertEqual(W.launch_argv('sh -c "echo 100%%" %F'), ["sh", "-c", "echo 100%"])
        self.assertEqual(W.launch_argv('broken "quote'), [])


class KWinCommandTests(unittest.TestCase):
    def test_script_targets_one_window(self):
        s = W.kwin_command_script(B, "activate")
        self.assertIn("workspace.activeWindow = w;", s)
        self.assertIn("0b5c7e1a-2222-4a2b-9c3d-bbbbbbbbbbbb", s)

    def test_injection_rejected(self):
        for bad in ["'); workspace.windowList().forEach(w => w.closeWindow()); ('", "", "abc"]:
            with self.assertRaises(ValueError):
                W.kwin_command_script(bad, "close")
        with self.assertRaises(ValueError):
            W.kwin_command_script(A, "format-disk")


if __name__ == "__main__":
    unittest.main()
