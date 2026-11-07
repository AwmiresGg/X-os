// Slides shown while X-OS installs.
import QtQuick
import calamares.slideshow 1.0

Presentation {
    id: presentation
    function nextSlide() { presentation.goToNextSlide() }
    Timer { interval: 9000; running: presentation.activatedInCalamares; repeat: true; onTriggered: presentation.nextSlide() }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0D1A" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.6 }
        Column {
            anchors.centerIn: parent; spacing: 14; width: parent.width * 0.8
            Text { text: "Welcome to X-OS"; color: "#EEF0FF"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "Beyond Windows. Beyond macOS."; color: "#B8BED8"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0D1A" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.6 }
        Column {
            anchors.centerIn: parent; spacing: 14; width: parent.width * 0.8
            Text { text: "Your browsers are on the way"; color: "#EEF0FF"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "Firefox and Chrome are downloaded from Mozilla's and Google's signed servers."; color: "#B8BED8"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0D1A" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.6 }
        Column {
            anchors.centerIn: parent; spacing: 14; width: parent.width * 0.8
            Text { text: "Windows apps"; color: "#EEF0FF"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "Open a .exe or .msi file and X-OS shows whether it can run it before anything is installed."; color: "#B8BED8"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0D1A" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.6 }
        Column {
            anchors.centerIn: parent; spacing: 14; width: parent.width * 0.8
            Text { text: "Switch keyboards"; color: "#EEF0FF"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "Press Alt + Shift to switch between your keyboard layouts."; color: "#B8BED8"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    function onActivate() { presentation.currentSlide = 0 }
    function onLeave() { }
}
