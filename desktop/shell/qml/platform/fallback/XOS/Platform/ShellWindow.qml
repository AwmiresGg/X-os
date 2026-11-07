// Non-Wayland fallback (X11 session, development): a frameless always-on-top window placed
// at the screen edge. No space reservation is possible here; the Wayland session is the
// supported configuration.
import QtQuick
import QtQuick.Window

Window {
    id: win
    property string edge: "top"
    property int exclusive: 0
    property int marginEdge: 0
    property bool overlay: false
    property bool keyboard: false

    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | (keyboard ? 0 : Qt.WindowDoesNotAcceptFocus)
    x: edge === "bottom" ? Math.round((Screen.width - width) / 2) : 0
    y: edge === "bottom" ? Screen.height - height - marginEdge : (edge === "top" ? marginEdge : 0)
    width: edge === "full" || edge === "top" ? Screen.width : width
    height: edge === "full" ? Screen.height : height
}
