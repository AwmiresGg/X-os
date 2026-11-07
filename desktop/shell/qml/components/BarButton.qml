// A menu-bar item: glyph and/or text, accent pill when its menu is open.
import QtQuick
import XOS.Theme

Item {
    id: btn
    property string glyph
    property string text
    property bool bold: false
    property bool open: false
    property int glyphSize: 15
    signal clicked()

    height: parent ? parent.height : 30
    width: content.implicitWidth + 16
    Accessible.role: Accessible.Button
    Accessible.name: text || glyph
    activeFocusOnTab: true
    Keys.onReturnPressed: clicked()
    Keys.onSpacePressed: clicked()

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 4
        anchors.bottomMargin: 4
        radius: Theme.radiusXs
        color: btn.open ? Theme.accentDeep
             : (mouse.containsMouse || btn.activeFocus) ? Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.10)
             : "transparent"
        border.width: btn.activeFocus ? 1 : 0
        border.color: Theme.accent
        Behavior on color { ColorAnimation { duration: Theme.durHover } }
    }
    Row {
        id: content
        anchors.centerIn: parent
        spacing: 5
        Glyph {
            visible: btn.glyph !== ""
            name: btn.glyph
            size: btn.glyphSize
            tint: mouse.containsMouse && !btn.open ? Theme.accent : Theme.text
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            visible: btn.text !== ""
            text: btn.text
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            font.weight: btn.bold ? Font.DemiBold : Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        onClicked: btn.clicked()
    }
}
