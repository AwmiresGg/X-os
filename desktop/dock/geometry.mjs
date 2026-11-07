// X-OS Signature Dock - geometry engine.
//
// Must stay within the JavaScript subset of Qt's V4 engine: no object spread,
// no optional chaining, no `**`.
//
// Pure functions (no Qt dependency) shared by the QML dock (imported as an
// ECMAScript module) and the Node unit tests in testing/unit/dock.test.mjs.
//
// Coordinate system: dock-local, origin at the top-left of the dock body,
// y grows downward (screen convention). The flat top edge is y = 0.
//
// The active icon floats in a glass circle of radius r centred at (cx, -lift).
// The dock surface below it is carved by a concave "notch" circle of radius
// N = r + gap, concentric with the floating circle when fully active, so the
// gap between icon and dock is uniform. The notch meets the flat top edge
// through two convex fillet arcs (radius f) that are tangent to both the edge
// and the notch circle, which makes the outline tangent-continuous (G1): the
// surface "flows" around the icon instead of showing a hard cut.

export const DEFAULTS = Object.freeze({
    iconSize: 48,        // icon glyph size
    containerPad: 6,     // glass circle padding around the glyph
    spacing: 14,         // gap between neighbouring icon containers
    padding: 16,         // horizontal padding inside the dock body
    height: 68,          // dock body height
    gap: 6,              // gap between floating circle and carved surface
    lift: 12,            // how far the active circle centre rises above the top edge
    fillet: 10,          // shoulder radius where the notch meets the top edge
    cornerRadius: 26,    // dock body corner radius
});

export function containerRadius(o = DEFAULTS) {
    return o.iconSize / 2 + o.containerPad;
}

/** Horizontal layout: centre x of every icon slot and total dock width. */
export function layout(count, o = DEFAULTS) {
    const d = 2 * containerRadius(o);
    const pitch = d + o.spacing;
    const width = count > 0 ? 2 * o.padding + count * d + (count - 1) * o.spacing : 2 * o.padding + d;
    const xs = [];
    for (let i = 0; i < count; i++) xs.push(o.padding + d / 2 + i * pitch);
    return { width, xs, pitch, diameter: d };
}

export function clamp(v, lo, hi) {
    return Math.min(hi, Math.max(lo, v));
}

/** Smooth 0..1 easing used for depth (C1 continuous at both ends). */
export function smoothstep(t) {
    t = clamp(t, 0, 1);
    return t * t * (3 - 2 * t);
}

/**
 * Notch geometry for activation amount t in [0, 1].
 * Returns null when the notch is too shallow to draw (flat edge).
 */
export function notch(cx, t, o = DEFAULTS) {
    const r = containerRadius(o);
    const N = r + o.gap;
    const f = o.fillet;
    // The opening width (not the depth) is driven by the eased activation, then the
    // depth that produces it is solved for. Driving depth directly would make the
    // width grow like sqrt(depth) and the notch would visibly "pop" open.
    const R = N + f;
    const fullDepth = N - o.lift;                  // lowest point of the carve when active
    const fullDx = Math.sqrt(R * R - (R - fullDepth) * (R - fullDepth));
    const w = fullDx * smoothstep(t);
    const depth = R - Math.sqrt(Math.max(0, R * R - w * w));
    if (w < 0.5) return null;                      // sub-pixel opening: draw a flat edge
    const cy = depth - N;                          // notch circle centre (above edge while lift > 0)
    const dy = N + f - depth;                      // vertical distance fillet centre -> notch centre
    const dx = Math.sqrt(Math.max(0, (N + f) * (N + f) - dy * dy));
    const k = f / (N + f);                         // tangent point between fillet and notch
    const tl = { x: (cx - dx) + (dx) * k, y: f + (cy - f) * k };
    const tr = { x: (cx + dx) - (dx) * k, y: tl.y };
    return { cx, cy, N, f, depth, dx, tl, tr, left: cx - dx, right: cx + dx };
}

/** Centre of the floating circle for activation t (rest position is the dock's middle). */
export function floatingCentre(t, o = DEFAULTS) {
    const rest = o.height / 2;
    return rest + (-o.lift - rest) * smoothstep(t);
}

/**
 * How much an icon at x should rise while the notch (at notchX) slides past.
 * Gives the "liquid" hand-over between icons when the active app changes.
 */
export function iconActivation(x, notchX, t, pitch) {
    const dist = Math.abs(x - notchX) / pitch;
    return clamp(1 - dist, 0, 1) * clamp(t, 0, 1);
}

const fmt = (v) => (Math.round(v * 100) / 100).toString();

/**
 * SVG path of the dock body with zero or one notch.
 * Usable directly by QML PathSvg and by browsers for previews.
 */
export function dockPath(width, n, o = DEFAULTS) {
    const h = o.height;
    const rc = Math.min(o.cornerRadius, h / 2, width / 2);
    const p = [];
    p.push(`M ${fmt(rc)} 0`);
    if (n) {
        // Keep the notch inside the straight part of the top edge.
        const left = Math.max(n.left, rc);
        const right = Math.min(n.right, width - rc);
        if (left !== n.left || right !== n.right) {
            // Notch would touch a rounded corner: draw it clipped but still tangent-safe.
            n = Object.assign({}, n, { left: left, right: right });
        }
        p.push(`L ${fmt(n.left)} 0`);
        // left fillet: convex shoulder, clockwise on screen
        p.push(`A ${fmt(n.f)} ${fmt(n.f)} 0 0 1 ${fmt(n.tl.x)} ${fmt(n.tl.y)}`);
        // notch: concave arc under the floating circle, counter-clockwise
        p.push(`A ${fmt(n.N)} ${fmt(n.N)} 0 0 0 ${fmt(n.tr.x)} ${fmt(n.tr.y)}`);
        // right fillet
        p.push(`A ${fmt(n.f)} ${fmt(n.f)} 0 0 1 ${fmt(n.right)} 0`);
    }
    p.push(`L ${fmt(width - rc)} 0`);
    p.push(`A ${fmt(rc)} ${fmt(rc)} 0 0 1 ${fmt(width)} ${fmt(rc)}`);
    p.push(`L ${fmt(width)} ${fmt(h - rc)}`);
    p.push(`A ${fmt(rc)} ${fmt(rc)} 0 0 1 ${fmt(width - rc)} ${fmt(h)}`);
    p.push(`L ${fmt(rc)} ${fmt(h)}`);
    p.push(`A ${fmt(rc)} ${fmt(rc)} 0 0 1 0 ${fmt(h - rc)}`);
    p.push(`L 0 ${fmt(rc)}`);
    p.push(`A ${fmt(rc)} ${fmt(rc)} 0 0 1 ${fmt(rc)} 0`);
    p.push("Z");
    return p.join(" ");
}

/** Minimum gap between the floating circle and the carved surface (for tests/diagnostics). */
export function surfaceGap(n, circleY, o = DEFAULTS) {
    if (!n) return Infinity;
    const r = containerRadius(o);
    const distCentres = Math.abs(circleY - n.cy);
    return n.N - (distCentres + r);
}
