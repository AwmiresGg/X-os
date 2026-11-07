// On/off switch. Purely a view of `checked`; the caller changes real state in onToggled.
import QtQuick
import XOS.Theme

Item {
    id: t
    property bool checked: false
    property string label
    signal toggled(bool value)
    width: 34
    height: 20
    Accessible.role: Accessible.CheckBox
    Accessible.name: label
    Accessible.checked: checked
    activeFocusOnTab: true
    Keys.onSpacePressed: toggled(!checked)

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: t.checked ? Theme.accent : Theme.surface2
        border.width: 1
        border.color: t.activeFocus ? Theme.accent : Theme.border
        Behavior on color { ColorAnimation { duration: Theme.durHover } }
    }
    Rectangle {
        width: 16; height: 16; radius: 8
        y: 2
        x: t.checked ? t.width - width - 2 : 2
        color: "white"
        Behavior on x { NumberAnimation { duration: Theme.durHover; easing.type: Easing.BezierSpline; easing.bezierCurve: Theme.curveHover } }
    }
    MouseArea { anchors.fill: parent; onClicked: t.toggled(!t.checked) }
}
