// Glass panel used by every popover: one material, one radius, one rim.
import QtQuick
import QtQuick.Effects
import XOS.Theme

Item {
    id: panel
    default property alias content: body.data
    property int padding: 6
    implicitWidth: body.childrenRect.width + 2 * padding
    implicitHeight: body.childrenRect.height + 2 * padding

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: Theme.radiusMd
        // Popovers stay highly opaque: text on them must be readable over any wallpaper.
        color: Qt.rgba(Theme.surface1.r, Theme.surface1.g, Theme.surface1.b, 0.94)
        border.width: 1
        border.color: Theme.borderStrong
        layer.enabled: !Theme.lowResource && GraphicsInfo.api !== GraphicsInfo.Software
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.shadow
            shadowBlur: 0.8
            shadowVerticalOffset: 6
        }
    }
    Item {
        id: body
        x: panel.padding
        y: panel.padding
        width: panel.width - 2 * panel.padding
        height: panel.height - 2 * panel.padding
    }
}
