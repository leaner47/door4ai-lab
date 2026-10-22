"""位置编码一讲的贯穿算例：沿用注意力一讲的四个 token、W_Q、W_K、W_V，文章分镜图、文中数字与实验页共用这组数。
运行：python3 labs-src/positional-encoding/toy.py
  → 生成 src/content/blog/positional-encoding.md（把 article.src.md 里的 {{figN}} 与 {{n:名字}} 填好）
  → 写出 labs-src/positional-encoding/toy.json（实验页开头的 TOY 常量就是它）
"""
import math, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# ———— 注意力一讲的小例子（原样照抄 labs-src/attention-qkv/toy.py）————
X = {'粮油': (0.0, 1.0), '店': (0.4, 0.2), '买了': (0.2, 0.0), '小米': (0.5, 0.5)}
WQ = ((1, 1), (0, -1.2)); WK = ((1, 1), (1, -1)); WV = ((1, 0), (0, 2))
ORIG = ['粮油', '店', '买了', '小米']
SHUF = ['店', '买了', '粮油', '小米']                 # 打乱前三个词，「小米」仍在最后
mv = lambda W, x: (W[0][0]*x[0] + W[0][1]*x[1], W[1][0]*x[0] + W[1][1]*x[1])
dot = lambda a, b: a[0]*b[0] + a[1]*b[1]
def rot(v, a):
    c, s = math.cos(a), math.sin(a); return (c*v[0] - s*v[1], s*v[0] + c*v[1])

# 绝对位置向量（「训练出来的」示意数字，取得小，免得盖掉内容）
P = [(0.1, 0.2), (0.2, -0.1), (-0.1, -0.2), (-0.2, 0.1)]
TH = math.radians(10)                             # 玩具 RoPE：每个位置转 10°

def attend(order, pe=None, rope=None):
    """最后一个 token（小米）的注意力：返回 分数 s、缩放后的份额、x′。"""
    xs = [X[t] for t in order]
    if pe: xs = [(x[0] + pe[i][0], x[1] + pe[i][1]) for i, x in enumerate(xs)]
    qs = [mv(WQ, x) for x in xs]; ks = [mv(WK, x) for x in xs]; vs = [mv(WV, x) for x in xs]
    if rope is not None:
        qs = [rot(q, i*rope) for i, q in enumerate(qs)]; ks = [rot(k, i*rope) for i, k in enumerate(ks)]
    m = len(order) - 1
    s = [dot(qs[m], k) for k in ks]
    e = [math.exp(v/math.sqrt(2)) for v in s]; Z = sum(e); w = [v/Z for v in e]
    d = (sum(w[i]*vs[i][0] for i in range(4)), sum(w[i]*vs[i][1] for i in range(4)))
    return dict(xs=xs, q=qs[m], k=ks, v=vs, s=s, w=w, xp=(xs[m][0] + d[0], xs[m][1] + d[1]))

A0 = attend(ORIG); A1 = attend(SHUF)
B0 = attend(ORIG, P); B1 = attend(SHUF, P)
R0 = attend(ORIG, rope=TH); R1 = attend(SHUF, rope=TH)
for i, t in enumerate(ORIG):                        # 不带位置：打乱后每个词的分数、份额原封不动
    j = SHUF.index(t); assert abs(A0['s'][i] - A1['s'][j]) < 1e-12 and abs(A0['w'][i] - A1['w'][j]) < 1e-12
assert max(abs(A0['xp'][i] - A1['xp'][i]) for i in range(2)) < 1e-12

q = mv(WQ, X['小米']); kL = mv(WK, X['粮油'])        # q = (1.0, −0.6)，k_粮油 = (1, −1)
phq = math.degrees(math.atan2(q[1], q[0])); phk = math.degrees(math.atan2(kL[1], kL[0]))
nq, nk = math.hypot(*q), math.hypot(*kL)
q30 = rot(q, math.radians(30)); k30 = rot(kL, math.radians(30))
def score_rope(m, n, th=TH): return dot(rot(q, m*th), rot(kL, n*th))
assert abs(score_rope(3, 0) - score_rope(13, 10)) < 1e-12

# 绝对位置向量：同一对词放在不同位置，分数不同
def score_abs(m, n, pm, pn):
    a = (X['小米'][0] + pm[0], X['小米'][1] + pm[1]); b = (X['粮油'][0] + pn[0], X['粮油'][1] + pn[1])
    return dot(mv(WQ, a), mv(WK, b))
ABS01 = score_abs(1, 0, P[1], P[0]); ABS23 = score_abs(3, 2, P[3], P[2])
# 加法式的正弦编码（2 维、每个位置 10°）：同样的距离 3，分数也不同
pe_sin = lambda p: (math.sin(p*TH), math.cos(p*TH))
SIN30 = score_abs(3, 0, pe_sin(3), pe_sin(0)); SIN1310 = score_abs(13, 10, pe_sin(13), pe_sin(10))

# 正弦编码 d = 4 的表（底数 10000）
def sinpe(pos, d=4, b=10000):
    out = []
    for i in range(d//2):
        w = b**(-2*i/d); out += [math.sin(pos*w), math.cos(pos*w)]
    return out

# 多个频率：两对，转速 10° 和 1°，两对的数相同
def score2(D):
    a = math.radians(phq - phk)
    return nq*nk*(math.cos(a + D*math.radians(10)) + math.cos(a + D*math.radians(1)))

# 真实频率
def thetas(b, d=128): return [b**(-2*i/d) for i in range(d//2)]
TH1e4, TH5e5 = thetas(10000), thetas(500000)
lam = lambda th: 2*math.pi/th
L = 8192; S = 4
LAM5 = [lam(t) for t in TH5e5]
N_SLOW = sum(l > L for l in LAM5)                   # 训练时没转满一圈的对数
N_SLOW_L2 = sum(lam(t) > 4096 for t in TH1e4)        # Llama 2：底数 1 万，4096
B_NTK = 500000 * S**(128/126)
def yarn_factor(i, s=S, Lc=L, a=1, bta=32, b=500000):
    r = Lc / lam(b**(-2*i/128))
    if r < a: return 1/s
    if r > bta: return 1.0
    g = (r - a)/(bta - a); return (1 - g)/s + g
def ntk_factor(i, s=S): return (B_NTK**(-2*i/128)) / (500000**(-2*i/128))
YARN_KEEP = sum(yarn_factor(i) == 1.0 for i in range(64)); YARN_DIV = sum(yarn_factor(i) == 1/S for i in range(64))
def llama3_factor(i, factor=8, lo=1, hi=4, Lo=8192):
    l = LAM5[i]
    if l < Lo/hi: return 1.0
    if l > Lo/lo: return 1/factor
    sm = (Lo/l - lo)/(hi - lo); return (1 - sm)/factor + sm
L3_KEEP = sum(llama3_factor(i) == 1.0 for i in range(64)); L3_DIV = sum(llama3_factor(i) == 1/8 for i in range(64))
TEMP = 0.1*math.log(S) + 1

# ———— 数字占位符 {{n:名字}} ————
f3 = lambda v: f'{v:.3f}'.replace('-', '−')
f2 = lambda v: f'{v:.2f}'.replace('-', '−')
f1 = lambda v: f'{v:.1f}'.replace('-', '−')
pc = lambda v: f'{v*100:.1f}%'
N = {
    'phq': f2(phq), 'phk': f2(phk), 'dph': f2(phq - phk), 'nq': f3(nq), 'nk': f3(nk), 'nqnk': f3(nq*nk),
    'q30x': f3(q30[0]), 'q30y': f3(q30[1]), 'k30x': f3(k30[0]), 'k30y': f3(k30[1]), 'q30k30': f3(dot(q30, k30)),
    'r30': f3(score_rope(3, 0)), 'r1310': f3(score_rope(13, 10)), 'r03': f3(score_rope(0, 3)), 'r33': f3(score_rope(3, 3)),
    'r21': f3(score_rope(3, 2)), 'r339': f3(score_rope(39, 0)),
    'cos44': f3(math.cos(math.radians(phq - phk + 30))), 'cos16': f3(math.cos(math.radians(phq - phk - 30))),
    'cos24': f3(math.cos(math.radians(phq - phk + 10))),
    'abs01': f3(ABS01), 'abs23': f3(ABS23), 'sin30': f3(SIN30), 'sin1310': f3(SIN1310),
    's2_3': f3(score2(3)), 's2_39': f3(score2(39)), 's2b_3': f3(nq*nk*math.cos(math.radians(phq - phk + 3))),
    's2b_39': f3(nq*nk*math.cos(math.radians(phq - phk + 39))),
    'th1': f3(TH1e4[1]), 'th32': f'{TH1e4[32]:.4f}', 'th63': f'{TH1e4[63]:.2e}'.replace('e-0', ' × 10^{-').replace('e-', ' × 10^{-') + '}',
    'lam63_1e4': f'{lam(TH1e4[63]):,.0f}', 'lam63_5e5': f'{lam(TH5e5[63]):,.0f}', 'lam32_5e5': f'{lam(TH5e5[32]):,.0f}',
    'th63_5e5': f'{TH5e5[63]:.2e}'.replace('e-0', ' × 10^{-').replace('e-', ' × 10^{-') + '}',
    'nslow': str(N_SLOW), 'nslow_l2': str(N_SLOW_L2), 'bntk': f'{B_NTK:,.0f}',
    'yarn_keep': str(YARN_KEEP), 'yarn_div': str(YARN_DIV), 'yarn_mid': str(64 - YARN_KEEP - YARN_DIV),
    'l3_keep': str(L3_KEEP), 'l3_div': str(L3_DIV), 'l3_mid': str(64 - L3_KEEP - L3_DIV),
    'temp': f3(TEMP), 'temp2': f3(TEMP**2),
    'turns0': f'{L/lam(TH5e5[0]):,.0f}', 'turns63': f'{L/lam(TH5e5[63]):.4f}',
}
for nm, A in (('a0', A0), ('b0', B0), ('b1', B1), ('r0', R0), ('r1', R1)):
    N[nm + 'x'] = f2(A['xp'][0]); N[nm + 'y'] = f2(A['xp'][1])

# ———— 表格（markdown，脚本生成）————
def tab_attn(A, order, show_x=False):
    h = '| 位置 | token | ' + ('$x + p$ | ' if show_x else '') + '分数 $s$ | 份额 |\n| --- | --- | ' + ('--- | ' if show_x else '') + '--- | --- |\n'
    for i, t in enumerate(order):
        xs = f"$({f2(A['xs'][i][0])},\\ {f2(A['xs'][i][1])})$ | " if show_x else ''
        h += f"| {i} | {t} | {xs}{f3(A['s'][i])} | {pc(A['w'][i])} |\n"
    return h
T = {
    'tab_a0': tab_attn(A0, ORIG), 'tab_a1': tab_attn(A1, SHUF),
    'tab_b0': tab_attn(B0, ORIG, True), 'tab_b1': tab_attn(B1, SHUF, True),
    'tab_r0': tab_attn(R0, ORIG), 'tab_r1': tab_attn(R1, SHUF),
}
rows = '| 位置 | 第 1 对：$\\sin(\\text{pos})$ | $\\cos(\\text{pos})$ | 第 2 对：$\\sin(0.01\\,\\text{pos})$ | $\\cos(0.01\\,\\text{pos})$ |\n| --- | --- | --- | --- | --- |\n'
for pos in range(4):
    v = sinpe(pos); rows += f'| {pos} | ' + ' | '.join(f3(a) for a in v) + ' |\n'
T['tab_sin'] = rows
rows = '| 位置差 $m - n$ | 夹角 $14.04° + 10° \\times (m-n)$ | 分数 $1.649 \\cos(\\cdot)$ |\n| --- | --- | --- |\n'
for D in (0, 1, 2, 3, 8, 18, 36, 39):
    a = phq - phk + 10*D; rows += f'| {D} | {a:.2f}° | {f3(nq*nk*math.cos(math.radians(a)))} |\n'
T['tab_delta'] = rows
rows = '| 第几对 $i$ | $\\theta_i$（rad / 位置） | 每个位置转 | 转一圈要多少个位置 |\n| --- | --- | --- | --- |\n'
for i in (0, 1, 16, 32, 48, 63):
    t = TH1e4[i]; rows += f'| {i} | {t:.3g} | {math.degrees(t):.3g}° | {lam(t):,.1f} |\n' if lam(t) < 100 else f'| {i} | {t:.3g} | {math.degrees(t):.3g}° | {lam(t):,.0f} |\n'
T['tab_theta'] = rows.replace('e-0', 'e−0')

# ———— SVG 小工具：颜色只用 CSS 变量（与注意力一讲同一套）————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None, op=None):
    return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""}{";stroke-opacity:"+str(op) if op else ""};fill:none"'
def arrow(x1, y1, x2, y2, col, w=2.5):
    ang = math.atan2(y2-y1, x2-x1); Lh = 11; a = 0.42
    if math.hypot(x2-x1, y2-y1) < 2: return ''
    bx, by = x2 - Lh*math.cos(ang), y2 - Lh*math.sin(ang)
    p1 = (x2 - Lh*math.cos(ang-a), y2 - Lh*math.sin(ang-a)); p2 = (x2 - Lh*math.cos(ang+a), y2 - Lh*math.sin(ang+a))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{s}</text>'
def it(s): return f'<tspan font-style="italic">{s}</tspan>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
def arc(cx, cy, r, a0, a1, col, w=1.6):
    """数学角度（逆时针，度），屏幕 y 向下。"""
    p0 = (cx + r*math.cos(math.radians(a0)), cy - r*math.sin(math.radians(a0)))
    p1 = (cx + r*math.cos(math.radians(a1)), cy - r*math.sin(math.radians(a1)))
    large = 1 if abs(a1 - a0) > 180 else 0; sweep = 0 if a1 > a0 else 1
    return f'<path d="M{p0[0]:.1f} {p0[1]:.1f} A{r} {r} 0 {large} {sweep} {p1[0]:.1f} {p1[1]:.1f}" {S_(col, w)}/>'
def axes(cx, cy, r):
    return (f'<line x1="{cx-r}" y1="{cy}" x2="{cx+r}" y2="{cy}" {S_("line", 1.2)}/>'
            f'<line x1="{cx}" y1="{cy-r}" x2="{cx}" y2="{cy+r}" {S_("line", 1.2)}/>')
def vec(cx, cy, u, v, col, w=3):
    return arrow(cx, cy, cx + v[0]*u, cy - v[1]*u, col, w)

figs = {}

# 图 1：不带位置时，两种词序下「小米」的份额
def bars_two(Aa, oa, Ab, ob, ta, tb, hi='粮油', h=38):
    b = text(20, 22, ta, 'muted', 15) + text(260, 22, tb, 'muted', 15)
    for col_i, (A, order, x0) in enumerate(((Aa, oa, 20), (Ab, ob, 260))):
        for i, t in enumerate(order):
            y = 38 + i*h; w = 110*A['w'][i]/0.5; c = 'warn' if t == hi else 'line'
            b += text(x0 + 52, y + 17, t, 'fg', 15, 'end')
            b += f'<rect x="{x0+60}" y="{y}" width="{w:.1f}" height="22" rx="4" {C(c)}/>'
            b += text(x0 + 66 + w, y + 17, pc(A['w'][i]), 'warn' if t == hi else 'muted', 15)
        b += text(x0, 38 + 4*h + 18, f"x′ = ({f2(A['xp'][0])}, {f2(A['xp'][1])})", 'accent', 15, weight=600)
    return b
H1 = 38 + 4*38 + 30
figs['fig1'] = fig(480, H1, '两种词序下小米分给每个词的份额', bars_two(A0, ORIG, A1, SHUF, '粮油 店 买了 小米', '店 买了 粮油 小米'),
                   '图 1　左右两句只是前三个词的顺序不同。「小米」分给每个词的份额一模一样，只是换了行；加出来的 x′ 也一样。')
figs['fig2'] = fig(480, H1, '加了位置向量后两种词序下小米的份额', bars_two(B0, ORIG, B1, SHUF, '粮油 店 买了 小米（加 p）', '店 买了 粮油 小米（加 p）'),
                   '图 2　加上位置向量之后，同样两句话，「小米」分出去的份额不同了，x′ 也不同了。')

# 图 3：正弦编码热力图（d = 32，位置 0–35，底数 10000）
def heat(d=32, npos=36):
    cw, ch = 12.4, 8; x0, y0 = 46, 30
    b = text(x0, 20, '维度 →', 'muted', 14) + text(x0 - 8, y0 + 10, '位置', 'muted', 14, 'end') + text(x0 - 8, y0 + 28, '↓', 'muted', 14, 'end')
    g = {'accent': [], 'warn': []}
    for pos in range(npos):
        for j, a in enumerate(sinpe(pos, d)):
            if abs(a) < 0.02: continue
            g['accent' if a >= 0 else 'warn'].append(f'<rect x="{x0 + j*cw:.0f}" y="{y0 + pos*ch:.0f}" width="{cw-1:.0f}" height="{ch-1:.0f}" fill-opacity="{abs(a):.2f}"/>')
    for c, rs in g.items(): b += f'<g style="fill:var(--{c})">' + ''.join(rs) + '</g>'
    for pos in (0, 10, 20, 30):
        b += text(x0 - 8, y0 + pos*ch + 7, str(pos), 'muted', 12, 'end')
    for j in (0, 8, 16, 24, 31):
        b += text(x0 + j*cw + 5.5, y0 + npos*ch + 16, str(j), 'muted', 12, 'middle')
    return b, y0 + npos*ch + 24
hb, hh = heat()
figs['fig3'] = fig(480, hh, '正弦位置编码热力图', hb,
                   '图 3　每一行是一个位置的编码（d = 32），每一列是一维。蓝色是正数，橙色是负数，越深绝对值越大。左边几列变得很快，越往右变得越慢。')

# 图 4：两个指针（d = 4 的两对），位置 0–3
def clock(cx, cy, r, w, label, pts=range(4)):
    b = f'<circle cx="{cx}" cy="{cy}" r="{r}" {S_("line", 1.5)}/>' + text(cx, cy + r + 26, label, 'muted', 15, 'middle')
    for p in pts:
        # 把 (sin, cos) 这一对画成点：横 = cos，纵 = sin（角度 = w·pos）
        a = p*w; px, py = cx + r*math.cos(a), cy - r*math.sin(a)
        b += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" {C("accent" if p else "muted")}/>'
        if w > 0.2:
            lx, ly = cx + (r + 16)*math.cos(a), cy - (r + 16)*math.sin(a)
            b += text(lx, ly + 5, str(p), 'fg', 14, 'middle')
    if w <= 0.2: b += text(cx + r + 10, cy - 14, '0–3 挤在一起', 'fg', 13, 'start')
    b += arrow(cx, cy, cx + r*math.cos(3*w)*0.92, cy - r*math.sin(3*w)*0.92, 'accent', 2.5)
    return b
figs['fig4'] = fig(480, 230, '两对数画成圆上的点', clock(120, 100, 70, 1.0, '第 1 对：每个位置转 1 rad ≈ 57.3°') + clock(360, 100, 70, 0.01, '第 2 对：每个位置转 0.573°'),
                   '图 4　每一对 (sin, cos) 都是圆上的一个点（以 cos 为横坐标、sin 为纵坐标）。位置 0、1、2、3 依次往逆时针转。左边转得快，右边几乎不动；箭头指着位置 3。')

# 图 5：把 q 转 30°
u = 120; cx, cy = 150, 140
b = axes(cx, cy, 135) + vec(cx, cy, u, q, 'muted', 3) + vec(cx, cy, u, q30, 'warn', 3.5)
b += arc(cx, cy, 52, phq, phq + 30, 'warn')
b += text(cx + q[0]*u + 6, cy - q[1]*u + 20, f'q ({f2(q[0])}, {f2(q[1])})', 'muted', 15)
b += text(cx + q30[0]*u + 6, cy - q30[1]*u - 8, f'转 30° 后 ({f2(q30[0])}, {f2(q30[1])})', 'warn', 15, weight=600)
b += text(cx + 58, cy + 14, '30°', 'warn', 14)
figs['fig5'] = fig(480, 280, '把 q 绕原点转 30 度', b, '图 5　灰色是「小米」原来的 q，橙色是把它绕原点逆时针转 30° 之后。长度不变，只是方向变了。')

# 图 6：两个一起转 30°，夹角不变
def pair_panel(cx, cy, u, qq, kk, label, ang_lab):
    b = axes(cx, cy, 100) + vec(cx, cy, u, kk, 'accent', 3) + vec(cx, cy, u, qq, 'warn', 3)
    a1 = math.degrees(math.atan2(kk[1], kk[0])); a2 = math.degrees(math.atan2(qq[1], qq[0]))
    b += arc(cx, cy, 34, min(a1, a2), max(a1, a2), 'fg', 1.4)
    b += text(cx, cy + 124, label, 'muted', 15, 'middle') + text(cx, cy + 146, '夹角 ' + ang_lab, 'fg', 15, 'middle')
    return b
u = 68
b = pair_panel(120, 115, u, q, kL, '原来', f'{phq-phk:.2f}°') + pair_panel(360, 115, u, q30, k30, '两个都转 30°', f'{phq-phk:.2f}°')
b += text(120, 22, f'点积 {f3(dot(q, kL))}', 'fg', 15, 'middle') + text(360, 22, f'点积 {f3(dot(q30, k30))}', 'fg', 15, 'middle')
figs['fig6'] = fig(480, 275, '两个向量一起转同样的角度，点积不变', b,
                   f'图 6　橙色是 q，蓝色是「粮油」的 k。两个一起转 30°，它们之间的夹角还是 {phq-phk:.2f}°，点积还是 1.6。')

# 图 7：(m, n) = (3, 0) 与 (13, 10)
qa, ka = rot(q, 3*TH), kL; qb, kb = rot(q, 13*TH), rot(kL, 10*TH)
b = pair_panel(120, 115, u, qa, ka, 'q 在位置 3，k 在位置 0', f'{phq-phk+30:.2f}°') + pair_panel(360, 115, u, qb, kb, 'q 在位置 13，k 在位置 10', f'{phq-phk+30:.2f}°')
b += text(120, 22, f'分数 {f3(dot(qa, ka))}', 'fg', 15, 'middle') + text(360, 22, f'分数 {f3(dot(qb, kb))}', 'fg', 15, 'middle')
figs['fig7'] = fig(480, 275, '相对距离相同，分数相同', b,
                   '图 7　左边 q 转 30°、k 不转；右边 q 转 130°、k 转 100°。两边都差 30°，夹角一样，分数一样。')

# 图 8：一个频率时，分数随距离的变化（周期 36）
def curve(fx, x0, y0, wpx, hpx, xmax, ymin, ymax, col, w=2.2, n=240, dash=None):
    pts = []
    for j in range(n + 1):
        D = xmax*j/n; v = fx(D)
        pts.append(f'{x0 + wpx*D/xmax:.1f},{y0 - hpx*(v - ymin)/(ymax - ymin):.1f}')
    return f'<polyline points="{" ".join(pts)}" {S_(col, w, dash)}/>'
x0, y0, wpx, hpx = 50, 200, 400, 170
f1d = lambda D: nq*nk*math.cos(math.radians(phq - phk + 10*D))
b = f'<line x1="{x0}" y1="{y0 - hpx*0.5}" x2="{x0+wpx}" y2="{y0 - hpx*0.5}" {S_("line", 1.2)}/>' + f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0-hpx}" {S_("line", 1.2)}/>'
b += curve(f1d, x0, y0, wpx, hpx, 72, -1.8, 1.8, 'accent')
for D in (3, 39):
    px, py = x0 + wpx*D/72, y0 - hpx*(f1d(D) + 1.8)/3.6
    b += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" {C("warn")}/>' + text(px, py - 12, f'{D}', 'warn', 15, 'middle', weight=600)
for D in (0, 18, 36, 54, 72): b += text(x0 + wpx*D/72, y0 + 20, str(D), 'muted', 13, 'middle')
b += text(x0 + wpx, y0 + 40, '位置差 m − n', 'muted', 14, 'end') + text(x0 - 8, y0 - hpx*0.5 + 5, '0', 'muted', 13, 'end')
b += text(x0 + 8, y0 - hpx - 6, '分数', 'muted', 14)
figs['fig8'] = fig(480, 250, '只有一个频率时分数随位置差周期变化', b,
                   '图 8　只有一对、每个位置转 10° 时，分数随位置差变化。转满 360° 就回到原样：位置差 3 和 39 的分数完全一样。')

# 图 9：多个频率叠加（q、k 每一对都同向，画平均的 cos）
def avg_cos(ths): return lambda D: sum(math.cos(D*t) for t in ths)/len(ths)
x0, y0, wpx, hpx = 50, 210, 400, 180
b = f'<line x1="{x0}" y1="{y0 - hpx*0.5}" x2="{x0+wpx}" y2="{y0 - hpx*0.5}" {S_("line", 1.2)}/>' + f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0-hpx}" {S_("line", 1.2)}/>'
b += curve(avg_cos([math.radians(10)]), x0, y0, wpx, hpx, 120, -1, 1, 'line', 2, 300)
b += curve(avg_cos([math.radians(10), math.radians(1)]), x0, y0, wpx, hpx, 120, -1, 1, 'accent', 2.2, 300)
b += curve(avg_cos(TH1e4), x0, y0, wpx, hpx, 120, -1, 1, 'warn', 2.6, 300)
for D in (0, 30, 60, 90, 120): b += text(x0 + wpx*D/120, y0 + 20, str(D), 'muted', 13, 'middle')
b += text(x0 + wpx, y0 + 40, '位置差 m − n', 'muted', 14, 'end')
b += text(x0 - 8, y0 - hpx + 5, '1', 'muted', 13, 'end') + text(x0 - 8, y0 - hpx*0.5 + 5, '0', 'muted', 13, 'end') + text(x0 - 8, y0 + 5, '−1', 'muted', 13, 'end')
ly = y0 + 62
b += f'<rect x="{x0}" y="{ly-10}" width="18" height="4" rx="2" {C("line")}/>' + text(x0 + 24, ly - 3, '1 对（10°）', 'muted', 14)
b += f'<rect x="{x0+130}" y="{ly-10}" width="18" height="4" rx="2" {C("accent")}/>' + text(x0 + 154, ly - 3, '2 对（10°、1°）', 'accent', 14)
b += f'<rect x="{x0+280}" y="{ly-10}" width="18" height="4" rx="2" {C("warn")}/>' + text(x0 + 304, ly - 3, '64 对（真实）', 'warn', 14)
figs['fig9'] = fig(480, 290, '频率越多，分数越不会周期性地回到原样', b,
                   '图 9　q 和 k 每一对都同向时，分数（除以对数）随位置差的变化。灰线每 36 个位置回到 1；蓝线要很久才回来；橙线是底数 10000、128 维的 64 对，离得越远越低，不再回到 1。')

# 图 10：训练长度 8192 内，每一对转了几圈（底数 50 万）
x0, y0, wpx, hpx = 56, 210, 400, 180
lo, hi_ = -3, 4      # log10 圈数范围
b = ''
for e in range(lo, hi_ + 1):
    yy = y0 - hpx*(e - lo)/(hi_ - lo)
    b += text(x0 - 8, yy + 5, ('10<tspan dy="-5" font-size="9">' + str(e).replace('-', '−') + '</tspan>' if e not in (0, 1) else ('1' if e == 0 else '10')), 'muted', 12, 'end')
y1 = y0 - hpx*(0 - lo)/(hi_ - lo)
b += f'<line x1="{x0}" y1="{y1:.1f}" x2="{x0+wpx}" y2="{y1:.1f}" {S_("fg", 1.2, "4 4")}/>' + text(x0 + wpx, y1 - 6, '一圈', 'fg', 13, 'end')
bw = wpx/64
for i in range(64):
    turns = L/LAM5[i]; hgt = hpx*(math.log10(turns) - lo)/(hi_ - lo)
    c = 'warn' if turns < 1 else 'accent'
    b += f'<rect x="{x0 + i*bw + 0.6:.1f}" y="{y0 - hgt:.1f}" width="{bw - 1.2:.1f}" height="{hgt:.1f}" {C(c)}/>'
for i in (0, 16, 32, 48, 63): b += text(x0 + (i + 0.5)*bw, y0 + 18, str(i), 'muted', 12, 'middle')
b += text(x0 + wpx, y0 + 38, '第几对 i', 'muted', 14, 'end') + text(x0 + 4, 16, '训练长度 8192 内转过的圈数（对数刻度）', 'muted', 14)
figs['fig10'] = fig(480, 250, '训练长度内每一对转过的圈数', b,
                    f'图 10　底数 50 万、128 维（Llama 3）时，64 对在 8192 个位置内各转了几圈。蓝色的转满了不止一圈，所有角度都见过；橙色的 {N_SLOW} 对连一圈都没转完。')

# 图 11：三种扩展办法，每一对的转速变成原来的几倍（s = 4）
x0, y0, wpx, hpx = 56, 200, 400, 170
b = ''
for v, lab in ((1, '1'), (0.5, '1/2'), (0.25, '1/4')):
    yy = y0 - hpx*(v - 0.2)/0.85
    b += f'<line x1="{x0}" y1="{yy:.1f}" x2="{x0+wpx}" y2="{yy:.1f}" {S_("line", 1)}/>' + text(x0 - 8, yy + 5, lab, 'muted', 13, 'end')
def series(fn, col, w, dash=None):
    pts = ' '.join(f'{x0 + (i + 0.5)*wpx/64:.1f},{y0 - hpx*(fn(i) - 0.2)/0.85:.1f}' for i in range(64))
    return f'<polyline points="{pts}" {S_(col, w, dash)}/>'
b += series(lambda i: 1/S, 'muted', 2.4, '6 4') + series(ntk_factor, 'accent', 2.4) + series(yarn_factor, 'warn', 2.8)
for i in (0, 16, 32, 48, 63): b += text(x0 + (i + 0.5)*wpx/64, y0 + 18, str(i), 'muted', 12, 'middle')
b += text(x0 + wpx, y0 + 38, '第几对 i', 'muted', 14, 'end')
ly = y0 + 60
b += f'<rect x="{x0}" y="{ly-10}" width="18" height="4" rx="2" {C("muted")}/>' + text(x0 + 24, ly - 3, '位置插值', 'muted', 14)
b += f'<rect x="{x0+120}" y="{ly-10}" width="18" height="4" rx="2" {C("accent")}/>' + text(x0 + 144, ly - 3, 'NTK-aware', 'accent', 14)
b += f'<rect x="{x0+250}" y="{ly-10}" width="18" height="4" rx="2" {C("warn")}/>' + text(x0 + 274, ly - 3, 'YaRN（分段）', 'warn', 14)
figs['fig11'] = fig(480, 280, '三种扩展办法下每一对转速的倍数', b,
                    '图 11　把 8192 扩到 4 倍（s = 4，底数 50 万）时，每一对的转速变成原来的几倍。位置插值全部放慢 4 倍；NTK-aware 快的几乎不变、慢的放慢 4 倍；YaRN 快的完全不动、慢的放慢 4 倍、中间平滑过渡。')

# 供实验页用的数据
toy = {'x': X, 'WQ': WQ, 'WK': WK, 'WV': WV, 'P': P, 'orig': ORIG, 'th_deg': 10}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False))

src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in T.items(): src = src.replace('{{' + k + '}}', v.rstrip('\n'))
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', v)
left = re.findall(r'\{\{[^}]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/positional-encoding.md').write_text(src, encoding='utf-8')
print(json.dumps({k: N[k] for k in N}, ensure_ascii=False, indent=0))
