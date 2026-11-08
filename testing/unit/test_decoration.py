import json
"""X-OS window decoration (Aurorae): generated files in sync and structurally valid."""
import configparser
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEMES = ROOT / "themes/decoration"
STATES = ["active", "hover", "pressed", "inactive", "hover-inactive", "pressed-inactive"]
FRAME = ["topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright"]


def ids(svg: Path) -> set:
    return {e.get("id") for e in ET.parse(svg).iter() if e.get("id")}


class DecorationTests(unittest.TestCase):
    def test_generated_in_sync(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/build-decoration.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_both_themes_complete(self):
        for name in ("XOS-Dark", "XOS-Light"):
            d = THEMES / name
            for kind in ("close", "minimize", "maximize", "restore"):
                missing = {f"{s}-center" for s in STATES} - ids(d / f"{kind}.svg")
                self.assertFalse(missing, f"{name}/{kind}: {missing}")
            frame_ids = ids(d / "decoration.svg")
            for prefix in ("decoration", "decoration-inactive", "decoration-maximized"):
                self.assertFalse({f"{prefix}-{p}" for p in FRAME} - frame_ids, f"{name}: {prefix}")
            rc = configparser.ConfigParser()
            rc.optionxform = str
            rc.read(d / f"{name}rc")
            lay = rc["Layout"]
            title_bar = int(lay["TitleEdgeTop"]) + int(lay["TitleHeight"]) + int(lay["TitleEdgeBottom"])
            self.assertEqual(title_bar, 34)
            self.assertEqual(lay["ButtonWidth"], lay["ButtonHeight"])

    def test_resting_state_is_neutral_and_hover_is_semantic(self):
        svg = (THEMES / "XOS-Dark/close.svg").read_text()
        rest = re.search(r'<g id="active-center">(.*?)</g>', svg).group(1)
        hover = re.search(r'<g id="hover-center">(.*?)</g>', svg).group(1)
        tok = json.loads((ROOT / "ui/theme/tokens.json").read_text())["color"]["dark"]
        self.assertIn("#3B3E44", rest)          # neutral dot, no colour at rest
        self.assertIn(tok["danger"], hover)     # danger colour only on hover
        self.assertIn("<path", hover)           # glyph appears on hover
        self.assertNotIn("<path", rest)
        self.assertIn(tok["accent"], (THEMES / "XOS-Dark/maximize.svg").read_text())   # X-OS accent

    def test_defaults_put_buttons_on_the_left(self):
        hook = (ROOT / "build/hooks/chroot/40-desktop-defaults.sh").read_text()
        self.assertIn("ButtonsOnLeft XIA", hook)
        self.assertIn("__aurorae__svg__XOS-Dark", hook)


if __name__ == "__main__":
    unittest.main()
