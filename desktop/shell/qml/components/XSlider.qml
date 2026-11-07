// Compact slider. Emits moved(value) while dragging (0..1); value is the source of truth.
import QtQuick
import XOS.Theme

Item {
    id: s
    property real value: 0.5
    property string glyph
    property string label
    signal moved(real value)
    height: 26
    Accessible.role: Accessible.Slider
    Accessible.name: label
    activeFocusOnTab: true
    Keys.onLeftPressed: moved(Math.max(0, value - 0.05))
    Keys.onRightPressed: moved(Math.min(1, value + 0.05))

    Glyph {
        id: g
        visible: s.glyph !== ""
        name: s.glyph
        size: 15
        tint: Theme.textDim
        anchors.verticalCenter: parent.verticalCenter
    }
    Item {
        id: track
        anchors.left: g.visible ? g.right : parent.left
        anchors.leftMargin: g.visible ? 8 : 0
        anchors.right: parent.right
        height: parent.height
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width; height: 6; radius: 3
            color: Theme.surface2
            border.width: s.activeFocus ? 1 : 0
            border.color: Theme.accent
            Rectangle { width: Math.max(6, parent.width * s.value); height: parent.height; radius: 3; color: Theme.accent }
        }
        Rectangle {
            width: 16; height: 16; radius: 8
            anchors.verticalCenter: parent.verticalCenter
            x: (parent.width - width) * s.value
            color: "white"
            border.color: Theme.borderStrong
        }
        MouseArea {
            anchors.fill: parent
            function at(mx) { return Math.max(0, Math.min(1, mx / width)) }
            onPressed: (m) => s.moved(at(m.x))
            onPositionChanged: (m) => { if (pressed) s.moved(at(m.x)) }
        }
    }
}
