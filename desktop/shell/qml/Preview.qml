// Offscreen preview of the whole shell (menu bar + dock + one popover) over the wallpaper,
// driven by demo data. Used for screenshots and visual regression checks.
import QtQuick
import QtQuick.Window
import XOS.Theme

Window {
    id: win
    width: 1440
    height: 900
    visible: true
    color: Theme.bg
    required property var settings
    required property var status
    required property var windows
    property string previewOpen: ""

    Binding { target: Theme; property: "mode"; value: win.settings.values.theme }

    Image {
        anchors.fill: parent
        source: Qt.resolvedUrl("../../../themes/liquid-glass/wallpapers/x-os-" + (Theme.dark ? "dark" : "light") + ".svg")
        sourceSize: Qt.size(width, height)
        fillMode: Image.PreserveAspectCrop
    }
    // a sample app window so the glass is seen over content, not just wallpaper
    Rectangle {
        x: 220; y: 120; width: 760; height: 470; radius: 12
        color: Theme.surface0; border.color: Theme.border
        Rectangle { width: parent.width; height: 40; radius: 12; color: Theme.surface1 }
        Text { x: 20; y: 11; text: "X-OS — Mozilla Firefox"; color: Theme.textDim; font.pixelSize: 13; font.family: Theme.fontFamily }
    }
    MenuBar {
        id: bar
        width: parent.width
        status: win.status
        windows: win.windows
        opacity_: win.settings.values.menuBarOpacity
        openMenu: win.previewOpen
    }
    DockBar {
        id: dock
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        width: implicitWidth
        height: implicitHeight
        windows: win.windows
        settings: win.settings
        status: win.status
    }
    Popovers {
        visible: win.previewOpen !== ""
        name: win.previewOpen
        status: win.status
        windows: win.windows
        settings: win.settings
        width: implicitWidth
        height: implicitHeight
        x: win.previewOpen === "system" ? 8 : win.previewOpen === "battery" ? parent.width - width - 330 : parent.width - width - 90
        y: 36
    }
}
