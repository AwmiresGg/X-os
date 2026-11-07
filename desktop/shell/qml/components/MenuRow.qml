// One row in a menu: label, optional detail, hover highlight in the accent, keyboard activatable.
import QtQuick
import XOS.Theme

Item {
    id: row
    property string text
    property string detail
    property string glyph
    property bool separator: false
    property bool enabled: true
    property bool destructive: false
    signal triggered()

    width: parent ? parent.width : 220
    height: separator ? 9 : 28
    Accessible.role: separator ? Accessible.Separator : Accessible.MenuItem
    Accessible.name: text
    activeFocusOnTab: !separator && enabled
    Keys.onReturnPressed: if (enabled) triggered()
    Keys.onSpacePressed: if (enabled) triggered()

    Rectangle {
        visible: row.separator
        anchors.verticalCenter: parent.verticalCenter
        x: 8; width: parent.width - 16; height: 1
        color: Theme.border
    }
    Rectangle {
        id: hl
        visible: !row.separator
        anchors.fill: parent
        radius: Theme.radiusXs
        color: (mouse.containsMouse || row.activeFocus) && row.enabled ? Theme.accentDeep : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.durHover } }
    }
    Row {
        visible: !row.separator
        anchors.verticalCenter: parent.verticalCenter
        x: 10
        spacing: 8
        Glyph {
            visible: row.glyph !== ""
            name: row.glyph
            size: 15
            tint: !row.enabled ? Theme.textFaint : Theme.text
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: row.text
            color: !row.enabled ? Theme.textFaint : (row.destructive && mouse.containsMouse ? Theme.danger : Theme.text)
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    Text {
        visible: !row.separator && row.detail !== ""
        text: row.detail
        color: Theme.textDim
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontCaption + 1
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: !row.separator
        hoverEnabled: true
        onClicked: if (row.enabled) row.triggered()
    }
}
