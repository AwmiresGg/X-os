"""Design-token checks: generated QML is in sync, contrast meets WCAG, one accent only."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS = json.loads((ROOT / "ui/theme/tokens.json").read_text())


def rgb(hexstr):
    h = hexstr.lstrip("#")
    if len(h) == 8:          # AARRGGBB (Qt order)
        h = h[2:]
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def luminance(c):
    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(rgb(a)), luminance(rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TokenTests(unittest.TestCase):
    def test_generated_qml_in_sync(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/gen-theme.py"), "--check"])
        self.assertEqual(r.returncode, 0)

    def test_text_contrast_wcag_aa(self):
        for mode, c in TOKENS["color"].items():
            for surface in ("bg", "surface0", "surface1", "surface2"):
                self.assertGreaterEqual(contrast(c["text"], c[surface]), 7.0, f"{mode} text/{surface}")
                self.assertGreaterEqual(contrast(c["textDim"], c[surface]), 4.5, f"{mode} textDim/{surface}")

    def test_accent_is_visible_as_ui_component(self):
        # WCAG 1.4.11: UI components / focus indicators need 3:1 against adjacent colours.
        for mode, c in TOKENS["color"].items():
            for surface in ("bg", "surface0", "surface1"):
                self.assertGreaterEqual(contrast(c["accent"], c[surface]), 3.0, f"{mode} accent/{surface}")
            self.assertGreaterEqual(contrast(c["onAccent"], c["accentDeep"]), 4.5, f"{mode} onAccent/accentDeep")

    def test_single_accent_hue(self):
        import colorsys
        hues = []
        for c in TOKENS["color"].values():
            for key in ("accent", "accentDeep"):
                h, l, s = colorsys.rgb_to_hls(*rgb(c[key]))
                hues.append(h * 360)
        self.assertLess(max(hues) - min(hues), 12, f"accent hues drift: {hues}")

    def test_motion_tokens_are_restrained(self):
        m = TOKENS["motion"]
        self.assertLessEqual(m["slide"]["ms"], 300, "frequent action must stay under 300 ms")
        self.assertLess(m["fadeOut"]["ms"], m["fadeIn"]["ms"], "exit must be subtler than enter")
        self.assertLess(m["popoverOut"]["ms"], m["popoverIn"]["ms"])
        for k, v in m.items():
            self.assertEqual(len(v["bezier"]), 4, k)


if __name__ == "__main__":
    unittest.main()
