// X-OS window tracker (KWin script). Pushes the window list to org.xos.Shell on every change.
// Read-only: it never moves or changes windows. Commands come from the shell as separate
// one-shot scripts (see lib/python/xos/windows.py). The shell loads this script into KWin
// over D-Bus when it starts (org.kde.KWin /Scripting loadScript), so the list is always fresh.

function relevant(w) {
    return w && w.normalWindow && !w.skipTaskbar && w.resourceClass !== "xos-shell";
}

function info(w) {
    return {
        id: w.internalId.toString(),
        caption: w.caption,
        appId: w.desktopFileName || w.resourceClass,
        resourceClass: w.resourceClass,
        minimized: w.minimized,
        pid: w.pid
    };
}

function push() {
    var list = [];
    var all = workspace.windowList();
    for (var i = 0; i < all.length; ++i) {
        if (relevant(all[i])) list.push(info(all[i]));
    }
    var a = workspace.activeWindow;
    callDBus("org.xos.Shell", "/Windows", "org.xos.Shell.Windows", "update",
             JSON.stringify({ windows: list, active: relevant(a) ? a.internalId.toString() : "" }));
}

function watch(w) {
    if (!w) return;
    w.captionChanged.connect(push);
    w.minimizedChanged.connect(push);
}

var existing = workspace.windowList();
for (var i = 0; i < existing.length; ++i) watch(existing[i]);
workspace.windowAdded.connect(function (w) { watch(w); push(); });
workspace.windowRemoved.connect(push);
workspace.windowActivated.connect(push);
push();
