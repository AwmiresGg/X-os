"""Icon family: source and generated files in sync, spec-valid, and every glyph the shell
references exists."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = json.loads((ROOT / "icons/xos/index.json").read_text())["icons"]


def referenced_glyphs() -> set[str]:
    names = set()
    for qml in (ROOT / "desktop/shell/qml").rglob("*.qml"):
        for line in qml.read_text().splitlines():
            # only the expression assigned to glyph: / a Glyph's name: (ternaries included)
            exprs = re.findall(r"\bglyph:\s*([^;,}\n]+)", line)
            if "Glyph" in line or re.search(r"\bname:\s*dock\.", line):
                exprs += re.findall(r"\bname:\s*([^;,}\n]+)", line)
            for e in exprs:
                names |= set(re.findall(r'"([a-z0-9-]+)"', e))
    # names produced by the status backends' icon() methods
    src = (ROOT / "lib/python/xos/shellstatus.py").read_text()
    names |= set(re.findall(r'return\s+"([a-z0-9-]+)"', src))
    names |= {f"wifi-{i}" for i in range(4)} | {"trash-full", "trash-empty"}
    # X-OS app icons mapped in the window model
    wsrc = (ROOT / "lib/python/xos/windows.py").read_text()
    block = wsrc[wsrc.index("XOS_ICONS = {"):wsrc.index("}", wsrc.index("XOS_ICONS = {"))]
    names |= set(re.findall(r':\s*"([a-z0-9-]+)"', block))
    return names


class IconTests(unittest.TestCase):
    def test_generated_files_match_source_and_validate(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/build-icons.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_referenced_glyph_exists(self):
        missing = sorted(n for n in referenced_glyphs() if n not in INDEX)
        self.assertEqual(missing, [], f"glyphs referenced by the shell but not drawn: {missing}")

    def test_app_glyphs_have_tiles(self):
        for name, meta in INDEX.items():
            if meta["category"] == "apps":
                self.assertTrue((ROOT / "icons/xos" / meta["tile"]).exists(), name)

    def test_no_colours_in_glyphs(self):
        for meta in INDEX.values():
            svg = (ROOT / "icons/xos" / meta["file"]).read_text()
            self.assertIsNone(re.search(r'#[0-9a-fA-F]{3,8}', svg), meta["file"])


if __name__ == "__main__":
    unittest.main()
