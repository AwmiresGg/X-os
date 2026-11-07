// Wayland: a wlr-layer-shell surface (KWin supports it), so the menu bar and dock are real
// shell surfaces: they stay on top, are on every desktop, never appear in Alt+Tab, and the
// menu bar reserves its height so maximized windows do not cover it.
import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LayerShell

Window {
    id: win
    // top | bottom | full  (full = covers the work area, used for popovers + click-outside)
    property string edge: "top"
    property int exclusive: 0          // pixels reserved at the anchored edge
    property int marginEdge: 0         // gap to the anchored screen edge
    property bool overlay: false       // above normal windows and the bars
    property bool keyboard: false      // receives keyboard focus on demand (popovers)

    color: "transparent"
    flags: Qt.FramelessWindowHint

    LayerShell.Window.scope: "xos-shell"
    LayerShell.Window.layer: overlay ? LayerShell.Window.LayerOverlay : LayerShell.Window.LayerTop
    LayerShell.Window.anchors: edge === "top" ? (LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight)
                             : edge === "bottom" ? LayerShell.Window.AnchorBottom
                             : (LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom
                                | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight)
    LayerShell.Window.exclusionZone: exclusive
    LayerShell.Window.keyboardInteractivity: keyboard ? LayerShell.Window.KeyboardInteractivityOnDemand
                                                      : LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.margins.top: edge === "top" ? marginEdge : 0
    LayerShell.Window.margins.bottom: edge === "bottom" ? marginEdge : 0
}
