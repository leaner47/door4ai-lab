/* 画图小工具：文章分镜图（build.mjs）和实验页交互图共用这一份，所以两边是同一套画法。
   只输出 SVG 字符串，颜色只用 CSS 变量。约定：训练点 = accent 蓝，验证点 = warn 橙，测试点 = ok 绿，
   真实规律 = muted 虚线，模型曲线 = fg。 */
const PLOT = (() => {
  const f1 = (v) => (Math.round(v * 10) / 10).toFixed(1);
  const st = (col, w = 2, dash) => `style="stroke:var(--${col});stroke-width:${w};fill:none${dash ? ';stroke-dasharray:' + dash : ''}"`;
  const fl = (col, op) => `style="fill:var(--${col})${op != null ? ';fill-opacity:' + op : ''}"`;
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  function text(x, y, s, col = 'fg', size = 16, anchor = 'start', extra = '') {
    return `<text x="${f1(x)}" y="${f1(y)}" font-size="${size}" text-anchor="${anchor}"${extra} ${fl(col)}>${s}</text>`;
  }
  // 斜体变量：mi('y') → <tspan font-style="italic">y</tspan>
  const mi = (s) => `<tspan font-style="italic">${s}</tspan>`;
  const sub = (s) => `<tspan font-size="0.72em" dy="4">${s}</tspan><tspan dy="-4"> </tspan>`;
  function line(x1, y1, x2, y2, col = 'line', w = 1.5, dash) { return `<line x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}" ${st(col, w, dash)}/>`; }
  function dot(x, y, col, r = 5, hollow = false) {
    return hollow ? `<circle cx="${f1(x)}" cy="${f1(y)}" r="${r}" style="fill:var(--paper,var(--bg));stroke:var(--${col});stroke-width:2"/>` : `<circle cx="${f1(x)}" cy="${f1(y)}" r="${r}" ${fl(col)}/>`;
  }
  // 一个坐标框：x 范围 xr、y 范围 yr（ylog 时为 log10 的范围）
  function frame(x0, y0, w, h, xr, yr, ylog = false) {
    const X = (x) => x0 + (x - xr[0]) / (xr[1] - xr[0]) * w;
    const Y = (y) => { const v = ylog ? Math.log10(Math.max(y, 1e-12)) : y; return y0 + h - (v - yr[0]) / (yr[1] - yr[0]) * h; };
    return { x0, y0, w, h, xr, yr, X, Y, ylog };
  }
  function axes(F, { xt = [], yt = [], xl = '', yl = '', size = 14, xfmt = String, yfmt = String, zero = false } = {}) {
    let s = line(F.x0, F.y0 + F.h, F.x0 + F.w, F.y0 + F.h) + line(F.x0, F.y0 + F.h, F.x0, F.y0);
    if (zero && !F.ylog && F.yr[0] < 0 && F.yr[1] > 0) s += line(F.x0, F.Y(0), F.x0 + F.w, F.Y(0), 'line', 1, '3 4');
    for (const t of xt) s += text(F.X(t), F.y0 + F.h + size + 4, xfmt(t), 'muted', size, 'middle');
    for (const t of yt) s += text(F.x0 - 6, F.Y(F.ylog ? Math.pow(10, t) : t) + size * 0.35, yfmt(t), 'muted', size, 'end');
    if (xl) s += text(F.x0 + F.w, F.y0 + F.h + size * 2 + 8, xl, 'muted', size, 'end');
    if (yl) s += text(F.x0 + 4, F.y0 - 6, yl, 'muted', size, 'start');
    return s;
  }
  // 函数曲线，超出坐标框的部分裁掉（在边界处插值）
  function curve(F, fn, col = 'fg', w = 2.5, dash, n = 240, xr = F.xr) {
    const yl = F.y0, yh = F.y0 + F.h; let d = '', prev = null;
    for (let i = 0; i <= n; i++) {
      const x = xr[0] + (xr[1] - xr[0]) * i / n, p = [F.X(x), F.Y(fn(x))];
      if (!isFinite(p[1])) { prev = null; continue; }
      if (prev) {
        let [ax, ay] = prev, [bx, by] = p; const inA = ay >= yl && ay <= yh, inB = by >= yl && by <= yh;
        if (inA || inB || (ay < yl && by > yh) || (ay > yh && by < yl)) {
          const clip = (px, py, qx, qy) => { const yy = py < yl ? yl : yh; const t = (yy - py) / (qy - py); return [px + t * (qx - px), yy]; };
          if (!inA) [ax, ay] = clip(ax, ay, bx, by);
          if (!inB) [bx, by] = clip(bx, by, ax, ay);
          if (!inA || !d) d += `M${f1(ax)} ${f1(ay)}`;
          d += `L${f1(bx)} ${f1(by)}`;
          if (!inB) d += ' ';
        }
      }
      prev = p;
    }
    return d ? `<path d="${d}" ${st(col, w, dash)}/>` : '';
  }
  // 折线（数据点序列），同样裁剪
  function polyline(F, xs, ys, col, w = 2.5, dash) {
    const pts = xs.map((x, i) => [F.X(x), F.Y(ys[i])]).filter(p => isFinite(p[1]));
    const c = pts.map(([x, y]) => `${f1(x)},${f1(Math.min(Math.max(y, F.y0), F.y0 + F.h))}`).join(' ');
    return `<polyline points="${c}" ${st(col, w, dash)}/>`;
  }
  function points(F, pts, col, r = 5, hollow = false) { return pts.map(p => dot(F.X(p.x), F.Y(p.y), col, r, hollow)).join(''); }
  // 竖直残差线：点到曲线
  function resid(F, pts, fn, col, w = 1.5) {
    return pts.map(p => { const a = F.Y(p.y), b = Math.min(Math.max(F.Y(fn(p.x)), F.y0), F.y0 + F.h); return line(F.X(p.x), a, F.X(p.x), b, col, w, '3 3'); }).join('');
  }
  // 误差图：横轴 xs，纵轴对数刻度；蓝实线训练误差，橙虚线验证误差，绿点线噪声方差
  function errChart(xs, tr, va, { xl = '', mark = null, yr = [-2, 2], xt, xfmt = String, w = 480, h = 270, noise = 0.0625, cur = null, legend = true, legendPos = 'left' } = {}) {
    const F = frame(56, 28, w - 80, h - 80, [xs[0], xs[xs.length - 1]], yr, true);
    const yt = []; for (let k = Math.ceil(yr[0]); k <= yr[1]; k++) yt.push(k);
    const lo = Math.pow(10, yr[0]), hi = Math.pow(10, yr[1]);
    let b = axes(F, { xt: xt || xs, yt, yfmt: pow10, xfmt }) + text(F.x0 + F.w, F.y0 + F.h + 40, xl, 'muted', 15, 'end') + text(F.x0 + 4, F.y0 - 10, '均方误差（对数刻度）', 'muted', 14);
    if (noise) b += line(F.x0, F.Y(noise), F.x0 + F.w, F.Y(noise), 'ok', 1.2, '2 4');
    if (cur != null) b += line(F.X(cur), F.y0, F.X(cur), F.y0 + F.h, 'muted', 1.2, '2 3');
    b += polyline(F, xs, tr.map(v => Math.max(v, lo)), 'accent', 2.5) + polyline(F, xs, va, 'warn', 2.5, '6 4');
    if (xs.length <= 30) xs.forEach((x, i) => { b += dot(F.X(x), F.Y(Math.max(tr[i], lo)), 'accent', 3.5) + (va[i] <= hi ? dot(F.X(x), F.Y(va[i]), 'warn', 3.5) : ''); });
    if (mark) b += dot(F.X(mark.x), F.Y(Math.min(mark.y, hi)), mark.col || 'warn', 7, true) + (mark.label ? text(F.X(mark.x) + (mark.dx ?? 0), F.Y(Math.min(mark.y, hi)) + (mark.dy ?? 26), mark.label, mark.col || 'warn', 14, mark.anchor || 'middle') : '');
    if (legend) {
      const lx = legendPos === 'right' ? F.x0 + F.w - 4 : F.x0 + 8, an = legendPos === 'right' ? 'end' : 'start';
      b += text(lx, F.y0 + 14, '— 训练误差', 'accent', 14, an) + text(lx, F.y0 + 32, '- - 验证误差', 'warn', 14, an);
      if (noise) b += text(lx, F.y0 + 50, '··· 噪声 ' + noise, 'ok', 14, an);
    }
    return b;
  }
  // 拟合图：真实规律 + 模型曲线 + 点
  function fitPanel(fn, { train = [], val = [], test = [], w = 480, h = 280, yr = [-2, 2], under = '', label = '', residVal = false } = {}) {
    const F = frame(48, 20, w - 68, h - 60, [0, 1], yr);
    let b = axes(F, { xt: [0, 0.5, 1], yt: [-2, -1, 0, 1, 2].filter(t => t >= yr[0] && t <= yr[1]), zero: true, yfmt: (t) => String(t).replace('-', '−') });
    b += curve(F, (x) => Math.sin(2 * Math.PI * x), 'muted', 2, '6 5') + under;
    if (fn) b += (residVal ? resid(F, val, fn, 'warn', 1.3) : '') + curve(F, fn, 'fg', 2.5);
    b += points(F, test, 'ok', 5) + points(F, val, 'warn', 4.6) + points(F, train, 'accent', 5);
    if (label) b += text(F.x0 + F.w, F.y0 + 14, label, 'muted', 14, 'end');
    return { F, body: b };
  }
  function svg(w, h, label, body) { return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${body}</svg>`; }
  // 对数轴刻度标签：10 的整数次幂写成 0.01、0.1、1、10、100
  const pow10 = (k) => { const v = Math.pow(10, k); return v >= 1 ? String(v) : v.toFixed(-k); };
  return { f1, st, fl, text, mi, sub, line, dot, frame, axes, curve, polyline, points, resid, svg, pow10, errChart, fitPanel };
})();
if (typeof module !== 'undefined') module.exports = PLOT;
