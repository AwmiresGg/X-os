import tempfile
import unittest
from pathlib import Path
from unittest import mock

from xos import shellstatus as ss


def w(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class BatteryTests(unittest.TestCase):
    def test_laptop_on_battery(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            ps = r / "sys/class/power_supply"
            for k, v in {"type": "Battery", "status": "Discharging", "energy_now": "38800000",
                         "energy_full": "40000000"}.items():
                w(ps / "BAT0" / k, v)
            w(ps / "AC/type", "Mains")
            w(ps / "AC/online", "0")
            # a wireless mouse battery must be ignored
            w(ps / "hidpp_battery_0/type", "Battery")
            w(ps / "hidpp_battery_0/scope", "Device")
            w(ps / "hidpp_battery_0/capacity", "5")
            b = ss.read_battery(r)
        self.assertEqual((b.present, b.percent, b.charging, b.source), (True, 97, False, "Battery"))
        self.assertEqual(b.icon(), "battery-full")

    def test_desktop_without_battery(self):
        with tempfile.TemporaryDirectory() as t:
            b = ss.read_battery(Path(t))
        self.assertFalse(b.present)
        self.assertEqual(b.icon(), "power")

    def test_icon_levels(self):
        self.assertEqual(ss.Battery(True, 8).icon(), "battery-empty")
        self.assertEqual(ss.Battery(True, 50, charging=True).icon(), "battery-charging")


class NetworkTests(unittest.TestCase):
    def test_parse_general(self):
        self.assertEqual(ss.parse_nmcli_general("connected:enabled\n"), ("connected", True))
        self.assertEqual(ss.parse_nmcli_general("connected (site only):disabled\n"), ("connected", False))
        self.assertEqual(ss.parse_nmcli_general(""), ("unknown", False))

    def test_parse_active_prefers_ethernet_and_detects_vpn(self):
        text = "Home\\:5G:802-11-wireless\nWired connection 1:802-3-ethernet\nwg0:wireguard\nlo:loopback\n"
        self.assertEqual(ss.parse_nmcli_active(text), ("ethernet", "Wired connection 1", True))
        self.assertEqual(ss.parse_nmcli_active("Home\\:5G:802-11-wireless\n"), ("wifi", "Home:5G", False))

    def test_signal_and_icon(self):
        self.assertEqual(ss.parse_wifi_signal(" :40\n*:82\n"), 82)
        self.assertEqual(ss.Network("connected", "wifi", "x", 82, True).icon(), "wifi-3")
        self.assertEqual(ss.Network("connected", "wifi", "x", 30, True).icon(), "wifi-1")
        self.assertEqual(ss.Network("connected", "ethernet").icon(), "ethernet")
        self.assertEqual(ss.Network("disconnected", wifi_enabled=False).icon(), "wifi-off")

    def test_no_networkmanager_is_unknown_not_crash(self):
        with mock.patch.object(ss, "_run", return_value=(127, "")):
            self.assertEqual(ss.read_network().state, "unknown")


class AudioBluetoothTests(unittest.TestCase):
    def test_wpctl(self):
        self.assertEqual(ss.parse_wpctl_volume("Volume: 0.45\n"), (45, False))
        self.assertEqual(ss.parse_wpctl_volume("Volume: 1.00 [MUTED]\n"), (100, True))
        self.assertIsNone(ss.parse_wpctl_volume("error"))
        self.assertEqual(ss.Audio(True, 50).icon(), "volume-medium")
        self.assertEqual(ss.Audio(True, 50, muted=True).icon(), "volume-mute")

    def test_set_volume_clamps(self):
        calls = []
        with mock.patch.object(ss, "_run", side_effect=lambda c, **k: calls.append(c) or (0, "")):
            ss.set_volume(150)
        self.assertEqual(calls[0][-1], "1.00")

    def test_rfkill(self):
        self.assertTrue(ss.parse_rfkill_bluetooth("wlan unblocked unblocked\nbluetooth unblocked unblocked\n"))
        self.assertFalse(ss.parse_rfkill_bluetooth("bluetooth blocked unblocked\n"))
        self.assertIsNone(ss.parse_rfkill_bluetooth("wlan unblocked unblocked\n"))


class BrightnessTests(unittest.TestCase):
    def test_read_and_set_via_logind(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            w(r / "sys/class/backlight/intel_backlight/max_brightness", "1000")
            w(r / "sys/class/backlight/intel_backlight/brightness", "500")
            w(r / "sys/class/backlight/intel_backlight/type", "raw")
            b = ss.read_brightness(r)
        self.assertEqual((b.available, b.device, b.percent), (True, "intel_backlight", 50))
        calls = []
        with mock.patch.object(ss, "_run", side_effect=lambda c, **k: calls.append(c) or (0, "")):
            self.assertTrue(ss.set_brightness(0, b))
        self.assertEqual(calls[0][:2], ["busctl", "call"])
        self.assertEqual(calls[0][-1], "10")      # never fully dark: minimum 1 %

    def test_power_actions_are_real_commands(self):
        self.assertEqual(ss.POWER_ACTIONS["sleep"], ["systemctl", "suspend"])
        self.assertEqual(ss.POWER_ACTIONS["lock"], ["loginctl", "lock-session"])


if __name__ == "__main__":
    unittest.main()
