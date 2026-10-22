// 用实验页里同一份计算代码（CALC-BEGIN…CALC-END）核对 toy.py 算出的文中数字
// 运行：node labs-src/distributed-training/check_lab.mjs
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const here = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(here, '../../public/labs/distributed-training/index.html'), 'utf8');
const code = html.slice(html.indexOf('/* CALC-BEGIN'), html.indexOf('/* CALC-END */'));
const toy = JSON.parse(fs.readFileSync(path.join(here, 'toy.json'), 'utf8'));
const C = new Function(code + '; return {GB, ARCH, paramCount, memPerGPU, zeroStates, ringBytes, ringTime, ringSim, tpRun, pipeSchedule, bubbleFormula, config3d};')();
let bad = 0; const eq = (name, a, b, tol = 1e-9) => { const ok = Math.abs(a - b) <= tol * Math.max(1, Math.abs(b)); if (!ok) bad++; console.log(ok ? 'ok ' : 'BAD', name, a, b); };
eq('P8', C.paramCount(C.ARCH['Llama-3-8B']), toy.P8); eq('P70', C.paramCount(C.ARCH['Llama-3-70B']), toy.P70); eq('P405', C.paramCount(C.ARCH['Llama-3-405B']), toy.P405);
for (let s = 0; s < 4; s++) eq('Z8 stage ' + s, C.memPerGPU({model:'Llama-3-8B',opt:'adam_mixed',s:8192,b:1,act:'flash',zero:s,tp:1,pp:1,dp:8}).states / 1e9, toy.Z8[s]);
for (let s = 0; s < 4; s++) eq('ZeRO paper 7.5B/64 stage ' + s, C.zeroStates(7.5e9, 64, s) / 1e9, toy.ZP[s]);
const m8 = C.memPerGPU({model:'Llama-3-8B',opt:'adam_mixed',s:8192,b:1,act:'flash',zero:0,tp:1,pp:1,dp:1});
eq('act flash total', m8.act, toy.act_layer * 32);
const m8r = C.memPerGPU({model:'Llama-3-8B',opt:'adam_mixed',s:8192,b:1,act:'full',zero:0,tp:1,pp:1,dp:1});
eq('act recompute total', m8r.act, toy.rc_layer * 32 + toy.act_layer);
eq('fp32 adam bytes', C.memPerGPU({model:'Llama-3-8B',opt:'adam_fp32',s:8192,b:1,act:'flash',zero:0,tp:1,pp:1,dp:1}).states, toy.P8 * 16);
eq('dp ring NVLink ms', C.ringTime(toy.P8 * 2, 8, 450e9) * 1e3, toy.dp_nvl_ms); eq('dp ring net ms', C.ringTime(toy.P8 * 2, 8, 50e9) * 1e3, toy.dp_net_ms);
eq('tp ar ms', C.ringTime(8192 * 4096 * 2, 8, 450e9) * 1e3, toy.tp_ar_nvl_ms);
const h = C.ringSim([[1,0,2,1],[2,1,0,3],[0,3,1,2],[1,2,1,0]]); const last = h[h.length - 1].st;
eq('ring all equal sums', last.every(r => r.join() === toy.ring_sums.join()) ? 1 : 0, 1);
const ex = C.tpRun([1,2], [[1,0,-1,-2],[0,1,1,0.5]], [[1,0],[0,1],[1,1],[2,-1]], 2, false);
eq('tp y', ex.sum.join() === toy.tp.Y.join() ? 1 : 0, 1); eq('tp parts', (ex.parts[0].join() === toy.tp.Y0.join() && ex.parts[1].join() === toy.tp.Y1.join()) ? 1 : 0, 1);
const wr = C.tpRun([1,2], [[1,0,-1,-2],[0,1,1,0.5]], [[1,0],[0,1],[1,1],[2,-1]], 2, true);
eq('tp wrong differs', wr.sum.join() !== ex.full.join() ? 1 : 0, 1);
[1, 4, 16].forEach((m, i) => { for (const k of ['gpipe', '1f1b']) eq(`bubble p=4 m=${m} ${k} (排程)`, C.pipeSchedule(4, m, k).bubble, toy.bub[i]); });
for (const p of [2, 5, 8, 16]) for (const m of [1, 3, 7, 32, 64]) for (const k of ['gpipe', '1f1b']) { const r = C.pipeSchedule(p, m, k); if (Math.abs(r.bubble - C.bubbleFormula(p, m)) > 1e-12) { bad++; console.log('BAD sched', p, m, k); } }
console.log('peak in-flight p=4 m=16: gpipe', C.pipeSchedule(4, 16, 'gpipe').peak, '1f1b', C.pipeSchedule(4, 16, '1f1b').peak);
const c = C.config3d({model:'Llama-3-405B',tp:8,cp:1,pp:16,dp:128,seq:8192,bdp:16});
eq('ll gpus', c.n, toy.ll.gpus); eq('ll tokens', c.tokens, toy.ll.tokens); eq('ll states GB', c.states / 1e9, toy.ll.states_gb);
console.log('ll days', c.days.toFixed(1));
const c2 = C.config3d({model:'Llama-3-405B',tp:8,cp:16,pp:16,dp:8,seq:131072,bdp:16}); eq('ll CP gpus', c2.n, 16384); eq('ll CP tokens', c2.tokens, toy.ll.tokens / 8 * 8 * 16 / 16 * 1);
console.log(bad ? `${bad} mismatches` : 'all match'); process.exit(bad ? 1 : 0);
