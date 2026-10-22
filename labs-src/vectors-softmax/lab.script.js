/* 贯穿算例：与 labs-src/vectors-softmax/toy.py（也即注意力讲的 toy.py）同一组数 */
const TOY = {
  tokens: ['粮油', '店', '买了', '小米'],
  x: { '粮油': [0, 1], '店': [0.4, 0.2], '买了': [0.2, 0], '小米': [0.5, 0.5] },
  WQ: [[1, 1], [0, -1.2]],
  s: [1.6, 0.48, 0.08, 1.0]
};
try { renderMathInElement(document.body, { delimiters: [{ left: '\\[', right: '\\]', display: true }, { left: '\\(', right: '\\)', display: false }], throwOnError: false }); } catch (e) {}
const $ = (id) => document.getElementById(id);
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const NS = 'http://www.w3.org/2000/svg';
function E(tag, at, parent, txt) { const el = document.createElementNS(NS, tag); for (const k in at) el.setAttribute(k, at[k]); if (txt !== undefined) el.textContent = txt; if (parent) parent.appendChild(el); return el; }
function mt(p, x, y, parts, o = {}) { const t = E('text', Object.assign({ x, y, 'font-size': 15 }, o), p); parts.forEach(([s, k]) => { const sp = E('tspan', {}, t, s); if (k === 'i') sp.setAttribute('font-style', 'italic'); if (k === 'sub') { sp.setAttribute('font-size', '.72em'); sp.setAttribute('dy', '4'); } }); return t; }
const K = (tex, disp = true) => { try { return katex.renderToString(tex, { displayMode: disp, throwOnError: false }); } catch (e) { return tex; } };
const minus = (s) => String(s).replace(/-/g, '−');
const r = (v, d = 2) => { const t = (+v).toFixed(d); return t === '-0.00' || t === '-0.0' || t === '-0' ? t.slice(1) : t; };
const tr = (v, d = 2) => { let t = r(v, d); if (t.includes('.')) t = t.replace(/0+$/, '').replace(/\.$/, ''); return t; };
const pct = (v) => (v * 100).toFixed(1) + '%';
const fmtInt = (n) => Math.round(n).toLocaleString('en-US');
function arrow(svg, x1, y1, x2, y2, col, w = 2.5, dash) {
  const a = Math.atan2(y2 - y1, x2 - x1), L = 11, h = 0.42;
  if (Math.hypot(x2 - x1, y2 - y1) < 2) return;
  const bx = x2 - L * Math.cos(a), by = y2 - L * Math.sin(a);
  E('line', Object.assign({ x1, y1, x2: bx, y2: by, stroke: col, 'stroke-width': w }, dash ? { 'stroke-dasharray': dash } : {}), svg);
  E('path', { d: `M${x2} ${y2} L${x2 - L * Math.cos(a - h)} ${y2 - L * Math.sin(a - h)} L${x2 - L * Math.cos(a + h)} ${y2 - L * Math.sin(a + h)} z`, fill: col }, svg);
}
function segInit(id, cb) { const s = $(id); s.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { s.querySelectorAll('button').forEach(o => o.setAttribute('aria-pressed', o === b)); cb(b.dataset.v); })); }
const segVal = (id) => $(id).querySelector('[aria-pressed=true]').dataset.v;

/* ---------- 01 两支箭头 ---------- */
let A1 = [0.5, 0.5], B1 = [0, 1];
const P1 = { ly: [[0.5, 0.5], [0, 1]], d: [[0.5, 0.5], [0.4, 0.2]], same: [[0.5, 0.5], [0.8, 0.8]], perp: [[0.5, 0.5], [-0.6, 0.6]], opp: [[0.5, 0.5], [-0.7, -0.7]] };
segInit('seg1', v => { [A1, B1] = P1[v].map(p => p.slice()); draw1(); });
const O1 = { x: 240, y: 180, u: 140 };
function draw1() {
  const svg = $('fig1'); svg.innerHTML = '';
  const fg = css('--fg'), mu = css('--muted'), li = css('--line'), ac = css('--accent'), wa = css('--warn');
  const X = (v) => O1.x + v * O1.u, Y = (v) => O1.y - v * O1.u;
  for (let g = -1; g <= 1; g += 0.5) {
    E('line', { x1: X(g), y1: Y(-1.2), x2: X(g), y2: Y(1.2), stroke: li, 'stroke-width': g === 0 ? 1.5 : 0.6, 'stroke-dasharray': g === 0 ? '' : '2 4' }, svg);
    E('line', { x1: X(-1.6), y1: Y(g), x2: X(1.6), y2: Y(g), stroke: li, 'stroke-width': g === 0 ? 1.5 : 0.6, 'stroke-dasharray': g === 0 ? '' : '2 4' }, svg);
    const near = (px, py) => [A1, B1].some(p => Math.hypot(p[0] - px, p[1] - py) < 0.22);
    if (g !== 0) { if (!near(g, 0)) E('text', { x: X(g), y: Y(0) + 17, fill: mu, 'font-size': 13, 'text-anchor': 'middle' }, svg, minus(g)); if (!near(0, g)) E('text', { x: X(0) - 7, y: Y(g) + 4, fill: mu, 'font-size': 13, 'text-anchor': 'end' }, svg, minus(g)); }
  }
  const dot = A1[0] * B1[0] + A1[1] * B1[1], la = Math.hypot(...A1), lb = Math.hypot(...B1);
  const cos = la && lb ? dot / la / lb : NaN, ang = Math.acos(Math.max(-1, Math.min(1, cos))) * 180 / Math.PI;
  if (lb > 0.01) {
    const ub = [B1[0] / lb, B1[1] / lb], pr = dot / lb, foot = [ub[0] * pr, ub[1] * pr];
    E('line', { x1: X(-ub[0] * 1.6), y1: Y(-ub[1] * 1.6), x2: X(ub[0] * 1.6), y2: Y(ub[1] * 1.6), stroke: mu, 'stroke-width': 0.8, 'stroke-dasharray': '6 5' }, svg);
    E('line', { x1: X(A1[0]), y1: Y(A1[1]), x2: X(foot[0]), y2: Y(foot[1]), stroke: wa, 'stroke-width': 1.5, 'stroke-dasharray': '5 4' }, svg);
    E('line', { x1: X(0), y1: Y(0), x2: X(foot[0]), y2: Y(foot[1]), stroke: wa, 'stroke-width': 6, 'stroke-linecap': 'round', opacity: 0.85 }, svg);
  }
  if (la > 0.01 && lb > 0.01) {
    const a0 = Math.atan2(A1[1], A1[0]), b0 = Math.atan2(B1[1], B1[0]);
    let d = b0 - a0; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI;
    const rr = 30, x0 = X(0) + rr * Math.cos(a0), y0 = Y(0) - rr * Math.sin(a0), x1 = X(0) + rr * Math.cos(a0 + d), y1 = Y(0) - rr * Math.sin(a0 + d);
    E('path', { d: `M${x0} ${y0} A${rr} ${rr} 0 0 ${d > 0 ? 0 : 1} ${x1} ${y1}`, fill: 'none', stroke: fg, 'stroke-width': 1.3 }, svg);
  }
  arrow(svg, X(0), Y(0), X(B1[0]), Y(B1[1]), mu, 3);
  arrow(svg, X(0), Y(0), X(A1[0]), Y(A1[1]), ac, 3);
  [[A1, ac, 'a'], [B1, mu, 'b']].forEach(([p, c, n]) => {
    const h = E('circle', { cx: X(p[0]), cy: Y(p[1]), r: 13, fill: c, 'fill-opacity': 0.15, stroke: c, 'stroke-width': 1.5, style: 'cursor:grab', 'data-h': n }, svg);
    const right = p[0] >= 0;
    mt(svg, X(p[0]) + (right ? 16 : -16), Y(p[1]) + (p[1] >= 0 ? -10 : 22), [[n, 'i'], [` (${minus(tr(p[0]))}, ${minus(tr(p[1]))})`, '']], { fill: c, 'font-size': 15, 'text-anchor': right ? 'start' : 'end', 'font-weight': 600 });
  });
  $('r1dot').textContent = minus(r(dot, 3)); $('r1la').textContent = r(la, 3); $('r1lb').textContent = r(lb, 3);
  $('r1cos').textContent = isNaN(cos) ? '—' : minus(r(cos, 3)); $('r1ang').textContent = isNaN(cos) ? '—' : r(ang, 1) + '°';
  const f = (v) => v < 0 ? `(${tr(v)})` : tr(v);
  $('calc1').innerHTML = K(`a\\cdot b = ${f(A1[0])}\\times${f(B1[0])} + ${f(A1[1])}\\times${f(B1[1])} = ${r(dot, 3)}`);
}
(function drag1() {
  const svg = $('fig1'); let which = null;
  const pt = (e) => { const p = svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY; const q = p.matrixTransform(svg.getScreenCTM().inverse()); return [Math.round((q.x - O1.x) / O1.u * 20) / 20, Math.round((O1.y - q.y) / O1.u * 20) / 20].map(v => Math.max(-1.25, Math.min(1.25, v))); };
  svg.addEventListener('pointerdown', (e) => {
    const p = pt(e); const da = Math.hypot(p[0] - A1[0], p[1] - A1[1]), db = Math.hypot(p[0] - B1[0], p[1] - B1[1]);
    which = da <= db ? 'a' : 'b'; if (Math.min(da, db) > 0.35) { which = null; return; }
    svg.setPointerCapture(e.pointerId); e.preventDefault();
  });
  svg.addEventListener('pointermove', (e) => { if (!which) return; const p = pt(e); if (which === 'a') A1 = p; else B1 = p; $('seg1').querySelectorAll('button').forEach(o => o.setAttribute('aria-pressed', false)); draw1(); });
  const up = () => { which = null; }; svg.addEventListener('pointerup', up); svg.addEventListener('pointercancel', up);
})();

/* ---------- 02 矩阵乘向量 ---------- */
let step2 = 0;
const W2 = () => [[+$('w11').value || 0, +$('w12').value || 0], [+$('w21').value || 0, +$('w22').value || 0]];
const X2 = () => [+$('x1').value || 0, +$('x2').value || 0];
['w11', 'w12', 'w21', 'w22', 'x1', 'x2'].forEach(id => $(id).addEventListener('input', draw2));
$('step2').onclick = () => { step2 = step2 >= 2 ? 1 : step2 + 1; draw2(); };
$('reset2').onclick = () => { step2 = 0; draw2(); };
$('def2').onclick = () => { $('w11').value = 1; $('w12').value = 1; $('w21').value = 0; $('w22').value = -1.2; $('x1').value = 0.5; $('x2').value = 0.5; step2 = 0; draw2(); };
function draw2() {
  const W = W2(), x = X2(), y = [W[0][0] * x[0] + W[0][1] * x[1], W[1][0] * x[0] + W[1][1] * x[1]];
  const fg = css('--fg'), mu = css('--muted'), li = css('--line'), ac = css('--accent'), wa = css('--warn');
  $('step2').textContent = step2 === 0 ? '第 1 行' : step2 === 1 ? '第 2 行' : '再看第 1 行';
  const a = $('fig2a'); a.innerHTML = '';
  const cw = 64, ch = 40, y0 = 20;
  const grid = (x0, vals, hlRow, hlCol, col, show = () => true) => {
    vals.forEach((row, i) => row.forEach((v, j) => {
      const on = (hlRow !== null && i === hlRow) || hlCol === j;
      if (on) E('rect', { x: x0 + j * cw + 3, y: y0 + i * ch + 3, width: cw - 6, height: ch - 6, rx: 5, fill: col, 'fill-opacity': 0.18 }, a);
      E('text', { x: x0 + j * cw + cw / 2, y: y0 + i * ch + ch / 2 + 6, 'font-size': 17, 'text-anchor': 'middle', fill: on ? col : (show(i) ? fg : li), 'font-weight': on ? 600 : 400 }, a, show(i) ? minus(tr(v)) : '?');
    }));
    const H = vals.length * ch, Wd = vals[0].length * cw;
    E('path', { d: `M${x0 + 7} ${y0} h-7 v${H} h7`, fill: 'none', stroke: fg, 'stroke-width': 1.5 }, a);
    E('path', { d: `M${x0 + Wd - 7} ${y0} h7 v${H} h-7`, fill: 'none', stroke: fg, 'stroke-width': 1.5 }, a);
  };
  const row = step2 === 0 ? null : step2 - 1;
  mt(a, 30, y0 + 45, [['W', 'i']], { fill: mu, 'font-size': 17, 'text-anchor': 'middle' });
  grid(56, W, row, null, wa);
  E('text', { x: 206, y: y0 + 46, fill: mu, 'font-size': 20, 'text-anchor': 'middle' }, a, '×');
  grid(226, [[x[0]], [x[1]]], null, step2 === 0 ? null : 0, ac);
  E('text', { x: 312, y: y0 + 46, fill: mu, 'font-size': 20, 'text-anchor': 'middle' }, a, '=');
  grid(334, [[y[0]], [y[1]]], row, null, wa, (i) => step2 === 0 ? false : (step2 === 2 ? true : i <= row));
  mt(a, 420, y0 + 45, [['y', 'i']], { fill: mu, 'font-size': 17, 'text-anchor': 'middle' });
  const f = (v) => v < 0 ? `(${tr(v)})` : tr(v);
  if (row === null) $('calc2').innerHTML = K(`y = Wx`, true);
  else $('calc2').innerHTML = K(`y_{${row + 1}} = ${f(W[row][0])}\\times${f(x[0])} + ${f(W[row][1])}\\times${f(x[1])} = ${r(y[row], 3).replace(/\.?0+$/, '') || '0'}`);
  /* 平面 */
  const b = $('fig2b'); b.innerHTML = '';
  const m = Math.max(1, Math.abs(x[0]), Math.abs(x[1]), Math.abs(y[0]), Math.abs(y[1])) * 1.15;
  const u = 140 / m, ox = 240, oy = 165, X = (v) => ox + v * u, Y = (v) => oy - v * u;
  E('line', { x1: 20, y1: oy, x2: 460, y2: oy, stroke: li, 'stroke-width': 1.5 }, b); E('line', { x1: ox, y1: 15, x2: ox, y2: 315, stroke: li, 'stroke-width': 1.5 }, b);
  const tick = m > 2 ? (m > 5 ? 2 : 1) : 0.5;
  for (let t = -Math.floor(m / tick) * tick; t <= m; t += tick) { if (Math.abs(t) < 1e-9) continue; if (Math.abs(X(t) - ox) < 210) { E('line', { x1: X(t), y1: oy - 3, x2: X(t), y2: oy + 3, stroke: li }, b); E('text', { x: X(t), y: oy + 19, fill: mu, 'font-size': 14, 'text-anchor': 'middle' }, b, minus(tr(t))); } if (Math.abs(Y(t) - oy) < 145) { E('line', { x1: ox - 3, y1: Y(t), x2: ox + 3, y2: Y(t), stroke: li }, b); E('text', { x: ox - 7, y: Y(t) + 5, fill: mu, 'font-size': 14, 'text-anchor': 'end' }, b, minus(tr(t))); } }
  arrow(b, X(0), Y(0), X(x[0]), Y(x[1]), ac, 3);
  mt(b, X(x[0]) + (x[0] >= 0 ? 10 : -10), Y(x[1]) + (x[1] >= 0 ? -8 : 20), [['x', 'i'], [` (${minus(tr(x[0]))}, ${minus(tr(x[1]))})`, '']], { fill: ac, 'font-size': 17, 'text-anchor': x[0] >= 0 ? 'start' : 'end' });
  if (step2 === 2) {
    arrow(b, X(0), Y(0), X(y[0]), Y(y[1]), wa, 3);
    mt(b, X(y[0]) + (y[0] >= 0 ? 10 : -10), Y(y[1]) + (y[1] >= 0 ? -8 : 20), [['y', 'i'], [` (${minus(tr(y[0], 3))}, ${minus(tr(y[1], 3))})`, '']], { fill: wa, 'font-size': 17, 'font-weight': 600, 'text-anchor': y[0] >= 0 ? 'start' : 'end' });
  }
  $('r2y').textContent = step2 === 2 ? `(${minus(tr(y[0], 3))}, ${minus(tr(y[1], 3))})` : '…';
  $('r2lx').textContent = r(Math.hypot(...x), 3); $('r2ly').textContent = step2 === 2 ? r(Math.hypot(...y), 3) : '…';
}

/* ---------- 03 形状检查器 ---------- */
let mode3 = 'vec';
segInit('seg3', v => { mode3 = v; draw3(); });
['am', 'an', 'bp', 'bq'].forEach(id => $(id).addEventListener('input', draw3));
function draw3() {
  const m = Math.max(1, Math.floor(+$('am').value || 1)), n = Math.max(1, Math.floor(+$('an').value || 1)), p = Math.max(1, Math.floor(+$('bp').value || 1)), q = Math.max(1, Math.floor(+$('bq').value || 1));
  $('bxq').style.display = mode3 === 'mat' ? '' : 'none';
  const ok = n === p, mu = css('--muted'), ac = css('--accent'), wa = css('--warn'), okc = css('--ok'), li = css('--line');
  const svg = $('fig3'); svg.innerHTML = '';
  const cap = 6, cs = 20;
  const box = (x0, y0, R, C, col, label, hiCol, hiRow) => {
    const r_ = Math.min(R, cap), c_ = Math.min(C, cap);
    for (let i = 0; i < r_; i++) for (let j = 0; j < c_; j++) {
      const ell = (R > cap && i === cap - 1) || (C > cap && j === cap - 1);
      E('rect', { x: x0 + j * cs + 1, y: y0 + i * cs + 1, width: cs - 2, height: cs - 2, rx: 3, fill: col, 'fill-opacity': ell ? 0.06 : 0.2, stroke: col, 'stroke-width': 1, 'stroke-dasharray': ell ? '2 2' : '' }, svg);
    }
    E('text', { x: x0 + c_ * cs / 2, y: y0 + r_ * cs + 22, fill: col, 'font-size': 15, 'text-anchor': 'middle', 'font-weight': 600 }, svg, label);
    return c_ * cs;
  };
  const fmt = (v) => fmtInt(v);
  let x = 20; const y0 = 30;
  const wA = box(x, y0, m, n, ac, `${fmt(m)} × ${fmt(n)}`); x += wA + 26;
  E('text', { x: x - 13, y: y0 + 60, fill: mu, 'font-size': 20, 'text-anchor': 'middle' }, svg, '×');
  const wB = box(x, y0, p, mode3 === 'mat' ? q : 1, ok ? ac : wa, mode3 === 'mat' ? `${fmt(p)} × ${fmt(q)}` : fmt(p)); x += wB + 26;
  E('text', { x: x - 13, y: y0 + 60, fill: mu, 'font-size': 20, 'text-anchor': 'middle' }, svg, '=');
  if (ok) x += box(x, y0, m, mode3 === 'mat' ? q : 1, okc, mode3 === 'mat' ? `${fmt(m)} × ${fmt(q)}` : fmt(m));
  else { E('text', { x: x + 4, y: y0 + 64, fill: wa, 'font-size': 26, 'font-weight': 700 }, svg, '✕'); x += 30; }
  const vw = Math.max(330, x + 40); svg.setAttribute('viewBox', `0 0 ${vw} 190`);
  const A = `(${m}\\times${n})`, B = mode3 === 'mat' ? `(${p}\\times${q})` : `(${p})`;
  $('verdict3').innerHTML = ok
    ? `<span class="okc">能乘。</span>${K(`${A}\\,${B} \\to ${mode3 === 'mat' ? `(${m}\\times${q})` : `(${m})`}`, false)}：${mode3 === 'mat' ? `结果里每个数是左边一行和右边一列的点积，一共 ${fmt(m)} × ${fmt(q)} = ${fmt(m * q)} 个点积，每个 ${fmt(n)} 次乘法。` : `左边 ${fmt(m)} 行，每行和向量做一次点积（每次 ${fmt(n)} 个乘法），得到 ${fmt(m)} 个数。`}`
    : `<span class="bad">不能乘。</span>${K(`${A}\\,${B}`, false)}：左边的列数是 ${fmt(n)}，右边${mode3 === 'mat' ? '的行数' : '向量的长度'}是 ${fmt(p)}。中间这两个数必须相同。${mode3 === 'mat' && q === n ? `（如果把右边转置成 ${fmt(q)} × ${fmt(p)} 就能乘。）` : ''}`;
}
const L3 = { toy: [2, 2, true], gpt2: [768, 3072, true], l3q: [4096, 4096, false], l3o: [4096, 128256, false] };
segInit('seg3b', v => { const [n, m, b] = L3[v]; $('ln').value = n; $('lm').value = m; $('lb').checked = b; draw3b(); });
['ln', 'lm'].forEach(id => $(id).addEventListener('input', () => { $('seg3b').querySelectorAll('button').forEach(o => o.setAttribute('aria-pressed', false)); draw3b(); }));
$('lb').addEventListener('change', draw3b);
function draw3b() {
  const n = Math.max(1, Math.floor(+$('ln').value || 1)), m = Math.max(1, Math.floor(+$('lm').value || 1)), b = $('lb').checked;
  const P = m * n + (b ? m : 0);
  const big = (v) => fmtInt(v).replace(/,/g, '{,}');
  $('calc3').innerHTML = K(b ? `\\underbrace{${big(m)}\\times${big(n)}}_{W} + \\underbrace{${big(m)}}_{b} = ${big(P)}` : `\\underbrace{${big(m)}\\times${big(n)}}_{W} = ${big(P)}`);
  $('r3p').textContent = fmtInt(P);
  const by = P * 2; $('r3mem').textContent = by >= 2 ** 30 ? (by / 2 ** 30).toFixed(2) + ' GB' : by >= 2 ** 20 ? (by / 2 ** 20).toFixed(1) + ' MB' : by >= 1024 ? (by / 1024).toFixed(1) + ' KB' : by + ' 字节';
  $('r3mul').textContent = fmtInt(m * n);
}

/* ---------- 04 softmax 与温度 ---------- */
let S4 = TOY.s.slice(), samp4 = null;
(function build4() {
  const box = $('sl4');
  TOY.tokens.forEach((t, i) => {
    const d = document.createElement('div'); d.className = 'ctrl';
    d.innerHTML = `<label for="s4_${i}">${t}</label><input type="range" id="s4_${i}" min="-3" max="3" step="0.01" value="${S4[i]}"><b id="s4v_${i}"></b>`;
    box.appendChild(d);
    d.querySelector('input').addEventListener('input', (e) => { S4[i] = +e.target.value; samp4 = null; draw4(); });
  });
})();
$('t4').addEventListener('input', () => { samp4 = null; draw4(); });
$('def4').onclick = () => { S4 = TOY.s.slice(); $('t4').value = 1; samp4 = null; draw4(); };
$('minus4').onclick = () => { S4 = S4.map(v => Math.max(-3, +(v - 1).toFixed(2))); samp4 = null; draw4(); };
$('samp4').onclick = () => { const p = soft4().p; const c = [0, 0, 0, 0]; for (let k = 0; k < 100; k++) { let u = Math.random(), i = 0; while (i < 3 && u >= p[i]) { u -= p[i]; i++; } c[i]++; } samp4 = c; draw4(); };
function soft4() {
  const T = +$('t4').value, z = S4.map(v => v / T), mx = Math.max(...z), e = z.map(v => Math.exp(v - mx)), sum = e.reduce((a, b) => a + b, 0);
  const eRaw = z.map(v => Math.exp(v)), sumRaw = eRaw.reduce((a, b) => a + b, 0);
  const sS = S4.reduce((a, b) => a + b, 0);
  return { T, z, e: eRaw, sum: sumRaw, p: e.map(v => v / sum), naive: S4.map(v => sS === 0 ? NaN : v / sS) };
}
function draw4() {
  const o = soft4(); const T = o.T;
  $('t4v').textContent = T.toFixed(2);
  S4.forEach((v, i) => { $('s4_' + i).value = v; $('s4v_' + i).textContent = minus(v.toFixed(2)); });
  const top = o.p.indexOf(Math.max(...o.p));
  const svg = $('fig4'); svg.innerHTML = '';
  const fg = css('--fg'), mu = css('--muted'), li = css('--line'), ac = css('--accent'), wa = css('--warn');
  const base = 180, H = 150, bw = 46;
  E('line', { x1: 20, y1: base, x2: 460, y2: base, stroke: li, 'stroke-width': 1.5 }, svg);
  TOY.tokens.forEach((t, i) => {
    const cx = 75 + i * 110;
    const h = o.p[i] * H;
    E('rect', { x: cx - bw / 2 - (samp4 ? 12 : 0), y: base - h, width: bw, height: Math.max(h, 1), rx: 4, fill: i === top ? wa : li }, svg);
    E('text', { x: cx - (samp4 ? 12 : 0), y: base - h - 8, fill: i === top ? wa : mu, 'font-size': 15, 'text-anchor': 'middle', 'font-weight': i === top ? 600 : 400 }, svg, pct(o.p[i]));
    if (samp4) {
      const hs = samp4[i] / 100 * H;
      E('rect', { x: cx + 14, y: base - hs, width: 22, height: Math.max(hs, 1), rx: 3, fill: ac, 'fill-opacity': 0.75 }, svg);
      E('text', { x: cx + 25, y: base - hs - 6, fill: ac, 'font-size': 13, 'text-anchor': 'middle' }, svg, samp4[i]);
    }
    E('text', { x: cx, y: base + 22, fill: fg, 'font-size': 15, 'text-anchor': 'middle' }, svg, t);
  });
  if (samp4) E('text', { x: 460, y: 222, fill: ac, 'font-size': 13, 'text-anchor': 'end' }, svg, '蓝色小柱：抽 100 次各被抽中几次');
  const naiveBad = o.naive.some(v => !(v >= 0 && v <= 1));
  const big = (v) => v >= 1e6 ? v.toExponential(2).replace('e+', ' × 10^') : v.toFixed(3);
  let h = `<tr><th>token</th><th class="num">分数 s</th><th class="num">s / T</th><th class="num">e<sup>s/T</sup></th><th class="num">概率（softmax）</th><th class="num">直接除以总和</th></tr>`;
  TOY.tokens.forEach((t, i) => {
    h += `<tr><td>${t}</td><td class="num">${minus(S4[i].toFixed(2))}</td><td class="num">${minus(o.z[i].toFixed(3))}</td><td class="num">${big(o.e[i])}</td><td class="num" style="color:${i === top ? 'var(--warn)' : ''}">${pct(o.p[i])}</td><td class="num" style="color:${o.naive[i] < 0 || o.naive[i] > 1 || isNaN(o.naive[i]) ? 'var(--warn)' : 'var(--muted)'}">${isNaN(o.naive[i]) ? '÷ 0' : minus(pct(o.naive[i]))}</td></tr>`;
  });
  h += `<tr><td>合计</td><td class="num">${minus(S4.reduce((a, b) => a + b, 0).toFixed(2))}</td><td></td><td class="num">${big(o.sum)}</td><td class="num">${pct(o.p.reduce((a, b) => a + b, 0))}</td><td class="num" style="color:${naiveBad ? 'var(--warn)' : 'var(--muted)'}">${naiveBad ? '坏了' : '100.0%'}</td></tr>`;
  $('tab4').innerHTML = h;
  $('r4top').textContent = `${TOY.tokens[top]} ${pct(o.p[top])}`;
  $('r4sum').textContent = pct(o.p.reduce((a, b) => a + b, 0));
  $('r4samp').textContent = samp4 ? `${samp4[top]} 次` : '—';
}

/* ---------- 05 数值稳定性 ---------- */
function f16(x) {
  if (!isFinite(x) || x === 0) return x;
  const a = Math.abs(x); if (a >= 65520) return x > 0 ? Infinity : -Infinity;
  let e = Math.floor(Math.log2(a)); if (e < -14) e = -14;
  const q = Math.pow(2, e - 10); let v = Math.round(a / q) * q; if (v >= 65520) v = Infinity;
  return x < 0 ? -v : v;
}
const RND = { f64: (x) => x, f32: Math.fround, f16 };
const LIM = { f64: Math.log(Number.MAX_VALUE), f32: Math.log(3.4028234663852886e38), f16: Math.log(65504) };
segInit('seg5', draw5);
$('k5').addEventListener('input', draw5);
function softPrec(s, R, stable) {
  const mx = s.reduce((a, b) => Math.max(a, b), -Infinity);
  const z = s.map(v => stable ? R(R(v) - R(mx)) : R(v));
  const e = z.map(v => R(Math.exp(v)));
  let sum = R(0); e.forEach(v => { sum = R(sum + v); });
  return { z, e, sum, p: e.map(v => R(v / sum)) };
}
function draw5() {
  const k = +$('k5').value, pr = segVal('seg5'), R = RND[pr];
  $('k5v').textContent = '× ' + k;
  const s = TOY.s.map(v => R(v * k));
  const a = softPrec(s, R, false), b = softPrec(s, R, true);
  const show = (v, d = 3) => { if (Number.isNaN(v)) return '<span class="bad">NaN</span>'; if (v === Infinity) return '<span class="bad">Infinity</span>'; if (v === 0) return '0'; const av = Math.abs(v); return av >= 1e5 || av < 1e-3 ? minus(v.toExponential(2)) : minus(v.toFixed(d)); };
  const P = (v) => Number.isNaN(v) ? '<span class="bad">NaN</span>' : pct(v);
  let h = `<tr><th>token</th><th class="num">分数</th><th class="num">直接 e<sup>s</sup></th><th class="num">直接：概率</th><th class="num">s − 最大值</th><th class="num">e<sup>s − max</sup></th><th class="num">先减：概率</th></tr>`;
  TOY.tokens.forEach((t, i) => { h += `<tr><td>${t}</td><td class="num">${show(s[i], 2)}</td><td class="num">${show(a.e[i])}</td><td class="num">${P(a.p[i])}</td><td class="num">${show(b.z[i], 2)}</td><td class="num">${show(b.e[i])}</td><td class="num">${P(b.p[i])}</td></tr>`; });
  h += `<tr><td>总和</td><td></td><td class="num">${show(a.sum)}</td><td></td><td></td><td class="num">${show(b.sum)}</td><td></td></tr>`;
  $('tab5').innerHTML = h;
  const bad = a.p.some(v => !Number.isFinite(v));
  $('r5a').textContent = bad ? 'NaN，算坏了' : '正常'; $('ro5a').className = 'ro ' + (bad ? 'warn' : '');
  const bad2 = b.p.some(v => !Number.isFinite(v));
  $('r5b').textContent = bad2 ? 'NaN' : `正常，粮油 ${pct(b.p[0])}`;
  $('r5lim').textContent = `s > ${LIM[pr].toFixed(2)}`;
}

/* ---------- 06 对数 ---------- */
$('p6').addEventListener('input', draw6); $('n6').addEventListener('input', draw6);
function draw6() {
  const p = +$('p6').value, N = +$('n6').value; $('p6v').textContent = p.toFixed(3); $('n6v').textContent = N;
  const pf = Math.fround(p);
  let prod = 1, zeroAt = null; const ln32 = [], lnSum = [];
  for (let k = 1; k <= N; k++) { prod = Math.fround(prod * pf); if (prod === 0 && zeroAt === null) zeroAt = k; ln32.push(prod > 0 ? Math.log(prod) : -Infinity); lnSum.push(k * Math.log(p)); }
  if (zeroAt === null) { let q = prod, k = N; while (q > 0 && k < 100000) { q = Math.fround(q * pf); k++; } zeroAt = q === 0 ? -k : null; }
  const svg = $('fig6'); svg.innerHTML = '';
  const fg = css('--fg'), mu = css('--muted'), li = css('--line'), wa = css('--warn');
  const X0 = 58, W = 400, Y0 = 26, H = 210, ymin = Math.min(-1, N * Math.log(p)) * 1.05;
  const X = (k) => X0 + (k / N) * W, Y = (v) => Y0 + (v / ymin) * H;
  E('line', { x1: X0, y1: Y0, x2: X0 + W, y2: Y0, stroke: li, 'stroke-width': 1.5 }, svg); E('line', { x1: X0, y1: Y0, x2: X0, y2: Y0 + H + 6, stroke: li, 'stroke-width': 1.5 }, svg);
  E('text', { x: X0 + W, y: Y0 - 8, fill: mu, 'font-size': 16, 'text-anchor': 'end' }, svg, `token 数（到 ${N}）`);
  const stepY = [1, 2, 5, 10, 20, 50, 100, 200, 500].find(s => -ymin / s <= 5) || 1000;
  for (let v = -stepY; v >= ymin; v -= stepY) { E('line', { x1: X0 - 4, y1: Y(v), x2: X0 + W, y2: Y(v), stroke: li, 'stroke-width': 0.5, 'stroke-dasharray': '2 4' }, svg); E('text', { x: X0 - 8, y: Y(v) + 4, fill: mu, 'font-size': 15, 'text-anchor': 'end' }, svg, minus(v)); }
  E('text', { x: X0 + 8, y: Y0 + 18, fill: mu, 'font-size': 16 }, svg, '0');
  let pts = []; for (let k = 1; k <= N; k++) { if (!isFinite(ln32[k - 1])) break; pts.push(`${X(k).toFixed(1)},${Y(ln32[k - 1]).toFixed(1)}`); }
  if (pts.length > 1) E('polyline', { points: pts.join(' '), fill: 'none', stroke: mu, 'stroke-width': 5, 'stroke-opacity': 0.55 }, svg);
  E('polyline', { points: lnSum.map((v, k) => `${X(k + 1).toFixed(1)},${Y(v).toFixed(1)}`).join(' '), fill: 'none', stroke: wa, 'stroke-width': 2 }, svg);
  if (zeroAt > 0) { const k = zeroAt - 1, xx = X(Math.max(k, 1)), yy = Y(ln32[Math.max(k, 1) - 1]); E('circle', { cx: xx, cy: yy, r: 5, fill: mu }, svg); E('text', { x: xx - 10, y: yy + 26, fill: fg, 'font-size': 16, 'text-anchor': 'end' }, svg, `第 ${zeroAt} 次乘成 0，灰线断了`); }
  E('text', { x: X0 + W - 24, y: Y(lnSum[N - 1]) + 20, fill: wa, 'font-size': 16, 'text-anchor': 'end' }, svg, `对数相加：${minus((N * Math.log(p)).toFixed(1))}`);
  E('text', { x: X0 + 4, y: Y0 - 8, fill: mu, 'font-size': 16 }, svg, '纵轴：ln（概率的连乘）');
  $('r6prod').textContent = prod === 0 ? '0' : minus(prod.toExponential(2));
  $('r6zero').textContent = zeroAt > 0 ? `第 ${zeroAt} 次` : zeroAt < 0 ? `第 ${-zeroAt} 次（N 之后）` : '不会';
  $('r6log').textContent = minus((N * Math.log(p)).toFixed(2));
  $('r6ce').textContent = (-Math.log(p)).toFixed(3);
}

const all = () => { draw1(); draw2(); draw3(); draw3b(); draw4(); draw5(); draw6(); };
all();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', all);
new MutationObserver(all).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
