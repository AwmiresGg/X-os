// An X-OS line glyph, tinted on the CPU by the shell's image provider (works with
// software rendering, no shader needed).
import QtQuick
import XOS.Theme

Image {
    property string name
    property color tint: Theme.text
    property int size: 16
    width: size
    height: size
    sourceSize: Qt.size(size * 2, size * 2)
    source: name ? "image://xicon/" + name + "?color=" + tint.toString() : ""
    smooth: true
    asynchronous: false
}
