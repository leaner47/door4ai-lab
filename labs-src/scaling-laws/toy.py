"""Scaling Laws 一讲的贯穿算例：文章分镜图、文中数字与实验页共用这组数。
运行：python3 labs-src/scaling-laws/toy.py
  → 生成 src/content/blog/scaling-laws.md（把 article.src.md 里的 {{figN}} 与 {{n:名字}} 填好）
  → 写出 labs-src/scaling-laws/toy.json（实验页开头的 TOY 常量抄的就是它）
"""
import math, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# ———— 第一部分：一层 y = W x，数乘法和加法 ————
X = [1, 2, 3]
W = [[1, 0, 2], [0, 1, 1]]
Y = [sum(W[i][j] * X[j] for j in range(3)) for i in range(2)]          # (7, 5)
G = [1, -1]                                                              # 上游梯度 ∂L/∂y
DX = [sum(W[i][j] * G[i] for i in range(2)) for j in range(3)]           # Wᵀ g
DW = [[G[i] * X[j] for j in range(3)] for i in range(2)]                 # g xᵀ
NPAR = 6

# ———— 第二部分：6ND 与卡时（Llama-3-8B） ————
H100 = 989.5e12          # H100 SXM BF16 稠密峰值（数据表 1979 TFLOPS 含稀疏，稀疏去掉减半）
V100 = 125e12            # V100 Tensor Core FP16 峰值
N8, D8 = 8.03e9, 15e12
C8 = 6 * N8 * D8
HOURS_100 = C8 / H100 / 3600
MFU = 0.40
HOURS_40 = HOURS_100 / MFU
REPORT8 = 1.3e6
EFF8 = HOURS_100 / REPORT8
# 注意力那一项（Kaplan 式 2·n_layer·n_ctx·d）：Llama-3-8B 32 层、8192 上下文、4096 维
ATT8 = 2 * 32 * 8192 * 4096

# ———— 第三部分：Kaplan 的幂律 L(N) = (N_c / N)^α ————
KA, KNC = 0.076, 8.8e13
kL = lambda n: (KNC / n) ** KA

# ———— 第四部分：Chinchilla 的损失公式（Besiroglu 等 2024 重新拟合的系数） ————
E, A, B, AL, BE = 1.8172, 482.01, 2085.43, 0.3478, 0.3658
E0, A0, B0, AL0, BE0 = 1.6934, 406.4, 410.7, 0.3392, 0.2849        # Hoffmann 等原文
L = lambda n, d: E + A / n ** AL + B / d ** BE
CB = 5.76e23                                                         # Gopher / Chinchilla 的算力
def opt(C, e=E, a=A, b=B, al=AL, be=BE):
    g = (al * a / (be * b)) ** (1 / (al + be))
    n = g * (C / 6) ** (be / (al + be)); return n, C / 6 / n
GG = (AL * A / (BE * B)) ** (1 / (AL + BE))
NOPT, DOPT = opt(CB)
NOPT0, DOPT0 = opt(CB, E0, A0, B0, AL0, BE0)
EXPN = BE / (AL + BE); EXPD = AL / (AL + BE)
OPTS = [('Gopher', 280e9), ('Chinchilla', 70e9), ('8B', 8e9)]
OPTROWS = [(nm, n, CB / 6 / n, L(n, CB / 6 / n), A / n ** AL, B / (CB / 6 / n) ** BE) for nm, n in OPTS]

# ———— 第五部分：把推理算进去 ————
TGT = L(N8, D8)
def dtr(n, tgt=TGT):
    r = tgt - E - A / n ** AL
    return None if r <= 0 else (B / r) ** (1 / BE)
def life(dinf):
    best = None
    for i in range(4000):
        n = 10 ** (9 + i * 0.00075)
        d = dtr(n)
        if d is None: continue
        c = 6 * n * d + 2 * n * dinf
        if best is None or c < best[0]: best = (c, n, d)
    return best
DINFS = [0, 1e12, 1e13, 1e14]
LIFE = [life(x) for x in DINFS]
NMIN = (A / (TGT - E)) ** (1 / AL)          # 只靠无限多数据也到不了目标的最小模型

# ———— 第六部分：涌现（示意） ————
EM_C, EM_K = None, None
# 每个答案 token 的损失 ℓ(N) = c·N^(−k)，取 ℓ(1e8)=1.2、ℓ(1e11)=0.02
EM_K = math.log10(1.2 / 0.02) / 3
EM_C = 1.2 * (1e8) ** EM_K
ptok = lambda n: math.exp(-EM_C * n ** (-EM_K))
ALEN = 5

# ———— 第七部分：公开模型 ————
MODELS = [  # 名字, N, D, 报告的 C（None = 未单独给）, 卡时, 卡型峰值, 卡名
    ('GPT-3', 175e9, 300e9, 3.14e23, 10000 * 14.8 * 24, V100, 'V100'),
    ('Gopher', 280e9, 300e9, 5.76e23, None, None, 'TPU v3'),
    ('Chinchilla', 70e9, 1.4e12, 5.76e23, None, None, 'TPU v3/v4'),
    ('Llama-3-8B', N8, 15e12, None, 1.3e6, H100, 'H100'),
    ('Llama-3-70B', 70.6e9, 15e12, None, 6.4e6, H100, 'H100'),
    ('Llama-3.1-405B', 405e9, 15.6e12, 3.8e25, 30.84e6, H100, 'H100'),
]

# ———— 数字格式 ————
def sci(v, k=2):
    """公式里用：3.14 \\times 10^{23}"""
    e = math.floor(math.log10(abs(v))); m = v / 10 ** e
    if round(m, k) >= 10: m /= 10; e += 1
    return f'{m:.{k}f} \\times 10^{{{e}}}'
def sct(v, k=2):
    """正文里用：3.14 × 10²³"""
    sup = str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹')
    e = math.floor(math.log10(abs(v))); m = v / 10 ** e
    if round(m, k) >= 10: m /= 10; e += 1
    return f'{m:.{k}f} × 10<sup>{e}</sup>'
def big(v):
    for u, s in ((1e12, 'T'), (1e9, 'B'), (1e6, 'M')):
        if v >= u: return f'{v/u:.3g}{s}'
    return f'{v:.3g}'
f3 = lambda v: f'{v:.3f}'
f4 = lambda v: f'{v:.4f}'
pt = lambda v: f'{v*100:.1f}%'
pc = lambda v: f'{v*100:.1f}\\%'
wan = lambda h: f'{h/1e4:.1f} 万'

N = {
    'y0': str(Y[0]), 'y1': str(Y[1]), 'dx0': str(DX[0]), 'dx1': str(DX[1]), 'dx2': str(DX[2]),
    'C8': sci(C8), 'C8t': sct(C8), 'h100': f'{HOURS_100:,.0f}', 'h40': f'{HOURS_40:,.0f}', 'h100m': f'{HOURS_100:,.0f}'.replace(',', '{,}'), 'h40m': f'{HOURS_40:,.0f}'.replace(',', '{,}'),
    'h100w': wan(HOURS_100), 'h40w': wan(HOURS_40), 'eff8': pt(EFF8), 'eff8pc': pc(EFF8),
    'h100s': sci(C8 / H100), 'att8': sci(ATT8), 'att8pct': pt(ATT8 / (2 * N8)), 'twoN8': sci(2 * N8),
    'k9': f'{kL(1e9):.3f}', 'k10': f'{kL(1e10):.3f}', 'k11': f'{kL(1e11):.3f}', 'kr': f'{10**-KA:.3f}', 'kdrop': pt(1 - 10**-KA),
    'k2': f'{2**-KA:.3f}', 'k2drop': pt(1 - 2**-KA),
    'ln9': f'{math.log(kL(1e9)):.4f}', 'ln10': f'{math.log(kL(1e10)):.4f}', 'lnN9': f'{math.log(1e9):.3f}', 'lnN10': f'{math.log(1e10):.3f}',
    'slope': f'{(math.log(kL(1e10)) - math.log(kL(1e9))) / (math.log(1e10) - math.log(1e9)):.3f}',
    'gg': f'{GG:.4f}', 'expn': f'{EXPN:.3f}', 'expd': f'{EXPD:.3f}',
    'nopt': big(NOPT), 'dopt': big(DOPT), 'ratio': f'{DOPT/NOPT:.1f}', 'lopt': f4(L(NOPT, DOPT)),
    'nopts': sci(NOPT), 'dopts': sci(DOPT), 'c6': sci(CB / 6), 'c6pow': sci((CB/6)**EXPN, 3),
    'ratio0': f'{DOPT0/NOPT0:.0f}', 'nopt0': big(NOPT0),
    'x10n': f'{10**EXPN:.2f}', 'x10d': f'{10**EXPD:.2f}',
    'tgt': f4(TGT), 'nmin': big(NMIN),
    'c8vscb': f'{C8/CB:.2f}',
    'tpp8': f'{D8/N8:.0f}', 'tpp8x': f'{D8/N8/20:.0f}',
}
for i, (nm, n, d, l, tn, td) in enumerate(OPTROWS):
    N.update({f'o{i}n': big(n), f'o{i}d': big(d), f'o{i}r': f'{d/n:.0f}' if d / n >= 10 else f'{d/n:.1f}',
              f'o{i}l': f4(l), f'o{i}tn': f4(tn), f'o{i}td': f4(td), f'o{i}ds': sci(d)})
N['dl8'] = f4(OPTROWS[2][3] - OPTROWS[1][3]); N['dlg'] = f4(OPTROWS[0][3] - OPTROWS[1][3])
for i, (dinf, (c, n, d)) in enumerate(zip(DINFS, LIFE)):
    N.update({f'f{i}n': big(n), f'f{i}d': big(d), f'f{i}r': f'{d/n:,.0f}', f'f{i}c': sci(c), f'f{i}tr': sct(6 * n * d), f'f{i}inf': sct(2 * n * dinf) if dinf else '0'})
c8life = [6 * N8 * D8 + 2 * N8 * x for x in DINFS]
N['f3c8'] = sci(c8life[3]); N['f3save'] = pt(1 - LIFE[3][0] / c8life[3])
N['f0c8'] = sci(c8life[0]); N['f0x'] = f'{c8life[0] / LIFE[0][0]:.1f}'
N['inf8'] = sci(2 * N8); N['inf70'] = sci(2 * 70.6e9); N['infr'] = f'{70.6/8.03:.1f}'
for nn in (1e8, 1e9, 1e10, 1e11):
    k = f'{int(math.log10(nn))}'
    N['pt' + k] = f3(ptok(nn)); N['pe' + k] = f3(ptok(nn) ** ALEN); N['pep' + k] = pt(ptok(nn) ** ALEN); N['ptp' + k] = pt(ptok(nn))
# 模型表
rows = []
for nm, n, d, crep, hrs, peak, card in MODELS:
    c6 = 6 * n * d
    eff = f'{c6 / (hrs * 3600 * peak) * 100:.0f}%' if hrs else '—'
    rows.append(f'| {nm} | {big(n)} | {big(d)} | {(f"{d/n:,.0f}" if d/n>=10 else f"{d/n:.1f}")} | ${sci(c6)}$ | {("$" + sci(crep) + "$") if crep else "—"} | {(f"{hrs/1e6:.2f}M {card}") if hrs else f"未公开（{card}）"} | {eff} |')
N['mtable'] = '\n'.join(rows)
for nm, n, d, crep, hrs, peak, card in MODELS:
    key = re.sub(r'[^a-z0-9]', '', nm.lower())
    N[key + 'c'] = sci(6 * n * d); N[key + 'r'] = f'{d/n:,.0f}' if d / n >= 10 else f'{d/n:.1f}'
    if hrs: N[key + 'eff'] = pt(6 * n * d / (hrs * 3600 * peak))
N['gpt3h'] = f'{10000*14.8*24:,.0f}'

# ———— SVG 小工具：颜色只用 CSS 变量 ————
def C_(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    body = esc(s)
    m = re.fullmatch(r'10\^(-?\d+)', s)
    if m: body = f'10<tspan font-size="{size*0.72:.1f}" dy="-7">{m.group(1)}</tspan>'
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C_(col)}>{body}</text>'
def mtext(x, y, parts, col='fg', size=16, anchor='start'):
    """parts: [(文字, 'i'|'sub'|'sup'|'')]，变量斜体、下标用 baseline 偏移"""
    out = f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" {C_(col)}>'
    for s, k in parts:
        if k == 'i': out += f'<tspan font-style="italic">{esc(s)}</tspan>'
        elif k == 'sub': out += f'<tspan font-size="{size*0.72:.1f}" dy="4">{esc(s)}</tspan><tspan dy="-4"></tspan>'
        elif k == 'sup': out += f'<tspan font-size="{size*0.72:.1f}" dy="-7">{esc(s)}</tspan><tspan dy="7"></tspan>'
        else: out += esc(s)
    return out + '</text>'
def line(x1, y1, x2, y2, col='line', w=1.5, dash=None): return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {S_(col, w, dash)}/>'
def arrow(x1, y1, x2, y2, col, w=2.2):
    ang = math.atan2(y2-y1, x2-x1); Lh = 9; a = 0.42
    bx, by = x2 - Lh*math.cos(ang), y2 - Lh*math.sin(ang)
    p1 = (x2 - Lh*math.cos(ang-a), y2 - Lh*math.sin(ang-a)); p2 = (x2 - Lh*math.cos(ang+a), y2 - Lh*math.sin(ang+a))
    return line(x1, y1, bx, by, col, w) + f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C_(col)}/>'
def rect(x, y, w, h, col, rx=4): return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,1):.1f}" height="{h:.1f}" rx="{rx}" {C_(col)}/>'
def box(x, y, w, h, col, rx=6, sw=1.5): return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" style="fill:none;stroke:var(--{col});stroke-width:{sw}"/>'
def circ(x, y, r, col, fill=True): return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" ' + (C_(col) if fill else S_(col, 2)) + '/>'
def path(pts, col, w=2.5, dash=None): return '<path d="' + ' '.join(('M' if i == 0 else 'L') + f'{x:.1f} {y:.1f}' for i, (x, y) in enumerate(pts)) + f'" {S_(col, w, dash)}/>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
SUP = str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹')
def p10(e): return f'10^{e}'

class Ax:
    """坐标轴：x、y 可以分别取对数"""
    def __init__(s, x0, y0, w, h, xr, yr, xlog=False, ylog=False):
        s.x0, s.y0, s.w, s.h, s.xr, s.yr, s.xlog, s.ylog = x0, y0, w, h, xr, yr, xlog, ylog
    def X(s, v):
        a, b = s.xr
        if s.xlog: v, a, b = math.log10(v), math.log10(a), math.log10(b)
        return s.x0 + (v - a) / (b - a) * s.w
    def Y(s, v):
        a, b = s.yr
        if s.ylog: v, a, b = math.log10(v), math.log10(a), math.log10(b)
        return s.y0 + s.h - (v - a) / (b - a) * s.h
    def frame(s):
        return line(s.x0, s.y0 + s.h, s.x0 + s.w, s.y0 + s.h, 'muted', 1.2) + line(s.x0, s.y0, s.x0, s.y0 + s.h, 'muted', 1.2)
    def xt(s, v, lab, size=14):
        x = s.X(v); return line(x, s.y0 + s.h, x, s.y0 + s.h + 5, 'muted', 1.2) + text(x, s.y0 + s.h + 21, lab, 'muted', size, 'middle')
    def yt(s, v, lab, size=14):
        y = s.Y(v); return line(s.x0 - 5, y, s.x0, y, 'muted', 1.2) + text(s.x0 - 8, y + 5, lab, 'muted', size, 'end')
    def grid_y(s, v): return line(s.x0, s.Y(v), s.x0 + s.w, s.Y(v), 'line', 1)
    def curve(s, f, col, a=None, b=None, n=160, w=2.5, dash=None):
        a = a or s.xr[0]; b = b or s.xr[1]; pts = []
        for i in range(n + 1):
            t = i / n
            v = 10 ** (math.log10(a) + t * (math.log10(b) - math.log10(a))) if s.xlog else a + t * (b - a)
            yv = f(v)
            if yv is None: continue
            pts.append((s.X(v), s.Y(yv)))
        return path(pts, col, w, dash)

figs = {}

# 图 1：前向 —— 6 条连线，每条一次乘一次加
def net(xs, ys, cols, labs_in, labs_out, edge_lab, edgecol='accent', back=False):
    b = ''
    xi, xo = 90, 390
    yi = [50, 120, 190]; yo = [85, 155]
    for i in range(2):
        for j in range(3):
            if back: b += arrow(xo - 24, yo[i], xi + 26, yi[j], edgecol, 1.6)
            else: b += arrow(xi + 24, yi[j], xo - 26, yo[i], edgecol, 1.6)
    for j in range(3):
        b += circ(xi, yi[j], 22, 'paper') + circ(xi, yi[j], 22, 'muted', False) + text(xi, yi[j] + 6, labs_in[j], cols[0], 17, 'middle')
    for i in range(2):
        b += circ(xo, yo[i], 22, 'paper') + circ(xo, yo[i], 22, 'muted', False) + text(xo, yo[i] + 6, labs_out[i], cols[1], 17, 'middle')
    for (i, j, s) in edge_lab:
        xm = xi + 24 + (xo - xi - 50) * 0.3; ym = yi[j] + (yo[i] - yi[j]) * 0.3
        b += rect(xm - 11, ym - 9, 22, 18, 'bg', 4) + text(xm, ym + 5, s, edgecol, 14, 'middle')
    return b
el = [(i, j, str(W[i][j])) for i in range(2) for j in range(3)]
b = net(None, None, ('fg', 'accent'), [str(v) for v in X], [str(v) for v in Y], el)
b += mtext(90, 236, [('x', 'i')], 'muted', 16, 'middle') + mtext(240, 236, [('W', 'i'), ('（6 个参数）', '')], 'accent', 16, 'middle') + mtext(390, 236, [('y', 'i'), (' = ', ''), ('W', 'i'), ('x', 'i')], 'muted', 16, 'middle')
figs['fig1'] = fig(480, 248, '一层 y = Wx 的前向：3 个输入、2 个输出、6 条连线', b,
                   f'图 1　前向：每条连线是一个参数，线上的数字是它的值。输入 (1, 2, 3) 沿 6 条线流到右边，得到 ({Y[0]}, {Y[1]})。每条线做一次乘法，再把乘积加进右边的和里。')

# 图 2：反向 —— 左：梯度沿原路传回输入；右：每个参数的梯度
b = ''
xi, xo = 60, 230; yi = [50, 115, 180]; yo = [82, 148]
for i in range(2):
    for j in range(3): b += arrow(xo - 22, yo[i], xi + 24, yi[j], 'warn', 1.5)
for j in range(3):
    b += circ(xi, yi[j], 20, 'paper') + circ(xi, yi[j], 20, 'muted', False) + text(xi, yi[j] + 6, str(DX[j]).replace('-', '−'), 'warn', 16, 'middle')
for i in range(2):
    b += circ(xo, yo[i], 20, 'paper') + circ(xo, yo[i], 20, 'muted', False) + text(xo, yo[i] + 6, str(G[i]).replace('-', '−'), 'warn', 16, 'middle')
b += text(145, 228, '① 传给上一层', 'warn', 15, 'middle')
gx, gy, cw, ch = 300, 70, 52, 44
for i in range(2):
    for j in range(3):
        b += box(gx + j * cw, gy + i * ch, cw - 4, ch - 4, 'warn', 5, 1.4) + text(gx + j * cw + (cw - 4) / 2, gy + i * ch + 27, str(DW[i][j]).replace('-', '−'), 'warn', 16, 'middle')
for j in range(3): b += text(gx + j * cw + 24, gy - 10, str(X[j]), 'muted', 14, 'middle')
for i in range(2): b += text(gx - 10, gy + i * ch + 27, str(G[i]).replace('-', '−'), 'muted', 14, 'end')
b += mtext(gx - 10, gy - 10, [('g', 'i'), ('＼', ''), ('x', 'i')], 'muted', 13, 'end')
b += text(gx + 76, 228, '② 每个参数的梯度', 'warn', 15, 'middle')
figs['fig2'] = fig(480, 240, '反向的两件事：把梯度传回输入，算出每个参数的梯度', b,
                   '图 2　反向：右边两个输出收到上游传来的梯度 (1, −1)。① 沿原来的 6 条线倒着走，每条线一次乘一次加，得到传给上一层的梯度 (1, −1, 1)；② 每个参数的梯度 = 它右端的梯度 × 它左端的输入，6 个参数各算一次。')

# 图 3：每个 token 的 6N 拆成三块 + 换成卡时
b = ''
parts = [('前向', 2, 'accent'), ('反向 ①', 2, 'warn'), ('反向 ②', 2, 'warn')]
x = 20; unit = 64
for i, (nm, k, col) in enumerate(parts):
    b += rect(x, 30, unit * k - 4, 34, col, 5)
    b += mtext(x + (unit * k - 4) / 2, 53, [('2', ''), ('N', 'i')], 'bg', 17, 'middle')
    b += text(x + (unit * k - 4) / 2, 88, nm, col, 15, 'middle')
    x += unit * k
b += mtext(x + 10, 53, [('= 6', ''), ('N', 'i')], 'fg', 18)
b += text(20, 20, '每个 token', 'muted', 14)
# 卡时条
ys = 124
mx = REPORT8
for i, (lab, h, col) in enumerate([('利用率 100%', HOURS_100, 'line'), ('利用率 40%', HOURS_40, 'accent'), ('官方报告', REPORT8, 'fg')]):
    y = ys + i * 40
    b += text(110, y + 19, lab, 'muted', 15, 'end')
    wv = 300 * h / mx
    b += rect(120, y, wv, 26, col, 4)
    b += text(120 + wv + 6, y + 19, f'{h/1e4:.1f} 万', 'muted' if col == 'line' else col, 15)
b += text(20, ys - 10, 'Llama-3-8B 的 H100 卡时', 'muted', 14)
figs['fig3'] = fig(480, ys + 3 * 40 + 4, '每个 token 的计算量 6N 和 Llama-3-8B 换算成的 H100 卡时', b,
                   f'图 3　上：每个 token 要算 6<i>N</i> 次浮点运算，前向 2<i>N</i>，反向两件事各 2<i>N</i>。下：Llama-3-8B 的 {N["C8t"]} 次运算换成 H100 卡时；官方报告的 130 万卡时，相当于平均只用上了峰值的 {pt(EFF8)}。')

# 图 4：Kaplan 幂律 —— 左普通坐标，右对数坐标
b = ''
a1 = Ax(46, 24, 160, 150, (0, 1e10), (1.5, 4.5))
b += a1.frame() + a1.curve(kL, 'accent', 1e6, 1e10, 400)
for v in (2, 3, 4): b += a1.yt(v, str(v))
b += a1.xt(0, '0') + a1.xt(5e9, '5B') + a1.xt(1e10, '10B')
b += mtext(126, 214, [('N', 'i'), ('（普通刻度）', '')], 'muted', 14, 'middle')
b += mtext(14, 16, [('L', 'i')], 'muted', 14)
a2 = Ax(296, 24, 160, 150, (1e6, 1e10), (1.5, 4.5), xlog=True, ylog=True)
b += a2.frame() + a2.curve(kL, 'accent')
for v in (2, 3, 4): b += a2.yt(v, str(v))
for e in (6, 8, 10): b += a2.xt(10 ** e, p10(e))
for nn in (1e9, 1e10):
    b += circ(a2.X(nn), a2.Y(kL(nn)), 4.5, 'warn')
b += text(a2.X(1e9) - 6, a2.Y(kL(1e9)) - 12, f'{kL(1e9):.2f}', 'warn', 14, 'end')
b += text(a2.X(1e10) - 2, a2.Y(kL(1e10)) - 12, f'{kL(1e10):.2f}', 'warn', 14, 'end')
b += mtext(376, 214, [('N', 'i'), ('（对数刻度）', '')], 'muted', 14, 'middle')
b += mtext(264, 16, [('L', 'i'), ('（对数刻度）', '')], 'muted', 14)
figs['fig4'] = fig(480, 222, '同一条幂律在普通坐标和对数坐标下', b,
                   f'图 4　同一条曲线 <i>L</i> = (<i>N</i><sub>c</sub>/<i>N</i>)<sup>0.076</sup>。左边是普通刻度：大部分变化挤在最左边，看不出规律。右边两个轴都取对数：变成一条直线，参数每乘 10，损失乘 {10**-KA:.3f}（橙色两点）。')

# 图 5：固定算力，拖 N —— 两项此消彼长，总和是 U 形
b = ''
ax = Ax(54, 22, 396, 196, (3e9, 1e12), (0, 0.36), xlog=True)
fn = lambda n: A / n ** AL
fd = lambda n: B / (CB / 6 / n) ** BE
b += ax.frame()
for v in (0, 0.1, 0.2, 0.3): b += ax.yt(v, f'{v:.1f}') + (ax.grid_y(v) if v else '')
for v, lab in ((1e10, '10B'), (1e11, '100B'), (1e12, '1T')): b += ax.xt(v, lab)
b += ax.curve(fn, 'muted', w=2, dash='5 4') + ax.curve(fd, 'warn', w=2, dash='5 4') + ax.curve(lambda n: fn(n) + fd(n), 'accent', w=3)
b += text(ax.X(9e11), ax.Y(fn(9e11)) - 10, '模型太小', 'muted', 14, 'end')
b += text(ax.X(3.3e9), ax.Y(fd(3.3e9)) - 10, '数据太少', 'warn', 14)
for nm, n, d, l, tn, td in OPTROWS:
    xx, yy = ax.X(n), ax.Y(tn + td)
    b += circ(xx, yy, 5, 'accent')
    lab = {'Gopher': f'Gopher 280B', 'Chinchilla': 'Chinchilla 70B', '8B': '8B'}[nm]
    b += text(xx, yy - 12, lab, 'fg', 14, 'middle')
b += mtext(14, 14, [('L', 'i'), (' − ', ''), ('E', 'i')], 'muted', 14)
b += mtext(252, 254, [('N', 'i'), ('（对数刻度）', '')], 'muted', 14, 'middle')
figs['fig5'] = fig(480, 262, '算力固定时，损失随参数量的 U 形曲线', b,
                   f'图 5　算力固定为 Gopher 的预算 {sct(CB)} FLOPs。横轴是参数量 <i>N</i>，数据量随之定为 <i>D</i> = <i>C</i>/(6<i>N</i>)。灰虚线是「模型太小」的那一项，橙虚线是「数据太少」的那一项，蓝线是两项之和。三个点是三种花法：最低的是 70B。')

# 图 6：把推理算进去 —— 最优模型随推理量变小
b = ''
ax = Ax(60, 26, 380, 170, (1e10, 1e15), (5e9, 5e10), xlog=True, ylog=True)
b += ax.frame()
for e in (10, 11, 12, 13, 14, 15): b += ax.xt(10 ** e, p10(e))
for v, lab in ((5e9, '5B'), (1e10, '10B'), (2e10, '20B'), (5e10, '50B')): b += ax.yt(v, lab)
pts = []
for i in range(41):
    di = 10 ** (10 + i * 5 / 40)
    c, n, d = life(di); pts.append((ax.X(di), ax.Y(n)))
b += path(pts, 'accent', 3)
b += line(ax.x0, ax.Y(N8), ax.x0 + ax.w, ax.Y(N8), 'warn', 1.4, '5 4') + text(ax.x0 + 6, ax.Y(N8) - 7, 'Llama-3-8B', 'warn', 14)
for di, (c, n, d) in zip(DINFS[1:], LIFE[1:]):
    xx, yy = ax.X(di), ax.Y(n)
    last = di == DINFS[-1]
    b += circ(xx, yy, 5, 'accent') + text(xx + (-8 if last else 8), yy - (16 if last else 9), f'{n/1e9:.1f}B · {d/n:,.0f} 个/参数', 'fg', 13, 'end' if last else 'start')
b += text(250, 236, '一生要服务的推理 token 数', 'muted', 14, 'middle')
b += text(12, 16, '最省的 N', 'muted', 14)
figs['fig6'] = fig(480, 244, '把推理算进总成本后，最省的模型大小随推理量变化', b,
                   f'图 6　目标是同一个损失（Llama-3-8B 的 {f4(TGT)}）。横轴是模型上线后一共要生成的 token 数，纵轴是训练 + 推理总运算最少的那个模型的大小。推理越多，最优模型越小、每个参数分到的训练 token 越多；到 10<sup>14</sup> 时最优就落在 8B 附近。')

# 图 7：涌现 —— 每个 token 平滑上升，整题全对像是突然出现
b = ''
ax = Ax(54, 22, 396, 180, (1e8, 1e12), (0, 1), xlog=True)
b += ax.frame()
for v in (0, 0.5, 1): b += ax.yt(v, f'{int(v*100)}%') + (ax.grid_y(v) if v else '')
for e in (8, 9, 10, 11, 12): b += ax.xt(10 ** e, p10(e))
b += ax.curve(ptok, 'accent', w=2.5) + ax.curve(lambda n: ptok(n) ** ALEN, 'warn', w=3)
b += text(ax.X(1e9) - 8, ax.Y(ptok(1e9)) - 6, '每个 token 对', 'accent', 14, 'end')
b += text(ax.X(3e9) + 10, ax.Y(ptok(3e9) ** ALEN) + 16, f'{ALEN} 个 token 全对', 'warn', 14)
b += mtext(252, 240, [('N', 'i'), ('（对数刻度，示意）', '')], 'muted', 14, 'middle')
figs['fig7'] = fig(480, 248, '同一组输出用两种度量：每个 token 的准确率平滑上升，整题全对看起来突然出现', b,
                   f'图 7　同一组模型、同一批输出（示意数字）。蓝线：每个答案 token 猜对的概率，随规模平滑上升。橙线：{ALEN} 个 token 全对才算对，即 <i>p</i><sup>{ALEN}</sup>；小模型时几乎是 0，到某个规模附近才「突然」升起来。')

# 图 8：公开模型 —— N 和 D 的散点，虚线是每参数 20 个 token
b = ''
ax = Ax(60, 22, 390, 220, (5e9, 1e12), (1e11, 3e13), xlog=True, ylog=True)
b += ax.frame()
for v, lab in ((1e10, '10B'), (1e11, '100B'), (1e12, '1T')): b += ax.xt(v, lab)
for v, lab in ((1e11, '100B'), (1e12, '1T'), (1e13, '10T')): b += ax.yt(v, lab)
for k, col, lab in ((20, 'ok', '20 个/参数'), (1, 'muted', '1 个/参数')):
    lo, hi = max(5e9, 1e11 / k), min(1e12, 3e13 / k)
    b += line(ax.X(lo), ax.Y(lo * k), ax.X(hi), ax.Y(hi * k), col, 1.5, '5 4')
b += text(ax.X(1.2e10), ax.Y(1.2e10 * 20) + 18, '20 个/参数', 'ok', 13)
b += text(ax.X(6e11) - 6, ax.Y(6e11) - 8, '1 个/参数', 'muted', 13, 'end')
off = {'GPT-3': (-8, 22, 'end'), 'Gopher': (8, 22, 'start'), 'Chinchilla': (8, 16, 'start'), 'Llama-3-8B': (8, 18, 'start'),
       'Llama-3-70B': (8, 18, 'start'), 'Llama-3.1-405B': (-8, -12, 'end')}
for nm, n, d, crep, hrs, peak, card in MODELS:
    xx, yy = ax.X(n), ax.Y(d)
    col = 'warn' if 'Llama' in nm else ('ok' if nm == 'Chinchilla' else 'accent')
    b += circ(xx, yy, 5.5, col)
    dx, dy, an = off[nm]
    r = d / n
    b += text(xx + dx, yy + dy, f'{nm} · {r:,.0f}' if r >= 10 else f'{nm} · {r:.1f}', col, 13, an)
b += mtext(255, 282, [('N', 'i'), ('（参数量）', '')], 'muted', 14, 'middle')
b += mtext(12, 14, [('D', 'i'), ('（训练 token）', '')], 'muted', 14)
figs['fig8'] = fig(480, 290, '公开模型的参数量与训练 token 数', b,
                   '图 8　六个公开模型，横轴参数量、纵轴训练 token 数，两个轴都是对数。点旁的数字是每个参数分到的 token。绿虚线是 Chinchilla 的「每参数 20 个」：GPT-3、Gopher 在它下面很远，Llama 3 全在它上面。')

# ———— 输出 ————
toy = {'x': X, 'W': W, 'g': G, 'H100': H100, 'V100': V100, 'kaplan': [KA, KNC],
       'fit': [E, A, B, AL, BE], 'fit0': [E0, A0, B0, AL0, BE0], 'CB': CB, 'tgt': TGT,
       'em': [EM_C, EM_K], 'models': [[m[0], m[1], m[2], m[3], m[4], m[6]] for m in MODELS]}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False))
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', v)
left = re.findall(r'\{\{[a-z0-9:_]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/scaling-laws.md').write_text(src, encoding='utf-8')
print(json.dumps({k: v for k, v in N.items() if k != 'mtable'}, ensure_ascii=False, indent=0))
print(N['mtable'])
