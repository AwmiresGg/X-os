// Stand-in for Calamares' Branding (only what the X-OS panels use), for offscreen renders.
pragma Singleton
import QtQuick
QtObject {
    enum ImageEntry { ProductLogo }
    enum StringEntry { ProductName, ShortVersion }
    property string brandingDir: ""
    function imagePath(e) { return brandingDir + "/logo.svg" }
    function string(e) { return e === 0 ? "X-OS" : "0.1" }
}
