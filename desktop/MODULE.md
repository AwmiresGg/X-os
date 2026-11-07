# desktop

**Status:** In progress: Signature Dock component + geometry engine (unit-tested); top bar, launcher, shell integration not started

**Dependencies:** Qt 6.5+ (QtQuick.Shapes, QtQuick.Effects), KWin, Plasma 6, LayerShellQt (planned)

**Tests:** testing/unit/dock.test.mjs (geometry); offscreen render of desktop/dock/demo

**Known issues / limitations:**
- Dock runs as a standalone QML component/preview; not yet a Plasma panel/layer-shell surface, so it does not yet track real windows.
- Background blur needs KWin's blur protocol once it is a shell surface; standalone preview shows translucency only.
- Grouped-window preview lists titles; live thumbnails need KWin's window-thumbnail item.
- Drag-and-drop reordering, dock position (left/right) and settings UI not implemented.

**Acceptance criteria:**
- [ ] Concave liquid notch with uniform gap (unit-tested)
- [ ] Persistent active state and smooth hand-over
- [ ] 60 FPS on Intel/AMD iGPU measured on hardware
- [ ] Static rendering path under software rendering

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
