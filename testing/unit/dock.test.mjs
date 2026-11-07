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
