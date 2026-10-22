// 用实验页 04 的同一份代码（charlm.js）、同一份语料、同样的默认设置训练一遍，输出文章里引用的损失曲线与生成文本。
// 运行：node labs-src/pretraining/run_lab.mjs > labs-src/pretraining/lab_run.json（toy.py 会自动调用）
import fs from 'fs';
const src = fs.readFileSync(new URL('./charlm.js', import.meta.url), 'utf8');
const { makeLM, lrAt } = new Function(src + '; return {makeLM, lrAt};')();
const lines = fs.readFileSync(new URL('./corpus.txt', import.meta.url), 'utf8').trim().split('\n');
const text = lines.join(''), valText = lines[lines.length - 1];
const DEF = { bigram: { peak: 0.1 }, mlp: { peak: 0.01 } };
const out = {};
for (const kind of ['bigram', 'mlp']) {
  const lm = makeLM(text, { kind, seed: 7, hidden: 64 });
  const nTrain = text.length - valText.length;
  const tr = lm.ids.slice(0, nTrain), va = lm.ids.slice(nTrain - lm.C);
  const T = 2000, curve = [], samples = {};
  for (let t = 0; t <= T; t++) {
    if (t % 25 === 0) curve.push([t, +lm.evalLoss(tr).toFixed(4), +lm.evalLoss(va).toFixed(4)]);
    if ([0, 50, 100, 200, 500, 2000].includes(t)) samples[t] = lm.sample(30, 1, 3, '我');
    if (t < T) lm.trainStep(32, lrAt(t, T, DEF[kind].peak, 100, 0.1, 'cos'), tr);
  }
  out[kind] = { V: lm.V, nParams: lm.nParams, curve, samples, nTrain, nVal: valText.length };
}
console.log(JSON.stringify(out));
