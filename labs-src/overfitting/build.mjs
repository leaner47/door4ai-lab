// 过拟合一讲：用 core.js 算出全部数字、用 plot.js 画全部分镜图，
// 把 article.src.md 里的 {{figN}} / {{n:名字}} / {{tab:名字}} 填好写到 src/content/blog/overfitting.md，
// 再把 core.js、plot.js 原样内联进 lab.src.html，写出 public/labs/overfitting/index.html。
// 运行：node labs-src/overfitting/build.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const coreSrc = fs.readFileSync(path.join(HERE, 'core.js'), 'utf8');
const plotSrc = fs.readFileSync(path.join(HERE, 'plot.js'), 'utf8');
const C = new Function(coreSrc + ';return CORE;')();
const P = new Function(plotSrc + ';return PLOT;')();
const { TRAIN, VAL, TEST, f, polyfit, polyval, mse } = C;
const { frame, axes, curve, points, resid, svg, text, line, mi, pow10, polyline, dot } = P;

const N = {}, T = {}, FIG = {};
// 数字格式：正文用 −，公式里用 -
const fx = (v, d = 3) => { let s = v.toFixed(d); if (/^-0\.?0*$/.test(s)) s = s.slice(1); return s; };
const tx = (v, d = 3) => fx(v, d).replace('-', '−');
const mx = (v, d = 3) => fx(v, d);
const pc = (v, d = 1) => (v * 100).toFixed(d) + '%';
const big = (v) => { const a = Math.abs(v); if (a < 1000) return tx(v, 1); const e = Math.floor(Math.log10(a)); const m = v / Math.pow(10, e); return `${tx(m, 2)} × 10^${e}`; };
const bigm = (v) => { const a = Math.abs(v); if (a < 1000) return mx(v, 1); const e = Math.floor(Math.log10(a)); const m = v / Math.pow(10, e); return `${mx(m, 2)} \\times 10^{${e}}`; };
const fig = (label, body, cap) => `<figure class="fig">\n${body}\n<figcaption>${cap}</figcaption>\n</figure>`;
const pred = (w) => (x) => polyval(w, x);
const errs = (w) => ({ tr: mse(pred(w), TRAIN), va: mse(pred(w), VAL), te: mse(pred(w), TEST) });

// ———— 数据 ————
T.data = '| 组 | 10 个点 $(x,\\ y)$ |\n| --- | --- |\n' + [['训练集', TRAIN], ['验证集', VAL], ['测试集', TEST]].map(([nm, s]) => `| ${nm} | ${s.map(p => `(${tx(p.x, 2)}, ${tx(p.y, 2)})`).join(' ')} |`).join('\n');
T.train = '| 第几个 | $x$ | $y$ |\n| --- | --- | --- |\n' + TRAIN.map((p, i) => `| ${i + 1} | ${tx(p.x, 2)} | ${tx(p.y, 2)} |`).join('\n');

// ———— 0 阶与 1 阶（手算） ————
const xbar = TRAIN.reduce((s, p) => s + p.x, 0) / 10, ybar = TRAIN.reduce((s, p) => s + p.y, 0) / 10;
const sumY = TRAIN.reduce((s, p) => s + p.y, 0);
const Syy = TRAIN.reduce((s, p) => s + (p.y - ybar) ** 2, 0);
const Sxy = TRAIN.reduce((s, p) => s + (p.x - xbar) * (p.y - ybar), 0), Sxx = TRAIN.reduce((s, p) => s + (p.x - xbar) ** 2, 0);
const w1 = Sxy / Sxx, w0 = ybar - w1 * xbar;
Object.assign(N, { sumX: mx(TRAIN.reduce((s, p) => s + p.x, 0), 2), xbar: mx(xbar, 1), sumY: mx(sumY, 2), ybar: mx(ybar, 3), Syy: mx(Syy, 4), mse0: mx(Syy / 10, 4), Sxy: mx(Sxy, 4), Sxx: mx(Sxx, 4), w1: mx(w1, 3), w0: mx(w0, 3) });
T.deg0 = '| 第几个 | $y$ | $y - \\bar y$ | $(y - \\bar y)^2$ |\n| --- | --- | --- | --- |\n' + TRAIN.map((p, i) => `| ${i + 1} | ${tx(p.y, 2)} | ${tx(p.y - ybar, 3)} | ${tx((p.y - ybar) ** 2, 4)} |`).join('\n');
T.deg1a = '| 第几个 | $x - \\bar x$ | $y - \\bar y$ | $(x - \\bar x)(y - \\bar y)$ | $(x - \\bar x)^2$ |\n| --- | --- | --- | --- | --- |\n' + TRAIN.map((p, i) => `| ${i + 1} | ${tx(p.x - xbar, 2)} | ${tx(p.y - ybar, 3)} | ${tx((p.x - xbar) * (p.y - ybar), 5)} | ${tx((p.x - xbar) ** 2, 4)} |`).join('\n') + `\n| 合计 | | | ${tx(Sxy, 5)} | ${tx(Sxx, 4)} |`;
const r1 = TRAIN.map(p => { const yh = w0 + w1 * p.x; return { yh, e: p.y - yh, e2: (p.y - yh) ** 2 }; });
const SSE1 = r1.reduce((s, r) => s + r.e2, 0);
T.deg1b = '| 第几个 | $x$ | $y$ | $\\hat y = w_0 + w_1 x$ | $y - \\hat y$ | $(y - \\hat y)^2$ |\n| --- | --- | --- | --- | --- | --- |\n' + TRAIN.map((p, i) => `| ${i + 1} | ${tx(p.x, 2)} | ${tx(p.y, 2)} | ${tx(r1[i].yh, 3)} | ${tx(r1[i].e, 3)} | ${tx(r1[i].e2, 4)} |`).join('\n');
Object.assign(N, { SSE1: mx(SSE1, 4), mse1: mx(SSE1 / 10, 4), yh1_1: mx(r1[0].yh, 3), x1: mx(TRAIN[0].x, 2), y1: mx(TRAIN[0].y, 2), e1_1: mx(r1[0].e, 3), e21_1: mx(r1[0].e2, 4) });

// ———— 0 到 9 阶 ————
const W = [], E = [];
for (let d = 0; d <= 9; d++) { W[d] = polyfit(TRAIN, d); E[d] = errs(W[d]); }
let bestD = 0; for (let d = 1; d <= 9; d++) if (E[d].va < E[bestD].va) bestD = d;
T.degs = '| 阶数 $d$ | 系数个数 | 训练误差 | 验证误差 |\n| --- | --- | --- | --- |\n' + E.map((e, d) => `| ${d} | ${d + 1} | ${d === 9 ? '0.0000' : tx(e.tr, 4)} | ${e.va > 10 ? tx(e.va, 1) : tx(e.va, 4)} |`).join('\n');
T.degsTest = '| 阶数 $d$ | 训练误差 | 验证误差 | 测试误差 |\n| --- | --- | --- | --- |\n' + [1, 3, 9].map(d => `| ${d} | ${d === 9 ? '0.0000' : tx(E[d].tr, 4)} | ${E[d].va > 10 ? tx(E[d].va, 1) : tx(E[d].va, 4)} | ${E[d].te > 10 ? tx(E[d].te, 1) : tx(E[d].te, 4)} |`).join('\n');
N.bestD = String(bestD);
for (const d of [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]) { N['tr' + d] = d === 9 ? '0' : mx(E[d].tr, 4); N['va' + d] = E[d].va > 10 ? mx(E[d].va, 1) : mx(E[d].va, 4); N['te' + d] = E[d].te > 10 ? mx(E[d].te, 1) : mx(E[d].te, 4); }
N.w3 = W[3].map((v, j) => `w_${j} = ${mx(v, 2)}`).join(',\\ ');
N.w9max = bigm(Math.max(...W[9].map(Math.abs)));
N.w9list = W[9].map((v, j) => `w_${j} = ${bigm(v)}`);
N.w9rows = W[9].map((v, j) => `w_{${j}} &= ${bigm(v)}`).join(' \\\\\n');
N.sumW9sq = bigm(W[9].slice(1).reduce((s, v) => s + v * v, 0));
// 验证集上逐点比较 3 阶与 9 阶
T.val39 = '| $x$ | $y$ | 3 阶 $\\hat y$ | $(\\hat y - y)^2$ | 9 阶 $\\hat y$ | $(\\hat y - y)^2$ |\n| --- | --- | --- | --- | --- | --- |\n' + VAL.map(p => { const a = polyval(W[3], p.x), b = polyval(W[9], p.x); return `| ${tx(p.x, 2)} | ${tx(p.y, 2)} | ${tx(a, 3)} | ${tx((a - p.y) ** 2, 4)} | ${tx(b, 3)} | ${tx((b - p.y) ** 2, 3)} |`; }).join('\n');
const s3 = VAL.reduce((s, p) => s + (polyval(W[3], p.x) - p.y) ** 2, 0), s9 = VAL.reduce((s, p) => s + (polyval(W[9], p.x) - p.y) ** 2, 0);
Object.assign(N, { sumV3: mx(s3, 4), sumV9: mx(s9, 2), v9at01: mx(polyval(W[9], 0.1), 2), v9at088: mx(polyval(W[9], 0.88), 2), v9at093: mx(polyval(W[9], 0.93), 2) });

// 图 1：真实规律 + 训练点
const yR = [-2, 2];
{
  const F = frame(48, 20, 412, 220, [0, 1], yR);
  const b = axes(F, { xt: [0, 0.5, 1], yt: [-2, -1, 0, 1, 2], xl: '', zero: true, xfmt: String, yfmt: (t) => String(t).replace('-', '−') })
    + text(F.x0 + F.w, F.y0 + F.h + 34, mi('x'), 'muted', 16, 'end') + text(F.x0 + 6, F.y0 + 6, mi('y'), 'muted', 16)
    + curve(F, f, 'muted', 2, '6 5') + points(F, TRAIN, 'accent', 5.5)
    + text(F.X(0.52), F.Y(1.25), '真实规律（模型看不到）', 'muted', 15, 'start')
    + text(F.X(0.17) + 10, F.Y(1.48) + 5, '(0.17, 1.48)', 'accent', 15);
  FIG.fig1 = fig('', svg(480, 280, '真实规律和 10 个训练点', b), '图 1　灰色虚线是真实规律 <i>y</i> = sin 2π<i>x</i>，模型看不到它。蓝点是加了噪声之后量到的 10 个训练点，这是模型唯一能看到的东西。');
}
// 图 2：1 阶直线 + 残差
{
  const F = frame(48, 20, 412, 220, [0, 1], yR);
  const fn = pred(W[1]);
  const b = axes(F, { xt: [0, 0.5, 1], yt: [-2, -1, 0, 1, 2], zero: true, yfmt: (t) => String(t).replace('-', '−') })
    + curve(F, f, 'muted', 2, '6 5') + resid(F, TRAIN, fn, 'accent', 1.5) + curve(F, fn, 'fg', 2.5) + points(F, TRAIN, 'accent', 5.5)
    + text(F.X(0.62), F.Y(1.45), `ŷ = ${tx(w0, 3)} ${w1 < 0 ? '−' : '+'} ${tx(Math.abs(w1), 3)} x`.replace('ŷ', `<tspan font-style="italic">ŷ</tspan>`).replace(/ x$/, ` <tspan font-style="italic">x</tspan>`), 'fg', 16);
  FIG.fig2 = fig('', svg(480, 270, '用一条直线拟合 10 个训练点，竖线是每个点的误差', b), `图 2　黑线是 1 阶多项式（直线）的最好拟合。蓝色虚竖线是每个训练点到直线的距离 <i>y</i> − <i>ŷ</i>，把它们平方再平均，就是训练误差 ${N.mse1}。`);
}
// 2 × 2 小图
function grid4(panels, label, cap, opt = {}) {
  let b = ''; const pw = 214, ph = 130;
  panels.forEach((pn, i) => {
    const cx = i % 2, cy = Math.floor(i / 2), x0 = 22 + cx * 236, y0 = 30 + cy * 172;
    const F = frame(x0, y0, pw, ph, [0, 1], opt.yr || yR);
    b += line(F.x0, F.y0 + F.h, F.x0 + F.w, F.y0 + F.h) + line(F.x0, F.y0, F.x0, F.y0 + F.h) + line(F.x0, F.Y(0), F.x0 + F.w, F.Y(0), 'line', 1, '3 4');
    b += curve(F, f, 'muted', 1.6, '5 4');
    if (pn.extra) b += pn.extra(F);
    if (pn.fn) b += curve(F, pn.fn, 'fg', 2.2);
    if (pn.val) b += (pn.resid ? resid(F, VAL, pn.fn, 'warn', 1.3) : '') + points(F, VAL, 'warn', 4.2);
    if (pn.train !== false) b += points(F, pn.pts || TRAIN, 'accent', 4.2);
    b += text(x0, y0 - 9, pn.title, 'fg', 15);
    if (pn.note) b += text(x0 + pw, y0 - 9, pn.note, pn.noteCol || 'muted', 14, 'end');
  });
  return fig(label, svg(480, 346, label, b), cap);
}
FIG.fig3 = grid4([0, 1, 3, 9].map(d => ({ title: `${d} 阶`, fn: pred(W[d]), note: `训练误差 ${d === 9 ? '0' : tx(E[d].tr, 3)}`, noteCol: 'accent' })), '0、1、3、9 阶多项式拟合同一组训练点',
  '图 3　同一组 10 个训练点，分别用 0、1、3、9 阶多项式去拟合。阶数越高，曲线越能弯，训练误差越小；9 阶穿过了全部 10 个点，训练误差是 0。');
FIG.fig4 = grid4([3, 9].flatMap(d => [{ title: `${d} 阶 · 训练点`, fn: pred(W[d]), note: `训练 ${d === 9 ? '0' : tx(E[d].tr, 3)}`, noteCol: 'accent' }, { title: `${d} 阶 · 验证点`, fn: pred(W[d]), val: true, resid: true, train: false, note: `验证 ${E[d].va > 10 ? tx(E[d].va, 1) : tx(E[d].va, 3)}`, noteCol: 'warn' }]), '3 阶和 9 阶在训练点和验证点上的表现',
  '图 4　上排 3 阶，下排 9 阶；左边是训练点（蓝），右边换成模型没见过的验证点（橙），橙色虚竖线是误差。9 阶在训练点上一分不差，在验证点上两头飞出了画面。');
// 误差随阶数（对数纵轴）
function errChart(xs, tr, va, o) { return fig(o.label, svg(o.w || 480, o.h || 270, o.label, P.errChart(xs, tr, va, o)), o.cap); }
const D10 = [...Array(10).keys()];
FIG.fig5 = errChart(D10, D10.map(d => Math.max(E[d].tr, 1e-2)), D10.map(d => E[d].va), { xl: '阶数 d', mark: { x: bestD, y: E[bestD].va, label: `最低 ${tx(E[bestD].va, 3)}`, dy: -14, dx: 6, anchor: 'start' }, label: '训练误差和验证误差随阶数变化', cap: `图 5　蓝线是训练误差，一路往下（9 阶是 0，画在最底下）；橙色虚线是验证误差，先降后升，在 ${bestD} 阶最低。绿色点线是噪声的方差 0.0625：任何模型在新数据上平均都很难低于它。纵轴每一格是 10 倍。` });

// ———— 测试集：三份数据的分工图 ————
{
  let b = '';
  const box = (x, y, w, h, col, title, lines) => {
    let s = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" style="fill:var(--${col});fill-opacity:0.10;stroke:var(--${col});stroke-width:1.6"/>`;
    s += text(x + w / 2, y + 26, title, col, 16, 'middle', ' font-weight="600"');
    lines.forEach((l, i) => { s += text(x + w / 2, y + 52 + i * 22, l, 'fg', 14, 'middle'); });
    return s;
  };
  b += box(8, 14, 148, 140, 'accent', '训练集 10 个', ['用来算系数', '每个阶数各拟合一次', '像平时的作业题']);
  b += box(166, 14, 148, 140, 'warn', '验证集 10 个', ['用来挑阶数', '比较 10 个模型', '像模拟考']);
  b += box(324, 14, 148, 140, 'ok', '测试集 10 个', ['挑完之后只用一次', '报告最终成绩', '像高考']);
  b += text(240, 186, '训练集决定参数，验证集决定超参数，测试集只负责打分', 'muted', 15, 'middle');
  FIG.fig6 = fig('', svg(480, 200, '训练集、验证集、测试集的分工', b), '图 6　三份数据互不重叠，各管一件事。');
}

// ———— 偏差与方差 ————
const R = 1000;
const BV = []; for (let d = 0; d <= 9; d++) BV[d] = C.biasVar(d, R);
const X0 = 0.2;
function atPoint(d) {
  const ps = BV[d].fits.map(w => polyval(w, X0)); const m = ps.reduce((a, c) => a + c, 0) / R;
  const v = ps.reduce((a, c) => a + (c - m) ** 2, 0) / R; const b = m - f(X0);
  // 直接模拟：每次再抽一个新的 y 来考
  const G = C.rng(99); let e = 0; ps.forEach(p => { const y = f(X0) + C.SIGMA * G.n(); e += (p - y) ** 2; }); e /= R;
  return { ps, m, v, b, e };
}
const A1 = atPoint(1), A3 = atPoint(3), A9 = atPoint(9);
Object.assign(N, { fx0: mx(f(X0), 3), R: String(R) });
for (const [k, A] of [['1', A1], ['3', A3], ['9', A9]]) {
  N['p5_' + k] = A.ps.slice(0, 5).map(v => mx(v, 3)).join(',\\ ');
  N['m_' + k] = mx(A.m, 3); N['b_' + k] = mx(A.b, 3); N['b2_' + k] = mx(A.b * A.b, 4); N['v_' + k] = mx(A.v, 4);
  N['sum_' + k] = mx(A.b * A.b + A.v + C.SIGMA ** 2, 4); N['e_' + k] = mx(A.e, 4);
}
for (let d = 0; d <= 9; d++) { N['bias2_' + d] = mx(BV[d].bias2, 4); N['var_' + d] = BV[d].variance > 10 ? mx(BV[d].variance, 1) : mx(BV[d].variance, 4); }
T.bv = '| 阶数 $d$ | 偏差² | 方差 | 偏差² + 方差 + 噪声 0.0625 |\n| --- | --- | --- | --- |\n' + BV.map((q, d) => `| ${d} | ${tx(q.bias2, 4)} | ${q.variance > 10 ? tx(q.variance, 2) : tx(q.variance, 4)} | ${tx(q.bias2 + q.variance + 0.0625, 4)} |`).join('\n');
{
  let b = ''; const pw = 214, ph = 200;
  [1, 9].forEach((d, i) => {
    const x0 = 22 + i * 236, y0 = 30; const F = frame(x0, y0, pw, ph, [0, 1], [-2.5, 2.5]);
    b += line(F.x0, F.y0 + F.h, F.x0 + F.w, F.y0 + F.h) + line(F.x0, F.y0, F.x0, F.y0 + F.h);
    BV[d].fits.slice(0, 20).forEach(w => { b += curve(F, pred(w), 'accent', 1, null, 160, [0.02, 0.95]); });
    b += curve(F, f, 'muted', 2, '5 4');
    b += polyline(F, BV[d].gx, BV[d].mean, 'warn', 3);
    b += line(F.X(X0), F.y0, F.X(X0), F.y0 + F.h, 'line', 1, '2 3');
    b += text(x0, y0 - 9, `${d} 阶：20 次重抽`, 'fg', 15) + text(F.X(X0) + 4, F.y0 + F.h - 6, mi("x") + " = 0.2", 'muted', 13);
  });
  b += text(22, 258, '细蓝线：每次重抽噪声后的拟合　粗橙线：1000 次的平均　灰虚线：真实规律', 'muted', 13);
  FIG.fig7 = fig('', svg(480, 268, '1 阶和 9 阶在重抽噪声后的拟合曲线', b), '图 7　训练点的 <i>x</i> 不变，只把噪声重新抽 1000 次，每次重新拟合（这里画出前 20 条）。1 阶的 20 条线挤在一起，但平均线（橙）离真实规律很远；9 阶的平均线几乎贴着真实规律，单条线却东倒西歪。');
}
{
  const xs = D10; const b2 = xs.map(d => Math.max(BV[d].bias2, 1e-4)), vv = xs.map(d => BV[d].variance), tot = xs.map(d => BV[d].bias2 + BV[d].variance + 0.0625);
  const F = frame(56, 28, 400, 190, [0, 9], [-4, 1], true);
  let b = axes(F, { xt: xs, yt: [-4, -3, -2, -1, 0, 1], yfmt: pow10 }) + text(F.x0 + F.w, F.y0 + F.h + 40, '阶数 d', 'muted', 15, 'end');
  b += polyline(F, xs, b2, 'accent', 2.5) + polyline(F, xs, vv, 'warn', 2.5, '6 4') + polyline(F, xs, tot, 'fg', 2);
  b += line(F.x0, F.Y(0.0625), F.x0 + F.w, F.Y(0.0625), 'ok', 1.2, '2 4');
  let bd = 0; tot.forEach((t, d) => { if (t < tot[bd]) bd = d; });
  b += dot(F.X(bd), F.Y(tot[bd]), 'fg', 6, true);
  b += text(F.X(4.6), F.Y(0.004), '— 偏差²', 'accent', 14) + text(F.X(4.6), F.Y(0.004) + 18, '- - 方差', 'warn', 14) + text(F.X(6.6), F.Y(0.004), '— 三项之和', 'fg', 14) + text(F.X(6.6), F.Y(0.004) + 18, '··· 噪声', 'ok', 14);
  N.bvBest = String(bd);
  FIG.fig8 = fig('', svg(480, 270, '偏差平方、方差和总误差随阶数变化', b), `图 8　蓝线是偏差²，阶数越高越小；橙色虚线是方差，阶数越高越大；黑线是三项之和（偏差² + 方差 + 噪声），在 ${bd} 阶最低。纵轴是对数刻度。`);
}

// ———— L2 正则化 ————
const LAMS = []; for (let k = -10; k <= 0; k += 0.25) LAMS.push(k);
const LE = LAMS.map(k => { const w = polyfit(TRAIN, 9, Math.pow(10, k)); return { k, w, ...errs(w) }; });
let bl = LE[0]; for (const q of LE) if (q.va < bl.va) bl = q;
const L3 = polyfit(TRAIN, 9, 1e-3), E3 = errs(L3);
const pen3 = 1e-3 * L3.slice(1).reduce((s, v) => s + v * v, 0), sse3 = E3.tr * 10;
Object.assign(N, { lamBestK: String(bl.k), lamBestVa: mx(bl.va, 4), lamBestTr: mx(bl.tr, 4), l3tr: mx(E3.tr, 4), l3va: mx(E3.va, 4), l3te: mx(E3.te, 4), l3sse: mx(sse3, 4), l3pen: mx(pen3, 4), l3obj: mx(sse3 + pen3, 4), l3sumsq: mx(L3.slice(1).reduce((s, v) => s + v * v, 0), 1), l3max: mx(Math.max(...L3.map(Math.abs)), 2), l3w: L3.map((v, j) => `w_${j} = ${mx(v, 2)}`) });
N.l3rows = [0, 2, 4, 6, 8].map(i => '&' + N.l3w.slice(i, i + 2).join(',\\quad ')).join(' \\\\\n');
N.pen0 = bigm(1e-3 * W[9].slice(1).reduce((s, v) => s + v * v, 0));
const lamShow = [[-Infinity, 0], [-7, 1e-7], [-3, 1e-3], [-1, 1e-1]];
T.lam = '| $\\lambda$ | 最大的系数 $\\lvert w_j \\rvert$ | 训练误差 | 验证误差 |\n| --- | --- | --- | --- |\n' + lamShow.map(([k, l]) => { const w = polyfit(TRAIN, 9, l), e = errs(w); return `| ${l === 0 ? '0' : `$10^{${k}}$`} | ${l === 0 ? '$' + bigm(Math.max(...w.map(Math.abs))) + '$' : tx(Math.max(...w.map(Math.abs)), 1)} | ${tx(e.tr, 4)} | ${e.va > 10 ? tx(e.va, 1) : tx(e.va, 4)} |`; }).join('\n');
FIG.fig9 = grid4(lamShow.map(([k, l]) => { const w = polyfit(TRAIN, 9, l), e = errs(w); return { title: l === 0 ? 'λ = 0' : `λ = 10<tspan font-size="0.7em" dy="-6">${k}</tspan>`, fn: pred(w), note: `验证 ${e.va > 10 ? tx(e.va, 1) : tx(e.va, 3)}`, noteCol: 'warn' }; }), '9 阶多项式在四种 L2 系数下的拟合',
  '图 9　都是 9 阶多项式，只改 L2 系数 λ。λ = 0 时就是图 3 里乱摆的那条；λ 稍大一点，曲线马上平静下来；λ 太大，曲线被压得太平，又回到欠拟合。');
{
  const xs = LE.map(q => q.k);
  FIG.fig10 = errChart(xs, LE.map(q => Math.max(q.tr, 1e-2)), LE.map(q => q.va), { xl: 'log₁₀ λ', xt: [-10, -8, -6, -4, -2, 0], xfmt: (t) => String(t).replace('-', '−'), mark: { x: bl.k, y: bl.va, label: `最低 ${tx(bl.va, 3)}`, dy: -36 }, label: '9 阶多项式的训练误差和验证误差随 L2 系数变化', cap: `图 10　横轴是 λ 的常用对数（−3 表示 λ = 0.001）。往右 λ 越大，训练误差（蓝）越高；验证误差（橙）先降后升，在 λ = 10<sup>${bl.k}</sup> 附近最低，${tx(bl.va, 4)}，比 3 阶多项式的 ${N.va3} 还低一点。` });
}

// ———— dropout 手算 ————
const hv = [0.8, -0.3, 0.5, 0.6], wv = [0.5, 0.5, 0.5, 0.5], mask = [1, 0, 0, 1];
{
  const out0 = hv.reduce((s, h, i) => s + h * wv[i], 0);
  const hd = hv.map((h, i) => mask[i] ? h / 0.5 : 0), out1 = hd.reduce((s, h, i) => s + h * wv[i], 0);
  let avg = 0; for (let m = 0; m < 16; m++) { let s = 0; for (let i = 0; i < 4; i++) if (m >> i & 1) s += hv[i] / 0.5 * wv[i]; avg += s / 16; }
  Object.assign(N, { dOut0: mx(out0, 1), dOut1: mx(out1, 1), dAvg: mx(avg, 1) });
  let b = '';
  const net = (x, title, vals, keep, out) => {
    const ox = x + 150, oy = 110;
    let s = text(x + 70, 20, title, 'muted', 15, 'middle');
    vals.forEach((v, i) => {
      const y = 44 + i * 44, on = keep[i];
      s += line(x + 18, y, ox - 22, oy, on ? 'accent' : 'line', on ? 1.6 : 1, on ? null : '3 4');
      s += `<circle cx="${x}" cy="${y}" r="17" style="fill:var(--paper,var(--bg));stroke:var(--${on ? 'accent' : 'muted'});stroke-width:1.6${on ? '' : ';stroke-dasharray:3 3'}"/>`;
      s += text(x, y + 5, on ? tx(v, 1) : '0', on ? 'fg' : 'muted', 14, 'middle');
    });
    s += `<circle cx="${ox}" cy="${oy}" r="22" style="fill:var(--paper,var(--bg));stroke:var(--fg);stroke-width:1.6"/>` + text(ox, oy + 5, tx(out, 1), 'fg', 15, 'middle', ' font-weight="600"');
    return s;
  };
  b += net(40, '不加 dropout', hv, [1, 1, 1, 1], out0);
  b += net(290, '关掉第 2、3 个，其余 ×2', hv.map(v => v / 0.5), mask, out1);
  b += text(240, 232, '每条连线的权重都是 0.5，右边的圆是输出', 'muted', 14, 'middle');
  FIG.fig11 = fig('', svg(480, 244, 'dropout：随机关掉一半隐藏单元，剩下的乘 2', b), '图 11　左边是不加 dropout 时的 4 个隐藏单元；右边是某一次训练时抽到的样子：第 2、3 个被关掉（变成 0），剩下两个乘以 1 ÷ (1 − 0.5) = 2。');
}

// ———— 小 MLP：dropout 与早停 ————
const runs = {}; for (const p of [0, 0.2, 0.5]) runs[p] = C.mlpTrain({ drop: p, seed: 11 });
const r0 = runs[0];
const nParams = (H) => H + H + H * H + H + H + 1;
Object.assign(N, { mlpParams: String(nParams(32)), stopStep: String(r0.best.step), stopVa: mx(r0.best.val, 4), stopTr: mx(r0.best.train, 4), stopTe: mx(mse(C.mlpPredict(r0.best.P), TEST), 4) });
for (const [k, p] of [['0', 0], ['2', 0.2], ['5', 0.5]]) { const r = runs[p]; N['mTr' + k] = mx(r.final.train, 4); N['mVa' + k] = mx(r.final.val, 4); N['mTe' + k] = mx(mse(C.mlpPredict(r.P), TEST), 4); }
T.drop = '| dropout 比例 $p$ | 训练误差 | 验证误差 | 测试误差 |\n| --- | --- | --- | --- |\n' + [['0（不用）', '0'], ['0.2', '2'], ['0.5', '5']].map(([nm, k]) => `| ${nm} | ${N['mTr' + k]} | ${N['mVa' + k]} | ${N['mTe' + k]} |`).join('\n');
{
  let b = ''; const pw = 214, ph = 190;
  [[0, '不用 dropout'], [0.2, 'dropout 0.2']].forEach(([p, nm], i) => {
    const x0 = 22 + i * 236, y0 = 30; const F = frame(x0, y0, pw, ph, [0, 1], yR);
    b += line(F.x0, F.y0 + F.h, F.x0 + F.w, F.y0 + F.h) + line(F.x0, F.y0, F.x0, F.y0 + F.h) + line(F.x0, F.Y(0), F.x0 + F.w, F.Y(0), 'line', 1, '3 4');
    b += curve(F, f, 'muted', 1.6, '5 4') + curve(F, C.mlpPredict(runs[p].P), 'fg', 2.2) + points(F, VAL, 'warn', 4) + points(F, TRAIN, 'accent', 4.2);
    b += text(x0, y0 - 9, nm, 'fg', 15) + text(x0 + pw, y0 - 9, `验证 ${tx(runs[p].final.val, 3)}`, 'warn', 14, 'end');
  });
  FIG.fig12 = fig('', svg(480, 244, '小 MLP 训练 2000 步：不用 dropout 与 dropout 0.2', b), `图 12　同一个小网络（${N.mlpParams} 个参数，种子相同），训练 2000 步。左边不用 dropout：曲线为了穿过每个蓝点，在点和点之间拐出多余的弯；右边 dropout 0.2：曲线更平顺，没有硬穿过每个点。`);
}
{
  const L = r0.log; const xs = L.map(q => q.step);
  const F = frame(56, 28, 400, 190, [0, 2000], [-3, 0.5], true);
  let b = axes(F, { xt: [0, 500, 1000, 1500, 2000], yt: [-3, -2, -1, 0], yfmt: pow10 }) + text(F.x0 + F.w, F.y0 + F.h + 40, '训练步数', 'muted', 15, 'end') + text(F.x0 + 4, F.y0 - 10, '均方误差（对数刻度）', 'muted', 14);
  b += polyline(F, xs, L.map(q => Math.max(q.train, 1e-3)), 'accent', 2.2) + polyline(F, xs, L.map(q => q.val), 'warn', 2.2, '6 4');
  b += line(F.X(r0.best.step), F.y0, F.X(r0.best.step), F.y0 + F.h, 'warn', 1.2, '2 3') + dot(F.X(r0.best.step), F.Y(r0.best.val), 'warn', 6, true);
  b += text(F.X(r0.best.step) + 8, F.Y(r0.best.val) + 26, `第 ${r0.best.step} 步：验证 ${tx(r0.best.val, 3)}`, 'warn', 14);
  b += text(F.x0 + F.w, F.Y(r0.final.val) - 10, `最后 ${tx(r0.final.val, 3)}`, 'warn', 14, 'end');
  b += text(F.x0 + 8, F.y0 + F.h - 26, '— 训练误差', 'accent', 14) + text(F.x0 + 8, F.y0 + F.h - 8, '- - 验证误差', 'warn', 14);
  FIG.fig13 = fig('', svg(480, 270, '不用 dropout 的小 MLP：训练误差与验证误差随步数变化', b), `图 13　不用 dropout 的那次训练，每 10 步记一次。训练误差（蓝）一路降到几乎为 0；验证误差（橙）在第 ${r0.best.step} 步最低，之后一路上升。早停就是停在那条竖线上。`);
}

// ———— 数据量 ————
const NS = [10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120, 160];
const DN = NS.map(n => { const pts = TRAIN.concat(C.EXTRA(n - 10)); const w = polyfit(pts, 9); return { n, pts, w, tr: mse(pred(w), pts), va: mse(pred(w), VAL) }; });
const dn = (n) => DN.find(q => q.n === n);
for (const n of [10, 20, 40, 160]) { N['nTr' + n] = n === 10 ? '0' : mx(dn(n).tr, 4); N['nVa' + n] = dn(n).va > 10 ? mx(dn(n).va, 1) : mx(dn(n).va, 4); N['nGap' + n] = mx(dn(n).va - dn(n).tr, 4); }
T.ndata = '| 训练点数 $n$ | 训练误差 | 验证误差 | 差距 |\n| --- | --- | --- | --- |\n' + [10, 20, 40, 80, 160].map(n => { const q = dn(n); return `| ${n} | ${n === 10 ? '0.0000' : tx(q.tr, 4)} | ${q.va > 10 ? tx(q.va, 1) : tx(q.va, 4)} | ${q.va > 10 ? tx(q.va - q.tr, 1) : tx(q.va - q.tr, 4)} |`; }).join('\n');
{
  let b = ''; const pw = 140, ph = 150;
  [20, 40, 160].forEach((n, i) => {
    const x0 = 14 + i * 158, y0 = 30; const F = frame(x0, y0, pw, ph, [0, 1], yR); const q = dn(n);
    b += line(F.x0, F.y0 + F.h, F.x0 + F.w, F.y0 + F.h) + line(F.x0, F.y0, F.x0, F.y0 + F.h) + line(F.x0, F.Y(0), F.x0 + F.w, F.Y(0), 'line', 1, '3 4');
    b += curve(F, f, 'muted', 1.6, '5 4') + points(F, q.pts, 'accent', n > 60 ? 2.4 : 3.2) + curve(F, pred(q.w), 'fg', 2.2);
    b += text(x0, y0 - 9, `n = ${n}`, 'fg', 15) + text(x0 + pw, y0 + ph + 20, `验证 ${tx(q.va, 3)}`, 'warn', 14, 'end');
  });
  FIG.fig14 = fig('', svg(480, 214, '9 阶多项式在 20、40、160 个训练点上的拟合', b), '图 14　模型一直是 9 阶多项式（10 个系数），只增加训练点。点越多，曲线越没法为了某一个点乱拐，只能贴着它们共同的走向。<i>n</i> = 10 的情形就是图 3 的最后一格。');
}
FIG.fig15 = errChart(NS, DN.map(q => Math.max(q.tr, 1e-2)), DN.map(q => q.va), { xl: '训练点数 n', xt: [10, 40, 80, 120, 160], mark: null, label: '9 阶多项式的训练误差和验证误差随训练点数变化', legendPos: 'right', cap: '图 15　训练点越多，训练误差（蓝）反而从 0 升上来，验证误差（橙）一路降下来，两条线向噪声 0.0625 靠拢，中间的差距越来越小。' });

// ———— 双下降 ————
const DD = []; for (let D = 0; D <= 60; D++) { const w = C.minNormFit(TRAIN, D), pr = (x) => C.legval(w, x); DD.push({ D, w, tr: mse(pr, TRAIN), va: mse(pr, VAL), te: mse(pr, TEST), nm: C.norm(w) }); }
let ddPeak = DD[0]; for (const q of DD) if (q.va > ddPeak.va) ddPeak = q;
let dd2 = DD[11]; for (const q of DD.slice(11)) if (q.va < dd2.va) dd2 = q;
let nmPeak = DD[0]; for (const q of DD) if (q.nm > nmPeak.nm) nmPeak = q;
Object.assign(N, { ddPeakD: String(ddPeak.D), ddPeakVa: mx(ddPeak.va, 1), dd2D: String(dd2.D), dd2Va: mx(dd2.va, 4), dd30Va: mx(DD[30].va, 4), dd60Va: mx(DD[60].va, 4), nm3: mx(DD[3].nm, 2), nm9: mx(DD[9].nm, 2), nm30: mx(DD[30].nm, 2), nm60: mx(DD[60].nm, 2), nmPeakD: String(nmPeak.D), dd12Va: mx(DD[12].va, 2), dd16Va: mx(DD[16].va, 4) });
T.dd = '| 阶数 $D$ | 系数个数 | 训练误差 | 验证误差 | 系数大小 $\\lVert w \\rVert$ |\n| --- | --- | --- | --- | --- |\n' + [3, 9, 10, 12, 16, 30, 60].map(D => { const q = DD[D]; return `| ${D} | ${D + 1} | ${q.tr < 1e-6 ? '0' : tx(q.tr, 4)} | ${q.va > 10 ? tx(q.va, 1) : tx(q.va, 4)} | ${tx(q.nm, 2)} |`; }).join('\n');
{
  const xs = DD.map(q => q.D);
  FIG.fig16 = errChart(xs, DD.map(q => Math.max(q.tr, 1e-2)), DD.map(q => q.va), { xl: '阶数 D（系数个数 D + 1）', xt: [0, 9, 20, 30, 40, 50, 60], mark: { x: dd2.D, y: dd2.va, label: `第二个谷底 ${tx(dd2.va, 3)}`, dy: -14, anchor: 'start', dx: 4 }, label: '阶数继续加到 60：验证误差的双下降', legendPos: 'right', cap: `图 16　把阶数从 9 继续加到 60（9 以上取系数最小的那条曲线）。训练误差（蓝）在 9 阶就到 0，之后一直是 0（画在最底下）。验证误差（橙）在 0 到 3 阶下降，到 9、10 阶冲上顶峰，然后第二次下降，在 ${dd2.D} 阶附近到 ${tx(dd2.va, 3)}。` });
}
{
  let b = ''; const pw = 214, ph = 190;
  [[9, '9 阶（刚好穿过）'], [30, '30 阶（取系数最小）']].forEach(([D, nm], i) => {
    const x0 = 22 + i * 236, y0 = 30; const F = frame(x0, y0, pw, ph, [0, 1], yR); const q = DD[D];
    b += line(F.x0, F.y0 + F.h, F.x0 + F.w, F.y0 + F.h) + line(F.x0, F.y0, F.x0, F.y0 + F.h) + line(F.x0, F.Y(0), F.x0 + F.w, F.Y(0), 'line', 1, '3 4');
    b += curve(F, f, 'muted', 1.6, '5 4') + curve(F, (x) => C.legval(q.w, x), 'fg', 2.2) + points(F, VAL, 'warn', 4) + points(F, TRAIN, 'accent', 4.2);
    b += text(x0, y0 - 9, nm, 'fg', 15) + text(x0 + pw, y0 + ph + 20, `‖w‖ = ${tx(q.nm, 1)}　验证 ${q.va > 10 ? tx(q.va, 1) : tx(q.va, 3)}`, 'muted', 14, 'end');
  });
  FIG.fig17 = fig('', svg(480, 254, '9 阶与 30 阶最小系数曲线对比', b), '图 17　两条曲线都穿过全部 10 个蓝点，训练误差都是 0。9 阶只有这一条能穿过，只好大起大落、冲出画面；30 阶有无数条能穿过，我们挑系数最小的那条：它在点和点之间还有些小弯，但幅度小得多。');
}

// ———— 写文章 ————
let src = fs.readFileSync(path.join(HERE, 'article.src.md'), 'utf8');
src = src.replace(/\{\{(fig\d+)\}\}/g, (m, k) => { if (!FIG[k]) throw new Error('缺图 ' + k); return FIG[k]; });
src = src.replace(/\{\{tab:([a-zA-Z0-9_]+)\}\}/g, (m, k) => { if (!T[k]) throw new Error('缺表 ' + k); return T[k]; });
src = src.replace(/\{\{n:([a-zA-Z0-9_]+)\}\}/g, (m, k) => { if (N[k] == null) throw new Error('缺数字 ' + k); return N[k]; });
const left = src.match(/\{\{[^}]*\}\}/g); if (left) throw new Error('未填: ' + left.join(' '));
fs.writeFileSync(path.join(ROOT, 'src/content/blog/overfitting.md'), src);

// ———— 写实验页 ————
let lab = fs.readFileSync(path.join(HERE, 'lab.src.html'), 'utf8');
lab = lab.replace('__CORE__', () => coreSrc.trim()).replace('__PLOT__', () => plotSrc.trim());
lab = lab.replace('<!doctype html>\n', '<!doctype html>\n<!-- 本页由 labs-src/overfitting/build.mjs 从 lab.src.html 生成（core.js、plot.js 原样内联）。改实验请改 lab.src.html 再运行脚本。 -->\n');
fs.mkdirSync(path.join(ROOT, 'public/labs/overfitting'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'public/labs/overfitting/index.html'), lab);
const chk = lab.match(/<script id="core">\n([\s\S]*?)<\/script>/);
if (!chk || chk[1].trim() !== coreSrc.trim()) throw new Error('实验页 core 与 core.js 不一致');

fs.writeFileSync(path.join(HERE, 'numbers.json'), JSON.stringify(N, null, 1));
console.log('ok', Object.keys(FIG).length, 'figs');
console.log(JSON.stringify(N, null, 0).slice(0, 4000));
