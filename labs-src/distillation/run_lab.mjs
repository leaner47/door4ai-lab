// 从生成的实验页里抽出计算核心（/*CORE-BEGIN*/ … /*CORE-END*/），在 node 里跑同一份代码，
// 输出文章要用的训练结果与核对数字到 labs-src/distillation/lab_results.json。
// 运行：node labs-src/distillation/run_lab.mjs（先运行 build.py）
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(HERE, '../../public/labs/distillation/index.html'), 'utf8');
const core = page.slice(page.indexOf('/*CORE-BEGIN*/'), page.indexOf('/*CORE-END*/'));
const D = new Function(core + ';return D;')();
const t0 = Date.now();
const teacher = D.makeTeacher(), test = D.test();
const out = { teacherErr: D.err(teacher, test), teacherGrid: D.grid(teacher), runs: {}, widths: {} };
for (const N of [30, 60, 120]) for (const T of [1, 2, 4, 8]) {
  const hard = D.student(teacher, N, 16, 'hard'), soft = D.student(teacher, N, 16, 'soft', T);
  out.runs[N + '_' + T] = { eh: D.err(hard, test), es: D.err(soft, test) };
  if (N === 60 && T === 4) { out.gridHard = D.grid(hard); out.gridSoft = D.grid(soft); const p = D.transfer(60); out.pts = { X: Array.from(p.X), Y: Array.from(p.Y) }; }
}
for (const h of D.WIDTHS) { out.widths[h] = { eh: D.err(D.student(teacher, 60, h, 'hard'), test), es: D.err(D.student(teacher, 60, h, 'soft', 4), test) }; }
// 实验 02 的核对数字
out.loss = {};
for (const [name, z] of [['start', D.Z], ['catonly', [6, -2, -2, -2]], ['same', D.V]]) {
  const r = D.loss(D.V, z, 0, 4, 0.5, true); out.loss[name] = { ce: r.ce, kl: r.kl, total: r.total, ratio: D.norm(r.gSoft.map(g => 0.5 * 16 * g)) / D.norm(r.gHard.map(g => 0.5 * g)) };
}
const gn = (T) => D.norm(D.softmax(D.Z, T).map((q, k) => (q - D.softmax(D.V, T)[k]) / T));
out.gnorm = { 4: gn(4), 20: gn(20), shrink4to20: gn(4) / gn(20) };
out.ms = Date.now() - t0;
fs.writeFileSync(path.join(HERE, 'lab_results.json'), JSON.stringify(out));
const { teacherGrid, gridHard, gridSoft, pts, ...brief } = out;
console.log(JSON.stringify(brief, null, 1));
