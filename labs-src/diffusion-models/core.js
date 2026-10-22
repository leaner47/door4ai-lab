/* 扩散模型一讲的计算核心：实验页（由 toy.py 内联进 index.html）与 node 核对脚本（mc.mjs）共用同一份代码。
   数据是二维玩具分布（两个像素的「图」），用若干个圆形高斯团的混合表示；
   去噪用的「预测噪声」默认是解析最优预测（给定 x_t 时噪声的条件平均，能精确算出），不是训练出来的网络；
   tinyMLP 是页内真正训练的小网络。随机数用固定种子。 */
const DM = (() => {
  /* ———— 随机数：mulberry32 + Box–Muller，固定种子 ———— */
  function rng(seed) {
    let a = seed >>> 0;
    const u = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    let spare = null;
    const n = () => { if (spare !== null) { const s = spare; spare = null; return s; } let x = 0; while (x === 0) x = u(); const y = u(); const r = Math.sqrt(-2 * Math.log(x)); spare = r * Math.sin(2 * Math.PI * y); return r * Math.cos(2 * Math.PI * y); };
    return { u, n };
  }

  /* ———— 噪声调度：数组下标就是 t，abar[0] = 1 ———— */
  function fromBetas(betas) {
    const T = betas.length, beta = [0], alpha = [1], abar = [1];
    for (let t = 1; t <= T; t++) { beta[t] = betas[t - 1]; alpha[t] = 1 - beta[t]; abar[t] = abar[t - 1] * alpha[t]; }
    return { T, beta, alpha, abar };
  }
  function linear(T = 1000, b1 = 1e-4, bT = 0.02) {          // DDPM：β 从 10⁻⁴ 线性增到 0.02
    const b = []; for (let i = 0; i < T; i++) b.push(b1 + (bT - b1) * i / (T - 1)); return fromBetas(b);
  }
  function cosine(T = 1000, s = 0.008) {                        // Nichol & Dhariwal 2021，β 不超过 0.999
    const f = (t) => Math.cos((t / T + s) / (1 + s) * Math.PI / 2) ** 2;
    const b = []; for (let t = 1; t <= T; t++) b.push(Math.min(0.999, 1 - f(t) / f(t - 1))); return fromBetas(b);
  }
  function fromAlphas(alphas) { return fromBetas(alphas.map((a) => 1 - a)); }

  /* ———— 玩具数据：两个像素的「图」，每个像素在 −1（黑）到 1（白）之间 ———— */
  const DISTS = {
    two: { name: '两团', comps: [{ mu: [0.7, -0.7], s: 0.1, w: 0.5, cls: 0 }, { mu: [-0.7, 0.7], s: 0.1, w: 0.5, cls: 1 }] },
    overlap: { name: '重叠的两团', comps: [{ mu: [0.35, -0.35], s: 0.4, w: 0.5, cls: 0 }, { mu: [-0.35, 0.35], s: 0.4, w: 0.5, cls: 1 }] },
    ring: { name: '圆环', comps: Array.from({ length: 24 }, (_, i) => { const a = 2 * Math.PI * i / 24; return { mu: [0.75 * Math.cos(a), 0.75 * Math.sin(a)], s: 0.05, w: 1 / 24, cls: Math.cos(a) - Math.sin(a) > 0 ? 0 : 1 }; }) },
  };
  function comps(dist, cls) {
    const cs = cls == null ? dist.comps : dist.comps.filter((c) => c.cls === cls);
    const W = cs.reduce((s, c) => s + c.w, 0);
    return cs.map((c) => ({ ...c, w: c.w / W }));
  }
  function sampleData(dist, n, R, cls = null) {
    const cs = comps(dist, cls), out = [];
    for (let i = 0; i < n; i++) {
      let u = R.u(), k = 0; while (k < cs.length - 1 && u > cs[k].w) { u -= cs[k].w; k++; }
      const c = cs[k]; out.push([c.mu[0] + c.s * R.n(), c.mu[1] + c.s * R.n()]);
    }
    return out;
  }

  /* ———— 前向加噪：x_t = √ᾱ x₀ + √(1−ᾱ) ε ———— */
  const noisy = (x0, ab, e) => [Math.sqrt(ab) * x0[0] + Math.sqrt(1 - ab) * e[0], Math.sqrt(ab) * x0[1] + Math.sqrt(1 - ab) * e[1]];

  /* ———— 解析最优预测：只看到 x_t 时，噪声 ε 的条件平均 E[ε | x_t]（cls 给定时只用那一类的团）
     每一团 k：x_t ~ N(√ᾱ μ_k, v_k I)，v_k = ᾱ s_k² + 1 − ᾱ；E[ε | x_t, k] = √(1−ᾱ) (x_t − √ᾱ μ_k) / v_k ———— */
  function epsOpt(dist, x, ab, cls = null, detail = false) {
    const cs = comps(dist, cls), sa = Math.sqrt(ab), sb = Math.sqrt(1 - ab);
    const lw = cs.map((c) => { const v = ab * c.s * c.s + 1 - ab; const dx = x[0] - sa * c.mu[0], dy = x[1] - sa * c.mu[1]; return Math.log(c.w) - Math.log(v) - (dx * dx + dy * dy) / (2 * v); });
    const m = Math.max(...lw); const ex = lw.map((l) => Math.exp(l - m)); const S = ex.reduce((a, b) => a + b, 0);
    let e0 = 0, e1 = 0; const r = [], each = [];
    cs.forEach((c, k) => { const v = ab * c.s * c.s + 1 - ab; const rk = ex[k] / S; r.push(rk); const ek = [sb * (x[0] - sa * c.mu[0]) / v, sb * (x[1] - sa * c.mu[1]) / v]; each.push(ek); e0 += rk * ek[0]; e1 += rk * ek[1]; });
    return detail ? { eps: [e0, e1], r, each, cs } : [e0, e1];
  }
  /* classifier-free guidance：ε̃ = ε_无条件 + s (ε_有条件 − ε_无条件)；s = 1 就是普通的有条件预测 */
  function epsCFG(dist, x, ab, cls, s) {
    const eu = epsOpt(dist, x, ab, null), ec = epsOpt(dist, x, ab, cls);
    return [eu[0] + s * (ec[0] - eu[0]), eu[1] + s * (ec[1] - eu[1])];
  }

  /* ———— 采样用的时间步：从 T 均匀取 steps 个，最后一步走到 0 ———— */
  function timesteps(T, steps) {
    const ts = []; for (let i = 0; i < steps; i++) ts.push(Math.round(T - i * T / steps)); ts.push(0);
    return ts;   // 例：T = 1000, steps = 4 → 1000, 750, 500, 250, 0
  }
  /* 一步往回走：从 t 到 tp（tp < t）。ddpm：均值 + 新噪声；ddim：先猜 x̂₀ 再按 tp 的比例重新混合，不加新噪声 */
  function step(x, e, abT, abP, method, z) {
    if (method === 'ddim') {
      const x0 = [(x[0] - Math.sqrt(1 - abT) * e[0]) / Math.sqrt(abT), (x[1] - Math.sqrt(1 - abT) * e[1]) / Math.sqrt(abT)];
      return [Math.sqrt(abP) * x0[0] + Math.sqrt(1 - abP) * e[0], Math.sqrt(abP) * x0[1] + Math.sqrt(1 - abP) * e[1]];
    }
    const a = abT / abP, b = 1 - a, c = b / Math.sqrt(1 - abT), k = 1 / Math.sqrt(a);
    const sig = Math.sqrt(Math.max(0, (1 - abP) / (1 - abT) * b));      // σ² = β̃：后验方差
    return [k * (x[0] - c * e[0]) + sig * z[0], k * (x[1] - c * e[1]) + sig * z[1]];
  }
  /* 完整采样：n 个点从纯噪声出发。pred(x, ab) 返回预测的噪声；keep 记下中间各步 */
  function sample({ sched, steps, method = 'ddpm', n = 400, seed = 7, pred, keep = false }) {
    const R = rng(seed), ts = timesteps(sched.T, Math.min(steps, sched.T));
    let xs = []; for (let i = 0; i < n; i++) xs.push([R.n(), R.n()]);
    const hist = keep ? [{ t: sched.T, xs: xs.map((p) => p.slice()) }] : null;
    for (let i = 0; i < ts.length - 1; i++) {
      const abT = sched.abar[ts[i]], abP = sched.abar[ts[i + 1]];
      xs = xs.map((x) => step(x, pred(x, abT, ts[i]), abT, abP, method, [R.n(), R.n()]));
      if (keep) hist.push({ t: ts[i + 1], xs: xs.map((p) => p.slice()) });
    }
    return keep ? hist : xs;
  }
  /* 质量：落在某一团 2.5 个标准差以内的比例（真实数据约 95.6%） */
  function quality(dist, xs, cls = null) {
    const cs = comps(dist, cls); let ok = 0;
    for (const x of xs) { if (cs.some((c) => Math.hypot(x[0] - c.mu[0], x[1] - c.mu[1]) < 2.5 * c.s)) ok++; }
    return ok / xs.length;
  }
  const stats = (xs) => { const n = xs.length; const m = [0, 0]; xs.forEach((x) => { m[0] += x[0] / n; m[1] += x[1] / n; }); let v = 0; xs.forEach((x) => { v += ((x[0] - m[0]) ** 2 + (x[1] - m[1]) ** 2) / n; }); return { mean: m, sd: Math.sqrt(v / 2) }; };

  /* ———— 页内真正训练的小网络：输入 (x₁, x₂, 时间特征 6 个) → 32 → 32 → 2，tanh，Adam ———— */
  function tfeat(t, T) { const u = t / T, f = []; for (let k = 1; k <= 3; k++) { f.push(Math.sin(Math.PI * k * u)); f.push(Math.cos(Math.PI * k * u)); } return f; }
  function mlp(seed = 11, H = 32) {
    const R = rng(seed), I = 8, O = 2;
    const mat = (r, c, sc) => Float64Array.from({ length: r * c }, () => R.n() * sc);
    const P = { W1: mat(H, I, 1 / Math.sqrt(I)), b1: new Float64Array(H), W2: mat(H, H, 1 / Math.sqrt(H)), b2: new Float64Array(H), W3: mat(O, H, 0.5 / Math.sqrt(H)), b3: new Float64Array(O) };
    const M = {}, V = {}; for (const k in P) { M[k] = new Float64Array(P[k].length); V[k] = new Float64Array(P[k].length); }
    let step = 0;
    function fwd(inp) {
      const h1 = new Float64Array(H), h2 = new Float64Array(H), o = new Float64Array(O);
      for (let i = 0; i < H; i++) { let s = P.b1[i]; for (let j = 0; j < I; j++) s += P.W1[i * I + j] * inp[j]; h1[i] = Math.tanh(s); }
      for (let i = 0; i < H; i++) { let s = P.b2[i]; for (let j = 0; j < H; j++) s += P.W2[i * H + j] * h1[j]; h2[i] = Math.tanh(s); }
      for (let i = 0; i < O; i++) { let s = P.b3[i]; for (let j = 0; j < H; j++) s += P.W3[i * H + j] * h2[j]; o[i] = s; }
      return { h1, h2, o };
    }
    const input = (x, t, T) => [x[0], x[1], ...tfeat(t, T)];
    function predict(x, t, T) { const o = fwd(input(x, t, T)).o; return [o[0], o[1]]; }
    /* 一步训练：随机取 batch 个 (x₀, t, ε)，损失 = ‖ε − ε_θ(x_t, t)‖² 的平均（DDPM 的 L_simple） */
    function train(dist, sched, R2, batch = 128, lr = 3e-3) {
      const G = {}; for (const k in P) G[k] = new Float64Array(P[k].length);
      let L = 0; const x0s = sampleData(dist, batch, R2);
      for (let b = 0; b < batch; b++) {
        const t = 1 + Math.floor(R2.u() * sched.T), e = [R2.n(), R2.n()], xt = noisy(x0s[b], sched.abar[t], e);
        const inp = input(xt, t, sched.T), { h1, h2, o } = fwd(inp);
        const d = [o[0] - e[0], o[1] - e[1]]; L += d[0] * d[0] + d[1] * d[1];
        const go = [2 * d[0] / batch, 2 * d[1] / batch], g2 = new Float64Array(H), g1 = new Float64Array(H);
        for (let i = 0; i < O; i++) { G.b3[i] += go[i]; for (let j = 0; j < H; j++) { G.W3[i * H + j] += go[i] * h2[j]; g2[j] += go[i] * P.W3[i * H + j]; } }
        for (let j = 0; j < H; j++) g2[j] *= 1 - h2[j] * h2[j];
        for (let i = 0; i < H; i++) { G.b2[i] += g2[i]; for (let j = 0; j < H; j++) { G.W2[i * H + j] += g2[i] * h1[j]; g1[j] += g2[i] * P.W2[i * H + j]; } }
        for (let j = 0; j < H; j++) g1[j] *= 1 - h1[j] * h1[j];
        for (let i = 0; i < H; i++) { G.b1[i] += g1[i]; for (let j = 0; j < I; j++) G.W1[i * I + j] += g1[i] * inp[j]; }
      }
      step++; const b1 = 0.9, b2 = 0.999;
      for (const k in P) for (let i = 0; i < P[k].length; i++) {
        M[k][i] = b1 * M[k][i] + (1 - b1) * G[k][i]; V[k][i] = b2 * V[k][i] + (1 - b2) * G[k][i] * G[k][i];
        P[k][i] -= lr * (M[k][i] / (1 - b1 ** step)) / (Math.sqrt(V[k][i] / (1 - b2 ** step)) + 1e-8);
      }
      return L / batch;
    }
    return { predict, train, get steps() { return step; } };
  }
  /* 解析最优预测的平均损失（所有 t 均匀、x₀ 和 ε 随机）：这是任何网络都降不到它以下的下限 */
  function optLoss(dist, sched, n, R) {
    let L = 0; const x0s = sampleData(dist, n, R);
    for (let i = 0; i < n; i++) { const t = 1 + Math.floor(R.u() * sched.T), e = [R.n(), R.n()], xt = noisy(x0s[i], sched.abar[t], e), p = epsOpt(dist, xt, sched.abar[t]); L += (p[0] - e[0]) ** 2 + (p[1] - e[1]) ** 2; }
    return L / n;
  }

  return { rng, linear, cosine, fromAlphas, DISTS, comps, sampleData, noisy, epsOpt, epsCFG, timesteps, step, sample, quality, stats, mlp, tfeat, optLoss };
})();
if (typeof module !== 'undefined') module.exports = DM;
