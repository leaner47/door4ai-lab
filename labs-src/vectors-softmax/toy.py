"""「向量、矩阵乘法与 softmax」一讲的贯穿算例：文章分镜图、文中数字与实验页共用这组数。
这组数和下一讲（注意力，labs-src/attention-qkv/toy.py）完全相同：同样 4 个 token、同样的 x、W_Q、W_K，
所以读者在下一讲会再次见到这里算出的 (1.0, −0.6)、1.6 / 0.48 / 0.08 / 1.0 和 47.8 %。
运行：python3 labs-src/vectors-softmax/toy.py
  → 生成 src/content/blog/vectors-softmax.md（把 article.src.md 里的 {{figN}} 与 {{n:名字}} 填好）
  → 写出 labs-src/vectors-softmax/toy.json（实验页开头的 TOY 常量抄自这里）
"""
import math, json, pathlib, re, struct
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

T = ['粮油', '店', '买了', '小米']
X = {'粮油': (0.0, 1.0), '店': (0.4, 0.2), '买了': (0.2, 0.0), '小米': (0.5, 0.5)}   # (像手机, 像粮食)
WQ = ((1, 1), (0, -1.2)); WK = ((1, 1), (1, -1))
B = (0.2, 0.4)                                     # 线性层一节的示范偏置 b
mv = lambda W, x: tuple(sum(W[i][j]*x[j] for j in range(len(x))) for i in range(len(W)))
dot = lambda a, b: sum(p*q for p, q in zip(a, b))
norm = lambda a: math.sqrt(dot(a, a))
xm = X['小米']

# ———— 1、2：向量与点积 ————
DOT = {t: dot(xm, X[t]) for t in T}
LEN = {t: norm(X[t]) for t in T}
COS = {t: DOT[t] / LEN['小米'] / LEN[t] for t in T}
ANG = {t: math.degrees(math.acos(max(-1, min(1, COS[t])))) for t in T}

# ———— 3：矩阵乘向量、矩阵乘矩阵 ————
Y = mv(WQ, xm)                                    # (1.0, −0.6)
K = {t: mv(WK, X[t]) for t in T}                  # W_K 乘 4 个 x（矩阵乘矩阵）
S = [dot(K[t], Y) for t in T]                     # 4×2 矩阵乘 2 维向量 → 4 个分数
S = [round(v, 10) for v in S]
assert S == [1.6, 0.48, 0.08, 1.0], S

# ———— 4：线性层 ————
YB = tuple(Y[i] + B[i] for i in range(2))
P_TOY = 2*2 + 2
P_GPT2 = 768*3072 + 3072
P_L3 = 4096*128256

# ———— 5：softmax 与温度 ————
E = [round(math.exp(v), 3) for v in S]            # 文中显示三位小数，份额按显示的数算，和注意力讲一致
SUM = round(sum(E), 3)
W = [e / SUM for e in E]
def soft(z, Tm=1.0):
    m = max(z); e = [math.exp((v - m)/Tm) for v in z]; s = sum(e); return [v/s for v in e]
TEMPS = [0.5, 1.0, math.sqrt(2), 2.0]
WT = {Tm: soft(S, Tm) for Tm in TEMPS}
ET05 = [math.exp(v/0.5) for v in S]
SHIFT = [v - max(S) for v in S]
ESH = [round(math.exp(v), 3) for v in SHIFT]; SUMSH = round(sum(ESH), 3)
NAIVE = [v/sum(S) for v in S]
S_MINUS = [round(v - 1, 2) for v in S]

# ———— 5b：数值稳定性（float32 / float16 的上限） ————
F32MAX = struct.unpack('>f', bytes.fromhex('7f7fffff'))[0]
LN_F32 = math.log(F32MAX); LN_F16 = math.log(65504)
S100 = [v*100 for v in S]

# ———— 6：对数 ————
P1 = round(W[0], 3)                               # 文中写作 0.478
LNP = math.log(P1)
PROD100 = P1**100
F32MIN_SUB = 2**-149

# ———— 数字格式 ————
def f2(v, nd=2):
    if abs(v) < 0.5*10**-nd: return '0'
    t = f'{v:.{nd}f}'.rstrip('0').rstrip('.')
    return t.replace('-', '-')                       # 公式里用 KaTeX 的减号
def f3(v): return f'{v:.3f}'
pct = lambda v: f'{v*100:.1f}\\%'
pct_t = lambda v: f'{v*100:.1f}%'
def big(n): return f'{n:,}'.replace(',', '{,}')

N = {
  'len_xm': f3(LEN['小米']),
  'dot_ly': f2(DOT['粮油']), 'dot_d': f2(DOT['店']), 'dot_m': f2(DOT['买了']), 'dot_x': f2(DOT['小米']),
  'len_d': f3(LEN['店']), 'len_m': f3(LEN['买了']),
  'cos_ly': f3(COS['粮油']), 'cos_d': f3(COS['店']), 'cos_m': f3(COS['买了']), 'cos_x': f3(COS['小米']),
  'ang_ly': f'{ANG["粮油"]:.0f}', 'ang_d': f'{ANG["店"]:.1f}', 'ang_m': f'{ANG["买了"]:.0f}',
  'y1': f'{Y[0]:.1f}', 'y2': f'{Y[1]:.1f}',
  'yb1': f2(YB[0], 1), 'yb2': f2(YB[1], 1),
  'p_gpt2': big(P_GPT2), 'p_l3': big(P_L3),
  'e0': f3(E[0]), 'e1': f3(E[1]), 'e2': f3(E[2]), 'e3': f3(E[3]), 'sum': f3(SUM),
  'w0': f3(W[0]), 'w1': f3(W[1]), 'w2': f3(W[2]), 'w3': f3(W[3]),
  'pw0': pct(W[0]), 'pw1': pct(W[1]), 'pw2': pct(W[2]), 'pw3': pct(W[3]),
  'ratio06': f'{math.exp(0.6):.2f}',
  'naive0': pct(NAIVE[0]), 'naive1': pct(NAIVE[1]), 'naive2': pct(NAIVE[2]), 'naive3': pct(NAIVE[3]), 'sum_s': f2(sum(S)),
  'sm0': f2(S_MINUS[0]), 'sm1': f2(S_MINUS[1]), 'sm2': f2(S_MINUS[2]), 'sm3': f2(S_MINUS[3]), 'sum_sm': f2(sum(S_MINUS)),
  'nm0': pct(S_MINUS[0]/sum(S_MINUS)), 'nm1': pct(S_MINUS[1]/sum(S_MINUS)),
  't05_0': pct(WT[0.5][0]), 't05_1': pct(WT[0.5][1]), 't05_2': pct(WT[0.5][2]), 't05_3': pct(WT[0.5][3]),
  'e05_0': f3(ET05[0]), 'e05_1': f3(ET05[1]), 'e05_2': f3(ET05[2]), 'e05_3': f3(ET05[3]), 'sum05': f3(sum(ET05)),
  't2_0': pct(WT[2.0][0]), 't2_1': pct(WT[2.0][1]), 't2_2': pct(WT[2.0][2]), 't2_3': pct(WT[2.0][3]),
  'tr_0': pct(WT[math.sqrt(2)][0]), 'tr_1': pct(WT[math.sqrt(2)][1]), 'tr_2': pct(WT[math.sqrt(2)][2]), 'tr_3': pct(WT[math.sqrt(2)][3]),
  'ratio_t05': f'{math.exp(0.6/0.5):.2f}', 'ratio_t2': f'{math.exp(0.6/2):.2f}',
  'sh0': f2(SHIFT[0]), 'sh1': f2(SHIFT[1]), 'sh2': f2(SHIFT[2]), 'sh3': f2(SHIFT[3]),
  'esh0': f3(ESH[0]), 'esh1': f3(ESH[1]), 'esh2': f3(ESH[2]), 'esh3': f3(ESH[3]), 'sumsh': f3(SUMSH),
  'wsh0': pct(ESH[0]/SUMSH),
  'ln_f32': f'{LN_F32:.2f}', 'ln_f16': f'{LN_F16:.2f}', 'f32max': '3.4 \\times 10^{38}',
  'e160': f'{math.exp(160)/10**69:.1f} \\times 10^{{69}}',
  'lnp': f3(LNP), 'nlnp': f3(-LNP), 'ln_sum': f3(math.log(SUM)), 'lnp2': f3(S[0] - math.log(SUM)),
  'prod100': f'{PROD100/10**math.floor(math.log10(PROD100)):.1f} \\times 10^{{{math.floor(math.log10(PROD100))}}}',
  'lnsum100': f'{100*LNP:.1f}', 'f32min': '1.4 \\times 10^{-45}',
  'n_under': str(math.ceil(math.log(F32MIN_SUB/2)/LNP)),
  'nl09': f3(-math.log(0.9)), 'nl001': f'{-math.log(0.01):.2f}',
  'p_toy': str(P_TOY),
}
# 检查：0.478^n 在 float32 里第一次变成 0 的 n
import array
p32 = array.array('f', [1.0])
n = 0
while p32[0] != 0.0:
    p32[0] = p32[0] * P1; n += 1
N['n_under'] = str(n)

# ———— SVG 小工具（与注意力讲同一套画法）：颜色只用 CSS 变量 ————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def arrow(x1, y1, x2, y2, col, w=2.5, dash=None):
    ang = math.atan2(y2-y1, x2-x1); L = 11; a = 0.42
    bx, by = x2 - L*math.cos(ang), y2 - L*math.sin(ang)
    p1 = (x2 - L*math.cos(ang-a), y2 - L*math.sin(ang-a)); p2 = (x2 - L*math.cos(ang+a), y2 - L*math.sin(ang+a))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w, dash)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>')
def line(x1, y1, x2, y2, col='line', w=1.5, dash=None):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {S_(col, w, dash)}/>'
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{s}</text>'
def it(s): return f'<tspan font-style="italic">{s}</tspan>'
def rect(x, y, w, h, col, rx=4, op=None, stroke=None):
    st = f'fill:var(--{col})' + (f';fill-opacity:{op}' if op else '') + (f';stroke:var(--{stroke});stroke-width:1.5' if stroke else '')
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" style="{st}"/>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
def plane(ox, oy, unit, xmin, xmax, ymin, ymax, xl='像手机', yl='像粮食'):
    b = arrow(ox + xmin*unit, oy, ox + xmax*unit + 14, oy, 'line', 1.5) + arrow(ox, oy - ymin*unit, ox, oy - ymax*unit - 14, 'line', 1.5)
    if xl: b += text(ox + xmax*unit + 14, oy + 22, xl, 'muted', 16, 'end')
    if yl: b += text(ox + 8, oy - ymax*unit - 12, yl, 'muted', 16)
    return b
def ticks(ox, oy, u, xs, ys):
    b = ''
    for v in xs: b += line(ox + v*u, oy - 4, ox + v*u, oy + 4, 'line') + text(ox + v*u, oy + 20, f2(v, 1), 'muted', 14, 'middle')
    for v in ys: b += line(ox - 4, oy - v*u, ox + 4, oy - v*u, 'line') + text(ox - 8, oy - v*u + 5, f2(v, 1).replace('-', '−'), 'muted', 14, 'end')
    return b
m_ = lambda s: s.replace('-', '−')                 # SVG 里的负号

figs = {}

# 图 1：一个向量 = 一支箭头（小米，向右 0.5、向上 0.5）
ox, oy, u = 70, 250, 300
b = plane(ox, oy, u, 0, 1.15, 0, 0.65)
b += ticks(ox, oy, u, [0.5, 1.0], [0.5])
px, py = ox + xm[0]*u, oy - xm[1]*u
b += line(ox, oy, px, oy, 'muted', 1.5, '5 4') + line(px, oy, px, py, 'muted', 1.5, '5 4')
b += text((ox+px)/2, oy - 10, '向右 0.5', 'muted', 16, 'middle') + text(px + 10, (oy+py)/2 + 6, '向上 0.5', 'muted', 16)
b += arrow(ox, oy, px, py, 'accent', 3)
b += text(px + 12, py - 6, '小米 (0.5, 0.5)', 'accent', 16, weight=600)
figs['fig1'] = fig(480, 280, '向量 (0.5, 0.5) 画成从原点出发的箭头', b,
  '图 1　两个数 (0.5, 0.5) 就是一支箭头：从原点出发，向右走 0.5，再向上走 0.5。箭头的长度是 0.707。')

# 图 2：四个 token 的四支箭头
ox, oy, u = 70, 240, 180
b = plane(ox, oy, u, 0, 1.15, 0, 1.15)
lab_pos = {'粮油': (12, 4, 'start'), '店': (10, 4, 'start'), '买了': (0, 22, 'middle'), '小米': (10, -8, 'start')}
for t in T:
    x, y = X[t]; px, py = ox + x*u, oy - y*u
    b += arrow(ox, oy, px, py, 'accent', 3 if t == '小米' else 2)
    dx, dy, an = lab_pos[t]; b += text(px + dx, py + dy, f'{t} ({f2(x,1)}, {f2(y,1)})', 'accent', 16, an, weight=600 if t == '小米' else None)
figs['fig2'] = fig(480, 270, '四个 token 的向量画成四支箭头', b,
  '图 2　四个 token、四支箭头。横坐标当作「像手机」的程度，纵坐标当作「像粮食」的程度（示意，真实模型的向量没有这种标签）。')

# 图 3：点积 = 投影 × 长度（小米 · 粮油）
ox, oy, u = 120, 250, 200
b = plane(ox, oy, u, 0, 0.9, 0, 1.0)
xl_, yl_ = X['粮油']
b += arrow(ox, oy, ox + xl_*u, oy - yl_*u, 'muted', 2.5) + text(ox - 10, oy - yl_*u + 14, '粮油 (0, 1)', 'muted', 16, 'end')
px, py = ox + xm[0]*u, oy - xm[1]*u
b += line(px, py, ox, py, 'warn', 1.5, '5 4')
b += line(ox, oy, ox, py, 'warn', 6)
b += text(ox - 10, (oy + py)/2 + 6, '投影 0.5', 'warn', 16, 'end')
b += arrow(ox, oy, px, py, 'accent', 3) + text(px + 10, py + 6, '小米 (0.5, 0.5)', 'accent', 16, weight=600)
r = 46; a0 = math.radians(45); a1 = math.radians(90)
b += f'<path d="M{ox + r*math.cos(a0):.1f} {oy - r*math.sin(a0):.1f} A{r} {r} 0 0 0 {ox + r*math.cos(a1):.1f} {oy - r*math.sin(a1):.1f}" {S_("fg", 1.5)}/>'
b += text(ox + 26, oy - 58, '45°', 'fg', 16)
figs['fig3'] = fig(480, 280, '小米向量在粮油方向上的投影是 0.5', b,
  '图 3　从「小米」箭头的尖端向「粮油」那条线做垂线，落在 0.5 处（橙色）。点积 = 粮油的长度 1 × 投影 0.5 = 0.5。两支箭头的夹角是 45°。')

# 图 4：三种方向关系
b = ''
cases = [('同向', 45, 'ok'), ('垂直', 135, 'muted'), ('反向', 225, 'warn')]
for i, (nm, deg, col) in enumerate(cases):
    cx, cy, u = 80 + i*160, 120, 70
    b += line(cx - 75, cy, cx + 75, cy, 'line', 1) + line(cx, cy + 75, cx, cy - 75, 'line', 1)
    vb = (math.cos(math.radians(deg)), math.sin(math.radians(deg)))
    b += arrow(cx, cy, cx + vb[0]*u, cy - vb[1]*u, col if col != 'muted' else 'fg', 2.5)
    b += arrow(cx, cy, cx + 0.5*u, cy - 0.5*u, 'accent', 3.5)
    d = dot(xm, vb)
    b += text(cx, 222, nm, 'fg', 16, 'middle', weight=600)
    b += text(cx, 246, f'点积 {m_(f3(d)) if abs(d) > 1e-9 else "0"}', col if col != 'muted' else 'fg', 16, 'middle')
figs['fig4'] = fig(480, 258, '同向、垂直、反向三种情况下的点积', b,
  '图 4　蓝色都是「小米」(0.5, 0.5)，另一支箭头长度都是 1，只改方向。同向时点积最大（0.707），垂直时为 0，反向时为负。')

# 图 5：矩阵乘向量，逐行做点积（两格分镜）
def grid(x0, y0, vals, cw=56, ch=34, hl_row=None, hl_col=None, colr='accent', fmt=lambda v: m_(f2(v, 1))):
    b = ''
    rows = len(vals); cols = len(vals[0])
    for i in range(rows):
        for j in range(cols):
            x, y = x0 + j*cw, y0 + i*ch
            on = (hl_row is not None and i == hl_row) or (hl_col is not None and j == hl_col)
            if on: b += rect(x + 2, y + 2, cw - 4, ch - 4, colr, 4, 0.18)
            b += text(x + cw/2, y + ch/2 + 6, fmt(vals[i][j]), colr if on else 'fg', 16, 'middle', weight=600 if on else None)
    # 方括号
    h = rows*ch; w = cols*cw
    b += f'<path d="M{x0+6} {y0} h-6 v{h} h6" {S_("fg", 1.5)}/><path d="M{x0+w-6} {y0} h6 v{h} h-6" {S_("fg", 1.5)}/>'
    return b
b = ''
for k in range(2):
    y0 = 18 + k*110
    b += text(4, y0 + 40, f'第 {k+1} 行', 'muted', 16)
    b += grid(70, y0, WQ, hl_row=k, colr='warn')
    b += text(196, y0 + 40, '×', 'muted', 18, 'middle')
    b += grid(216, y0, [[xm[0]], [xm[1]]], hl_col=0, colr='accent')
    b += text(296, y0 + 40, '=', 'muted', 18, 'middle')
    yv = [[Y[0]], [Y[1]]]
    b += grid(316, y0, yv, hl_row=k, colr='warn', fmt=lambda v: m_(f'{v:.1f}'))
    r0, r1 = WQ[k]
    expr = f'{m_(f2(r0,1))} × 0.5 + {"(" + m_(f2(r1,1)) + ")" if r1 < 0 else f2(r1,1)} × 0.5 = {m_(f"{Y[k]:.1f}")}'
    b += text(70, y0 + 92, expr, 'warn', 15)
figs['fig5'] = fig(480, 236, '矩阵的每一行和向量做点积，得到结果的一个数', b,
  '图 5　上：矩阵第 1 行（橙）和向量（蓝）做点积，得到结果的第 1 个数 1.0。下：第 2 行做同样的事，得到 −0.6。')

# 图 6：形状 (4×2)(2) → (4)
b = ''
cw, ch = 30, 30
def blocks(x0, y0, r, c, col, label):
    o = ''
    for i in range(r):
        for j in range(c):
            o += rect(x0 + j*cw + 1, y0 + i*ch + 1, cw - 2, ch - 2, col, 3, 0.22, stroke=col)
    o += text(x0 + c*cw/2, y0 + r*ch + 24, label, col, 16, 'middle', weight=600)
    return o
y0 = 34
b += blocks(70, y0, 4, 2, 'accent', '4 × 2')
b += text(155, y0 + 66, '×', 'muted', 20, 'middle')
b += blocks(180, y0 + 30, 2, 1, 'accent', '2')
b += text(240, y0 + 66, '=', 'muted', 20, 'middle')
b += blocks(270, y0, 4, 1, 'warn', '4')
b += text(70 + cw, y0 - 10, '每行 2 个数', 'muted', 14, 'middle')
b += text(320, y0 + 50, '4 行 → 4 个点积', 'muted', 15)
b += text(320, y0 + 74, '→ 4 个数', 'muted', 15)
figs['fig6'] = fig(480, 192, '4 行 2 列的矩阵乘 2 个数的向量，得到 4 个数', b,
  '图 6　矩阵有 4 行，每行 2 个数；向量也是 2 个数，所以每一行都能和它做点积。做 4 次，得到 4 个数。中间的「2」必须对上。')

# 图 7：矩阵乘矩阵 = 对右边每一列做一次矩阵乘向量
b = ''
XT = [[X[t][0] for t in T], [X[t][1] for t in T]]
KT = [[K[t][0] for t in T], [K[t][1] for t in T]]
cw7 = 44; xw, xx, xk = 8, 104, 302
b += grid(xw, 40, WK, cw=36, colr='muted')
b += text(92, 80, '×', 'muted', 18, 'middle')
b += grid(xx, 40, XT, cw=cw7, hl_col=0, colr='accent', fmt=lambda v: m_(f2(v, 1)))
b += text(xx + 4*cw7 + 11, 80, '=', 'muted', 18, 'middle')
b += grid(xk, 40, KT, cw=42, hl_col=0, colr='warn', fmt=lambda v: m_(f2(v, 1)))
for j, t in enumerate(T):
    b += text(xx + j*cw7 + cw7/2, 30, t, 'accent' if j == 0 else 'muted', 14, 'middle')
b += text(xw + 36, 140, '2 × 2', 'muted', 15, 'middle') + text(xx + 2*cw7, 140, '2 × 4', 'muted', 15, 'middle') + text(xk + 2*42, 140, '2 × 4', 'muted', 15, 'middle')
b += text(8, 172, '第 1 列：(1 × 0 + 1 × 1,  1 × 0 + (−1) × 1) = (1, −1)', 'warn', 15)
figs['fig7'] = fig(480, 186, '一个 2 乘 2 矩阵同时乘 4 个向量', b,
  '图 7　把 4 个 token 的向量竖着排成 4 列，就是一个 2 × 4 矩阵。左边的矩阵对每一列各做一次「矩阵乘向量」，结果也排成 4 列。高亮的是第 1 列「粮油」。')

# 图 8：线性层 y = Wx + b
ox, oy, u = 110, 160, 150
b = plane(ox, oy, u, -0.3, 1.45, -0.75, 0.75, '', '')
for v in [0.5, 1.0]: b += line(ox + v*u, oy - 4, ox + v*u, oy + 4, 'line') + text(ox + v*u, oy - 9, f2(v, 1), 'muted', 14, 'middle')
b += ticks(ox, oy, u, [], [0.5, -0.5])
px, py = ox + xm[0]*u, oy - xm[1]*u
b += arrow(ox, oy, px, py, 'accent', 3) + text(px + 10, py - 4, f'{it("x")} (0.5, 0.5)', 'accent', 16)
wx, wy = ox + Y[0]*u, oy - Y[1]*u
b += arrow(ox, oy, wx, wy, 'warn', 2, '6 5')
b += text(wx - 6, wy + 22, f'{it("W")}{it("x")} (1.0, −0.6)', 'warn', 16, 'end')
yx, yy = ox + YB[0]*u, oy - YB[1]*u
b += arrow(wx, wy, yx, yy, 'muted', 2) + text((wx + yx)/2 + 10, (wy + yy)/2 + 18, f'+{it("b")}', 'muted', 16)
b += arrow(ox, oy, yx, yy, 'warn', 3) + text(yx + 10, yy + 4, f'{it("y")} (1.2, −0.2)', 'warn', 16, weight=600)
figs['fig8'] = fig(480, 300, '线性层先乘矩阵再加偏置', b,
  '图 8　蓝色是输入 x。先乘矩阵得到虚线的 Wx = (1.0, −0.6)，再整体挪一下 b = (0.2, 0.4)，得到橙色的 y = (1.2, −0.2)。')

# 图 9：指数函数 e^s，标出 4 个分数
b = ''
X0 = 40; W9 = 400; smin, smax = -1.5, 2.0; Y0 = 262; H9 = 230; emax = 5.5
sx = lambda s: X0 + (s - smin)/(smax - smin)*W9
sy = lambda e: Y0 - e/emax*H9
b += arrow(X0, Y0, X0 + W9 + 16, Y0, 'line', 1.5) + arrow(sx(0), Y0 + 6, sx(0), Y0 - H9 - 14, 'line', 1.5)
b += f'<text x="{X0 + W9 + 14}" y="{Y0 + 22}" font-size="16" text-anchor="end" font-style="italic" {C("muted")}>s</text>'
b += f'<text x="{sx(0) + 8}" y="{Y0 - H9 - 4}" font-size="16" {C("muted")}><tspan font-style="italic">e</tspan><tspan font-size="11" dy="-7" font-style="italic">s</tspan></text>'
for v in [-1, 1, 2]: b += line(sx(v), Y0 - 4, sx(v), Y0 + 4) + text(sx(v), Y0 + 20, m_(str(v)), 'muted', 14, 'middle')
b += line(sx(0) - 4, sy(1), sx(0) + 4, sy(1))
pts = ' '.join(f'{sx(smin + i*(smax-smin)/120):.1f},{sy(math.exp(smin + i*(smax-smin)/120)):.1f}' for i in range(121) if math.exp(smin + i*(smax-smin)/120) <= emax)
b += f'<polyline points="{pts}" {S_("fg", 2.5)}/>'
lp = {0: (-12, 4, 'end'), 1: (10, 24, 'start'), 2: (-16, -10, 'end'), 3: (-12, -8, 'end')}
for i, t in enumerate(T):
    s = S[i]; e = math.exp(s)
    b += f'<circle cx="{sx(s):.1f}" cy="{sy(e):.1f}" r="5" {C("warn" if i == 0 else "accent")}/>'
    dx, dy, an = lp[i]
    b += text(sx(s) + dx, sy(e) + dy, f'{t} {f3(e)}', 'warn' if i == 0 else 'accent', 15, an)
figs['fig9'] = fig(480, 290, '指数函数曲线上标出四个分数', b,
  '图 9　黑线是指数函数 eˢ：永远在横轴上方，越往右涨得越快。四个点是四个分数取指数之后的值，最右边橙色的是「粮油」。')

# 图 10：分数 → eˢ → 份额（三列条形）
def bars3(cols, hi, h=40):
    b = ''
    x0s = [70, 210, 340]
    for c, (title, vals, fmt) in enumerate(cols):
        b += text(x0s[c], 24, title, 'muted', 16)
        mx = max(vals)
        for i, t in enumerate(T):
            y = 44 + i*h
            if c == 0: b += text(60, y + 17, t, 'fg', 16, 'end')
            wv = 80*vals[i]/mx; col = 'warn' if i == hi else 'line'
            b += rect(x0s[c], y, max(wv, 1), 24, col)
            b += text(x0s[c] + wv + 6, y + 18, fmt(vals[i]), 'warn' if i == hi else 'muted', 15)
    return b
figs['fig10'] = fig(480, 44 + 4*40 + 6, '分数、取指数之后、除以总和之后', bars3([
    (f'分数 {it("s")}', S, lambda v: '1.0' if v == 1 else f2(v)), ('eˢ', [math.exp(v) for v in S], f3), ('份额', W, pct_t)], 0),
  '图 10　从左到右：分数 → 取指数（都变成正数，差距拉大）→ 除以总和（加起来是 100%）。排名始终不变。')

# 图 11：四种温度
b = ''
for k, Tm in enumerate(TEMPS):
    cx = 10 + k*118; base = 190
    lab = {0.5: '0.5', 1.0: '1', 2.0: '2'}.get(Tm, '√2 ≈ 1.41')
    b += f'<text x="{cx + 52}" y="24" font-size="16" text-anchor="middle" {C("fg")}><tspan font-style="italic">T</tspan> = {lab}</text>'
    for i, t in enumerate(T):
        p = WT[Tm][i]; hgt = p*190
        x = cx + 6 + i*24
        b += rect(x, base - hgt, 18, max(hgt, 1), 'warn' if i == 0 else 'line', 3)
        b += text(x + 9, base + 18, t[0], 'muted', 13, 'middle')
    b += text(cx + 52, base + 42, f'粮油 {pct_t(WT[Tm][0])}', 'warn', 15, 'middle')
figs['fig11'] = fig(480, 244, '同一组分数在四种温度下的份额', b,
  '图 11　同一组分数，除以不同的温度 T 再做 softmax。T 越小，第一名（橙）越高、分布越尖；T 越大，四根柱子越接近。柱下的字是「粮、店、买、小」。')

# 图 12：对数曲线 ln p
b = ''
X0, W12, Y0, H12 = 60, 390, 30, 230
pmin = 0.02
sx = lambda p: X0 + p*W12
lmin = -4.2
sy = lambda l: Y0 + (0 - l)/(0 - lmin)*H12
b += arrow(X0, Y0, X0 + W12 + 16, Y0, 'line', 1.5) + arrow(X0, Y0 - 6, X0, Y0 + H12 + 14, 'line', 1.5)
b += f'<text x="{X0 + W12 + 14}" y="{Y0 - 8}" font-size="16" text-anchor="end" font-style="italic" {C("muted")}>p</text>'
b += f'<text x="{X0 + 10}" y="{Y0 + H12 + 10}" font-size="16" {C("muted")}>ln <tspan font-style="italic">p</tspan></text>'
for v in [0.5, 1.0]: b += line(sx(v), Y0 - 4, sx(v), Y0 + 4) + text(sx(v), Y0 - 10, f2(v, 1), 'muted', 14, 'middle')
for v in [-1, -2, -3, -4]: b += line(X0 - 4, sy(v), X0 + 4, sy(v)) + text(X0 - 8, sy(v) + 5, m_(str(v)), 'muted', 14, 'end')
pts = ' '.join(f'{sx(p):.1f},{sy(math.log(p)):.1f}' for p in [pmin + i*(1 - pmin)/200 for i in range(201)] if math.log(p) >= lmin)
b += f'<polyline points="{pts}" {S_("fg", 2.5)}/>'
for p, col, an, dx, dy in [(P1, 'warn', 'start', 10, 20), (0.05, 'accent', 'start', 10, 6)]:
    b += f'<circle cx="{sx(p):.1f}" cy="{sy(math.log(p)):.1f}" r="5" {C(col)}/>'
    b += text(sx(p) + dx, sy(math.log(p)) + dy, f'{it("p")} = {f3(p) if p == P1 else f2(p)}，ln {it("p")} = {m_(f3(math.log(p)))}', col, 15, an)
figs['fig12'] = fig(480, 290, '对数函数 ln p 在 0 到 1 之间的曲线', b,
  '图 12　概率 p 在 0 到 1 之间时，ln p 都是负数：p = 1 时正好是 0，p 越小越往下掉。橙色点是「粮油」的份额 0.478。')

# ———— 输出 ————
toy = {'tokens': T, 'x': X, 'WQ': WQ, 'WK': WK, 'b': B, 'y': Y, 'k': K, 's': S}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False))
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', v)
left = re.findall(r'\{\{[a-z0-9:_]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/vectors-softmax.md').write_text(src, encoding='utf-8')
print(json.dumps(N, ensure_ascii=False, indent=0))
