// X-OS floating dock.
//
// Geometry comes from desktop/dock/geometry.mjs (unit-tested). Behaviour follows the
// reference: app tiles sit in the bar; ONE accent circle floats above the active app in a
// concave cradle with a visible gap; switching slides circle + cradle (the icon fades out in
// transit and in on arrival). Motion durations come from the Theme and become 0 with
// Reduce Motion.
import QtQuick
import QtQuick.Shapes
import QtQuick.Effects
import XOS.Theme
import "components"
import "../../dock/geometry.mjs" as Geo

Item {
    id: dock
    required property var windows
    required property var settings
    required property var status
    signal contextMenu(var item, real anchorX)

    readonly property var cfg: settings ? settings.values : ({ dockIconSize: 46, dockOpacity: 0.55 })
    readonly property var apps: windows ? windows.items : []
    readonly property bool trashFull: !!status && !!((status.data.trash || {}).full)
    // one extra slot after a separator: the Trash
    readonly property int count: apps.length + 1

    // ---------------------------------------------------------------- geometry (reference ratios)
    readonly property real iconSize: cfg.dockIconSize
    readonly property real barH: Math.round(iconSize + 18)
    readonly property var opts: Object.assign({}, Geo.DEFAULTS, {
        iconSize: iconSize,
        containerPad: Math.max(2, (Theme.barCircleRatio * barH - iconSize) / 2),
        spacing: Math.round(iconSize * 0.22),
        padding: Math.ceil(0.48 * barH),
        height: barH,
        gap: Math.max(Theme.barMinGap, Theme.barGapRatio * barH),
        lift: Theme.barLift,
        fillet: Theme.barFilletRatio * barH,
        cornerRadius: Math.round(0.28 * barH)
    })
    readonly property var lay: Geo.layout(count, opts)
    readonly property real r: Geo.containerRadius(opts)
    readonly property real headroom: r + opts.lift + 6

    implicitWidth: lay.width
    implicitHeight: headroom + barH

    property int activeIndex: {
        for (let i = 0; i < apps.length; ++i) if (apps[i].active) return i
        return -1
    }
    property real notchX: lay.xs.length ? lay.xs[Math.max(0, activeIndex)] : 0
    Behavior on notchX {
        NumberAnimation { duration: Theme.durSlide; easing.type: Easing.BezierSpline; easing.bezierCurve: Theme.curveSlide }
    }
    property real activeT: activeIndex >= 0 ? 1 : 0
    Behavior on activeT {
        NumberAnimation { duration: Theme.durSlide; easing.type: Easing.BezierSpline; easing.bezierCurve: Theme.curveSlide }
    }
    readonly property var notch: Geo.notch(notchX, activeT, opts)
    readonly property bool gpu: GraphicsInfo.api !== GraphicsInfo.Software && !Theme.lowResource

    // ---------------------------------------------------------------- body
    Item {
        id: body
        y: dock.headroom
        width: dock.lay.width
        height: dock.barH

        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            layer.enabled: dock.gpu
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: Theme.shadow
                shadowBlur: 0.9
                shadowVerticalOffset: 6
            }
            ShapePath {
                strokeWidth: 1
                strokeColor: Theme.borderStrong
                fillColor: Qt.rgba(Theme.surface1.r, Theme.surface1.g, Theme.surface1.b, dock.cfg.dockOpacity)
                PathSvg { path: Geo.dockPath(dock.lay.width, dock.notch, dock.opts) }
            }
        }
        // inner top highlight (glass edge), skipped in low-resource mode
        Shape {
            visible: dock.gpu
            anchors.fill: parent
            anchors.topMargin: 1
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                fillColor: "transparent"
                strokeWidth: 1
                strokeColor: Theme.highlight
                PathSvg { path: Geo.dockPath(dock.lay.width, dock.notch, dock.opts) }
            }
        }
        // separator before the Trash
        Rectangle {
            visible: dock.apps.length > 0
            x: (dock.lay.xs[dock.count - 2] + dock.lay.xs[dock.count - 1]) / 2
            anchors.verticalCenter: parent.verticalCenter
            width: 1
            height: dock.iconSize * 0.7
            color: Theme.border
        }
    }

    // ---------------------------------------------------------------- tiles
    Repeater {
        model: dock.count
        delegate: Item {
            id: slot
            required property int index
            readonly property bool isTrash: index === dock.count - 1
            readonly property var app: isTrash ? null : dock.apps[index]
            readonly property real act: isTrash ? 0
                : Geo.iconActivation(dock.lay.xs[index], dock.notchX, dock.activeT, dock.lay.pitch)
            readonly property bool hovered: hover.hovered

            x: dock.lay.xs[index] - dock.iconSize / 2
            y: body.y + (dock.barH - dock.iconSize) / 2 - (hovered && act < 0.5 ? 3 : 0)
            width: dock.iconSize
            height: dock.iconSize
            Behavior on y { NumberAnimation { duration: Theme.durHover; easing.type: Easing.BezierSpline; easing.bezierCurve: Theme.curveHover } }

            Accessible.role: Accessible.Button
            Accessible.name: isTrash ? "Trash" : app.name + (app.running ? ", running" : "")
            activeFocusOnTab: true
            function activate() {
                if (isTrash) dock.windows.openUrl("trash:/")
                else dock.windows.activateApp(app.appId)
            }
            Keys.onReturnPressed: activate()
            Keys.onSpacePressed: activate()
            Keys.onMenuPressed: if (!isTrash) dock.contextMenu(app, x + width / 2)

            // tile: dims while the circle is over it (reference: grey in transit)
            Image {
                anchors.fill: parent
                visible: !slot.isTrash
                source: slot.app ? slot.app.tile : ""
                sourceSize: Qt.size(dock.iconSize * 2, dock.iconSize * 2)
                opacity: 1 - 0.75 * Math.min(1, slot.act * 1.4)
                smooth: true
            }
            Rectangle {      // Trash: glyph on the same tile material as the app tiles
                visible: slot.isTrash
                anchors.fill: parent
                radius: dock.iconSize * 0.24
                color: Theme.surface2
                border.color: Theme.borderStrong
                Glyph { anchors.centerIn: parent; size: dock.iconSize * 0.56; name: dock.trashFull ? "trash-full" : "trash-empty" }
            }
            // running indicator (static dot — no pulsing)
            Rectangle {
                visible: !slot.isTrash && slot.app.running
                width: 4; height: 4; radius: 2
                anchors.horizontalCenter: parent.horizontalCenter
                y: parent.height + 4 + (slot.hovered && slot.act < 0.5 ? 3 : 0)
                color: slot.app && slot.app.active ? Theme.accent : Theme.textDim
            }
            // focus ring (keyboard navigation)
            Rectangle {
                visible: slot.activeFocus
                anchors.fill: parent; anchors.margins: -3
                radius: dock.iconSize * 0.28
                color: "transparent"; border.width: 2; border.color: Theme.accent
            }

            HoverHandler { id: hover }
            TapHandler {
                id: tap
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onTapped: (pt, button) => {
                    if (button === Qt.RightButton && !slot.isTrash)
                        dock.contextMenu(slot.app, slot.x + slot.width / 2)
                    else
                        slot.activate()
                }
            }
            // name tooltip above the tile
            Rectangle {
                visible: slot.hovered && slot.act < 0.5
                anchors.horizontalCenter: parent.horizontalCenter
                y: -dock.headroom + 2
                width: tip.implicitWidth + 16; height: 24; radius: Theme.radiusXs
                color: Theme.surface1; border.color: Theme.borderStrong
                Text {
                    id: tip
                    anchors.centerIn: parent
                    text: slot.isTrash ? "Trash" : slot.app.name + (slot.app.windows.length > 1 ? "  ·  " + slot.app.windows.length : "")
                    color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fontCaption + 1
                }
            }
        }
    }

    // ---------------------------------------------------------------- the floating active circle
    Item {
        id: circle
        readonly property real cy: body.y + Geo.floatingCentre(dock.activeT, dock.opts)
        x: dock.notchX - dock.r
        y: cy - dock.r
        width: 2 * dock.r
        height: 2 * dock.r
        opacity: Geo.smoothstep(dock.activeT)
        visible: opacity > 0.01

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: Theme.accentDeep
            border.width: 1
            border.color: Theme.accentGlow
            Rectangle {      // faint top highlight (the "3D" cue)
                visible: dock.gpu
                x: parent.width * 0.2; y: parent.height * 0.06
                width: parent.width * 0.6; height: parent.height * 0.3; radius: height / 2
                gradient: Gradient {
                    GradientStop { position: 0; color: Qt.rgba(1, 1, 1, 0.10) }
                    GradientStop { position: 1; color: Qt.rgba(1, 1, 1, 0) }
                }
            }
            layer.enabled: dock.gpu
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: Theme.shadow
                shadowBlur: 0.7
                shadowVerticalOffset: 4
            }
        }
        // the active app's glyph (fades in only when the circle has arrived)
        Repeater {
            model: dock.apps.length
            delegate: Item {
                required property int index
                readonly property var app: dock.apps[index]
                readonly property real act: Geo.iconActivation(dock.lay.xs[index], dock.notchX, dock.activeT, dock.lay.pitch)
                anchors.centerIn: parent
                width: dock.iconSize * 0.62; height: width
                opacity: Math.max(0, (act - 0.82) / 0.18)
                visible: opacity > 0
                Glyph {
                    visible: parent.app.glyph !== ""
                    anchors.fill: parent
                    size: parent.width
                    name: parent.app.glyph
                    tint: Theme.onAccent
                }
                Image {
                    visible: parent.app.glyph === ""
                    anchors.fill: parent
                    source: parent.app.tile
                    sourceSize: Qt.size(width * 2, height * 2)
                }
            }
        }
    }
}
