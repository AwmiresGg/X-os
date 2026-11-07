// X-OS Signature Dock.
//
// A floating liquid-glass dock whose surface deforms around the active
// application. Geometry comes from ../geometry.mjs (unit-tested); this file only
// binds it to Qt Quick and animates two numbers:
//   notchX  - x of the notch, slides between icons when the active app changes
//   activeT - 0..1 activation depth (the notch opens / closes)
// Icons near notchX rise into the floating state, which gives the liquid
// hand-over between apps. With effects === "static" (LITE profile / software
// rendering) everything snaps without animation and without shadows.
import QtQuick
import QtQuick.Shapes
import "../geometry.mjs" as Geo

Item {
    id: dock

    // Model: array of { id, name, icon, running, windows, titles }
    property var apps: []
    property int activeIndex: -1

    // Settings (Control Center > Personalization > Dock)
    property string effects: "full"         // full | reduced | static
    property real animationSpeed: 1.0       // 0.5 .. 2
    property real animationIntensity: 1.0   // 0 .. 1  (lift and spring overshoot)
    property real iconSize: 48
    property real glassOpacity: 0.62
    property real shadowIntensity: 0.55
    property bool dark: true
    property bool showIndicators: true
    property bool autoHide: false

    signal activated(int index)

    readonly property var opts: Object.assign({}, Geo.DEFAULTS, {
        iconSize: iconSize,
        lift: Geo.DEFAULTS.lift * (0.4 + 0.6 * animationIntensity)
    })
    readonly property var lay: Geo.layout(apps.length, opts)
    readonly property real cRadius: Geo.containerRadius(opts)
    readonly property real headroom: cRadius + opts.lift + 12   // space above the body for the floating circle
    // Effect tiers: full = springs + GPU shadows; reduced = animations, no GPU-only
    // effects; static = no animation (LITE profile). Qt's software renderer cannot
    // draw MultiEffect layers (the item would vanish), so it is capped at "reduced".
    readonly property bool softwareRendering: GraphicsInfo.api === GraphicsInfo.Software
    readonly property string tier: softwareRendering && effects === "full" ? "reduced" : effects
    readonly property bool animated: tier !== "static"

    implicitWidth: lay.width
    implicitHeight: headroom + opts.height + 14

    // ---------------------------------------------------------------- animation state
    property real notchX: lay.xs.length ? lay.xs[Math.max(0, activeIndex)] : 0
    Behavior on notchX {
        enabled: dock.animated
        SpringAnimation {
            spring: 3.2 * dock.animationSpeed
            damping: 0.42 + 0.3 * (1 - dock.animationIntensity)
            epsilon: 0.2
        }
    }
    property real activeT: activeIndex >= 0 ? 1 : 0
    Behavior on activeT {
        enabled: dock.animated
        NumberAnimation { duration: 380 / dock.animationSpeed; easing.type: Easing.InOutCubic }
    }

    // Auto-hide: slide below the screen edge unless hovered.
    property bool revealed: !autoHide || hoverArea.hovered
    HoverHandler { id: hoverArea }

    Item {
        id: content
        width: dock.lay.width
        height: dock.implicitHeight
        anchors.horizontalCenter: parent.horizontalCenter
        y: dock.revealed ? 0 : dock.implicitHeight - 4
        Behavior on y { enabled: dock.animated; NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }

        // ---------------------------------------------------------- dock body
        Shape {
            id: body
            y: dock.headroom
            width: dock.lay.width
            height: dock.opts.height
            preferredRendererType: Shape.CurveRenderer
            antialiasing: true

            ShapePath {
                strokeWidth: 1
                strokeColor: dock.dark ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.85)
                fillGradient: LinearGradient {
                    x1: 0; y1: 0; x2: 0; y2: body.height
                    GradientStop { position: 0.0; color: dock.dark ? Qt.rgba(0.20, 0.22, 0.30, dock.glassOpacity)
                                                                   : Qt.rgba(1, 1, 1, dock.glassOpacity + 0.15) }
                    GradientStop { position: 1.0; color: dock.dark ? Qt.rgba(0.08, 0.09, 0.14, dock.glassOpacity + 0.12)
                                                                   : Qt.rgba(0.90, 0.92, 0.98, dock.glassOpacity + 0.2) }
                }
                PathSvg { path: Geo.dockPath(dock.lay.width, Geo.notch(dock.notchX, dock.activeT, dock.opts), dock.opts) }
            }
        }
        // Inner top highlight (thin light line just inside the rim).
        Shape {
            y: dock.headroom + 1.2
            width: dock.lay.width
            height: dock.opts.height
            visible: dock.tier !== "static"
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                fillColor: "transparent"
                strokeWidth: 1
                strokeColor: Qt.rgba(1, 1, 1, dock.dark ? 0.07 : 0.5)
                PathSvg { path: Geo.dockPath(dock.lay.width, Geo.notch(dock.notchX, dock.activeT, dock.opts), dock.opts) }
            }
        }
        // Soft ambient shadow under the dock.
        Rectangle {
            visible: dock.tier !== "static" && dock.shadowIntensity > 0
            z: -1
            x: 18; width: dock.lay.width - 36
            y: dock.headroom + dock.opts.height - 10
            height: 22; radius: 11
            color: Qt.rgba(0, 0, 0, 0.35 * dock.shadowIntensity)
            layer.enabled: true
            layer.smooth: true
            opacity: 0.8
        }

        // ---------------------------------------------------------- icons
        Repeater {
            model: dock.apps.length
            delegate: DockIcon {
                id: slot
                required property int modelData
                index: modelData
                readonly property var app: dock.apps[modelData]
                name: app.name
                icon: app.icon
                running: !!app.running
                windows: app.windows || 0
                dark: dock.dark
                effects: dock.tier
                shadowIntensity: dock.shadowIntensity
                showIndicator: dock.showIndicators
                radius: dock.cRadius
                activation: dock.activeIndex < 0 && dock.activeT <= 0 ? 0
                            : Geo.iconActivation(dock.lay.xs[modelData], dock.notchX, dock.activeT, dock.lay.pitch)
                x: dock.lay.xs[modelData] - radius
                y: dock.headroom + Geo.floatingCentre(activation, dock.opts) - radius
                z: activation
                onClicked: dock.activated(modelData)
                onHoverChanged: (h) => { if (h) preview.show(modelData); else preview.hideSoon() }
            }
        }

        // ---------------------------------------------------------- grouped window preview
        Rectangle {
            id: preview
            property int target: -1
            readonly property var app: target >= 0 && target < dock.apps.length ? dock.apps[target] : null
            visible: opacity > 0
            opacity: app && (app.titles || []).length > 0 && shown ? 1 : 0
            property bool shown: false
            Behavior on opacity { enabled: dock.animated; NumberAnimation { duration: 140 } }
            function show(i) { hideTimer.stop(); target = i; shown = true }
            function hideSoon() { hideTimer.restart() }
            Timer { id: hideTimer; interval: 220; onTriggered: preview.shown = false }

            width: Math.max(180, col.implicitWidth + 24)
            height: col.implicitHeight + 18
            radius: 14
            x: target >= 0 ? Math.min(Math.max(0, dock.lay.xs[target] - width / 2), dock.lay.width - width) : 0
            y: dock.headroom - dock.cRadius * 2 - height - 6
            color: dock.dark ? Qt.rgba(0.12, 0.13, 0.19, 0.92) : Qt.rgba(1, 1, 1, 0.94)
            border.color: dock.dark ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(0, 0, 0, 0.08)
            Column {
                id: col
                anchors.centerIn: parent
                spacing: 6
                Text {
                    text: preview.app ? preview.app.name : ""
                    font.pixelSize: 13; font.weight: Font.DemiBold
                    color: dock.dark ? "#EEF0FF" : "#1B1E2E"
                }
                Repeater {
                    model: preview.app ? preview.app.titles || [] : []
                    Text {
                        required property string modelData
                        text: "▢  " + modelData
                        font.pixelSize: 12
                        color: dock.dark ? "#B8BED8" : "#454B66"
                        elide: Text.ElideRight
                        width: Math.min(implicitWidth, 260)
                    }
                }
            }
        }
    }
}
