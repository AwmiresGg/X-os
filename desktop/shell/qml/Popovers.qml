// Content of every menu-bar popover. Each control is wired to a real action on the
// status/windows/settings objects provided by the shell process.
import QtQuick
import XOS.Theme
import "components"

Item {
    id: root
    required property string name
    required property var status
    required property var windows
    required property var settings
    property var dockItem: null            // for the dock context menu
    signal close()

    readonly property var st: status ? status.data : ({})
    readonly property var cfg: settings ? settings.values : ({})
    implicitWidth: loader.item ? loader.item.implicitWidth : 0
    implicitHeight: loader.item ? loader.item.implicitHeight : 0

    Loader {
        id: loader
        sourceComponent: ({
            system: systemMenu, window: windowMenu, battery: batteryMenu, network: networkMenu,
            bluetooth: bluetoothMenu, sound: soundMenu, control: controlCenter, calendar: calendar,
            dock: dockMenu
        })[root.name] || null
    }

    component Title: Text {
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontEmphasis
        font.weight: Font.DemiBold
    }
    component Caption: Text {
        color: Theme.textDim
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontCaption + 1
    }
    component Column_: Column { width: parent ? parent.width : 0; spacing: 2 }

    // ---------------------------------------------------------------- X-OS menu
    Component {
        id: systemMenu
        Panel {
            implicitWidth: 230
            implicitHeight: (confirm === "" ? menuCol.height : confirmCol.height) + 2 * padding
            property string confirm: ""
            Column_ {
                id: menuCol
                visible: confirm === ""
                MenuRow { text: "About X-OS"; onTriggered: { root.windows.openUrl("systemsettings:kcm_about-distro"); root.close() } }
                MenuRow { text: "System Settings…"; onTriggered: { root.windows.openUrl("systemsettings"); root.close() } }
                MenuRow { separator: true }
                MenuRow { text: "Force Quit…"; detail: "click a window"; onTriggered: { root.windows.forceQuit(); root.close() } }
                MenuRow { separator: true }
                MenuRow { text: "Sleep"; onTriggered: { root.status.power("sleep"); root.close() } }
                MenuRow { text: "Restart…"; onTriggered: confirm = "restart" }
                MenuRow { text: "Shut Down…"; onTriggered: confirm = "shutdown" }
                MenuRow { separator: true }
                MenuRow { text: "Lock Screen"; onTriggered: { root.status.power("lock"); root.close() } }
                MenuRow { text: "Log Out…"; onTriggered: { root.status.power("logout"); root.close() } }
            }
            Column {
                id: confirmCol
                visible: confirm !== ""
                width: 218
                spacing: 10
                Title { text: confirm === "restart" ? "Restart now?" : "Shut down now?"; x: 8; topPadding: 6 }
                Caption {
                    x: 8; width: 202; wrapMode: Text.Wrap
                    text: "Unsaved work in open apps may be lost."
                }
                Row {
                    x: 8; spacing: 8; bottomPadding: 6
                    Rectangle {
                        width: 97; height: 30; radius: Theme.radiusXs; color: Theme.surface2
                        Text { anchors.centerIn: parent; text: "Cancel"; color: Theme.text; font.pixelSize: Theme.fontBody }
                        MouseArea { anchors.fill: parent; onClicked: confirm = "" }
                    }
                    Rectangle {
                        width: 97; height: 30; radius: Theme.radiusXs; color: Theme.accentDeep
                        border.color: Theme.accent
                        Text { anchors.centerIn: parent; text: confirm === "restart" ? "Restart" : "Shut Down"; color: Theme.onAccent; font.pixelSize: Theme.fontBody; font.weight: Font.DemiBold }
                        MouseArea { anchors.fill: parent; onClicked: { root.status.power(confirm); root.close() } }
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------- dock context menu
    Component {
        id: dockMenu
        Panel {
            implicitWidth: 240
            readonly property var it: root.dockItem || { windows: [], name: "", appId: "", pinned: false, running: false }
            Column_ {
                Text {
                    text: it.name; x: 10; height: 26; verticalAlignment: Text.AlignVCenter
                    color: Theme.textDim; font.pixelSize: Theme.fontCaption + 1; font.weight: Font.DemiBold
                }
                Repeater {
                    model: it.windows
                    MenuRow {
                        required property var modelData
                        glyph: modelData.minimized ? "window-minimize" : "window-restore"
                        text: modelData.caption
                        onTriggered: { root.windows.windowAction(modelData.id, "activate"); root.close() }
                    }
                }
                MenuRow { separator: true; visible: it.windows.length > 0 }
                MenuRow { text: "New Window"; onTriggered: { root.windows.launch(it.appId); root.close() } }
                MenuRow { text: it.pinned ? "Remove from Dock" : "Keep in Dock"; onTriggered: { root.windows.togglePin(it.appId); root.close() } }
                MenuRow {
                    visible: it.running
                    text: it.windows.length > 1 ? "Quit (close " + it.windows.length + " windows)" : "Quit"
                    destructive: true
                    onTriggered: { for (const w of it.windows) root.windows.windowAction(w.id, "close"); root.close() }
                }
            }
        }
    }

    // ---------------------------------------------------------------- Window menu (active window)
    Component {
        id: windowMenu
        Panel {
            implicitWidth: 210
            readonly property string wid: root.windows.active.id
            Column_ {
                MenuRow { glyph: "window-minimize"; text: "Minimize"; onTriggered: { root.windows.windowAction(wid, "minimize"); root.close() } }
                MenuRow { glyph: "window-maximize"; text: "Zoom"; onTriggered: { root.windows.windowAction(wid, "toggle-maximize"); root.close() } }
                MenuRow { separator: true }
                MenuRow { glyph: "window-close"; text: "Close Window"; onTriggered: { root.windows.windowAction(wid, "close"); root.close() } }
            }
        }
    }

    // ---------------------------------------------------------------- battery
    Component {
        id: batteryMenu
        Panel {
            implicitWidth: 230
            readonly property var b: root.st.battery || {}
            Column_ {
                Item {
                    width: parent.width; height: 44
                    Title { text: "Battery"; x: 8; y: 6 }
                    Caption { text: (b.percent || 0) + "%" + (b.charging ? " · charging" : ""); anchors.right: parent.right; anchors.rightMargin: 8; y: 9 }
                    Caption { text: "Power source: " + (b.source || "AC"); x: 8; y: 26 }
                }
                MenuRow { separator: true }
                MenuRow { text: "Battery Settings…"; onTriggered: { root.windows.openUrl("systemsettings:kcm_powerdevilprofilesconfig"); root.close() } }
            }
        }
    }

    // ---------------------------------------------------------------- network
    Component {
        id: networkMenu
        Panel {
            implicitWidth: 250
            readonly property var n: root.st.network || {}
            Column_ {
                Item {
                    width: parent.width; height: 36
                    Title { text: "Wi-Fi"; x: 8; anchors.verticalCenter: parent.verticalCenter }
                    Toggle {
                        label: "Wi-Fi"
                        checked: !!n.wifi_enabled
                        anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                        onToggled: (v) => root.status.setWifi(v)
                    }
                }
                MenuRow {
                    glyph: n.icon || "network-off"
                    text: n.state === "connected" ? n.name : "Not connected"
                    detail: n.state === "connected" ? (n.kind === "wifi" ? n.signal + "%" : "Ethernet") : ""
                    enabled: false
                }
                MenuRow { visible: !!n.vpn; glyph: "vpn"; text: "VPN connected"; enabled: false }
                MenuRow { separator: true }
                MenuRow { text: "Network Settings…"; onTriggered: { root.windows.openUrl("systemsettings:kcm_networkmanagement"); root.close() } }
            }
        }
    }

    // ---------------------------------------------------------------- bluetooth
    Component {
        id: bluetoothMenu
        Panel {
            implicitWidth: 240
            readonly property var bt: root.st.bluetooth || {}
            Column_ {
                Item {
                    width: parent.width; height: 36
                    Title { text: "Bluetooth"; x: 8; anchors.verticalCenter: parent.verticalCenter }
                    Toggle {
                        label: "Bluetooth"
                        checked: !!bt.powered
                        anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                        onToggled: (v) => root.status.setBluetooth(v)
                    }
                }
                MenuRow { separator: true }
                MenuRow { text: "Bluetooth Settings…"; onTriggered: { root.windows.openUrl("systemsettings:kcm_bluetooth"); root.close() } }
            }
        }
    }

    // ---------------------------------------------------------------- sound
    Component {
        id: soundMenu
        Panel {
            implicitWidth: 250
            readonly property var a: root.st.audio || {}
            Column_ {
                spacing: 6
                Item {
                    width: parent.width; height: 30
                    Title { text: "Sound"; x: 8; anchors.verticalCenter: parent.verticalCenter }
                    Caption { text: (a.muted ? "Muted" : (a.volume || 0) + "%"); anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter }
                }
                XSlider {
                    x: 8; width: parent.width - 16
                    glyph: a.icon || "volume-medium"
                    label: "Volume"
                    value: (a.volume || 0) / 100
                    onMoved: (v) => root.status.setVolume(Math.round(v * 100))
                }
                MenuRow { text: a.muted ? "Unmute" : "Mute"; onTriggered: root.status.setMuted(!a.muted) }
                MenuRow { separator: true }
                MenuRow { text: "Sound Settings…"; onTriggered: { root.windows.openUrl("systemsettings:kcm_pulseaudio"); root.close() } }
            }
        }
    }

    // ---------------------------------------------------------------- Control Center
    Component {
        id: controlCenter
        Panel {
            implicitWidth: 300
            padding: 10
            readonly property var n: root.st.network || {}
            readonly property var bt: root.st.bluetooth || {}
            readonly property var a: root.st.audio || {}
            readonly property var br: root.st.brightness || {}
            Column {
                width: 280
                spacing: 10
                Grid {
                    columns: 2; spacing: 8
                    Repeater {
                        model: [
                            { key: "wifi", glyph: n.wifi_enabled ? (n.icon || "wifi-3") : "wifi-off", label: "Wi-Fi",
                              sub: n.state === "connected" ? n.name : (n.wifi_enabled ? "On" : "Off"), on: !!n.wifi_enabled, show: true },
                            { key: "bt", glyph: bt.powered ? "bluetooth" : "bluetooth-off", label: "Bluetooth",
                              sub: bt.powered ? "On" : "Off", on: !!bt.powered, show: !!bt.present },
                            { key: "dark", glyph: "night-light", label: "Dark Mode",
                              sub: Theme.dark ? "On" : "Off", on: Theme.dark, show: true },
                            { key: "motion", glyph: "eye", label: "Reduce Motion",
                              sub: root.cfg.reducedMotion ? "On" : "Off", on: !!root.cfg.reducedMotion, show: true }
                        ]
                        delegate: Rectangle {
                            required property var modelData
                            visible: modelData.show
                            width: 136; height: 52; radius: Theme.radiusSm
                            color: modelData.on ? Theme.accentDeep : Theme.surface2
                            border.width: 1
                            border.color: modelData.on ? Theme.accentGlow : Theme.border
                            Accessible.role: Accessible.CheckBox
                            Accessible.name: modelData.label
                            Accessible.checked: modelData.on
                            Glyph { name: modelData.glyph; size: 18; tint: modelData.on ? Theme.onAccent : Theme.text; x: 10; anchors.verticalCenter: parent.verticalCenter }
                            Column {
                                x: 36; anchors.verticalCenter: parent.verticalCenter
                                Text { text: modelData.label; color: modelData.on ? Theme.onAccent : Theme.text; font.pixelSize: Theme.fontBody; font.weight: Font.DemiBold }
                                Text { text: modelData.sub; color: modelData.on ? Theme.onAccent : Theme.textDim; font.pixelSize: Theme.fontCaption; elide: Text.ElideRight; width: 92 }
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    const k = modelData.key
                                    if (k === "wifi") root.status.setWifi(!modelData.on)
                                    else if (k === "bt") root.status.setBluetooth(!modelData.on)
                                    else if (k === "dark") { root.settings.set("theme", Theme.dark ? "light" : "dark"); root.status.setDark(!Theme.dark) }
                                    else if (k === "motion") root.settings.set("reducedMotion", !root.cfg.reducedMotion)
                                }
                            }
                        }
                    }
                }
                Rectangle {
                    width: parent.width; height: col.implicitHeight + 16; radius: Theme.radiusSm
                    color: Theme.surface2; border.color: Theme.border
                    Column {
                        id: col
                        x: 10; y: 8; width: parent.width - 20; spacing: 6
                        Caption { text: "Display"; visible: !!br.available }
                        XSlider { visible: !!br.available; width: parent.width; glyph: "brightness"; label: "Brightness"
                                  value: (br.percent || 0) / 100; onMoved: (v) => root.status.setBrightness(Math.round(v * 100)) }
                        Caption { text: "Sound"; visible: !!a.available }
                        XSlider { visible: !!a.available; width: parent.width; glyph: a.icon || "volume-medium"; label: "Volume"
                                  value: (a.volume || 0) / 100; onMoved: (v) => root.status.setVolume(Math.round(v * 100)) }
                    }
                }
                Rectangle {
                    width: parent.width; height: col2.implicitHeight + 16; radius: Theme.radiusSm
                    color: Theme.surface2; border.color: Theme.border
                    Column {
                        id: col2
                        x: 10; y: 8; width: parent.width - 20; spacing: 6
                        Caption { text: "Dock transparency"; }
                        XSlider { width: parent.width; label: "Dock transparency"
                                  value: 1 - root.cfg.dockOpacity; onMoved: (v) => root.settings.set("dockOpacity", 1 - v) }
                        Caption { text: "Menu bar transparency" }
                        XSlider { width: parent.width; label: "Menu bar transparency"
                                  value: 1 - root.cfg.menuBarOpacity; onMoved: (v) => root.settings.set("menuBarOpacity", 1 - v) }
                        Caption { text: "Dock icon size" }
                        XSlider { width: parent.width; label: "Dock icon size"
                                  value: (root.cfg.dockIconSize - 32) / 40; onMoved: (v) => root.settings.set("dockIconSize", Math.round(32 + v * 40)) }
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------- calendar
    Component {
        id: calendar
        Panel {
            implicitWidth: 250
            padding: 10
            property date shown: new Date()
            readonly property date today: new Date()
            Column {
                width: 230
                spacing: 6
                Item {
                    width: parent.width; height: 28
                    Title { text: Qt.formatDate(shown, "MMMM yyyy"); anchors.verticalCenter: parent.verticalCenter; x: 4 }
                    Row {
                        anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                        BarButton { glyph: "chevron-left"; height: 26; onClicked: shown = new Date(shown.getFullYear(), shown.getMonth() - 1, 1) }
                        BarButton { glyph: "chevron-right"; height: 26; onClicked: shown = new Date(shown.getFullYear(), shown.getMonth() + 1, 1) }
                    }
                }
                Grid {
                    columns: 7
                    Repeater {
                        model: 7
                        Text {
                            required property int index
                            width: 32; height: 20; horizontalAlignment: Text.AlignHCenter
                            text: Qt.locale().dayName((index + Qt.locale().firstDayOfWeek) % 7, Locale.NarrowFormat)
                            color: Theme.textFaint; font.pixelSize: Theme.fontCaption
                        }
                    }
                    Repeater {
                        model: 42
                        Rectangle {
                            required property int index
                            readonly property date first: new Date(shown.getFullYear(), shown.getMonth(), 1)
                            readonly property int lead: (first.getDay() - Qt.locale().firstDayOfWeek + 7) % 7
                            readonly property date day: new Date(shown.getFullYear(), shown.getMonth(), index - lead + 1)
                            readonly property bool isToday: day.toDateString() === today.toDateString()
                            width: 32; height: 28; radius: 14
                            color: isToday ? Theme.accentDeep : "transparent"
                            border.color: isToday ? Theme.accent : "transparent"
                            Text {
                                anchors.centerIn: parent
                                text: day.getDate()
                                color: isToday ? Theme.onAccent : (day.getMonth() === shown.getMonth() ? Theme.text : Theme.textFaint)
                                font.pixelSize: Theme.fontBody
                            }
                        }
                    }
                }
            }
        }
    }
}
