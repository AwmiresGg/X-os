// X-OS installer sidebar (Calamares branding, `sidebar: qml`).
// Same language as X-OS Setup: a rounded card, the X-OS mark, numbered steps; finished steps
// get a check, the current one the accent. Uses only Calamares' documented QML API
// (ViewManager model + currentStepIndex, Branding).
import QtQuick
import io.calamares.ui 1.0
import io.calamares.core 1.0

Rectangle {
    id: side
    color: "#1A1B1E"
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    readonly property color cText: "#EDEEF0"
    readonly property color cDim: "#A0A4AC"
    readonly property color cFaint: "#6A6E77"
    readonly property color cAccent: "#7A8CFF"
    readonly property color cAccentDeep: "#2E3566"
    readonly property string ui: "Inter"

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: 14
        anchors.rightMargin: 4
        radius: 18
        color: "#212226"
        border.color: Qt.rgba(1, 1, 1, 0.07)

        Column {
            id: head
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 20
            spacing: 10
            Image {
                width: 46; height: 46
                sourceSize: Qt.size(92, 92)
                source: "file:" + Branding.imagePath(Branding.ProductLogo)
                smooth: true
            }
            Text {
                text: Branding.string(Branding.ProductName)
                color: side.cText
                font.family: side.ui
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }
            Text {
                // "Installer" is a product label, not a step; kept untranslated like the name.
                text: "Installer · " + Branding.string(Branding.ShortVersion)
                color: side.cFaint
                font.family: side.ui
                font.pixelSize: 12
            }
        }

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: head.bottom
            anchors.topMargin: 26
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 4

            Repeater {
                model: ViewManager
                delegate: Item {
                    id: step
                    required property int index
                    required property string display
                    readonly property bool current: index === ViewManager.currentStepIndex
                    readonly property bool done: index < ViewManager.currentStepIndex
                    width: parent.width
                    height: 34

                    Rectangle {
                        anchors.fill: parent
                        radius: 10
                        color: step.current ? Qt.rgba(0.478, 0.549, 1.0, 0.10) : "transparent"
                    }
                    Rectangle {            // step number / check
                        id: dot
                        anchors.left: parent.left
                        anchors.leftMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        width: 22; height: 22; radius: 11
                        color: step.done ? side.cAccent : step.current ? side.cAccentDeep : "transparent"
                        border.width: step.done ? 0 : 1
                        border.color: step.current ? side.cAccent : Qt.rgba(1, 1, 1, 0.22)
                        Text {
                            anchors.centerIn: parent
                            text: step.done ? "✓" : (step.index + 1)
                            color: step.done ? "#141517" : step.current ? side.cText : side.cDim
                            font.family: side.ui
                            font.pixelSize: step.done ? 12 : 11
                            font.weight: Font.DemiBold
                        }
                        Behavior on color { ColorAnimation { duration: 180 } }
                    }
                    Text {
                        anchors.left: dot.right
                        anchors.leftMargin: 12
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: step.display
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignLeft
                        color: step.current ? side.cText : step.done ? side.cDim : side.cFaint
                        font.family: side.ui
                        font.pixelSize: 14
                        font.weight: step.current ? Font.DemiBold : Font.Normal
                    }
                    Accessible.role: Accessible.ListItem
                    Accessible.name: step.display + (step.current ? ", current step" : step.done ? ", done" : "")
                }
            }
        }

        Text {                     // a quiet reminder of the one rule that matters
            // only true until the Install step starts writing
            visible: ViewManager.currentStepIndex < ViewManager.rowCount() - 2
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 20
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignLeft
            text: "Nothing on your disks changes until you press Install."
            color: side.cFaint
            font.family: side.ui
            font.pixelSize: 11
            lineHeight: 1.2
        }
    }
}
