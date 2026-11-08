// X-OS login screen (SDDM greeter theme, Qt 6).
// Uses only SDDM's documented API: sddm.login/powerOff/reboot/suspend, userModel, sessionModel.
import QtQuick
import QtQuick.Controls.Basic

Rectangle {
    id: root
    width: 1280
    height: 800
    color: "#141517"

    // ------------------------------------------------------------------ tokens (XOS.Theme dark)
    readonly property color cText: "#EDEEF0"
    readonly property color cDim: "#A0A4AC"
    readonly property color cFaint: "#6A6E77"
    readonly property color cAccent: "#7A8CFF"
    readonly property color cAccentDeep: "#2E3566"
    readonly property color cDanger: "#E5636B"
    readonly property color cGlass: Qt.rgba(0.094, 0.106, 0.122, 0.72)
    readonly property color cRim: Qt.rgba(1, 1, 1, 0.16)
    readonly property string ui: "Inter"

    property int userIndex: userModel.lastIndex >= 0 ? userModel.lastIndex : 0
    property int sessionIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
    property string error: ""
    property bool busy: false

    function userData(i, role) {
        return userModel.data(userModel.index(i, 0), role)
    }
    readonly property string userName: userModel.count > 0 ? userData(userIndex, Qt.UserRole + 1) || "" : ""
    readonly property string realName: userModel.count > 0 ? (userData(userIndex, Qt.UserRole + 2) || userName) : ""
    readonly property string userIcon: userModel.count > 0 ? (userData(userIndex, Qt.UserRole + 4) || "") : ""

    function login() {
        if (busy || userName === "") return
        busy = true
        error = ""
        sddm.login(userName, password.text, sessionIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.busy = false
            root.error = "Wrong password. Try again."
            password.text = ""
            shake.restart()
            password.forceActiveFocus()
        }
        function onLoginSucceeded() { root.busy = false }
    }

    // ------------------------------------------------------------------ background
    Image {
        anchors.fill: parent
        source: config.background || "/usr/share/wallpapers/X-OS/x-os-dark.svg"
        fillMode: Image.PreserveAspectCrop
        sourceSize: Qt.size(width, height)
        asynchronous: true
    }
    Rectangle { anchors.fill: parent; color: Qt.rgba(0, 0, 0, 0.35) }

    // ------------------------------------------------------------------ clock
    Column {
        id: clockCol
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.13
        spacing: 2
        Text {
            id: time
            anchors.horizontalCenter: parent.horizontalCenter
            color: root.cText
            font.family: root.ui
            font.pixelSize: Math.round(root.height * 0.11)
            font.weight: Font.Light
            text: Qt.formatTime(new Date(), Qt.locale().timeFormat(Locale.ShortFormat).replace(/:ss/, "").replace(/ ?[aA][pP]?/, ""))
        }
        Text {
            id: date
            anchors.horizontalCenter: parent.horizontalCenter
            color: root.cDim
            font.family: root.ui
            font.pixelSize: Math.round(root.height * 0.024)
            text: Qt.formatDate(new Date(), "dddd, d MMMM")
        }
        Timer {
            interval: 1000; running: true; repeat: true
            onTriggered: {
                time.text = Qt.formatTime(new Date(), Qt.locale().timeFormat(Locale.ShortFormat).replace(/:ss/, "").replace(/ ?[aA][pP]?/, ""))
                date.text = Qt.formatDate(new Date(), "dddd, d MMMM")
            }
        }
    }

    // ------------------------------------------------------------------ login card
    Column {
        id: card
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.52
        spacing: 14
        transform: Translate { id: shakeX; x: 0 }

        Rectangle {        // avatar
            anchors.horizontalCenter: parent.horizontalCenter
            width: 96; height: 96; radius: 48
            color: root.cAccentDeep
            border.color: Qt.rgba(0.478, 0.549, 1.0, 0.45)
            border.width: 1
            clip: true
            Image {
                id: face
                anchors.fill: parent
                anchors.margins: 1
                source: root.userIcon ? "file://" + root.userIcon : ""
                fillMode: Image.PreserveAspectCrop
                visible: status === Image.Ready
                sourceSize: Qt.size(192, 192)
            }
            Text {
                anchors.centerIn: parent
                visible: !face.visible
                text: root.realName ? root.realName.charAt(0).toUpperCase() : "?"
                color: root.cText
                font.family: root.ui
                font.pixelSize: 40
                font.weight: Font.DemiBold
            }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.realName
            color: root.cText
            font.family: root.ui
            font.pixelSize: 22
            font.weight: Font.DemiBold
        }

        Rectangle {        // password pill
            id: pill
            anchors.horizontalCenter: parent.horizontalCenter
            width: 320; height: 46; radius: 23
            color: root.cGlass
            border.width: password.activeFocus ? 2 : 1
            border.color: root.error !== "" ? root.cDanger : password.activeFocus ? root.cAccent : root.cRim
            TextField {
                id: password
                anchors.left: parent.left
                anchors.right: go.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 18
                anchors.rightMargin: 6
                echoMode: TextInput.Password
                passwordCharacter: "●"
                placeholderText: "Password"
                placeholderTextColor: root.cFaint
                color: root.cText
                font.family: root.ui
                font.pixelSize: 15
                background: null
                focus: true
                enabled: !root.busy
                Keys.onReturnPressed: root.login()
                Keys.onEnterPressed: root.login()
                Accessible.name: "Password for " + root.realName
            }
            Rectangle {
                id: go
                anchors.right: parent.right
                anchors.rightMargin: 5
                anchors.verticalCenter: parent.verticalCenter
                width: 36; height: 36; radius: 18
                color: goMouse.containsMouse ? root.cAccent : root.cAccentDeep
                border.color: root.cAccent
                Text {
                    anchors.centerIn: parent
                    text: root.busy ? "…" : "→"
                    color: goMouse.containsMouse ? "#141517" : root.cText
                    font.pixelSize: 18
                    font.family: root.ui
                }
                MouseArea { id: goMouse; anchors.fill: parent; hoverEnabled: true; onClicked: root.login() }
                Accessible.role: Accessible.Button
                Accessible.name: "Log in"
            }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.error !== "" ? root.error
                : keyboard && keyboard.capsLock ? "Caps Lock is on" : " "
            color: root.error !== "" ? root.cDanger : root.cDim
            font.family: root.ui
            font.pixelSize: 13
        }
    }
    SequentialAnimation {
        id: shake
        NumberAnimation { target: shakeX; property: "x"; to: -10; duration: 50 }
        NumberAnimation { target: shakeX; property: "x"; to: 10; duration: 70 }
        NumberAnimation { target: shakeX; property: "x"; to: -6; duration: 60 }
        NumberAnimation { target: shakeX; property: "x"; to: 0; duration: 60 }
    }

    // ------------------------------------------------------------------ other users
    Row {
        visible: userModel.count > 1
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: bottomBar.top
        anchors.bottomMargin: 24
        spacing: 10
        Repeater {
            model: userModel
            delegate: Rectangle {
                required property int index
                required property string realName
                required property string name
                visible: index !== root.userIndex
                height: 34; radius: 17
                width: label.implicitWidth + 28
                color: chipMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : root.cGlass
                border.color: root.cRim
                Text { id: label; anchors.centerIn: parent; text: realName || name; color: root.cText; font.family: root.ui; font.pixelSize: 13 }
                MouseArea {
                    id: chipMouse; anchors.fill: parent; hoverEnabled: true
                    onClicked: { root.userIndex = index; root.error = ""; password.text = ""; password.forceActiveFocus() }
                }
            }
        }
    }

    // ------------------------------------------------------------------ bottom bar
    Item {
        id: bottomBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 64

        Row {       // session
            anchors.left: parent.left
            anchors.leftMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Text { text: "Session"; color: root.cFaint; font.family: root.ui; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
            Rectangle {
                height: 32; radius: 16; width: sessLabel.implicitWidth + 28
                color: sessMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : root.cGlass
                border.color: root.cRim
                Text {
                    id: sessLabel; anchors.centerIn: parent; color: root.cText; font.family: root.ui; font.pixelSize: 13
                    // The X-OS desktop runs as the Plasma Wayland session; name it as users know it.
                    text: (sessionModel.data(sessionModel.index(root.sessionIndex, 0), Qt.UserRole + 4) || "Plasma")
                        .replace(/^Plasma \(Wayland\)$/, "X-OS").replace(/^Plasma \(X11\)$/, "X-OS (X11)")
                }
                MouseArea {
                    id: sessMouse; anchors.fill: parent; hoverEnabled: true
                    onClicked: root.sessionIndex = (root.sessionIndex + 1) % Math.max(1, sessionModel.rowCount())
                }
                Accessible.role: Accessible.Button
                Accessible.name: "Session: " + sessLabel.text
            }
        }

        Row {       // power
            anchors.right: parent.right
            anchors.rightMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10
            Repeater {
                model: [
                    { label: "Sleep", icon: "icons/sleep.svg", can: sddm.canSuspend, act: function () { sddm.suspend() } },
                    { label: "Restart", icon: "icons/restart.svg", can: sddm.canReboot, act: function () { sddm.reboot() } },
                    { label: "Shut Down", icon: "icons/power.svg", can: sddm.canPowerOff, act: function () { sddm.powerOff() } }
                ]
                delegate: Rectangle {
                    required property var modelData
                    visible: modelData.can
                    width: 40; height: 40; radius: 20
                    color: pMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.14) : root.cGlass
                    border.color: root.cRim
                    Image { anchors.centerIn: parent; source: modelData.icon; width: 18; height: 18; sourceSize: Qt.size(36, 36) }
                    MouseArea { id: pMouse; anchors.fill: parent; hoverEnabled: true; onClicked: modelData.act() }
                    ToolTip.visible: pMouse.containsMouse
                    ToolTip.text: modelData.label
                    Accessible.role: Accessible.Button
                    Accessible.name: modelData.label
                }
            }
        }
    }

    Component.onCompleted: password.forceActiveFocus()
}
