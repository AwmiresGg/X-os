// X-OS default desktop layout: wallpaper only. The menu bar and the dock are drawn by
// xos-shell (layer-shell surfaces), so no Plasma panel is created.
var all = desktops();
for (var i = 0; i < all.length; ++i) {
    var d = all[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file:///usr/share/wallpapers/X-OS/x-os-dark.svg");
}
