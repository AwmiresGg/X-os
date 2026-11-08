// X-OS Settings - Tweaks, Updates, Security, This PC, About.
import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import XOS.Theme

Window {
    id: win
    required property var backend
    property string themeMode: "dark"
    width: 1040
    height: 680
    minimumWidth: 860
    minimumHeight: 560
    visible: true
    title: "X-OS Settings"
    color: Theme.bg
    Component.onCompleted: Theme.mode = themeMode

    readonly property var pages: [
        { id: "tweaks", title: "Tweaks", glyph: "system-monitor" },
        { id: "updates", title: "Updates", glyph: "updates" },
        { id: "security", title: "Security", glyph: "security" },
        { id: "this-pc", title: "This PC", glyph: "this-pc" },
        { id: "about", title: "About", glyph: "xos-mark" }
    ]

    function gl(name, color) { return "image://glyph/" + name + "?color=" + color }

    // ------------------------------------------------------------------ building blocks
    component Card: Rectangle {
        default property alias content: inner.data
        property int pad: 20
        Layout.fillWidth: true
        implicitHeight: inner.implicitHeight + pad * 2
        radius: 16
        color: Theme.surface1
        border.color: Theme.border
        ColumnLayout { id: inner; anchors.fill: parent; anchors.margins: parent.pad; spacing: 12 }
    }
    component Label2: Text {
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: 14
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    component Dim: Label2 { color: Theme.textDim; font.pixelSize: 13 }
    component Pill: Rectangle {
        id: pill
        property string text: ""
        property bool primary: false
        signal clicked()
        implicitWidth: Math.max(96, t.implicitWidth + 36)
        implicitHeight: 34
        radius: 17
        opacity: enabled ? 1 : 0.45
        color: primary ? (ma.pressed ? Qt.darker(Theme.accent, 1.2) : ma.containsMouse ? Qt.lighter(Theme.accent, 1.08) : Theme.accent)
                       : (ma.pressed ? Theme.surface0 : ma.containsMouse ? Theme.surface2 : "transparent")
        border.color: primary ? "transparent" : Theme.borderStrong
        Behavior on color { ColorAnimation { duration: 120 } }
        Text { id: t; anchors.centerIn: parent; text: pill.text; color: pill.primary ? "#FFFFFF" : Theme.text
               font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold }
        MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; enabled: pill.enabled
                    cursorShape: Qt.PointingHandCursor; onClicked: pill.clicked() }
        activeFocusOnTab: true
        Keys.onReturnPressed: clicked()
        Keys.onSpacePressed: clicked()
        Accessible.role: Accessible.Button
        Accessible.name: text
    }
    component Toggle: Rectangle {
        id: tg
        property bool on: false
        signal toggled(bool v)
        implicitWidth: 44; implicitHeight: 26; radius: 13
        color: on ? Theme.accent : Theme.surface2
        border.color: on ? "transparent" : Theme.borderStrong
        opacity: enabled ? 1 : 0.45
        Behavior on color { ColorAnimation { duration: 160 } }
        Rectangle { width: 20; height: 20; radius: 10; y: 3; x: tg.on ? tg.width - 23 : 3; color: "#FFFFFF"
                    Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } } }
        MouseArea { anchors.fill: parent; enabled: tg.enabled; cursorShape: Qt.PointingHandCursor; onClicked: tg.toggled(!tg.on) }
        Accessible.role: Accessible.CheckBox
        Accessible.checked: on
    }
    component Row2: RowLayout {          // a settings row: symbol, text, control on the right
        property string glyph: ""
        property string heading: ""
        property string detail: ""
        default property alias control: holder.data
        Layout.fillWidth: true
        spacing: 14
        Rectangle { visible: glyph !== ""; width: 34; height: 34; radius: 10; color: Theme.surface2
            Image { anchors.centerIn: parent; width: 18; height: 18; sourceSize: Qt.size(36, 36); source: win.gl(glyph, Theme.text) } }
        ColumnLayout { Layout.fillWidth: true; spacing: 2
            Label2 { text: heading; font.weight: Font.DemiBold }
            Dim { text: detail; visible: detail !== "" } }
        Item { id: holder; implicitWidth: childrenRect.width; implicitHeight: childrenRect.height }
    }
    component Hero: RowLayout {          // big status at the top of a page
        property string glyph: ""
        property color tint: Theme.accent
        property string heading: ""
        property string detail: ""
        Layout.fillWidth: true
        spacing: 16
        Rectangle { width: 56; height: 56; radius: 28; color: Qt.rgba(tint.r, tint.g, tint.b, 0.16)
            Image { anchors.centerIn: parent; width: 28; height: 28; sourceSize: Qt.size(56, 56); source: win.gl(glyph, tint) } }
        ColumnLayout { Layout.fillWidth: true; spacing: 3
            Label2 { text: heading; font.pixelSize: 19; font.weight: Font.DemiBold }
            Dim { text: detail; visible: detail !== "" } }
    }

    // ------------------------------------------------------------------ layout
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // sidebar
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 232
            color: Theme.surface0
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border }
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                anchors.topMargin: 22
                spacing: 4
                RowLayout {
                    Layout.leftMargin: 8; Layout.bottomMargin: 16; spacing: 10
                    Image { width: 28; height: 28; Layout.preferredWidth: 28; Layout.preferredHeight: 28; sourceSize: Qt.size(56, 56)
                            source: backend.logo }
                    Label2 { text: "Settings"; font.pixelSize: 17; font.weight: Font.DemiBold; Layout.fillWidth: false }
                }
                Repeater {
                    model: win.pages
                    delegate: Rectangle {
                        required property var modelData
                        readonly property bool sel: backend.page === modelData.id
                        Layout.fillWidth: true
                        height: 36; radius: 10
                        color: sel ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18)
                                   : (m.containsMouse ? Theme.surface2 : "transparent")
                        Behavior on color { ColorAnimation { duration: 120 } }
                        RowLayout { anchors.fill: parent; anchors.leftMargin: 10; spacing: 11
                            Image { width: 17; height: 17; Layout.preferredWidth: 17; Layout.preferredHeight: 17; sourceSize: Qt.size(34, 34)
                                    source: win.gl(modelData.glyph, sel ? Theme.accent : Theme.textDim) }
                            Label2 { text: modelData.title; font.weight: sel ? Font.DemiBold : Font.Normal
                                     color: sel ? Theme.text : Theme.textDim } }
                        MouseArea { id: m; anchors.fill: parent; hoverEnabled: true; onClicked: backend.page = modelData.id }
                        Accessible.role: Accessible.PageTab
                        Accessible.name: modelData.title
                    }
                }
                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth: true; height: 36; radius: 10
                    color: mm.containsMouse ? Theme.surface2 : "transparent"
                    RowLayout { anchors.fill: parent; anchors.leftMargin: 10; spacing: 11
                        Image { width: 17; height: 17; Layout.preferredWidth: 17; Layout.preferredHeight: 17; sourceSize: Qt.size(34, 34); source: win.gl("settings", Theme.textDim) }
                        Label2 { text: "More settings"; color: Theme.textDim } }
                    MouseArea { id: mm; anchors.fill: parent; hoverEnabled: true; onClicked: backend.moreSettings() }
                }
            }
        }

        // content
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Flickable {
                id: flick
                anchors.fill: parent
                contentHeight: pageCol.implicitHeight + 64
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { }
                ColumnLayout {
                    id: pageCol
                    x: 36; y: 30
                    width: Math.min(760, flick.width - 72)
                    spacing: 16
                    Label2 { text: (win.pages.find(p => p.id === backend.page) || {}).title || ""
                             font.pixelSize: 26; font.weight: Font.Bold }
                    Loader {
                        Layout.fillWidth: true
                        sourceComponent: ({ "tweaks": tweaksPage, "updates": updatesPage, "security": securityPage,
                                            "this-pc": pcPage, "about": aboutPage })[backend.page]
                    }
                }
            }
            // working... bar
            Rectangle {
                visible: backend.busy !== ""
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                anchors.margins: 16
                height: 44; radius: 14
                color: Theme.surface2; border.color: Theme.border
                RowLayout { anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 8; spacing: 12
                    BusyIndicator { running: parent.visible; implicitWidth: 22; implicitHeight: 22 }
                    Label2 { text: backend.busy + "…" }
                    Pill { text: "Stop"; onClicked: backend.cancel() } }
            }
            // toast
            Rectangle {
                id: toast
                property string msg: ""
                opacity: msg === "" ? 0 : 1
                Behavior on opacity { NumberAnimation { duration: 200 } }
                anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 72
                width: Math.min(parent.width - 60, tt.implicitWidth + 40); height: 40; radius: 20
                color: Theme.surface2; border.color: Theme.borderStrong
                Text { id: tt; anchors.centerIn: parent; text: toast.msg; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13 }
                Timer { id: toastTimer; interval: 4200; onTriggered: toast.msg = "" }
                Connections { target: backend; function onToast(m) { toast.msg = m; toastTimer.restart() } }
            }
        }
    }

    // ------------------------------------------------------------------ Tweaks
    Component {
        id: tweaksPage
        ColumnLayout {
            spacing: 16
            Dim { text: "Set up the whole computer for what you are doing: power, performance and effects change together. Switch back to Balanced at any time." }
            GridLayout {
                Layout.fillWidth: true
                columns: 2; columnSpacing: 12; rowSpacing: 12
                Repeater {
                    model: backend.modes
                    delegate: Rectangle {
                        required property var modelData
                        readonly property bool sel: backend.mode === modelData.id
                        Layout.fillWidth: true
                        Layout.preferredHeight: 96
                        radius: 16
                        color: ma2.containsMouse && !sel ? Theme.surface2 : Theme.surface1
                        border.width: sel ? 2 : 1
                        border.color: sel ? Theme.accent : Theme.border
                        Behavior on color { ColorAnimation { duration: 120 } }
                        RowLayout { anchors.fill: parent; anchors.margins: 16; spacing: 14
                            Rectangle { width: 44; height: 44; radius: 13
                                color: sel ? Theme.accent : Theme.surface2
                                Image { anchors.centerIn: parent; width: 22; height: 22; sourceSize: Qt.size(44, 44)
                                        source: win.gl(modelData.glyph, sel ? "#FFFFFF" : Theme.text) } }
                            ColumnLayout { Layout.fillWidth: true; spacing: 3
                                Label2 { text: modelData.title; font.weight: Font.DemiBold; font.pixelSize: 15 }
                                Dim { text: modelData.subtitle; font.pixelSize: 12; maximumLineCount: 2; elide: Text.ElideRight } }
                        }
                        MouseArea { id: ma2; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                    enabled: backend.busy === ""; onClicked: if (!sel) backend.applyMode(modelData.id) }
                        Accessible.role: Accessible.RadioButton
                        Accessible.name: modelData.title + ". " + modelData.subtitle
                        Accessible.checked: sel
                    }
                }
            }
            Card {
                id: modeCard
                property var m: backend.modes.find(x => x.id === backend.mode) || backend.modes[0]
                Label2 { text: "What " + modeCard.m.title + " changes"; font.weight: Font.DemiBold }
                Dim { text: "Power profile: " + modeCard.m.power + "   ·   Effects: " + modeCard.m.effects }
                Dim { text: "Kernel: " + modeCard.m.sysctl.join(",  "); font.pixelSize: 12 }
                Repeater { model: modeCard.m.notes; delegate: Dim { required property string modelData; text: modelData; font.pixelSize: 12 } }
                Dim { text: "Firewall, updates and security protections are never changed by a mode."; font.pixelSize: 12; color: Theme.textFaint }
            }
        }
    }

    // ------------------------------------------------------------------ Updates
    Component {
        id: updatesPage
        ColumnLayout {
            spacing: 16
            readonly property var u: backend.upd
            Card {
                Hero {
                    glyph: "updates"
                    tint: u.updates.length > 0 ? Theme.accent : Theme.success
                    heading: !u.checked ? "Check for updates" : u.summary
                    detail: !u.checked ? "System packages from Debian and apps from Flathub."
                          : (u.errors.length ? u.errors.join(" ") : "Last checked at " + u.when)
                }
                RowLayout { spacing: 10
                    Pill { text: "Check now"; enabled: backend.busy === ""; onClicked: backend.checkUpdates() }
                    Pill { text: "Install all"; primary: true; visible: u.updates.length > 0
                           enabled: backend.busy === ""; onClicked: backend.installUpdates() } }
            }
            Card {
                visible: u.updates.length > 0
                Label2 { text: u.updates.length + " update" + (u.updates.length === 1 ? "" : "s"); font.weight: Font.DemiBold }
                Repeater {
                    model: u.updates
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true; spacing: 10
                        Image { width: 16; height: 16; Layout.preferredWidth: 16; Layout.preferredHeight: 16; sourceSize: Qt.size(32, 32)
                                source: win.gl(modelData.kind === "app" ? "app-grid" : "xos-mark", Theme.textDim) }
                        Label2 { text: modelData.name; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Rectangle { visible: modelData.security; radius: 8; height: 20; width: sl.implicitWidth + 16
                                    color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.18)
                                    Text { id: sl; anchors.centerIn: parent; text: "Security"; color: Theme.warning
                                           font.family: Theme.fontFamily; font.pixelSize: 11; font.weight: Font.DemiBold } }
                        Dim { text: (modelData.old ? modelData.old + "  →  " : "") + modelData.new
                              Layout.fillWidth: false; wrapMode: Text.NoWrap; font.pixelSize: 12 }
                    }
                }
            }
            Card {
                Row2 { glyph: "notifications"; heading: "Check automatically"
                       detail: "Once a day. X-OS tells you when updates are ready - it never installs them without you."
                       Toggle { on: backend.autoUpdates; onToggled: v => backend.setAutoUpdates(v) } }
            }
            Card {
                visible: backend.log !== "" && backend.page === "updates"
                Label2 { text: "Details"; font.weight: Font.DemiBold }
                Text { Layout.fillWidth: true; text: backend.log.split("\n").slice(-14).join("\n"); color: Theme.textDim
                       font.family: Theme.fontMono; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
            }
        }
    }

    // ------------------------------------------------------------------ Security
    Component {
        id: securityPage
        ColumnLayout {
            spacing: 16
            readonly property var s: backend.sec
            readonly property var d: s.definitions || {}
            readonly property bool ok: s.antivirus && d.installed && d.age_days < 8 && s.firewall !== false
            Card {
                Hero {
                    glyph: "security"
                    tint: ok ? Theme.success : Theme.warning
                    heading: ok ? "Your computer is protected" : "Your attention is needed"
                    detail: !s.antivirus ? "The virus scanner is not installed."
                          : !d.installed ? "Virus definitions are missing - update them."
                          : d.age_days >= 8 ? "Virus definitions are " + d.age_days + " days old - update them."
                          : s.firewall === false ? "The firewall is off."
                          : "Virus definitions updated " + (d.age_days === 0 ? "today" : d.age_days + " day" + (d.age_days === 1 ? "" : "s") + " ago") + "."
                }
            }
            Card {
                Label2 { text: "Virus & threat protection"; font.weight: Font.DemiBold; font.pixelSize: 15 }
                Dim { text: backend.scan.running ? backend.scan.target + " running for " + backend.scan.elapsed + " s…"
                          : (backend.scan.result !== "" ? backend.scan.target + ": " + backend.scan.result
                                                         : "Quick scan checks Downloads, Desktop, Documents and temporary files.") }
                RowLayout { spacing: 10
                    Pill { text: "Quick scan"; primary: true; enabled: backend.busy === ""; onClicked: backend.startScan("quick") }
                    Pill { text: "Full scan"; enabled: backend.busy === ""; onClicked: backend.startScan("full") }
                    Pill { text: "Scan a folder…"; enabled: backend.busy === ""; onClicked: folderDialog.open() } }
                Repeater {
                    model: backend.scan.found || []
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true; spacing: 10
                        Image { width: 16; height: 16; Layout.preferredWidth: 16; Layout.preferredHeight: 16; sourceSize: Qt.size(32, 32); source: win.gl("badge-warning", Theme.danger) }
                        Label2 { text: modelData.path; elide: Text.ElideMiddle; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                        Dim { text: modelData.signature; Layout.fillWidth: false; wrapMode: Text.NoWrap; font.pixelSize: 12 }
                    }
                }
            }
            Card {
                Row2 { glyph: "eye"; heading: "Real-time protection"
                       detail: "Checks files in your home folder as they are opened. Uses about 1 GB of memory."
                       Toggle { on: !!s.realtime; enabled: backend.busy === ""; onToggled: v => backend.setRealtime(v) } }
                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                Row2 { glyph: "updates"; heading: "Virus definitions"
                       detail: d.installed ? "Updated automatically every hour when online." : "Not installed yet."
                       Pill { text: "Update now"; enabled: backend.busy === ""; onClicked: backend.updateDefinitions() } }
                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                Row2 { glyph: "archive"; heading: "Quarantine"
                       detail: (s.quarantine || 0) + " item" + (s.quarantine === 1 ? "" : "s") + ". Threats are moved here, never deleted silently."
                       Pill { text: "Open"; onClicked: backend.openQuarantine() } }
            }
            Card {
                Row2 { glyph: "lock"; heading: "Firewall"
                       detail: s.firewall === null ? "Not installed." : "Blocks incoming connections nobody asked for."
                       Toggle { on: !!s.firewall; enabled: backend.busy === "" && s.firewall !== null; onToggled: v => backend.setFirewall(v) } }
                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                Row2 { glyph: "power"; heading: "Secure Boot"
                       detail: s.secureBoot === true ? "On: only signed boot software can start."
                             : s.secureBoot === false ? "Off. You can turn it on in your computer's firmware settings."
                             : "Not available on this computer (legacy BIOS)." }
            }
            FolderDialog { id: folderDialog; title: "Choose a folder to scan"; onAccepted: backend.startScan(selectedFolder.toString()) }
        }
    }

    // ------------------------------------------------------------------ This PC
    Component {
        id: pcPage
        ColumnLayout {
            spacing: 16
            Dim { text: "Drives and devices. Double-click to open; Windows partitions and USB drives are opened safely." }
            GridLayout {
                Layout.fillWidth: true
                columns: 2; columnSpacing: 12; rowSpacing: 12
                Repeater {
                    model: backend.drives
                    delegate: Rectangle {
                        id: tile
                        required property var modelData
                        readonly property string icon: ({ system: "this-pc", windows: "disk-manager", data: "disk-manager",
                                                          removable: "usb-drive", optical: "disc" })[modelData.kind] || "disk-manager"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 92
                        radius: 16
                        color: dm.containsMouse ? Theme.surface2 : Theme.surface1
                        border.color: Theme.border
                        Behavior on color { ColorAnimation { duration: 120 } }
                        RowLayout { anchors.fill: parent; anchors.margins: 16; spacing: 14
                            Rectangle { width: 46; height: 46; radius: 13; color: Theme.surface2
                                Image { anchors.centerIn: parent; width: 24; height: 24; sourceSize: Qt.size(48, 48)
                                        source: win.gl(tile.icon, Theme.text) } }
                            ColumnLayout { Layout.fillWidth: true; spacing: 5
                                RowLayout { Layout.fillWidth: true
                                    Label2 { text: modelData.name + (modelData.kind === "system" ? "  (this system)" : "")
                                             font.weight: Font.DemiBold; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                                    Rectangle { visible: modelData.removable; width: 26; height: 26; radius: 13
                                        color: ej.containsMouse ? Theme.surface2 : "transparent"
                                        Image { anchors.centerIn: parent; width: 14; height: 14; sourceSize: Qt.size(28, 28)
                                                source: win.gl("eject", Theme.textDim) }
                                        MouseArea { id: ej; anchors.fill: parent; hoverEnabled: true; onClicked: backend.ejectDrive(modelData.path) }
                                        Accessible.role: Accessible.Button; Accessible.name: "Eject " + modelData.name } }
                                Rectangle { Layout.fillWidth: true; height: 6; radius: 3; color: Theme.surface2
                                    visible: modelData.percent !== null && modelData.percent !== undefined
                                    Rectangle { height: parent.height; radius: 3; width: parent.width * Math.min(1, (modelData.percent || 0) / 100)
                                                color: (modelData.percent || 0) > 90 ? Theme.danger : Theme.accent } }
                                Dim { font.pixelSize: 12
                                      text: modelData.freeText !== "" ? modelData.freeText + " free of " + modelData.sizeText
                                          : modelData.sizeText + "  ·  " + (modelData.fstype || "").toUpperCase() + "  ·  not opened yet" }
                            }
                        }
                        MouseArea { id: dm; anchors.fill: parent; hoverEnabled: true; z: -1
                                    onDoubleClicked: backend.openDrive(modelData.path, modelData.mountpoint) }
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.name
                        Keys.onReturnPressed: backend.openDrive(modelData.path, modelData.mountpoint)
                        activeFocusOnTab: true
                    }
                }
            }
            Dim { visible: backend.drives.length === 0; text: "No drives found." }
        }
    }

    // ------------------------------------------------------------------ About
    Component {
        id: aboutPage
        ColumnLayout {
            spacing: 16
            Card {
                RowLayout { spacing: 18
                    Image { width: 72; height: 72; Layout.preferredWidth: 72; Layout.preferredHeight: 72; sourceSize: Qt.size(144, 144); source: backend.logo }
                    ColumnLayout { spacing: 4
                        Label2 { text: backend.about.version || "X-OS"; font.pixelSize: 20; font.weight: Font.DemiBold }
                        Dim { text: "Built on Debian 13 · Linux " + backend.about.kernel } } }
            }
            Card {
                Row2 { glyph: "this-pc"; heading: "Computer name"; detail: backend.about.host }
                Row2 { glyph: "system-monitor"; heading: "Processor"; detail: backend.about.cpu || "Unknown" }
                Row2 { glyph: "disk-manager"; heading: "Memory"; detail: backend.about.memory || "Unknown" }
            }
        }
    }
}
