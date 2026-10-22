"""「扩散模型」一讲的贯穿算例：文章里的手算数字、分镜图，以及实验页的组装。
运行（先跑 mc.mjs，它用实验页同一份 core.js 做随机抽样）：
  node labs-src/diffusion-models/mc.mjs     → labs-src/diffusion-models/mc.json
  python3 labs-src/diffusion-models/toy.py  → src/content/blog/diffusion-models.md（由 article.src.md 填入 {{figN}} 与 {{n:名字}}）
                                            → public/labs/diffusion-models/index.html（lab.src.html 里的 /*__CORE__*/ 换成 core.js）
"""
import math, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MC = json.loads((HERE / 'mc.json').read_text())

# ———— 贯穿全讲的「图」：只有两个像素（左、右），亮度从 −1（黑）到 1（白） ————
MU_A, MU_B, SD = (0.7, -0.7), (-0.7, 0.7), 0.1          # 左边亮 / 右边亮 两团，每团标准差 0.1（与 core.js 的 two 相同）
X0 = MU_A                                                 # 要加噪的那张图：左边亮
ALPHAS = [0.9, 0.8, 0.5, 0.25]                            # 手算用的 4 步小调度
BETAS = [1 - a for a in ALPHAS]
ABAR = [1.0]
for a in ALPHAS: ABAR.append(ABAR[-1] * a)               # ABAR[t]，t = 0..4
EPS = (-1.0, 0.5)                                         # 一步跳到 t = 3 时用的噪声
# 一步步加噪时每步的新噪声：ε₁、ε₂、ε₄ 直接给定；ε₃ 选成让前三步的噪声合起来正好等于 0.8 ε，
# 这样一步步走到的 x₃ 和一步到位算出的 x₃ 是同一个点
_E1, _E2 = (0.6, -0.2), (-1.2, 0.9)
_c1 = (0.5 * 0.8 * 0.1) ** 0.5; _c2 = (0.5 * 0.2) ** 0.5; _c3 = 0.5 ** 0.5
_E3 = tuple((0.8 * EPS[i] - _c1 * _E1[i] - _c2 * _E2[i]) / _c3 for i in range(2))
EPS_STEPS = [_E1, _E2, _E3, (-0.5, -0.8)]
T3 = 3
Z = (0.4, -0.2)                                           # 往回走一步时加的新噪声

add = lambda a, b: (a[0] + b[0], a[1] + b[1])
sc = lambda k, a: (k * a[0], k * a[1])
sub = lambda a, b: (a[0] - b[0], a[1] - b[1])
dot = lambda a, b: a[0] * b[0] + a[1] * b[1]
sq = lambda a: dot(a, a)

# 一步步加噪
XS = [X0]
for t in range(1, 5):
    XS.append(add(sc(math.sqrt(ALPHAS[t-1]), XS[-1]), sc(math.sqrt(BETAS[t-1]), EPS_STEPS[t-1])))
# 一步到位
ab3 = ABAR[T3]; sa3, sb3 = math.sqrt(ab3), math.sqrt(1 - ab3)
X3 = add(sc(sa3, X0), sc(sb3, EPS))
X0_BACK = sc(1 / sa3, sub(X3, sc(sb3, EPS)))

# 解析最优预测（与 core.js 的 epsOpt 同一公式）
def eps_opt(x, ab, comps):
    sa, sb = math.sqrt(ab), math.sqrt(1 - ab)
    rows = []
    for mu, w in comps:
        v = ab * SD * SD + 1 - ab
        d = sub(x, sc(sa, mu))
        rows.append(dict(mu=mu, v=v, d=d, d2=sq(d), lik=w * math.exp(-sq(d) / (2 * v)), e=sc(sb / v, d)))
    S = sum(r['lik'] for r in rows)
    for r in rows: r['r'] = r['lik'] / S
    e = (sum(r['r'] * r['e'][0] for r in rows), sum(r['r'] * r['e'][1] for r in rows))
    return e, rows
EH, ROWS = eps_opt(X3, ab3, [(MU_A, 0.5), (MU_B, 0.5)])
EA, EB = ROWS[0]['e'], ROWS[1]['e']
LOSS_EH = sq(sub(EPS, EH)); LOSS_EA = sq(sub(EPS, EA))

# 往回走一步：t = 3 → 2
a3, b3, ab2 = ALPHAS[2], BETAS[2], ABAR[2]
BT = (1 - ab2) / (1 - ab3) * b3                            # β̃：后验方差
PREC1, PREC2 = 1 / (1 - ab2), a3 / b3                      # 两个钟形的精度
CEN1, CEN2 = sc(math.sqrt(ab2), X0), sc(1 / math.sqrt(a3), X3)
MU_POST = sc(1 / (PREC1 + PREC2), add(sc(PREC1, CEN1), sc(PREC2, CEN2)))
CX0 = math.sqrt(ab2) * b3 / (1 - ab3); CXT = math.sqrt(a3) * (1 - ab2) / (1 - ab3)
MU_POST2 = add(sc(CX0, X0), sc(CXT, X3))
K_EPS = b3 / math.sqrt(1 - ab3)                            # β/√(1−ᾱ)
MU_TRUE = sc(1 / math.sqrt(a3), sub(X3, sc(K_EPS, EPS)))
MU_TH = sc(1 / math.sqrt(a3), sub(X3, sc(K_EPS, EH)))
X2 = add(MU_TH, sc(math.sqrt(BT), Z))
K_LOSS = b3 / (math.sqrt(a3) * math.sqrt(1 - ab3))
assert abs(MU_POST[0] - MU_TRUE[0]) < 1e-9 and abs(MU_POST2[1] - MU_TRUE[1]) < 1e-9

# DDIM：从 t = 3 直接跳到 t = 1
X0H = sc(1 / sa3, sub(X3, sc(sb3, EH)))
X1_DDIM = add(sc(math.sqrt(ABAR[1]), X0H), sc(math.sqrt(1 - ABAR[1]), EH))

# guidance：条件 = 左边亮
def guided(s): return add(EH, sc(s, sub(EA, EH)))
CFG_S = [0, 1, 3, 7.5]
CFG = {s: (guided(s), sc(1 / sa3, sub(X3, sc(sb3, guided(s))))) for s in CFG_S}

# 交叉注意力：一个潜空间位置看三个文字 token
CA_TOK = ['一只', '橘', '猫']
CA_Q = (1.0, 0.5)
CA_K = [(0.2, 0.1), (0.9, 0.3), (0.4, 1.0)]
CA_V = [(0.1, 0.0), (1.0, 0.2), (0.1, 0.9)]
CA_S = [dot(CA_Q, k) for k in CA_K]
CA_SS = [s / math.sqrt(2) for s in CA_S]
CA_E = [math.exp(s) for s in CA_SS]; CA_SUM = sum(CA_E); CA_W = [e / CA_SUM for e in CA_E]
CA_OUT = (sum(w * v[0] for w, v in zip(CA_W, CA_V)), sum(w * v[1] for w, v in zip(CA_W, CA_V)))

# 真实规模
def linear_sched(T=1000, b1=1e-4, bT=0.02):
    ab = [1.0]
    for i in range(T): ab.append(ab[-1] * (1 - (b1 + (bT - b1) * i / (T - 1))))
    return ab
AB = linear_sched()
HALF = next(t for t in range(1001) if AB[t] < 0.5)
PIX = 512 * 512 * 3; LAT = 64 * 64 * 4

# 流匹配：直线插值
FM_T = 0.5
FM_X = add(sc(1 - FM_T, X0), sc(FM_T, EPS)); FM_V = sub(EPS, X0)

# ———— 文中数字 ————
def f(v, d=3):
    s = f'{v:.{d}f}'
    if '.' in s: s = s.rstrip('0').rstrip('.')
    if s in ('-0', ''): s = '0'
    return s.replace('-', '−')
def fl(v, d=3):   # 公式里用的负号保持 ASCII（KaTeX 里写 -）
    return f(v, d).replace('−', '-')
def vec(v, d=3): return f'({f(v[0], d)},\\ {f(v[1], d)})'.replace('−', '-')
def vtxt(v, d=3): return f'({f(v[0], d)}, {f(v[1], d)})'
pct = lambda v, d=1: f'{v*100:.{d}f}%'
N = {
  'x1': vec(XS[1], 4), 'x2s': vec(XS[2]), 'x3s': vec(XS[3]), 'x4s': vec(XS[4]),
  'x1a': fl(math.sqrt(0.9) * 0.7, 4), 'x1b': fl(math.sqrt(0.1) * 0.6, 4), 'x1c': fl(math.sqrt(0.1) * -0.2, 4),
  'x3': vec(X3), 'e3': vec(EPS_STEPS[2], 4), 'x0back': vec(X0_BACK),
  'abT': f'{AB[1000]:.2e}'.replace('e-05', ' \\times 10^{-5}'), 'sabT': f(math.sqrt(AB[1000]), 4), 'half': str(HALF),
  'ab100': f(AB[100], 3), 'ab250': f(AB[250], 3), 'ab500': f(AB[500], 3), 'sab500': f(math.sqrt(AB[500]), 3),
  'v3': f(ROWS[0]['v'], 4), 'sb3v': f(sb3 / ROWS[0]['v'], 4),
  'dA': vec(ROWS[0]['d']), 'dB': vec(ROWS[1]['d']), 'd2A': f(ROWS[0]['d2'], 4), 'd2B': f(ROWS[1]['d2'], 4),
  'expA': f(math.exp(-ROWS[0]['d2'] / (2 * ROWS[0]['v'])), 4), 'expB': f(math.exp(-ROWS[1]['d2'] / (2 * ROWS[1]['v'])), 4),
  'argA': f(ROWS[0]['d2'] / (2 * ROWS[0]['v']), 4), 'argB': f(ROWS[1]['d2'] / (2 * ROWS[1]['v']), 4),
  'rA': f(ROWS[0]['r'], 4), 'rB': f(ROWS[1]['r'], 4), 'rApct': pct(ROWS[0]['r']), 'rApctTex': pct(ROWS[0]['r']).replace('%', '\\%'), 'rBpct': pct(ROWS[1]['r']),
  'eA': vec(EA, 4), 'eB': vec(EB, 4), 'eh': vec(EH, 4), 'lossEh': f(LOSS_EH, 3), 'lossEa': f(LOSS_EA, 5),
  'floor': f(MC['floor'], 3), 'trainEnd': f(MC['train'][-1][1], 3), 'netq': pct(MC['net_q']),
  'bt': f(BT, 5), 'sbt': f(math.sqrt(BT), 4), 'prec1': f(PREC1, 4), 'prec2': f(PREC2, 4), 'precsum': f(PREC1 + PREC2, 4),
  'num1': vec(sc(PREC1, CEN1), 4), 'numsum': vec(add(sc(PREC1, CEN1), sc(PREC2, CEN2)), 4), 'cen1': vec(CEN1, 4), 'cen2': vec(CEN2, 4), 'mupost': vec(MU_POST, 4), 'cx0': f(CX0, 4), 'cxt': f(CXT, 4),
  'keps': f(K_EPS, 4), 'ia3': f(1 / math.sqrt(a3), 4), 'mutrue': vec(MU_TRUE, 4), 'muth': vec(MU_TH, 4),
  'inner_true': vec(sub(X3, sc(K_EPS, EPS)), 4), 'inner_th': vec(sub(X3, sc(K_EPS, EH)), 4),
  'x2': vec(X2, 3), 'kloss': f(K_LOSS, 4), 'mudiff': vec(sub(MU_TRUE, MU_TH), 4), 'ediff': vec(sub(EPS, EH), 4),
  'x0h': vec(X0H, 4), 'x1ddim': vec(X1_DDIM, 4), 'x0h_inner': vec(sub(X3, sc(sb3, EH)), 4),
  'ddim_a': f(math.sqrt(ABAR[1]), 4), 'ddim_b': f(math.sqrt(1 - ABAR[1]), 4),
  'pix': f'{PIX:,}'.replace(',', '{,}'), 'lat': f'{LAT:,}'.replace(',', '{,}'), 'ratio': f(PIX / LAT, 2),
  'caS': ' / '.join(f(s, 3) for s in CA_S), 'caW': ' / '.join(pct(w) for w in CA_W), 'caOut': vec(CA_OUT, 3),
  'fmx': vec(FM_X, 3), 'fmv': vec(FM_V, 3),
  'q1': pct(MC['q_ddim'][0], 0), 'q5ddim': pct(MC['q_ddim'][3]), 'q5ddpm': pct(MC['q_ddpm'][3]),
  'q10ddim': pct(MC['q_ddim'][4]), 'q10ddpm': pct(MC['q_ddpm'][4]), 'q50ddim': pct(MC['q_ddim'][6]), 'q1000ddpm': pct(MC['q_ddpm'][9]),
  'qtrue': pct(MC['q_true']),
}
for i, s in enumerate(CFG_S):
    e, x = CFG[s]; k = str(s).replace('.', '_')
    N[f'ge{k}'] = vec(e, 3); N[f'gx{k}'] = vec(x, 3)
for c in MC['cfg']:
    k = str(c['s']).replace('.', '_')
    N[f'cl{k}'] = pct(c['left']); N[f'csd{k}'] = f(c['sd'], 3); N[f'cc{k}'] = pct(c['clip'])
N['cltrue'] = pct(MC['cfg_true']['left']); N['csdtrue'] = f(MC['cfg_true']['sd'], 3)
for i in range(3):
    N[f'caS{i}'] = f(CA_S[i], 3); N[f'caSS{i}'] = f(CA_SS[i], 3); N[f'caE{i}'] = f(CA_E[i], 3); N[f'caW{i}'] = pct(CA_W[i])
N['caSum'] = f(CA_SUM, 3)

# ———— SVG 小工具：颜色只用 CSS 变量 ————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def arrow(x1, y1, x2, y2, col, w=2.5, dash=None):
    ang = math.atan2(y2-y1, x2-x1); L = 10; a = 0.42
    if math.hypot(x2-x1, y2-y1) < 4: return ''
    bx, by = x2 - L*math.cos(ang), y2 - L*math.sin(ang)
    p1 = (x2 - L*math.cos(ang-a), y2 - L*math.sin(ang-a)); p2 = (x2 - L*math.cos(ang+a), y2 - L*math.sin(ang+a))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w, dash)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None, halo=False):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    st = f'fill:var(--{col})' + (';paint-order:stroke;stroke:var(--bg);stroke-width:4' if halo else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} style="{st}">{s}</text>'
def mt(x, y, parts, col='fg', size=16, anchor='start', halo=False):
    """数学记号：parts = [('x','i'),('t','sub'),…]；i 斜体，sub 下标，sup 上标"""
    st = f'fill:var(--{col})' + (';paint-order:stroke;stroke:var(--bg);stroke-width:4' if halo else '')
    b = f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" style="{st}">'
    for s, k in parts:
        if k == 'i': b += f'<tspan font-style="italic">{s}</tspan>'
        elif k == 'sub': b += f'<tspan font-size="{size*0.72:.1f}" dy="4">{s}</tspan><tspan dy="-4"> </tspan>'
        elif k == 'isub': b += f'<tspan font-size="{size*0.72:.1f}" dy="4" font-style="italic">{s}</tspan><tspan dy="-4"> </tspan>'
        else: b += f'<tspan>{s}</tspan>'
    return b + '</text>'
def ehat(x, y, col, size=16, anchor='start'):
    """带帽子的 ε：帽子单独画一个字符，避免组合附加符号在各字体里错位"""
    w = size * 0.45
    x0 = x if anchor == 'start' else (x - w if anchor == 'end' else x - w / 2)
    return (f'<text x="{x0:.1f}" y="{y:.1f}" font-size="{size}" font-style="italic" style="fill:var(--{col});paint-order:stroke;stroke:var(--bg);stroke-width:4">ε</text>'
            f'<text x="{x0 + w/2 + 1:.1f}" y="{y - size*0.42:.1f}" font-size="{size*0.8:.1f}" text-anchor="middle" style="fill:var(--{col})">ˆ</text>')
def rect(x, y, w, h, col, rx=4, stroke=None, sw=1.5, op=None):
    st = f'fill:var(--{col})' if col else 'fill:none'
    if op is not None: st += f';fill-opacity:{op}'
    if stroke: st += f';stroke:var(--{stroke});stroke-width:{sw}'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" style="{st}"/>'
def dot_(x, y, col, r=3, op=1):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" style="fill:var(--{col});fill-opacity:{op}"/>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
def swatch(x, y, px, s=22):
    """两个像素的小图：−1 黑，1 白（像素本身用固定灰度，深浅色下一样）"""
    b = ''
    for i, v in enumerate(px):
        g = round(255 * (max(-1, min(1, v)) + 1) / 2)
        b += f'<rect x="{x + i*s:.1f}" y="{y:.1f}" width="{s}" height="{s}" fill="rgb({g},{g},{g})" style="stroke:var(--muted);stroke-width:1"/>'
    return b

class Plane:
    """左像素为横轴、右像素为纵轴的平面"""
    def __init__(self, ox, oy, u, lim=1.3, labels=True, size=15):
        self.ox, self.oy, self.u, self.lim = ox, oy, u, lim
        self.b = ''
        L = lim * u
        self.b += f'<rect x="{ox-L:.1f}" y="{oy-L:.1f}" width="{2*L:.1f}" height="{2*L:.1f}" rx="4" style="fill:none;stroke:var(--line);stroke-width:1"/>'
        self.b += f'<line x1="{ox-L:.1f}" y1="{oy:.1f}" x2="{ox+L:.1f}" y2="{oy:.1f}" {S_("line", 1)}/>'
        self.b += f'<line x1="{ox:.1f}" y1="{oy-L:.1f}" x2="{ox:.1f}" y2="{oy+L:.1f}" {S_("line", 1)}/>'
        if labels:
            self.b += text(ox + L - 4, oy + 16, '左像素', 'muted', size - 2, 'end')
            self.b += text(ox + 5, oy - L + 15, '右像素', 'muted', size - 2, 'start')
    def p(self, v): return (self.ox + v[0] * self.u, self.oy - v[1] * self.u)
    def inside(self, v): return abs(v[0]) <= self.lim and abs(v[1]) <= self.lim

figs = {}

# 图 1：数据平面上的两团 + 两张小图
pl = Plane(150, 150, 95, 1.3)
for c in MC['forward'][0]['xs']:
    pl.b += dot_(*pl.p(c), 'accent', 2.4, 0.55)
pa, pb = pl.p(MU_A), pl.p(MU_B)
b = pl.b
b += swatch(pa[0] - 100, pa[1] - 30, MU_A) + text(pa[0] - 78, pa[1] + 12, '左边亮', 'accent', 15, 'middle')
b += swatch(pb[0] + 34, pb[1] - 30, MU_B) + text(pb[0] + 56, pb[1] + 12, '右边亮', 'accent', 15, 'middle')
b += text(300, 60, '每个点 = 一张两像素的图', 'muted', 15)
b += text(300, 86, '横坐标 = 左像素亮度', 'muted', 15)
b += text(300, 112, '纵坐标 = 右像素亮度', 'muted', 15)
b += text(300, 150, '−1 黑，1 白', 'muted', 15)
b += swatch(300, 166, (-1, -1)) + text(352, 183, '(−1, −1)', 'muted', 14)
b += swatch(300, 196, (1, 1)) + text(352, 213, '(1, 1)', 'muted', 14)
figs['fig1'] = fig(480, 300, '两像素小图的数据分布：左边亮和右边亮两团点', b,
                   '图 1　贯穿全讲的「图」只有两个像素。每个蓝点是一张训练图：右下那团是「左边亮」，左上那团是「右边亮」。')

# 图 2：加一步噪声（局部放大）
U2 = 900; P2 = lambda v: (90 + (v[0] - 0.62) * U2, 60 + (-0.6 - v[1]) * U2)
p0, p1 = P2(X0), P2(XS[1])
shr = P2(sc(math.sqrt(ALPHAS[0]), X0))
b = rect(20, 20, 300, 200, None, 6, 'line', 1)
b += dot_(*p0, 'accent', 6) + text(p0[0] + 4, p0[1] + 26, f'x₀ {vtxt(X0, 1)}', 'accent', 15, 'middle')
b += arrow(*p0, *shr, 'muted', 2) + text((p0[0] + shr[0]) / 2 - 16, (p0[1] + shr[1]) / 2 - 4, '× √0.9', 'muted', 14, 'end')
b += arrow(*shr, *p1, 'warn', 2.5) + text((shr[0] + p1[0]) / 2, (shr[1] + p1[1]) / 2 - 12, '+ √0.1 ε₁', 'warn', 15, 'middle')
b += dot_(*p1, 'fg', 5) + text(p1[0], p1[1] + 26, f'x₁ {vtxt(XS[1], 3)}', 'fg', 15, 'middle')
b += text(30, 42, '局部放大（右下那团附近）', 'muted', 13)
b += text(340, 80, '先缩小一点', 'muted', 15) + text(340, 106, '（往原点方向）', 'muted', 14) + text(340, 140, '再加一点噪声', 'warn', 15)
figs['fig2'] = fig(480, 240, '加一步噪声：先把 x0 缩小，再加上一小段噪声', b,
                   '图 2　加一步噪声（局部放大）。灰色箭头：x₀ 乘以 √0.9，往原点缩了一点；橙色箭头：加上 √0.1 倍的噪声 ε₁。')

# 图 3：4 步轨迹
pl = Plane(160, 160, 100, 1.4)
b = pl.b
pts = [pl.p(x) for x in XS]
for i in range(4):
    b += arrow(*pts[i], *pts[i+1], 'warn' if i else 'warn', 2)
offs = [(-10, -12, 'end'), (10, 18, 'start'), (8, -10, 'start'), (10, 18, 'start'), (-10, 18, 'end')]
for i, (pp, x) in enumerate(zip(pts, XS)):
    b += dot_(*pp, 'accent' if i == 0 else 'fg', 5 if i == 0 else 4)
    dx, dy, an = offs[i]
    b += text(pp[0] + dx, pp[1] + dy, f'x{"₀₁₂₃₄"[i]}', 'accent' if i == 0 else 'fg', 15, an, halo=True)
y0 = 30
b += text(318, y0, 't', 'muted', 14, 'middle', italic=True) + text(360, y0, 'ᾱ', 'muted', 14, 'middle', italic=True) + text(430, y0, '原图还剩 √ᾱ', 'muted', 14, 'middle')
for t in range(5):
    y = y0 + 26 + t * 26
    b += text(318, y, str(t), 'fg', 15, 'middle') + text(360, y, f(ABAR[t], 4), 'fg', 15, 'middle') + text(430, y, f(math.sqrt(ABAR[t]), 3), 'accent', 15, 'middle')
figs['fig3'] = fig(480, 320, '一张图连加 4 步噪声的轨迹，以及每步之后原图还剩多少', b,
                   '图 3　同一张图连加 4 步噪声（每步的新噪声不同）。右边的表：第 t 步之后，原图只剩 √ᾱ 倍。')

# 图 4：真实调度曲线
X0p, Y0p, Wp, Hp = 60, 230, 380, 190
b = f'<line x1="{X0p}" y1="{Y0p}" x2="{X0p+Wp}" y2="{Y0p}" {S_("line", 1.5)}/><line x1="{X0p}" y1="{Y0p}" x2="{X0p}" y2="{Y0p-Hp-8}" {S_("line", 1.5)}/>'
for t in (0, 250, 500, 750, 1000):
    b += text(X0p + Wp * t / 1000, Y0p + 20, str(t), 'muted', 14, 'middle')
for v in (0, 0.5, 1):
    b += text(X0p - 8, Y0p - Hp * v + 5, f(v, 1), 'muted', 14, 'end')
def poly(fn, col, w=2.5, dash=None):
    ps = ' '.join(f'{X0p + Wp*t/1000:.1f},{Y0p - Hp*fn(t):.1f}' for t in range(0, 1001, 10))
    return f'<polyline points="{ps}" {S_(col, w, dash)}/>'
b += poly(lambda t: math.sqrt(AB[t]), 'accent') + poly(lambda t: math.sqrt(1 - AB[t]), 'warn')
b += text(X0p + 10, Y0p - Hp * 0.5, '原图的系数 √ᾱ', 'accent', 15)
b += text(X0p + Wp * 0.55, Y0p - Hp * 0.8, '噪声的系数 √(1 − ᾱ)', 'warn', 15)
xh = X0p + Wp * HALF / 1000
b += f'<line x1="{xh:.1f}" y1="{Y0p}" x2="{xh:.1f}" y2="{Y0p - Hp*0.707:.1f}" {S_("muted", 1, "4 4")}/>'
b += text(xh + 6, Y0p - 8, f't = {HALF}', 'muted', 14)
b += text(X0p + Wp - 2, Y0p + 40, 't', 'muted', 15, 'end', italic=True)
figs['fig4'] = fig(480, 270, 'DDPM 线性调度下原图系数与噪声系数随 t 的变化', b,
                   f'图 4　DDPM 的真实调度（T = 1000，β 从 10⁻⁴ 线性增到 0.02）。蓝线一路降到 {f(math.sqrt(AB[1000]), 4)}，橙线升到接近 1；两条线在 t = {HALF} 附近交叉。')

# 图 5：前向加噪的一群点
def panels(groups, title_fn, col='accent', lim=1.6, w=480, h=150, extra=None):
    n = len(groups); cw = w / n; u = (cw / 2 - 8) / lim
    b = ''
    for i, g in enumerate(groups):
        ox = cw * i + cw / 2; oy = 74
        pl = Plane(ox, oy, u, lim, labels=False)
        b += pl.b
        for x in g['xs']:
            if pl.inside(x): b += dot_(*pl.p(x), col, 1.6, 0.6)
        b += text(ox, oy + lim * u + 22, title_fn(g), 'fg', 14, 'middle')
        if extra: b += extra(g, ox, oy + lim * u + 42)
    return b
b = panels(MC['forward'], lambda g: f't = {g["t"]}', 'accent')
figs['fig5'] = fig(480, 190, '300 张图在 t 等于 0、100、250、500、1000 时的样子', b,
                   '图 5　300 张训练图一起加噪。t = 250 时两团已经糊在一起；t = 1000 时几乎就是一团标准正态噪声，看不出原来有两团。')

# 图 6：训练一步：x0、ε、x3，以及猜的 ε̂
pl = Plane(160, 160, 105, 1.35)
b = pl.b
p0, p3 = pl.p(X0), pl.p(X3)
pm = pl.p(sc(sa3, X0))
b += dot_(*p0, 'accent', 6) + text(p0[0] + 8, p0[1] + 22, 'x₀', 'accent', 15)
b += arrow(*p0, *pm, 'muted', 2) + text(pm[0] + 12, pm[1] - 2, '× 0.6', 'muted', 14)
b += arrow(*pm, *p3, 'warn', 2.6) + text((pm[0] + p3[0]) / 2 - 4, (pm[1] + p3[1]) / 2 + 26, '+ 0.8 ε', 'warn', 15, 'middle', halo=True)
b += dot_(*p3, 'fg', 5) + text(p3[0] - 10, p3[1] - 12, 'x₃', 'fg', 15, 'end', halo=True)
# 右侧：ε 与 ε̂ 画在以原点为起点的小坐标里
q = Plane(390, 120, 52, 1.35, labels=False)
b += q.b
b += arrow(q.ox, q.oy, *q.p(EPS), 'warn', 2.6) + text(q.p(EPS)[0] - 4, q.p(EPS)[1] - 10, 'ε', 'warn', 16, 'end', italic=True)
b += arrow(q.ox, q.oy, *q.p(EH), 'ok', 2.6) + ehat(q.p(EH)[0] + 2, q.p(EH)[1] + 20, 'ok', 16)
b += f'<line x1="{q.p(EPS)[0]:.1f}" y1="{q.p(EPS)[1]:.1f}" x2="{q.p(EH)[0]:.1f}" y2="{q.p(EH)[1]:.1f}" {S_("muted", 1.5, "4 3")}/>'
b += text(390, 216, '真实噪声 ε 与', 'muted', 14, 'middle') + text(390, 236, '网络猜的噪声（绿）', 'muted', 14, 'middle')
b += text(390, 262, f'损失 = 虚线长度² = {f(LOSS_EH, 3)}', 'fg', 14, 'middle')
figs['fig6'] = fig(480, 310, '训练的一步：从 x0 加噪得到 x3，网络从 x3 猜噪声', b,
                   '图 6　左：x₀ 乘 0.6、再加 0.8 ε，得到 x₃。右：网络只看到 x₃ 和 t = 3，猜出绿色的噪声；它和真实噪声 ε（橙）的差，平方后就是损失。')

# 图 7：最好的猜法是平均
pl = Plane(160, 160, 105, 1.35)
b = pl.b
for mu, col, name, dy in ((MU_A, 'accent', '左边亮那团缩小后', 34), (MU_B, 'accent', '右边亮那团缩小后', -26)):
    c = pl.p(sc(sa3, mu)); rr = 2 * math.sqrt(ab3 * SD * SD + 1 - ab3) * pl.u * 0.35
    b += f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="5" style="fill:var(--accent)"/>'
    b += text(c[0], c[1] + dy, name, 'accent', 13, 'middle', halo=True)
p3 = pl.p(X3)
b += arrow(*pl.p(sc(sa3, MU_A)), *p3, 'muted', 1.5, '4 3') + arrow(*pl.p(sc(sa3, MU_B)), *p3, 'muted', 1.5, '4 3')
b += dot_(*p3, 'fg', 5) + text(p3[0] - 10, p3[1] + 22, 'x₃', 'fg', 15, 'end', halo=True)
# 右：两种猜法与加权平均
q = Plane(390, 120, 52, 1.35, labels=False)
b += q.b
b += arrow(q.ox, q.oy, *q.p(EA), 'muted', 2) + text(q.p(EA)[0] - 2, q.p(EA)[1] - 8, '左', 'muted', 14, 'middle')
b += arrow(q.ox, q.oy, *q.p(EB), 'muted', 2) + text(q.p(EB)[0] + 12, q.p(EB)[1] + 6, '右', 'muted', 14, 'middle')
b += arrow(q.ox, q.oy, *q.p(EH), 'ok', 2.8) + ehat(q.p(EH)[0] - 8, q.p(EH)[1] + 18, 'ok', 16, 'end')
b += text(390, 218, f'左：若来自左边亮 ×{pct(ROWS[0]["r"])}', 'muted', 13, 'middle') + text(390, 240, f'右：若来自右边亮 ×{pct(ROWS[1]["r"])}', 'muted', 13, 'middle') + text(390, 266, '绿 = 两者加权', 'ok', 14, 'middle')
figs['fig7'] = fig(480, 310, '只看 x3 分不清它来自哪一团，最好的猜法是两种猜法的加权平均', b,
                   f'图 7　x₃ 离「右边亮」那团缩小后的中心更近，所以从 x₃ 看，它来自右边亮的可能性是 {pct(ROWS[1]["r"])}。最好的猜法（绿）是两种猜法按可能性加权的平均。')

# 图 8：往回走一步
pl = Plane(170, 160, 120, 1.15)
b = pl.b
p3, pt, pth, p2 = pl.p(X3), pl.p(MU_TRUE), pl.p(MU_TH), pl.p(X2)
b += dot_(*pl.p(X0), 'accent', 5) + text(pl.p(X0)[0] + 8, pl.p(X0)[1] + 20, 'x₀', 'accent', 15)
b += dot_(*p3, 'fg', 5) + text(p3[0] - 10, p3[1] + 20, 'x₃', 'fg', 15, 'end', halo=True)
b += arrow(*p3, *pt, 'warn', 2, '5 4') + dot_(*pt, 'warn', 4) + text(pt[0] + 8, pt[1] - 8, '用真实 ε 算的均值', 'warn', 13, 'start', halo=True)
b += arrow(*p3, *pth, 'ok', 2.6) + dot_(*pth, 'ok', 4) + text(pth[0], pth[1] - math.sqrt(BT)*pl.u - 8, '用猜的噪声算的均值', 'ok', 13, 'middle', halo=True)
b += f'<circle cx="{pth[0]:.1f}" cy="{pth[1]:.1f}" r="{math.sqrt(BT)*pl.u:.1f}" style="fill:var(--ok);fill-opacity:0.08;stroke:var(--ok);stroke-width:1;stroke-dasharray:3 3"/>'
b += arrow(*pth, *p2, 'muted', 1.8) + dot_(*p2, 'fg', 4) + text(p2[0] + 8, p2[1] + 18, 'x₂', 'fg', 15, 'start', halo=True)
b += text(340, 60, '绿色虚线圈：', 'muted', 14) + text(340, 80, '加新噪声 σz 的范围', 'muted', 14) + text(340, 100, f'（半径 σ = {f(math.sqrt(BT), 3)}）', 'muted', 14)
figs['fig8'] = fig(480, 320, '从 x3 往回走一步到 x2', b,
                   '图 8　从 x₃ 往回走一步。绿色：用网络猜的噪声算出的均值，再加一点新噪声 σz 得到 x₂；橙色虚线：如果知道真实噪声，均值会落在这里，离 x₀ 更近。')

# 图 9：从噪声画出一群点
b = panels(MC['reverse'], lambda g: f't = {g["t"]}', 'ok')
figs['fig9'] = fig(480, 190, '300 个点从纯噪声出发，往回走 1000 步，在各时刻的样子', b,
                   '图 9　300 个点从纯噪声出发，每步用解析最优的猜测往回走（DDPM，1000 步）。走到 t = 0，点又聚回了两团。')

# 图 10：步数与质量
X0p, Y0p, Wp, Hp = 64, 210, 300, 170
b = f'<line x1="{X0p}" y1="{Y0p}" x2="{X0p+Wp}" y2="{Y0p}" {S_("line", 1.5)}/><line x1="{X0p}" y1="{Y0p}" x2="{X0p}" y2="{Y0p-Hp-6}" {S_("line", 1.5)}/>'
lx = lambda st: X0p + Wp * math.log10(st) / 3
for st in (1, 10, 100, 1000):
    b += text(lx(st), Y0p + 20, str(st), 'muted', 14, 'middle')
for v in (0, 0.5, 1):
    b += text(X0p - 8, Y0p - Hp * v + 5, f'{int(v*100)}%', 'muted', 14, 'end')
b += f'<line x1="{X0p}" y1="{Y0p - Hp*MC["q_true"]:.1f}" x2="{X0p+Wp}" y2="{Y0p - Hp*MC["q_true"]:.1f}" {S_("muted", 1, "4 4")}/>'
b += text(X0p + Wp + 4, Y0p - Hp * MC['q_true'] + 18, f'真实数据 {pct(MC["q_true"], 0)}', 'muted', 13, 'end')
for key, col, dash in (('q_ddpm', 'accent', None), ('q_ddim', 'ok', None)):
    ps = ' '.join(f'{lx(st):.1f},{Y0p - Hp*q:.1f}' for st, q in zip(MC['steps'], MC[key]))
    b += f'<polyline points="{ps}" {S_(col, 2.4, dash)}/>'
    for st, q in zip(MC['steps'], MC[key]): b += dot_(lx(st), Y0p - Hp * q, col, 3)
b += text(lx(3) + 28, Y0p - Hp * 0.18 + 4, 'DDPM', 'accent', 14) + text(lx(5) - 12, Y0p - Hp * 0.70 - 6, 'DDIM', 'ok', 14, 'end')
b += text(X0p + Wp / 2, Y0p + 42, '采样步数（网络调用次数）', 'muted', 14, 'middle')
b += text(X0p + Wp / 2, 18, '落在某一团里的点所占比例', 'muted', 14, 'middle')
# 右侧三个小图
for i, g in enumerate(MC['panels']):
    oy = 40 + i * 64; ox = 428; u = 26 / 1.3
    pp = Plane(ox, oy, u, 1.3, labels=False); b += pp.b
    for x in g['xs']:
        if pp.inside(x): b += dot_(*pp.p(x), 'ok', 1.2, 0.6)
    b += text(ox - 36, oy + 5, f'{g["st"]} 步', 'fg', 13, 'end')
figs['fig10'] = fig(480, 270, '采样步数与生成质量的关系，以及 1、5、50 步时生成的点', b,
                    '图 10　步数越少越快，但太少就画不好。1 步时所有点都挤在中间（两团的平均），5 步时还很散，10 步以上就接近真实数据。右边是 DDIM 走 1、5、50 步画出的 300 个点。')

# 图 11：潜空间
b = ''
def box(x, y, w, h, label, sub_, col):
    return rect(x, y, w, h, 'paper', 6, col, 2) + text(x + w / 2, y + h / 2 - 2, label, col, 15, 'middle') + text(x + w / 2, y + h / 2 + 18, sub_, 'muted', 13, 'middle')
b += box(10, 50, 110, 110, '原图', '512 × 512 × 3', 'fg')
b += box(186, 80, 60, 60, '潜空间', '', 'accent') + text(216, 160, '64 × 64 × 4', 'muted', 13, 'middle')
b += box(330, 50, 110, 110, '生成的图', '512 × 512 × 3', 'fg')
b += arrow(122, 100, 182, 100, 'muted', 2) + text(152, 90, '编码器', 'muted', 13, 'middle')
b += arrow(250, 100, 326, 100, 'muted', 2) + text(288, 90, '解码器', 'muted', 13, 'middle')
b += f'<path d="M206 78 C 190 30, 242 30, 226 78" {S_("ok", 2)}/>' + text(216, 30, '扩散在这里做', 'ok', 14, 'middle')
b += text(65, 190, f'{PIX:,} 个数', 'fg', 14, 'middle') + text(216, 190, f'{LAT:,} 个数', 'accent', 14, 'middle')
b += text(240, 222, f'少了 {PIX // LAT} 倍：每 8 × 8 × 3 = 192 个数压成 4 个数', 'muted', 14, 'middle')
figs['fig11'] = fig(480, 240, '潜空间扩散：编码器把图压成 64 乘 64 乘 4，扩散在小图上做，解码器再还原', b,
                    '图 11　潜空间扩散（Stable Diffusion 的尺寸）。训练和采样都在中间那张小「图」上做，只有最后一步用解码器还原成像素。')

# 图 12：交叉注意力
b = ''
b += text(110, 24, '潜空间的位置（出 q）', 'accent', 14, 'middle')
for r in range(4):
    for c in range(4):
        b += rect(50 + c * 30, 36 + r * 30, 26, 26, 'accent' if (r, c) == (1, 2) else 'paper', 3, 'accent', 1, 0.9 if (r, c) == (1, 2) else None)
b += text(110, 172, '64 × 64 = 4096 个位置', 'muted', 13, 'middle')
b += text(360, 24, '文字 token（出 k、v）', 'warn', 14, 'middle')
for i, tok in enumerate(CA_TOK):
    y = 40 + i * 40
    b += rect(320, y, 80, 30, 'paper', 5, 'warn', 1.5) + text(360, y + 21, tok, 'fg', 15, 'middle')
    b += text(412, y + 21, pct(CA_W[i]), 'warn', 15, 'start', weight=600)
    sx, sy = 50 + 2 * 30 + 26, 36 + 30 + 13
    b += f'<line x1="{sx}" y1="{sy}" x2="318" y2="{y+15}" style="stroke:var(--warn);stroke-width:{1 + 6*CA_W[i]:.1f};stroke-opacity:0.7"/>'
b += text(360, 172, '最多 77 个 token', 'muted', 13, 'middle')
b += text(240, 206, '每个位置用自己的 q 去和每个文字 token 的 k 打分，按份额取 v', 'muted', 13, 'middle')
figs['fig12'] = fig(480, 222, '交叉注意力：潜空间的每个位置去看文字 token', b,
                    '图 12　交叉注意力。蓝色那个位置的 q，和三个文字 token 的 k 打分，softmax 后的份额写在右边（线越粗分得越多）。')

# 图 13：guidance 在 x3 处把 x̂0 往外推
pl = Plane(200, 160, 52, 2.9)
b = pl.b
b += dot_(*pl.p(MU_A), 'accent', 5) + text(pl.p(MU_A)[0] - 12, pl.p(MU_A)[1] + 5, '左边亮', 'accent', 13, 'end', halo=True)
b += dot_(*pl.p(MU_B), 'accent', 5) + text(pl.p(MU_B)[0] - 8, pl.p(MU_B)[1] - 8, '右边亮', 'accent', 13, 'end')
b += f'<rect x="{pl.p((-1,1))[0]:.1f}" y="{pl.p((-1,1))[1]:.1f}" width="{2*pl.u:.1f}" height="{2*pl.u:.1f}" style="fill:none;stroke:var(--muted);stroke-width:1;stroke-dasharray:4 3"/>'
b += text(pl.p((1, 1))[0] - 4, pl.p((1, 1))[1] - 6, '像素范围', 'muted', 12, 'end')
xs_ = [CFG[s][1] for s in CFG_S]
b += f'<line x1="{pl.p(xs_[0])[0]:.1f}" y1="{pl.p(xs_[0])[1]:.1f}" x2="{pl.p(xs_[2])[0]:.1f}" y2="{pl.p(xs_[2])[1]:.1f}" {S_("line", 1.5)}/>'
cols = {0: 'muted', 1: 'ok', 3: 'warn', 7.5: 'warn'}
for s in CFG_S:
    x = CFG[s][1]
    if not pl.inside(x): continue
    pp = pl.p(x); b += dot_(*pp, cols[s], 5)
    b += text(pp[0] + 10, pp[1] + (5 if s == 1 else (18 if s else -10)), f's = {s}', cols[s], 14, 'start', halo=True)
b += text(360, 60, '在 x₃ 这一步', 'muted', 14) + text(360, 82, '网络猜的原图：', 'muted', 14)
for i, s in enumerate(CFG_S[:3]):
    b += text(360, 112 + i * 24, f's = {s}：{vtxt(CFG[s][1], 2)}', cols[s], 14)
s75 = CFG[7.5][1]
b += text(360, 112 + 3 * 24, f's = 7.5：{vtxt(s75, 1)}', 'warn', 14) + text(360, 112 + 4 * 24, '（出了画面）', 'muted', 13)
figs['fig13'] = fig(480, 320, 'guidance scale 越大，网络猜的 x0 越往左边亮的方向外推', b,
                    '图 13　同一个 x₃，不同的 guidance scale s 下网络猜出的原图。s = 0 是不看文字（两团中间偏右边亮），s = 1 落在左边亮那团，s 再大就沿同一个方向冲出像素范围（虚线框）。')

# 图 14：guidance 的采样结果
def cfg_extra(g, ox, y):
    return text(ox, y, f'散布 {f(g["sd"], 2)}', 'muted', 13, 'middle')
b = panels(MC['cfg'], lambda g: f's = {g["s"]}', 'ok', lim=1.6, h=190, extra=cfg_extra)
# 每个小图画一条 x = y 的分界线
n = len(MC['cfg']); cw = 480 / n; u = (cw / 2 - 8) / 1.6
for i in range(n):
    ox = cw * i + cw / 2
    b += f'<line x1="{ox - 1.6*u:.1f}" y1="{74 + 1.6*u:.1f}" x2="{ox + 1.6*u:.1f}" y2="{74 - 1.6*u:.1f}" {S_("muted", 1, "3 3")}/>'
figs['fig14'] = fig(480, 210, '重叠的两团上，guidance scale 为 0、1、3、7.5 时生成的点', b,
                    f'图 14　换成两团互相重叠的数据，条件是「左边亮」（虚线右下方）。s = 0 时一半落错边；s = 1 时 {MC["cfg"][1]["left"]*100:.1f}% 落在右下方；s 越大，点越集中、越往外跑。')

# 图 15：页内小网络的训练曲线
X0p, Y0p, Wp, Hp = 60, 200, 380, 160
b = f'<line x1="{X0p}" y1="{Y0p}" x2="{X0p+Wp}" y2="{Y0p}" {S_("line", 1.5)}/><line x1="{X0p}" y1="{Y0p}" x2="{X0p}" y2="{Y0p-Hp-6}" {S_("line", 1.5)}/>'
ymax = 1.0
for v in (0, 0.5, 1.0): b += text(X0p - 8, Y0p - Hp * v / ymax + 5, f(v, 1), 'muted', 14, 'end')
for st in (0, 500, 1000, 1500): b += text(X0p + Wp * st / 1500, Y0p + 20, str(st), 'muted', 14, 'middle')
ps = ' '.join(f'{X0p + Wp*s/1500:.1f},{Y0p - Hp*min(v, ymax)/ymax:.1f}' for s, v in MC['train'])
b += f'<polyline points="{ps}" {S_("ok", 2.4)}/>'
yf = Y0p - Hp * MC['floor'] / ymax
b += f'<line x1="{X0p}" y1="{yf:.1f}" x2="{X0p+Wp}" y2="{yf:.1f}" {S_("muted", 1.2, "5 4")}/>'
b += text(X0p + Wp - 4, yf + 20, f'解析最优的损失 {f(MC["floor"], 3)}', 'muted', 14, 'end')
b += text(X0p + 60, Y0p - Hp * 0.75, '小网络的损失', 'ok', 14)
b += text(X0p + Wp / 2, Y0p + 42, '训练步数', 'muted', 14, 'middle')
figs['fig15'] = fig(480, 260, '一个小网络的训练损失随步数下降，停在解析最优损失上方', b,
                    f'图 15　在两团数据上真的训练一个小网络（实验 02 里能重跑）。损失降到 {f(MC["train"][-1][1], 3)} 附近就不再明显下降：它的下面有一条线 {f(MC["floor"], 3)}，那是最好的猜法也躲不掉的损失。')

# ———— 写文章 ————
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
def repl(m):
    k = m.group(1)
    if k not in N: raise KeyError(k)
    return N[k]
src = re.sub(r'\{\{n:([A-Za-z0-9_]+)\}\}', repl, src)
left = re.findall(r'\{\{[^}]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/diffusion-models.md').write_text(src, encoding='utf-8')

# ———— 组装实验页 ————
lab = (HERE / 'lab.src.html').read_text(encoding='utf-8')
core = (HERE / 'core.js').read_text(encoding='utf-8')
assert '/*__CORE__*/' in lab
lab = lab.replace('/*__CORE__*/', core)
out = ROOT / 'public/labs/diffusion-models/index.html'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(lab, encoding='utf-8')

print('E3', _E3); print('XS', [vtxt(x, 4) for x in XS]); print('X3', X3, 'back', X0_BACK)
print('rows', [(r['d2'], r['r'], r['e']) for r in ROWS]); print('EH', EH, 'loss', LOSS_EH, LOSS_EA)
print('BT', BT, 'mu_post', MU_POST, MU_POST2, 'mu_true', MU_TRUE, 'mu_th', MU_TH, 'x2', X2)
print('x0h', X0H, 'x1ddim', X1_DDIM); print('cfg', {s: CFG[s] for s in CFG_S})
print('ca', CA_S, CA_W, CA_OUT); print('half', HALF, AB[1000]); print('fm', FM_X, FM_V)
print('ok')
