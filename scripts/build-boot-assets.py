#!/usr/bin/env python3
"""Render X-OS boot artwork (GRUB theme + Plymouth splash) from the committed SVG artwork.

    python3 scripts/build-boot-assets.py        (needs PySide6 with QtSvg; run in the Qt tools env)

Outputs (committed, so image builds need no Qt):
  themes/boot/grub/xos/  background.png, select_*.png (9-slice highlight), logo.png
  themes/boot/plymouth/xos/  logo.png, dot.png, dot-on.png, bullet.png, entry.png
"""
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
GRUB = ROOT / "themes/boot/grub/xos"
PLY = ROOT / "themes/boot/plymouth/xos"
WALL = ROOT / "themes/liquid-glass/wallpapers/x-os-dark.svg"
LOGO = ROOT / "icons/xos/brand/x-os-logo.svg"
ACCENT, ACCENT_DEEP = QColor("#2BC4B0"), QColor("#17524C")


def image(w, h):
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    return img


def svg(path: Path, w: int, h: int, dim: float = 0.0) -> QImage:
    img = image(w, h)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(str(path)).render(p, QRectF(0, 0, w, h))
    if dim:
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, int(255 * dim)))
    p.end()
    return img


def rounded(w, h, r, fill: QColor, rim: QColor | None = None) -> QImage:
    img = image(w, h)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
    p.fillPath(path, fill)
    if rim:
        p.setPen(QPen(rim, 1))
        p.drawPath(path)
    p.end()
    return img


def slice9(src: QImage, prefix: Path, c: int) -> None:
    """GRUB styled box: <prefix>_{nw,n,ne,w,c,e,sw,s,se}.png with corner size c."""
    w, h = src.width(), src.height()
    parts = {"nw": (0, 0, c, c), "n": (c, 0, w - 2 * c, c), "ne": (w - c, 0, c, c),
             "w": (0, c, c, h - 2 * c), "c": (c, c, w - 2 * c, h - 2 * c), "e": (w - c, c, c, h - 2 * c),
             "sw": (0, h - c, c, c), "s": (c, h - c, w - 2 * c, c), "se": (w - c, h - c, c, c)}
    for k, (x, y, ww, hh) in parts.items():
        src.copy(x, y, ww, hh).save(str(prefix.parent / f"{prefix.name}_{k}.png"))


def dot(d, color: QColor) -> QImage:
    img = image(d, d)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(0, 0, d, d))
    p.end()
    return img


def main() -> int:
    QGuiApplication(sys.argv[:1])
    GRUB.mkdir(parents=True, exist_ok=True)
    PLY.mkdir(parents=True, exist_ok=True)

    # GRUB: wallpaper (slightly dimmed so the menu reads), logo, rounded selection box
    bg = svg(WALL, 1920, 1080, dim=0.25)
    bg.save(str(GRUB / "background.png"))
    svg(LOGO, 96, 96).save(str(GRUB / "logo.png"))
    slice9(rounded(60, 44, 12, QColor(23, 82, 76, 235), ACCENT), GRUB / "select", 14)

    # Plymouth: logo, progress dots, password field
    svg(LOGO, 128, 128).save(str(PLY / "logo.png"))
    dot(8, QColor(255, 255, 255, 60)).save(str(PLY / "dot.png"))
    dot(8, ACCENT).save(str(PLY / "dot-on.png"))
    dot(10, QColor("#ECEEF1")).save(str(PLY / "bullet.png"))
    rounded(320, 44, 22, QColor(24, 27, 31, 235), QColor(255, 255, 255, 41)).save(str(PLY / "entry.png"))
    print("boot assets written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
