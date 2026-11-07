// X-OS Setup wizard - Liquid Glass, dark by default, RTL-aware.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: win
    width: 1100
    height: 700
    minimumWidth: 900
    minimumHeight: 600
    visible: true
    title: "X-OS Setup"
    color: "#070811"

    required property var backend
    property int startPage: 0
    property string startLocale: ""

    // ------------------------------------------------------------- state
    property string uiLocale: startLocale || "en_US.UTF-8"
    readonly property bool rtl: uiLocale === "fa_IR.UTF-8" || uiLocale === "ar_EG.UTF-8"
    readonly property string lang: uiLocale.slice(0, 2)
    property var keyboard: [{ layout: "us", variant: "", label: "English (US)" }]
    property string theme: "dark"
    property string wallpaper: "nebula-dark"
    property var chosenBrowsers: ["firefox"]
    property string wifiSsid: ""
    property int page: startPage

    LayoutMirroring.enabled: rtl
    LayoutMirroring.childrenInherit: true

    // ------------------------------------------------------------- strings
    readonly property var strings: ({
        en: {
            welcome: "Welcome to X-OS", welcomeSub: "Choose your language to begin.",
            keyboard: "Keyboard", keyboardSub: "Choose up to 4 layouts. Switch between them with Alt + Shift.",
            testHere: "Type here to test your keyboard…",
            wifi: "Connect to the internet", wifiSub: "Needed to download Chrome and updates during installation. You can skip this.",
            refresh: "Refresh", password: "Password", connect: "Connect", connected: "Connected", open: "Open network",
            noWifi: "No Wi-Fi networks found. Wired (Ethernet) connections work automatically.",
            look: "Make it yours", lookSub: "Pick a theme and background. You can change them later in the Control Center.",
            dark: "Dark", light: "Light", auto: "Automatic",
            apps: "Apps", appsSub: "These browsers are downloaded from their makers' official, signed servers while X-OS installs.",
            preinstalled: "Firefox ESR is already included and works offline.",
            from: "from", needsNet: "Needs internet. If offline now, it downloads automatically on first start.",
            ready: "Ready", readySub: "Try X-OS without changing your computer, or install it.",
            tryIt: "Try X-OS", install: "Install X-OS…",
            devWarn: "Development build: not ready for installation on a computer you depend on. Back up your files first. Nothing on your disk changes until you confirm in the installer.",
            back: "Back", next: "Next", skip: "Skip",
            summaryLang: "Language", summaryKb: "Keyboard", summaryNet: "Network", summaryLook: "Appearance", summaryApps: "Browsers",
            none: "Not connected"
        },
        fa: {
            welcome: "به X-OS خوش آمدید", welcomeSub: "برای شروع، زبان خود را انتخاب کنید.",
            keyboard: "صفحه‌کلید", keyboardSub: "تا ۴ چیدمان انتخاب کنید. جابه‌جایی با Alt + Shift.",
            testHere: "برای امتحان صفحه‌کلید اینجا تایپ کنید…",
            wifi: "اتصال به اینترنت", wifiSub: "برای دانلود کروم و به‌روزرسانی‌ها هنگام نصب لازم است. می‌توانید رد کنید.",
            refresh: "تازه‌سازی", password: "رمز عبور", connect: "اتصال", connected: "متصل", open: "شبکهٔ باز",
            noWifi: "شبکهٔ وای‌فای پیدا نشد. اتصال کابلی (اترنت) خودکار کار می‌کند.",
            look: "ظاهر دلخواه", lookSub: "پوسته و پس‌زمینه را انتخاب کنید. بعداً در مرکز کنترل قابل تغییر است.",
            dark: "تیره", light: "روشن", auto: "خودکار",
            apps: "برنامه‌ها", appsSub: "این مرورگرها هنگام نصب X-OS از سرورهای رسمی و امضاشدهٔ سازندگانشان دانلود می‌شوند.",
            preinstalled: "Firefox ESR از قبل نصب است و بدون اینترنت هم کار می‌کند.",
            from: "از", needsNet: "به اینترنت نیاز دارد. اگر الان آفلاین هستید، در اولین روشن شدن خودکار دانلود می‌شود.",
            ready: "آماده", readySub: "X-OS را بدون تغییر در رایانه امتحان کنید، یا نصبش کنید.",
            tryIt: "امتحان X-OS", install: "نصب X-OS…",
            devWarn: "نسخهٔ در حال توسعه: برای نصب روی رایانه‌ای که به آن وابسته‌اید آماده نیست. اول از فایل‌هایتان نسخهٔ پشتیبان بگیرید. تا در نصب‌کننده تأیید نکنید، چیزی روی دیسک تغییر نمی‌کند.",
            back: "قبلی", next: "بعدی", skip: "رد کردن",
            summaryLang: "زبان", summaryKb: "صفحه‌کلید", summaryNet: "شبکه", summaryLook: "ظاهر", summaryApps: "مرورگرها",
            none: "متصل نیست"
        }
    })
    function t(key) {
        const s = strings[lang] || strings.en
        const v = s[key] !== undefined ? s[key] : strings.en[key]
        // Right-to-left mark: Qt picks paragraph direction from the first strong
        // character, so Persian sentences starting with "X-OS" would render LTR.
        return rtl && s[key] !== undefined ? "\u200F" + v : v
    }

    font.family: "Inter"
    font.pixelSize: 15

    // ------------------------------------------------------------- background
    Image {
        anchors.fill: parent
        source: (win.backend.wallpapers.find(w => w.id === win.wallpaper) || {}).url || ""
        fillMode: Image.PreserveAspectCrop
        sourceSize: Qt.size(width, height)
        opacity: 0.9
    }
    Rectangle { anchors.fill: parent; color: win.theme === "light" ? "#20FFFFFF" : "#55000000" }

    readonly property color fg: theme === "light" ? "#151827" : "#EEF0FF"
    readonly property color fgDim: theme === "light" ? "#4A5070" : "#A9B0CF"
    readonly property color accent: "#7C8CFF"

    component Glass: Rectangle {
        radius: 22
        color: win.theme === "light" ? Qt.rgba(1, 1, 1, 0.72) : Qt.rgba(0.11, 0.12, 0.19, 0.78)
        border.color: win.theme === "light" ? Qt.rgba(1, 1, 1, 0.9) : Qt.rgba(1, 1, 1, 0.12)
    }
    component Title: Label { color: win.fg; font.pixelSize: 30; font.weight: Font.DemiBold; Layout.fillWidth: true; wrapMode: Text.Wrap }
    component Sub: Label { color: win.fgDim; font.pixelSize: 15; Layout.fillWidth: true; wrapMode: Text.Wrap }
    component Choice: Rectangle {
        id: ch
        property bool selected: false
        property alias text: lbl.text
        property string detail: ""
        signal picked()
        Layout.fillWidth: true
        implicitHeight: 52
        radius: 14
        color: selected ? Qt.rgba(0.49, 0.55, 1, 0.28) : (ma.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(1, 1, 1, 0.03))
        border.color: selected ? win.accent : Qt.rgba(1, 1, 1, 0.08)
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
            Label { id: lbl; color: win.fg; font.pixelSize: 16; Layout.fillWidth: true }
            Label { text: ch.detail; color: win.fgDim; font.pixelSize: 13 }
            Label { text: ch.selected ? "✓" : ""; color: win.accent; font.pixelSize: 18 }
        }
        MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: ch.picked() }
        Accessible.role: Accessible.RadioButton
        Accessible.name: lbl.text
    }
    component PrimaryButton: Button {
        id: pb
        contentItem: Label { text: pb.text; color: "white"; font.pixelSize: 15; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle {
            implicitWidth: 140; implicitHeight: 44; radius: 22
            gradient: Gradient { orientation: Gradient.Horizontal
                GradientStop { position: 0; color: pb.enabled ? "#6F7EFF" : "#555A70" }
                GradientStop { position: 1; color: pb.enabled ? "#A46BFF" : "#555A70" } }
            opacity: pb.down ? 0.8 : 1
        }
    }
    component GhostButton: Button {
        id: gb
        contentItem: Label { text: gb.text; color: win.fg; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { implicitWidth: 120; implicitHeight: 44; radius: 22; color: gb.hovered ? Qt.rgba(1, 1, 1, 0.10) : "transparent"; border.color: Qt.rgba(1, 1, 1, 0.18) }
    }

    // ------------------------------------------------------------- layout
    RowLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 24

        // Step rail
        Glass {
            Layout.preferredWidth: 230
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 6
                Image { source: win.backend.logo; sourceSize: Qt.size(64, 64); Layout.preferredWidth: 56; Layout.preferredHeight: 56 }
                Label { text: "X-OS"; color: win.fg; font.pixelSize: 22; font.weight: Font.Bold; Layout.bottomMargin: 18 }
                Repeater {
                    model: ["welcome", "keyboard", "wifi", "look", "apps", "ready"]
                    delegate: RowLayout {
                        required property string modelData
                        required property int index
                        spacing: 10
                        Layout.fillWidth: true
                        Rectangle {
                            width: 26; height: 26; radius: 13
                            color: index < win.page ? win.accent : (index === win.page ? Qt.rgba(0.49, 0.55, 1, 0.35) : "transparent")
                            border.color: index <= win.page ? win.accent : Qt.rgba(1, 1, 1, 0.2)
                            Label { anchors.centerIn: parent; text: index < win.page ? "✓" : (index + 1); color: win.fg; font.pixelSize: 12 }
                        }
                        Label {
                            text: win.t(modelData === "welcome" ? "summaryLang" : modelData === "look" ? "summaryLook" : modelData)
                            color: index === win.page ? win.fg : win.fgDim
                            font.weight: index === win.page ? Font.DemiBold : Font.Normal
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Label { visible: win.backend.demo; text: "DEMO MODE"; color: "#FFB86B"; font.pixelSize: 11 }
            }
        }

        // Page area
        Glass {
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 36
                spacing: 18

                StackLayout {
                    id: stack
                    currentIndex: win.page
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    // 0 Language
                    ColumnLayout {
                        spacing: 14
                        Title { text: win.t("welcome") }
                        Sub { text: win.t("welcomeSub") }
                        GridLayout {
                            columns: 2; columnSpacing: 10; rowSpacing: 10; Layout.fillWidth: true; Layout.topMargin: 10
                            Repeater {
                                model: win.backend.languages
                                Choice {
                                    required property var modelData
                                    text: modelData.name
                                    selected: win.uiLocale === modelData.locale
                                    onPicked: win.uiLocale = modelData.locale
                                }
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }

                    // 1 Keyboard
                    ColumnLayout {
                        spacing: 12
                        Title { text: win.t("keyboard") }
                        Sub { text: win.t("keyboardSub") }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            ColumnLayout {
                                width: parent.width; spacing: 8
                                Repeater {
                                    model: win.backend.keyboards
                                    Choice {
                                        required property var modelData
                                        text: modelData.label
                                        detail: modelData.layout + (modelData.variant ? " · " + modelData.variant : "")
                                        selected: win.keyboard.some(k => k.layout === modelData.layout && k.variant === modelData.variant)
                                        onPicked: {
                                            let ks = win.keyboard.filter(k => !(k.layout === modelData.layout && k.variant === modelData.variant))
                                            if (ks.length === win.keyboard.length && ks.length < 4) ks.push(modelData)
                                            if (ks.length > 0) { win.keyboard = ks; win.backend.applyKeyboard(ks) }
                                        }
                                    }
                                }
                            }
                        }
                        TextField {
                            Layout.fillWidth: true
                            placeholderText: win.t("testHere")
                            color: win.fg; placeholderTextColor: win.fgDim
                            background: Rectangle { radius: 12; color: Qt.rgba(1, 1, 1, 0.06); border.color: Qt.rgba(1, 1, 1, 0.15); implicitHeight: 44 }
                        }
                    }

                    // 2 Wi-Fi
                    ColumnLayout {
                        id: wifiPage
                        spacing: 12
                        property string selected: ""
                        property string error: ""
                        Component.onCompleted: win.backend.scanWifi()
                        RowLayout {
                            Layout.fillWidth: true
                            Title { text: win.t("wifi") }
                            GhostButton { text: win.t("refresh"); onClicked: win.backend.scanWifi() }
                        }
                        Sub { text: win.t("wifiSub") }
                        Sub { visible: win.backend.wifi.length === 0; text: win.t("noWifi") }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            ColumnLayout {
                                width: parent.width; spacing: 8
                                Repeater {
                                    model: win.backend.wifi
                                    Choice {
                                        required property var modelData
                                        text: modelData.ssid
                                        detail: (modelData.connected ? win.t("connected") + "   " : "")
                                                + (modelData.secure ? modelData.security.split(" ")[0] : win.t("open"))
                                                + "   " + modelData.signal + "%"
                                        selected: modelData.connected || wifiPage.selected === modelData.ssid
                                        onPicked: { wifiPage.selected = modelData.ssid; wifiPage.error = ""; pw.text = "" }
                                    }
                                }
                            }
                        }
                        RowLayout {
                            visible: wifiPage.selected !== ""
                            Layout.fillWidth: true
                            spacing: 10
                            TextField {
                                id: pw
                                Layout.fillWidth: true
                                echoMode: TextInput.Password
                                visible: (win.backend.wifi.find(n => n.ssid === wifiPage.selected) || {}).secure === true
                                placeholderText: win.t("password") + " — " + wifiPage.selected
                                color: win.fg; placeholderTextColor: win.fgDim
                                background: Rectangle { radius: 12; color: Qt.rgba(1, 1, 1, 0.06); border.color: Qt.rgba(1, 1, 1, 0.15); implicitHeight: 44 }
                                onAccepted: connectBtn.clicked()
                            }
                            PrimaryButton {
                                id: connectBtn
                                text: win.t("connect")
                                onClicked: {
                                    wifiPage.error = win.backend.connectWifi(wifiPage.selected, pw.text)
                                    pw.text = ""
                                    if (wifiPage.error === "") win.wifiSsid = wifiPage.selected
                                }
                            }
                        }
                        Label { visible: wifiPage.error !== ""; text: wifiPage.error; color: "#FF7A90"; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    }

                    // 3 Appearance
                    ColumnLayout {
                        spacing: 14
                        Title { text: win.t("look") }
                        Sub { text: win.t("lookSub") }
                        RowLayout {
                            spacing: 18; Layout.topMargin: 8
                            Repeater {
                                model: [{ id: "dark", wp: "nebula-dark" }, { id: "light", wp: "nebula-light" }, { id: "auto", wp: "nebula-dark" }]
                                ColumnLayout {
                                    required property var modelData
                                    spacing: 8
                                    Rectangle {
                                        Layout.preferredWidth: 220; Layout.preferredHeight: 138; radius: 16; clip: true
                                        color: "transparent"
                                        border.width: win.theme === modelData.id ? 3 : 1
                                        border.color: win.theme === modelData.id ? win.accent : Qt.rgba(1, 1, 1, 0.15)
                                        Image {
                                            anchors.fill: parent; anchors.margins: 3
                                            source: (win.backend.wallpapers.find(w => w.id === modelData.wp) || {}).url || ""
                                            sourceSize: Qt.size(440, 276); fillMode: Image.PreserveAspectCrop
                                        }
                                        Rectangle {   // mini dock
                                            anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 10
                                            width: 110; height: 16; radius: 8
                                            color: modelData.id === "light" ? Qt.rgba(1, 1, 1, 0.7) : Qt.rgba(0.12, 0.13, 0.2, 0.8)
                                        }
                                        MouseArea {
                                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: { win.theme = modelData.id; win.wallpaper = modelData.wp; win.backend.applyAppearance(win.theme, win.wallpaper) }
                                        }
                                    }
                                    Label { text: win.t(modelData.id); color: win.fg; Layout.alignment: Qt.AlignHCenter }
                                }
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }

                    // 4 Apps
                    ColumnLayout {
                        spacing: 12
                        Title { text: win.t("apps") }
                        Sub { text: win.t("appsSub") }
                        Repeater {
                            model: win.backend.browserList
                            Choice {
                                required property var modelData
                                text: modelData.name
                                detail: win.t("from") + " " + modelData.source
                                selected: win.chosenBrowsers.indexOf(modelData.id) >= 0
                                onPicked: {
                                    const b = win.chosenBrowsers.slice(), i = b.indexOf(modelData.id)
                                    if (i >= 0) b.splice(i, 1); else b.push(modelData.id)
                                    win.chosenBrowsers = b
                                }
                            }
                        }
                        Sub { text: "• " + win.t("preinstalled") + "\n• " + win.t("needsNet") }
                        Item { Layout.fillHeight: true }
                    }

                    // 5 Ready
                    ColumnLayout {
                        spacing: 14
                        Title { text: win.t("ready") }
                        Sub { text: win.t("readySub") }
                        GridLayout {
                            columns: 2; columnSpacing: 24; rowSpacing: 8; Layout.topMargin: 6
                            Label { text: win.t("summaryLang"); color: win.fgDim }
                            Label { text: (win.backend.languages.find(l => l.locale === win.uiLocale) || {}).name || ""; color: win.fg }
                            Label { text: win.t("summaryKb"); color: win.fgDim }
                            Label { text: win.keyboard.map(k => k.label).join(", "); color: win.fg }
                            Label { text: win.t("summaryNet"); color: win.fgDim }
                            Label { text: win.wifiSsid || win.t("none"); color: win.fg }
                            Label { text: win.t("summaryLook"); color: win.fgDim }
                            Label { text: win.t(win.theme); color: win.fg }
                            Label { text: win.t("summaryApps"); color: win.fgDim }
                            Label { text: win.chosenBrowsers.map(id => (win.backend.browserList.find(b => b.id === id) || {}).name).join(", ") || "—"; color: win.fg }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.topMargin: 8
                            implicitHeight: warn.implicitHeight + 24; radius: 14
                            color: Qt.rgba(1, 0.72, 0.42, 0.12); border.color: Qt.rgba(1, 0.72, 0.42, 0.5)
                            Label { id: warn; anchors.fill: parent; anchors.margins: 12; text: "⚠  " + win.t("devWarn"); color: win.fg; wrapMode: Text.Wrap }
                        }
                        Label { id: finishError; color: "#FF7A90"; visible: text !== ""; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            spacing: 14
                            GhostButton { text: win.t("tryIt"); onClicked: { finishError.text = win.finish(); if (!finishError.text) win.backend.tryXos() } }
                            PrimaryButton { text: win.t("install"); onClicked: { finishError.text = win.finish() || win.backend.startInstaller() } }
                        }
                    }
                }

                // Navigation
                RowLayout {
                    Layout.fillWidth: true
                    visible: win.page < 5
                    GhostButton { text: win.t("back"); visible: win.page > 0; onClicked: win.page-- }
                    Item { Layout.fillWidth: true }
                    GhostButton { text: win.t("skip"); visible: win.page === 2; onClicked: win.page++ }
                    PrimaryButton { text: win.t("next"); onClicked: win.page++ }
                }
            }
        }
    }

    function finish() {
        return backend.save({ locale: uiLocale, keyboard: keyboard, theme: theme, wallpaper: wallpaper,
                              browsers: chosenBrowsers, wifiSsid: wifiSsid })
    }
}
