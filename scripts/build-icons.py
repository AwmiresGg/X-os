#!/usr/bin/env python3
"""Build the X-OS icon family from icons/xos/glyphs.json.

* writes icons/xos/symbolic/<category>/<name>.svg (stroke style applied uniformly)
* validates every glyph against icons/xos/ICONS.md (grid, live area, no colours/text/images)
* writes icons/xos/index.json
* generates icons/xos/apps/xos-<name>.svg tiles for every glyph in the "apps" category

    scripts/build-icons.py            # build + validate
    scripts/build-icons.py --check    # validate the committed files match the source (tests)
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "icons/xos/glyphs.json"
OUT = ROOT / "icons/xos"
SVGNS = "http://www.w3.org/2000/svg"
LO, HI = 1.5, 22.5
STROKE = 1.75

HEAD = (f'<svg xmlns="{SVGNS}" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
        f'stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round">')

TILE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
        '<defs><linearGradient id="h" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.06"/>'
        '<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient></defs>'
        '<rect x="2.5" y="2.5" width="59" height="59" rx="15" fill="#22262B" stroke="#FFFFFF" stroke-opacity="0.16"/>'
        '<rect x="3" y="3" width="58" height="58" rx="14.5" fill="url(#h)"/>'
        # glyph scaled 24 -> 32 px; stroke kept at 1.75 in glyph units (renders 2.33 px at 64)
        '<g transform="translate(16 16) scale(1.3333)" fill="none" stroke="#ECEEF1" stroke-width="1.75" '
        'stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>')


def glyph_svg(body: str) -> str:
    # class="fill" marks small solid details: currentColor fill, no stroke
    body = body.replace('class="fill"', 'fill="currentColor" stroke="none"')
    return HEAD + body + "</svg>\n"


def tile_svg(body: str) -> str:
    return TILE.format(body=body.replace('class="fill"', 'fill="#ECEEF1" stroke="none"')) + "\n"


_NUM = re.compile(r"-?\d*\.?\d+(?:e-?\d+)?")


def path_points(d: str):
    """Absolute end/control points of a path (enough to check the live area)."""
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    x = y = sx = sy = 0.0
    cmd, i, pts = None, 0, []
    arity = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                x, y = sx, sy
                continue
        if cmd is None:
            raise ValueError("path data does not start with a command")
        n = arity[cmd.upper()]
        args = [float(v) for v in tokens[i:i + n]]
        if len(args) < n:
            raise ValueError(f"truncated path command {cmd}")
        i += n
        rel = cmd.islower()
        U = cmd.upper()
        if U == "H":
            x = args[0] + (x if rel else 0)
        elif U == "V":
            y = args[0] + (y if rel else 0)
        elif U == "A":
            x, y = (args[5] + x, args[6] + y) if rel else (args[5], args[6])
        else:
            for k in range(0, n, 2):
                px, py = args[k] + (x if rel else 0), args[k + 1] + (y if rel else 0)
                pts.append((px, py))
            x, y = pts[-1]
        pts.append((x, y))
        if U == "M":
            sx, sy = x, y
            cmd = "l" if rel else "L"          # implicit lineto after moveto
    return pts


def validate(name: str, svg: str) -> list[str]:
    errs = []
    root = ET.fromstring(svg)
    if root.get("viewBox") != "0 0 24 24":
        errs.append("viewBox must be 0 0 24 24")
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag in ("text", "image", "style", "script", "use", "foreignObject"):
            errs.append(f"forbidden element <{tag}>")
        for attr in ("fill", "stroke"):
            v = el.get(attr)
            if v not in (None, "none", "currentColor"):
                errs.append(f"<{tag}> {attr}={v!r} (only none/currentColor)")
        sw = el.get("stroke-width")
        if sw is not None and el is not root:
            errs.append(f"<{tag}> overrides stroke-width")
        if el.get("transform"):
            errs.append(f"<{tag}> uses a transform")
        pts = []
        if tag == "path":
            pts = path_points(el.get("d", ""))
        elif tag == "rect":
            x, y, w, h = (float(el.get(k, 0)) for k in ("x", "y", "width", "height"))
            pts = [(x, y), (x + w, y + h)]
        elif tag == "circle":
            cx, cy, r = (float(el.get(k, 0)) for k in ("cx", "cy", "r"))
            pts = [(cx - r, cy - r), (cx + r, cy + r)]
        elif tag == "line":
            pts = [(float(el.get("x1")), float(el.get("y1"))), (float(el.get("x2")), float(el.get("y2")))]
        for px, py in pts:
            if not (LO <= px <= HI and LO <= py <= HI):
                errs.append(f"<{tag}> point ({px:g},{py:g}) outside live area")
                break
    return [f"{name}: {e}" for e in errs]


def build(write: bool = True) -> tuple[dict, list[str]]:
    src = json.loads(SRC.read_text())
    index, errors, seen = {}, [], {}
    for cat, glyphs in src.items():
        if cat.startswith("_"):
            continue
        for name, body in glyphs.items():
            if name in seen:
                errors.append(f"{name}: defined in both {seen[name]} and {cat}")
            seen[name] = cat
            svg = glyph_svg(body)
            errors += validate(name, svg)
            rel = f"symbolic/{cat}/{name}.svg"
            index[name] = {"category": cat, "file": rel,
                           "keywords": sorted(set(name.split("-")) | {cat})}
            files = {OUT / rel: svg}
            if cat == "apps":
                index[name]["tile"] = f"apps/xos-{name}.svg"
                files[OUT / "apps" / f"xos-{name}.svg"] = tile_svg(body)
            for path, text in files.items():
                if write:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text)
                elif not path.exists() or path.read_text() != text:
                    errors.append(f"{path.relative_to(ROOT)} is out of date (run scripts/build-icons.py)")
    idx_text = json.dumps({"schema": 1, "icons": index}, indent=2) + "\n"
    if write:
        (OUT / "index.json").write_text(idx_text)
    elif (OUT / "index.json").read_text() != idx_text:
        errors.append("icons/xos/index.json is out of date")
    return index, errors


def main() -> int:
    check = "--check" in sys.argv
    if not check:
        # stale generated files from earlier icon sets
        for d in (OUT / "symbolic", OUT / "apps"):
            if d.is_dir():
                for f in d.rglob("*.svg"):
                    f.unlink()
    index, errors = build(write=not check)
    for e in errors:
        print("ERROR", e)
    print(f"{len(index)} glyphs, {sum(1 for v in index.values() if 'tile' in v)} app tiles, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
