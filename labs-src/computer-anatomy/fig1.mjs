// Fig 1 — CPU vs GPU: two bare chips on one board. Cores light up while they work.
import { k, ctx, bench, pcb, smdRow } from "./common.mjs";

const W = 640, H = 380;
const PLATE = { x: -164, y: -84, w: 328, d: 166, r: 8 };
const BOARD = { x: -152, y: -72, w: 304, d: 140, r: 3 };

// CPU: 8 big cores around a shared L3 cache (an 8-core desktop chip)
const CPU_SUB = { x: -140, y: -48, w: 96, d: 96, r: 2 };
const CPU_DIE = { x: -128, y: -36, w: 72, d: 72, r: 1 };
// GPU: 128 SM tiles (each SM = 128 small cores → 16 384 cores, like an RTX 4090)
const GPU_SUB = { x: -14, y: -62, w: 154, d: 124, r: 2 };
const GPU_DIE = { x: -2, y: -50, w: 130, d: 100, r: 1 };

export function fig1() {
  const P = k.fitProjection([...k.boxCorners(PLATE, -15, 16)], W, H, { pad: 18, azimuth: 45, elevation: 34 });
  const c = ctx(P);
  const { at } = c;
  const parts = [];
  parts.push(bench(c, PLATE));
  const b = pcb(c, BOARD, 0);
  parts.push(b.svg);
  const Z = b.top; // board top

  // traces: a bus of 8 lines from CPU substrate to GPU substrate, pads at both ends
  const traces = [];
  const pads = [];
  for (let i = 0; i < 8; i++) {
    const y = -21 + i * 6;
    traces.push(c.poly([[CPU_SUB.x + CPU_SUB.w, y, Z], [GPU_SUB.x - 2.5, y, Z]]));
    pads.push(at([GPU_SUB.x - 2.5, y, Z]));
  }
  parts.push(c.L(traces.join(""), { tone: "lo" }));
  parts.push(c.D(pads, { size: 0.7, tone: "mid" }));
  // a board label plate near the front left with three rule lines
  const label = { x: -138, y: 52, w: 40, d: 11, r: 1 };
  parts.push(c.slab(label, Z, 0.5, { tone: "lo", crease: "none" }, 3));
  parts.push(c.L([0, 1, 2].map((i) => k.lineOnTop([label.x + 3, label.y + 3 + i * 2.6], [label.x + 3 + [30, 22, 26][i], label.y + 3 + i * 2.6], Z + 0.5, P)).join(""), { tone: "lo", free: true }));

  // ---- CPU ----
  const items = [];
  items.push({ at: [CPU_SUB.x + CPU_SUB.w / 2, CPU_SUB.y + CPU_SUB.d / 2, Z], svg: cpu(c, Z) });
  items.push({ at: [GPU_SUB.x + GPU_SUB.w / 2, GPU_SUB.y + GPU_SUB.d / 2, Z], svg: gpu(c, Z) });
  // decoupling capacitors and a crystal in the space around the chips
  items.push(...smdRow(c, [-150 + 16, -64], [-56, -64], 9, Z));
  items.push(...smdRow(c, [-6, 66 - 2], [130, 66 - 2], 12, Z));
  items.push(...smdRow(c, [146, -50], [146, 50], 9, Z, { axis: "y" }));
  parts.push(c.paint(items));

  const svg = k.figureSvg({
    width: W,
    height: H,
    label: "一块电路板上并排放着两颗去掉外壳的芯片：左边是 CPU，8 个大核心围着一块共享缓存；右边是 GPU，128 个小计算单元排成方阵，中间夹着一条二级缓存。正在工作的核心会亮起。",
    body: parts,
  });

  const body = k.plateHtml({
    fig: "Fig 1",
    title: "CPU · GPU",
    hint: "选一种任务，看谁在干活",
    readout: "—",
    keys: [
      { mark: "lit", label: "亮起 = 正在干活的核心" },
      { mark: "raised", label: "左：CPU 的 8 个大核；右：GPU 的 128 组小核（每组 128 个）" },
    ],
    caption: "同一块板子上的两颗芯片。CPU 的核心少而强，擅长一步接一步、充满判断的复杂活；GPU 的核心多而简单，擅长成千上万份一模一样的活同时做。",
    body: `<div class="iso-stage" id="f1-stage">${svg}</div>`,
  });
  return { body, P };
}

function cpu(c, Z) {
  const { P, at } = c;
  const out = [];
  const z1 = Z + 1.6;
  out.push(c.S(k.slabOf(CPU_SUB, Z, 1.6, P, 3, 0.4), { tone: "mid" }));
  // gold pads ring on the substrate (dots) and corner triangle mark
  const ring = [];
  for (let i = 0; i < 18; i++) {
    ring.push(at([CPU_SUB.x + 5 + i * 4.9, CPU_SUB.y + 3, z1]));
    if (Math.abs(5 + i * 4.9 - 52) > 10) ring.push(at([CPU_SUB.x + 5 + i * 4.9, CPU_SUB.y + CPU_SUB.d - 3, z1]));
    ring.push(at([CPU_SUB.x + 3, CPU_SUB.y + 5 + i * 4.9, z1]));
    ring.push(at([CPU_SUB.x + CPU_SUB.w - 3, CPU_SUB.y + 5 + i * 4.9, z1]));
  }
  out.push(c.D(ring, { size: 0.35, tone: "lo" }));
  out.push(k.faceTextSvg(k.topMatrix([CPU_SUB.x + 52, CPU_SUB.y + CPU_SUB.d - 4.5], z1, P, "x"), "CPU", { size: 4.6, tone: "mid", anchor: "middle" }));
  out.push(c.L(c.poly([[CPU_SUB.x + 4, CPU_SUB.y + CPU_SUB.d - 11, z1], [CPU_SUB.x + 4, CPU_SUB.y + CPU_SUB.d - 4, z1], [CPU_SUB.x + 11, CPU_SUB.y + CPU_SUB.d - 4, z1]], true), { tone: "mid" }));
  // die
  const dz = z1 + 1.2;
  out.push(c.S(k.slabOf(CPU_DIE, z1, 1.2, P, 2, 0.3), { tone: "lo" }));
  // L3 cache strip in the middle with an SRAM dot texture
  const l3 = { x: CPU_DIE.x + 31, y: CPU_DIE.y + 4, w: 10, d: 64, r: 0.5 };
  out.push(c.S(k.slabOf(l3, dz, 0.8, P, 2), { tone: "mid", crease: "lo" }));
  out.push(c.D(k.dotGrid(l3.x + 2, l3.y + 2.5, 4, 30, 2.05, dz + 0.8, P), { size: 0.25, tone: "lo" }));
  // 8 cores: 2 columns × 4 rows
  const cores = [];
  for (let col = 0; col < 2; col++) {
    for (let row = 0; row < 4; row++) {
      const plan = { x: CPU_DIE.x + 4 + col * 38, y: CPU_DIE.y + 4 + row * 16.25, w: 26, d: 14, r: 0.6 };
      cores.push({ plan, i: col * 4 + row });
    }
  }
  cores.sort((a, b) => c.depth([a.plan.x, a.plan.y, 0]) - c.depth([b.plan.x, b.plan.y, 0]));
  for (const { plan, i } of cores) {
    const top = dz + 2;
    const inner = c.L(k.planOutline(k.insetPlan(plan, 2.2), top, P, 2), { tone: "faint" });
    out.push(`<g data-hot data-core="cpu" data-i="${i}">${c.S(k.slabOf(plan, dz, 2, P, 2, 0.4), { tone: "hi", crease: "lo" })}${inner}`);
    // L2 block at the inner end of each core
    const l2x = plan.x + (plan.x < CPU_DIE.x + 30 ? plan.w - 7 : 1.5);
    out.push(c.S(k.slabOf({ x: l2x, y: plan.y + 2.5, w: 5.5, d: 9, r: 0.3 }, top, 0.6, P, 2), { tone: "mid", crease: "none" }));
    out.push(`</g>`);
  }
  return out.join("");
}

function gpu(c, Z) {
  const { P, at } = c;
  const out = [];
  const z1 = Z + 1.6;
  out.push(c.S(k.slabOf(GPU_SUB, Z, 1.6, P, 3, 0.4), { tone: "mid" }));
  // capacitor islands at the substrate corners
  for (const [x, y] of c.byDepth(k.corners(GPU_SUB, 5))) {
    for (let j = 0; j < 3; j++) out.push(c.slab({ x: x - 3 + j * 2.2, y: y - 0.8, w: 1.6, d: 1.6, r: 0.2 }, z1, 0.6, { tone: "lo", crease: "none" }, 2));
  }
  out.push(k.faceTextSvg(k.topMatrix([GPU_SUB.x + GPU_SUB.w / 2, GPU_SUB.y + GPU_SUB.d - 4.5], z1, P, "x"), "GPU", { size: 4.6, tone: "mid", anchor: "middle" }));
  const dz = z1 + 1.2;
  out.push(c.S(k.slabOf(GPU_DIE, z1, 1.2, P, 2, 0.3), { tone: "lo" }));
  // L2 cache strip across the middle
  const l2 = { x: GPU_DIE.x + 4, y: -4, w: GPU_DIE.w - 8, d: 8, r: 0.5 };
  out.push(c.S(k.slabOf(l2, dz, 0.6, P, 2), { tone: "mid", crease: "lo" }));
  out.push(c.D(k.dotGrid(l2.x + 2, l2.y + 2, 60, 3, 2.03, dz + 0.6, P), { size: 0.22, tone: "lo" }));
  // memory-controller strips along both long edges
  for (const y of [GPU_DIE.y + 1, GPU_DIE.y + GPU_DIE.d - 3]) {
    out.push(c.S(k.slabOf({ x: GPU_DIE.x + 4, y, w: GPU_DIE.w - 8, d: 2, r: 0.3 }, dz, 0.4, P, 2), { tone: "lo", crease: "none" }));
  }
  // 128 SM tiles: 16 columns × (4 + 4) rows
  const tiles = [];
  const cols = 16, tw = (GPU_DIE.w - 8 - (cols - 1) * 1.2) / cols;
  const half = 50 - 3 - 5.5; // from die edge margin to strip gap
  const td = (half - 3 * 1.2) / 4;
  let i = 0;
  for (let col = 0; col < cols; col++) {
    for (let row = 0; row < 8; row++) {
      const y = row < 4 ? -47 + row * (td + 1.2) : 5.5 + (row - 4) * (td + 1.2);
      tiles.push({ plan: { x: GPU_DIE.x + 4 + col * (tw + 1.2), y, w: tw, d: td, r: 0.3 }, col, row, i: i++ });
    }
  }
  tiles.sort((a, b) => c.depth([a.plan.x, a.plan.y, 0]) - c.depth([b.plan.x, b.plan.y, 0]));
  for (const t of tiles) {
    out.push(`<g data-hot data-core="gpu" data-i="${t.i}" data-col="${t.col}" data-row="${t.row}">${c.S(k.slabOf(t.plan, dz, 1.1, P, 2, 0.25), { tone: "hi", crease: "lo" })}</g>`);
  }
  return out.join("");
}

// The model behind the race (orders of magnitude, public spec sheets):
//  parallel job: 1e12 simple multiply-adds. CPU 8 cores ≈ 1.2 TFLOPS (AVX2 FMA @ ~4.7 GHz);
//                GPU RTX 4090 ≈ 82.6 TFLOPS FP32.
//  serial job: 1e9 steps, each needs the previous result. Only one core can work.
//                CPU core ~5.4 GHz with out-of-order execution ≈ 1 step/cycle → ≈ 0.19 s
//                GPU core ~2.5 GHz, ~4 cycles latency per dependent step → ≈ 1.6 s
export const F1_MODEL = {
  parallel: { cpu: 1e12 / 1.2e12, gpu: 1e12 / 82.6e12, cpuCores: "all", gpuCores: "all" },
  serial: { cpu: 1e9 / 5.4e9, gpu: (1e9 * 4) / 2.52e9, cpuCores: "one", gpuCores: "one" },
};

export const F1_LIVE = `
{
  const M = ${JSON.stringify(F1_MODEL)};
  const stage = document.getElementById("f1-stage");
  const plate = stage.closest(".iso-plate");
  const readout = plate.querySelector("[data-readout]");
  const cpuCores = [...stage.querySelectorAll('[data-core="cpu"] > .iso-solid:first-child')];
  const gpuCores = [...stage.querySelectorAll('[data-core="gpu"] > .iso-solid')];
  const gpuMeta = [...stage.querySelectorAll('[data-core="gpu"]')].map(g => ({ col: +g.dataset.col, row: +g.dataset.row }));
  const cpuIdx = [...stage.querySelectorAll('[data-core="cpu"]')].map(g => +g.dataset.i);
  const barC = document.getElementById("f1-bar-cpu"), barG = document.getElementById("f1-bar-gpu");
  const tC = document.getElementById("f1-t-cpu"), tG = document.getElementById("f1-t-gpu");
  const still = matchMedia("(prefers-reduced-motion: reduce)");
  let mode = "parallel", t0 = 0, frame = 0, visible = false, done = false;
  const fmtT = (s) => s >= 1 ? s.toFixed(2) + " s" : s >= 0.001 ? (s * 1000).toFixed(1) + " ms" : (s * 1e6).toFixed(0) + " μs";
  const setLit = (el, on) => { if (on) { if (!el.hasAttribute("data-lit")) el.setAttribute("data-lit", ""); } else if (el.hasAttribute("data-lit")) el.removeAttribute("data-lit"); };
  // the slower chip takes 4 s of animation; the faster one finishes in proportion (min 0.25 s so you can see it)
  function durations() { const m = M[mode]; const slow = Math.max(m.cpu, m.gpu); return { cpu: Math.max(0.25, 4 * m.cpu / slow), gpu: Math.max(0.25, 4 * m.gpu / slow) }; }
  function draw(time) {
    const d = durations(), m = M[mode];
    const pc = Math.min(1, time / d.cpu), pg = Math.min(1, time / d.gpu);
    barC.style.transform = "scaleX(" + pc + ")"; barG.style.transform = "scaleX(" + pg + ")";
    tC.textContent = pc < 1 ? "进行中…" : fmtT(m.cpu); tG.textContent = pg < 1 ? "进行中…" : fmtT(m.gpu);
    const beat = Math.floor(time * 6);
    cpuCores.forEach((el, j) => setLit(el, pc < 1 && (mode === "parallel" || cpuIdx[j] === 0)));
    gpuCores.forEach((el, j) => {
      const g = gpuMeta[j];
      // parallel: every SM busy, a soft wave shows work being handed out; serial: one SM, the rest idle
      const on = pg < 1 && (mode === "parallel" ? ((g.col + g.row + beat) % 5 !== 0) : (g.col === 0 && g.row === 0));
      setLit(el, on);
    });
    const text = pc >= 1 && pg >= 1
      ? (m.cpu < m.gpu ? "CPU 快 " + (m.gpu / m.cpu).toFixed(0) + " 倍" : "GPU 快 " + (m.cpu / m.gpu).toFixed(0) + " 倍")
      : (mode === "parallel" ? "1 万亿次乘加 · 所有核心一起上" : "10 亿步接力 · 只能一个核心干");
    if (readout.textContent !== text) readout.textContent = text;
    done = pc >= 1 && pg >= 1;
  }
  function tick(now) {
    if (!t0) t0 = now;
    draw((now - t0) / 1000);
    frame = visible && !done ? requestAnimationFrame(tick) : 0;
  }
  function start(next) {
    mode = next; done = false; t0 = 0;
    document.querySelectorAll("[data-f1]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.f1 === mode)));
    if (still.matches) { draw(99); return; }
    if (!frame && visible) frame = requestAnimationFrame(tick);
  }
  document.querySelectorAll("[data-f1]").forEach(b => b.addEventListener("click", () => start(b.dataset.f1)));
  new IntersectionObserver((e) => { const was = visible; visible = e[e.length - 1].isIntersecting; if (visible && !was && !frame) { if (still.matches) draw(99); else { if (done) t0 = 0, done = false; frame = requestAnimationFrame(tick); } } }, { rootMargin: "80px 0px" }).observe(stage);
  draw(0);
}
`;
