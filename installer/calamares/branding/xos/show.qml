// Slides shown while X-OS installs.
import QtQuick
import calamares.slideshow 1.0

Presentation {
    id: presentation
    function nextSlide() { presentation.goToNextSlide() }
    Timer { interval: 8000; running: presentation.activatedInCalamares; repeat: true; onTriggered: presentation.nextSlide() }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0C0E" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.55 }
        Column {
            anchors.centerIn: parent; spacing: 16; width: parent.width * 0.78
            Image { anchors.horizontalCenter: parent.horizontalCenter; source: "logo.svg"; width: 72; height: 72; sourceSize: Qt.size(144, 144) }
            Text { text: "Welcome to X-OS"; color: "#ECEEF1"; font.family: "Inter"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "Beyond Windows. Beyond macOS."; color: "#9AA1AB"; font.family: "Inter"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0C0E" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.55 }
        Column {
            anchors.centerIn: parent; spacing: 16; width: parent.width * 0.78
            Image { anchors.horizontalCenter: parent.horizontalCenter; source: "logo.svg"; width: 72; height: 72; sourceSize: Qt.size(144, 144) }
            Text { text: "Your apps, your way"; color: "#ECEEF1"; font.family: "Inter"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "Firefox is ready. Chrome and other browsers download from their makers' signed servers."; color: "#9AA1AB"; font.family: "Inter"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0C0E" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.55 }
        Column {
            anchors.centerIn: parent; spacing: 16; width: parent.width * 0.78
            Image { anchors.horizontalCenter: parent.horizontalCenter; source: "logo.svg"; width: 72; height: 72; sourceSize: Qt.size(144, 144) }
            Text { text: "Windows programs"; color: "#ECEEF1"; font.family: "Inter"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "Double-click a .exe or .msi file: X-OS tells you how well it runs before anything is installed."; color: "#9AA1AB"; font.family: "Inter"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0C0E" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.55 }
        Column {
            anchors.centerIn: parent; spacing: 16; width: parent.width * 0.78
            Image { anchors.horizontalCenter: parent.horizontalCenter; source: "logo.svg"; width: 72; height: 72; sourceSize: Qt.size(144, 144) }
            Text { text: "Designed to stay calm"; color: "#ECEEF1"; font.family: "Inter"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "A thin menu bar on top, a floating dock below, and Control Center for everything else."; color: "#9AA1AB"; font.family: "Inter"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0B0C0E" }
        Image { anchors.fill: parent; source: "welcome.svg"; fillMode: Image.PreserveAspectCrop; opacity: 0.55 }
        Column {
            anchors.centerIn: parent; spacing: 16; width: parent.width * 0.78
            Image { anchors.horizontalCenter: parent.horizontalCenter; source: "logo.svg"; width: 72; height: 72; sourceSize: Qt.size(144, 144) }
            Text { text: "Two keyboards, one shortcut"; color: "#ECEEF1"; font.family: "Inter"; font.pixelSize: 30; font.weight: Font.DemiBold; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Text { text: "Press Alt + Shift to switch between your keyboard layouts."; color: "#9AA1AB"; font.family: "Inter"; font.pixelSize: 17; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }

    function onActivate() { presentation.currentSlide = 0 }
    function onLeave() { }
}
