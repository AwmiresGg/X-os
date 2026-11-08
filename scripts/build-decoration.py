#!/usr/bin/env python3
"""Generate the X-OS window decoration (KWin Aurorae SVG themes XOS-Dark / XOS-Light).

    scripts/build-decoration.py          # writes themes/decoration/<theme>/
    scripts/build-decoration.py --check  # exit 1 if the committed files are out of date

Design (documentation/design/DESIGN-SYSTEM.md, "Window controls"):
  * buttons on the left: close, minimize, maximize — 12 px dots, quiet neutral at rest;
  * colour + glyph only on hover: close = danger, minimize = warning, maximize = X-OS accent;
  * unfocused windows: hollow rings; title bar = window surface, 10 px top corners.
Colours come from ui/theme/tokens.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = json.loads((ROOT / "ui/theme/tokens.json").read_text())
OUT = ROOT / "themes/decoration"

TITLE_H = 34        # title bar height
BTN = 16            # button cell (hit area)
DOT_R = 6           # dot radius (12 px)
RADIUS = 10         # top corner radius
SVGNS = 'xmlns="http://www.w3.org/2000/svg"'


def rgb(hexstr: str) -> str:
    h = hexstr.lstrip("#")
    return "#" + (h[2:] if len(h) == 8 else h)


def palette(mode: str) -> dict:
    c = TOKENS["color"][mode]
    dark = mode == "dark"
    return {
        "title": rgb(c["surface1"]),
        "titleInactive": rgb(c["surface0"]),
        "edge": "#2F3136" if dark else "#D5D7DC",          # 1 px window outline
        "highlight": "#FFFFFF",
        "highlightOpacity": 0.06 if dark else 0.9,
        "dot": "#3B3E44" if dark else "#C9CBD1",            # quiet resting state
        "ring": "#3B3E44" if dark else "#BDBFC6",
        "close": rgb(c["danger"]) if dark else "#E0555E",
        "minimize": rgb(c["warning"]) if dark else "#E2A93B",
        "maximize": rgb(c["accent"]),
        "glyph": "#14161A",
        "text": rgb(c["text"]),
        "textInactive": rgb(c["textFaint"]),
    }


# --------------------------------------------------------------------------- buttons
def glyph(kind: str) -> str:
    cx = cy = BTN / 2
    s = 'fill="none" stroke="{g}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.75"'
    if kind == "close":
        d = 2.1
        return f'<path d="M{cx-d} {cy-d}L{cx+d} {cy+d}M{cx+d} {cy-d}L{cx-d} {cy+d}" {s}/>'
    if kind == "minimize":
        return f'<path d="M{cx-2.7} {cy}H{cx+2.7}" {s}/>'
    if kind == "maximize":     # two corner arrows pointing outwards (expand)
        return (f'<path d="M{cx-2.8} {cy+0.2}V{cy-2.8}H{cx-0.2}M{cx+2.8} {cy-0.2}V{cy+2.8}H{cx+0.2}" {s}/>')
    if kind == "restore":      # corner arrows pointing inwards (contract)
        return (f'<path d="M{cx-1.0} {cy-3.2}V{cy-1.0}H{cx-3.2}M{cx+1.0} {cy+3.2}V{cy+1.0}H{cx+3.2}" {s}/>')
    raise ValueError(kind)


def button_svg(kind: str, p: dict) -> str:
    color = p["maximize" if kind == "restore" else kind]
    cx = cy = BTN / 2
    g = glyph(kind).replace("{g}", p["glyph"])

    def group(gid, body):
        # an invisible full-cell rect fixes every element's size to the button cell
        return (f'<g id="{gid}"><rect x="0" y="0" width="{BTN}" height="{BTN}" fill="none" stroke="none"/>'
                f'{body}</g>')
    dot = lambda fill: f'<circle cx="{cx}" cy="{cy}" r="{DOT_R}" fill="{fill}"/>'
    ring = lambda col: f'<circle cx="{cx}" cy="{cy}" r="{DOT_R - 0.6}" fill="none" stroke="{col}" stroke-width="1.2"/>'
    parts = [
        group("active-center", dot(p["dot"])),
        group("hover-center", dot(color) + g),
        group("pressed-center", dot(color) + f'<circle cx="{cx}" cy="{cy}" r="{DOT_R}" fill="#000000" fill-opacity="0.18"/>' + g),
        group("inactive-center", ring(p["ring"])),
        group("hover-inactive-center", dot(color) + g),
        group("pressed-inactive-center", dot(color) + g),
        group("deactivated-center", ring(p["ring"])),
        group("deactivated-inactive-center", ring(p["ring"])),
    ]
    return f'<svg {SVGNS} width="{BTN}" height="{BTN}" viewBox="0 0 {BTN} {BTN}">' + "".join(parts) + "</svg>\n"


# --------------------------------------------------------------------------- frame
def frame(prefix: str, title: str, p: dict, rounded: bool) -> str:
    """9-patch elements for one decoration state. Tile size 10 px; 1 px outline on the
    sides and bottom; rounded top corners (except maximized)."""
    t, r = 10, RADIUS
    e, hl, ho = p["edge"], p["highlight"], p["highlightOpacity"]
    out = []

    def el(name, x, body):
        out.append(f'<g id="{prefix}-{name}" transform="translate({x} 0)">{body}</g>')
    # top row
    if rounded:
        tl = (f'<path d="M0 {t}V{r}A{r} {r} 0 0 1 {r} 0H{t}V{t}Z" fill="{title}"/>'
              f'<path d="M0.5 {t}V{r}A{r - 0.5} {r - 0.5} 0 0 1 {r} 0.5H{t}" fill="none" stroke="{e}"/>'
              f'<path d="M1.5 {t}V{r}A{r - 1.5} {r - 1.5} 0 0 1 {r} 1.5H{t}" fill="none" stroke="{hl}" stroke-opacity="{ho}"/>')
        tr = (f'<g transform="translate({t} 0) scale(-1 1)">'
              f'<path d="M0 {t}V{r}A{r} {r} 0 0 1 {r} 0H{t}V{t}Z" fill="{title}"/>'
              f'<path d="M0.5 {t}V{r}A{r - 0.5} {r - 0.5} 0 0 1 {r} 0.5H{t}" fill="none" stroke="{e}"/>'
              f'<path d="M1.5 {t}V{r}A{r - 1.5} {r - 1.5} 0 0 1 {r} 1.5H{t}" fill="none" stroke="{hl}" stroke-opacity="{ho}"/></g>')
    else:
        tl = f'<rect width="{t}" height="{t}" fill="{title}"/>'
        tr = tl
    top = (f'<rect width="{t}" height="{t}" fill="{title}"/>'
           + (f'<rect width="{t}" height="1" fill="{e}"/><rect y="1" width="{t}" height="1" fill="{hl}" fill-opacity="{ho}"/>' if rounded else ""))
    side = (f'<rect width="1" height="{t}" fill="{e}"/>' if rounded else f'<rect width="1" height="{t}" fill="{title}"/>')
    el("topleft", 0, tl)
    el("top", 20, top)
    el("topright", 40, tr)
    out.append(f'<g id="{prefix}-left" transform="translate(0 20)">{side}</g>')
    out.append(f'<g id="{prefix}-center" transform="translate(20 20)"><rect width="{t}" height="{t}" fill="{title}"/></g>')
    out.append(f'<g id="{prefix}-right" transform="translate(40 20)">{side}</g>')
    bottom = (f'<rect width="{t}" height="1" fill="{e}"/>' if rounded else f'<rect width="{t}" height="1" fill="{title}"/>')
    corner = (f'<rect width="1" height="1" fill="{e}"/>')
    out.append(f'<g id="{prefix}-bottomleft" transform="translate(0 40)">{corner}</g>')
    out.append(f'<g id="{prefix}-bottom" transform="translate(20 40)">{bottom}</g>')
    out.append(f'<g id="{prefix}-bottomright" transform="translate(40 40)">{corner}</g>')
    return "".join(out)


def decoration_svg(p: dict) -> str:
    body = (frame("decoration", p["title"], p, True)
            + f'<g transform="translate(60 0)">{frame("decoration-inactive", p["titleInactive"], p, True)}</g>'
            + f'<g transform="translate(120 0)">{frame("decoration-maximized", p["title"], p, False)}</g>'
            + f'<g transform="translate(180 0)">{frame("decoration-maximized-inactive", p["titleInactive"], p, False)}</g>')
    return f'<svg {SVGNS} width="240" height="60" viewBox="0 0 240 60">{body}</svg>\n'


def rgb_tuple(h: str) -> str:
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def themerc(p: dict) -> str:
    edge = (TITLE_H - BTN) // 2
    return f"""[General]
ActiveTextColor={rgb_tuple(p["text"])}
InactiveTextColor={rgb_tuple(p["textInactive"])}
TitleAlignment=Center
TitleVerticalAlignment=Center
Animation=120
UseTextShadow=false
Shadow=false

[Layout]
BorderLeft=1
BorderRight=1
BorderBottom=1
TitleEdgeTop={edge}
TitleEdgeBottom={edge}
TitleEdgeLeft=12
TitleEdgeRight=12
TitleEdgeTopMaximized={edge}
TitleEdgeBottomMaximized={edge}
TitleEdgeLeftMaximized=12
TitleEdgeRightMaximized=12
TitleBorderLeft=12
TitleBorderRight=12
TitleHeight={BTN}
ButtonWidth={BTN}
ButtonHeight={BTN}
ButtonSpacing=6
ButtonMarginTop=0
ExplicitButtonSpacer=10
PaddingTop=0
PaddingBottom=0
PaddingLeft=0
PaddingRight=0
"""


def metadata(name: str, mode: str) -> str:
    return (f"[Desktop Entry]\nName=X-OS {mode.capitalize()}\nComment=X-OS window decoration ({mode})\n"
            f"X-KDE-PluginInfo-Name={name}\nX-KDE-PluginInfo-Author=X-OS project\n"
            f"X-KDE-PluginInfo-License=BSL-1.0\nX-KDE-PluginInfo-Version=1.0\n")


def files() -> dict:
    out = {}
    for mode in ("dark", "light"):
        name = f"XOS-{mode.capitalize()}"
        p = palette(mode)
        d = OUT / name
        out[d / "decoration.svg"] = decoration_svg(p)
        for kind in ("close", "minimize", "maximize", "restore"):
            out[d / f"{kind}.svg"] = button_svg(kind, p)
        out[d / f"{name}rc"] = themerc(p)
        out[d / "metadata.desktop"] = metadata(name, mode)
    return out


def main() -> int:
    stale = []
    for path, text in files().items():
        if "--check" in sys.argv:
            if not path.exists() or path.read_text() != text:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    if stale:
        print("out of date (run scripts/build-decoration.py):", *stale, sep="\n  ")
        return 1
    if "--check" not in sys.argv:
        print(f"wrote {len(files())} files to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
