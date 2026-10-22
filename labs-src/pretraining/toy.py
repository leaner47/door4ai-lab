"""预训练一讲的贯穿算例：文章分镜图、文中数字与实验页共用这组数。
运行：python3 labs-src/pretraining/toy.py
  → 调 node 跑 run_lab.mjs（实验 04 的同一份模型代码）得到 lab_run.json
  → 生成 src/content/blog/pretraining.md（把 article.src.md 里的 {{figN}} 与 {{n:名字}} 填好）
  → 写出 toy.json（实验页开头的 TOY 常量就是它）
"""
import math, json, pathlib, re, subprocess
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def softmax(z):
    m = max(z); e = [math.exp(v - m) for v in z]; s = sum(e); return [v / s for v in e]

# ———— 贯穿算例：7 个 token 的词表，一句「我爱吃米饭。」 ————
VOC = ['我', '爱', '吃', '米', '饭', '粥', '。']
S1, S2 = '我爱吃米饭。', '我爱吃米粥。'
# bigram 模型：参数就是一张 7 × 7 的分数表，第 a 行是「上一个字是 a 时，下一个字的 7 个分数」
Z0 = {r: [0.0] * 7 for r in VOC}
Z0['我'][1] = 1.0; Z0['爱'][2] = 2.0; Z0['吃'][3] = 0.5
Z0['米'][4] = 2.0; Z0['米'][5] = 1.5; Z0['米'][6] = 0.5
Z0['饭'][6] = 2.5
ix = {c: i for i, c in enumerate(VOC)}
pairs = lambda s: list(zip(s, s[1:]))
def probs(Z, a): return softmax(Z[a])
def losses(Z, sents): return [-math.log(probs(Z, a)[ix[b]]) for s in sents for a, b in pairs(s)]

# 第二部分：一句话里 5 个位置的概率与损失
P5 = [probs(Z0, a)[ix[b]] for a, b in pairs(S1)]
L5 = [-math.log(p) for p in P5]
PROD = math.prod(P5)
MEAN5 = sum(L5) / 5
PPL5 = math.exp(MEAN5)
PM = probs(Z0, '米')                       # 「米」之后 7 个候选
EM = [math.exp(v) for v in Z0['米']]; SUMM = sum(EM)
# 数值检查梯度：把 z[米][饭] 加 0.01
d = 0.01
Zp = {r: v[:] for r, v in Z0.items()}; Zp['米'][4] += d
Lfan = -math.log(PM[4]); Lfan_p = -math.log(probs(Zp, '米')[4])

# 第三部分：一个训练步（batch = 两句话，10 个样本），SGD 学习率 4
ETA = 4.0
B = [S1, S2]; NB = sum(len(s) - 1 for s in B)
LB = losses(Z0, B); LOSSB = sum(LB) / NB
G = {r: [0.0] * 7 for r in VOC}
for s in B:
    for a, b in pairs(s):
        p = probs(Z0, a)
        for k in range(7): G[a][k] += (p[k] - (1 if VOC[k] == b else 0)) / NB
Z1 = {r: [Z0[r][k] - ETA * G[r][k] for k in range(7)] for r in VOC}
LB1 = losses(Z1, B); LOSSB1 = sum(LB1) / NB
PM1 = probs(Z1, '米')
traj = []; Z = {r: v[:] for r, v in Z0.items()}
for st in range(81):
    L = losses(Z, B); traj.append(sum(L) / NB)
    g = {r: [0.0] * 7 for r in VOC}
    for s in B:
        for a, b in pairs(s):
            p = probs(Z, a)
            for k in range(7): g[a][k] += (p[k] - (1 if VOC[k] == b else 0)) / NB
    Z = {r: [Z[r][k] - ETA * g[r][k] for k in range(7)] for r in VOC}
FLOOR = 2 * math.log(2) / NB
PM80 = probs(Z, '米')

# 第四部分：去重。两段只差两个字的文字，2 字片段的 Jaccard 相似度
DA, DB = '今天天气很好我们去公园', '今天天气很好我们去看书'
sh = lambda s: [s[i:i + 2] for i in range(len(s) - 1)]
SA, SB = sh(DA), sh(DB)
INTER = [x for x in SA if x in SB]; UNION = list(dict.fromkeys(SA + SB))
JAC = len(INTER) / len(UNION)
cand = lambda j, r=8, b=14: 1 - (1 - j ** r) ** b
# GPT-3 训练数据（Brown et al. 2020 表 2.2）
GPT3 = [('Common Crawl（过滤后）', 410, 60, 0.44), ('WebText2', 19, 22, 2.9), ('Books1', 12, 8, 1.9), ('Books2', 55, 8, 0.43), ('Wikipedia', 3, 3, 3.4)]
GTOT = sum(r[1] for r in GPT3)
LLAMA3 = [('通用知识', 50), ('数学与推理', 25), ('代码', 17), ('多语言', 8)]

# 第五部分：学习率。Llama 3 405B：峰值 8e-5，线性预热 8000 步，余弦衰减到 8e-7，共 1,200,000 步
PEAK, WARM, TOTAL, LOW = 8e-5, 8000, 1_200_000, 8e-7
def lr(t):
    if t < WARM: return PEAK * t / WARM
    q = (t - WARM) / (TOTAL - WARM); return LOW + 0.5 * (PEAK - LOW) * (1 + math.cos(math.pi * q))
jit = lambda eta, a=1.0, s=1.0: eta * s * s / (a * (2 - eta * a))

# 实验 04 的真实训练（node 跑同一份代码）
run = json.loads(subprocess.check_output(['node', str(HERE / 'run_lab.mjs')], text=True))
(HERE / 'lab_run.json').write_text(json.dumps(run, ensure_ascii=False))
mlp, big = run['mlp'], run['bigram']
vmin = min(mlp['curve'], key=lambda r: r[2])
bvmin = min(big['curve'], key=lambda r: r[2])

# 实验页由 lab.src.html 生成：填入语料、模型代码（charlm.js 原样）与 TOY 常量
lab = ROOT / 'public/labs/pretraining/index.html'
lab.parent.mkdir(parents=True, exist_ok=True)
_toy_for_lab = {'voc': VOC, 's1': S1, 's2': S2, 'z0': Z0, 'eta': ETA, 'peak': PEAK, 'warm': WARM, 'total': TOTAL, 'low': LOW, 'gpt3': GPT3, 'llama3': LLAMA3}
_h = (HERE / 'lab.src.html').read_text(encoding='utf-8')
_h = _h.replace('__CORPUS__', (HERE / 'corpus.txt').read_text(encoding='utf-8').strip()).replace('__CHARLM__', (HERE / 'charlm.js').read_text(encoding='utf-8').strip()).replace('__TOY__', json.dumps(_toy_for_lab, ensure_ascii=False))
_h = _h.replace('<!doctype html>\n', '<!doctype html>\n<!-- 本页由 labs-src/pretraining/toy.py 从 lab.src.html 生成。改实验请改 lab.src.html（模型代码改 charlm.js、语料改 corpus.txt）再运行脚本。 -->\n', 1)
lab.write_text(_h, encoding='utf-8')
if lab.exists():
    h = lab.read_text(encoding='utf-8')
    m = re.search(r'<script id="charlm">\n(.*?)</script>', h, re.S)
    assert m and m.group(1).strip() == (HERE / 'charlm.js').read_text(encoding='utf-8').strip(), '实验页 charlm 与 charlm.js 不一致'
    corpus = re.search(r'<script id="corpus" type="text/plain">\n(.*?)</script>', h, re.S)
    assert corpus and corpus.group(1).strip() == (HERE / 'corpus.txt').read_text(encoding='utf-8').strip(), '实验页语料与 corpus.txt 不一致'

# ———— 文中数字 ————
f3 = lambda v: f'{v:.3f}'
pt = lambda v: f'{v*100:.1f}%'
pc = lambda v: f'{v*100:.1f}\\%'
N = {
    'em_fan': f3(EM[4]), 'em_zhou': f3(EM[5]), 'em_ju': f3(EM[6]), 'summ': f3(SUMM),
    'pm_fan': f3(PM[4]), 'pm_zhou': f3(PM[5]), 'pm_ju': f3(PM[6]), 'pm_other': f3(PM[0]),
    'pm_fanpc': pt(PM[4]),
    'p1': f3(P5[0]), 'p2': f3(P5[1]), 'p3': f3(P5[2]), 'p4': f3(P5[3]), 'p5': f3(P5[4]),
    'l1': f3(L5[0]), 'l2': f3(L5[1]), 'l3': f3(L5[2]), 'l4': f3(L5[3]), 'l5': f3(L5[4]),
    'prod': f'{PROD:.4f}', 'sumlog': f3(sum(math.log(p) for p in P5)), 'suml': f3(sum(L5)),
    'mean5': f3(MEAN5), 'ppl5': f'{PPL5:.2f}', 'gm5': f3(1 / PPL5), 'lnprod': f3(math.log(PROD)),
    'lfan': f3(Lfan), 'lfanp': f'{Lfan_p:.4f}', 'lfan4': f'{Lfan:.4f}', 'dl': f'{Lfan - Lfan_p:.4f}', 'gfan': f3(1 - PM[4]), 'gfan01': f'{(1 - PM[4]) * d:.4f}',
    'nb': str(NB), 'lossb': f3(LOSSB), 'lossb1': f3(LOSSB1), 'ln7': f3(math.log(7)),
    'b_zhou5': f3(probs(Z0, '粥')[ix['。']]), 'pzhou': f3(PM[5]),
    'g_fan': f3(G['米'][4]), 'g_zhou': f3(G['米'][5]), 'g_ju': f3(G['米'][6]), 'g_oth': f3(G['米'][0]),
    'g_fan_m': f3(-G['米'][4]), 'g_zhou_m': f3(-G['米'][5]),
    'z1_fan': f3(Z1['米'][4]), 'z1_zhou': f3(Z1['米'][5]), 'z1_ju': f3(Z1['米'][6]), 'z1_oth': f3(Z1['米'][0]),
    'pm1_fan': f3(PM1[4]), 'pm1_zhou': f3(PM1[5]), 'pm1_zhoupc': pt(PM1[5]), 'pm_zhoupc': pt(PM[5]), 'pm1_fanpc': pt(PM1[4]),
    'eta_gfan': f3(ETA * G['米'][4]), 'eta_gzhou': f3(ETA * G['米'][5]), 'eta_gju': f3(ETA * G['米'][6]), 'eta_goth': f3(ETA * G['米'][0]),
    'tr10': f3(traj[10]), 'tr80': f3(traj[80]), 'floor': f3(FLOOR), 'pfloor': f'{math.exp(FLOOR):.3f}', 'ln2': f3(math.log(2)),
    'pm80_fanpc': pt(PM80[4]), 'pm80_zhoupc': pt(PM80[5]),
    'na': str(len(SA)), 'ni': str(len(INTER)), 'nu': str(len(UNION)), 'jac': f3(JAC),
    'j8': f'{JAC**8:.4f}', 'j8c': f'{1 - JAC**8:.4f}', 'j8c14': f'{(1 - JAC**8)**14:.3f}', 'candj': pt(cand(JAC)),
    'cand75': pt(cand(0.75)), 'cand90': pt(cand(0.9)), 'cand50': pt(cand(0.5)), 'p75_8': f'{0.75**8:.4f}',
    'gtot': str(GTOT),
    'warmpc': f'{WARM / TOTAL * 100:.2f}%', 'lr_half': f'{lr(TOTAL / 2 + WARM / 2) :.2e}',
    'jit01': f'{jit(0.1):.4f}', 'jit001': f'{jit(0.01):.4f}', 'jitratio': f'{jit(0.1) / jit(0.01):.1f}',
    'jit01sd': f'{math.sqrt(jit(0.1)):.3f}', 'jit001sd': f'{math.sqrt(jit(0.01)):.3f}',
    'mlp_par': f"{mlp['nParams']:,}", 'big_par': f"{big['nParams']:,}", 'labV': str(mlp['V']), 'lnV': f"{math.log(mlp['V']):.2f}",
    'mlp_tr_end': f"{mlp['curve'][-1][1]:.2f}", 'mlp_va_end': f"{mlp['curve'][-1][2]:.2f}",
    'mlp_va_min': f"{vmin[2]:.2f}", 'mlp_va_min_t': str(vmin[0]),
    'big_tr_end': f"{big['curve'][-1][1]:.2f}", 'big_va_min': f"{bvmin[2]:.2f}", 'big_va_min_t': str(bvmin[0]),
    'ntrain': str(mlp['nTrain']), 'nval': str(mlp['nVal']),
}
for a, b in [(0, 'gp_cc'), (1, 'gp_wt'), (2, 'gp_b1'), (3, 'gp_b2'), (4, 'gp_wk')]:
    N[b] = f'{GPT3[a][1] / GTOT * 100:.1f}%'
rows = []
for t in ['0', '50', '100', '200', '500', '2000']:
    rows.append(f"| {t} | `{big['samples'][t]}` | `{mlp['samples'][t]}` |")
N['sampletable'] = '\n'.join(rows)

# ———— SVG 小工具：颜色只用 CSS 变量 ————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None, raw=False):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{s if raw else esc(s)}</text>'
def it(s): return f'<tspan font-style="italic">{s}</tspan>'
def arrow(x1, y1, x2, y2, col, w=2.5):
    ang = math.atan2(y2-y1, x2-x1); L = 10; a = 0.42
    bx, by = x2 - L*math.cos(ang), y2 - L*math.sin(ang)
    p1 = (x2 - L*math.cos(ang-a), y2 - L*math.sin(ang-a)); p2 = (x2 - L*math.cos(ang+a), y2 - L*math.sin(ang+a))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>')
def rect(x, y, w, h, col, rx=4): return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,1):.1f}" height="{h:.1f}" rx="{rx}" {C(col)}/>'
def box(x, y, w, h, col, sw=1.5, rx=6, dash=None): return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" {S_(col, sw, dash)}/>'
def line(x1, y1, x2, y2, col, w=1.5, dash=None): return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {S_(col, w, dash)}/>'
def poly(pts, col, w=2.5, dash=None): return '<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + f'" {S_(col, w, dash)}/>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')

figs = {}
# 图 1：一句话拆成 5 个训练样本
b = ''; cw = 34
for i in range(1, 6):
    y = 8 + (i - 1) * 42
    b += text(20, y + 22, f'样本 {i}', 'muted', 15)
    for j in range(6):
        x = 90 + j * (cw + 6)
        if j < i:
            b += box(x, y, cw, 32, 'line'); b += text(x + cw/2, y + 22, S1[j], 'fg', 17, 'middle')
        elif j == i:
            b += box(x, y, cw, 32, 'accent', 2.4); b += text(x + cw/2, y + 22, S1[j], 'accent', 17, 'middle', weight=600)
    xe = 90 + i * (cw + 6) + cw + 12
    b += text(xe, y + 22, f'猜第 {i+1} 个', 'muted', 15)
figs['fig1'] = fig(480, 8 + 5*42, '一句话拆成五个训练样本', b,
                   '图 1　「我爱吃米饭。」6 个 token，拆出 5 个训练样本。灰框是给模型看的前文，蓝框是要它猜的下一个 token。')

# 图 2：因果遮罩
b = ''; cs = 40; x0, y0 = 120, 54
for j, c in enumerate(S1): b += text(x0 + j*cs + cs/2, y0 - 12, c, 'muted', 16, 'middle')
b += text(x0 + 3*cs, 18, '能看到的字', 'muted', 15, 'middle')
for i, c in enumerate(S1):
    y = y0 + i*cs
    b += text(x0 - 12, y + cs/2 + 6, f'第 {i+1} 位 {c}', 'fg', 15, 'end')
    for j in range(6):
        x = x0 + j*cs
        if j <= i: b += rect(x + 3, y + 3, cs - 6, cs - 6, 'accent-soft', 4) + box(x + 3, y + 3, cs - 6, cs - 6, 'accent', 1.2, 4)
        else: b += box(x + 3, y + 3, cs - 6, cs - 6, 'line', 1.2, 4, '3 3')
    tgt = S1[i+1] if i < 5 else '—'
    b += text(x0 + 6*cs + 14, y + cs/2 + 6, f'→ 猜 {tgt}', 'accent' if i < 5 else 'muted', 15)
figs['fig2'] = fig(480, y0 + 6*cs + 6, '因果遮罩：每个位置只能看到自己和前面的字', b,
                   '图 2　一次前向同时算出 6 个位置。第 <i>i</i> 行是第 <i>i</i> 个位置能看到的字：实心格能看到，虚线格被遮住。每一行右边是它要猜的字；最后一位后面没有字，不算损失。')

# 图 3：「米」之后 7 个候选的概率
b = ''
for i, c in enumerate(VOC):
    y = 8 + i * 32
    b += text(40, y + 18, c, 'fg', 16, 'end')
    wv = 300 * PM[i] / max(PM); col = 'accent' if c == '饭' else 'line'
    b += rect(52, y + 2, wv, 22, col)
    b += text(52 + wv + 8, y + 19, f3(PM[i]), 'accent' if c == '饭' else 'muted', 15)
figs['fig3'] = fig(480, 8 + 7*32, '读完我爱吃米之后七个候选的概率', b,
                   f'图 3　读完「我爱吃米」，模型给 7 个候选的概率。正确答案「饭」是 {f3(PM[4])}。')

# 图 4：−ln p 曲线，5 个位置的点
ox, oy, W_, H_ = 50, 230, 400, 200
def X(p): return ox + p * W_
def Y(l): return oy - l / 3.5 * H_
pts = [(X(p), Y(-math.log(p))) for p in [0.03 + i * 0.97 / 200 for i in range(201)]]
b = line(ox, oy, ox + W_ + 10, oy, 'line') + line(ox, oy, ox, oy - H_ - 10, 'line')
for v in (0, 0.5, 1): b += text(X(v), oy + 20, f'{v:g}', 'muted', 14, 'middle')
for v in (1, 2, 3): b += text(ox - 8, Y(v) + 5, str(v), 'muted', 14, 'end')
b += text(ox + W_/2, oy + 42, '正确 token 的概率 ' + it('p'), 'muted', 15, 'middle', raw=True)
b += text(ox + 8, oy - H_ - 2, '损失 −ln ' + it('p'), 'muted', 15, raw=True)
b += poly(pts, 'warn', 2.5)
lab_off = [(8, -8, 'start'), (6, -12, 'start'), (8, -8, 'start'), (-8, 18, 'end'), (8, 18, 'start')]
for k, (p, l) in enumerate(zip(P5, L5)):
    b += f'<circle cx="{X(p):.1f}" cy="{Y(l):.1f}" r="5.5" {C("accent")}/>'
    dx, dy, an = lab_off[k]
    b += text(X(p) + dx, Y(l) + dy, f'{S1[k+1]} {l:.2f}', 'accent', 14, an)
figs['fig4'] = fig(480, 280, '负对数曲线和五个位置', b,
                   '图 4　橙色曲线是 −ln <i>p</i>：概率越接近 1，损失越接近 0；概率越接近 0，损失越大，而且涨得越来越快。蓝点是「我爱吃米饭。」5 个位置，标的是要猜的字和它的损失。')

# 图 5：逐位置损失柱 + 平均线
b = ''; base = 190; mxl = max(L5); bw = 54; gap = 26; x0 = 70
for k, l in enumerate(L5):
    x = x0 + k * (bw + gap); hgt = 150 * l / mxl
    b += rect(x, base - hgt, bw, hgt, 'warn', 3)
    b += text(x + bw/2, base - hgt - 6, f'{l:.3f}', 'warn', 14, 'middle')
    b += text(x + bw/2, base + 20, f'→{S1[k+1]}', 'muted', 15, 'middle')
ym = base - 150 * MEAN5 / mxl
b += line(x0 - 10, ym, x0 + 5*(bw+gap) - gap + 10, ym, 'fg', 1.5, '6 4')
b += text(x0 - 14, ym + 5, f'平均 {MEAN5:.3f}', 'fg', 14, 'end')
figs['fig5'] = fig(480, base + 30, '五个位置的损失和平均损失', b,
                   f'图 5　每个位置的损失 −ln <i>p</i>，虚线是它们的平均 {MEAN5:.3f}，这就是这句话的交叉熵损失。')

# 图 6：一个训练步的流水线
st = [('取一批文本', '切成 token', 'line'), ('前向', '每个位置的概率', 'accent'), ('交叉熵', '−ln p 取平均', 'warn'),
      ('反向传播', '每个参数的梯度', 'warn'), ('优化器更新', '参数往下坡走一步', 'ok')]
b = ''; bw, bh = 300, 44; x = 60
for i, (t1, t2, col) in enumerate(st):
    y = 10 + i * 62
    b += box(x, y, bw, bh, col, 2.2 if col != 'line' else 1.5, 8)
    b += text(x + 16, y + 28, t1, col if col != 'line' else 'fg', 17, weight=600) + text(x + bw - 14, y + 28, t2, 'muted', 15, 'end')
    if i < 4: b += arrow(x + bw/2, y + bh + 2, x + bw/2, y + 62 - 2, 'muted', 1.6)
yb = 10 + 4*62 + bh/2; yt = 10 + bh/2
b += f'<path d="M{x+bw+4} {yb} H{x+bw+40} V{yt} H{x+bw+14}" {S_("muted", 1.6, "5 4")}/>'
b += f'<path d="M{x+bw+4} {yt} l10 -6 v12 z" {C("muted")}/>'
b += text(x + bw + 48, (yb + yt)/2 + 5, '下一批', 'muted', 15)
figs['fig6'] = fig(480, 10 + 5*62 - 10, '一个训练步的五个环节', b,
                   '图 6　一个训练步。前向（注意力、MLP 几讲）、交叉熵（本讲）、反向传播、优化器（梯度下降一讲）首尾相接，换一批数据再来一遍。')

# 图 7：「米」那一行，走一步之前与之后
b = text(80, 22, '走一步之前', 'muted', 15) + text(290, 22, '走一步之后', 'muted', 15)
mx = max(max(PM), max(PM1))
for i, c in enumerate(VOC):
    y = 36 + i * 32
    b += text(66, y + 17, c, 'fg', 16, 'end')
    for x0, P in ((80, PM), (290, PM1)):
        wv = 118 * P[i] / mx; col = 'accent' if c in ('饭', '粥') else 'line'
        b += rect(x0, y, wv, 22, col)
        b += text(x0 + wv + 6, y + 17, f3(P[i]), 'accent' if c in ('饭', '粥') else 'muted', 14)
figs['fig7'] = fig(480, 36 + 7*32, '米那一行在一个训练步之前与之后', b,
                   f'图 7　bigram 表里「米」那一行的 7 个概率。这一批里「米」后面一次是「饭」、一次是「粥」：「粥」明显升了，「饭」几乎没动，其余 5 个都降。')

# 图 8：80 步的损失曲线和下限
ox, oy, W_, H_ = 60, 210, 390, 180
X = lambda t: ox + t / 80 * W_
Y = lambda l: oy - l / 1.2 * H_
b = line(ox, oy, ox + W_ + 8, oy, 'line') + line(ox, oy, ox, oy - H_ - 8, 'line')
for v in (0, 20, 40, 60, 80): b += text(X(v), oy + 20, str(v), 'muted', 14, 'middle')
for v in (0.4, 0.8, 1.2): b += text(ox - 8, Y(v) + 5, f'{v:g}', 'muted', 14, 'end')
b += text(ox + W_/2, oy + 42, '训练步数', 'muted', 15, 'middle') + text(ox + 8, oy - H_ - 2, '平均损失', 'muted', 15)
b += line(ox, Y(FLOOR), ox + W_, Y(FLOOR), 'ok', 1.5, '6 4') + text(ox + W_, Y(FLOOR) - 8, f'下限 {FLOOR:.3f}', 'ok', 14, 'end')
b += poly([(X(t), Y(l)) for t, l in enumerate(traj)], 'warn', 2.5)
b += f'<circle cx="{X(0):.1f}" cy="{Y(traj[0]):.1f}" r="5" {C("warn")}/>' + text(X(0) + 10, Y(traj[0]) + 4, f'{traj[0]:.3f}', 'warn', 14)
b += f'<circle cx="{X(1):.1f}" cy="{Y(traj[1]):.1f}" r="4" {C("warn")}/>' + text(X(1) + 10, Y(traj[1]) + 10, f'第 1 步后 {traj[1]:.3f}', 'warn', 14)
figs['fig8'] = fig(480, 258, '在两句话上反复训练的损失曲线', b,
                   f'图 8　在这两句话上一步一步训练，平均损失从 {traj[0]:.3f} 往下走，但不会到 0：它停在绿色虚线 {FLOOR:.3f} 附近。')

# 图 9：两段文字的 2 字片段
b = ''
def shrow(y, s, other, lab):
    out = text(8, y + 22, lab, 'muted', 15); x = 30
    for g in sh(s):
        shared = g in other; w = 44
        out += box(x, y, w, 32, 'accent' if shared else 'warn', 2 if shared else 2.2)
        out += text(x + w/2, y + 22, g, 'accent' if shared else 'warn', 15, 'middle')
        x += w + 0
    return out
b += shrow(8, DA, SB, 'A') + shrow(56, DB, SA, 'B')
figs['fig9'] = fig(480, 98, '两段文字切成两个字一段的片段', b,
                   f'图 9　两段文字各切成 {len(SA)} 个「两字片段」。蓝框两边都有（{len(INTER)} 个），橙框只有一边有（各 2 个）。')

# 图 10：MinHash 分桶之后，被判为重复的概率随相似度变化
ox, oy, W_, H_ = 60, 200, 390, 170
X = lambda j: ox + j * W_; Y = lambda p: oy - p * H_
b = line(ox, oy, ox + W_ + 8, oy, 'line') + line(ox, oy, ox, oy - H_ - 8, 'line')
for v in (0, 0.25, 0.5, 0.75, 1): b += text(X(v), oy + 20, f'{v:g}', 'muted', 14, 'middle')
for v in (0.5, 1): b += text(ox - 8, Y(v) + 5, f'{v*100:.0f}%', 'muted', 14, 'end')
b += text(ox + W_ + 4, oy - 8, 'Jaccard 相似度', 'muted', 15, 'end') + text(ox + 8, oy - H_ - 2, '被当成重复的概率', 'muted', 15)
b += poly([(X(j / 200), Y(cand(j / 200))) for j in range(201)], 'warn', 2.5)
b += line(X(0.75), oy, X(0.75), Y(cand(0.75)), 'muted', 1.2, '4 4')
b += f'<circle cx="{X(JAC):.1f}" cy="{Y(cand(JAC)):.1f}" r="5.5" {C("accent")}/>' + text(X(JAC) - 10, Y(cand(JAC)) + 4, f'A 和 B：{cand(JAC)*100:.1f}%', 'accent', 14, 'end')
b += f'<circle cx="{X(0.75):.1f}" cy="{Y(cand(0.75)):.1f}" r="4.5" {C("fg")}/>' + text(X(0.75) + 10, Y(cand(0.75)) + 14, f'0.75：{cand(0.75)*100:.1f}%', 'fg', 14)
figs['fig10'] = fig(480, 220, 'MinHash 分桶后被判为重复的概率曲线', b,
                    '图 10　FineWeb 的设置（112 个哈希，分成 14 组、每组 8 个）下，两篇文档被当成重复的概率。相似度过了 0.75 左右，曲线迅速升到接近 100%。')

# 图 11：GPT-3 训练数据：按数据量的份额 vs 实际抽样的份额
b = text(190, 22, '占全部数据量', 'muted', 15, 'middle') + text(380, 22, '训练时抽样的比例', 'muted', 15, 'middle')
for i, (nm, tok, wt, ep) in enumerate(GPT3):
    y = 36 + i * 40; sz = tok / GTOT * 100
    b += text(118, y + 18, nm.replace('（过滤后）', ''), 'fg', 15, 'end')
    b += rect(130, y + 2, 1.5 * sz, 22, 'line') + text(130 + 1.5 * sz + 6, y + 19, f'{sz:.1f}%', 'muted', 14)
    b += rect(330, y + 2, 1.5 * wt, 22, 'accent') + text(330 + 1.5 * wt + 6, y + 19, f'{wt}%', 'accent', 14)
figs['fig11'] = fig(480, 36 + 5*40 + 4, 'GPT-3 各数据源的数据量份额与抽样比例', b,
                    '图 11　GPT-3 的五个数据源。灰条是各自占全部 4990 亿 token 的份额，蓝条是训练时实际从它抽样的比例。书和维基百科被多抽，网页被少抽。')

# 图 12：学习率曲线，全程 + 前 2 万步
def lrpanel(x0, y0, w, h, t0, t1, ticks, title):
    X = lambda t: x0 + (t - t0) / (t1 - t0) * w; Y = lambda v: y0 + h - v / PEAK * h
    out = line(x0, y0 + h, x0 + w + 6, y0 + h, 'line') + line(x0, y0 + h, x0, y0 - 6, 'line')
    for t, lab in ticks: out += text(X(t), y0 + h + 18, lab, 'muted', 13, 'middle')
    out += text(x0 + w/2, y0 - 12, title, 'muted', 14, 'middle')
    out += poly([(X(t0 + (t1 - t0) * i / 300), Y(lr(t0 + (t1 - t0) * i / 300))) for i in range(301)], 'accent', 2.5)
    return out, X, Y
b1, X1, Y1 = lrpanel(56, 34, 190, 150, 0, TOTAL, [(0, '0'), (600000, '60 万'), (1200000, '120 万')], '全程 120 万步')
b2, X2, Y2 = lrpanel(282, 34, 180, 150, 0, 20000, [(0, '0'), (8000, '8000'), (20000, '2 万')], '前 2 万步放大')
b = b1 + b2
b += text(50, Y1(PEAK) + 5, '8×10⁻⁵', 'muted', 13, 'end') + text(50, Y1(0) + 5, '0', 'muted', 13, 'end')
b += line(X2(8000), Y2(0), X2(8000), Y2(PEAK), 'muted', 1.2, '4 4')
b += text(X2(4000), Y2(PEAK * 0.45), '预热', 'warn', 14, 'middle')
b += text(X1(700000), Y1(PEAK * 0.62), '余弦衰减', 'warn', 14, 'start')
figs['fig12'] = fig(480, 210, 'Llama 3 405B 的学习率曲线：全程与前两万步', b,
                    '图 12　Llama 3 405B 的学习率：前 8000 步从 0 线性升到 8×10⁻⁵，之后沿余弦曲线降到 8×10⁻⁷。左边看全程，预热只占最开始的 0.67%，几乎看不见；右边把前 2 万步放大。')

# 图 13：实验 04 的真实损失曲线（小 MLP）
ox, oy, W_, H_ = 56, 210, 395, 180
X = lambda t: ox + t / 2000 * W_; Y = lambda l: oy - l / 6 * H_
b = line(ox, oy, ox + W_ + 8, oy, 'line') + line(ox, oy, ox, oy - H_ - 8, 'line')
for v in (0, 500, 1000, 1500, 2000): b += text(X(v), oy + 20, str(v), 'muted', 14, 'middle')
for v in (2, 4, 6): b += text(ox - 8, Y(v) + 5, str(v), 'muted', 14, 'end')
b += text(ox + W_/2, oy + 42, '训练步数', 'muted', 15, 'middle')
b += poly([(X(t), Y(a)) for t, a, _ in mlp['curve']], 'warn', 2.5)
b += poly([(X(t), Y(v)) for t, _, v in mlp['curve']], 'accent', 2.5, '6 4')
b += text(X(2000), Y(mlp['curve'][-1][1]) - 10, f"训练 {mlp['curve'][-1][1]:.2f}", 'warn', 14, 'end')
b += text(X(2000), Y(mlp['curve'][-1][2]) - 10, f"验证 {mlp['curve'][-1][2]:.2f}", 'accent', 14, 'end')
b += f'<circle cx="{X(vmin[0]):.1f}" cy="{Y(vmin[2]):.1f}" r="5" {C("accent")}/>' + text(X(vmin[0]) + 10, Y(vmin[2]) + 20, f'最低 {vmin[2]:.2f}（第 {vmin[0]} 步）', 'accent', 14)
b += text(X(0) + 10, Y(mlp['curve'][0][1]) + 4, f"开始 {mlp['curve'][0][1]:.2f}", 'muted', 14)
figs['fig13'] = fig(480, 258, '页内小模型的训练损失和验证损失', b,
                    '图 13　实验 04 默认设置下真实训练的结果。橙色实线是训练文字上的平均损失，蓝色虚线是留出来没给它看的一句话上的平均损失。')

# ———— 输出 ————
toy = {'voc': VOC, 's1': S1, 's2': S2, 'z0': Z0, 'eta': ETA, 'peak': PEAK, 'warm': WARM, 'total': TOTAL, 'low': LOW,
       'gpt3': GPT3, 'llama3': LLAMA3}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False))
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', v)
left = re.findall(r'\{\{[a-z0-9:_]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/pretraining.md').write_text(src, encoding='utf-8')
print(json.dumps({k: v for k, v in N.items() if k != 'sampletable'}, ensure_ascii=False))
print(N['sampletable'])
print('traj', [round(traj[i], 3) for i in (0, 1, 2, 5, 10, 20, 40, 80)])
