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

/**
 * The dock outline as a polygon (array of [x, y]) for the compositor's blur region, so the
 * blur follows the cradle instead of a rectangle. Arcs are sampled every `step` px of arc length.
 */
export function dockPolygon(width, n, o = DEFAULTS, step = 4) {
    const h = o.height;
    const rc = Math.min(o.cornerRadius, h / 2, width / 2);
    const pts = [];
    function arc(cx, cy, r, a0, a1) {
        const segs = Math.max(2, Math.ceil(Math.abs(a1 - a0) * r / step));
        for (let i = 0; i <= segs; i++) {
            const a = a0 + (a1 - a0) * i / segs;
            pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
        }
    }
    // top-left corner, from the left edge up to the top edge
    arc(rc, rc, rc, Math.PI, 1.5 * Math.PI);
    if (n && n.left >= rc && n.right <= width - rc) {
        const fl = { x: n.left, y: n.f }, fr = { x: n.right, y: n.f };
        // left fillet: from straight up (-90 deg) towards the notch centre
        arc(fl.x, fl.y, n.f, -0.5 * Math.PI, Math.atan2(n.tl.y - fl.y, n.tl.x - fl.x));
        // notch: around the bottom of the notch circle, counter-clockwise on screen
        const a0 = Math.atan2(n.tl.y - n.cy, n.tl.x - n.cx);
        const a1 = Math.atan2(n.tr.y - n.cy, n.tr.x - n.cx);
        arc(n.cx, n.cy, n.N, a0, a1 < a0 ? a1 : a1 - 2 * Math.PI);
        arc(fr.x, fr.y, n.f, Math.atan2(n.tr.y - fr.y, n.tr.x - fr.x), -0.5 * Math.PI);
    }
    arc(width - rc, rc, rc, 1.5 * Math.PI, 2 * Math.PI);
    arc(width - rc, h - rc, rc, 0, 0.5 * Math.PI);
    arc(rc, h - rc, rc, 0.5 * Math.PI, Math.PI);
    return pts.map(([x, y]) => [Math.round(x * 10) / 10, Math.round(y * 10) / 10]);
}

// ======================================================================== launch droplet
// When an app opens, its icon pulls out of the dock as a liquid droplet (the reference
// video's metaball behaviour), pinches off, floats, and settles into the active circle
// while the cradle opens under it. The surface is the smooth union of the icon circle
// and the dock's top edge; its outline is traced with marching squares, so the neck,
// the pinch-off and the separated droplet all come from one field (no special cases).

/** Polynomial smooth minimum (Inigo Quilez). k = blend radius; k <= 0 is a hard min. */
export function smin(a, b, k) {
    if (k <= 0) return Math.min(a, b);
    const h = Math.max(k - Math.abs(a - b), 0) / k;
    return Math.min(a, b) - h * h * k * 0.25;
}

/**
 * Outline of the union of a circle (cx, cy, R) and the half-plane y >= 0, blended by k,
 * inside the box [x0, x1] x [y0, y1]. Returns { edge, loops }:
 *   edge  - polyline entering at the left border and leaving at the right (left to right),
 *           replacing the straight top edge of the dock over that range;
 *   loops - closed outlines not attached to the edge (the detached droplet).
 */
export function gooContour(cx, cy, R, k, x0, x1, y0, y1, step) {
    step = step || 1.5;
    const nx = Math.max(2, Math.ceil((x1 - x0) / step));
    const ny = Math.max(2, Math.ceil((y1 - y0) / step));
    const sx = (x1 - x0) / nx, sy = (y1 - y0) / ny;
    const v = new Array((nx + 1) * (ny + 1));
    function field(x, y) {
        const dx = x - cx, dy = y - cy;
        return smin(Math.sqrt(dx * dx + dy * dy) - R, -y, k);
    }
    for (let j = 0; j <= ny; j++)
        for (let i = 0; i <= nx; i++)
            v[j * (nx + 1) + i] = field(x0 + i * sx, y0 + j * sy);
    const V = function (i, j) { return v[j * (nx + 1) + i]; };
    const hCount = nx * (ny + 1);
    const pts = {};
    // edge ids: horizontal (i,j)-(i+1,j) -> j*nx+i ; vertical (i,j)-(i,j+1) -> hCount + j*(nx+1)+i
    function hEdge(i, j) {
        const id = j * nx + i;
        if (!(id in pts)) {
            const a = V(i, j), b = V(i + 1, j), t = a / (a - b);
            pts[id] = [x0 + (i + t) * sx, y0 + j * sy];
        }
        return id;
    }
    function vEdge(i, j) {
        const id = hCount + j * (nx + 1) + i;
        if (!(id in pts)) {
            const a = V(i, j), b = V(i, j + 1), t = a / (a - b);
            pts[id] = [x0 + i * sx, y0 + (j + t) * sy];
        }
        return id;
    }
    const segs = [];
    for (let j = 0; j < ny; j++) {
        for (let i = 0; i < nx; i++) {
            const a = V(i, j) < 0, b = V(i + 1, j) < 0, c = V(i + 1, j + 1) < 0, d = V(i, j + 1) < 0;
            const T = a !== b, Rt = b !== c, B = d !== c, L = a !== d;
            const n = (T ? 1 : 0) + (Rt ? 1 : 0) + (B ? 1 : 0) + (L ? 1 : 0);
            if (n === 0) continue;
            if (n === 2) {
                const e = [];
                if (T) e.push(hEdge(i, j));
                if (Rt) e.push(vEdge(i + 1, j));
                if (B) e.push(hEdge(i, j + 1));
                if (L) e.push(vEdge(i, j));
                segs.push(e);
            } else {           // saddle: decide with the cell centre
                const centre = field(x0 + (i + 0.5) * sx, y0 + (j + 0.5) * sy) < 0;
                const top = hEdge(i, j), right = vEdge(i + 1, j), bottom = hEdge(i, j + 1), left = vEdge(i, j);
                if ((a && centre) || (!a && !centre)) { segs.push([top, right]); segs.push([bottom, left]); }
                else { segs.push([top, left]); segs.push([right, bottom]); }
            }
        }
    }
    const at = {};
    for (let s = 0; s < segs.length; s++)
        for (let q = 0; q < 2; q++) (at[segs[s][q]] = at[segs[s][q]] || []).push(s);
    const used = new Array(segs.length);
    function walk(startKey, s0) {
        const line = [pts[startKey]];
        let cur = startKey, s = s0;
        while (s !== undefined) {
            used[s] = true;
            const next = segs[s][0] === cur ? segs[s][1] : segs[s][0];
            line.push(pts[next]);
            cur = next;
            s = undefined;
            const cand = at[cur] || [];
            for (let c = 0; c < cand.length; c++) if (!used[cand[c]]) { s = cand[c]; break; }
        }
        return line;
    }
    let edge = null;
    const loops = [];
    for (const key in at) {                 // open chains start on the box border
        const list = at[key];
        if (list.length === 1 && !used[list[0]]) {
            const line = walk(Number(key), list[0]);
            if (!edge || line.length > edge.length) edge = line;
        }
    }
    for (let s = 0; s < segs.length; s++)
        if (!used[s]) loops.push(walk(segs[s][0], s));
    if (edge && edge[0][0] > edge[edge.length - 1][0]) edge.reverse();
    return { edge: edge || [], loops: loops };
}

function easeOutCubic(u) { u = clamp(u, 0, 1); return 1 - (1 - u) * (1 - u) * (1 - u); }
function easeInOutCubic(u) {
    u = clamp(u, 0, 1);
    return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
}

/**
 * Everything the dock draws during a launch, for progress p in [0, 1]:
 *   cy       droplet centre (dock-local, < 0 is above the bar)
 *   k        blend radius (liquid neck); fades to 0 before the descent so the droplet
 *            settles into the cradle instead of merging back into the bar
 *   goo      true while the outline comes from the field (neck / pinch-off / float)
 *   notchT   cradle opening under the descending droplet
 *   accent   accent-circle opacity (fades in as the droplet arrives)
 *   tile     opacity of the app's tile left in the bar (ends at the normal "active" 0.25)
 *   oldT     closing progress of the previous app's cradle (1 = still open)
 */
export const LAUNCH = Object.freeze({ peakAt: 0.6, kFadeStart: 0.5, kFadeEnd: 0.64, gooEnd: 0.66 });

export function launchState(p, o = DEFAULTS) {
    p = clamp(p, 0, 1);
    const R = containerRadius(o);
    const cy0 = o.height / 2, peak = -1.75 * R, cyf = floatingCentre(1, o);   // starts at the icon's rest position
    const cy = p <= LAUNCH.peakAt
        ? cy0 + (peak - cy0) * easeOutCubic(p / LAUNCH.peakAt)
        : peak + (cyf - peak) * easeInOutCubic((p - LAUNCH.peakAt) / (1 - LAUNCH.peakAt));
    const kf = clamp((p - LAUNCH.kFadeStart) / (LAUNCH.kFadeEnd - LAUNCH.kFadeStart), 0, 1);
    return {
        cy: cy,
        R: R,
        // ramps in so the first frame is the flat bar (no jump), fades before the descent
        k: 0.9 * R * smoothstep(p / 0.15) * (1 - kf),
        goo: p < LAUNCH.gooEnd,
        // the cradle opens ahead of the falling droplet (fully open at p = gooEnd + 0.16)
        notchT: smoothstep((p - LAUNCH.gooEnd) / 0.16),
        accent: smoothstep((p - 0.8) / 0.2),
        tile: 0.25 + 0.75 * (1 - smoothstep(p / 0.15)),
        oldT: 1 - smoothstep(p / 0.3),
    };
}

/**
 * Dock outline with any number of top-edge features, sorted by x:
 *   { notch: <notch()> }            a cradle
 *   { edge: [[x, y], ...] }         a polyline replacing the top edge (droplet neck)
 * plus extra closed loops (detached droplet) as separate subpaths.
 */
export function dockPathFeatures(width, features, loops, o = DEFAULTS) {
    const h = o.height;
    const rc = Math.min(o.cornerRadius, h / 2, width / 2);
    const p = ["M " + fmt(rc) + " 0"];
    const fs = features.filter(function (f) { return f && (f.notch || (f.edge && f.edge.length)); }).sort(function (a, b) {
        const xa = a.notch ? a.notch.left : a.edge[0][0];
        const xb = b.notch ? b.notch.left : b.edge[0][0];
        return xa - xb;
    });
    for (let i = 0; i < fs.length; i++) {
        const f = fs[i];
        if (f.notch) {
            const n = f.notch;
            p.push("L " + fmt(n.left) + " 0");
            p.push("A " + fmt(n.f) + " " + fmt(n.f) + " 0 0 1 " + fmt(n.tl.x) + " " + fmt(n.tl.y));
            p.push("A " + fmt(n.N) + " " + fmt(n.N) + " 0 0 0 " + fmt(n.tr.x) + " " + fmt(n.tr.y));
            p.push("A " + fmt(n.f) + " " + fmt(n.f) + " 0 0 1 " + fmt(n.right) + " 0");
        } else if (f.edge.length) {
            for (let k = 0; k < f.edge.length; k++) p.push("L " + fmt(f.edge[k][0]) + " " + fmt(f.edge[k][1]));
        }
    }
    p.push("L " + fmt(width - rc) + " 0");
    p.push("A " + fmt(rc) + " " + fmt(rc) + " 0 0 1 " + fmt(width) + " " + fmt(rc));
    p.push("L " + fmt(width) + " " + fmt(h - rc));
    p.push("A " + fmt(rc) + " " + fmt(rc) + " 0 0 1 " + fmt(width - rc) + " " + fmt(h));
    p.push("L " + fmt(rc) + " " + fmt(h));
    p.push("A " + fmt(rc) + " " + fmt(rc) + " 0 0 1 0 " + fmt(h - rc));
    p.push("L 0 " + fmt(rc));
    p.push("A " + fmt(rc) + " " + fmt(rc) + " 0 0 1 " + fmt(rc) + " 0");
    p.push("Z");
    for (let l = 0; l < (loops || []).length; l++) {
        const loop = loops[l];
        if (loop.length < 3) continue;
        p.push("M " + fmt(loop[0][0]) + " " + fmt(loop[0][1]));
        for (let k = 1; k < loop.length; k++) p.push("L " + fmt(loop[k][0]) + " " + fmt(loop[k][1]));
        p.push("Z");
    }
    return p.join(" ");
}

/** Space needed above the bar's top edge for the droplet's highest point. */
export function launchHeadroom(o = DEFAULTS) {
    return 2.75 * containerRadius(o) + 6;
}

/** Half-width of the top-edge range the droplet field may touch (for the goo box). */
export function gooHalfWidth(o = DEFAULTS) {
    return containerRadius(o) * 1.9 + 4;
}

/**
 * Full dock path during a launch at slot x (progress p), with the previous active app's
 * cradle (oldX, or null) closing at the same time when it does not overlap.
 */
export function launchPath(width, x, p, oldX, o = DEFAULTS) {
    const s = launchState(p, o);
    const rc = Math.min(o.cornerRadius, o.height / 2, width / 2);
    const features = [];
    const loops = [];
    const half = gooHalfWidth(o);
    if (s.goo) {
        const x0 = Math.max(rc + 0.5, x - half), x1 = Math.min(width - rc - 0.5, x + half);
        const c = gooContour(x, s.cy, s.R, s.k, x0, x1, s.cy - s.R - 4, 3, 1.5);
        features.push({ edge: c.edge });
        for (let i = 0; i < c.loops.length; i++) loops.push(c.loops[i]);
    } else {
        const n = notch(x, s.notchT, o);
        if (n) features.push({ notch: n });
        loops.push(circlePoints(x, s.cy, s.R, 48));
    }
    if (oldX !== null && oldX !== undefined && s.oldT > 0) {
        const on = notch(oldX, s.oldT, o);
        const myLeft = x - half, myRight = x + half;
        if (on && (on.right < myLeft || on.left > myRight)) features.push({ notch: on });
    }
    return dockPathFeatures(width, features, loops, o);
}

export function circlePoints(cx, cy, r, n) {
    const out = [];
    for (let i = 0; i < n; i++) {
        const a = 2 * Math.PI * i / n;
        out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
    return out;
}
