#!/usr/bin/env python3
"""Render the X-OS Calamares sidebar + navigation QML offscreen against mock ViewManager /
Branding modules (testing/installer/calamares-mock), at a given step, into one PNG.

    python3 render_calamares_panels.py <branding-dir> <step-index> <out.png>
Needs PySide6 (Qt 6); run inside the image chroot for the image's own Qt."""
import sys
from pathlib import Path
from PySide6.QtCore import QTimer, QUrl, QSize
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor
from PySide6.QtQuick import QQuickView

branding, step, out = Path(sys.argv[1]).resolve(), int(sys.argv[2]), sys.argv[3]
app = QGuiApplication(sys.argv)
mock = str(Path(__file__).resolve().parent / "calamares-mock")


def view(name, size):
    v = QQuickView()
    v.engine().addImportPath(mock)
    v.setResizeMode(QQuickView.SizeRootObjectToView)
    v.resize(size)
    v.setSource(QUrl.fromLocalFile(str(branding / name)))
    for e in v.errors():
        print("QML ERROR", name, e.toString())
        sys.exit(1)
    v.show()
    return v


side = view("calamares-sidebar.qml", QSize(200, 640))
nav = view("calamares-navigation.qml", QSize(830, 72))
vm = side.engine().singletonInstance("io.calamares.ui", "ViewManager")
vm.setProperty("currentStepIndex", step)
br = side.engine().singletonInstance("io.calamares.ui", "Branding")
br.setProperty("brandingDir", str(branding))
vm2 = nav.engine().singletonInstance("io.calamares.ui", "ViewManager")
vm2.setProperty("currentStepIndex", step)


def grab():
    a, b = side.grabWindow(), nav.grabWindow()
    img = QImage(a.width() + b.width(), max(a.height(), b.height()), QImage.Format_RGB32)
    img.fill(QColor("#121417"))
    p = QPainter(img)
    p.drawImage(0, 0, a)
    p.drawImage(a.width(), img.height() - b.height(), b)
    p.end()
    img.save(out)
    app.quit()


QTimer.singleShot(700, grab)
app.exec()
