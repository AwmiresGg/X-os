import os
import tempfile
import unittest
from pathlib import Path

from xos import hardware, profiles

GiB = 1024 ** 3


def w(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class FakeSystem:
    """Builds a minimal sysfs/procfs tree."""

    def __init__(self, root: Path):
        self.root = root
        (root / "sys/bus/pci/drivers").mkdir(parents=True)

    def pci(self, addr, cls, vid, did, driver=None, net=None, wireless=False):
        d = self.root / "sys/bus/pci/devices" / addr
        w(d / "class", f"0x{cls:06x}\n")
        w(d / "vendor", f"0x{vid}\n")
        w(d / "device", f"0x{did}\n")
        w(d / "modalias", f"pci:v0000{vid.upper()}d0000{did.upper()}\n")
        if driver:
            drv = self.root / "sys/bus/pci/drivers" / driver
            drv.mkdir(exist_ok=True)
            os.symlink(drv, d / "driver")
        if net:
            n = d / "net" / net
            n.mkdir(parents=True)
            if wireless:
                (n / "wireless").mkdir()
        return d

    def usb(self, name, vid, pid, product, ifclass, driver=None):
        base = self.root / "sys/bus/usb/devices"
        d = base / name
        w(d / "idVendor", vid)
        w(d / "idProduct", pid)
        w(d / "product", product)
        w(d / "speed", "480")
        i = base / f"{name}:1.0"
        w(i / "bInterfaceClass", ifclass)
        if driver:
            drv = self.root / "sys/bus/usb/drivers" / driver
            drv.mkdir(parents=True, exist_ok=True)
            os.symlink(drv, i / "driver")


class HardwareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fs = FakeSystem(self.root)
        w(self.root / "usr/share/misc/pci.ids",
          "# comment\n1002  Advanced Micro Devices, Inc. [AMD/ATI]\n\t1638  Cezanne [Radeon Vega]\n"
          "8086  Intel Corporation\n\t2723  Wi-Fi 6 AX200\n\t\t8086 0084  subsys\nC 00  Unclassified\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_pci_categories_names_and_drivers(self):
        self.fs.pci("0000:05:00.0", 0x030000, "1002", "1638", driver="amdgpu")
        self.fs.pci("0000:02:00.0", 0x028000, "8086", "2723", driver="iwlwifi", net="wlan0", wireless=True)
        self.fs.pci("0000:00:00.0", 0x060000, "1002", "1630")              # host bridge, no driver: fine
        self.fs.pci("0000:03:00.0", 0x010802, "144d", "a808")              # NVMe without driver: problem
        devs = {d.address: d for d in hardware.pci_devices(self.root)}
        gpu = devs["0000:05:00.0"]
        self.assertEqual(gpu.category, "Graphics adapters")
        self.assertEqual(gpu.vendor, "Advanced Micro Devices, Inc. [AMD/ATI]")
        self.assertEqual(gpu.name, "Cezanne [Radeon Vega]")
        self.assertEqual(gpu.driver, "amdgpu")
        self.assertEqual(devs["0000:02:00.0"].category, "Wi-Fi adapters")
        self.assertEqual(devs["0000:00:00.0"].status, "ok")
        self.assertEqual(devs["0000:03:00.0"].status, "no-driver")
        self.assertEqual(devs["0000:03:00.0"].category, "Storage controllers")

    def test_usb_classification(self):
        self.fs.usb("1-1", "046d", "c52b", "USB Receiver", "03", driver="usbhid")
        self.fs.usb("1-2", "8087", "0029", "Bluetooth", "e0", driver="btusb")
        self.fs.usb("1-3", "0bda", "5520", "Integrated Camera", "0e")
        devs = {d.address: d for d in hardware.usb_devices(self.root)}
        self.assertEqual(devs["1-1"].category, "Input devices")
        self.assertEqual(devs["1-2"].category, "Bluetooth adapters")
        self.assertEqual(devs["1-3"].category, "Cameras")
        self.assertEqual(devs["1-3"].status, "no-driver")
        self.assertEqual(devs["1-1"].driver, "usbhid")

    def test_input_devices(self):
        w(self.root / "proc/bus/input/devices",
          'I: Bus=0011\nN: Name="AT Translated Set 2 keyboard"\nS: Sysfs=/devices/platform/i8042/serio0/input/input0\n'
          'H: Handlers=sysrq kbd event0\nB: EV=120013\n\n'
          'I: Bus=0018\nN: Name="SYNA2393:00 06CB:7A13 Touchpad"\nS: Sysfs=/devices/x/input/input5\n'
          'H: Handlers=mouse1 event5\n\n'
          'I: Bus=0003\nN: Name="Logitech USB Optical Mouse"\nS: Sysfs=/devices/y/input/input7\nH: Handlers=mouse2 event7\n')
        cats = sorted(d.category for d in hardware.input_devices(self.root))
        self.assertEqual(cats, ["Keyboards", "Mice", "Touchpads"])

    def test_cpu_memory_and_level(self):
        w(self.root / "proc/cpuinfo",
          "processor\t: 0\nvendor_id\t: AuthenticAMD\nmodel name\t: AMD Ryzen 5 5600U\n"
          "flags\t\t: fpu lm cx16 lahf_lm popcnt sse4_1 sse4_2 ssse3 avx avx2 bmi1 bmi2 f16c fma abm movbe xsave svm\n\n"
          "processor\t: 1\nvendor_id\t: AuthenticAMD\n")
        w(self.root / "proc/meminfo", "MemTotal:        8000000 kB\nMemAvailable:    6000000 kB\nSwapTotal: 0 kB\n")
        c = hardware.cpu_info(self.root)
        self.assertEqual((c["vendor"], c["threads"], c["x86_64_level"], c["virtualization"]), ("AMD", 2, 3, True))
        self.assertEqual(hardware.memory_info(self.root)["total_bytes"], 8000000 * 1024)

    def test_battery_health(self):
        b = self.root / "sys/class/power_supply/BAT0"
        for k, v in {"type": "Battery", "status": "Discharging", "capacity": "81",
                     "energy_full": "40000000", "energy_full_design": "50000000"}.items():
            w(b / k, v)
        w(self.root / "sys/class/power_supply/AC/type", "Mains")
        bats = hardware.batteries(self.root)
        self.assertEqual(len(bats), 1)
        self.assertEqual((bats[0]["capacity_percent"], bats[0]["health_percent"]), (81, 80))

    def test_probe_on_empty_tree_does_not_crash(self):
        hw = hardware.probe(Path(self.tmp.name) / "nonexistent")
        self.assertEqual(hw["devices"], [])
        self.assertEqual(hw["firmware"], "bios")

    def test_probe_runs_on_this_machine(self):
        hw = hardware.probe()
        self.assertGreater(hw["cpu"]["threads"], 0)


class ProfileTests(unittest.TestCase):
    def hw(self, ram_gib, threads, driver="amdgpu"):
        return {"memory": {"total_bytes": int(ram_gib * GiB)}, "cpu": {"threads": threads},
                "gpus": [{"driver": driver}] if driver else []}

    def test_recommendations_match_spec_tiers(self):
        self.assertEqual(profiles.recommend(self.hw(2, 2))[0], "lite")
        self.assertEqual(profiles.recommend(self.hw(4, 4))[0], "balanced")
        self.assertEqual(profiles.recommend(self.hw(8, 8))[0], "balanced")
        self.assertEqual(profiles.recommend(self.hw(16, 8))[0], "performance")
        self.assertEqual(profiles.recommend(self.hw(32, 16, driver=None))[0], "lite")

    def test_security_services_never_disabled(self):
        for pid in profiles.PROFILES:
            units = {a["unit"] for a in profiles.plan(pid) if a["kind"] == "service-disable"}
            self.assertFalse(units & profiles.PROTECTED_SERVICES, pid)

    def test_apply_to_fake_root_writes_config(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            w(root / "etc/xdg/kwinrc", "[Compositing]\nBackend=OpenGL\nAnimationDurationFactor=1\n[Other]\nx=1\n")
            profiles.apply("lite", root=root)
            self.assertEqual(profiles.current(root), "lite")
            kwin = (root / "etc/xdg/kwinrc").read_text()
            self.assertIn("AnimationDurationFactor=0\n", kwin)
            self.assertEqual(kwin.count("AnimationDurationFactor"), 1)
            self.assertIn("Backend=OpenGL", kwin)
            self.assertIn("[Plugins]\nblurEnabled=false", kwin)
            self.assertIn("vm.swappiness = 100", (root / "etc/sysctl.d/60-xos-profile.conf").read_text())
            self.assertIn("dockEffects=static", (root / "etc/xdg/xos-shellrc").read_text())


if __name__ == "__main__":
    unittest.main()
