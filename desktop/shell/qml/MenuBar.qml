// X-OS menu bar: thin, minimal, translucent. Every item reflects real state and opens a
// real menu; nothing here is decorative.
import QtQuick
import XOS.Theme
import "components"

Item {
    id: bar
    required property var status
    required property var windows
    property real opacity_: 0.55          // user setting (Control Center › Menu bar transparency)
    property string openMenu: ""           // name of the popover currently open
    signal requestMenu(string name, real anchorX)

    height: 30
    readonly property var st: status ? status.data : ({})
    readonly property var bat: st.battery || {}
    readonly property var net: st.network || {}
    readonly property var bt: st.bluetooth || {}
    readonly property var aud: st.audio || {}

    function toggle(name, item) {
        bar.requestMenu(openMenu === name ? "" : name, item.mapToItem(bar, item.width / 2, 0).x)
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(Theme.surface1.r, Theme.surface1.g, Theme.surface1.b, bar.opacity_)
        Rectangle {          // hairline under the bar
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Theme.border
        }
    }

    // ---------------------------------------------------------------- left
    Row {
        anchors.left: parent.left
        anchors.leftMargin: 8
        height: parent.height
        spacing: 2
        BarButton {
            id: sysBtn
            glyph: "xos-mark"
            glyphSize: 17
            open: bar.openMenu === "system"
            Accessible.name: "X-OS menu"
            onClicked: bar.toggle("system", sysBtn)
        }
        BarButton {
            text: bar.windows ? bar.windows.active.name : ""
            bold: true
            open: false
            Accessible.name: "Active application: " + text
            onClicked: winBtn.clicked()
        }
        BarButton {
            id: winBtn
            text: "Window"
            visible: !!bar.windows && bar.windows.active.id !== ""
            open: bar.openMenu === "window"
            onClicked: bar.toggle("window", winBtn)
        }
    }

    // ---------------------------------------------------------------- right
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 8
        height: parent.height
        spacing: 0
        BarButton {
            id: batBtn
            visible: !!bar.bat.present
            glyph: bar.bat.icon || "battery-full"
            text: (bar.bat.percent || 0) + "%"
            open: bar.openMenu === "battery"
            Accessible.name: "Battery " + text + (bar.bat.charging ? ", charging" : "")
            onClicked: bar.toggle("battery", batBtn)
        }
        BarButton {
            id: netBtn
            glyph: bar.net.icon || "network-off"
            open: bar.openMenu === "network"
            Accessible.name: bar.net.state === "connected" ? "Network: " + bar.net.name : "Network: not connected"
            onClicked: bar.toggle("network", netBtn)
        }
        BarButton {
            id: btBtn
            visible: !!bar.bt.present
            glyph: bar.bt.powered ? "bluetooth" : "bluetooth-off"
            open: bar.openMenu === "bluetooth"
            Accessible.name: "Bluetooth " + (bar.bt.powered ? "on" : "off")
            onClicked: bar.toggle("bluetooth", btBtn)
        }
        BarButton {
            id: volBtn
            visible: !!bar.aud.available
            glyph: bar.aud.icon || "volume-mute"
            open: bar.openMenu === "sound"
            Accessible.name: "Volume " + (bar.aud.volume || 0) + "%"
            onClicked: bar.toggle("sound", volBtn)
        }
        BarButton {
            glyph: "search"
            Accessible.name: "Search"
            onClicked: bar.windows.search()
        }
        BarButton {
            id: ccBtn
            glyph: "control-center"
            open: bar.openMenu === "control"
            Accessible.name: "Control Center"
            onClicked: bar.toggle("control", ccBtn)
        }
        BarButton {
            id: clockBtn
            open: bar.openMenu === "calendar"
            text: clock.dateText + "   " + clock.timeText
            onClicked: bar.toggle("calendar", clockBtn)
        }
    }

    QtObject {
        id: clock
        property date now: new Date()
        readonly property string dateText: Qt.formatDate(now, "ddd d MMM")
        // Locale order and 12/24 h, but never seconds in the bar.
        readonly property string timeText: Qt.formatTime(now, Qt.locale().timeFormat(Locale.ShortFormat).replace(/:ss/, ""))
    }
    Timer {
        // Fire on the minute boundary, then every minute: no needless wake-ups.
        interval: 60000 - (new Date().getSeconds() * 1000)
        running: true
        repeat: true
        onTriggered: { clock.now = new Date(); interval = 60000 }
    }
}
