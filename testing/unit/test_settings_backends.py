"""Backends of X-OS Settings: Tweaks, Security, Updates, This PC (pure parts; no root)."""
import json
import tempfile
import unittest
from pathlib import Path

from xos import security, thispc, tweaks, updates


class TweaksTests(unittest.TestCase):
    def test_every_mode_is_complete_and_safe(self):
        for m in tweaks.MODES.values():
            self.assertIn(m.power, ("performance", "balanced", "power-saver"), m.id)
            self.assertTrue(set(m.sysctl) <= tweaks.ALLOWED_SYSCTL, m.id)
            text = tweaks.sysctl_text(m.id)
            self.assertIn("vm.swappiness", text)
        self.assertIn("balanced", tweaks.MODES)

    def test_gaming_raises_map_count_for_proton(self):
        self.assertIn("vm.max_map_count = 2147483642", tweaks.sysctl_text("gaming"))
        self.assertEqual(tweaks.MODES["gaming"].power, "performance")
        self.assertEqual(tweaks.MODES["battery"].power, "power-saver")

    def test_apply_system_writes_files_under_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            tweaks.apply_system("development", root=root, run=False)
            self.assertIn("fs.inotify.max_user_watches = 1048576",
                          (root / "etc/sysctl.d/60-xos-tweaks.conf").read_text())
            self.assertEqual(tweaks.current(root), "development")
            with self.assertRaises(ValueError):
                tweaks.apply_system("rm -rf /", root=root, run=False)

    def test_unknown_sysctl_is_refused(self):
        tweaks.MODES["evil"] = tweaks.Mode("evil", "", "", "", "balanced", 1, True, "full", {"kernel.modules_disabled": 1})
        try:
            with self.assertRaises(ValueError):
                tweaks.sysctl_text("evil")
        finally:
            del tweaks.MODES["evil"]

    def test_session_commands_never_need_root(self):
        for cmd in tweaks.session_commands("gaming"):
            self.assertNotIn(cmd[0], ("pkexec", "sudo", "sysctl"))


class SecurityTests(unittest.TestCase):
    def test_parse_scan_output_with_quarantine(self):
        out = ("/home/u/Downloads/eicar.com: Win.Test.EICAR_HDB-1 FOUND\n"
               "/home/u/Downloads/eicar.com: moved to '/home/u/.local/share/xos/quarantine/eicar.com'\n"
               "/home/u/Desktop/x y.exe: Win.Trojan.Agent-123 FOUND\n")
        found = security.parse_scan_output(out)
        self.assertEqual([f.signature for f in found], ["Win.Test.EICAR_HDB-1", "Win.Trojan.Agent-123"])
        self.assertTrue(found[0].quarantined_to.endswith("quarantine/eicar.com"))
        self.assertEqual(found[1].path, "/home/u/Desktop/x y.exe")
        self.assertEqual(security.scan_exit_meaning(1), "threats")
        self.assertEqual(security.scan_exit_meaning(2), "error")

    def test_scan_command_moves_to_quarantine_and_skips_it(self):
        cmd = security.scan_command(["/home/u/Downloads"], Path("/home/u/.local/share/xos/quarantine"))
        self.assertEqual(cmd[0], "clamscan")
        self.assertIn("--move=/home/u/.local/share/xos/quarantine", cmd)
        self.assertEqual(cmd[-2:], ["--", "/home/u/Downloads"])      # paths after --
        with self.assertRaises(ValueError):
            security.scan_command([])

    def test_onaccess_block_is_idempotent(self):
        base = "LocalSocket /run/clamav/clamd.ctl\nUser clamav\n"
        on = security.onaccess_conf(base, True)
        self.assertIn("OnAccessIncludePath /home", on)
        self.assertEqual(security.onaccess_conf(on, True), on)
        self.assertEqual(security.onaccess_conf(on, False), base)

    def test_firewall_flag(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ufw.conf"
            f.write_text("# x\nENABLED=yes\nLOGLEVEL=low\n")
            self.assertTrue(security.firewall_enabled(f))
            f.write_text("ENABLED=no\n")
            self.assertFalse(security.firewall_enabled(f))
            self.assertIsNone(security.firewall_enabled(Path(d) / "missing"))

    def test_definitions_age(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(security.definitions(Path(d))["installed"])
            (Path(d) / "daily.cld").write_bytes(b"x")
            info = security.definitions(Path(d))
            self.assertTrue(info["installed"])
            self.assertEqual(info["age_days"], 0)


class UpdatesTests(unittest.TestCase):
    def test_parse_apt(self):
        text = ("Listing...\n"
                "bash/stable-security 5.2.37-1.1+deb13u1 amd64 [upgradable from: 5.2.37-1.1]\n"
                "firefox-esr/stable-security 140.5.0esr-1~deb13u1 amd64 [upgradable from: 140.4.0esr-1~deb13u1]\n"
                "tzdata/stable-updates 2025c-0+deb13u1 all [upgradable from: 2025b-0+deb13u1]\n"
                "WARNING: apt does not have a stable CLI interface.\n")
        ups = updates.parse_apt_upgradable(text)
        self.assertEqual([u.name for u in ups], ["bash", "firefox-esr", "tzdata"])
        self.assertTrue(ups[0].security)
        self.assertFalse(ups[2].security)
        self.assertEqual(ups[1].old, "140.4.0esr-1~deb13u1")
        self.assertEqual(updates.summary([u.to_dict() for u in ups]),
                         "3 updates available, including 2 security updates.")

    def test_parse_flatpak(self):
        ups = updates.parse_flatpak_updates("Application ID\tVersion\norg.telegram.desktop\t5.8.3\n"
                                            "org.mozilla.firefox\t\n\n")
        self.assertEqual([(u.name, u.new) for u in ups], [("org.telegram.desktop", "5.8.3"), ("org.mozilla.firefox", "")])
        self.assertEqual(updates.summary([]), "X-OS is up to date.")


LSBLK = {"blockdevices": [
    {"name": "nvme0n1", "path": "/dev/nvme0n1", "type": "disk", "rm": False, "hotplug": False, "tran": "nvme",
     "model": "WD SN570", "size": 512110190592, "children": [
        {"name": "nvme0n1p1", "path": "/dev/nvme0n1p1", "type": "part", "fstype": "vfat", "label": "SYSTEM",
         "parttypename": "EFI System", "size": 104857600, "mountpoints": ["/boot/efi"]},
        {"name": "nvme0n1p2", "path": "/dev/nvme0n1p2", "type": "part", "fstype": None,
         "parttypename": "Microsoft reserved", "size": 16777216, "mountpoints": [None]},
        {"name": "nvme0n1p3", "path": "/dev/nvme0n1p3", "type": "part", "fstype": "ntfs", "label": None,
         "partlabel": "Basic data partition", "parttypename": "Microsoft basic data", "size": 250000000000,
         "fsused": None, "fsavail": None, "mountpoints": [None]},
        {"name": "nvme0n1p4", "path": "/dev/nvme0n1p4", "type": "part", "fstype": "ntfs", "label": "Recovery",
         "parttypename": "Windows recovery environment", "size": 700000000, "mountpoints": [None]},
        {"name": "nvme0n1p5", "path": "/dev/nvme0n1p5", "type": "part", "fstype": "ext4", "label": None,
         "parttypename": "Linux filesystem", "size": 260000000000, "fsused": 12000000000,
         "fsavail": 230000000000, "mountpoints": ["/"]},
        {"name": "nvme0n1p6", "path": "/dev/nvme0n1p6", "type": "part", "fstype": "swap",
         "parttypename": "Linux swap", "size": 2000000000, "mountpoints": ["[SWAP]"]}]},
    {"name": "sda", "path": "/dev/sda", "type": "disk", "rm": True, "hotplug": True, "tran": "usb",
     "model": "Cruzer", "size": 32000000000, "children": [
        {"name": "sda1", "path": "/dev/sda1", "type": "part", "fstype": "exfat", "label": "XOS_amir",
         "parttypename": "Microsoft basic data", "size": 32000000000, "fsused": 4000000000,
         "fsavail": 28000000000, "mountpoints": ["/media/u/XOS_amir"]}]},
    {"name": "sr0", "path": "/dev/sr0", "type": "rom", "rm": True, "fstype": "iso9660", "label": "VENUSDVD",
     "size": 4000000000, "mountpoints": [None]},
    {"name": "loop0", "path": "/dev/loop0", "type": "loop", "fstype": "squashfs", "size": 1, "mountpoints": ["/snap"]},
]}


class ThisPcTests(unittest.TestCase):
    def test_user_storage_only(self):
        ds = thispc.parse_lsblk(json.dumps(LSBLK))
        self.assertEqual([(d.kind, d.name, d.path) for d in ds], [
            ("system", "X-OS", "/dev/nvme0n1p5"),
            ("windows", "Windows", "/dev/nvme0n1p3"),
            ("removable", "XOS_amir", "/dev/sda1"),
            ("optical", "VENUSDVD", "/dev/sr0"),
        ])
        x = ds[0].to_dict()
        self.assertEqual(x["percent"], 5)
        self.assertIsNone(ds[1].to_dict()["percent"])       # not mounted: no usage yet

    def test_live_medium_is_hidden(self):
        live = {"blockdevices": [{"name": "sdb", "path": "/dev/sdb", "type": "disk", "rm": True, "tran": "usb",
                                  "children": [{"name": "sdb1", "path": "/dev/sdb1", "type": "part",
                                                "fstype": "iso9660", "size": 1, "mountpoints": ["/run/live/medium"]}]}]}
        self.assertEqual(thispc.parse_lsblk(json.dumps(live)), [])

    def test_human_sizes(self):
        self.assertEqual(thispc.human(512110190592), "512.1 GB")
        self.assertEqual(thispc.human(2_000_000_000_000), "2 TB")
        self.assertEqual(thispc.human(None), "")

    def test_mount_refuses_non_devices(self):
        self.assertEqual(thispc.mount("/etc/passwd")[0], False)
        self.assertEqual(thispc.eject("; rm -rf /")[0], False)


if __name__ == "__main__":
    unittest.main()
