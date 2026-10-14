// Fig 4 — Docker as a container ship at a quay. Hull = the server's hardware, deck = the one shared Linux kernel,
// containers = apps packed with everything they need. A gantry crane lifts boxes from the quay stack (the image
// registry) and sets them on deck (docker run), or takes them off (docker stop / rm).
import { k, ctx } from "./common.mjs";

const W = 660, H = 440;
const WATER = { x: -196, y: -128, w: 392, d: 192, r: 6 };
const QUAY = { x: -196, y: -128, w: 392, d: 36, r: 2 };
const QZ = 14; // quay top
const HULL = [[-150, -40], [116, -40], [170, 0], [116, 40], [-150, 40]];
const DECK = 21;
const CW = 40, CD = 15, CH = 15; // container size (20 ft box, ~1 unit = 15 cm)
const BAYS = [-102, -58, -14, 30, 74];
const ROWS = [-32.5, -16, 0.5, 17];
const TIERS = 2;
const CRANE_TOP = 112;
const PICK_Y = -110; // trolley position above the quay stack

export const APPS = [
  ["nginx", "网页服务器"], ["postgres", "数据库"], ["redis", "缓存"], ["python", "后端 API"], ["node", "前端网站"],
  ["jupyter", "数据分析笔记本"], ["ollama", "本地大模型"], ["grafana", "监控面板"], ["mysql", "数据库"], ["rabbitmq", "消息队列"],
];

function slots() {
  const out = [];
  // fill order: lower tier first, from the bow end (near the viewer's right) back toward the bridge
  for (let t = 0; t < TIERS; t++) {
    const tier = [];
    for (const bx of BAYS) for (const ry of ROWS) tier.push({ x: bx, y: ry, z: DECK + t * CH });
    // load back-to-front so the box on the hook is never behind a box already on deck
    tier.sort((a, b) => a.x * 0.559 + a.y * 0.829 - (b.x * 0.559 + b.y * 0.829));
    out.push(...tier);
  }
  return out;
}

function container(c, x, y, z, tone = "hi", lit = false) {
  const { P, at } = c;
  const plan = { x, y, w: CW, d: CD, r: 0.4 };
  const ribs = [];
  for (let i = 1; i < 16; i++) ribs.push(k.segment([x + i * 2.5, y + CD, z], [x + i * 2.5, y + CD, z + CH], P));
  const doors = [];
  for (const f of [0.18, 0.36, 0.5, 0.64, 0.82]) doors.push(k.segment([x + CW, y + CD * f, z], [x + CW, y + CD * f, z + CH], P));
  const top = [[x + 1, y + 1], [x + CW - 1, y + 1], [x + 1, y + CD - 1], [x + CW - 1, y + CD - 1]].map(([a, b]) => at([a, b, z + CH]));
  return c.S(k.slabOf(plan, z, CH, P, 1, 0.3), { tone, lit, crease: "lo", inner: k.lineSvg(ribs.join(""), { tone: "faint" }) + k.lineSvg(doors.join(""), { tone: "lo" }) }) + c.D(top, { size: 0.4, tone: "lo" });
}

export function fig4() {
  const pts = [...k.boxCorners(WATER, -6, 0), [-110, 60, CRANE_TOP + 4], [110, -136, CRANE_TOP + 14], [-110, -136, CRANE_TOP + 14]];
  const P = k.fitProjection(pts, W, H, { pad: 14, azimuth: 56, elevation: 30 });
  const c = ctx(P);
  const { at } = c;
  const out = [];
  // water: a shallow basin
  out.push(c.halo(WATER, -6, 4));
  out.push(c.S(k.slabOf(WATER, -6, 6, P, 6, 0.6), { tone: "lo", crease: "faint" }));
  // quay with edge fenders, rails and bollards
  out.push(c.S(k.slabOf(QUAY, 0, QZ, P, 2, 0.8), { tone: "mid" }));
  out.push(c.L(k.sideSeam(QUAY, 4, P, 2), { tone: "faint" }));
  for (const x of [-180, -120, -60, 0, 60, 120, 180]) out.push(c.slab({ x: x - 3, y: QUAY.y + QUAY.d, w: 6, d: 2.4, r: 0.8 }, 2, 10, { tone: "lo" }, 2));
  for (const y of [-124, -98]) out.push(c.slab({ x: QUAY.x + 2, y, w: QUAY.w - 4, d: 2, r: 0.5 }, QZ, 0.8, { tone: "lo", crease: "none" }, 1));
  const bollards = [[-140, -96], [150, -96]];
  for (const [x, y] of bollards) { out.push(c.cyl(x, y, 3, QZ, 4, { tone: "mid" }, 16)); out.push(c.cyl(x, y, 4, QZ + 4, 1.4, { tone: "mid" }, 16)); }
  // the registry: a short stack of boxes waiting on the quay
  const pile = [];
  for (const [x, t] of [[-186, 0], [-186, 1], [-142, 0], [130, 0], [146, 1]]) pile.push({ at: [x + 20, -120, QZ + t * CH], svg: container(c, x, -120, QZ + t * CH, "mid") });
  // crane rails' far legs (static parts of the crane are in a moving group below)
  out.push(`<g data-part="crane-back">${craneBack(c)}</g>`);
  out.push(c.paint(pile));
  out.push(`<g data-part="crane-mid">${craneMid(c)}</g>`);

  // hull: waterline band, main hull with a seam, deck plate (= the shared kernel)
  const inset = (ring, d) => ring.map(([x, y]) => [x + (x > 0 ? -d * 0.6 : d), y - Math.sign(y) * d]);
  out.push(c.halo({ x: -150, y: -40, w: 320, d: 80, r: 20 }, -2, 2));
  out.push(c.S(k.extrude(inset(HULL, 2), -1, 6, P, { bevel: 0 }), { tone: "lo" }));
  const hull = k.extrude(HULL, 5, DECK - 5, P, { bevel: 0.6 });
  out.push(c.S(hull, { tone: "mid", inner: k.lineSvg(k.ringSeam(HULL, 13, P), { tone: "faint" }) }));
  const deckRing = inset(HULL, 3);
  out.push(`<g data-hot data-part="kernel">${c.S(k.extrude(deckRing, DECK, 0.6, P, { bevel: 0.3 }), { tone: "mid", crease: "lo" })}</g>`);
  out.push(k.faceTextSvg(k.topMatrix([140, 1.5], DECK + 0.6, P, "x"), "LINUX KERNEL", { size: 3, tone: "mid", anchor: "middle" }));
  // container guide sockets (twist-lock dots) on deck for every slot
  const locks = [];
  for (const bx of BAYS) for (const ry of ROWS) locks.push(at([bx + 1, ry + 1, DECK + 0.6]), at([bx + CW - 1, ry + CD - 1, DECK + 0.6]));
  out.push(c.D(locks, { size: 0.45, tone: "lo" }));
  // cleats
  for (const [x, y] of [[-138, -38], [112, -36]]) out.push(c.slab({ x: x - 2, y: y - 1, w: 4, d: 2, r: 0.5 }, DECK, 1.5, { tone: "mid" }, 1));
  // mooring lines from bollards to deck cleats
  out.push(k.wireSvg(at([-140, -96, QZ + 5]), at([-138, -38, DECK + 1.5]), { tone: "lo", size: 0.9 }));
  out.push(k.wireSvg(at([150, -96, QZ + 5]), at([112, -36, DECK + 1.5]), { tone: "lo", size: 0.9 }));

  // bridge at the stern (static, behind the first bay)
  out.push(bridge(c));

  // containers on deck: every slot pre-built, hidden until loaded; painted in depth order
  const S = slots();
  const deck = S.map((s, i) => ({ at: [s.x + CW / 2, s.y + CD / 2, s.z], svg: `<g data-hot data-slot="${i}" style="display:none">${container(c, s.x, s.y, s.z, "hi", true)}</g>` }));
  out.push([...deck].sort((a, b) => c.depth([a.at[0], a.at[1], a.at[2]]) - c.depth([b.at[0], b.at[1], b.at[2]]) || a.at[2] - b.at[2]).map((d) => d.svg).join(""));


  // crane front: girders, trolley, spreader, cables and the carried box (moved live)
  out.push(`<g data-part="crane">${craneFront(c)}</g>`);
  out.push(`<g data-part="load" style="opacity:0">${container(c, -CW / 2, -CD / 2, 0)}</g>`);
  out.push(`<g data-part="spreader">${c.slab({ x: -CW / 2 - 1, y: -CD / 2 - 0.5, w: CW + 2, d: CD + 1, r: 0.6 }, CH, 2.4, { tone: "mid", lit: true }, 1, 0.3)}${c.D([[-12, -4], [12, -4], [-12, 4], [12, 4]].map(([dx, dy]) => at([dx, dy * 1.4, CH + 2.4])), { size: 0.7, tone: "hi" })}</g>`);
  out.push(`<g data-part="cables"><path class="iso-line" data-tone="mid" d=""/></g>`);

  const svg = k.figureSvg({
    width: W,
    height: H,
    label: "一艘停靠在码头的集装箱船。船体代表服务器硬件，甲板代表大家共用的 Linux 内核，甲板上的每个集装箱是一个打包好的应用。码头上的箱子堆代表镜像仓库，岸边的龙门吊把箱子吊上船（启动容器）或吊下来（停止容器）。",
    body: out,
  });
  const body = k.plateHtml({
    fig: "Fig 4",
    title: "Docker",
    hint: "按下面的按钮装卸集装箱",
    readout: "—",
    keys: [
      { mark: "raised", label: "集装箱 = 容器：应用 + 它需要的全部依赖" },
      { mark: "flat", label: "甲板 = 共用的 Linux 内核；船体 = 服务器硬件" },
      { mark: "dim", label: "码头上的箱子堆 = 镜像仓库（如 Docker Hub）" },
    ],
    caption: "码头吊车一次只吊一个箱子。不管箱子里装的是数据库还是大模型，吊车只认标准的箱子外形——这就是容器「在哪都能跑」的原因。",
    body: `<div class="iso-stage" id="f4-stage">${svg}</div>`,
  });
  return { body, P, S };
}

// crane: two portal frames on the quay rails joined by a boom that reaches out over the ship.
// It is built at x = 0 and moved along x as a group. Back legs (y on the quay's far rail) are drawn before the ship.
function craneBack(c) {
  const out = [];
  for (const x of [-16, 16]) out.push(c.slab({ x: x - 2.5, y: -126, w: 5, d: 5, r: 0.8 }, QZ, CRANE_TOP - 10 - QZ, { tone: "mid" }, 1, 0.3));
  out.push(c.slab({ x: -20, y: -127, w: 40, d: 7, r: 1 }, QZ - 0.2, 3, { tone: "lo" }, 1)); // bogie
  return out.join("");
}
function craneMid(c) {
  const out = [];
  out.push(c.slab({ x: -20, y: -101, w: 40, d: 7, r: 1 }, QZ - 0.2, 3, { tone: "lo" }, 1));
  for (const x of [-16, 16]) out.push(c.slab({ x: x - 2.5, y: -100, w: 5, d: 5, r: 0.8 }, QZ + 2.8, CRANE_TOP - 10 - QZ - 2.8, { tone: "mid" }, 1, 0.3));
  return out.join("");
}
function craneFront(c) {
  const { P, at } = c;
  const out = [];
  // portal beam and machinery house
  out.push(c.slab({ x: -20, y: -128, w: 40, d: 34, r: 1 }, CRANE_TOP - 10, 4, { tone: "mid" }, 1, 0.4));
  out.push(c.slab({ x: -12, y: -136, w: 24, d: 18, r: 1 }, CRANE_TOP - 6, 8, { tone: "mid" }, 2, 0.4));
  out.push(c.L(k.sideSeam({ x: -12, y: -136, w: 24, d: 18, r: 1 }, CRANE_TOP - 1, P, 2), { tone: "faint" }));
  // two boom girders out over the water, with cross ties
  for (const x of [-9, 6]) out.push(c.slab({ x, y: -134, w: 3, d: 190, r: 0.5 }, CRANE_TOP - 6, 3, { tone: "mid" }, 1, 0.3));
  for (let y = -120; y <= 50; y += 17) out.push(c.slab({ x: -9, y, w: 18, d: 1.6, r: 0.3 }, CRANE_TOP - 3, 0.8, { tone: "lo", crease: "none" }, 1));
  out.push(c.D([-118, -84, -50, -16, 18, 50].map((y) => at([-7.5, y, CRANE_TOP - 3])), { size: 0.4, tone: "lo" }));
  return out.join("");
}

function bridge(c) {
  const { P } = c;
  const out = [];
  const B = { x: -146, y: -30, w: 28, d: 60, r: 1.5 };
  out.push(c.slab(B, DECK, 26, { tone: "mid" }, 2, 0.5));
  const win = [];
  for (let i = 0; i < 7; i++) win.push(c.slotX(B.x + B.w, B.y + 4 + i * 7.8, B.y + 9.5 + i * 7.8, DECK + 18, DECK + 22));
  for (let i = 0; i < 6; i++) win.push(c.slotX(B.x + B.w, B.y + 6 + i * 9, B.y + 10 + i * 9, DECK + 8, DECK + 11));
  out.push(c.L(win.join(""), { tone: "lo" }));
  const roof = { x: -150, y: -38, w: 36, d: 76, r: 1.5 };
  out.push(c.slab(roof, DECK + 26, 3, { tone: "mid" }, 2, 0.5));
  out.push(c.cyl(-136, 0, 6, DECK + 29, 14, { tone: "mid" }, 24, 0.4));
  out.push(c.L(k.sideArc(-136, 0, 6, DECK + 39, P, 20), { tone: "faint" }));
  out.push(c.cyl(-136, 0, 6.6, DECK + 43, 1.4, { tone: "lo" }, 24));
  out.push(c.cyl(-124, -26, 0.8, DECK + 29, 16, { tone: "mid" }, 8));
  out.push(c.cyl(-124, -26, 2, DECK + 45, 0.8, { tone: "mid" }, 12));
  return out.join("");
}

export function f4Live(P, S) {
  return `
{
  const P = ${JSON.stringify(P)};
  const SLOTS = ${JSON.stringify(S)};
  const APPS = ${JSON.stringify(APPS)};
  const CW = ${CW}, CD = ${CD}, CH = ${CH}, TOP = ${CRANE_TOP}, PICK_Y = ${PICK_Y}, QZ = ${QZ};
  const stage = document.getElementById("f4-stage");
  const readout = stage.closest(".iso-plate").querySelector("[data-readout]");
  const crane = stage.querySelector('[data-part="crane"]'), back = stage.querySelector('[data-part="crane-back"]'), mid = stage.querySelector('[data-part="crane-mid"]');
  const load = stage.querySelector('[data-part="load"]'), spreader = stage.querySelector('[data-part="spreader"]');
  const cable = stage.querySelector('[data-part="cables"] path');
  const slotEl = (i) => stage.querySelector('[data-slot="' + i + '"]');
  const list = document.getElementById("f4-list");
  const still = matchMedia("(prefers-reduced-motion: reduce)");
  let n = 0; // containers on deck
  let pose = { x: 30, y: PICK_Y, z: 70 }; // spreader centre bottom (container bottom), world units
  let queue = [], busy = false, carrying = false, frame = 0;
  const ease = (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  function place() {
    crane.setAttribute("transform", translateAlong(P, [pose.x, 0, 0]));
    back.setAttribute("transform", translateAlong(P, [pose.x, 0, 0]));
    mid.setAttribute("transform", translateAlong(P, [pose.x, 0, 0]));
    load.setAttribute("transform", translateAlong(P, [pose.x, pose.y, pose.z]));
    spreader.setAttribute("transform", translateAlong(P, [pose.x, pose.y, pose.z]));
    const top = TOP - 6, s = pose.z + CH + 2.4;
    let d = "";
    for (const [dx, dy] of [[-12, -4], [12, -4], [-12, 4], [12, 4]]) d += segment([pose.x + dx * 0.5, pose.y + dy, top], [pose.x + dx, pose.y + dy * 1.4, s], P);
    cable.setAttribute("d", d);
  }
  function move(to, ms) {
    return new Promise((done) => {
      const from = { ...pose }, t0 = performance.now();
      if (still.matches) { Object.assign(pose, to); place(); return done(); }
      const step = (now) => {
        const t = Math.min(1, (now - t0) / ms), e = ease(t);
        for (const key of Object.keys(to)) pose[key] = from[key] + (to[key] - from[key]) * e;
        place();
        if (t < 1) requestAnimationFrame(step); else done();
      };
      requestAnimationFrame(step);
    });
  }
  const fade = (on) => { load.style.transition = still.matches ? "none" : "opacity .5s"; load.style.opacity = on ? 1 : 0; };
  async function runOne() {
    if (n >= SLOTS.length) return;
    const s = SLOTS[n], cx = s.x + CW / 2, cy = s.y + CD / 2;
    await move({ y: PICK_Y, z: 64 }, 500);
    await move({ x: cx }, 700);
    await move({ z: QZ + 30 }, 350);
    fade(true);
    await move({ z: s.z + 26 > 64 ? s.z + 26 : 64 }, 450);
    await move({ y: cy }, 800);
    await move({ z: s.z }, 650);
    slotEl(n).style.display = ""; load.style.transition = "none"; load.style.opacity = 0;
    n++; render();
    await move({ z: s.z + 30 }, 450);
  }
  async function stopOne() {
    if (n <= 0) return;
    const s = SLOTS[n - 1], cx = s.x + CW / 2, cy = s.y + CD / 2;
    await move({ z: Math.max(64, s.z + 30) }, 350);
    await move({ x: cx, y: cy }, 800);
    await move({ z: s.z }, 600);
    slotEl(n - 1).style.display = "none"; load.style.transition = "none"; load.style.opacity = 1;
    n--; render();
    await move({ z: Math.max(64, s.z + 30) }, 500);
    await move({ y: PICK_Y }, 800);
    fade(false);
    await move({ z: 64 }, 300);
  }
  async function pump() {
    if (busy) return; busy = true;
    while (queue.length) { const job = queue.shift(); await (job === "run" ? runOne() : stopOne()); }
    busy = false;
  }
  function render() {
    const vmMem = n * 2.0, ctMem = n * 0.06, vmBoot = n ? 40 : 0, ctBoot = n ? 1 : 0;
    readout.textContent = n + " 个容器 · 共用 1 个内核";
    list.innerHTML = Array.from({ length: n }, (_, i) => { const a = APPS[i % APPS.length]; return '<span class="app"><b>' + a[0] + (i >= APPS.length ? "-" + (Math.floor(i / APPS.length) + 1) : "") + '</b> ' + a[1] + '</span>'; }).join("") || '<span class="small">甲板空着——还没有运行任何容器</span>';
    const max = Math.max(1, ${S.length} * 2.0);
    document.getElementById("f4-ct").style.transform = "scaleX(" + (ctMem / max) + ")";
    document.getElementById("f4-vm").style.transform = "scaleX(" + (vmMem / max) + ")";
    document.getElementById("f4-ct-v").textContent = "≈ " + (ctMem * 1024).toFixed(0) + " MB";
    document.getElementById("f4-vm-v").textContent = "≈ " + vmMem.toFixed(0) + " GB";
  }
  document.getElementById("f4-run").addEventListener("click", () => { if (n + queue.filter(q => q === "run").length - queue.filter(q => q === "stop").length < SLOTS.length) { queue.push("run"); pump(); } });
  document.getElementById("f4-stop").addEventListener("click", () => { queue.push("stop"); pump(); });
  // start with three containers already on deck
  for (let i = 0; i < 3; i++) slotEl(i).style.display = "";
  n = 3; render(); place();
}
`;
}
