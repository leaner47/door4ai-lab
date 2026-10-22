/* 推理模型实验室。TOY 里的数与 labs-src/reasoning-models/toy.py 相同（文章用的同一组数）。 */
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const pc = (v, d = 1) => (v * 100).toFixed(d) + '%';
/* SVG 小工具：颜色直接用 CSS 变量，深浅色切换不用重画 */
const T = (x, y, s, o = {}) => `<text x="${(+x).toFixed(1)}" y="${(+y).toFixed(1)}" font-size="${o.size || 15}" text-anchor="${o.anchor || 'start'}"${o.italic ? ' font-style="italic"' : ''}${o.weight ? ` font-weight="${o.weight}"` : ''} style="fill:var(--${o.c || 'fg'})">${esc(s)}</text>`;
const R = (x, y, w, h, c, rx = 4) => `<rect x="${(+x).toFixed(1)}" y="${(+y).toFixed(1)}" width="${Math.max(w, 1).toFixed(1)}" height="${Math.max(h, 0).toFixed(1)}" rx="${rx}" style="fill:var(--${c})"/>`;
const B = (x, y, w, h, c, sw = 1.5, rx = 6, dash) => `<rect x="${(+x).toFixed(1)}" y="${(+y).toFixed(1)}" width="${w.toFixed(1)}" height="${h}" rx="${rx}" style="fill:none;stroke:var(--${c});stroke-width:${sw}${dash ? ';stroke-dasharray:' + dash : ''}"/>`;
const L = (x1, y1, x2, y2, c, w = 1.5, dash) => `<line x1="${(+x1).toFixed(1)}" y1="${(+y1).toFixed(1)}" x2="${(+x2).toFixed(1)}" y2="${(+y2).toFixed(1)}" style="stroke:var(--${c});stroke-width:${w}${dash ? ';stroke-dasharray:' + dash : ''}"/>`;
const PL = (pts, c, w = 2.5, dash) => `<polyline points="${pts.map(([x, y]) => x.toFixed(1) + ',' + y.toFixed(1)).join(' ')}" style="fill:none;stroke:var(--${c});stroke-width:${w}${dash ? ';stroke-dasharray:' + dash : ''}"/>`;
const CI = (x, y, r, c) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r}" style="fill:var(--${c})"/>`;
const vw = (id) => { const lab = document.getElementById(id).closest('.lab'); return Math.max(320, Math.min(800, lab ? lab.clientWidth - 36 : 800)); };
const tw = (s) => 12 + 9 * [...s].reduce((a, c) => a + (c.charCodeAt(0) > 255 ? 2 : 1), 0);
const seg = (id, f) => $(id).addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; [...$(id).children].forEach((x) => x.setAttribute('aria-pressed', x === b)); f(b); });
/* 可复现的随机数 */
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const gauss = (r) => { let u = 0; while (u === 0) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); };
/* 二项分布 */
function binom(k, p) { const out = []; let c = 1; for (let i = 0; i <= k; i++) { out.push(c * Math.pow(p, i) * Math.pow(1 - p, k - i)); c = c * (k - i) / (i + 1); } return out; }
function voteSame(p, k) { return binom(k, p).reduce((s, v, i) => s + v * (2 * i > k ? 1 : 2 * i === k ? 0.5 : 0), 0); }
function voteDiff(p, k) { if (k === 1) return p; return 1 - Math.pow(1 - p, k) - (k - 1) * p * Math.pow(1 - p, k - 1); }

/* ———— 01 直接答与分步答 ———— */
const STEPS = [
  { q: '一箱有 12 个苹果。买了 3 箱', toks: (a) => ['3', '箱', '是', '12', '×', '3', '=', String(a), '。'], f: () => 12 * 3, first: true },
  { q: '吃掉 7 个', toks: (a, b) => ['吃掉', '7', '个', '，', String(b), '−', '7', '=', String(a), '。'], f: (x) => x - 7 },
  { q: '又买了 5 个', toks: (a, b) => ['又买了', '5', '个', '，', String(b), '+', '5', '=', String(a), '。'], f: (x) => x + 5 },
  { q: '分成 2 份，取其中 1 份', toks: (a, b) => ['分成', '2', '份', '，', String(b), '÷', '2', '=', String(a), '。'], f: (x) => x / 2 },
  { q: '送人 4 个', toks: (a, b) => ['送人', '4', '个', '，', String(b), '−', '4', '=', String(a), '。'], f: (x) => x - 4 },
];
const s1 = { mode: 'cot', steps: 2, shown: 999 };
function plan1() {
  const n = s1.steps; let v = 0; const vals = [];
  for (let i = 0; i < n; i++) { v = STEPS[i].f(v); vals.push(v); }
  const ans = vals[n - 1];
  if (s1.mode === 'direct') return { toks: [[String(vals[0]), n === 1 ? 2 : 3]], ans, got: vals[0] };
  const toks = []; let prev = 0;
  for (let i = 0; i < n; i++) { STEPS[i].toks(vals[i], prev).forEach((t, j, arr) => toks.push([t, j === arr.length - 2 ? (i === n - 1 ? 2 : 1) : 0])); prev = vals[i]; }
  ['答案', '是'].forEach((t) => toks.push([t, 0])); toks.push([String(ans), 2]);
  return { toks, ans, got: ans };
}
function draw1() {
  $('#st1v').textContent = s1.steps;
  const q = STEPS.slice(0, s1.steps).map((s) => s.q).join('，') + '，还剩几个？';
  $('#q1').textContent = '题目：' + q;
  const P = plan1(), W = vw('fig1'), shown = Math.min(s1.shown, P.toks.length);
  let s = '', x = 10, y = 14;
  const col = { 0: 'muted', 1: 'accent', 2: 'ok', 3: 'warn' };
  P.toks.slice(0, shown).forEach(([t, k]) => {
    const w = tw(t); if (x + w > W - 10) { x = 10; y += 76; }
    s += B(x, y, w, 32, k ? col[k] : 'line', k ? 2.2 : 1.4) + T(x + w / 2, y + 22, t, { anchor: 'middle', c: col[k] });
    s += R(x + w / 2 - 4, y + 38, 8, 26, k === 0 ? 'line' : col[k], 2);
    x += w + 5;
  });
  if (shown < P.toks.length) { const w = 34; if (x + w > W - 10) { x = 10; y += 76; } s += B(x, y, w, 32, 'line', 1.2, 6, '4 4') + T(x + w / 2, y + 22, '…', { anchor: 'middle', c: 'muted' }); }
  const H = Math.max(110, y + 80);
  $('#fig1').setAttribute('viewBox', `0 0 ${W} ${H}`); $('#fig1').innerHTML = s;
  $('#r1a').textContent = shown; $('#r1b').textContent = shown * 32;
  const done = shown === P.toks.length;
  $('#r1c').textContent = done ? (P.got === P.ans ? `${P.got}（对）` : `${P.got}（错，应为 ${P.ans}）`) : '–';
  $('#r1cbox').className = 'ro' + (done ? (P.got === P.ans ? ' ok' : ' warn') : '');
}
seg('#mode1', (b) => { s1.mode = b.dataset.m; s1.shown = 999; draw1(); });
$('#st1').addEventListener('input', () => { s1.steps = +$('#st1').value; s1.shown = 999; draw1(); });
$('#next1').onclick = () => { if (s1.shown >= plan1().toks.length) s1.shown = 0; s1.shown++; draw1(); };
$('#all1').onclick = () => { s1.shown = 999; draw1(); };
$('#reset1').onclick = () => { s1.shown = 0; draw1(); };

/* ———— 02 多数投票 ———— */
const s2 = { wrong: 'same' };
function draw2() {
  const p = +$('#p2').value, k = +$('#k2').value, W = vw('fig2'), narrow = W < 600;
  $('#p2v').textContent = p.toFixed(2); $('#k2v').textContent = k;
  const dist = binom(k, p), vote = s2.wrong === 'same' ? voteSame : voteDiff;
  // 左：答对条数分布；右：投票正确率随 k
  const PW = narrow ? W : W * 0.48, H1 = 230;
  let s = T(10, 20, `${k} 条里答对几条`, { c: 'muted', size: 14 });
  const X0 = 14, X1 = PW - 10, base = 190, mx = Math.max(...dist), bw = (X1 - X0) / (k + 1);
  dist.forEach((v, i) => {
    const win = s2.wrong === 'same' ? 2 * i > k : i >= 2 || (k === 1 && i === 1);
    const tie = s2.wrong === 'same' ? 2 * i === k : (i === 1 && k > 1);
    const c = win ? 'ok' : tie ? 'accent' : 'warn', h = 150 * v / mx;
    s += R(X0 + i * bw + bw * 0.12, base - h, bw * 0.76, h, c, Math.min(3, bw / 4));
    if (k <= 12) { s += T(X0 + (i + 0.5) * bw, base + 20, i, { anchor: 'middle', size: 14, c: 'muted' }); if (k <= 7) s += T(X0 + (i + 0.5) * bw, base - h - 6, v.toFixed(3), { anchor: 'middle', size: 13, c }); }
  });
  s += L(X0, base, X1, base, 'line');
  if (k > 12) s += T(X0, base + 20, '0', { size: 14, c: 'muted' }) + T(X1, base + 20, k, { size: 14, c: 'muted', anchor: 'end' });
  // 曲线
  const ox = narrow ? 0 : W * 0.52, oy = narrow ? H1 + 10 : 0;
  const cx0 = ox + 48, cx1 = (narrow ? W : W) - 14, cy0 = oy + 190, cy1 = oy + 30;
  s += T(cx0 - 4, oy + 20, '投票答对的概率', { c: 'muted', size: 14 });
  s += L(cx0, cy0, cx1, cy0, 'line') + L(cx0, cy0, cx0, cy1, 'line');
  [0, 0.5, 1].forEach((v) => { const yy = cy0 - (cy0 - cy1) * v; s += T(cx0 - 6, yy + 5, v.toFixed(1), { anchor: 'end', size: 13, c: 'muted' }) + L(cx0, yy, cx1, yy, 'line', 0.6, '2 5'); });
  const kx = (kk) => cx0 + (cx1 - cx0) * (kk - 1) / 60, ky = (v) => cy0 - (cy0 - cy1) * v;
  [1, 11, 21, 31, 41, 51, 61].forEach((kk) => { s += T(kx(kk), cy0 + 18, kk, { anchor: 'middle', size: 13, c: 'muted' }); });
  s += T(cx1, cy0 + 36, '采样条数 k', { anchor: 'end', size: 13, c: 'muted' });
  s += L(cx0, ky(p), cx1, ky(p), 'muted', 1.2, '5 4');
  const pts = []; for (let kk = 1; kk <= 61; kk++) pts.push([kx(kk), ky(vote(p, kk))]);
  s += PL(pts, 'ok') + CI(kx(k), ky(vote(p, k)), 5, 'ok');
  const H = narrow ? oy + 236 : 236;
  $('#fig2').setAttribute('viewBox', `0 0 ${W} ${H}`); $('#fig2').innerHTML = s;
  $('#r2a').textContent = pc(p); $('#r2b').textContent = pc(vote(p, k)); $('#r2c').textContent = pc(1 - Math.pow(1 - p, k));
}
['#p2', '#k2'].forEach((id) => $(id).addEventListener('input', draw2));
seg('#w2', (b) => { s2.wrong = b.dataset.m; draw2(); });

/* ———— 03 best-of-N ———— */
const NS = [1, 2, 4, 8, 16, 32, 64];
const s3 = { N: 8, sample: null, cache: {} };
$('#n3').innerHTML = NS.map((n) => `<button data-n="${n}" aria-pressed="${n === 8}">${n}</button>`).join('');
function bon(p, N, d, q, T, seed) {
  const r = rng(seed); let hit = 0;
  for (let t = 0; t < T; t++) {
    let best = -1e9, bc = false;
    for (let i = 0; i < N; i++) { const c = r() < p; const looks = c || r() < q; const sc = (looks ? d : 0) + gauss(r); if (sc > best) { best = sc; bc = c; } }
    if (bc) hit++;
  }
  return hit / T;
}
function curve3(p, d, q) {
  const key = [p, d, q].join('|');
  if (!s3.cache[key]) s3.cache[key] = NS.map((n, i) => n === 1 ? p : bon(p, n, d, q, 4000, 1000 + i));
  return s3.cache[key];
}
function draw3sample() {
  const p = +$('#p3').value, d = +$('#d3').value, q = +$('#q3').value, N = s3.N, W = vw('fig3a');
  if (!s3.sample || s3.sample.length !== N || s3.sample.key !== [p, d, q].join('|')) {
    const r = rng((Math.random() * 1e9) | 0);
    s3.sample = Array.from({ length: N }, () => { const c = r() < p; const looks = c || r() < q; return { c, looks, sc: (looks ? d : 0) + gauss(r) }; });
    s3.sample.key = [p, d, q].join('|');
  }
  const xs = (v) => 30 + (W - 60) * (v + 3) / (Math.max(4, d) + 6);
  let s = L(30, 70, W - 30, 70, 'line') + T(30, 96, '验证器打分 →', { size: 13, c: 'muted' });
  let bi = 0; s3.sample.forEach((o, i) => { if (o.sc > s3.sample[bi].sc) bi = i; });
  s3.sample.forEach((o, i) => {
    const x = xs(o.sc), y = 70 - 14 - (i % 4) * 11;
    s += CI(x, y, i === bi ? 7 : 5, o.c ? 'ok' : 'warn');
    if (!o.c && o.looks) s += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="8.5" style="fill:none;stroke:var(--warn);stroke-width:1.5"/>`;
  });
  const b = s3.sample[bi];
  s += T(W - 30, 20, `挑中：${b.c ? '对的' : (b.looks ? '骗过验证器的错答案' : '错的')}`, { anchor: 'end', size: 14, c: b.c ? 'ok' : 'warn' });
  s += CI(36, 16, 5, 'ok') + T(46, 21, '对', { size: 13, c: 'muted' }) + CI(76, 16, 5, 'warn') + T(86, 21, '错', { size: 13, c: 'muted' });
  s += `<circle cx="120" cy="16" r="6.5" style="fill:none;stroke:var(--warn);stroke-width:1.5"/>` + CI(120, 16, 4, 'warn') + T(132, 21, '骗过验证器', { size: 13, c: 'muted' });
  $('#fig3a').setAttribute('viewBox', `0 0 ${W} 110`); $('#fig3a').innerHTML = s;
}
function draw3() {
  const p = +$('#p3').value, d = +$('#d3').value, q = +$('#q3').value, W = vw('fig3');
  $('#p3v').textContent = p.toFixed(2); $('#d3v').textContent = d.toFixed(2); $('#q3v').textContent = q.toFixed(2);
  const cov = NS.map((n) => 1 - Math.pow(1 - p, n)), vt = NS.map((n) => voteSame(p, n)), ver = curve3(p, d, q);
  const X0 = 52, X1 = W - 16, Y0 = 230, Y1 = 24;
  const nx = (i) => X0 + (X1 - X0) * i / (NS.length - 1), ny = (v) => Y0 - (Y0 - Y1) * v;
  let s = L(X0, Y0, X1, Y0, 'line') + L(X0, Y0, X0, Y1, 'line');
  [0, 0.25, 0.5, 0.75, 1].forEach((v) => { s += T(X0 - 6, ny(v) + 5, v.toFixed(2), { anchor: 'end', size: 13, c: 'muted' }) + L(X0, ny(v), X1, ny(v), 'line', 0.6, '2 5'); });
  NS.forEach((n, i) => { s += T(nx(i), Y0 + 18, n, { anchor: 'middle', size: 13, c: n === s3.N ? 'fg' : 'muted', weight: n === s3.N ? 600 : null }); });
  s += T(X1, Y0 + 36, '回答个数 N', { anchor: 'end', size: 13, c: 'muted' });
  const lim = q > 0 ? p / (p + (1 - p) * q) : 1;
  if (q > 0) s += L(X0, ny(lim), X1, ny(lim), 'ok', 1, '2 4');
  [[cov, 'muted', '5 4'], [vt, 'warn'], [ver, 'ok']].forEach(([vals, c, dash]) => { s += PL(vals.map((v, i) => [nx(i), ny(v)]), c, 2.5, dash); vals.forEach((v, i) => { s += CI(nx(i), ny(v), NS[i] === s3.N ? 5 : 3, c); }); });
  $('#fig3').setAttribute('viewBox', `0 0 ${W} 270`); $('#fig3').innerHTML = s;
  const i = NS.indexOf(s3.N);
  $('#r3a').textContent = pc(cov[i]); $('#r3b').textContent = pc(ver[i]); $('#r3c').textContent = pc(vt[i]); $('#r3d').textContent = pc(lim);
  draw3sample();
}
$('#leg3').innerHTML = '<span><i style="background:var(--muted)"></i>至少一个对（上限）</span><span><i style="background:var(--ok)"></i>验证器挑分最高的</span><span><i style="background:var(--warn)"></i>多数投票</span>';
['#p3', '#d3', '#q3'].forEach((id) => $(id).addEventListener('input', () => { s3.sample = null; draw3(); }));
seg('#n3', (b) => { s3.N = +b.dataset.n; s3.sample = null; draw3(); });
$('#draw3').onclick = () => { s3.sample = null; draw3sample(); };

/* ———— 04 思考的成本 ———— */
const money = (v) => v >= 100 ? '$' + Math.round(v).toLocaleString('en-US') : v >= 1 ? '$' + v.toFixed(2) : '$' + v.toPrecision(3);
function draw4() {
  const g = (id) => Math.max(0, +$(id).value || 0);
  const t = g('#t4'), a = g('#a4'), i = g('#i4'), ip = g('#ip4'), op = g('#op4'), sp = Math.max(1, g('#sp4')), ft = g('#ft4'), n = g('#n4');
  const cIn = i * ip / 1e6, cT = t * op / 1e6, cA = a * op / 1e6, c = cIn + cT + cA;
  const time = ft + (t + a) / sp, tT = t / sp, tA = a / sp;
  $('#r4a').textContent = money(c); $('#r4b').textContent = money(c * n); $('#r4c').textContent = time.toFixed(2) + ' s'; $('#r4d').textContent = c ? pc(cT / c) : '–';
  const W = vw('fig4'), X0 = 70, X1 = W - 14;
  let s = '';
  const bar = (y, lab, parts, tot) => { s += T(X0 - 8, y + 19, lab, { anchor: 'end', size: 14, c: 'muted' }); let x = X0; parts.forEach(([v, col]) => { const w = tot ? (X1 - X0) * v / tot : 0; if (w > 0.5) s += R(x, y, w, 26, col, 0); x += w; }); };
  bar(14, '费用', [[cIn, 'line'], [cT, 'warn'], [cA, 'accent']], c);
  bar(62, '时间', [[ft, 'line'], [tT, 'warn'], [tA, 'accent']], time);
  s += R(X0, 100, 12, 10, 'line', 2) + T(X0 + 18, 110, '输入 / 等首个 token', { size: 13, c: 'muted' });
  const xx = X0 + 160; s += R(xx, 100, 12, 10, 'warn', 2) + T(xx + 18, 110, '思考', { size: 13, c: 'muted' }) + R(xx + 70, 100, 12, 10, 'accent', 2) + T(xx + 88, 110, '回答', { size: 13, c: 'muted' });
  $('#fig4').setAttribute('viewBox', `0 0 ${W} 120`); $('#fig4').innerHTML = s;
}
document.querySelectorAll('.grid4 input').forEach((el) => el.addEventListener('input', draw4));
seg('#pre4', (b) => { $('#t4').value = b.dataset.t; $('#a4').value = b.dataset.a; draw4(); });

/* ———— 05 固定预算 ———— */
function draw5() {
  const ps = +$('#ps5').value, pb = +$('#pb5').value, M = +$('#m5').value, W = vw('fig5');
  $('#ps5v').textContent = ps.toFixed(2); $('#pb5v').textContent = pb.toFixed(2); $('#m5v').textContent = M;
  const BS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const S = BS.map((b) => voteSame(ps, M * b)), Bg = BS.map((b) => voteSame(pb, b));
  const X0 = 52, X1 = W - 16, Y0 = 210, Y1 = 24;
  const bx = (i) => X0 + (X1 - X0) * i / (BS.length - 1), by = (v) => Y0 - (Y0 - Y1) * v;
  let s = L(X0, Y0, X1, Y0, 'line') + L(X0, Y0, X0, Y1, 'line');
  [0, 0.25, 0.5, 0.75, 1].forEach((v) => { s += T(X0 - 6, by(v) + 5, v.toFixed(2), { anchor: 'end', size: 13, c: 'muted' }) + L(X0, by(v), X1, by(v), 'line', 0.6, '2 5'); });
  BS.forEach((b, i) => { s += T(bx(i), Y0 + 18, b, { anchor: 'middle', size: 13, c: 'muted' }); });
  s += T(X1, Y0 + 36, '预算 b：够大模型答几次', { anchor: 'end', size: 13, c: 'muted' });
  s += PL(S.map((v, i) => [bx(i), by(v)]), 'accent') + PL(Bg.map((v, i) => [bx(i), by(v)]), 'fg', 2.5, '6 4');
  S.forEach((v, i) => { s += CI(bx(i), by(v), 3.5, 'accent'); }); Bg.forEach((v, i) => { s += CI(bx(i), by(v), 3.5, 'fg'); });
  $('#fig5').setAttribute('viewBox', `0 0 ${W} 250`); $('#fig5').innerHTML = s;
  $('#r5a').textContent = pc(S[0]); $('#r5b').textContent = pc(Bg[0]);
  $('#r5c').textContent = Math.max(...S) < 0.1 && Math.max(...Bg) < 0.3 ? '都不行' : S[2] > Bg[2] + 0.005 ? '小模型多想' : Bg[2] > S[2] + 0.005 ? '换大模型' : '差不多';
}
['#ps5', '#pb5', '#m5'].forEach((id) => $(id).addEventListener('input', draw5));
seg('#pre5', (b) => { $('#ps5').value = b.dataset.s; $('#pb5').value = b.dataset.b; draw5(); });

/* ———— 06 强化学习让思考变长 ———— */
const LENS = [200, 400, 800, 1600, 3200];
const LEVEL = { easy: [0.95, 0.96, 0.96, 0.97, 0.97], mid: [0.20, 0.35, 0.50, 0.65, 0.75], hard: [0.02, 0.02, 0.03, 0.03, 0.03] };
const Z0 = [1, 0.5, 0, -0.5, -1];
const s6 = { lv: 'mid', z: Z0.slice(), steps: 0, hist: [], r: rng(43) };
const sm = (z) => { const m = Math.max(...z), e = z.map((v) => Math.exp(v - m)), t = e.reduce((a, b) => a + b, 0); return e.map((v) => v / t); };
const stat6 = () => { const p = sm(s6.z), acc = LEVEL[s6.lv]; return { len: p.reduce((s, v, k) => s + v * LENS[k], 0), acc: p.reduce((s, v, k) => s + v * acc[k], 0) }; };
function step6() {
  const lam = +$('#lam6').value, acc = LEVEL[s6.lv], G = 8, Q = 16, eta = 1, r = s6.r;
  const p = sm(s6.z), g = [0, 0, 0, 0, 0];
  for (let qi = 0; qi < Q; qi++) {
    const ys = [], rs = [];
    for (let i = 0; i < G; i++) { let u = r(), k = 0; while (k < 4 && u > p[k]) { u -= p[k]; k++; } ys.push(k); rs.push((r() < acc[k] ? 1 : 0) - lam * LENS[k] / 3200); }
    const mean = rs.reduce((a, b) => a + b, 0) / G, sd = Math.sqrt(rs.reduce((a, b) => a + (b - mean) ** 2, 0) / G);
    if (sd < 1e-9) continue;
    ys.forEach((k, i) => { const A = (rs[i] - mean) / sd; for (let j = 0; j < 5; j++) g[j] += A * ((j === k ? 1 : 0) - p[j]) / G / Q; });
  }
  s6.z = s6.z.map((v, j) => v + eta * g[j]); s6.steps++; s6.hist.push(stat6());
}
function reset6() { s6.z = Z0.slice(); s6.steps = 0; s6.r = rng(43); s6.hist = [stat6()]; draw6(); }
function draw6() {
  $('#lam6v').textContent = (+$('#lam6').value).toFixed(2);
  const W = vw('fig6'), narrow = W < 600, p = sm(s6.z), acc = LEVEL[s6.lv];
  const PW = narrow ? W : W * 0.44;
  let s = T(10, 18, '每档的答对率（示意）与当前概率', { size: 14, c: 'muted' });
  const bw = (PW - 20) / 5;
  LENS.forEach((len, k) => {
    const x = 10 + k * bw, h = 160 * p[k];
    s += T(x + bw / 2, 42, pc(acc[k], 0), { anchor: 'middle', size: 13, c: 'ok' });
    s += R(x + bw * 0.15, 220 - h, bw * 0.7, h, 'accent', 3);
    s += T(x + bw / 2, 214 - h, pc(p[k], 0), { anchor: 'middle', size: 13, c: 'accent' });
    s += T(x + bw / 2, 240, len, { anchor: 'middle', size: 13, c: 'muted' });
  });
  s += L(10, 220, PW - 10, 220, 'line');
  const ox = narrow ? 0 : W * 0.5, oy = narrow ? 262 : 0;
  const X0 = ox + 52, X1 = W - 14, Y0 = oy + 220, Y1 = oy + 36, n = Math.max(50, s6.hist.length - 1);
  s += T(X0 - 4, oy + 18, '平均思考长度（蓝）与正确率（绿）', { size: 14, c: 'muted' });
  s += L(X0, Y0, X1, Y0, 'line') + L(X0, Y0, X0, Y1, 'line');
  [0, 1600, 3200].forEach((v) => { const yy = Y0 - (Y0 - Y1) * v / 3200; s += T(X0 - 6, yy + 5, v, { anchor: 'end', size: 12, c: 'accent' }) + L(X0, yy, X1, yy, 'line', 0.6, '2 5'); });
  [0, 0.5, 1].forEach((v) => { const yy = Y0 - (Y0 - Y1) * v; s += T(X1 - 2, yy - 4, pc(v, 0), { anchor: 'end', size: 12, c: 'ok' }); });
  const hx = (i) => X0 + (X1 - X0) * i / n;
  s += PL(s6.hist.map((h, i) => [hx(i), Y0 - (Y0 - Y1) * h.len / 3200]), 'accent') + PL(s6.hist.map((h, i) => [hx(i), Y0 - (Y0 - Y1) * h.acc]), 'ok');
  s += T(X1, Y0 + 20, `训练步数（0–${n}）`, { anchor: 'end', size: 13, c: 'muted' });
  const H = narrow ? oy + 252 : 256;
  $('#fig6').setAttribute('viewBox', `0 0 ${W} ${H}`); $('#fig6').innerHTML = s;
  const st = stat6(); $('#r6a').textContent = s6.steps; $('#r6b').textContent = Math.round(st.len); $('#r6c').textContent = pc(st.acc);
}
$('#go6').onclick = () => { for (let i = 0; i < 50; i++) step6(); draw6(); };
$('#reset6').onclick = reset6;
$('#lam6').addEventListener('input', () => $('#lam6v').textContent = (+$('#lam6').value).toFixed(2));
seg('#lv6', (b) => { s6.lv = b.dataset.l; reset6(); });

const all = () => { draw1(); draw2(); draw3(); draw4(); draw5(); draw6(); };
s6.hist = [stat6()];
all();
let lastW = 0; addEventListener('resize', () => { const w = vw('fig2'); if (w !== lastW) { lastW = w; all(); } });
