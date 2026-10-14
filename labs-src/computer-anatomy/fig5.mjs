// Fig 5 — a server rack next to a home desk. 1 unit ≈ 1 cm. The rack front faces +x (toward the viewer).
import { k, ctx } from "./common.mjs";

const W = 660, H = 460;
const FLOOR = { x: -126, y: -96, w: 170, d: 246, r: 4 };
const R = { x: -100, y: -80, w: 100, d: 60 }; // rack footprint
const U = 4.445;
const STACK = [["ups", 2], ["storage", 2], ["blank", 1], ["1u", 1], ["1u", 1], ["1u", 1], ["1u", 1], ["blank", 1], ["gpu", 4], ["1u", 1], ["1u", 1], ["blank", 2], ["switch", 1], ["patch", 1], ["empty", 2]];
const Z0 = 7;
const RACK_TOP = Z0 + STACK.reduce((s, [, u]) => s + u, 0) * U + 1;

export function fig5() {
  const P = k.fitProjection([...k.boxCorners(FLOOR, -6, 0), [R.x, R.y, RACK_TOP + 4], [-70, 40, 122]], W, H, { pad: 14, azimuth: 26, elevation: 26 });
  const c = ctx(P);
  const { at } = c;
  const out = [];
  // raised data-centre floor: 30 cm tiles (lines run edge to edge), a perforated tile in front of the rack
  out.push(c.halo(FLOOR, -6, 6));
  out.push(c.S(k.slabOf(FLOOR, -6, 6, P, 3, 0.8), { tone: "mid" }));
  const grid = [];
  for (let x = FLOOR.x + 28; x < FLOOR.x + FLOOR.w - 4; x += 30) grid.push(c.poly([[x, FLOOR.y, 0], [x, FLOOR.y + FLOOR.d, 0]]));
  for (let y = FLOOR.y + 30; y < FLOOR.y + FLOOR.d - 4; y += 30) grid.push(c.poly([[FLOOR.x, y, 0], [FLOOR.x + FLOOR.w, y, 0]]));
  out.push(c.L(grid.join(""), { tone: "faint" }));
  out.push(c.D(k.dotGrid(5, -82, 9, 16, 3.4, 0, P), { size: 0.35, tone: "lo" }));

  out.push(`<g data-hot data-who="server">${rack(c)}</g>`);
  out.push(`<g data-hot data-who="pc" transform="${k.translateAlong(P, [-34, 12, 0])}">${desk(c)}</g>`);

  const svg = k.figureSvg({
    width: W,
    height: H,
    label: "左后方是机房里的一个服务器机柜，里面从下到上装着不间断电源、存储服务器、几台 1U 计算服务器、一台 4U 的 GPU 服务器和网络交换机，前面板上的指示灯不停闪烁。右前方是一张普通书桌：显示器、键盘、鼠标，桌边立着一台台式机主机。",
    body: out,
  });
  return k.plateHtml({
    fig: "Fig 5",
    title: "服务器 · 个人电脑",
    hint: "点下面的按钮切换高亮",
    readout: "—",
    keys: [
      { mark: "lit", label: "高亮 = 当前讲解的那一边" },
      { mark: "dotted", label: "闪烁的小点 = 硬盘和网口的工作指示灯" },
    ],
    caption: "同样是电脑：左边是机柜里一层层插着的服务器，没有屏幕和键盘，靠网线被远程使用；右边是一个人坐在桌前用的个人电脑。",
    body: `<div class="iso-stage" id="f5-stage">${svg}</div>`,
  });
}

function rack(c) {
  const { P, at } = c;
  const out = [];
  const X1 = R.x + R.w; // front face x = 0
  out.push(c.halo({ x: R.x, y: R.y, w: R.w, d: R.d, r: 2 }, 0, RACK_TOP));
  // casters and plinth
  for (const [x, y] of c.byDepth(k.corners({ x: R.x, y: R.y, w: R.w, d: R.d, r: 2 }, 6))) out.push(c.cyl(x, y, 2.6, 0, 3, { tone: "lo" }, 14));
  out.push(c.slab({ x: R.x, y: R.y, w: R.w, d: R.d, r: 1.5 }, 3, Z0 - 3, { tone: "lo" }, 2, 0.4));
  // far front post (y side away from the viewer)
  const post = (y) => c.slab({ x: X1 - 3, y, w: 3, d: 3, r: 0.4 }, Z0, RACK_TOP - Z0, { tone: "mid" }, 1, 0.3);
  out.push(post(R.y));
  // equipment, bottom to top
  let z = Z0;
  const ports = {};
  STACK.forEach(([kind, u], i) => {
    const h = u * U;
    out.push(unit(c, kind, z, h, ports, i));
    z += h;
  });
  // patch cables from the switch down the front to each 1U and the GPU server
  const sw = ports.switch, cables = [];
  const targets = (ports.nics || []).slice(0, 7);
  targets.forEach((t, i) => {
    const from = sw[i + 2];
    const ly = -24.6 - i * 0.55, hz = from[2] - 1.6 - i * 0.3;
    const via = [at([X1 + 1.6, from[1], hz]), at([X1 + 1.6, ly, hz]), at([X1 + 1.6, ly, t[2] + 1.2]), at([X1 + 1.6, t[1], t[2] + 1.2])];
    cables.push(k.wireSvg(at(from), at(t), { via, tone: "mid", size: 0.55 }));
  });
  // near front post and side panel with vent slots
  out.push(post(R.y + R.d - 3));
  const side = { x: R.x + 2, y: R.y + R.d - 2, w: R.w - 5, d: 2, r: 0.3 };
  out.push(c.slab(side, Z0, RACK_TOP - Z0, { tone: "mid" }, 1, 0.3));
  const vents = [];
  for (let j = 0; j < 3; j++) for (let i = 0; i < 9; i++) vents.push(c.slotY(R.y + R.d, side.x + 12 + j * 28, side.x + 32 + j * 28, Z0 + 12 + i * 11, Z0 + 13.6 + i * 11));
  out.push(c.L(vents.join(""), { tone: "lo" }));
  out.push(c.slab({ x: R.x, y: R.y, w: R.w, d: R.d, r: 1.5 }, RACK_TOP, 3, { tone: "mid" }, 2, 0.5));
  out.push(c.L(k.planOutline({ x: R.x + 20, y: R.y + 15, w: 60, d: 30, r: 2 }, RACK_TOP + 3, P, 2), { tone: "faint" }));
  out.push(cables.join(""));
  return out.join("");
}

function unit(c, kind, z, h, ports, i) {
  const { P, at } = c;
  const X1 = 0, y0 = R.y + 3, y1 = R.y + R.d - 3;
  const plan = { x: R.x + 4, y: y0 + 0.5, w: R.w - 4, d: y1 - y0 - 1, r: 0.3 };
  const out = [];
  const lines = [], leds = [];
  const gap = 0.25;
  if (kind === "empty") {
    // empty rack units: just the mounting holes on the posts
    const holes = [];
    for (let n = 0; n < Math.round(h / U) * 3; n++) holes.push(at([X1, y0 - 1.5, z + 0.75 + n * (U / 3)]), at([X1, y1 + 1.5, z + 0.75 + n * (U / 3)]));
    return c.D(holes, { size: 0.35, tone: "lo" });
  }
  const tone = kind === "blank" ? "lo" : "mid";
  const box = c.slab(plan, z + gap, h - 2 * gap, { tone, crease: "lo" }, 1, 0.2);
  // ears with two screws each
  const ears = [y0 - 0.4, y1 + 0.4].map((y) => at([X1, y, z + h / 2]));
  const zc = z + h / 2;
  if (kind === "1u") {
    for (let n = 0; n < 8; n++) lines.push(c.slotX(X1, y0 + 4 + n * 4.2, y0 + 7.6 + n * 4.2, z + 0.9, z + h - 0.9));
    lines.push(c.slotX(X1, y1 - 14, y1 - 6, z + 1.4, z + h - 1.4));
    leds.push(at([X1, y1 - 3.5, zc]), ...Array.from({ length: 8 }, (_, n) => at([X1, y0 + 5.8 + n * 4.2, z + h - 0.5])));
    (ports.nics ||= []).push([X1, y1 - 10, zc]);
  } else if (kind === "storage") {
    for (let r = 0; r < 3; r++) for (let col = 0; col < 4; col++) lines.push(c.slotX(X1, y0 + 4 + col * 10.5, y0 + 13.5 + col * 10.5, z + 0.6 + r * 2.7, z + 2.9 + r * 2.7));
    for (let r = 0; r < 3; r++) for (let col = 0; col < 4; col++) leds.push(at([X1, y0 + 12.5 + col * 10.5, z + 1.75 + r * 2.7]));
  } else if (kind === "gpu") {
    for (let r = 0; r < 7; r++) lines.push(c.slotX(X1, y0 + 4, y0 + 30, z + 2 + r * 2.1, z + 3 + r * 2.1));
    for (let n = 0; n < 4; n++) lines.push(c.slotX(X1, y0 + 33 + n * 3.6, y0 + 36 + n * 3.6, z + 2, z + 8));
    lines.push(c.slotX(X1, y0 + 33, y0 + 47, z + 10, z + 15.5));
    leds.push(...Array.from({ length: 4 }, (_, n) => at([X1, y0 + 34.5 + n * 3.6, z + 9])));
    (ports.nics ||= []).push([X1, y0 + 40, z + 12.75]);
  } else if (kind === "switch") {
    const sw = [];
    for (let n = 0; n < 12; n++) for (let r = 0; r < 2; r++) {
      const y = y0 + 4 + n * 3.2, zz = z + 0.6 + r * 1.75;
      lines.push(c.slotX(X1, y, y + 2.4, zz, zz + 1.4));
      if (r === 0) sw.push([X1, y + 1.2, zz + 0.7]);
      leds.push(at([X1, y + 0.5, zz + 1.4 + 0.15]));
    }
    ports.switch = sw;
  } else if (kind === "patch") {
    for (let n = 0; n < 16; n++) lines.push(c.slotX(X1, y0 + 4 + n * 2.7, y0 + 5.8 + n * 2.7, z + 1.3, z + h - 1.3));
  } else if (kind === "ups") {
    lines.push(c.slotX(X1, y0 + 6, y0 + 20, z + 2.5, z + 6.5));
    for (let r = 0; r < 4; r++) lines.push(c.slotX(X1, y0 + 26, y1 - 4, z + 1.2 + r * 1.8, z + 2 + r * 1.8));
    leds.push(at([X1, y0 + 23, z + 6]), at([X1, y0 + 23, z + 3.5]));
  } else if (kind === "blank") {
    // nothing but the screws
  }
  out.push(`<g data-unit="${kind}">${box}</g>`);
  out.push(c.L(lines.join(""), { tone: "lo" }));
  out.push(c.D(ears, { size: 0.45, tone: "mid" }));
  if (leds.length) out.push(c.D(leds, { size: 0.5, tone: "hi", pulse: kind !== "ups" }));
  return out.join("");
}

function desk(c) {
  const { P, at } = c;
  const out = [];
  const TOP = { x: -54, y: 0, w: 64, d: 104, r: 2 }, TZ = 72;
  out.push(c.halo(TOP, 0, 0.1));
  // legs: the far ones first
  const legs = c.byDepth(k.corners(TOP, 4));
  for (const [x, y] of legs) out.push(c.slab({ x: x - 2, y: y - 2, w: 4, d: 4, r: 0.5 }, 0, TZ, { tone: "mid" }, 1, 0.3));
  out.push(c.slab({ x: TOP.x + 4, y: TOP.y + 4, w: 3, d: TOP.d - 8, r: 0.3 }, TZ - 10, 6, { tone: "lo" }, 1)); // back apron
  out.push(`<g data-part="pc">${c.slab(TOP, TZ, 3, { tone: "mid" }, 3, 0.8)}</g>`);
  const z = TZ + 3;
  // monitor: base, neck, screen with a few text lines on it
  out.push(c.slab({ x: -46, y: 40, w: 14, d: 22, r: 2 }, z, 1.2, { tone: "mid" }, 3, 0.3));
  out.push(c.slab({ x: -42, y: 49, w: 3, d: 4, r: 0.5 }, z + 1.2, 16, { tone: "mid" }, 1));
  const SCR = { x: -40, y: 18, w: 2.4, d: 66, r: 0.6 };
  out.push(`<g data-part="pc">${c.slab(SCR, z + 10, 38, { tone: "mid" }, 1, 0.3)}</g>`);
  const fx = SCR.x + SCR.w;
  out.push(c.L(c.slotX(fx, SCR.y + 2, SCR.y + SCR.d - 2, z + 13, z + 46), { tone: "lo" }));
  const text = [];
  [[40, 0], [26, 3], [46, 3], [30, 0], [36, 3], [20, 0], [42, 3], [28, 3]].forEach(([len, ind], i) => text.push(c.poly([[fx, SCR.y + 6 + ind, z + 42 - i * 3.6], [fx, SCR.y + 6 + ind + len, z + 42 - i * 3.6]])));
  out.push(c.L(text.join(""), { tone: "mid", free: true }));
  // keyboard and mouse
  const KB = { x: -18, y: 28, w: 15, d: 44, r: 1 };
  out.push(c.slab(KB, z, 1.4, { tone: "mid" }, 2, 0.3));
  out.push(c.D(k.dotGrid(KB.x + 2.5, KB.y + 2.5, 5, 16, 2.6, z + 1.4, P), { size: 0.3, tone: "lo" }));
  out.push(c.slab({ x: -14, y: 80, w: 8, d: 5, r: 2.4 }, z, 1.6, { tone: "mid" }, 4, 0.3));
  // tower beside the desk, front face at +x
  const T = { x: -34, y: 108, w: 46, d: 20, r: 1.2 };
  out.push(c.halo(T, 0, 0.1));
  for (const [x, y] of c.byDepth(k.corners(T, 4))) out.push(c.cyl(x, y, 1.6, 0, 1.5, { tone: "lo" }, 10));
  out.push(`<g data-part="pc">${c.slab(T, 1.5, 44, { tone: "mid" }, 2, 0.5)}</g>`);
  const tf = T.x + T.w;
  out.push(c.L(k.sideRing([tf, T.y + 10, 40], 1.6, "x", P), { tone: "mid" }));
  out.push(c.L([0, 1].map((n) => c.slotX(tf, T.y + 5 + n * 4, T.y + 7.4 + n * 4, 34, 35.2)).join(""), { tone: "lo" }));
  const vent = [];
  for (let r = 0; r < 9; r++) vent.push(c.slotX(tf, T.y + 4, T.y + T.d - 4, 6 + r * 2.6, 7 + r * 2.6));
  out.push(c.L(vent.join(""), { tone: "lo" }));
  out.push(c.D([at([tf, T.y + 15, 40])], { size: 0.5, tone: "hi" }));
  // a side window on the +y face
  out.push(c.L(c.slotY(T.y + T.d, T.x + 6, T.x + T.w - 6, 8, 40), { tone: "lo" }));
  return out.join("");
}

export const F5_LIVE = `
{
  const stage = document.getElementById("f5-stage");
  const readout = stage.closest(".iso-plate").querySelector("[data-readout]");
  const groups = { server: stage.querySelector('[data-who="server"]'), pc: stage.querySelector('[data-who="pc"]') };
  const text = { server: "7×24 小时 · 多人远程使用 · 坏一块盘不停机", pc: "一个人用 · 有屏幕键盘 · 关机下班" };
  function pick(who) {
    for (const [name, g] of Object.entries(groups)) {
      const sel = name === "server" ? '[data-unit] > .iso-solid' : '[data-part="pc"] > .iso-solid';
      g.querySelectorAll(sel).forEach((el) => { if (name === who) el.setAttribute("data-lit", ""); else el.removeAttribute("data-lit"); });
    }
    readout.textContent = text[who];
    document.querySelectorAll("[data-f5]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.f5 === who)));
    document.querySelectorAll("[data-col]").forEach((td) => td.classList.toggle("on", td.dataset.col === who));
  }
  document.querySelectorAll("[data-f5]").forEach((b) => b.addEventListener("click", () => pick(b.dataset.f5)));
  pick("server");
}
`;
