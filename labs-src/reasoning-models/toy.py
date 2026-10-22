"""推理模型一讲的贯穿算例：文章分镜图、文中数字与实验页共用这组数。
运行：python3 labs-src/reasoning-models/toy.py
  → 生成 src/content/blog/reasoning-models.md（把 article.src.md 里的 {{figN}} 与 {{n:名字}} 填好）
  → 写出 labs-src/reasoning-models/toy.json（实验页开头 TOY 常量里的同一组数）
贯穿全文的题：「一箱有 12 个苹果。买了 3 箱，吃掉 7 个，还剩几个？」答案 29。
"""
import math, json, pathlib, re
from math import comb
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# ———— 第一部分：一道两步的题，直接答与分步答 ————
BOX, NBOX, EAT = 12, 3, 7
MID = BOX * NBOX            # 36
ANS = MID - EAT             # 29
# 分步回答的 token（切分是示意）；标记：0 普通，1 写下的中间结果，2 最终答案
COT = [('3', 0), ('箱', 0), ('是', 0), ('12', 0), ('×', 0), ('3', 0), ('=', 0), ('36', 1), ('。', 0),
       ('吃掉', 0), ('7', 0), ('个', 0), ('，', 0), ('36', 1), ('−', 0), ('7', 0), ('=', 0), ('29', 2), ('。', 0),
       ('答案', 0), ('是', 0), ('29', 2)]
NCOT = len(COT)
# 一个公开的 8 B 模型（Llama-3-8B：32 层，约 8.03 B 参数）
LAYERS, NPARAM = 32, 8.03e9
FLOP_TOK = 2 * NPARAM                       # 每生成一个 token 约 2N 次浮点运算
DEPTH_DIRECT = LAYERS
DEPTH_COT = NCOT * LAYERS
# Wei 等 2022，GSM8K 解题率（论文表 1/2）
WEI = [('PaLM 540B', 17.9, 56.9), ('GPT-3 175B', 15.6, 46.9)]

# ———— 第二部分：多数投票（二项分布） ————
P = 0.6                                       # 分步答时单条推理答对的概率（示意）
def vote(p, k):
    """k 条里答对的多于一半就赢；正好一半时抛硬币。最坏情况：错的都错成同一个答案。"""
    return sum(comb(k, i) * p**i * (1 - p)**(k - i) * (1 if 2*i > k else .5 if 2*i == k else 0) for i in range(k + 1))
BIN5 = [comb(5, i) * P**i * (1 - P)**(5 - i) for i in range(6)]
V3, V5 = vote(P, 3), vote(P, 5)
KS = [1, 3, 5, 9, 15, 25, 41]
# 错的答案各不相同时，k = 3、p = 0.4
pq = 0.4
SC3 = (comb(3, 2) * pq**2 * (1 - pq) + pq**3) + comb(3, 1) * pq * (1 - pq)**2 / 3

# ———— 第三部分：best-of-N 与验证器（蒙特卡洛，种子固定） ————
rng = np.random.default_rng(20261022)
def bon(p, N, d, q, T=200000):
    """N 个回答，每个答对的概率 p。验证器打分 = d·[看起来对] + 标准正态噪声；
    答错的回答里有比例 q「看起来也对」（验证器被骗）。挑分最高的那个。"""
    c = rng.random((T, N)) < p
    fooled = (~c) & (rng.random((T, N)) < q)
    s = rng.normal(size=(T, N)) + d * (c | fooled)
    return float(c[np.arange(T), s.argmax(1)].mean())
NS = [1, 2, 4, 8, 16, 32, 64]
COVER = [1 - (1 - P)**n for n in NS]
VOTE_N = [vote(P, n) for n in NS]
BON_A = [bon(P, n, 2.0, 0.0) for n in NS]
BON_B = [bon(P, n, 2.0, 0.25) for n in NS]
LIMIT_B = P / (P + (1 - P) * 0.25)

# ———— 第四部分：同样的预算 ————
M = 14                                         # 大模型参数是小模型的 14 倍（Snell 等 2024 的设定）
def snell_k(R): return M + 3 * (1 / R) * (M - 1)   # R = 推理 token / 预训练 token
SN = {R: snell_k(R) for R in (0.16, 1.0, 22.0)}
# 示意：只算推理的钱。预算 b = 大模型答 b 次；同样的钱小模型答 14b 次，多数投票
EASY = (0.6, 0.75); HARD = (0.35, 0.6)          # (小模型单次答对率, 大模型单次答对率)，示意
BS = [1, 2, 3, 4, 5, 6]
def curve(ps, pb): return [vote(ps, M * b) for b in BS], [vote(pb, b) for b in BS]
EASY_S, EASY_B = curve(*EASY); HARD_S, HARD_B = curve(*HARD)

# ———— 第五部分：GRPO 为什么会让回答变长（一组 4 个，手算） ————
GRP = [('短', 1), ('短', 0), ('长', 1), ('长', 1)]   # (风格, 奖励)
R_ = [r for _, r in GRP]; MEAN = sum(R_) / 4
STD = math.sqrt(sum((r - MEAN)**2 for r in R_) / 4)
ADV = [(r - MEAN) / STD for r in R_]
SUM_SHORT = sum(a for (s, _), a in zip(GRP, ADV) if s == '短')
SUM_LONG = sum(a for (s, _), a in zip(GRP, ADV) if s == '长')
# 实验 06 的设定（示意）：思考长度 5 档与各档答对率
LENS = [200, 400, 800, 1600, 3200]
PLEN = [0.20, 0.35, 0.50, 0.65, 0.75]

# ———— 第六部分：代价 ————
PRICE = 10.0        # 每百万输出 token 的价格（美元），示意
SPEED = 100.0       # 每秒生成多少 token，示意
TOK = [('直接答', 3), ('分步答', NCOT), ('推理模型', 845)]   # 845：DeepSeek-R1 在 ASDIV 上平均每个回答的 token 数（Chen 等 2024）
COST = [(n, t, t * PRICE / 1e6, t / SPEED) for n, t in TOK]
DAY = 1_000_000     # 每天一百万次请求

# ———— 文中数字 ————
f3 = lambda v: f'{v:.3f}'
pt = lambda v: f'{v*100:.1f}%'
N = {
    'mid': str(MID), 'ans': str(ANS), 'ncot': str(NCOT), 'layers': str(LAYERS),
    'gflop': f'{FLOP_TOK/1e9:.1f}', 'depthcot': str(DEPTH_COT), 'cotflop': f'{NCOT*FLOP_TOK/1e9:.0f}',
    'b0': f'{BIN5[0]:.4f}', 'b1': f'{BIN5[1]:.4f}', 'b2': f'{BIN5[2]:.4f}', 'b3': f'{BIN5[3]:.4f}', 'b4': f'{BIN5[4]:.4f}', 'b5': f'{BIN5[5]:.4f}',
    'v3': f3(V3), 'v5': f'{V5:.4f}', 'v3pc': pt(V3), 'v5pc': pt(V5),
    'p3': f'{P**3:.3f}', 'p2q': f'{3*P*P*(1-P):.3f}',
    'v9pc': pt(vote(P, 9)), 'v41pc': pt(vote(P, 41)), 'w41pc': pt(vote(0.4, 41)), 'w3pc': pt(vote(0.4, 3)),
    'sc3': f3(SC3), 'sc3pc': pt(SC3),
    'cov4pc': pt(1 - (1 - P)**4), 'cov8pc': pt(1 - (1 - P)**8),
    'bonA8pc': pt(BON_A[3]), 'bonB8pc': pt(BON_B[3]), 'bonB64pc': pt(BON_B[6]), 'limB': f3(LIMIT_B), 'limBpc': pt(LIMIT_B),
    'vote8pc': pt(vote(P, 8)), 'vote64pc': pt(vote(P, 64)),
    'sn016': f'{SN[0.16]:.0f}', 'sn1': f'{SN[1.0]:.0f}', 'sn22': f'{SN[22.0]:.1f}',
    'e_s1': pt(EASY_S[0]), 'e_b1': pt(EASY_B[0]), 'e_s3': pt(EASY_S[2]), 'e_b3': pt(EASY_B[2]),
    'h_s1': pt(HARD_S[0]), 'h_b1': pt(HARD_B[0]), 'h_s3': pt(HARD_S[2]), 'h_b3': pt(HARD_B[2]),
    'gmean': f'{MEAN:.2f}', 'gstd': f3(STD), 'aplus': f3(ADV[0]), 'aminus': f3(-ADV[1]),
    'sshort': f3(-SUM_SHORT), 'slong': f3(SUM_LONG),
    'c_dir': f'{COST[0][2]:.6f}', 'c_cot': f'{COST[1][2]:.5f}', 'c_r': f'{COST[2][2]:.5f}',
    't_dir': f'{COST[0][3]:.2f}', 't_cot': f'{COST[1][3]:.2f}', 't_r': f'{COST[2][3]:.2f}',
    'day_dir': f'{COST[0][2]*DAY:,.0f}', 'day_cot': f'{COST[1][2]*DAY:,.0f}', 'day_r': f'{COST[2][2]*DAY:,.0f}',
    'ratio_r': f'{845/3:.0f}',
}

# ———— SVG 小工具：颜色只用 CSS 变量 ————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{esc(s)}</text>'
def rect(x, y, w, h, col, rx=4): return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,1):.1f}" height="{h:.1f}" rx="{rx}" {C(col)}/>'
def box(x, y, w, h, col, sw=1.5, rx=6, dash=None):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" {S_(col, sw, dash)}/>'
def line(x1, y1, x2, y2, col, w=1.5, dash=None): return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {S_(col, w, dash)}/>'
def arrow(x1, y1, x2, y2, col, w=2):
    ang = math.atan2(y2-y1, x2-x1); L = 9; a = 0.42
    bx, by = x2 - L*math.cos(ang), y2 - L*math.sin(ang)
    p1 = (x2 - L*math.cos(ang-a), y2 - L*math.sin(ang-a)); p2 = (x2 - L*math.cos(ang+a), y2 - L*math.sin(ang+a))
    return line(x1, y1, bx, by, col, w) + f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
def tw(s): return 12 + 9.0 * sum(2 if ord(c) > 255 else 1 for c in s)
def poly(pts, col, w=2.5, dash=None):
    return f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" {S_(col, w, dash)}/>'

figs = {}

# 图 1：直接答 vs 分步答，每个生成的 token 下面是一次 32 层的前向计算
b = text(10, 22, '直接答', 'muted', 15)
x0 = 10; y = 34
b += box(x0, y, 92, 32, 'line'); b += text(x0 + 46, y + 22, '题目……', 'muted', 15, 'middle')
xa = x0 + 100
b += box(xa, y, 40, 32, 'warn', 2.2); b += text(xa + 20, y + 22, '?', 'warn', 16, 'middle', weight=600)
b += rect(xa + 14, y + 38, 12, 40, 'line', 2); b += text(xa + 34, y + 64, '32 层，一次', 'muted', 14)
y2 = 140
b += text(10, y2 - 12, '分步答', 'muted', 15)
x = 10; yy = y2; rows = []
for t, k in COT:
    w = tw(t)
    if x + w > 470: x = 10; yy += 74
    col = {0: 'line', 1: 'accent', 2: 'ok'}[k]
    b += box(x, yy, w, 30, col, 2.2 if k else 1.4)
    b += text(x + w/2, yy + 21, t, {0: 'muted', 1: 'accent', 2: 'ok'}[k], 15, 'middle')
    b += rect(x + w/2 - 4, yy + 35, 8, 26, 'accent' if k == 1 else ('ok' if k == 2 else 'line'), 2)
    x += w + 4
H1 = yy + 72
figs['fig1'] = fig(480, H1, '直接答只有一次前向计算，分步答每个 token 都有一次', b,
                   f'图 2　每个方框是一个生成的 token，下面的小竖条是生成它时做的一次前向计算（都是 {LAYERS} 层）。直接答：答案只有一次计算的机会。分步答：{NCOT} 个 token，{NCOT} 次计算；蓝框「{MID}」写下来以后，后面的 token 都能读到它（切分是示意）。')

# 图 2：Wei 等 2022 的 GSM8K 结果（真实数据）
b = ''
for i, (name, s, c) in enumerate(WEI):
    y = 14 + i * 96
    b += text(10, y + 16, name, 'fg', 16, weight=600)
    for j, (lab, v, col) in enumerate((('直接答', s, 'line'), ('思维链', c, 'accent'))):
        yy = y + 26 + j * 32; wv = 300 * v / 60
        b += text(92, yy + 18, lab, 'muted', 15, 'end')
        b += rect(100, yy, wv, 24, col)
        b += text(100 + wv + 8, yy + 18, f'{v:.1f}%', 'accent' if j else 'muted', 16)
figs['fig2'] = fig(480, 14 + 2 * 96, 'GSM8K 上直接答与思维链提示的解题率', b,
                   '图 1　GSM8K（小学数学应用题）的解题率，提示里给 8 个例题。只是把例题的答案改成「先写步骤再给答案」，两个模型的正确率都翻了将近三倍。数据：Wei 等 2022，表 1。')

# 图 3：串行层数
b = ''
items = [('直接答', DEPTH_DIRECT, 'warn'), ('分步答', DEPTH_COT, 'accent')]
for i, (lab, v, col) in enumerate(items):
    y = 18 + i * 52
    b += text(70, y + 20, lab, 'fg', 16, 'end')
    wv = 300 * v / DEPTH_COT
    b += rect(80, y, wv, 28, col)
    b += text(80 + wv + 8, y + 20, f'{v} 层', col, 16)
figs['fig3'] = fig(480, 18 + 2 * 52, '直接答与分步答得到答案之前，最多能串着做多少层计算', b,
                   f'图 3　算出最后那个「{ANS}」之前，计算最多能一层接一层串多深。直接答只有 {LAYERS} 层；分步答每写一个 token 就多 {LAYERS} 层，{NCOT} 个 token 是 {NCOT} × {LAYERS} = {DEPTH_COT} 层。')

# 图 4：k = 5 时答对条数的分布
b = ''; base = 190; bw = 52; gap = 18; x0 = 40
mx = max(BIN5)
for i, v in enumerate(BIN5):
    x = x0 + i * (bw + gap); h = 140 * v / mx
    col = 'ok' if i >= 3 else 'warn'
    b += rect(x, base - h, bw, h, col, 3)
    b += text(x + bw/2, base - h - 8, f'{v:.3f}', col, 15, 'middle')
    b += text(x + bw/2, base + 22, str(i), 'fg', 16, 'middle')
b += line(x0 - 6, base, x0 + 6 * (bw + gap) - gap + 6, base, 'line', 1.5)
b += text(x0 + 3 * (bw + gap) - gap/2, base + 46, '5 条里答对几条', 'muted', 15, 'middle')
xm = x0 + 3 * (bw + gap) - gap/2
b += line(xm, 24, xm, base, 'muted', 1.2, '4 4')
b += text(xm - 8, 22, '错的占多数', 'warn', 15, 'end') + text(xm + 8, 22, '对的占多数', 'ok', 15)
figs['fig4'] = fig(480, base + 56, '采样 5 条推理，答对条数的二项分布', b,
                   f'图 4　单条答对的概率 <i>p</i> = 0.6，采样 5 条，答对条数的分布。绿色三根（3、4、5 条）加起来 {V5:.3f}，就是投票答对的概率。')

# 坐标轴小工具
def axes(x0, y0, w, h, xt, yt, xlabs, ylabs):
    b = line(x0, y0, x0 + w, y0, 'line', 1.5) + line(x0, y0, x0, y0 - h, 'line', 1.5)
    for (xx, s) in xlabs: b += line(xx, y0, xx, y0 + 5, 'line', 1.2) + text(xx, y0 + 22, s, 'muted', 14, 'middle')
    for (yy, s) in ylabs: b += line(x0 - 5, yy, x0, yy, 'line', 1.2) + text(x0 - 9, yy + 5, s, 'muted', 14, 'end') + line(x0, yy, x0 + w, yy, 'line', 0.6, '2 5')
    b += text(x0 + w, y0 + 42, xt, 'muted', 14, 'end')
    b += text(x0 - 4, y0 - h - 12, yt, 'muted', 14)
    return b

# 图 5：投票准确率随 k 的变化（p = 0.6 与 0.4）
X0, Y0, W, Hh = 60, 230, 380, 190
kx = lambda k: X0 + W * math.log(k) / math.log(41)
yv = lambda v: Y0 - Hh * v
b = axes(X0, Y0, W, Hh, '采样条数 k（对数刻度）', '投票答对的概率',
         [(kx(k), str(k)) for k in KS], [(yv(v), f'{v:.1f}') for v in (0, .2, .4, .6, .8, 1.0)])
for p, col in ((0.6, 'ok'), (0.4, 'warn')):
    pts = [(kx(k), yv(vote(p, k))) for k in range(1, 42, 2)]
    b += poly(pts, col)
    for k in KS: b += f'<circle cx="{kx(k):.1f}" cy="{yv(vote(p, k)):.1f}" r="3.5" {C(col)}/>'
    b += text(kx(41) - 4, yv(vote(p, 41)) - 12, f'p = {p}', col, 15, 'end', italic=False)
figs['fig5'] = fig(480, Y0 + 50, '多数投票答对的概率随采样条数的变化', b,
                   f'图 5　投票答对的概率（最坏情况：错的都错成同一个数）。单条答对率 0.6 时，越投越准，41 条到 {vote(0.6, 41)*100:.1f}%；单条答对率 0.4 时，越投越错。')

# 图 6：best-of-N
X0, Y0, W, Hh = 60, 236, 380, 196
nx = lambda n: X0 + W * math.log2(n) / 6
yv = lambda v: Y0 - Hh * (v - 0.5) / 0.5
b = axes(X0, Y0, W, Hh, '回答个数 N（对数刻度）', '最后选中的答案是对的',
         [(nx(n), str(n)) for n in NS], [(yv(v), f'{v:.1f}') for v in (.5, .6, .7, .8, .9, 1.0)])
series = [(COVER, 'muted', '4 5', '有一个对就算（上限）'), (BON_A, 'ok', None, '验证器 · 不被骗'),
          (BON_B, 'accent', None, '验证器 · 被骗 25%'), (VOTE_N, 'warn', None, '多数投票')]
for vals, col, dash, lab in series:
    b += poly([(nx(n), yv(v)) for n, v in zip(NS, vals)], col, 2.5, dash)
    for n, v in zip(NS, vals): b += f'<circle cx="{nx(n):.1f}" cy="{yv(v):.1f}" r="3.2" {C(col)}/>'
ly = 300
for i, (vals, col, dash, lab) in enumerate(series):
    xx = 20 + (i % 2) * 230; yy = ly + (i // 2) * 24
    b += line(xx, yy, xx + 22, yy, col, 3, dash) + text(xx + 30, yy + 5, lab, col, 14)
figs['fig6'] = fig(480, ly + 36, '四种挑选方式的准确率随回答个数的变化', b,
                   f'图 6　单个回答答对率 0.6。虚线是「N 个里至少有一个对」，任何挑法都不可能超过它。验证器不被骗时（绿）贴着上限走；有 25% 的错答案能骗过它时（蓝），停在 {LIMIT_B*100:.1f}% 附近上不去。验证器的结果是蒙特卡洛模拟（每点 20 万次）。')

# 图 7：同样的预算，大模型少想 vs 小模型多想（示意）
def panel(ox, title, S, Bv):
    X0, Y0, W, Hh = ox + 40, 226, 170, 170
    bx = lambda i: X0 + W * (i) / (len(BS) - 1)
    yv = lambda v: Y0 - Hh * v
    b = text(ox + 40, 22, title, 'fg', 16, weight=600)
    b += line(X0, Y0, X0 + W, Y0, 'line', 1.5) + line(X0, Y0, X0, Y0 - Hh, 'line', 1.5)
    for v in (0, .5, 1.0): b += text(X0 - 7, yv(v) + 5, f'{v:.1f}', 'muted', 14, 'end') + line(X0, yv(v), X0 + W, yv(v), 'line', .6, '2 5')
    for i, bb in enumerate(BS): b += text(bx(i), Y0 + 20, str(bb), 'muted', 14, 'middle')
    b += poly([(bx(i), yv(v)) for i, v in enumerate(S)], 'accent') + poly([(bx(i), yv(v)) for i, v in enumerate(Bv)], 'fg', 2.5, '6 4')
    for i, v in enumerate(S): b += f'<circle cx="{bx(i):.1f}" cy="{yv(v):.1f}" r="3.2" {C("accent")}/>'
    for i, v in enumerate(Bv): b += f'<circle cx="{bx(i):.1f}" cy="{yv(v):.1f}" r="3.2" {C("fg")}/>'
    return b
b = panel(0, '容易的题', EASY_S, EASY_B) + panel(240, '难的题', HARD_S, HARD_B)
b += text(240, 270, '预算：够大模型答几次', 'muted', 14, 'middle')
b += line(40, 296, 62, 296, 'accent', 3) + text(70, 301, '小模型 · 同样的钱答 14 倍的次数，投票', 'accent', 14)
b += line(40, 320, 62, 320, 'fg', 2.5, '6 4') + text(70, 325, '大模型 · 参数多 14 倍', 'fg', 14)
figs['fig7'] = fig(480, 336, '同样的推理预算下，大模型与小模型多数投票的准确率', b,
                   f'图 7　示意模型：两道题上小模型、大模型单次答对率分别是 {EASY[0]} / {EASY[1]}（容易）和 {HARD[0]} / {HARD[1]}（难），准确率用二项分布真算。容易的题，把钱花在小模型多答几次上更划算；难的题，小模型单次答对率不到一半，投票越投越错，钱该花在大模型上。')

# 图 8：GRPO 一组里，长回答整体被加强
b = text(14, 22, '回答', 'muted', 15) + text(150, 22, '奖励', 'muted', 15) + text(250, 22, '优势 A', 'muted', 15)
for i, ((s, r), A) in enumerate(zip(GRP, ADV)):
    y = 40 + i * 44
    col = 'accent' if s == '长' else 'line'
    wbox = 120 if s == '长' else 70
    b += box(10, y, wbox, 32, col, 2 if s == '长' else 1.5)
    b += text(10 + wbox/2, y + 22, f'{s}：{"对" if r else "错"}', 'accent' if s == '长' else 'muted', 15, 'middle')
    b += text(162, y + 22, f'{r}', 'ok' if r else 'warn', 16, 'middle', weight=600)
    cx = 340; wv = 40 * abs(A)
    b += rect(cx if A >= 0 else cx - wv, y + 6, wv, 20, 'ok' if A > 0 else 'warn', 3)
    b += text(cx + (wv + 6 if A >= 0 else -wv - 6), y + 22, f'{A:+.3f}'.replace('-', '−'), 'ok' if A > 0 else 'warn', 15, 'start' if A >= 0 else 'end')
b += line(340, 36, 340, 40 + 4 * 44, 'muted', 1.2)
yb = 40 + 4 * 44 + 26
b += text(14, yb, f'短回答优势合计 −{-SUM_SHORT:.3f}　长回答优势合计 +{SUM_LONG:.3f}', 'fg', 15)
figs['fig8'] = fig(480, yb + 12, '同一道题的四个回答，两个短的、两个长的，各自的奖励与优势', b,
                   '图 8　同一道题采样 4 个回答：两个没检查就交卷的短回答（一对一错），两个算完又验算一遍的长回答（都对）。按组内平均算优势：长回答合计为正，被加强；短回答合计为负，被削弱。奖励里没有一个字提到长度。')

# 图 9：三种答法的 token、费用与时间
b = text(80, 22, '输出 token', 'muted', 15) + text(300, 22, '等待时间', 'muted', 15)
for i, (n, t, c, s) in enumerate(COST):
    y = 40 + i * 46
    col = ['warn', 'accent', 'fg'][i]
    b += text(70, y + 20, n, 'fg', 16, 'end')
    wv = 160 * math.log10(t) / math.log10(845)
    b += rect(80, y, wv, 28, 'line' if i < 2 else 'muted')
    b += text(80 + wv + 6, y + 20, f'{t}', 'fg', 15)
    ws = 120 * math.log10(s * 100) / math.log10(845)
    b += rect(300, y, max(ws, 3), 28, 'accent' if i < 2 else 'warn')
    b += text(300 + max(ws, 3) + 6, y + 20, f'{s:.2f} s', 'fg', 15)
figs['fig9'] = fig(480, 40 + 3 * 46, '直接答、分步答与推理模型的输出 token 数和等待时间', b,
                   f'图 9　同一道苹果题三种答法要生成的 token 数，以及按每秒 {SPEED:.0f} 个 token 生成要等多久（对数刻度）。845 是 DeepSeek-R1 在一套小学应用题上平均每个回答的长度。')

# ———— 输出 ————
toy = {'cot': COT, 'mid': MID, 'ans': ANS, 'box': BOX, 'nbox': NBOX, 'eat': EAT, 'layers': LAYERS, 'nparam': NPARAM,
       'p': P, 'M': M, 'easy': EASY, 'hard': HARD, 'lens': LENS, 'plen': PLEN, 'price': PRICE, 'speed': SPEED}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False))
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', v)
left = re.findall(r'\{\{[a-zA-Z0-9:_]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/reasoning-models.md').write_text(src, encoding='utf-8')
print(json.dumps(N, ensure_ascii=False, indent=0))
print('vote p=.6', [round(vote(P, k), 4) for k in KS])
print('cover', [round(v, 3) for v in COVER]); print('bonA', [round(v, 3) for v in BON_A]); print('bonB', [round(v, 3) for v in BON_B]); print('vote', [round(v, 3) for v in VOTE_N])
print('easy', [round(v, 3) for v in EASY_S], [round(v, 3) for v in EASY_B])
print('hard', [round(v, 3) for v in HARD_S], [round(v, 3) for v in HARD_B])
print('grpo', ADV, SUM_SHORT, SUM_LONG)
