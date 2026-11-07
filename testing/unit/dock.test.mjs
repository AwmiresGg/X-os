// Unit tests for the Signature Dock geometry engine.  Run: node --test testing/unit/
import { test } from "node:test";
import assert from "node:assert/strict";
import * as G from "../../desktop/dock/geometry.mjs";
import { readFileSync } from "node:fs";

test("geometry.mjs avoids syntax Qt's V4 engine rejects", () => {
    const src = readFileSync(new URL("../../desktop/dock/geometry.mjs", import.meta.url), "utf8")
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
    assert.ok(!/\.\.\.[A-Za-z_]/.test(src), "object/array spread");
    assert.ok(!/\?\./.test(src), "optional chaining");
    assert.ok(!/\*\*/.test(src), "exponent operator");
});

const O = G.DEFAULTS;
const near = (a, b, eps = 1e-6) => Math.abs(a - b) <= eps;

test("layout centres slots with equal pitch and no overlapping containers", () => {
    const { width, xs, pitch, diameter } = G.layout(6);
    assert.equal(xs.length, 6);
    for (let i = 1; i < xs.length; i++) {
        assert.ok(near(xs[i] - xs[i - 1], pitch));
        assert.ok(xs[i] - xs[i - 1] >= diameter, "containers must not overlap");
    }
    assert.ok(near(xs[0] - diameter / 2, O.padding));
    assert.ok(near(width - (xs[5] + diameter / 2), O.padding));
});

test("no notch at rest, full-depth notch when active", () => {
    assert.equal(G.notch(100, 0), null);
    const n = G.notch(100, 1);
    const N = G.containerRadius() + O.gap;
    assert.ok(near(n.depth, N - O.lift));
    assert.ok(n.depth > 0 && n.depth < O.height, "notch stays inside the dock body");
});

test("fillets are tangent to the top edge and to the notch circle (G1 continuity)", () => {
    for (const t of [0.1, 0.35, 0.6, 0.9, 1]) {
        const n = G.notch(200, t);
        const fl = { x: n.cx - n.dx, y: n.f };     // left fillet centre
        // tangent to y=0: centre is exactly f below the edge, contact at (left, 0)
        assert.ok(near(fl.y - n.f, 0));
        // externally tangent to notch circle
        const dCentres = Math.hypot(n.cx - fl.x, n.cy - fl.y);
        assert.ok(near(dCentres, n.N + n.f, 1e-9), `t=${t}`);
        // tangent point lies on both circles
        assert.ok(near(Math.hypot(n.tl.x - fl.x, n.tl.y - fl.y), n.f, 1e-9));
        assert.ok(near(Math.hypot(n.tl.x - n.cx, n.tl.y - n.cy), n.N, 1e-9));
        // symmetric
        assert.ok(near(n.cx - n.tl.x, n.tr.x - n.cx, 1e-9));
    }
});

test("floating circle keeps a uniform gap and never overlaps the surface when active", () => {
    const n = G.notch(150, 1);
    const cy = G.floatingCentre(1);
    assert.ok(near(cy, -O.lift));
    assert.ok(near(cy, n.cy), "concentric at full activation");
    assert.ok(near(G.surfaceGap(n, cy), O.gap));
});

test("geometry changes continuously over the animation (no jumps)", () => {
    let prev = null;
    for (let i = 0; i <= 1000; i++) {
        const t = i / 1000;
        const n = G.notch(300, t);
        const depth = n ? n.depth : 0;
        const width = n ? 2 * n.dx : 0;
        if (prev) {
            assert.ok(Math.abs(depth - prev.depth) < 0.2, `depth jump at t=${t}`);
            assert.ok(Math.abs(width - prev.width) < 4, `width jump at t=${t}: ${prev.width} -> ${width}`);
        }
        prev = { depth, width };
    }
});

test("icon hand-over: only icons near the sliding notch rise", () => {
    const { xs, pitch } = G.layout(5);
    const mid = (xs[1] + xs[2]) / 2;
    assert.ok(near(G.iconActivation(xs[1], mid, 1, pitch), 0.5));
    assert.ok(near(G.iconActivation(xs[2], mid, 1, pitch), 0.5));
    assert.equal(G.iconActivation(xs[4], mid, 1, pitch), 0);
    assert.equal(G.iconActivation(xs[2], xs[2], 0, pitch), 0);
});

test("SVG path is well-formed and contains no NaN", () => {
    const { width, xs } = G.layout(7);
    for (const x of [xs[0], xs[3], xs[6]]) {
        for (const t of [0, 0.5, 1]) {
            const d = G.dockPath(width, G.notch(x, t));
            assert.ok(!/NaN|Infinity/.test(d), d);
            assert.ok(d.startsWith("M ") && d.endsWith("Z"));
        }
    }
    assert.equal((G.dockPath(400, null).match(/A /g) || []).length, 4);
    assert.equal((G.dockPath(400, G.notch(200, 1)).match(/A /g) || []).length, 7);
});

test("notch at the outermost icon does not cut into the rounded corners", () => {
    const { width, xs } = G.layout(3);
    const n = G.notch(xs[0], 1);
    assert.ok(n.left >= 0, "notch shoulder starts inside the dock");
    const d = G.dockPath(width, n);
    const firstL = Number(d.split(" ")[4]);
    assert.ok(firstL >= Math.min(O.cornerRadius, O.height / 2) - 1e-9);
});

test("blur polygon follows the cradle and stays inside the dock body", () => {
    const { width, xs } = G.layout(5);
    const flat = G.dockPolygon(width, null);
    const n = G.notch(xs[2], 1);
    const carved = G.dockPolygon(width, n);
    assert.ok(carved.length > flat.length);
    for (const [x, y] of carved) {
        assert.ok(x >= -0.01 && x <= width + 0.01 && y >= -0.01 && y <= G.DEFAULTS.height + 0.01, `${x},${y}`);
    }
    // under the floating circle the outline dips to the notch depth
    const lowest = Math.max(...carved.filter(([x]) => Math.abs(x - n.cx) < 2).map(([, y]) => y));
    assert.ok(Math.abs(lowest - n.depth) < 0.5, `lowest ${lowest} vs depth ${n.depth}`);
    // and every polygon point near the notch is outside the floating circle (+gap)
    const cy = G.floatingCentre(1);
    for (const [x, y] of carved) {
        assert.ok(Math.hypot(x - n.cx, y - cy) >= G.containerRadius() + G.DEFAULTS.gap - 0.6);
    }
});

// ------------------------------------------------------------------ launch droplet
function gooAt(x, p) {
    const s = G.launchState(p);
    const h = G.gooHalfWidth();
    return G.gooContour(x, s.cy, s.R, s.k, x - h, x + h, s.cy - s.R - 4, 3, 1.5);
}

test("droplet: the first frame is the flat bar (no jump when the launch starts)", () => {
    const { xs } = G.layout(5);
    const c = gooAt(xs[2], 0);
    assert.equal(c.loops.length, 0);
    assert.ok(Math.min(...c.edge.map((q) => q[1])) > -0.5);
});

test("droplet: pinches off exactly once, never flickers back", () => {
    const { xs } = G.layout(5);
    const seq = [];
    for (let i = 0; i <= 200; i++) {
        const p = i / 200;
        if (!G.launchState(p).goo) break;
        seq.push(gooAt(xs[2], p).loops.length);
    }
    const first = seq.indexOf(1);
    assert.ok(first > 0, "the neck must exist before the pinch");
    assert.ok(seq.slice(0, first).every((n) => n === 0));
    assert.ok(seq.slice(first).every((n) => n === 1), seq.join(""));
});

test("droplet: neck height changes continuously while attached", () => {
    const { xs } = G.layout(5);
    let prev = null;
    for (let i = 0; i <= 200; i++) {
        const p = i / 200;
        const c = gooAt(xs[2], p);
        if (c.loops.length) break;
        const apex = Math.min(...c.edge.map((q) => q[1]));
        if (prev !== null) assert.ok(Math.abs(apex - prev) < 6, `jump at p=${p}: ${prev} -> ${apex}`);
        prev = apex;
    }
});

test("droplet: settles into the cradle without touching the surface", () => {
    const { width, xs } = G.layout(5);
    const x = xs[2];
    for (let i = 0; i <= 100; i++) {
        const p = i / 100;
        const s = G.launchState(p);
        if (s.goo) continue;
        const poly = G.dockPolygon(width, G.notch(x, s.notchT), G.DEFAULTS, 1);
        const minD = Math.min(...poly.map(([px, py]) => Math.hypot(px - x, py - s.cy)));
        assert.ok(minD >= s.R - 0.5, `p=${p}: droplet overlaps the bar (distance ${minD.toFixed(2)} < R ${s.R})`);
    }
});

test("droplet: end state equals the normal active state (seamless hand-over)", () => {
    const s = G.launchState(1);
    assert.ok(near(s.cy, G.floatingCentre(1), 1e-9));
    assert.equal(s.notchT, 1);
    assert.equal(s.accent, 1);
    assert.ok(near(s.tile, 0.25));
    assert.equal(s.goo, false);
});

test("droplet: launch path is well-formed for every slot and phase", () => {
    const { width, xs } = G.layout(7);
    for (const x of [xs[0], xs[3], xs[6]]) {
        for (const p of [0, 0.1, 0.3, 0.45, 0.65, 0.8, 1]) {
            const d = G.launchPath(width, x, p, xs[1]);
            assert.ok(!/NaN|Infinity|undefined/.test(d), d.slice(0, 200));
            assert.ok(d.startsWith("M ") && d.endsWith("Z"));
        }
    }
});

test("goo contour with no blending is the plain circle", () => {
    const c = G.gooContour(100, -60, 30, 0, 40, 160, -95, 3, 1);
    assert.equal(c.loops.length, 1);
    for (const [x, y] of c.loops[0]) assert.ok(Math.abs(Math.hypot(x - 100, y + 60) - 30) < 0.6);
    for (const [, y] of c.edge) assert.ok(Math.abs(y) < 0.01);
});

test("dock path tolerates empty droplet edges and missing features", () => {
    const d = G.dockPathFeatures(300, [null, { edge: [] }, { notch: G.notch(150, 1) }], [[]]);
    assert.ok(!/NaN|undefined/.test(d));
    assert.equal((d.match(/A /g) || []).length, 7);
});
