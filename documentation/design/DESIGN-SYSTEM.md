# X-OS Design System — "Liquid Glass"

Source of truth for tokens: `ui/theme/tokens.json` (QML: `import XOS.Theme`, singleton `Theme`).
Reference analysis: `REFERENCE-ANALYSIS.md`.

## 1. Colour

Dark is the default. One accent. Solid colours first; translucency only for floating chrome.

| Token | Dark | Light | Use |
|---|---|---|---|
| `bg` | `#0B0C0E` | `#ECEEF1` | desktop fallback, window backgrounds |
| `surface0` | `#121417` | `#F7F8FA` | app canvas |
| `surface1` | `#181B1F` | `#FFFFFF` | cards, lists |
| `surface2` | `#22262B` | `#E3E6EA` | controls, hover fills |
| `glass` | `#181B1F` @ 72 % | `#FAFBFC` @ 72 % | menu bar, dock, popovers |
| `border` | white @ 10 % | black @ 10 % | 1 px hairlines |
| `borderStrong` | white @ 16 % | black @ 16 % | glass rims |
| `text` | `#ECEEF1` | `#15171A` | primary text, glyphs |
| `textDim` | `#9AA1AB` | `#555C66` | secondary |
| `textFaint` | `#5E6570` | `#8A919B` | disabled, placeholders |
| **`accent`** | **`#7A8CFF`** | **`#4A5FE0`** | focus rings, hover glyph tint, indicators, selection |
| `accentDeep` | `#2E3566` | `#DDE2FF` | active circle fill, selected rows |
| `accentGlow` | accent @ 35 % | accent @ 25 % | the only "neon": focus glow, active circle rim |
| `warning` / `danger` / `success` | `#E5B567` / `#E5636B` / `#5FC48A` | darker variants | **semantic states only** (never decoration) |

Rules: no rainbow or multi-hue gradients; gradients only as ≤ 6 % luminance shifts inside one
surface (glass depth); never colour per app; neon (`accentGlow`) only on focus / active / important
state, never as ambient decoration; text contrast ≥ 4.5:1 on its surface (WCAG AA).

## 2. Materials

| Material | Recipe | Fallback (low-resource / software rendering) |
|---|---|---|
| Glass | `glass` fill + compositor background blur (radius 24) + 1 px `borderStrong` rim + 1 px inner top highlight (white @ 6 %) + shadow | solid `surface1`, no blur, rim kept |
| Shadow | 0 8 24 black @ 40 % (dark) / 0 8 24 black @ 12 % (light) | none |
| Active circle | solid `accentDeep`, 1 px `accentGlow` rim, top highlight white @ 10 % | solid `accentDeep` |

Blur is requested from KWin (blur protocol) for shell surfaces; it is never faked by
rendering a blurred copy of the wallpaper in QML (expensive, wrong with windows behind).

## 3. Geometry

4-pt grid. Radii: `xs 6 · sm 10 · md 14 · lg 20 · pill = height/2`.

**The cradle** (shared by menu bar and dock; ratios from the reference):

| Ratio | Value |
|---|---|
| circle diameter / bar height | 0.83 |
| circle centre | 2 px above the bar's top edge (≈ half inside the cradle) |
| gap circle ↔ cradle | 0.07 × bar height (min 4 px) |
| shoulder (fillet) radius | 0.15 × bar height |

Bar sizes: dock 64 px (default; 48–88 configurable), menu bar 34 px, both floating 8 px from the
screen edge.

## 4. Typography

Inter (UI), JetBrains Mono (code/terminal), Vazirmatn (Persian/Arabic fallback).
Scale: 11 caption · 13 body · 15 emphasis · 20 title · 28 display. Weights 400 / 500 / 600.
Menu bar text 13/500. Never below 11 px.

## 5. Iconography

See `icons/xos/ICONS.md`. Line glyphs on a 24-px grid, 1.75 px stroke, round caps/joins,
2-px corner radius on rectangles, optical padding 2 px. Glyphs are monochrome (`text`); state
colour comes from the theme (hover → `accent`, disabled → `textFaint`). App tiles = glyph on a
`surface2` squircle with a 1 px rim — never multi-colour artwork.

## 6. Motion

Context: desktop shell = productivity tool → restraint first (Emil Kowalski lens), production
polish second (Jakub Krehel lens). Only transform/opacity/geometry of shell chrome is animated.

| Token | Duration | Curve (cubic-bezier) | Used for |
|---|---|---|---|
| `instant` | 0 | — | keyboard-initiated changes (Alt+Tab), reduced motion |
| `hover` | 120 ms | (0.2, 0, 0, 1) | glyph tint, rim brighten |
| `fadeOut` | 80 ms | (0.4, 0, 1, 1) | icon leaving the circle (exit subtler than enter) |
| `fadeIn` | 140 ms | (0, 0, 0.2, 1) | icon entering the circle |
| `slide` | 240 ms | (0.32, 0.72, 0, 1) | circle + cradle moving to another item (reference ≈ 270 ms) |
| `launch` | 460 ms | phases in `launchState` (ease-out rise to a peak at 60 %, ease-in-out settle) | droplet pull-out → pinch → settle, on app launch only |
| `popover` | 160 ms in / 100 ms out | (0, 0, 0.2, 1) / (0.4, 0, 1, 1) | menus; scale from 0.96 at the trigger, never from 0 |

Frequency gate: switching apps is frequent → fast slide, no droplet. Launch is rarer → droplet.
No looping, pulsing or breathing indicators anywhere. **Reduced motion** (setting + Plasma
`AnimationDurationFactor = 0`) makes every token `instant`. **Low-resource profile** (LITE)
additionally disables blur and shadows (solid fallbacks above).

## 7. Accessibility

Keyboard: every bar item is focusable (Tab / arrows), focus ring = 2 px `accent` outside the shape.
Screen readers: every item has `Accessible.name`/role. Scaling follows the Plasma scale factor.
Contrast checked against both themes. Nothing is conveyed by colour alone (active = circle + position).

## 8. Window controls (title bar)

KWin Aurorae themes `XOS-Dark` / `XOS-Light`, generated by `scripts/build-decoration.py`
from the tokens (`themes/decoration/`). Placement: **left**, order close · minimize · maximize.

| State | Look |
|---|---|
| Focused window, at rest | three 12 px dots in a quiet neutral (`#3A3F46` dark / `#C9CED4` light): no colour, no glyphs |
| Hover / pressed (per button) | close → `danger` with ×, minimize → `warning` with –, maximize → **X-OS accent** with outward corners (restore: inward corners) |
| Unfocused window | hollow rings; title text `textFaint` |

Why: macOS shows three colours permanently; X-OS keeps the chrome silent until the pointer
asks for it (more minimal), uses its own accent for maximize, and makes the focused window
recognisable at a glance (filled dots vs rings). Title bar = window surface colour, 34 px,
10 px top corners, centred title, 1 px outline. Dark Mode switches the theme live
(`kwriteconfig6` + `org.kde.KWin.reconfigure`).
