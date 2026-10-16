import { fig2, pcSplit, PC } from "./fig2.mjs";
import { fig3, macSplit, MAC } from "./fig3.mjs";

const presets = [
  [8, "8B 模型 · 8-bit"],
  [14, "7B · FP16"],
  [20, "32B · 4-bit"],
  [40, "70B · 4-bit"],
  [75, "70B · 8-bit"],
  [140, "70B · FP16"],
];
const control = (id) => `<div class="controls">
  <label class="slider">模型大小 <input type="range" min="1" max="160" step="1" value="40" data-size id="${id}" aria-label="模型大小（GB）"><output data-size-out>40 GB</output></label>
  <div class="presets">${presets.map(([v, t]) => `<button data-preset="${v}">${t}</button>`).join("")}</div></div>`;

export function html2() {
  return `
<p><b>内存</b>（RAM，Random Access Memory）是 CPU 的操作台：程序打开后，它要用的数据都先从硬盘搬到内存里，因为内存比硬盘快上百倍。关机后内存清空——这就是没保存的文档会丢的原因。</p>
<p><b>显存</b>（VRAM，Video RAM）是焊在显卡上、专门给 GPU 用的内存。GPU 那上万个核心同时开工，胃口极大，所以显存做得<em>特别快</em>（RTX 4090 带宽约 1 TB/s，是普通内存的 10 倍以上），代价是<em>贵且小</em>：一张顶级游戏卡也只有 24 GB。</p>
<p>关键在于：在普通电脑里，这两张台子是<b>分开的</b>，中间只靠一条 PCIe 通道相连，大约 32 GB/s——比显存慢 30 倍。所以跑 AI 模型时，最重要的问题往往不是「GPU 算得多快」，而是「<b>模型能不能整个塞进显存</b>」。</p>
${control("f2-size")}
${fig2()}
<div class="readrow">
  <div><div class="big" id="f2-tps">—</div><div class="small">最快生成速度（token/s），独显电脑</div></div>
  <div><div class="big" id="f2-where" style="font-size:20px">—</div><div class="small">模型放在哪里</div></div>
</div>
<p class="small">估算方法：大模型每生成一个 token，都要把全部参数从内存里读一遍，所以速度上限 ≈ 内存带宽 ÷ 模型大小。放在显存里的部分按 1008 GB/s 算，溢出到内存的部分由 CPU 按约 90 GB/s 算，再放不下就只能从 SSD（约 7 GB/s）读。真实速度会再低一些。</p>
<div class="note"><b>注意看：</b>把滑块从 20 GB 拖到 30 GB——只多了一点点，速度却断崖式下跌。因为多出来的那 6 GB 掉到了慢十倍的内存里，整体被它拖慢。</div>`;
}

export function html3() {
  return `
<p>苹果 M 系列芯片（以及一些新的 AMD、英伟达芯片）换了个思路：<b>不分家</b>。CPU、GPU 和神经网络引擎做在同一颗芯片上，内存颗粒直接贴在芯片旁边，大家共用一个内存池——这就叫<b>统一内存</b>（Unified Memory）。</p>
<p>好处是两张台子合成一张：GPU 能用的「显存」就是全部内存，128 GB 的机器可以装下独显电脑根本放不进显存的大模型；而且数据不用在 CPU 和 GPU 之间搬来搬去。代价是速度：546 GB/s 比 4090 的显存慢一截，而且内存焊死、买了就不能加。</p>
${control("f3-size")}
${fig3()}
<div class="readrow">
  <div><div class="big" id="f3-tps">—</div><div class="small">最快生成速度（token/s），统一内存</div></div>
  <div><div class="big" id="f2b-tps" style="opacity:.55">—</div><div class="small">同一个模型，独显电脑（对比）</div></div>
</div>
<div class="note" id="f3-note"><b>注意看：</b>模型小时，独显电脑更快（显存带宽更高）；模型一旦超出 24 GB 显存一截（约 27 GB 以上），统一内存反超——它不用把模型拆到慢速内存里。这就是很多人买大内存 Mac 跑本地大模型的原因。</div>
<p class="small">macOS 默认只允许 GPU 使用约 75% 的统一内存（128 GB 机器约 96 GB），可以手动调高。</p>`;
}

export const LIVE = `
{
  const PC = ${JSON.stringify(PC)}, MAC = ${JSON.stringify(MAC)};
  const pcSplit = ${pcSplit.toString()};
  const macSplit = ${macSplit.toString()};
  const s2 = document.getElementById("f2-stage"), s3 = document.getElementById("f3-stage");
  const r2 = s2.closest(".iso-plate").querySelector("[data-readout]"), r3 = s3.closest(".iso-plate").querySelector("[data-readout]");
  const lit = (g, on) => { const el = g.querySelector(".iso-solid"); if (on) el.setAttribute("data-lit", ""); else el.removeAttribute("data-lit"); };
  const vram = [...s2.querySelectorAll("[data-vram]")].sort((a, b) => a.dataset.vram - b.dataset.vram);
  const ram = [...s2.querySelectorAll("[data-ram]")].sort((a, b) => a.dataset.ram - b.dataset.ram);
  const mem = [...s3.querySelectorAll("[data-mem]")].sort((a, b) => a.dataset.mem - b.dataset.mem);
  const units = [...s3.querySelectorAll('[data-unit="cpu"],[data-unit="gpu"]')];
  const fmt = (t) => t >= 10 ? t.toFixed(0) : t >= 1 ? t.toFixed(1) : t.toFixed(2);
  function set(S) {
    S = +S;
    document.querySelectorAll("[data-size]").forEach(i => { if (+i.value !== S) i.value = S; });
    document.querySelectorAll("[data-size-out]").forEach(o => o.textContent = S + " GB");
    const p = pcSplit(S), m = macSplit(S);
    vram.forEach((g, i) => lit(g, i < Math.ceil(p.v / 2 - 1e-9)));
    ram.forEach((g, i) => lit(g, i < Math.ceil(p.r / 4 - 1e-9)));
    lit(s2.querySelector('[data-part="ssd"]'), p.d > 0);
    lit(s2.querySelector('[data-part="gpu"]'), true);
    lit(s2.querySelector('[data-part="cpu"]'), p.r > 0);
    s2.querySelector('[data-part="bus"]').style.opacity = p.r > 0 ? 1 : 0;
    mem.forEach((g, i) => lit(g, i < Math.ceil(m.m / 16 - 1e-9)));
    units.forEach(g => lit(g, true));
    s3.querySelector('[data-part="mbus"]').style.opacity = 1;
    r2.textContent = "显存 " + p.v.toFixed(0) + "/24 · 内存 " + p.r.toFixed(0) + "/64" + (p.d > 0 ? " · 溢出到硬盘 " + p.d.toFixed(0) : "") + " GB";
    r3.textContent = "统一内存 " + m.m.toFixed(0) + "/128 GB" + (m.d > 0 ? " · 溢出到硬盘 " + m.d.toFixed(0) : "");
    const t2 = document.getElementById("f2-tps"), t3 = document.getElementById("f3-tps"), tb = document.getElementById("f2b-tps");
    t2.textContent = "≈ " + fmt(p.tps) + " token/s"; t2.classList.toggle("warn", p.tps < 5);
    t3.textContent = "≈ " + fmt(m.tps) + " token/s"; t3.classList.toggle("warn", m.tps < 5);
    tb.textContent = "≈ " + fmt(p.tps) + " token/s";
    document.getElementById("f2-where").textContent = p.d > 0 ? "显存 + 内存 + 硬盘（几乎不可用）" : p.r > 0 ? "显存放不下，拆一部分到内存" : "整个放进显存 ✓";
  }
  document.querySelectorAll("[data-size]").forEach(i => i.addEventListener("input", () => set(i.value)));
  document.querySelectorAll("[data-preset]").forEach(b => b.addEventListener("click", () => set(b.dataset.preset)));
  set(40);
}
`;
