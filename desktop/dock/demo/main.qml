// Interactive preview of the Signature Dock on the X-OS wallpaper.
//
//   qml desktop/dock/demo/main.qml
//   qml desktop/dock/demo/main.qml -- --capture /tmp/frames --effects full
//
// With --capture DIR the demo walks through a fixed scenario (activate app 1,
// hand over to app 3, deactivate), saves PNG frames to DIR and quits. Used for
// screenshots and for the visual regression check in testing/.
import QtQuick
import QtQuick.Window
import "../qml"

Window {
    id: win
    width: 1280
    height: 400
    visible: true
    color: "#05060C"
    title: "X-OS Dock preview"

    readonly property var args: Qt.application.arguments
    function arg(name, dflt) {
        const i = args.indexOf(name)
        return i >= 0 && i + 1 < args.length ? args[i + 1] : dflt
    }
    readonly property string captureDir: arg("--capture", "")
    readonly property string iconDir: Qt.resolvedUrl("../../../icons/xos/apps/")

    Image {
        anchors.fill: parent
        source: Qt.resolvedUrl("../../../themes/liquid-glass/wallpapers/x-os-nebula-dark.svg")
        sourceSize: Qt.size(width * 2, height * 2)
        fillMode: Image.PreserveAspectCrop
        verticalAlignment: Image.AlignBottom
    }

    Dock {
        id: dock
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        width: implicitWidth
        height: implicitHeight
        effects: win.arg("--effects", "full")
        dark: win.arg("--theme", "dark") === "dark"
        apps: [
            { id: "files", name: "Files", icon: win.iconDir + "xos-files.svg", running: true, windows: 2,
              titles: ["Home", "Downloads"] },
            { id: "web", name: "Web", icon: win.iconDir + "xos-web.svg", running: true, windows: 1, titles: ["X-OS Docs"] },
            { id: "terminal", name: "Terminal", icon: win.iconDir + "xos-terminal.svg", running: true, windows: 3,
              titles: ["~", "build", "ssh"] },
            { id: "messages", name: "Messages", icon: win.iconDir + "xos-messages.svg", running: false },
            { id: "code", name: "Code", icon: win.iconDir + "xos-code.svg", running: true, windows: 1 },
            { id: "music", name: "Music", icon: win.iconDir + "xos-music.svg", running: false },
            { id: "store", name: "X-Store", icon: win.iconDir + "xos-store.svg", running: false },
            { id: "compat", name: "Windows Apps", icon: win.iconDir + "xos-compat.svg", running: false },
            { id: "settings", name: "Control Center", icon: win.iconDir + "xos-control-center.svg", running: true, windows: 1 }
        ]
        onActivated: (i) => activeIndex = (activeIndex === i ? -1 : i)
    }

    // ------------------------------------------------------------ capture scenario
    property int step: 0
    property int frame: 0
    readonly property var scenario: [
        { at: 0,    active: -1 },
        { at: 400,  active: 1 },
        { at: 1500, active: 2 },
        { at: 2600, active: 6 },
        { at: 3700, active: -1 },
        { at: 4600, active: -2 }   // end
    ]
    property real clock: 0
    Timer {
        running: win.captureDir !== ""
        interval: 50
        repeat: true
        onTriggered: {
            win.clock += interval
            const s = win.scenario[win.step]
            if (s && win.clock >= s.at) {
                if (s.active === -2) { Qt.quit(); return }
                dock.activeIndex = s.active
                win.step++
            }
            const name = win.captureDir + "/frame-" + String(win.frame++).padStart(4, "0") + ".png"
            win.contentItem.grabToImage(r => r.saveToFile(name))
        }
    }
}
