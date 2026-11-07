// Slides shown while X-OS installs.
// Calamares' stock Slide is inset (5 % / 20 % margins) and the view behind it clears to white,
// so every slide here is full-bleed on the installer's own background.
import QtQuick
import calamares.slideshow 1.0

Presentation {
    id: presentation
    function nextSlide() { presentation.goToNextSlide() }
    Timer { interval: 8000; running: presentation.activatedInCalamares; repeat: true; onTriggered: presentation.nextSlide() }

    component XSlide: Slide {
        id: s
        property string heading: ""
        property string body: ""
        property string glyph: "logo.svg"
        x: 0; y: 0
        width: presentation.width
        height: presentation.height

        Rectangle { anchors.fill: parent; color: "#0B0C0E"; radius: 16; clip: true
            Image {
                anchors.fill: parent
                anchors.margins: 1
                source: "file:///usr/share/wallpapers/X-OS/x-os-dark.svg"
                fillMode: Image.PreserveAspectCrop
                sourceSize: Qt.size(width, height)
                opacity: 0.9
            }
        }
        Rectangle { anchors.fill: parent; color: "transparent"; radius: 16; border.color: Qt.rgba(1, 1, 1, 0.07) }
        Column {
            anchors.centerIn: parent
            width: parent.width * 0.74
            spacing: 14
            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                source: s.glyph
                width: 72; height: 72
                sourceSize: Qt.size(144, 144)
            }
            Item { width: 1; height: 4 }
            Text {
                text: s.heading
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                color: "#ECEEF1"
                font.family: "Inter"
                font.pixelSize: 30
                font.weight: Font.DemiBold
            }
            Text {
                text: s.body
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                lineHeight: 1.15
                color: "#9AA1AB"
                font.family: "Inter"
                font.pixelSize: 17
            }
        }
    }

    // backdrop behind the slides (not a Slide, so Presentation leaves it alone)
    Rectangle { anchors.fill: parent; color: "#121417"; z: -1 }

    XSlide { heading: "Welcome to X-OS"; body: "Beyond Windows. Beyond macOS." }
    XSlide { heading: "Your apps, your way"; body: "Firefox is ready. Chrome and other browsers download from their makers' signed servers." }
    XSlide { heading: "Windows programs"; body: "Double-click a .exe or .msi file: X-OS tells you how well it runs before anything is installed." }
    XSlide { heading: "Designed to stay calm"; body: "A thin menu bar on top, a floating dock below, and Control Center for everything else." }
    XSlide { heading: "Two keyboards, one shortcut"; body: "Press Alt + Shift to switch between your keyboard layouts." }

    function onActivate() { presentation.currentSlide = 0 }
    function onLeave() { }
}
