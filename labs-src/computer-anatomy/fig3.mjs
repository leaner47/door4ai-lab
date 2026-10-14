// Fig 3 — unified memory: one SoC package (CPU cores, GPU cores, Neural Engine on one die) with
// 8 memory packages on the same substrate. A model of S GB fills the shared pool; CPU and GPU both read it.
import { k, ctx, bench, pcb, smdRow } from "./common.mjs";

const W = 660, H = 400;
const PLATE = { x: -170, y: -92, w: 340, d: 184, r: 8 };
const BOARD = { x: -156, y: -80, w: 312, d: 160, r: 4 };
export const MAC = { mem: 128, bw: 546, gpuDefault: 96, ssdBW: 7, pkgs: 8 };

export function fig3() {
  const P = k.fitProjection([...k.boxCorners(PLATE, -15, 16)], W, H, { pad: 16, azimuth: 45, elevation: 34 });
  const c = ctx(P);
  const { at } = c;
  const out = [bench(c, PLATE)];
  const b = pcb(c, BOARD, 0);
  out.push(b.svg);
  const Z = b.top;
  const T = (txt, x, y, z, size = 4) => k.faceTextSvg(k.topMatrix([x, y], z, P, "x"), txt, { size, tone: "mid", anchor: "middle" });

  const items = [];
  // SSD NAND chips and controllers on the logic board, left side
  for (const [x, y] of [[-146, -62], [-146, -26]]) {
    items.push({ at: [x + 14, y + 12, Z], svg: c.slab({ x, y, w: 28, d: 24, r: 1 }, Z, 1.6, { tone: "mid" }, 2, 0.3) + c.L(k.planOutline({ x: x + 3, y: y + 3, w: 22, d: 18, r: 0.6 }, Z + 1.6, P, 2), { tone: "faint" }) });
  }
  items.push({ at: [-132, 22, Z], svg: c.slab({ x: -146, y: 12, w: 28, d: 20, r: 1 }, Z, 1.4, { tone: "lo" }, 2, 0.3) });
  // Thunderbolt / IO controllers on the right
  for (const y of [-56, -18, 20]) items.push({ at: [134, y + 9, Z], svg: c.slab({ x: 124, y, w: 20, d: 18, r: 1 }, Z, 1.4, { tone: "mid" }, 2, 0.3) });
  items.push(...smdRow(c, [-100, 66], [100, 66], 18, Z));
  items.push(...smdRow(c, [-100, -70], [100, -70], 18, Z));
  out.push(c.paint(items));

  // package substrate
  const SUB = { x: -96, y: -60, w: 192, d: 120, r: 3 };
  out.push(c.halo(k.insetPlan(SUB, 6), Z, 0.1));
  out.push(c.S(k.slabOf(SUB, Z, 2, P, 3, 0.5), { tone: "mid" }));
  const zs = Z + 2;
  out.push(c.L(k.planOutline(k.insetPlan(SUB, 3), zs, P, 3), { tone: "faint" }));
  // short memory traces from each package column to the die edge
  const tr = [];
  for (let i = 0; i < 12; i++) {
    const y = -40 + i * 7.3;
    tr.push(c.poly([[-41, y, zs], [-34, y, zs]]), c.poly([[34, y, zs], [41, y, zs]]));
  }
  out.push(c.L(tr.join(""), { tone: "lo" }));
  out.push(`<path data-part="mbus" class="iso-line" data-tone="lit" d="${tr.join("")}" style="opacity:0;transition:opacity .4s;stroke-width:1"/>`);

  // die
  const DIE = { x: -34, y: -50, w: 68, d: 100, r: 1 };
  out.push(c.S(k.slabOf(DIE, zs, 1.4, P, 2, 0.3), { tone: "lo" }));
  const dz = zs + 1.4;
  const tiles = [];
  // CPU: 12 performance cores (3 × 4) + 4 efficiency cores, top of the die
  for (let col = 0; col < 3; col++) for (let row = 0; row < 4; row++) tiles.push({ plan: { x: DIE.x + 4 + col * 13, y: DIE.y + 4 + row * 8.2, w: 12, d: 7.2, r: 0.4 }, kind: "cpu", h: 1.6 });
  for (let row = 0; row < 4; row++) tiles.push({ plan: { x: DIE.x + 46, y: DIE.y + 4 + row * 8.2, w: 8, d: 7.2, r: 0.4 }, kind: "cpu", h: 1.2 });
  // shared cache (SLC) block on the right of the CPU cluster
  out.push(c.S(k.slabOf({ x: DIE.x + 56, y: DIE.y + 4, w: 8, d: 32, r: 0.4 }, dz, 0.6, P, 2), { tone: "mid", crease: "none" }));
  // GPU: 40 cores (8 columns × 5 rows)
  for (let col = 0; col < 8; col++) for (let row = 0; row < 5; row++) tiles.push({ plan: { x: DIE.x + 4 + col * 7.6, y: DIE.y + 41 + row * 8.3, w: 6.8, d: 7.4, r: 0.3 }, kind: "gpu", h: 1.1 });
  // Neural Engine: 16 small cores along the bottom
  for (let i = 0; i < 16; i++) tiles.push({ plan: { x: DIE.x + 4 + i * 3.8, y: DIE.y + 85, w: 3.2, d: 10, r: 0.2 }, kind: "npu", h: 0.8 });
  tiles.sort((a, b) => c.depth([a.plan.x, a.plan.y]) - c.depth([b.plan.x, b.plan.y]));
  for (const t of tiles) {
    out.push(`<g data-hot data-unit="${t.kind}">${c.slab(t.plan, dz, t.h, { tone: t.kind === "npu" ? "mid" : "hi", crease: "lo" }, 1, 0.2)}</g>`);
  }

  // 8 memory packages (16 GB each): 4 on each side of the die
  const pk = [];
  for (const side of [-1, 1]) for (let i = 0; i < 4; i++) pk.push({ x: side < 0 ? -90 : 42, y: -54 + i * 27.5, side, i });
  // fill order alternates sides from the middle out
  const order = [...pk].sort((a, b) => Math.abs(a.y + 13.75 - 0) - Math.abs(b.y + 13.75 - 0) || a.side - b.side);
  const tagged = pk.map((p) => ({ ...p, n: order.indexOf(p) }));
  tagged.sort((a, b) => c.depth([a.x, a.y]) - c.depth([b.x, b.y]));
  for (const p of tagged) {
    const plan = { x: p.x, y: p.y, w: 48, d: 24, r: 1.2 };
    out.push(`<g data-hot data-mem="${p.n}">${c.slab(plan, zs, 2.4, { tone: "mid", crease: "lo" }, 3, 0.5)}</g>`);
    out.push(c.L(k.planOutline(k.insetPlan(plan, 2.5), zs + 2.4, P, 2), { tone: "faint" }));
    out.push(c.D([at([plan.x + 3.5, plan.y + 3.5, zs + 2.4])], { size: 0.45, tone: "lo" }));
  }
  out.push(T("SoC", 0, SUB.y + SUB.d - 3.5, zs, 4));

  const svg = k.figureSvg({
    width: W,
    height: H,
    label: "一块苹果 M 系列芯片的封装：中间一颗芯片上同时有 CPU 核心、GPU 核心和神经网络引擎，左右两侧是 8 颗内存颗粒，直接焊在同一块基板上。模型放进内存后，CPU 和 GPU 读的是同一份数据，不需要搬运。",
    body: out,
  });
  return k.plateHtml({
    fig: "Fig 3",
    title: "统一内存芯片",
    hint: "拖滑块改变模型大小",
    readout: "—",
    keys: [
      { mark: "lit", label: "亮起 = 被模型占用的内存颗粒（每颗 16 GB），以及正在读取它的 CPU / GPU 核心" },
      { mark: "raised", label: "中间的芯片：上方 CPU、中部 GPU、底部神经网络引擎" },
    ],
    caption: "以 M4 Max（128 GB 统一内存，约 546 GB/s）为例。内存就贴在芯片旁边，CPU 和 GPU 共用这一池；没有「显存」与「内存」之分，也就没有中间那条窄通道。",
    body: `<div class="iso-stage" id="f3-stage">${svg}</div>`,
  });
}

export function macSplit(S) {
  const m = Math.min(S, MAC.mem), d = Math.max(S - MAC.mem, 0);
  return { m, d, tps: 1 / (m / MAC.bw + d / MAC.ssdBW) };
}
