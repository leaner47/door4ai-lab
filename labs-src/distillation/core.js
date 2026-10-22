/*CORE-BEGIN*/
/* 蒸馏实验的计算核心：贯穿算例（四类 logits）+ 页内真实训练（老师 MLP → 学生 MLP）。
   这段代码原样内联在 public/labs/distillation/index.html 里；labs-src/distillation/run_lab.mjs 从页面里抽出同一段来跑，
   文章里的训练结果（误差、分界图、容量曲线）都来自它。 */
const D = {};
D.CLASSES = ['猫', '狗', '狐狸', '汽车'];
D.V = [4, 1, 0, -5];      // 老师对一张猫图的 logits（示意，平均为 0）
D.Z = [2, 0, 1, -3];      // 学生对同一张图的 logits（示意，平均为 0）
D.HARD = 0;               // 硬标签：猫
D.softmax = (z, T = 1) => { const m = Math.max(...z.map(v => v / T)); const e = z.map(v => Math.exp(v / T - m)); const s = e.reduce((a, b) => a + b, 0); return e.map(v => v / s); };
D.entropy = (p) => -p.reduce((s, v) => s + (v > 0 ? v * Math.log(v) : 0), 0);
D.ce = (p, q) => -p.reduce((s, v, i) => s + (v > 0 ? v * Math.log(q[i]) : 0), 0);
D.kl = (p, q) => p.reduce((s, v, i) => s + (v > 0 ? v * Math.log(v / q[i]) : 0), 0);
/* 损失 = α·CE(硬标签, q¹) + (1 − α)·s·KL(pᵀ ‖ qᵀ)，s = T²（或 1）。返回每一项与各自对 z 的梯度 */
D.loss = (v, z, y, T, alpha, mulT2 = true) => {
  const pT = D.softmax(v, T), qT = D.softmax(z, T), q1 = D.softmax(z, 1);
  const s = mulT2 ? T * T : 1;
  const ce = -Math.log(q1[y]), kl = D.kl(pT, qT);
  const gHard = q1.map((q, k) => q - (k === y ? 1 : 0));
  const gSoft = qT.map((q, k) => (q - pT[k]) / T);           // KL(pᵀ‖qᵀ) 对 z 的梯度
  const gTot = gHard.map((g, k) => alpha * g + (1 - alpha) * s * gSoft[k]);
  return { pT, qT, q1, ce, kl, s, total: alpha * ce + (1 - alpha) * s * kl, gHard, gSoft, gTot };
};
D.norm = (g) => Math.sqrt(g.reduce((a, b) => a + b * b, 0));

/* ———— 页内真实训练 ———— */
D.rng = (seed) => { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; }; };
D.gauss = (r) => { let u = 0; while (u === 0) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); };
D.NOISE = 0.08;
/* 三条旋臂的二维数据，三类；X 是 [x0, y0, x1, y1, …] */
D.makeData = (n, seed) => {
  const r = D.rng(seed), X = new Float64Array(2 * n), Y = new Int32Array(n);
  for (let i = 0; i < n; i++) {
    const c = i % 3, t = r(), ang = c * 2 * Math.PI / 3 + t * 3.2, rad = 0.15 + t * 0.85;
    X[2 * i] = rad * Math.cos(ang) + D.gauss(r) * D.NOISE; X[2 * i + 1] = rad * Math.sin(ang) + D.gauss(r) * D.NOISE; Y[i] = c;
  }
  return { n, X, Y };
};
/* 单隐层 MLP：2 → h（tanh）→ 3 */
D.init = (h, seed) => {
  const r = D.rng(seed), m = { h, W1: new Float64Array(2 * h), b1: new Float64Array(h), W2: new Float64Array(3 * h), b2: new Float64Array(3) };
  for (let j = 0; j < 2 * h; j++) m.W1[j] = D.gauss(r) * 1.5;
  for (let j = 0; j < h; j++) m.b1[j] = D.gauss(r) * 0.5;
  for (let j = 0; j < 3 * h; j++) m.W2[j] = D.gauss(r) / Math.sqrt(h);
  return m;
};
D.logits = (m, x0, x1, a) => {
  const h = m.h, z = [m.b2[0], m.b2[1], m.b2[2]];
  for (let j = 0; j < h; j++) { const t = Math.tanh(m.W1[2 * j] * x0 + m.W1[2 * j + 1] * x1 + m.b1[j]); if (a) a[j] = t; z[0] += m.W2[j] * t; z[1] += m.W2[h + j] * t; z[2] += m.W2[2 * h + j] * t; }
  return z;
};
/* 全批量 Adam。target = null 用硬标签 Y（交叉熵）；否则 target[i] 是老师在温度 T 下的概率，损失 T²·KL(pᵀ‖qᵀ) */
D.train = (m, data, { target = null, T = 1, steps = 300, lr = 0.03 } = {}) => {
  const { n, X, Y } = data, h = m.h, P = [m.W1, m.b1, m.W2, m.b2];
  const G = P.map(p => new Float64Array(p.length)), M1 = P.map(p => new Float64Array(p.length)), M2 = P.map(p => new Float64Array(p.length));
  const a = new Float64Array(h), dz = [0, 0, 0];
  for (let t = 1; t <= steps; t++) {
    G.forEach(g => g.fill(0));
    for (let i = 0; i < n; i++) {
      const x0 = X[2 * i], x1 = X[2 * i + 1], z = D.logits(m, x0, x1, a);
      if (target) { const q = D.softmax(z, T); for (let k = 0; k < 3; k++) dz[k] = T * T * (q[k] - target[i][k]) / T; }
      else { const q = D.softmax(z, 1); for (let k = 0; k < 3; k++) dz[k] = q[k] - (k === Y[i] ? 1 : 0); }
      for (let k = 0; k < 3; k++) { G[3][k] += dz[k]; for (let j = 0; j < h; j++) G[2][k * h + j] += dz[k] * a[j]; }
      for (let j = 0; j < h; j++) {
        const da = (m.W2[j] * dz[0] + m.W2[h + j] * dz[1] + m.W2[2 * h + j] * dz[2]) * (1 - a[j] * a[j]);
        G[1][j] += da; G[0][2 * j] += da * x0; G[0][2 * j + 1] += da * x1;
      }
    }
    const c1 = 1 - Math.pow(0.9, t), c2 = 1 - Math.pow(0.999, t);
    for (let p = 0; p < 4; p++) for (let j = 0; j < P[p].length; j++) {
      const g = G[p][j] / n; M1[p][j] = 0.9 * M1[p][j] + 0.1 * g; M2[p][j] = 0.999 * M2[p][j] + 0.001 * g * g;
      P[p][j] -= lr * (M1[p][j] / c1) / (Math.sqrt(M2[p][j] / c2) + 1e-8);
    }
  }
  return m;
};
D.pred = (m, x0, x1) => { const z = D.logits(m, x0, x1); return z[0] >= z[1] ? (z[0] >= z[2] ? 0 : 2) : (z[1] >= z[2] ? 1 : 2); };
D.err = (m, data) => { let e = 0; for (let i = 0; i < data.n; i++) if (D.pred(m, data.X[2 * i], data.X[2 * i + 1]) !== data.Y[i]) e++; return e / data.n; };
D.grid = (m, g = 36) => { const out = []; for (let r = 0; r < g; r++) for (let c = 0; c < g; c++) out.push(D.pred(m, -1.2 + 2.4 * (c + 0.5) / g, 1.2 - 2.4 * (r + 0.5) / g)); return out; };
/* 固定的设置：老师 32 个隐藏单元、600 个带标签的点；学生只拿到 N 个点；验证集 1500 个点 */
D.SEED = { teacherData: 1, test: 2, transfer: 10, teacherInit: 3, studentInit: 5 };
D.makeTeacher = () => { const data = D.makeData(600, D.SEED.teacherData); const m = D.train(D.init(32, D.SEED.teacherInit), data, { steps: 300 }); return m; };
D.TEST = null;
D.test = () => D.TEST || (D.TEST = D.makeData(1500, D.SEED.test));
D.transfer = (N) => D.makeData(N, D.SEED.transfer + N);
D.softTargets = (teacher, data, T) => { const out = []; for (let i = 0; i < data.n; i++) out.push(D.softmax(D.logits(teacher, data.X[2 * i], data.X[2 * i + 1]), T)); return out; };
D.student = (teacher, N, h, mode, T) => {
  const tr = D.transfer(N), m = D.init(h, D.SEED.studentInit);
  D.train(m, tr, mode === 'soft' ? { target: D.softTargets(teacher, tr, T), T } : {});
  return m;
};
D.WIDTHS = [1, 2, 3, 4, 6, 8, 16, 32];
/*CORE-END*/
