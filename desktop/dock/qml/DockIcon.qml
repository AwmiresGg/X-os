// One application slot of the Signature Dock: a circular liquid-glass container
// holding the app glyph, a running indicator and (for grouped apps) window dots.
import QtQuick
import QtQuick.Effects

Item {
    id: root

    required property int index
    required property string name
    required property url icon
    required property bool running
    required property int windows

    property real activation: 0         // 0 = resting in the dock, 1 = floating
    property real radius: 30
    property bool dark: true
    property string effects: "full"     // full | reduced | static
    property real shadowIntensity: 0.5
    property bool showIndicator: true

    signal clicked()
    signal hoverChanged(bool hovered)

    width: radius * 2
    height: radius * 2

    readonly property bool hovered: hover.hovered

    // Elevated glass circle. Running apps always get one; pinned-only apps get a
    // subtler variant so the dock stays calm.
    Rectangle {
        id: glass
        anchors.fill: parent
        radius: width / 2
        scale: root.hovered && root.effects !== "static" ? 1.06 : 1.0
        Behavior on scale { enabled: root.effects !== "static"; NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

        readonly property real strength: root.running ? 1.0 : 0.55
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.dark ? Qt.rgba(1, 1, 1, 0.22 * glass.strength + 0.10 * root.activation)
                                                           : Qt.rgba(1, 1, 1, 0.85) }
            GradientStop { position: 0.55; color: root.dark ? Qt.rgba(1, 1, 1, 0.07 * glass.strength)
                                                            : Qt.rgba(1, 1, 1, 0.55) }
            GradientStop { position: 1.0; color: root.dark ? Qt.rgba(0.55, 0.62, 1.0, 0.10 * glass.strength + 0.12 * root.activation)
                                                           : Qt.rgba(0.80, 0.84, 1.0, 0.65) }
        }
        border.width: 1
        border.color: root.dark ? Qt.rgba(1, 1, 1, 0.16 + 0.14 * root.activation) : Qt.rgba(1, 1, 1, 0.9)

        // Specular highlight: a soft crescent on the upper rim (the "3D" cue).
        Rectangle {
            x: parent.width * 0.22; y: parent.height * 0.05
            width: parent.width * 0.56; height: parent.height * 0.30
            radius: height / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, root.dark ? 0.09 : 0.45) }
                GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0.0) }
            }
            visible: root.effects !== "static"
        }

        Image {
            id: glyph
            anchors.centerIn: parent
            source: root.icon
            width: root.radius * 1.36
            height: width
            sourceSize: Qt.size(width * 2, height * 2)
            smooth: true
            mipmap: true
        }

        layer.enabled: root.effects === "full" && root.shadowIntensity > 0
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(0, 0, 0, 0.55 * root.shadowIntensity)
            shadowBlur: 0.6 + 0.3 * root.activation
            shadowVerticalOffset: 3 + 7 * root.activation
            shadowHorizontalOffset: 0
            autoPaddingEnabled: true
        }
    }

    // Running indicator below the container; fades out while floating (the raised
    // circle itself signals the active app).
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.bottom
        anchors.topMargin: 3
        spacing: 3
        visible: root.showIndicator && root.running
        opacity: 1 - root.activation
        Repeater {
            model: Math.min(Math.max(root.windows, 1), 3)
            Rectangle {
                width: root.windows > 1 ? 4 : 5; height: width; radius: width / 2
                color: root.dark ? "#C9D2FF" : "#3F4AA8"
            }
        }
    }

    HoverHandler {
        id: hover
        onHoveredChanged: root.hoverChanged(hovered)
    }
    TapHandler { onTapped: root.clicked() }

    Accessible.role: Accessible.Button
    Accessible.name: root.name + (root.running ? ", running" : "")
    Accessible.onPressAction: root.clicked()
}
