import { writeFileSync, existsSync } from "node:fs";
import { k } from "./common.mjs";
import { kitScript } from "./scripts/inline-kit.mjs";
import { fig1, F1_LIVE } from "./fig1.mjs";

const figs = {};
figs.f1 = fig1();
const opt = async (name) => (existsSync(`./${name}.mjs`) ? await import(`./${name}.mjs`) : null);
const m23 = await opt("sec23"), m4 = await opt("sec4"), m5 = await opt("sec5");

const light = k.ISO_CSS.match(/\.iso\[data-theme="light"\]\{([^}]*)\}/)[1];
const CSS = `
${k.ISO_CSS}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]) .iso{${light}}}
:root[data-theme="light"] .iso{${light}}
.iso{--anatomy-page:#000;--anatomy-card:#111214;--anatomy-paper:#111214;
  --bg:#000;--paper:#111214;--fg:#e9e6df;--muted:#8d8a84;--line:#26272b;--accent:#e8b04a;--warn:#ff7a6b;--ok:#6be0a0;--chip:#1a1b1f}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]) .iso{--anatomy-page:#f7f3ea;--anatomy-card:#fffdf8;--anatomy-paper:#fffdf8;
  --bg:#f7f3ea;--paper:#fffdf8;--fg:#1d1b18;--muted:#6f6a62;--line:#e3dccd;--accent:#b0781a;--warn:#c4402f;--ok:#2f8f5b;--chip:#f1ebdd}}
:root[data-theme="light"] .iso{--anatomy-page:#f7f3ea;--anatomy-card:#fffdf8;--anatomy-paper:#fffdf8;
  --bg:#f7f3ea;--paper:#fffdf8;--fg:#1d1b18;--muted:#6f6a62;--line:#e3dccd;--accent:#b0781a;--warn:#c4402f;--ok:#2f8f5b;--chip:#f1ebdd}
*{box-sizing:border-box}
html{color-scheme:dark light}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.85 "Times New Roman",Times,"PingFang SC","Heiti SC","Microsoft YaHei","Noto Sans SC",serif;-webkit-font-smoothing:antialiased}
main{width:min(760px,100% - 32px);margin:56px auto 120px}
h1{font-size:clamp(30px,6vw,44px);line-height:1.2;margin:0 0 10px;letter-spacing:.02em;font-weight:600}
h2{font-size:24px;margin:72px 0 6px;font-weight:600}
h2 .n{color:var(--accent);margin-right:10px;font-variant-numeric:tabular-nums}
h3{font-size:17px;margin:28px 0 4px}
p{margin:10px 0}
.lede{color:var(--muted);font-size:17px}
em{color:var(--accent);font-style:normal}
b{font-weight:600}
.toc{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 8px;padding:0;list-style:none}
.toc a{display:inline-block;padding:4px 12px;border:1px solid var(--line);border-radius:999px;color:var(--fg);text-decoration:none;font-size:14px;background:var(--paper)}
.toc a:hover{border-color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:18px 0}
.tile{background:var(--paper);border:1px solid var(--line);padding:12px 14px;border-radius:10px}
.tile .w{font-size:13px;color:var(--muted)}
.tile .t{font-size:17px;font-weight:600;margin:2px 0}
.tile .d{font-size:14px;line-height:1.6}
.controls{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;margin:18px 0 12px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:var(--paper)}
.seg button{font:inherit;font-size:14px;color:var(--muted);background:none;border:0;padding:6px 14px;cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--fg);color:var(--bg)}
.btn{font:inherit;font-size:14px;color:var(--fg);background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 14px;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.slider{display:flex;align-items:center;gap:12px;flex:1 1 280px}
.slider input{flex:1;accent-color:var(--accent)}
.slider output{min-width:72px;text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.presets{display:flex;flex-wrap:wrap;gap:6px}
.presets button{font:inherit;font-size:13px;padding:3px 10px;border-radius:999px;border:1px solid var(--line);background:var(--chip);color:var(--fg);cursor:pointer}
.race{margin:14px 0 4px;display:grid;grid-template-columns:52px 1fr 92px;gap:8px 12px;align-items:center;font-size:14px}
.race .bar{height:10px;border-radius:6px;background:var(--chip);overflow:hidden;border:1px solid var(--line)}
.race .bar i{display:block;height:100%;background:var(--fg);transform-origin:left;transform:scaleX(0)}
.race .v{text-align:right;font-variant-numeric:tabular-nums;color:var(--muted)}
.readrow{display:flex;flex-wrap:wrap;gap:10px 28px;margin:14px 0}
.big{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.1}
.big.warn{color:var(--warn)}
.small{font-size:13px;color:var(--muted)}
.note{border-left:3px solid var(--accent);padding:6px 14px;margin:14px 0;background:var(--paper);font-size:15px}
.cmp{width:100%;border-collapse:collapse;font-size:14.5px;margin:16px 0;background:var(--paper)}
.cmp th,.cmp td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.cmp th{font-weight:600;background:var(--chip)}
.cmp tbody th{white-space:nowrap}
.tablewrap{overflow-x:auto}
.iso-figure{margin:10px 0 0}
[data-part="bus"]{stroke-dasharray:2 6;animation:flow .7s linear infinite}
@keyframes flow{to{stroke-dashoffset:-8}}
@media (prefers-reduced-motion: reduce){[data-part="bus"]{animation:none}}
.iso{--hot-top:#f0b94e;--hot-side:#a8741c;--hot-edge:#ffd27a}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]) .iso{--hot-top:#f5c460;--hot-side:#d79a2c;--hot-edge:#7a4a00}}
:root[data-theme="light"] .iso{--hot-top:#f5c460;--hot-side:#d79a2c;--hot-edge:#7a4a00}
[data-hot] .iso-solid[data-lit]>.iso-top,[data-hot].iso-solid[data-lit]>.iso-top{fill:var(--hot-top)}
[data-hot] .iso-solid[data-lit]>.iso-shade,[data-hot].iso-solid[data-lit]>.iso-shade{fill:var(--hot-side)}
[data-hot] .iso-solid[data-lit]>.iso-edge,[data-hot].iso-solid[data-lit]>.iso-edge{stroke:var(--hot-edge)}
[data-hot] .iso-solid>.iso-top,[data-hot] .iso-solid>.iso-shade{transition:fill .25s}
.iso-plate{padding:46px 14px}
.iso-stage{outline:none}
.iso-legend{font-size:13.5px;line-height:1.6;color:var(--muted)}
.apps{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0;min-height:30px}
.app{font-size:13px;padding:3px 10px;border-radius:6px;background:var(--chip);border:1px solid var(--line)}
.app b{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-weight:600;margin-right:4px}
.cmp td[data-col].on,.cmp th[data-col].on{background:color-mix(in srgb,var(--accent) 12%,var(--paper))}
.foot{margin-top:80px;color:var(--muted);font-size:14px;border-top:1px solid var(--line);padding-top:18px}
@media (max-width:520px){.iso-plate{padding:40px 6px}.race{grid-template-columns:44px 1fr 80px}h2{margin-top:56px}}
`;

const sec = (id, n, title, html) => `<section id="${id}"><h2><span class="n">${n}</span>${title}</h2>${html}</section>`;

const intro = `
<h1 class="lab-intro">电脑里到底有什么</h1>
<p class="lede lab-intro">CPU、GPU、内存、显存、统一内存、Docker、服务器——一次讲清。每张图都是一台可以「动手」的小机器：点按钮、拖滑块，看它怎么干活。</p>
<ul class="toc">
  <li><a href="#kitchen">先打个比方</a></li><li><a href="#cpu-gpu">CPU 与 GPU</a></li><li><a href="#memory">内存与显存</a></li>
  <li><a href="#unified">统一内存</a></li><li><a href="#docker">Docker</a></li><li><a href="#server">服务器 vs 个人电脑</a></li>
</ul>`;

const kitchen = sec("kitchen", "0", "先打个比方：电脑是一间厨房", `
<p>把电脑想成一间餐厅后厨，下面每个零件都能在厨房里找到对应的角色。后面所有内容都会回到这个比方。</p>
<div class="grid">
  <div class="tile"><div class="w">CPU · 中央处理器</div><div class="t">主厨</div><div class="d">人少（几个到几十个），但每个都很全能，什么复杂菜都会做，会随机应变。</div></div>
  <div class="tile"><div class="w">GPU · 图形处理器</div><div class="t">上万个帮厨</div><div class="d">每个只会简单动作（切、搅），但人多，同时开工时快得惊人。</div></div>
  <div class="tile"><div class="w">内存 RAM</div><div class="t">主厨的操作台</div><div class="d">正在做的菜放这里，拿取飞快；一断电台面就清空。</div></div>
  <div class="tile"><div class="w">显存 VRAM</div><div class="t">帮厨们自己的操作台</div><div class="d">离 GPU 最近、最快，但面积小且贵。</div></div>
  <div class="tile"><div class="w">硬盘 SSD</div><div class="t">仓库 / 冰箱</div><div class="d">容量大、断电不丢，但取东西要走一趟，慢得多。</div></div>
</div>`);

const s1 = sec("cpu-gpu", "1", "CPU 与 GPU：少数精英 vs 人海战术", `
<p><b>CPU</b>（Central Processing Unit，中央处理器）是电脑的「大脑」：打开软件、算表格、判断「如果…就…」，都是它在做。它的核心（core，可以理解成一个独立干活的工人）通常只有 8～16 个，但每个都<em>很聪明</em>：频率高、会预判下一步、会插队处理，特别擅长<b>一步接一步、前一步决定后一步</b>的活。</p>
<p><b>GPU</b>（Graphics Processing Unit，图形处理器，也就是「显卡」上的那颗芯片）原本是为画游戏画面设计的：屏幕上几百万个像素，每个都要做一模一样的计算。所以它的思路完全相反——塞进<em>成千上万个简单核心</em>（RTX 4090 有 16 384 个），每个都不聪明，但可以<b>同时</b>干同样的活。AI 训练和推理本质上就是海量的乘法加法，正好是 GPU 的主场。</p>
<div class="controls"><span class="seg" role="group" aria-label="任务类型">
  <button data-f1="parallel" aria-pressed="true">大量简单任务（并行）</button>
  <button data-f1="serial" aria-pressed="false">一长串接力任务（串行）</button></span></div>
${figs.f1.body}
<div class="race" aria-live="polite">
  <span>CPU</span><span class="bar"><i id="f1-bar-cpu"></i></span><span class="v" id="f1-t-cpu">—</span>
  <span>GPU</span><span class="bar"><i id="f1-bar-gpu"></i></span><span class="v" id="f1-t-gpu">—</span>
</div>
<p class="small">进度条只按比例显示快慢；右侧是按公开规格估算的真实耗时：并行任务 = 1 万亿次乘加（8 核 CPU 约 1.2 TFLOPS，RTX 4090 约 82.6 TFLOPS）；串行任务 = 10 亿步、每步依赖上一步（CPU 单核约 5.4 GHz、每周期一步；GPU 单核约 2.5 GHz、每步约 4 个周期）。实际快慢还取决于程序写法，这里只看数量级。</p>
<div class="note"><b>注意看：</b>切到「串行」时，GPU 上 128 组核心只有一组亮着，其余全在发呆——活没法拆开，人再多也没用。这就是为什么电脑离不开 CPU，而 AI 离不开 GPU。</div>
`);

const s2 = m23 ? sec("memory", "2", "内存与显存：两张分开的操作台", m23.html2()) : "";
const s3 = m23 ? sec("unified", "3", "统一内存：大家共用一张大桌子", m23.html3()) : "";
const s4 = m4 ? sec("docker", "4", "Docker：把软件装进集装箱", m4.html()) : "";
const s5 = m5 ? sec("server", "5", "服务器 vs 个人电脑", m5.html()) : "";

const outro = `<div class="foot">
<b>一句话复习：</b>CPU 是少数全能主厨，GPU 是上万个帮厨；内存是 CPU 的操作台，显存是 GPU 的操作台，中间隔着一条窄通道；统一内存把两张台子合成一张；Docker 把软件连同它需要的一切装进标准集装箱；服务器是为 7×24 小时、多人同时使用而造的电脑。
</div>`;

const live = [F1_LIVE, m23?.LIVE, m4?.LIVE, m5?.LIVE].filter(Boolean).join("\n");
const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>电脑里有什么</title><style>${CSS}</style><script>if(window.self!==window.top)document.documentElement.classList.add("embedded")</script><style>html.embedded .lab-intro{display:none}html.embedded .wrap{padding-top:20px}html.embedded main{margin-top:28px}html.embedded .lab-intro+section{margin-top:0}</style></head>
<body class="iso"><main>${intro}${kitchen}${s1}${s2}${s3}${s4}${s5}${outro}</main>
<script type="module">${(kitScript() + "\n" + live).replace(/<\/(script)/gi, "<\\/$1")}</script></body></html>`;
writeFileSync("index.html", html);
console.log("wrote index.html", (html.length / 1024).toFixed(0) + " KB");
