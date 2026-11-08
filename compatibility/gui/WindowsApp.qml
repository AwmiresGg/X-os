// X-OS "Windows app" dialog. Liquid Glass, dark by default, one accent.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import XOS.Theme

ApplicationWindow {
    id: win
    required property var backend
    readonly property var info: backend.info
    width: 560
    height: 600
    minimumWidth: 480
    minimumHeight: 520
    visible: true
    title: "Install Windows app"
    color: Theme.surface0
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBody

    // Rating badge colours: semantic, not decorative.
    function ratingColor(r) {
        return r === "platinum" || r === "gold" ? Theme.success
             : r === "silver" ? Theme.accent
             : r === "bronze" ? Theme.warning
             : r === "unsupported" ? Theme.danger : Theme.textDim
    }
    function ratingText(r) {
        return ({ platinum: "Runs perfectly", gold: "Runs well", silver: "Runs with minor issues",
                  bronze: "Runs with problems", unsupported: "Does not run on X-OS",
                  untested: "Not tested yet" })[r] || r
    }

    component Card: Rectangle {
        default property alias body: inner.data
        Layout.fillWidth: true
        implicitHeight: inner.implicitHeight + 24
        radius: Theme.radiusMd
        color: Theme.surface1
        border.color: Theme.border
        ColumnLayout { id: inner; x: 14; y: 12; width: parent.width - 28; spacing: 6 }
    }
    component Label_: Label { color: Theme.text; wrapMode: Text.Wrap; Layout.fillWidth: true }
    component Dim: Label { color: Theme.textDim; font.pixelSize: Theme.fontCaption + 1; wrapMode: Text.Wrap; Layout.fillWidth: true }
    component Btn: Button {
        id: b
        property bool primary: false
        contentItem: Label {
            text: b.text; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            color: !b.enabled ? Theme.textFaint : b.primary ? Theme.onAccent : Theme.text
            font.weight: b.primary ? Font.DemiBold : Font.Medium
        }
        background: Rectangle {
            implicitWidth: 120; implicitHeight: 38; radius: 19
            color: !b.enabled ? Theme.surface2 : b.primary ? Theme.accentDeep : (b.hovered ? Theme.surface2 : "transparent")
            border.color: b.primary && b.enabled ? Theme.accent : Theme.borderStrong
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12

        // ---------------------------------------------------------------- header
        RowLayout {
            spacing: 14
            Rectangle {
                width: 52; height: 52; radius: 14
                color: Theme.surface2; border.color: Theme.borderStrong
                Image {
                    anchors.centerIn: parent; width: 28; height: 28
                    sourceSize: Qt.size(56, 56)
                    source: win.backend.iconUrl
                }
            }
            ColumnLayout {
                spacing: 2
                Label { text: win.info.name; color: Theme.text; font.pixelSize: Theme.fontTitle; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                Dim { text: win.info.file + "  ·  " + win.info.format + (win.info.arch ? " " + win.info.arch : "") + "  ·  " + win.info.size }
            }
        }

        // ---------------------------------------------------------------- compatibility
        Card {
            RowLayout {
                spacing: 8
                Rectangle { width: 10; height: 10; radius: 5; color: win.ratingColor(win.info.rating) }
                Label { text: win.ratingText(win.info.rating); color: Theme.text; font.weight: Font.DemiBold }
                Label { text: win.info.rating.toUpperCase(); color: win.ratingColor(win.info.rating); font.pixelSize: Theme.fontCaption; font.weight: Font.DemiBold }
                Item { Layout.fillWidth: true }
                Dim { visible: !win.info.verified && win.info.rating !== "untested"; text: "community rating, not yet verified on X-OS"; Layout.fillWidth: false }
            }
            Repeater {
                model: win.info.warnings
                Dim { required property string modelData; text: "•  " + modelData }
            }
        }
        Card {
            visible: win.info.alternative !== ""
            border.color: Theme.accentGlow
            Label_ { text: "Recommended instead"; font.weight: Font.DemiBold; color: Theme.accent }
            Dim { text: win.info.alternative }
        }

        // ---------------------------------------------------------------- state-specific
        Card {
            visible: !win.info.canInstall
            border.color: Theme.danger
            Label_ { text: "X-OS will not run this file."; font.weight: Font.DemiBold }
            Dim { text: "The reasons are listed above. Nothing was executed." }
        }
        Card {
            visible: win.info.canInstall && (win.backend.state === "ready" || win.backend.state === "failed")
            Label_ {
                visible: !win.backend.wineReady && win.info.canInstall
                text: "Windows support (Wine) is not installed yet. X-OS will install it from Debian's signed repositories first (internet and administrator password needed)."
            }
            Label_ {
                visible: win.backend.state === "failed"
                text: "Installation did not finish: " + win.backend.error
                color: Theme.danger
            }
            CheckBox {
                id: trust
                text: "I trust where this file came from"
                indicator: Rectangle {
                    x: 0; y: (trust.height - height) / 2
                    width: 18; height: 18; radius: 5
                    color: trust.checked ? Theme.accentDeep : "transparent"
                    border.color: trust.checked || trust.activeFocus ? Theme.accent : Theme.borderStrong
                    Label { anchors.centerIn: parent; text: "✓"; visible: trust.checked; color: Theme.accent; font.pixelSize: 13 }
                }
                contentItem: Label { text: trust.text; color: Theme.text; leftPadding: 28; verticalAlignment: Text.AlignVCenter }
            }
            Dim {
                text: "It will run in its own private Windows environment (" + win.info.prefix + "). Windows programs can still read your personal files. SHA-256 " + win.info.sha + "…"
            }
        }
        Card {
            visible: win.backend.state === "setup" || win.backend.state === "working"
            RowLayout {
                spacing: 10
                BusyIndicator { running: parent.visible; implicitWidth: 22; implicitHeight: 22 }
                Label_ { text: win.backend.step }
            }
        }
        Card {
            visible: win.backend.state === "done"
            Label_ { text: "Installed"; font.weight: Font.DemiBold; color: Theme.success }
            Dim { text: win.backend.launchers.length ? "It is in your applications menu. Open it now:" : "The installer finished. Look for the app in your applications menu." }
            Repeater {
                model: win.backend.launchers
                Btn { required property var modelData; text: "Open " + modelData.name; primary: true; onClicked: win.backend.openLauncher(modelData.file) }
            }
        }

        // ---------------------------------------------------------------- details log
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.backend.log !== ""
            radius: Theme.radiusSm
            color: Theme.bg
            border.color: Theme.border
            ScrollView {
                anchors.fill: parent; anchors.margins: 8
                TextArea {
                    readOnly: true
                    text: win.backend.log
                    color: Theme.textDim
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontCaption
                    wrapMode: TextArea.Wrap
                    background: null
                    onTextChanged: cursorPosition = length
                }
            }
        }
        Item { Layout.fillHeight: true; visible: win.backend.log === "" }

        // ---------------------------------------------------------------- buttons
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Btn {
                text: win.backend.state === "done" ? "Close" : "Cancel"
                enabled: win.backend.state !== "setup" && win.backend.state !== "working"
                onClicked: win.backend.quit()
            }
            Btn {
                visible: win.info.canInstall && (win.backend.state === "ready" || win.backend.state === "failed")
                primary: true
                enabled: win.info.canInstall && trust.checked
                text: !win.info.canInstall ? "Can't install"
                    : win.backend.wineReady ? (win.backend.state === "failed" ? "Try again" : "Install")
                    : "Set up & install"
                onClicked: win.backend.install()
            }
        }
    }
}
