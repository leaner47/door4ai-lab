// Fig 2 — discrete PC: motherboard (CPU + 2 RAM sticks + SSD) and a bare graphics card (GPU + 12 VRAM chips),
// joined by a PCIe riser ribbon. A model of S GB fills VRAM first, then spills into RAM, then onto the SSD.
import { k, ctx, bench, pcb, smdRow } from "./common.mjs";

const W = 660, H = 400;
const PLATE = { x: -184, y: -92, w: 368, d: 184, r: 8 };
const MOBO = { x: -172, y: -80, w: 178, d: 160, r: 3 };
const CARD = { x: 30, y: -72, w: 142, d: 144, r: 3 };
export const PC = { vram: 24, vramBW: 1008, ram: 64, ramBW: 89.6, ssdBW: 7, vramChips: 12, ramChips: 16 };

export function fig2() {
  const P = k.fitProjection([...k.boxCorners(PLATE, -15, 40)], W, H, { pad: 16, azimuth: 45, elevation: 32 });
  const c = ctx(P);
  const { at } = c;
  const out = [bench(c, PLATE)];
  const m = pcb(c, MOBO, 0);
  const g = pcb(c, CARD, 0);
  out.push(m.svg, g.svg);
  const Z = m.top;
  const T = (txt, x, y, z, size = 4) => k.faceTextSvg(k.topMatrix([x, y], z, P, "x"), txt, { size, tone: "mid", anchor: "middle" });

  // --- motherboard, back to front ---
  // VRM heatsink with fins along the back edge
  const hs = { x: -164, y: -72, w: 60, d: 12, r: 1 };
  out.push(c.slab(hs, Z, 9, { tone: "mid" }, 2, 0.4));
  out.push(c.L(Array.from({ length: 11 }, (_, i) => k.segment([hs.x + 5 + i * 5, hs.y + hs.d, Z], [hs.x + 5 + i * 5, hs.y + hs.d, Z + 9], P)).join(""), { tone: "lo" }));
  // CPU socket + lever + heat spreader
  const sock = { x: -162, y: -50, w: 50, d: 50, r: 1.5 };
  out.push(c.slab(sock, Z, 2, { tone: "lo" }, 2, 0.3));
  out.push(c.slab({ x: sock.x - 5, y: sock.y + 2, w: 2.4, d: 46, r: 1 }, Z, 2.6, { tone: "mid" }, 2));
  out.push(c.slab({ x: sock.x - 5, y: sock.y + sock.d - 4, w: 6, d: 2.4, r: 1 }, Z, 2.6, { tone: "mid" }, 2));
  const ihs = { x: sock.x + 5, y: sock.y + 5, w: 40, d: 40, r: 2 };
  out.push(`<g data-hot data-part="cpu">${c.slab(ihs, Z + 2, 3, { tone: "hi", crease: "lo" }, 4, 0.6)}</g>`);
  out.push(c.L(k.planOutline(k.insetPlan(ihs, 3), Z + 5, P, 3), { tone: "faint" }));
  out.push(T("CPU", ihs.x + 20, ihs.y + 23, Z + 5));
  // caps beside socket
  out.push(c.paint(smdRow(c, [-156, 8], [-116, 8], 8, Z)));

  // two DIMM slots with sticks; chips on the +x face
  const STICK_Y = -60, STICK_D = 104;
  for (const [si, sx] of [[0, -96], [1, -64]]) {
    const slot = { x: sx - 1, y: STICK_Y - 6, w: 6, d: STICK_D + 12, r: 1 };
    out.push(c.slab(slot, Z, 4, { tone: "lo" }, 2, 0.3));
    out.push(c.slab({ x: sx - 1.6, y: slot.y - 1, w: 7.2, d: 4, r: 1 }, Z, 7, { tone: "mid" }, 2)); // back latch
    const stick = { x: sx + 0.5, y: STICK_Y, w: 3, d: STICK_D, r: 0.6 };
    out.push(c.slab(stick, Z + 4, 22, { tone: "mid" }, 2, 0.3));
    for (let i = 0; i < 8; i++) {
      const chip = { x: stick.x + 3, y: STICK_Y + 4 + i * 12.3, w: 1, d: 10, r: 0.2 };
      out.push(`<g data-hot data-ram="${si * 8 + i}">${c.slab(chip, Z + 9, 12, { tone: "mid", crease: "lo" }, 1)}</g>`);
    }
    out.push(c.slab({ x: sx - 1.6, y: slot.y + slot.d - 3, w: 7.2, d: 4, r: 1 }, Z, 7, { tone: "mid" }, 2)); // front latch
  }
  out.push(T("RAM", -78, 62, Z));

  // M.2 SSD in front of the sticks
  const ssd = { x: -164, y: 50, w: 56, d: 16, r: 1 };
  out.push(`<g data-hot data-part="ssd">${c.slab(ssd, Z + 1, 1.2, { tone: "mid" }, 2, 0.3)}</g>`);
  out.push(c.slab({ x: ssd.x + 6, y: ssd.y + 3, w: 15, d: 10, r: 0.5 }, Z + 2.2, 1, { tone: "hi", crease: "lo" }, 2));
  out.push(c.slab({ x: ssd.x + 24, y: ssd.y + 3, w: 15, d: 10, r: 0.5 }, Z + 2.2, 1, { tone: "hi", crease: "lo" }, 2));
  out.push(c.slab({ x: ssd.x + 43, y: ssd.y + 4, w: 9, d: 8, r: 0.5 }, Z + 2.2, 0.8, { tone: "lo", crease: "none" }, 2));
  out.push(c.cyl(ssd.x + ssd.w + 3, ssd.y + 8, 2.4, Z, 2.6, { tone: "mid" }, 16));
  out.push(T("SSD", ssd.x + 28, ssd.y + ssd.d + 5, Z, 3.6));

  // PCIe slot and riser ribbon to the card's edge connector
  const slot = { x: -26, y: -52, w: 8, d: 92, r: 1 };
  out.push(c.slab(slot, Z, 5, { tone: "lo" }, 2, 0.3));
  out.push(c.slab({ x: slot.x - 1, y: slot.y + slot.d - 2, w: 10, d: 5, r: 1 }, Z, 7, { tone: "mid" }, 2));
  const edge = { x: 36, y: -52, w: 9, d: 92, r: 1 };
  out.push(c.slab(edge, Z, 5, { tone: "lo" }, 2, 0.3));
  const ribbon = { x: -24, y: -48, w: 66, d: 84, r: 0.5 };
  out.push(c.slab(ribbon, Z + 5, 0.6, { tone: "mid", crease: "lo" }, 1));
  const lanes = [];
  for (let i = 0; i < 16; i++) {
    const y = ribbon.y + 3 + i * 5.2;
    lanes.push(c.poly([[ribbon.x, y, Z + 5.6], [ribbon.x + ribbon.w, y, Z + 5.6]]));
  }
  out.push(c.L(lanes.join(""), { tone: "faint" }));
  out.push(`<path data-part="bus" class="iso-line" data-tone="lit" data-flow d="${lanes.join("")}" style="opacity:0;transition:opacity .4s"/>`);
  // clamps on both ends of the ribbon
  out.push(c.slab({ x: slot.x - 1, y: ribbon.y - 3, w: 10, d: ribbon.d + 6, r: 1 }, Z + 5.6, 1.4, { tone: "mid" }, 2, 0.3));
  out.push(c.slab({ x: edge.x - 0.5, y: ribbon.y - 3, w: 10, d: ribbon.d + 6, r: 1 }, Z + 5.6, 1.4, { tone: "mid" }, 2, 0.3));

  // --- graphics card, back to front ---
  const items = [];
  // power connector at the back corner, pins as dots
  const pwr = { x: 136, y: -66, w: 26, d: 9, r: 1 };
  items.push({ at: [pwr.x, pwr.y, Z], svg: c.slab(pwr, Z, 7, { tone: "mid" }, 2, 0.4) + c.D(Array.from({ length: 12 }, (_, i) => at([pwr.x + 3 + (i % 6) * 4, pwr.y + 3 + Math.floor(i / 6) * 3, Z + 7])), { size: 0.45, tone: "lo" }) });
  // GPU package
  const sub = { x: 80, y: -22, w: 44, d: 44, r: 1.5 };
  const die = { x: 89, y: -13, w: 26, d: 26, r: 0.8 };
  items.push({ at: [102, 0, Z], svg: c.slab(sub, Z, 1.6, { tone: "mid" }, 2, 0.3) + `<g data-hot data-part="gpu">${c.slab(die, Z + 1.6, 1.8, { tone: "hi", crease: "lo" }, 2, 0.4)}</g>` + T("GPU", 102, sub.y + sub.d - 2.5, Z + 1.6, 3.4) });
  // 12 VRAM chips around the package
  const chips = [];
  for (let i = 0; i < 4; i++) chips.push({ x: 70 + i * 15.5, y: -42 }, { x: 70 + i * 15.5, y: 30 });
  chips.push({ x: 60, y: -17 }, { x: 60, y: 5 }, { x: 132, y: -17 }, { x: 132, y: 5 });
  // fill order: nearest-to-die first, alternating sides, so the ring fills evenly
  const order = chips.map((p, i) => ({ ...p, i })).sort((a, b) => Math.hypot(a.x + 6 - 102, a.y + 5.5) - Math.hypot(b.x + 6 - 102, b.y + 5.5) || a.y - b.y);
  order.forEach((p, n) => {
    const plan = { x: p.x, y: p.y, w: 12, d: 11, r: 0.6 };
    items.push({ at: [p.x + 6, p.y + 5.5, Z], svg: `<g data-hot data-vram="${n}">${c.slab(plan, Z, 1.6, { tone: "mid", crease: "lo" }, 2, 0.3)}</g>` + c.D([at([p.x + 2, p.y + 2, Z + 1.6])], { size: 0.4, tone: "lo" }) });
  });
  // VRM chokes along the near edge
  for (let i = 0; i < 7; i++) {
    const ch = { x: 152, y: -40 + i * 11, w: 8, d: 8, r: 1 };
    items.push({ at: [156, ch.y + 4, Z], svg: c.slab(ch, Z, 6, { tone: "mid" }, 2, 0.4) + c.L(k.planOutline(k.insetPlan(ch, 2), Z + 6, P, 2), { tone: "faint" }) });
  }
  items.push(...smdRow(c, [70, 52], [140, 52], 10, Z));
  items.push(...smdRow(c, [70, -54], [130, -54], 8, Z));
  out.push(c.paint(items));
  out.push(T("VRAM", 101, 63, Z, 3.6));

  const svg = k.figureSvg({
    width: W,
    height: H,
    label: "左边是主板：CPU、两根内存条和一块 SSD 硬盘；右边是拆掉风扇的显卡：中间是 GPU 芯片，四周 12 颗显存颗粒。两块板之间用一条 PCIe 排线相连。滑块改变模型大小，被占用的显存、内存颗粒会亮起；放不进显存时，排线上会出现数据流。",
    body: out,
  });
  const body = k.plateHtml({
    fig: "Fig 2",
    title: "独立显卡电脑",
    hint: "拖滑块改变模型大小",
    readout: "—",
    keys: [
      { mark: "lit", label: "亮起 = 被模型占用的颗粒（每颗显存 2 GB、每颗内存 4 GB）" },
      { mark: "dashed", label: "中间的排线 = PCIe 通道，约 32 GB/s" },
    ],
    caption: "一台装 RTX 4090（24 GB 显存，约 1008 GB/s）和 64 GB DDR5 内存（双通道约 90 GB/s）的电脑。模型先塞进显存，装不下的部分只能留在内存里，由 CPU 慢慢算或经过 PCIe 来回搬。",
    body: `<div class="iso-stage" id="f2-stage">${svg}</div>`,
  });
  return body;
}

// tokens/s upper bound for memory-bound generation: every token reads all weights once
export function pcSplit(S) {
  const v = Math.min(S, PC.vram), r = Math.min(Math.max(S - PC.vram, 0), PC.ram), d = Math.max(S - PC.vram - PC.ram, 0);
  const t = v / PC.vramBW + r / PC.ramBW + d / PC.ssdBW;
  return { v, r, d, tps: 1 / t };
}
