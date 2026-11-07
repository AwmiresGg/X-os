// No compositor blur available on this platform: same API, no effect.
import QtQuick

QtObject {
    property Item target
    property bool enabled
    property var polygon
    property bool lowResource: false
}
