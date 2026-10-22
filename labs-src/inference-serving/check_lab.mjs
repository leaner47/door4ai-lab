// 在 node 里抽出实验页的 <script id="core">，用同一份代码核对 toy.py 算出的文章数字。
// 运行：node labs-src/inference-serving/check_lab.mjs
import fs from 'fs';
const here = new URL('.', import.meta.url).pathname;
const html = fs.readFileSync(here + '../../public/labs/inference-serving/index.html', 'utf8');
const core = html.match(/<script id="core">([\s\S]*?)<\/script>/)[1];
const toy = JSON.parse(fs.readFileSync(here + 'toy.json', 'utf8'));
const api = new Function(core + '; return {step,bMaxMem,bMaxSla,prefillTime,staticBatch,contBatch,kvAlloc,prefixCalc,expLen,speedup,bestGamma,specMC,specRule,rng,TOY};')();
let bad = 0;
const near = (name, a, b, tol = 1e-6) => { const ok = Math.abs(a - b) <= tol * Math.max(1, Math.abs(b)); if (!ok) bad++; console.log(ok ? 'ok ' : 'BAD', name, a, b); };
for (const [B, v] of Object.entries(toy.tab)) {
  const s = api.step(+B, 1000);
  near(`B=${B} t_ms`, s.t * 1e3, v.t_ms); near(`B=${B} tot`, +B / s.t, v.tot);
}
near('BMAX', api.bMaxMem(1000), toy.BMAX);
near('B_SLA', api.bMaxSla(1000, 16, 50), toy.B_SLA);
const st = api.staticBatch(toy.OUT, 4), cb = api.contBatch(toy.OUT, 4);
near('static T', st.T, toy.ST_T); near('cont T', cb.T, toy.CB_T);
near('static avg', st.spans.reduce((s, x) => s + x.e, 0) / 8, toy.ST_AVG);
near('cont avg', cb.spans.reduce((s, x) => s + x.e, 0) / 8, toy.CB_AVG);
const pc = api.prefixCalc(800, 200, 0);
near('prefix hit', pc.hit, 50); near('prefix users', pc.m1, toy.B_PREFIX); near('no-prefix users', pc.m0, toy.BMAX);
near('pf full', pc.p0 * 1e3, toy.PF_FULL_ms); near('pf own', pc.p1 * 1e3, toy.PF_OWN_ms);
near('E4', api.expLen(0.8, 4), toy.E4); near('SP4', api.speedup(0.8, 4, 0.05), toy.SP4); near('best g', api.bestGamma(0.8, 0.05), toy.BEST_G);
const mc = api.specMC(0.8, 4, 200000, api.rng(1)); near('E4 MC (tol 1%)', mc, toy.E4, 0.01);
const rr = api.specRule(api.TOY.P, api.TOY.Q, 200000, api.rng(2));
near('rule acc (tol 1%)', rr.acc, 0.8, 0.01); rr.freq.forEach((f, i) => near(`rule freq ${i} (tol 0.005)`, f, api.TOY.P[i], 0.005 / Math.max(1, api.TOY.P[i])));
const kv = api.kvAlloc([5, 9, 3], 36, 12, 4);
near('toy res waste', 1 - kv.resUsed / kv.resAlloc, 19 / 36); near('toy pg alloc', kv.pgAlloc, 24);
const sp = (B) => { const td = api.step(B, 1000).t, tv = api.step(B, 1000, 5).t; return api.expLen(0.8, 4) * td / (tv + 4 * 0.05 * td); };
near('spec speedup at B_SLA', sp(toy.B_SLA), toy.SPBS);
console.log(bad ? `${bad} 项不一致` : '全部一致');
process.exit(bad ? 1 : 0);
