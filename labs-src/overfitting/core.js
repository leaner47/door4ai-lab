/* 过拟合一讲的全部计算。build.mjs 在 node 里用它算文章里的数字和图；
   实验页把这个文件原样内联进 <script id="core">（build.mjs 会检查两边一致）。 */
const CORE = (() => {
  // ———— 固定种子的随机数 ————
  function rng(seed) {
    let a = seed >>> 0;
    const u = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    let spare = null;
    const n = () => { if (spare !== null) { const s = spare; spare = null; return s; } let p, q, r; do { p = 2 * u() - 1; q = 2 * u() - 1; r = p * p + q * q; } while (r >= 1 || r === 0); const m = Math.sqrt(-2 * Math.log(r) / r); spare = q * m; return p * m; };
    return { u, n };
  }
  const f = (x) => Math.sin(2 * Math.PI * x);   // 真实规律（模型不知道）
  const SIGMA = 0.25;                             // 噪声的标准差
  const r2 = (v) => Math.round(v * 100) / 100;
  // 一组点：x 在 [0, 1] 里均匀随机，y = f(x) + 噪声；都保留两位小数
  function sample(n, seed, sigma = SIGMA) {
    const R = rng(seed), pts = [];
    for (let i = 0; i < n; i++) { const x = r2(R.u()); pts.push({ x, y: r2(f(x) + sigma * R.n()) }); }
    return pts.sort((a, b) => a.x - b.x);
  }
  // 整讲的三组点
  const TRAIN = sample(10, 84);
  const VAL = sample(10, 395);
  const TEST = sample(10, 724);
  const EXTRA = (n) => sample(n, 404);            // 实验「数据量」追加的训练点

  // ———— 最小二乘（Householder QR），可带 L2：min Σ(ŷ−y)² + λ Σ_{j≥1} w_j² ————
  function lstsq(A, b) {                          // A: m×n 行数组（m ≥ n），返回 x
    const m = A.length, n = A[0].length, R = A.map(r => r.slice()), y = b.slice();
    for (let k = 0; k < n; k++) {
      let s = 0; for (let i = k; i < m; i++) s += R[i][k] * R[i][k];
      let nrm = Math.sqrt(s); if (nrm === 0) continue;
      if (R[k][k] > 0) nrm = -nrm;
      const v = []; for (let i = k; i < m; i++) v.push(R[i][k]); v[0] -= nrm;
      let vv = 0; for (const t of v) vv += t * t; if (vv === 0) continue;
      for (let j = k; j < n; j++) { let d = 0; for (let i = k; i < m; i++) d += v[i - k] * R[i][j]; d = 2 * d / vv; for (let i = k; i < m; i++) R[i][j] -= d * v[i - k]; }
      let d = 0; for (let i = k; i < m; i++) d += v[i - k] * y[i]; d = 2 * d / vv; for (let i = k; i < m; i++) y[i] -= d * v[i - k];
    }
    const x = new Array(n).fill(0);
    for (let i = n - 1; i >= 0; i--) { let s = y[i]; for (let j = i + 1; j < n; j++) s -= R[i][j] * x[j]; x[i] = Math.abs(R[i][i]) < 1e-300 ? 0 : s / R[i][i]; }
    return x;
  }
  const powers = (x, d) => { const r = [1]; for (let j = 1; j <= d; j++) r.push(r[j - 1] * x); return r; };
  // 多项式拟合：ŷ = w0 + w1 x + … + wd x^d
  function polyfit(pts, d, lam = 0) {
    const A = pts.map(p => powers(p.x, d)), b = pts.map(p => p.y);
    if (lam > 0) for (let j = 1; j <= d; j++) { const r = new Array(d + 1).fill(0); r[j] = Math.sqrt(lam); A.push(r); b.push(0); }
    if (A.length < d + 1) { // 点数少于系数个数时不在本讲范围内（只会在实验里拖到极端时出现），补 0 行让它可解
      while (A.length < d + 1) { A.push(new Array(d + 1).fill(0)); b.push(0); }
    }
    return lstsq(A, b);
  }
  const polyval = (w, x) => { let s = 0; for (let j = w.length - 1; j >= 0; j--) s = s * x + w[j]; return s; };
  const mse = (pred, pts) => pts.reduce((s, p) => s + (pred(p.x) - p.y) ** 2, 0) / pts.length;

  // ———— 偏差与方差：同样的 10 个 x，噪声重抽 R 次 ————
  const GRID = Array.from({ length: 101 }, (_, i) => i / 100);
  function biasVar(d, R = 200, lam = 0, seed = 7) {
    const G = rng(seed), xs = TRAIN.map(p => p.x), fits = [];
    for (let r = 0; r < R; r++) {
      const pts = xs.map(x => ({ x, y: r2(f(x) + SIGMA * G.n()) }));
      fits.push(polyfit(pts, d, lam));
    }
    // 在训练点覆盖的范围 [0.02, 0.95] 里取格点
    const gx = GRID.filter(x => x >= xs[0] && x <= xs[xs.length - 1]);
    let b2 = 0, v = 0; const mean = [];
    for (const x of gx) {
      const ps = fits.map(w => polyval(w, x)); const m = ps.reduce((a, c) => a + c, 0) / R;
      mean.push(m); b2 += (m - f(x)) ** 2; v += ps.reduce((a, c) => a + (c - m) ** 2, 0) / R;
    }
    return { fits, gx, mean, bias2: b2 / gx.length, variance: v / gx.length };
  }

  // ———— 小 MLP：1 → H → H → 1，tanh，Adam，全批量；可选 dropout（训练时随机关掉隐藏单元） ————
  function mlpInit(H, seed) {
    const R = rng(seed), g = (s) => R.n() * s;
    const W1 = Array.from({ length: H }, () => g(3)), b1 = Array.from({ length: H }, () => g(1));
    const W2 = Array.from({ length: H }, () => Array.from({ length: H }, () => g(1 / Math.sqrt(H)))), b2 = new Array(H).fill(0);
    const W3 = Array.from({ length: H }, () => g(1 / Math.sqrt(H))), b3 = [0];
    return { H, W1, b1, W2, b2, W3, b3 };
  }
  const tx = (x) => 2 * x - 1;                    // 输入缩放到 [−1, 1]
  function mlpForward(P, x, mask1, mask2, keep) {
    const H = P.H, z1 = new Array(H), h1 = new Array(H), z2 = new Array(H), h2 = new Array(H);
    const t = tx(x);
    for (let i = 0; i < H; i++) { z1[i] = P.W1[i] * t + P.b1[i]; h1[i] = Math.tanh(z1[i]); if (mask1) h1[i] = mask1[i] ? h1[i] / keep : 0; }
    for (let i = 0; i < H; i++) { let s = P.b2[i]; const row = P.W2[i]; for (let j = 0; j < H; j++) s += row[j] * h1[j]; z2[i] = s; h2[i] = Math.tanh(s); if (mask2) h2[i] = mask2[i] ? h2[i] / keep : 0; }
    let o = P.b3[0]; for (let i = 0; i < H; i++) o += P.W3[i] * h2[i];
    return { t, h1, h2, o };
  }
  const mlpPredict = (P) => (x) => mlpForward(P, x, null, null, 1).o;
  // 训练器：每调用一次 advance(k) 往前走 k 步；每 every 步记一次训练损失、验证损失（以及可选的整条曲线快照）。
  // mlpTrain 一口气跑完；实验页分小段跑，边训练边画。
  function mlpTrainer({ H = 32, steps = 2000, lr = 0.01, drop = 0, seed = 11, every = 10, train = TRAIN, val = VAL, grid = null } = {}) {
    const P = mlpInit(H, seed), R = rng(seed + 1000), keep = 1 - drop;
    const params = [P.W1, P.b1, P.b2, P.W3, P.b3, ...P.W2];
    const m = params.map(a => new Array(a.length).fill(0)), v = params.map(a => new Array(a.length).fill(0));
    const b1 = 0.9, b2 = 0.999, eps = 1e-8;
    const log = [], snaps = []; let best = { step: 0, val: Infinity, P: null }; let s = 0;
    const snap = () => JSON.parse(JSON.stringify(P));
    const evalNow = () => {
      const pr = mlpPredict(P); const tr = mse(pr, train), va = mse(pr, val);
      log.push({ step: s, train: tr, val: va });
      if (grid) snaps.push(grid.map(pr));
      if (va < best.val) best = { step: s, val: va, train: tr, P: snap() };
    };
    function oneStep() {
      const g = params.map(a => new Array(a.length).fill(0));
      const [gW1, gb1, gb2, gW3, gb3] = g, gW2 = g.slice(5);
      const n = train.length;
      for (const p of train) {
        const mk1 = drop > 0 ? Array.from({ length: P.H }, () => R.u() < keep) : null;
        const mk2 = drop > 0 ? Array.from({ length: P.H }, () => R.u() < keep) : null;
        const F = mlpForward(P, p.x, mk1, mk2, keep);
        const dO = 2 * (F.o - p.y) / n;                    // MSE 对输出的导数
        gb3[0] += dO;
        const dh2 = new Array(P.H);
        for (let i = 0; i < P.H; i++) { gW3[i] += dO * F.h2[i]; dh2[i] = dO * P.W3[i]; }
        const dz2 = new Array(P.H);
        for (let i = 0; i < P.H; i++) {
          if (mk2 && !mk2[i]) { dz2[i] = 0; continue; }   // 被关掉的单元没有梯度
          const hraw = mk2 ? F.h2[i] * keep : F.h2[i];     // 放大之前的 tanh 值
          dz2[i] = dh2[i] * (mk2 ? 1 / keep : 1) * (1 - hraw * hraw);
        }
        const dh1 = new Array(P.H).fill(0);
        for (let i = 0; i < P.H; i++) { if (dz2[i] === 0) continue; gb2[i] += dz2[i]; const row = P.W2[i], grow = gW2[i]; for (let j = 0; j < P.H; j++) { grow[j] += dz2[i] * F.h1[j]; dh1[j] += dz2[i] * row[j]; } }
        for (let i = 0; i < P.H; i++) {
          if (mk1 && !mk1[i]) continue;
          const hraw = mk1 ? F.h1[i] * keep : F.h1[i];
          const dz1 = dh1[i] * (mk1 ? 1 / keep : 1) * (1 - hraw * hraw);
          gW1[i] += dz1 * F.t; gb1[i] += dz1;
        }
      }
      const c1 = 1 - Math.pow(b1, s + 1), c2 = 1 - Math.pow(b2, s + 1);
      const eta = lr * 0.5 * (1 + Math.cos(Math.PI * s / steps));   // 余弦衰减到 0，最后几步几乎不动，结果更稳
      for (let k = 0; k < params.length; k++) {
        const a = params[k], gk = g[k], mk = m[k], vk = v[k];
        for (let i = 0; i < a.length; i++) {
          mk[i] = b1 * mk[i] + (1 - b1) * gk[i]; vk[i] = b2 * vk[i] + (1 - b2) * gk[i] * gk[i];
          a[i] -= eta * (mk[i] / c1) / (Math.sqrt(vk[i] / c2) + eps);
        }
      }
      s++;
    }
    evalNow();
    return {
      P, log, snaps, get best() { return best; }, get step() { return s; }, steps, done: () => s >= steps,
      advance(k) { for (let i = 0; i < k && s < steps; i++) { oneStep(); if (s % every === 0) evalNow(); } },
    };
  }
  function mlpTrain(opts = {}) {
    const T = mlpTrainer(opts); T.advance(T.steps);
    return { P: T.P, log: T.log, snaps: T.snaps, best: T.best, final: T.log[T.log.length - 1] };
  }

  // ———— 双下降：阶数继续加到 9 以上。基函数换成勒让德多项式 P_j(2x − 1)（同样能组合出所有 D 阶多项式），
  //      系数多于数据时有无数条曲线穿过全部点，取系数平方和 ‖w‖² 最小的那条 ————
  function legendre(x, D) { const t = 2 * x - 1, P = [1, t]; for (let j = 1; j < D; j++) P.push(((2 * j + 1) * t * P[j] - j * P[j - 1]) / (j + 1)); return P.slice(0, D + 1); }
  const MN_EPS = 1e-10;   // 极小的 L2，只为数值稳定，结果与严格的最小范数解几乎相同
  function minNormFit(pts, D) {
    const Phi = pts.map(p => legendre(p.x, D)), y = pts.map(p => p.y), n = pts.length, N = D + 1;
    if (N <= n) {   // 系数不多于数据：普通最小二乘（和 polyfit 是同一条曲线）
      const A = Phi.map(r => r.slice()), b = y.slice();
      for (let j = 0; j < N; j++) { const r = new Array(N).fill(0); r[j] = Math.sqrt(MN_EPS); A.push(r); b.push(0); }
      return lstsq(A, b);
    }
    // 系数多于数据：w = Φᵀα，(ΦΦᵀ + εI) α = y
    const K = Phi.map((a, i) => Phi.map((b, j) => a.reduce((s, v, k) => s + v * b[k], 0) + (i === j ? MN_EPS : 0)));
    const alpha = lstsq(K, y);
    const w = new Array(N).fill(0);
    for (let i = 0; i < n; i++) for (let j = 0; j < N; j++) w[j] += Phi[i][j] * alpha[i];
    return w;
  }
  const legval = (w, x) => legendre(x, w.length - 1).reduce((s, v, j) => s + v * w[j], 0);
  const norm = (w) => Math.sqrt(w.reduce((s, v) => s + v * v, 0));

  return { rng, f, SIGMA, r2, sample, TRAIN, VAL, TEST, EXTRA, lstsq, polyfit, polyval, mse, GRID, biasVar, mlpInit, mlpForward, mlpPredict, mlpTrainer, mlpTrain, legendre, minNormFit, legval, norm };
})();
if (typeof module !== 'undefined') module.exports = CORE;
