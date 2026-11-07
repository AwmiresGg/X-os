// X-OS installer navigation bar (Calamares branding, `navigation: qml`).
// Cancel on the leading side as a quiet text button; Back (outlined pill) and Next / Install /
// Done (accent pill) on the trailing side, as in X-OS Setup. Labels, icons and enabled states
// come from Calamares' ViewManager, so translations and the "Install" step stay correct.
import QtQuick
import io.calamares.ui 1.0
import io.calamares.core 1.0

Rectangle {
    id: nav
    color: "#121417"
    implicitHeight: 72
    height: 72
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    readonly property string ui: "Inter"

    component Pill: Rectangle {
        id: pill
        property string label: ""
        property bool primary: false
        property bool quiet: false
        signal activated()
        height: 40
        width: Math.max(primary ? 132 : 104, txt.implicitWidth + 44)
        radius: 20
        opacity: enabled ? 1 : 0.4
        color: !enabled ? "transparent"
             : primary ? (mouse.pressed ? "#1E6A62" : mouse.containsMouse ? "#1D635C" : "#17524C")
             : (mouse.pressed ? "#181B1F" : mouse.containsMouse ? "#22262B" : "transparent")
        border.width: quiet ? 0 : (activeFocus ? 2 : 1)
        border.color: primary || activeFocus ? "#2BC4B0" : Qt.rgba(1, 1, 1, 0.18)
        activeFocusOnTab: enabled
        Behavior on color { ColorAnimation { duration: 120 } }
        Text {
            id: txt
            anchors.centerIn: parent
            text: pill.label.replace("&", "")
            color: pill.quiet ? "#9AA1AB" : "#ECEEF1"
            font.family: nav.ui
            font.pixelSize: 14
            font.weight: pill.primary ? Font.DemiBold : Font.Medium
        }
        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            enabled: pill.enabled
            cursorShape: Qt.PointingHandCursor
            onClicked: pill.activated()
        }
        Keys.onReturnPressed: pill.activated()
        Keys.onEnterPressed: pill.activated()
        Keys.onSpacePressed: pill.activated()
        Accessible.role: Accessible.Button
        Accessible.name: txt.text
        Accessible.onPressAction: pill.activated()
    }

    Rectangle {               // hairline separating the page from the controls
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 8
        anchors.rightMargin: 20
        height: 1
        color: Qt.rgba(1, 1, 1, 0.06)
    }

    // On the last page ("All done") there is nothing to go back or forward to: the only action
    // is Done (Calamares' quit, which also performs "Restart now" when ticked), so it becomes
    // the single primary button on the trailing side.
    // (rowCount() is not a notifying property; currentStepIndex is, and re-evaluates this.)
    readonly property bool lastPage: ViewManager.rowCount() > 1
        && ViewManager.currentStepIndex >= ViewManager.rowCount() - 1

    Pill {
        id: quit
        // positioned with x, not by switching anchors (anchor changes need AnchorChanges)
        x: nav.lastPage ? nav.width - width - 20 : 8
        anchors.verticalCenter: parent.verticalCenter
        quiet: !nav.lastPage
        primary: nav.lastPage
        label: ViewManager.quitLabel
        visible: ViewManager.quitVisible
        enabled: ViewManager.quitEnabled
        onActivated: ViewManager.quit()
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10
        visible: ViewManager.backAndNextVisible && !nav.lastPage
        Pill {
            label: ViewManager.backLabel
            enabled: ViewManager.backEnabled
            onActivated: ViewManager.back()
        }
        Pill {
            primary: true
            label: ViewManager.nextLabel
            enabled: ViewManager.nextEnabled
            onActivated: ViewManager.next()
        }
    }
}
