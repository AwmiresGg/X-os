# Reference Video Analysis (menu bar + dock)

Source: the user's reference video (Google Drive, `1UVStELuXunRVWDKgRbtnn9pRC4Arrgcj`),
downloaded 2026-11-07: QuickTime/HEVC, 720×708, 30 fps, 167 frames, 5.57 s.
Analysed frame by frame (contact sheets of every 4th frame, full-resolution crops of
frames 60, 85, 100, 118, 123, 128, 134). The frames themselves are not committed
(third-party content); this document records what they show.

The video shows **two bar concepts** (plus a code-editor panel that is not part of the design).

## Concept 1 — dark bar with a cradled active circle (top of the frame)

| Aspect | Observation |
|---|---|
| Shape | Floating pill, fully rounded ends, dark smoky glass, ~1 px light border (~25–30 % white), soft inner lightening |
| Items | 5 thin-stroke white line icons (home, heart, plus-in-circle, person, bell), no containers, evenly spaced |
| Active state | Icon sits in a **solid deep-teal circle** with a faint top highlight; icon white |
| Geometry | Circle diameter ≈ 0.83 × bar height; circle centre ≈ on the bar's top edge (≈ half the circle inside); the bar's top edge dips into a **concave cradle** concentric with the circle, leaving a **visible gap** ≈ 0.07 × bar height; shoulders are smooth (no corners). When the active item is the first one, the cradle cuts into the rounded end and the end curls up like a lip |
| Hover | Hovered icon's stroke turns **teal** (frames 76–80, 100) — no scale, no background |
| Switching | On click the circle **detaches and slides** to the target (≈ 8 frames ≈ 270 ms); the cradle travels with it; the icon inside fades out during travel and the target icon fades in on arrival; the previous icon returns to the bar in grey, then white |
| Extra | A thin centred "home indicator" line under the items |

## Concept 2 — light frosted tab bar with a liquid droplet (middle of the frame)

| Aspect | Observation |
|---|---|
| Shape | Floating pill, warm translucent frosted glass, thin light border |
| Items | Icon + label (Home, Likes, Add, Profile, Alerts); dark line icons; active = **small dot** under the label |
| Selection | The selected icon **pulls up out of the bar through a stretching neck** (metaball/"gooey" join, f≈118–123), **pinches off** into a floating droplet (f≈128), then **falls back and merges** into the bar (f≈132–134); the label stays in the bar; the dot moves to the new tab |
| Bar | Squeezes narrower (~10 %) while the droplet is out, then relaxes back (elastic) |
| Tint | The glass tint drifts warm → pink between selections |

## How X-OS combines them (one design, not two bars)

* **One geometry, used twice.** The *cradle* (concept 1) is the X-OS signature for "this is
  active" in both the **menu bar** (top) and the **dock** (bottom). Same circle/gap/shoulder
  ratios, same teal circle, same slide timing.
* **One liquid behaviour.** The *droplet* (concept 2) is how an item **enters** the cradle:
  when an app is launched its icon pulls out of the dock through a neck, separates, and
  settles into the circle above the cradle. Switching between already-running apps uses the
  faster concept-1 slide. (Frequent actions stay fast; the expressive motion is kept for the
  rarer launch — see DESIGN-SYSTEM.md › Motion.)
* **Menu bar mapping.** The left end holds the X-OS system menu in the cradled circle
  (exactly concept 1's "first item active" pose). Opening a status menu (network, sound,
  battery, notifications, Control Center) slides the circle to that item while its popover is
  open, and back to the X-OS mark when it closes — the circle always marks "where you are".
* **Dock mapping.** Line-icon glyphs on dark glass (concept 1 look), optional labels and the
  running/active **dot** (concept 2), cradle + circle for the focused app.
* **One accent.** Concept 1's teal becomes the single X-OS accent. Concept 2's warm/pink
  tint drift is *not* adopted (it would add competing colours).
