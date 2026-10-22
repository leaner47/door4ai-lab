/* 蒸馏实验室的界面；计算都在上面的 D（core.js）里 */
const $ = (s) => document.querySelector(s);
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const vw = (id) => { const lab = document.getElementById(id).closest('.lab'); return Math.max(300, Math.min(800, lab ? lab.clientWidth - 36 : 800)); };
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const T_ = (x, y, s, o = {}) => `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-size="${o.size || 15}" text-anchor="${o.anchor || 'start'}"${o.italic ? ' font-style="italic"' : ''}${o.weight ? ` font-weight="${o.weight}"` : ''} fill="${o.fill || css('--fg')}">${esc(s)}</text>`;
const R_ = (x, y, w, h, fill, o = '') => `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(0, w).toFixed(1)}" height="${Math.max(0, h).toFixed(1)}" rx="3" fill="${fill}" ${o}/>`;
const L_ = (x1, y1, x2, y2, stroke, w = 1.5, dash = '') => `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${stroke}" stroke-width="${w}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`;
const pc = (v, d = 1) => (v * 100).toFixed(d) + '%';
const num = (v, d = 3) => (v < 0 ? '−' : '') + Math.abs(v).toFixed(d);
const segInit = (id, cb) => { const el = $(id); el.addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; el.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b)); cb(b); }); };
const segVal = (id, key = 'v') => $(id).querySelector('[aria-pressed=true]').dataset[key];

/* ———— 01 温度 ———— */
const tFrom = (s) => +(Math.pow(20, s / 100)).toFixed(2);   // 0..100 → 1..20（对数刻度）
function draw1() {
  const T = tFrom(+$('#t1').value); $('#t1v').textContent = T.toFixed(T < 10 ? 2 : 1).replace(/\.?0+$/, '');
  const p = D.softmax(D.V, T), W = vw('fig1'), narrow = W < 560, H = 250;
  $('#fig1').setAttribute('viewBox', `0 0 ${W} ${H}`);
  const base = 200, top = 34, slot = (W - 40) / 4, bw = Math.min(46, slot * 0.3);
  let s = L_(20, base, W - 20, base, css('--line'));
  s += R_(20, 8, 12, 12, css('--muted')) + T_(38, 19, '硬标签', { size: 14, fill: css('--muted') });
  s += R_(110, 8, 12, 12, css('--accent')) + T_(128, 19, `老师 T = ${$('#t1v').textContent}`, { size: 14, fill: css('--muted') });
  D.CLASSES.forEach((c, i) => {
    const cx = 20 + slot * (i + 0.5), hy = (i === D.HARD ? 1 : 0) * (base - top), hp = p[i] * (base - top);
    s += R_(cx - bw - 3, base - hy, bw, hy, css('--muted'));
    s += R_(cx + 3, base - hp, bw, hp, css('--accent'));
    s += T_(cx + 3 + bw / 2, base - hp - 6, pc(p[i], p[i] < 0.001 ? 2 : 1), { anchor: 'middle', size: narrow ? 12 : 14, fill: css('--accent') });
    s += T_(cx, base + 22, c, { anchor: 'middle', size: 15 });
    s += T_(cx, base + 40, `v = ${num(D.V[i], 0)}`, { anchor: 'middle', size: 13, fill: css('--muted') });
  });
  $('#fig1').innerHTML = s;
  $('#r1a').textContent = pc(p[0]); $('#r1b').textContent = (p[1] / p[3]).toFixed(p[1] / p[3] < 10 ? 2 : 0); $('#r1c').textContent = D.entropy(p).toFixed(3);
}
$('#t1').addEventListener('input', draw1);

/* ———— 02 KL 与交叉熵 ———— */
const STUD = [D.Z, [6, -2, -2, -2], D.V];
function draw2() {
  const z = STUD[+segVal('#st2', 'k')], T = +$('#t2').value, a = +$('#a2').value, mul = $('#m2').checked;
  $('#t2v').textContent = T; $('#a2v').textContent = a.toFixed(1);
  const r = D.loss(D.V, z, D.HARD, T, a, mul);
  const W = vw('fig2'), narrow = W < 560, colW = narrow ? W : W / 2, blockH = 230, H = narrow ? blockH * 2 : blockH;
  $('#fig2').setAttribute('viewBox', `0 0 ${W} ${H}`);
  let s = '';
  // 左：分布
  { const ox = 0, base = 180, top = 40, slot = (colW - 30) / 4, bw = Math.min(30, slot * 0.32);
    s += T_(ox + 10, 18, `温度 ${T} 下的分布`, { size: 14, fill: css('--muted') });
    s += R_(ox + 10, 26, 10, 10, css('--accent')) + T_(ox + 24, 36, '老师 p', { size: 13, fill: css('--muted') }) + R_(ox + 84, 26, 10, 10, css('--warn')) + T_(ox + 98, 36, '学生 q', { size: 13, fill: css('--muted') });
    s += L_(ox + 10, base, ox + colW - 20, base, css('--line'));
    D.CLASSES.forEach((c, i) => {
      const cx = ox + 15 + slot * (i + 0.5), hp = r.pT[i] * (base - top - 10), hq = r.qT[i] * (base - top - 10);
      s += R_(cx - bw - 2, base - hp, bw, hp, css('--accent')) + R_(cx + 2, base - hq, bw, hq, css('--warn'));
      s += T_(cx, base + 20, c, { anchor: 'middle', size: 14 });
      s += T_(cx - bw / 2 - 2, base - hp - 5, (r.pT[i] * 100).toFixed(0), { anchor: 'middle', size: 12, fill: css('--accent') });
      s += T_(cx + bw / 2 + 2, base - hq - 5, (r.qT[i] * 100).toFixed(0), { anchor: 'middle', size: 12, fill: css('--warn') });
    });
    s += T_(ox + 10, base + 42, '（数字是百分比）', { size: 12, fill: css('--muted') });
  }
  // 右：梯度
  { const ox = narrow ? 0 : colW, oy = narrow ? blockH : 0, mid = oy + 115, slot = (colW - 30) / 4, bw = Math.min(26, slot * 0.3);
    const gh = r.gHard.map(g => a * g), gs = r.gSoft.map(g => (1 - a) * r.s * g);
    const mx = Math.max(0.2, ...gh.map(Math.abs), ...gs.map(Math.abs)), sc = 75 / mx;
    s += T_(ox + 10, oy + 18, '每个 logit 的梯度（负 = 要升）', { size: 14, fill: css('--muted') });
    s += R_(ox + 10, oy + 26, 10, 10, css('--muted')) + T_(ox + 24, oy + 36, '硬项', { size: 13, fill: css('--muted') }) + R_(ox + 70, oy + 26, 10, 10, css('--accent')) + T_(ox + 84, oy + 36, mul ? '软项（含 T²）' : '软项（不乘 T²）', { size: 13, fill: css('--muted') });
    s += L_(ox + 10, mid, ox + colW - 20, mid, css('--line'));
    D.CLASSES.forEach((c, i) => {
      const cx = ox + 15 + slot * (i + 0.5);
      [[gh[i], css('--muted'), cx - bw - 2], [gs[i], css('--accent'), cx + 2]].forEach(([g, col, x]) => {
        const h = Math.abs(g) * sc; s += R_(x, g >= 0 ? mid - h : mid, bw, h, col);
        s += T_(x + bw / 2, g >= 0 ? mid - h - 5 : mid + h + 14, num(g, 2), { anchor: 'middle', size: 11, fill: col });
      });
      s += T_(cx, oy + 222, c, { anchor: 'middle', size: 14 });
    });
  }
  $('#fig2').innerHTML = s;
  $('#r2a').textContent = r.ce.toFixed(3); $('#r2b').textContent = r.kl.toFixed(3); $('#r2c').textContent = r.total.toFixed(3);
  const nh = D.norm(r.gHard.map(g => a * g)), ns = D.norm(r.gSoft.map(g => (1 - a) * r.s * g));
  $('#r2d').textContent = nh < 1e-9 ? '—' : (ns / nh).toFixed(2);
  draw2b(z, T, mul);
}
function draw2b(z, Tcur, mul) {
  const W = vw('fig2b'), H = 220, X0 = 64, X1 = W - 20, Y0 = 180, Y1 = 30;
  $('#fig2b').setAttribute('viewBox', `0 0 ${W} ${H}`);
  const Ts = []; for (let T = 1; T <= 20; T += 0.25) Ts.push(T);
  const raw = Ts.map(T => D.norm(D.softmax(z, T).map((q, k) => (q - D.softmax(D.V, T)[k]) / T)));
  const scl = raw.map((g, i) => g * Ts[i] * Ts[i]);
  const all = raw.concat(scl).filter(v => v > 0); const lo = Math.log10(Math.min(...all) * 0.8), hi = Math.log10(Math.max(...all) * 1.25);
  const xs = (T) => X0 + (X1 - X0) * (Math.log(T) / Math.log(20)), ys = (g) => Y0 - (Y0 - Y1) * ((Math.log10(Math.max(g, 1e-12)) - lo) / (hi - lo || 1));
  let s = L_(X0, Y0, X1, Y0, css('--line')) + L_(X0, Y0, X0, Y1 - 10, css('--line'));
  [1, 2, 4, 8, 20].forEach(T => { s += T_(xs(T), Y0 + 20, T, { anchor: 'middle', size: 13, fill: css('--muted') }); });
  s += T_(X1, Y0 + 38, '温度 T（对数刻度）', { anchor: 'end', size: 13, fill: css('--muted') });
  for (let e = Math.ceil(lo); e <= Math.floor(hi); e++) { s += L_(X0 - 4, ys(10 ** e), X0, ys(10 ** e), css('--line')) + T_(X0 - 8, ys(10 ** e) + 4, e === 0 ? '1' : `1e${e}`.replace('-', '−'), { anchor: 'end', size: 12, fill: css('--muted') }); }
  s += T_(X0 + 6, Y1 - 14, '软项梯度长度（对数刻度）', { size: 13, fill: css('--muted') });
  if (raw.some(v => v > 1e-9)) {
    const path = (arr) => arr.map((g, i) => `${i ? 'L' : 'M'}${xs(Ts[i]).toFixed(1)} ${ys(g).toFixed(1)}`).join(' ');
    s += `<path d="${path(raw)}" fill="none" stroke="${css('--muted')}" stroke-width="2" stroke-dasharray="5 4"/>`;
    s += `<path d="${path(scl)}" fill="none" stroke="${css('--accent')}" stroke-width="2.5"/>`;
    const i = Ts.indexOf(Tcur), g0 = mul ? scl[i] : raw[i];
    s += `<circle cx="${xs(Tcur).toFixed(1)}" cy="${ys(g0).toFixed(1)}" r="5" fill="${css('--warn')}"/>`;
    s += T_(xs(20) - 4, ys(scl[scl.length - 1]) - 8, '乘 T²', { anchor: 'end', size: 13, fill: css('--accent') });
    s += T_(xs(20) - 4, ys(raw[raw.length - 1]) - 8, '不乘', { anchor: 'end', size: 13, fill: css('--muted') });
  } else s += T_((X0 + X1) / 2, (Y0 + Y1) / 2, '学生和老师完全一样：软项梯度处处为 0', { anchor: 'middle', size: 14, fill: css('--muted') });
  $('#fig2b').innerHTML = s;
}
segInit('#st2', draw2); ['#t2', '#a2', '#m2'].forEach(id => $(id).addEventListener('input', draw2));

/* ———— 03 / 04 真实训练 ———— */
let TEACHER = null, TGRID = null;
const cache3 = {}, cache4 = {};
const CLS = () => [css('--accent'), css('--warn'), css('--ok')];
function region(ox, oy, size, grid, pts, title, sub) {
  const g = Math.round(Math.sqrt(grid.length)), c = size / g, cols = CLS();
  /* 每一类拼成一条 path（同一行连续的格子并成一段），避免格子之间露缝 */
  const d = ['', '', ''];
  for (let r = 0; r < g; r++) { let k = 0; while (k < g) { const cl = grid[r * g + k]; let e = k; while (e + 1 < g && grid[r * g + e + 1] === cl) e++; d[cl] += `M${(ox + k * c).toFixed(2)} ${(oy + r * c).toFixed(2)}h${((e - k + 1) * c).toFixed(2)}v${(c + 0.3).toFixed(2)}h${(-(e - k + 1) * c).toFixed(2)}z`; k = e + 1; } }
  let s = `<g>` + d.map((dd, i) => dd ? `<path d="${dd}" fill="${cols[i]}" fill-opacity="0.28"/>` : '').join('');
  if (pts) for (let i = 0; i < pts.n; i++) {
    const x = ox + (pts.X[2 * i] + 1.2) / 2.4 * size, y = oy + (1.2 - pts.X[2 * i + 1]) / 2.4 * size;
    s += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${size < 160 ? 2.4 : 3.2}" fill="${cols[pts.Y[i]]}" stroke="${css('--paper')}" stroke-width="1"/>`;
  }
  s += `</g>` + T_(ox + size / 2, oy + size + 20, title, { anchor: 'middle', size: 14 }) + (sub ? T_(ox + size / 2, oy + size + 38, sub, { anchor: 'middle', size: 13, fill: css('--muted') }) : '');
  return s;
}
function run3() {
  const N = +segVal('#n3'), T = +segVal('#tt3'), key = N + '_' + T;
  if (!cache3[key]) {
    const hard = D.student(TEACHER, N, 16, 'hard'), soft = D.student(TEACHER, N, 16, 'soft', T);
    cache3[key] = { N, T, pts: D.transfer(N), eh: D.err(hard, D.test()), es: D.err(soft, D.test()), gh: D.grid(hard), gs: D.grid(soft) };
  }
  draw3();
}
function draw3() {
  const W = vw('fig3');
  if (!TEACHER) { $('#fig3').setAttribute('viewBox', `0 0 ${W} 60`); $('#fig3').innerHTML = T_(W / 2, 36, '老师训练中…', { anchor: 'middle', size: 15, fill: css('--muted') }); return; }
  const r = cache3[segVal('#n3') + '_' + segVal('#tt3')]; if (!r) return;
  const gap = 12, size = Math.min(240, (W - 2 * gap) / 3), H = size + 46, x0 = (W - 3 * size - 2 * gap) / 2;
  $('#fig3').setAttribute('viewBox', `0 0 ${W} ${H}`);
  $('#fig3').innerHTML = region(x0, 4, size, TGRID, null, size < 180 ? '老师' : '老师（32 单元）', `错 ${pc(TERR)}`) + region(x0 + size + gap, 4, size, r.gh, r.pts, size < 180 ? '硬标签' : '硬标签学生', `错 ${pc(r.eh)}`) + region(x0 + 2 * (size + gap), 4, size, r.gs, r.pts, size < 180 ? `软标签 T = ${r.T}` : `软标签学生 T = ${r.T}`, `错 ${pc(r.es)}`);
  $('#r3a').textContent = pc(TERR); $('#r3b').textContent = pc(r.eh); $('#r3c').textContent = pc(r.es);
}
segInit('#n3', () => { setTimeout(run3, 0); }); segInit('#tt3', () => { setTimeout(run3, 0); });
let TERR = 0, sweepDone = false;
function sweep4(i = 0) {
  if (i >= D.WIDTHS.length) { sweepDone = true; draw4(); return; }
  const h = D.WIDTHS[i], hard = D.student(TEACHER, 60, h, 'hard'), soft = D.student(TEACHER, 60, h, 'soft', 4);
  cache4[h] = { eh: D.err(hard, D.test()), es: D.err(soft, D.test()), gs: D.grid(soft, 30), gh: D.grid(hard, 30) };
  draw4(); setTimeout(() => sweep4(i + 1), 0);
}
function draw4() {
  const h = D.WIDTHS[+$('#w4').value]; $('#w4v').textContent = h; $('#r4a').textContent = (2 * h + h + 3 * h + 3).toLocaleString();
  const W = vw('fig4'), narrow = W < 560;
  const mapS = narrow ? Math.min(150, (W - 12) / 2) : 190, plotW = narrow ? W : W - 2 * mapS - 40, plotH = 230;
  const H = narrow ? plotH + mapS + 50 : 280;
  $('#fig4').setAttribute('viewBox', `0 0 ${W} ${H}`);
  if (!TEACHER) { $('#fig4').innerHTML = T_(W / 2, 40, '老师训练中…', { anchor: 'middle', size: 15, fill: css('--muted') }); return; }
  const X0 = 50, X1 = plotW - 16, Y0 = plotH - 34, Y1 = 22, emax = 0.55;
  const xs = (k) => X0 + (X1 - X0) * k / (D.WIDTHS.length - 1), ys = (e) => Y0 - (Y0 - Y1) * Math.sqrt(e / emax);
  let s = L_(X0, Y0, X1, Y0, css('--line')) + L_(X0, Y0, X0, Y1 - 6, css('--line'));
  D.WIDTHS.forEach((w, k) => { s += T_(xs(k), Y0 + 18, w, { anchor: 'middle', size: 13, fill: css('--muted') }); });
  s += T_(X1, Y0 + 34, '隐藏层宽度', { anchor: 'end', size: 13, fill: css('--muted') });
  [0.01, 0.05, 0.2, 0.5].forEach(e => { s += L_(X0 - 4, ys(e), X0, ys(e), css('--line')) + T_(X0 - 7, ys(e) + 4, pc(e, 0), { anchor: 'end', size: 12, fill: css('--muted') }); });
  s += T_(X0 + 4, Y1 - 8, '验证错误率', { size: 13, fill: css('--muted') });
  s += L_(X0, ys(TERR), X1, ys(TERR), css('--fg'), 1.2, '5 4') + T_(X0 + 6, ys(TERR) + 16, `老师 ${pc(TERR)}`, { size: 12 });
  const done = D.WIDTHS.filter(w => cache4[w]);
  const path = (f) => done.map((w, k) => `${k ? 'L' : 'M'}${xs(D.WIDTHS.indexOf(w)).toFixed(1)} ${ys(cache4[w][f]).toFixed(1)}`).join(' ');
  s += `<path d="${path('eh')}" fill="none" stroke="${css('--warn')}" stroke-width="2.2"/><path d="${path('es')}" fill="none" stroke="${css('--ok')}" stroke-width="2.5"/>`;
  done.forEach(w => { const k = D.WIDTHS.indexOf(w); s += `<circle cx="${xs(k)}" cy="${ys(cache4[w].eh)}" r="3.5" fill="${css('--warn')}"/><circle cx="${xs(k)}" cy="${ys(cache4[w].es)}" r="3.5" fill="${css('--ok')}"/>`; });
  const k = D.WIDTHS.indexOf(h); s += L_(xs(k), Y1, xs(k), Y0, css('--muted'), 1, '2 3');
  s += R_(X0 + 10, Y1 + 4, 14, 4, css('--warn')) + T_(X0 + 30, Y1 + 10, '硬标签', { size: 12, fill: css('--muted') }) + R_(X0 + 82, Y1 + 4, 14, 4, css('--ok')) + T_(X0 + 102, Y1 + 10, '软标签', { size: 12, fill: css('--muted') });
  const c = cache4[h];
  if (c) {
    const mx = narrow ? (W - 2 * mapS - 12) / 2 : plotW + 20, my = narrow ? plotH + 4 : 30;
    s += region(mx, my, mapS, c.gh, null, '硬标签', `错 ${pc(c.eh)}`) + region(mx + mapS + 12, my, mapS, c.gs, null, '软标签', `错 ${pc(c.es)}`);
    $('#r4b').textContent = pc(c.eh); $('#r4c').textContent = pc(c.es);
  } else { $('#r4b').textContent = '训练中…'; $('#r4c').textContent = '训练中…'; }
  $('#fig4').innerHTML = s + (sweepDone ? '' : T_(plotW - 20, Y1 + 10, `训练中 ${done.length}/${D.WIDTHS.length}`, { anchor: 'end', size: 12, fill: css('--muted') }));
}
$('#w4').addEventListener('input', draw4);

/* ———— 05 R1 蒸馏成绩（论文表 4、5、6） ———— */
const R1 = {
  metrics: ['AIME 2024 pass@1', 'MATH-500 pass@1', 'GPQA Diamond pass@1', 'LiveCodeBench pass@1', 'Codeforces 等级分'],
  rows: [
    ['GPT-4o-0513', 'ref', [9.3, 74.6, 49.9, 32.9, 759]],
    ['Claude-3.5-Sonnet-1022', 'ref', [16.0, 78.3, 65.0, 38.9, 717]],
    ['o1-mini', 'ref', [63.6, 90.0, 60.0, 53.8, 1820]],
    ['R1-Distill-Qwen-1.5B', 'stu', [28.9, 83.9, 33.8, 16.9, 954]],
    ['R1-Distill-Qwen-7B', 'stu', [55.5, 92.8, 49.1, 37.6, 1189]],
    ['R1-Distill-Llama-8B', 'stu', [50.4, 89.1, 49.0, 39.6, 1205]],
    ['R1-Distill-Qwen-14B', 'stu', [69.7, 93.9, 59.1, 53.1, 1481]],
    ['R1-Distill-Qwen-32B', 'stu', [72.6, 94.3, 62.1, 57.2, 1691]],
    ['R1-Distill-Llama-70B', 'stu', [70.0, 94.5, 65.2, 57.5, 1633]],
    ['Qwen2.5-32B 纯 RL', 'rl', [47.0, 91.6, 55.0, 40.2, null]],
    ['DeepSeek-R1（老师）', 'teacher', [79.8, 97.3, 71.5, 65.9, 2029]],
  ],
};
function draw5() {
  const m = +segVal('#m5'), W = vw('fig5'), narrow = W < 560, rowH = 32, lw = narrow ? 150 : 200, H = 30 + R1.rows.length * rowH + 6;
  $('#fig5').setAttribute('viewBox', `0 0 ${W} ${H}`);
  const mx = m === 4 ? 2200 : 100, bw = W - lw - 70;
  let s = T_(lw, 18, R1.metrics[m], { size: 14, fill: css('--muted') });
  const col = { ref: css('--line'), stu: css('--accent'), rl: css('--warn'), teacher: css('--ok') };
  R1.rows.forEach(([name, kind, vals], i) => {
    const y = 30 + i * rowH, v = vals[m];
    s += T_(lw - 10, y + 18, narrow ? name.replace('R1-Distill-', '蒸馏 ').replace('Claude-3.5-Sonnet-1022', 'Claude-3.5-Sonnet') : name, { anchor: 'end', size: narrow ? 12 : 14, fill: kind === 'ref' ? css('--muted') : css('--fg') });
    if (v == null) { s += T_(lw + 4, y + 18, '论文未报告', { size: 13, fill: css('--muted') }); return; }
    const w = bw * v / mx; s += R_(lw, y + 4, w, rowH - 12, col[kind]);
    s += T_(lw + w + 6, y + 18, m === 4 ? String(v) : v.toFixed(1), { size: 13, fill: kind === 'ref' ? css('--muted') : col[kind] });
  });
  $('#fig5').innerHTML = s;
}
segInit('#m5', draw5);

const all = () => { draw1(); draw2(); draw3(); draw4(); draw5(); };
all();
addEventListener('resize', () => { all(); });
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', all);
new MutationObserver(all).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
/* 训练老师（约半秒），再训练实验 03 的默认学生和实验 04 的 8 个宽度 */
setTimeout(() => {
  TEACHER = D.makeTeacher(); TERR = D.err(TEACHER, D.test()); TGRID = D.grid(TEACHER);
  run3(); draw4(); setTimeout(() => sweep4(0), 30);
}, 60);
