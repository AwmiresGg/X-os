import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from xos import compat


def make_pe(machine=0x8664, subsystem=2, extra=b"", dotnet=False, pe32plus=True):
    """Construct a minimal, structurally valid PE header."""
    pe_off = 0x80
    buf = bytearray(0x400)
    buf[0:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, pe_off)
    buf[pe_off:pe_off + 4] = b"PE\0\0"
    struct.pack_into("<H", buf, pe_off + 4, machine)
    opt = pe_off + 24
    struct.pack_into("<H", buf, opt, 0x20B if pe32plus else 0x10B)
    struct.pack_into("<H", buf, opt + 68, subsystem)
    if dotnet:
        dd = opt + (112 if pe32plus else 96)
        struct.pack_into("<II", buf, dd + 14 * 8, 0x2008, 0x48)
    return bytes(buf) + extra


class DetectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def file(self, name, data):
        p = self.dir / name
        p.write_bytes(data)
        return p

    def test_nsis_x64_gui_installer(self):
        d = compat.detect(self.file("npp.8.6.Installer.x64.exe", make_pe(extra=b"..Nullsoft.NSIS..")))
        self.assertEqual((d.format, d.arch, d.subsystem, d.framework, d.silent_args), ("exe", "x64", "gui", "nsis", "/S"))
        self.assertFalse(d.blockers)
        self.assertEqual(len(d.sha256), 64)

    def test_inno_x86_and_dotnet(self):
        d = compat.detect(self.file("tool.exe", make_pe(machine=0x14C, pe32plus=False, dotnet=True, extra=b"Inno Setup")))
        self.assertEqual((d.arch, d.framework, d.dotnet), ("x86", "inno", True))

    def test_extension_is_not_trusted(self):
        d = compat.detect(self.file("renamed.txt", make_pe()))
        self.assertEqual(d.format, "exe")
        d = compat.detect(self.file("fake.exe", b"#!/bin/sh\necho not windows\n"))
        self.assertEqual(d.format, "unknown")

    def test_driver_and_anticheat_blockers(self):
        self.assertTrue(compat.detect(self.file("drv.sys", make_pe(subsystem=1))).blockers)
        self.assertTrue(compat.detect(self.file("g.exe", make_pe(extra=b"vgk.sys"))).blockers)
        self.assertTrue(compat.detect(self.file("arm.exe", make_pe(machine=0xAA64))).blockers)

    def test_msi(self):
        d = compat.detect(self.file("EpicInstaller-15.msi", compat.OLE_MAGIC + b"\0" * 504))
        self.assertEqual((d.format, d.silent_args), ("msi", "/qn /norestart"))
        self.assertEqual(compat.detect(self.file("old.doc", compat.OLE_MAGIC + b"\0" * 504)).format, "unknown")

    def test_msix_and_bundle(self):
        p = self.dir / "App.msix"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("AppxManifest.xml", "<Package/>")
        self.assertEqual(compat.detect(p).format, "msix")
        p = self.dir / "App.msixbundle"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("AppxMetadata/AppxBundleManifest.xml", "<Bundle/>")
        self.assertEqual(compat.detect(p).format, "msixbundle")
        p = self.dir / "plain.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("readme.txt", "x")
        self.assertEqual(compat.detect(p).format, "unknown")

    def test_batch_and_com(self):
        self.assertEqual(compat.detect(self.file("setup.bat", b"@echo off\r\necho hi\r\n")).format, "bat")
        self.assertEqual(compat.detect(self.file("run.cmd", b"@echo off\r\n")).format, "cmd")
        d = compat.detect(self.file("game.com", b"\xb4\x09\xba\x00\x01\xcd\x21"))
        self.assertEqual((d.format, d.arch), ("com", "x86-16"))


class DatabaseAndPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apps = compat.load_db(compat.default_db_path())

    def test_database_is_valid_and_honest(self):
        ids = [a["id"] for a in self.apps]
        self.assertEqual(len(ids), len(set(ids)))
        for a in self.apps:
            self.assertIn(a["rating"], compat.RATINGS)
            self.assertIs(a["verified_on_xos"], False, f"{a['id']}: only test runs may set verified_on_xos")

    def test_match_by_name_and_generic_names_need_hash(self):
        self.assertEqual(compat.match(self.apps, "/dl/npp.8.6.4.Installer.x64.exe")["id"], "notepad-plus-plus")
        self.assertEqual(compat.match(self.apps, "tsetup-x64.5.2.exe")["id"], "telegram-win")
        self.assertIsNone(compat.match(self.apps, "setup.exe"))

    def test_plan_unknown_app_is_untested_and_isolated(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "Some Tool.exe"
            p.write_bytes(make_pe(machine=0x14C, pe32plus=False, dotnet=True))
            pl = compat.plan(compat.detect(p), None, Path("/home/u"))
            self.assertEqual(pl["rating"], "untested")
            self.assertTrue(pl["can_install"])
            self.assertEqual(pl["prefix"], "/home/u/.local/share/xos/prefixes/some-tool")
            self.assertEqual(pl["prefix_arch"], "win64", "64-bit prefix by default (runs 32-bit installers too)")
            self.assertIn("dotnet48", pl["dependencies"])
            self.assertTrue(any("not in the X-OS compatibility database" in w for w in pl["warnings"]))

    def test_plan_unsupported_cannot_install(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "Install VALORANT.exe"
            p.write_bytes(make_pe())
            entry = compat.match(self.apps, p.name)
            pl = compat.plan(compat.detect(p), entry, Path("/home/u"))
            self.assertEqual((pl["rating"], pl["can_install"]), ("unsupported", False))


if __name__ == "__main__":
    unittest.main()


class InstallStepsTests(unittest.TestCase):
    def plan_for(self, name, data, entry=None):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / name
            p.write_bytes(data)
            return compat.plan(compat.detect(p), entry, Path("/home/u"))

    def test_exe_silent_uses_database_switches(self):
        apps = compat.load_db(compat.default_db_path())
        entry = compat.match(apps, "7z2409-x64.exe")
        pl = self.plan_for("7z2409-x64.exe", make_pe(machine=0x14C, pe32plus=False), entry)
        steps = compat.install_steps(pl, "/dl/7z2409-x64.exe", silent=True)
        self.assertEqual(steps[0], ["wine", "wineboot", "--init"])
        self.assertEqual(steps[-1], ["wine", "/dl/7z2409-x64.exe", "/S"])
        self.assertEqual(compat.install_steps(pl, "/dl/x.exe")[-1], ["wine", "/dl/x.exe"])   # interactive

    def test_msi_and_env(self):
        pl = self.plan_for("tool.msi", compat.OLE_MAGIC + b"\0" * 504)
        steps = compat.install_steps(pl, "/dl/tool.msi", silent=True)
        self.assertEqual(steps[-1], ["wine", "msiexec", "/i", "/dl/tool.msi", "/qn", "/norestart"])
        env = compat.env_for(pl, {"PATH": "/usr/bin"})
        self.assertEqual((env["WINEPREFIX"], env["WINEARCH"]), (pl["prefix"], "win64"))

    def test_unsupported_and_msix_refused(self):
        pl = self.plan_for("Install VALORANT.exe", make_pe(),
                           compat.match(compat.load_db(compat.default_db_path()), "Install VALORANT.exe"))
        with self.assertRaises(ValueError):
            compat.install_steps(pl, "/dl/v.exe")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "App.msix"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("AppxManifest.xml", "<Package/>")
            with self.assertRaises(ValueError):
                compat.install_steps(compat.plan(compat.detect(p), None, Path("/h")), str(p))


class SilentSwitchTests(unittest.TestCase):
    def test_msi_ignores_exe_switches_from_database(self):
        apps = compat.load_db(compat.default_db_path())
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "7z2409-x64.msi"
            p.write_bytes(compat.OLE_MAGIC + b"\0" * 504)
            pl = compat.plan(compat.detect(p), compat.match(apps, p.name), Path("/h"))
        self.assertEqual(pl["silent_args"], "/qn /norestart")
