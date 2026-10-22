// 用实验页同一份 core.js 跑出文章里需要随机抽样的数据（固定种子），写到 mc.json，供 toy.py 画图。
// 运行：node labs-src/diffusion-models/mc.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.join(HERE, 'core.js'), 'utf8').replace('if (typeof module', 'if (false && typeof module');
const DM = new Function(src + ';return DM;')();

const S = DM.linear();
const two = DM.DISTS.two, ov = DM.DISTS.overlap;
const r3 = (v) => Math.round(v * 1000) / 1000;
const pts = (xs) => xs.map((p) => [r3(p[0]), r3(p[1])]);
const out = {};

// 前向：同一批 300 个数据点，在 t = 0, 100, 250, 500, 1000 时的样子（每个点自己的 ε 固定）
{
  const R = DM.rng(1), x0 = DM.sampleData(two, 300, R), E = x0.map(() => [R.n(), R.n()]);
  out.forward = [0, 100, 250, 500, 1000].map((t) => ({ t, xs: pts(x0.map((x, i) => DM.noisy(x, S.abar[t], E[i]))) }));
}
// 反向：300 个点从纯噪声出发，DDPM 1000 步，记下 t = 1000, 750, 500, 250, 0
{
  const hist = DM.sample({ sched: S, steps: 1000, method: 'ddpm', n: 300, seed: 7, pred: (x, ab) => DM.epsOpt(two, x, ab), keep: true });
  out.reverse = [1000, 750, 500, 250, 0].map((t) => ({ t, xs: pts(hist.find((h) => h.t === t).xs) }));
}
// 步数与质量：DDPM / DDIM，400 个点
{
  const steps = [1, 2, 3, 5, 10, 20, 50, 100, 250, 1000];
  out.steps = steps;
  for (const m of ['ddpm', 'ddim']) out['q_' + m] = steps.map((st) => r3(DM.quality(two, DM.sample({ sched: S, steps: st, method: m, n: 400, seed: 7, pred: (x, ab) => DM.epsOpt(two, x, ab) }))));
  out.panels = [1, 5, 50].map((st) => ({ st, xs: pts(DM.sample({ sched: S, steps: st, method: 'ddim', n: 300, seed: 7, pred: (x, ab) => DM.epsOpt(two, x, ab) })) }));
  out.q_true = r3(DM.quality(two, DM.sampleData(two, 4000, DM.rng(3))));
}
// guidance：重叠的两团，条件 = 左边亮（第 0 类），DDIM 50 步，s = 0, 1, 3, 7.5
{
  out.cfg = [0, 1, 3, 7.5].map((s) => {
    const xs = DM.sample({ sched: S, steps: 50, method: 'ddim', n: 300, seed: 7, pred: (x, ab) => DM.epsCFG(ov, x, ab, 0, s) });
    const st = DM.stats(xs);
    return { s, xs: pts(xs), left: r3(xs.filter((x) => x[0] > x[1]).length / xs.length), sd: r3(st.sd), mean: st.mean.map(r3), clip: r3(xs.filter((x) => Math.abs(x[0]) > 1 || Math.abs(x[1]) > 1).length / xs.length) };
  });
  const R = DM.rng(3), d = DM.sampleData(ov, 4000, R, 0);
  out.cfg_true = { left: r3(d.filter((x) => x[0] > x[1]).length / d.length), sd: r3(DM.stats(d).sd) };
}
// 页内小网络：训练 1500 步的损失曲线（每 50 步一个滑动平均）与解析最优的下限
{
  const net = DM.mlp(11), R = DM.rng(5); let ema = 0; const curve = [];
  for (let i = 1; i <= 1500; i++) { ema = 0.95 * ema + 0.05 * net.train(two, S, R); if (i % 50 === 0) curve.push([i, r3(ema / (1 - 0.95 ** i))]); }
  out.train = curve;
  out.floor = r3(DM.optLoss(two, S, 20000, DM.rng(9)));
  out.net_q = r3(DM.quality(two, DM.sample({ sched: S, steps: 50, method: 'ddim', n: 400, seed: 7, pred: (x, ab, t) => net.predict(x, t, S.T) })));
}
// 噪声调度的关键数
out.sched = { abarT: S.abar[1000], half: S.abar.findIndex((a) => a < 0.5), at: [100, 250, 500, 1000].map((t) => [t, S.abar[t]]) };

fs.writeFileSync(path.join(HERE, 'mc.json'), JSON.stringify(out));
console.log('steps', out.steps.join(' '));
console.log('ddpm', out.q_ddpm.join(' ')); console.log('ddim', out.q_ddim.join(' ')); console.log('true', out.q_true);
console.log('cfg', out.cfg.map((c) => [c.s, c.left, c.sd, c.mean, c.clip].join(' ')).join(' | '), 'true', out.cfg_true);
console.log('train', out.train.at(-1), 'floor', out.floor, 'net_q', out.net_q, 'sched', out.sched);
