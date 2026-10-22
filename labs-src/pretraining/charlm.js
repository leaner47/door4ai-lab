// 字符级小语言模型：bigram 表 或 小 MLP（看前 C 个字）。前向、交叉熵、手写反向、AdamW。
// 实验页 04 里的 <script id="charlm"> 与本文件逐字相同（toy.py 运行时检查）；node 里用 test.mjs 跑同一份代码。
function makeRng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function makeLM(text, opt) {
  const kind = opt.kind, C = kind === 'bigram' ? 1 : (opt.ctx || 4), D = opt.emb || 24, H = opt.hidden || 128;
  const chars = ['␂', ...Array.from(new Set(text))]; const V = chars.length; const id = {}; chars.forEach((c, i) => id[c] = i);
  const ids = Array.from(text, (c) => id[c]);
  const rng = makeRng(opt.seed || 1); const gauss = () => { let u = 0, v = 0; while (!u) u = rng(); v = rng(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const P = {}; const shapes = kind === 'bigram' ? { T: V * V } : { E: V * D, W1: C * D * H, b1: H, W2: H * V, b2: V };
  for (const k in shapes) P[k] = new Float32Array(shapes[k]);
  if (kind !== 'bigram') {
    for (let i = 0; i < P.E.length; i++) P.E[i] = gauss() * 0.5;
    const s1 = 1 / Math.sqrt(C * D); for (let i = 0; i < P.W1.length; i++) P.W1[i] = gauss() * s1;
    const s2 = 0.3 / Math.sqrt(H); for (let i = 0; i < P.W2.length; i++) P.W2[i] = gauss() * s2;
  }
  const G = {}, M = {}, S = {}; for (const k in P) { G[k] = new Float32Array(P[k].length); M[k] = new Float32Array(P[k].length); S[k] = new Float32Array(P[k].length); }
  let nParams = 0; for (const k in P) nParams += P[k].length;
  const ctxAt = (arr, t) => { const c = new Array(C); for (let j = 0; j < C; j++) { const p = t - C + j; c[j] = p >= 0 ? arr[p] : 0; } return c; };
  const logits = new Float32Array(V), h = new Float32Array(H), x = new Float32Array(C * D), dh = new Float32Array(H);
  function forward(ctx) {
    if (kind === 'bigram') { const r = ctx[C - 1] * V; for (let v = 0; v < V; v++) logits[v] = P.T[r + v]; return; }
    for (let j = 0; j < C; j++) for (let d = 0; d < D; d++) x[j * D + d] = P.E[ctx[j] * D + d];
    for (let k = 0; k < H; k++) { let s = P.b1[k]; for (let i = 0; i < C * D; i++) s += x[i] * P.W1[i * H + k]; h[k] = Math.tanh(s); }
    for (let v = 0; v < V; v++) logits[v] = P.b2[v];
    for (let k = 0; k < H; k++) { const hk = h[k], o = k * V; for (let v = 0; v < V; v++) logits[v] += hk * P.W2[o + v]; }
  }
  function softmaxInPlace(z, temp = 1) { let m = -1e9; for (let v = 0; v < V; v++) m = Math.max(m, z[v] / temp); let s = 0; for (let v = 0; v < V; v++) { z[v] = Math.exp(z[v] / temp - m); s += z[v]; } for (let v = 0; v < V; v++) z[v] /= s; }
  // 一个训练步：取 B 个位置 → 前向 → 交叉熵 → 反向 → AdamW
  let step = 0;
  function trainStep(B, lr, trainIds) {
    for (const k in G) G[k].fill(0);
    let loss = 0;
    for (let b = 0; b < B; b++) {
      const t = 1 + Math.floor(rng() * (trainIds.length - 1)); const ctx = ctxAt(trainIds, t), y = trainIds[t];
      forward(ctx); softmaxInPlace(logits); loss += -Math.log(Math.max(logits[y], 1e-12));
      logits[y] -= 1; // ∂L/∂z = p − y
      if (kind === 'bigram') { const r = ctx[C - 1] * V; for (let v = 0; v < V; v++) G.T[r + v] += logits[v] / B; continue; }
      for (let v = 0; v < V; v++) G.b2[v] += logits[v] / B;
      for (let k = 0; k < H; k++) { const o = k * V; let s = 0; for (let v = 0; v < V; v++) { G.W2[o + v] += h[k] * logits[v] / B; s += P.W2[o + v] * logits[v]; } dh[k] = s * (1 - h[k] * h[k]) / B; }
      for (let k = 0; k < H; k++) G.b1[k] += dh[k];
      for (let i = 0; i < C * D; i++) { let s = 0; const xi = x[i], o = i * H; for (let k = 0; k < H; k++) { G.W1[o + k] += xi * dh[k]; s += P.W1[o + k] * dh[k]; } G.E[ctx[Math.floor(i / D)] * D + (i % D)] += s; }
    }
    step++; const b1 = 0.9, b2 = 0.99, eps = 1e-8, wd = kind === 'bigram' ? 0 : 0.01;
    const c1 = 1 - Math.pow(b1, step), c2 = 1 - Math.pow(b2, step);
    for (const k in P) { const p = P[k], g = G[k], m = M[k], s = S[k];
      for (let i = 0; i < p.length; i++) { m[i] = b1 * m[i] + (1 - b1) * g[i]; s[i] = b2 * s[i] + (1 - b2) * g[i] * g[i]; p[i] -= lr * ((m[i] / c1) / (Math.sqrt(s[i] / c2) + eps) + wd * p[i]); } }
    return loss / B;
  }
  function evalLoss(arr) { let L = 0, n = 0; for (let t = 1; t < arr.length; t++) { forward(ctxAt(arr, t)); softmaxInPlace(logits); L += -Math.log(Math.max(logits[arr[t]], 1e-12)); n++; } return L / n; }
  function sample(n, temp, seed, prefix = '') { const r = makeRng(seed); const out = prefix ? Array.from(prefix, (c) => id[c] ?? 0) : []; const arr = [0, ...out];
    for (let i = 0; i < n; i++) { forward(ctxAt(arr, arr.length)); softmaxInPlace(logits, temp); let u = r(), v = 0; for (; v < V - 1; v++) { u -= logits[v]; if (u <= 0) break; } if (v === 0) v = 1; arr.push(v); }
    return arr.slice(1).map((v) => chars[v]).join(''); }
  function probsAfter(prefix) { const arr = [0, ...Array.from(prefix, (c) => id[c] ?? 0)]; forward(ctxAt(arr, arr.length)); const z = Float32Array.from(logits); softmaxInPlace(z); return z; }
  return { V, C, chars, id, ids, nParams, trainStep, evalLoss, sample, probsAfter, get step() { return step; } };
}
function lrAt(t, T, peak, warm, floorRatio, kind) {
  if (kind === 'const') return peak;
  if (t < warm) return peak * (t + 1) / warm;
  const q = Math.min(1, (t - warm) / Math.max(1, T - warm));
  return peak * floorRatio + 0.5 * peak * (1 - floorRatio) * (1 + Math.cos(Math.PI * q));
}
