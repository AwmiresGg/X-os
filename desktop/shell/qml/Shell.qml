// X-OS shell: menu bar (top), floating dock (bottom) and one popover layer.
// Each is a layer-shell surface on Wayland (XOS.Platform.ShellWindow).
import QtQuick
import XOS.Theme
import XOS.Platform

QtObject {
    id: shell
    required property var settings
    required property var status
    required property var windows
    property string previewOpen: ""
    property real previewLaunch: -1

    property string openMenu: ""
    onOpenMenuChanged: windows.setMenuOpen(openMenu !== "")
    property real menuX: 0
    property bool fromDock: false
    property var dockItem: null

    function openAt(name, x, dock, item) {
        fromDock = !!dock
        dockItem = item || null
        menuX = x
        openMenu = name
    }

    // Theme follows the user's settings.
    property Binding themeMode: Binding { target: Theme; property: "mode"; value: shell.settings.values.theme }
    property Binding motion: Binding { target: Theme; property: "reducedMotion"; value: !!shell.settings.values.reducedMotion }
    property Binding lowRes: Binding { target: Theme; property: "lowResource"; value: !!shell.settings.values.lowResource }

    property ShellWindow menuBarWindow: ShellWindow {
        edge: "top"
        exclusive: 30
        width: 1                         // stretched by the top/left/right anchors
        height: 30
        visible: true
        MenuBar {
            anchors.fill: parent
            status: shell.status
            windows: shell.windows
            opacity_: shell.settings.values.menuBarOpacity
            openMenu: shell.openMenu
            onRequestMenu: (name, x) => shell.openAt(name, x, false)
        }
    }

    property ShellWindow dockWindow: ShellWindow {
        edge: "bottom"
        marginEdge: 8                    // floating: never touches the screen edge
        exclusive: dockBar.barH + 8      // maximized windows end above the dock
        width: dockBar.implicitWidth
        height: dockBar.implicitHeight
        visible: true
        DockBar {
            id: dockBar
            objectName: "dockBar"
            anchors.fill: parent
            windows: shell.windows
            settings: shell.settings
            status: shell.status
            onContextMenu: (item, x) => shell.openAt("dock", x, true, item)
        }
    }

    // One full-work-area overlay while a menu is open: clicking outside the panel closes it.
    property ShellWindow popoverWindow: ShellWindow {
        edge: "full"
        overlay: true
        keyboard: true
        visible: shell.openMenu !== ""
        MouseArea {
            anchors.fill: parent
            onClicked: shell.openMenu = ""
        }
        Popovers {
            id: pop
            name: shell.openMenu
            status: shell.status
            windows: shell.windows
            settings: shell.settings
            dockItem: shell.dockItem
            onClose: shell.openMenu = ""
            focus: true
            Keys.onEscapePressed: shell.openMenu = ""
            x: Math.max(8, Math.min(parent.width - width - 8,
                   shell.openMenu === "system" ? 8 : shell.fromDock
                       ? (parent.width - dockBar.implicitWidth) / 2 + shell.menuX - width / 2
                       : shell.menuX - width / 2))
            y: shell.fromDock ? parent.height - height - dockBar.barH - 18 : 6
            width: implicitWidth
            height: implicitHeight
            MouseArea { anchors.fill: parent; z: -1 }     // clicks on the panel don't close it
        }
    }
}
