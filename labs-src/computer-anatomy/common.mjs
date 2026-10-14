import * as k from "./kit/iso-kit.mjs";
export { k };

export function ctx(P) {
  const at = (p) => k.iso(p, P);
  const f = (v) => (Math.round(v * 10) / 10).toString();
  const c = {
    P,
    at,
    S: (paths, style = {}) => k.solidSvg(paths, style),
    L: (d, style = {}) => k.lineSvg(d, style),
    D: (pts, style = {}) => k.dotsSvg(pts, style),
    depth: (p) => k.depthOf([p[0], p[1], p[2] || 0], P),
    byDepth: (pts) => [...pts].sort((a, b) => c.depth(a) - c.depth(b)),
    // a closed or open polyline through world points
    poly: (pts, closed = false) => "M" + pts.map((p) => at(p).map(f).join(" ")).join("L") + (closed ? "Z" : ""),
    slab: (plan, z, h, style = {}, steps = 3, bevel = 0) => k.solidSvg(k.slabOf(plan, z, h, P, steps, bevel), style),
    cyl: (x, y, r, z, h, style = {}, steps = 20, bevel = 0) => k.solidSvg(k.cylinder(x, y, r, z, h, P, steps, bevel), style),
    halo: (plan, z, h) => `<path class="iso-halo" d="${k.haloOf(plan, z, h, P)}"/>`,
    // painter: items [{ at:[x,y,z], svg }]
    paint: (items) => [...items].sort((a, b) => c.depth(a.at) - c.depth(b.at) || (a.at[2] || 0) - (b.at[2] || 0)).map((i) => i.svg).join(""),
  };
  // a slot outline on the +x face (x fixed) — closed, so it has no free ends
  c.slotX = (x, y0, y1, z0, z1) => c.poly([[x, y0, z0], [x, y1, z0], [x, y1, z1], [x, y0, z1]], true);
  c.slotY = (y, x0, x1, z0, z1) => c.poly([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]], true);
  return c;
}

// bench plate on four feet, with groove, corner screws and a ruler strip on the near (+y) edge
export function bench(c, PLATE, { H = 10, FOOT = 5, ruler = true } = {}) {
  const { P, at } = c;
  const out = [c.halo(PLATE, -H - FOOT, H)];
  for (const [x, y] of c.byDepth(k.corners(PLATE, 20))) {
    out.push(c.cyl(x, y, 7, -H - FOOT, 1.6, { tone: "lo" }, 28));
    out.push(c.cyl(x, y, 5.4, -H - FOOT + 1.6, FOOT - 1.6, { tone: "mid" }, 28));
  }
  out.push(c.S(k.slabOf(PLATE, -H, H, P, 8, 1.4), { tone: "mid" }));
  out.push(c.L(k.planOutline(k.insetPlan(PLATE, 5), 0, P), { tone: "lo" }));
  const screws = k.corners(PLATE, 10);
  out.push(c.L(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(c.D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  if (ruler) {
    const strip = { x: PLATE.x + 22, y: PLATE.y + PLATE.d - 13, w: PLATE.w - 44, d: 6, r: 1 };
    out.push(c.S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
    const t = k.topTicks(strip.x + 4, strip.x + strip.w - 4, 4, 5, strip.y, 0.6, [2, 3.4], P);
    out.push(c.L(t.minor, { tone: "lo" }), c.L(t.major, { tone: "mid" }));
    out.push(c.D([at([strip.x + 2, strip.y + 3, 0.6]), at([strip.x + strip.w - 2, strip.y + 3, 0.6])], { size: 0.45 }));
  }
  return out.join("");
}

// a printed circuit board on brass standoffs; returns svg and the board's top z
export function pcb(c, plan, z0, { lift = 6, t = 1.6, holes = 6 } = {}) {
  const { P, at } = c;
  const out = [c.halo(k.insetPlan(plan, 4), z0, 0.1)];
  const posts = k.corners(plan, holes);
  for (const [x, y] of c.byDepth(posts)) out.push(c.cyl(x, y, 2.6, z0, lift, { tone: "lo" }, 6));
  const top = z0 + lift + t;
  out.push(c.S(k.slabOf(plan, z0 + lift, t, P, 4, 0.5), { tone: "mid" }));
  out.push(c.L(k.planOutline(k.insetPlan(plan, 2.5), top, P, 4), { tone: "faint" }));
  for (const [x, y] of posts) {
    out.push(c.L(k.ring(x, y, 3, top, P, 16), { tone: "lo" }));
  }
  out.push(c.D(posts.map(([x, y]) => at([x, y, top])), { size: 0.6, tone: "mid" }));
  return { svg: out.join(""), top };
}

// small SMD parts in a row along a plan edge
export function smdRow(c, from, to, n, z, { w = 2, d = 1.2, h = 0.7, axis = "x" } = {}) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const s = n === 1 ? 0.5 : i / (n - 1);
    const x = from[0] + (to[0] - from[0]) * s, y = from[1] + (to[1] - from[1]) * s;
    const plan = axis === "x" ? { x: x - w / 2, y: y - d / 2, w, d, r: 0.3 } : { x: x - d / 2, y: y - w / 2, w: d, d: w, r: 0.3 };
    out.push({ at: [x, y, z], svg: c.slab(plan, z, h, { tone: "lo", crease: "none" }, 2) });
  }
  return out;
}

export const fmt = (v, d = 1) => Number(v).toFixed(d);
