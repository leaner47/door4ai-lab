"""蒸馏一讲的贯穿算例：文章分镜图、文中数字与实验页共用这组数。
贯穿算例：一张猫的图片，四个类别（猫、狗、狐狸、汽车）。
  老师 logits v = (4, 1, 0, −5)，学生 logits z = (2, 0, 1, −3)，硬标签 = 猫。两组都是平均为 0（第六步要用）。
页内训练的结果（图 6、图 7 和文中的错误率）来自 lab_results.json：由 run_lab.mjs 从实验页里抽出同一段 JS 跑出来。
运行顺序：
  python3 labs-src/distillation/build.py      → public/labs/distillation/index.html
  node labs-src/distillation/run_lab.mjs      → labs-src/distillation/lab_results.json
  python3 labs-src/distillation/toy.py        → src/content/blog/distillation.md（把 article.src.md 的 {{figN}} 与 {{n:名字}} 填好）
"""
import math, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

CL = ['猫', '狗', '狐狸', '汽车']
V = [4, 1, 0, -5]
Z = [2, 0, 1, -3]
Y = [1, 0, 0, 0]
NCL = 4

def sm(z, T=1.0):
    e = [math.exp(v / T) for v in z]; s = sum(e); return e, s, [x / s for x in e]

E1, S1, P1 = sm(V, 1)
E2, S2, P2 = sm(V, 2)
E4, S4, P4 = sm(V, 4)
E10, S10, P10 = sm(V, 10)
EQ1, SQ1, Q1 = sm(Z, 1)
EQ4, SQ4, Q4 = sm(Z, 4)
H_P4 = -sum(p * math.log(p) for p in P4)
CE_TERMS = [-p * math.log(q) for p, q in zip(P4, Q4)]
CE_PQ4 = sum(CE_TERMS)
KL4 = sum(p * math.log(p / q) for p, q in zip(P4, Q4))
CE_HARD = -math.log(Q1[0])
G_HARD = [q - y for q, y in zip(Q1, Y)]
G_SOFT4 = [(q - p) / 4 for q, p in zip(Q4, P4)]
norm = lambda g: math.sqrt(sum(x * x for x in g))
def gsoft(T):
    _, _, p = sm(V, T); _, _, q = sm(Z, T); return [(b - a) / T for a, b in zip(p, q)]
TS = [1, 2, 4, 8, 16, 32]
GN = {T: norm(gsoft(T)) for T in TS}
LIMIT = norm([(z - v) for z, v in zip(Z, V)]) / NCL     # T 很大时 T²·|梯度| 的极限 = |z − v| / N
APPROX16 = [(z - v) / (NCL * 16 * 16) for z, v in zip(Z, V)]
G16 = gsoft(16)

LAB = json.loads((HERE / 'lab_results.json').read_text())

# ———— 文中数字 ————
f2 = lambda v: f'{v:.2f}'
f3 = lambda v: f'{v:.3f}'
f4 = lambda v: f'{v:.4f}'
pt = lambda v, d=1: f'{v*100:.{d}f}%'
def sg(v, d=3):
    s = f'{abs(v):.{d}f}'; return ('-' if v < 0 else '') + s       # 公式里用 -，KaTeX 会排成减号
def sgt(v, d=3):
    s = f'{abs(v):.{d}f}'; return ('−' if v < 0 else '+') + s      # 正文里
N = {}
for name, arr in (('e1', E1), ('e4', E4), ('eq4', EQ4), ('eq1', EQ1)):
    for i, x in enumerate(arr): N[f'{name}_{i}'] = f3(x) if x >= 0.01 else f'{x:.5f}'
N.update({'s1': f3(S1), 's4': f3(S4), 'sq4': f3(SQ4), 'sq1': f3(SQ1)})
for name, arr in (('p1', P1), ('p2', P2), ('p4', P4), ('p10', P10), ('q1', Q1), ('q4', Q4)):
    for i, x in enumerate(arr):
        N[f'{name}_{i}'] = f3(x) if x >= 0.001 else f'{x:.5f}'
        N[f'{name}pc_{i}'] = pt(x, 1) if x >= 0.001 else pt(x, 3)
N['ratio_dog_car_1'] = f'{P1[1]/P1[3]:.0f}'
N['ratio_dog_car_4'] = f'{P4[1]/P4[3]:.2f}'
N['ratio_cat_dog_1'] = f'{P1[0]/P1[1]:.1f}'
N['ratio_cat_dog_4'] = f'{P4[0]/P4[1]:.2f}'
N['e6'] = f'{math.exp(6):.0f}'; N['e15'] = f'{math.exp(1.5):.2f}'
N['hp4'] = f3(H_P4); N['cepq4'] = f3(CE_PQ4); N['kl4'] = f3(KL4); N['cehard'] = f3(CE_HARD)
for i in range(4):
    N[f'lnq4_{i}'] = sg(math.log(Q4[i])); N[f'ceterm_{i}'] = f3(CE_TERMS[i])
    N[f'gh_{i}'] = sg(G_HARD[i]); N[f'gs4_{i}'] = sg(G_SOFT4[i], 4); N[f'd4_{i}'] = sg(Q4[i] - P4[i])
    N[f'gs16_{i}'] = sg(G16[i], 5); N[f'ap16_{i}'] = sg(APPROX16[i], 5)
    N[f'lnp4_{i}'] = sg(math.log(P4[i]))
for T in TS:
    N[f'gn_{T}'] = f'{GN[T]:.5f}' if GN[T] < 0.01 else f4(GN[T]); N[f'gnt_{T}'] = f3(GN[T] * T * T)
N['limit'] = f3(LIMIT)
N['ghnorm'] = f4(norm(G_HARD))
N['ratio_noT2'] = f3(0.5 * GN[4] / (0.5 * norm(G_HARD)))
N['ratio_T2'] = f3(0.5 * 16 * GN[4] / (0.5 * norm(G_HARD)))
N['shrink'] = f'{GN[4] / GN[16]:.1f}'
# 页内训练
r = LAB['runs']
N['terr'] = pt(LAB['teacherErr']); N['eh60'] = pt(r['60_4']['eh']); N['es60'] = pt(r['60_4']['es'])
N['es60_1'] = pt(r['60_1']['es']); N['es60_2'] = pt(r['60_2']['es']); N['es60_8'] = pt(r['60_8']['es'])
N['eh30'] = pt(r['30_4']['eh']); N['es30'] = pt(r['30_4']['es']); N['eh120'] = pt(r['120_4']['eh']); N['es120'] = pt(r['120_4']['es'])
w = LAB['widths']
for h in ['1', '2', '3', '4', '6', '8', '16', '32']:
    N[f'wh_{h}'] = pt(w[h]['eh']); N[f'ws_{h}'] = pt(w[h]['es'])

# ———— SVG 小工具：颜色只用 CSS 变量 ————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{esc(s)}</text>'
def rect(x, y, w, h, col, rx=3, op=None):
    o = f';fill-opacity:{op}' if op is not None else ''
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{max(h,0):.1f}" rx="{rx}" style="fill:var(--{col}){o}"/>'
def line(x1, y1, x2, y2, col, w=1.5, dash=None): return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {S_(col, w, dash)}/>'
def arrow(x1, y1, x2, y2, col, w=2.2):
    ang = math.atan2(y2-y1, x2-x1); L = 9; a = 0.45
    bx, by = x2 - L*math.cos(ang), y2 - L*math.sin(ang)
    p1 = (x2 - L*math.cos(ang-a), y2 - L*math.sin(ang-a)); p2 = (x2 - L*math.cos(ang+a), y2 - L*math.sin(ang+a))
    return line(x1, y1, bx, by, col, w) + f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>'
def legend(x, y, items):
    b = ''
    for lab, col in items:
        b += rect(x, y - 10, 12, 12, col) + text(x + 18, y, lab, 'muted', 14); x += 30 + 15 * len(lab)
    return b
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
def pl(v):     # 柱顶的百分比标注
    return pt(v, 1) if v >= 0.001 else pt(v, 2)

figs = {}
# 图 1：硬标签 vs 老师（T = 1）
base, top = 200, 62; slot = 440 / 4; bw = 34
b = legend(20, 22, [('硬标签', 'muted'), ('老师的概率（T = 1）', 'accent')])
b += line(20, base, 460, base, 'line')
for i, c in enumerate(CL):
    cx = 20 + slot * (i + 0.5); hy = Y[i] * (base - top); hp = P1[i] * (base - top)
    b += rect(cx - bw - 3, base - hy, bw, hy, 'muted') + rect(cx + 3, base - hp, bw, hp, 'accent')
    b += text(cx + 3 + bw/2, base - hp - 6, pl(P1[i]), 'accent', 14, 'middle')
    if Y[i]: b += text(cx - 3 - bw/2, base - hy - 6, '1', 'muted', 14, 'middle')
    b += text(cx, base + 24, c, 'fg', 16, 'middle')
figs['fig1'] = fig(480, 238, '硬标签与老师在温度 1 下的概率', b,
    f'图 1　同一张猫的图片。灰色是硬标签：猫 1，其余全是 0。蓝色是老师的概率：猫 {pt(P1[0])}，狗 {pt(P1[1])}，狐狸 {pt(P1[2])}，汽车 {pt(P1[3],3)}（在柱子底部，几乎看不见）。')

# 图 2：四个温度下老师的分布
b = ''; pw, ph = 230, 150
for k, (T, P) in enumerate(((1, P1), (2, P2), (4, P4), (10, P10))):
    ox = 10 + (k % 2) * 240; oy = 10 + (k // 2) * (ph + 16)
    base = oy + ph - 26; topy = oy + 30; slot = (pw - 10) / 4; bw = 30
    b += text(ox + 4, oy + 16, f'T = {T}', 'fg', 16, weight=600)
    b += line(ox, base, ox + pw - 10, base, 'line')
    for i, c in enumerate(CL):
        cx = ox + slot * (i + 0.5); hp = P[i] * (base - topy)
        b += rect(cx - bw/2, base - hp, bw, hp, 'accent')
        b += text(cx, base - hp - 5, f'{P[i]*100:.0f}' if P[i] >= 0.005 else ('0.01' if T == 1 else f'{P[i]*100:.1f}'), 'accent', 13, 'middle')
        b += text(cx, base + 18, c, 'muted', 14, 'middle')
figs['fig2'] = fig(480, 2 * (150 + 16) + 4, '老师在温度 1、2、4、10 下的分布', b,
    '图 2　同一组 logits，除以不同的温度再做 softmax（柱顶数字是百分比）。T 越大，分布越平：猫的份额让出来，狗、狐狸、汽车一个个露出来，但排序始终不变。')

# 图 3：T = 4 时老师与学生
base, top = 196, 44; slot = 440 / 4; bw = 32
b = legend(20, 22, [('老师 p（T = 4）', 'accent'), ('学生 q（T = 4）', 'warn')])
b += line(20, base, 460, base, 'line')
for i, c in enumerate(CL):
    cx = 20 + slot * (i + 0.5); hp = P4[i] * (base - top) * 1.6; hq = Q4[i] * (base - top) * 1.6
    b += rect(cx - bw - 2, base - hp, bw, hp, 'accent') + rect(cx + 2, base - hq, bw, hq, 'warn')
    b += text(cx - 2 - bw/2, base - hp - 6, f'{P4[i]*100:.1f}', 'accent', 13, 'middle')
    b += text(cx + 2 + bw/2, base - hq - 6, f'{Q4[i]*100:.1f}', 'warn', 13, 'middle')
    b += text(cx, base + 24, c, 'fg', 16, 'middle')
figs['fig3'] = fig(480, 230, '温度 4 下老师与学生的分布', b,
    '图 3　温度都取 4（柱顶数字是百分比）。学生把狐狸排在狗前面，汽车也给多了；老师的分布里，狗比狐狸更像猫。软标签的损失就是要量出这两组柱子差多少。')

# 图 4：硬项与软项的梯度方向
def gradpanel(ox, title, g, col, scale, note):
    mid = 120; b = text(ox + 110, 22, title, 'fg', 15, 'middle', weight=600) + text(ox + 110, 42, note, 'muted', 13, 'middle')
    b += line(ox + 4, mid, ox + 216, mid, 'line')
    for i, c in enumerate(CL):
        cx = ox + 14 + 52 * i + 20; h = abs(g[i]) * scale
        b += rect(cx - 14, mid - h if g[i] > 0 else mid, 28, h, col)
        lab = f'{g[i]:+.3f}'.replace('-', '−') if abs(g[i]) >= 0.001 else f'{g[i]:+.4f}'.replace('-', '−')
        b += text(cx, (mid - h - 6) if g[i] > 0 else (mid + h + 16), lab, col, 12, 'middle')
        b += text(cx, 222, c, 'fg', 15, 'middle')
    return b
b = gradpanel(10, '硬标签的梯度', G_HARD, 'muted', 200, '刻度 ×1') + gradpanel(250, '软标签的梯度（T = 4）', G_SOFT4, 'accent', 2000, '刻度 ×10')
b += line(240, 30, 240, 210, 'line', 1, '3 4')
figs['fig4'] = fig(480, 234, '硬标签与软标签对每个 logit 的梯度', b,
    '图 4　柱子朝上 = 梯度为正 = 这个 logit 要降；朝下 = 要升。看「狗」：硬标签要把它压下去，软标签要把它抬起来。右边的刻度放大了 10 倍：软标签的梯度小得多，第六步专门讲这件事。')

# 图 5：软项梯度长度随 T（对数坐标），乘与不乘 T²
X0, X1, Y0, Y1 = 70, 450, 210, 30
Tgrid = [1 * (32 ** (k / 120)) for k in range(121)]
raw = [norm(gsoft(T)) for T in Tgrid]; scl = [g * T * T for g, T in zip(raw, Tgrid)]
lo, hi = math.log10(min(raw) * 0.7), math.log10(max(scl) * 1.6)
xs = lambda T: X0 + (X1 - X0) * math.log(T) / math.log(32)
ys = lambda g: Y0 - (Y0 - Y1) * (math.log10(g) - lo) / (hi - lo)
b = line(X0, Y0, X1, Y0, 'line') + line(X0, Y0, X0, Y1 - 8, 'line')
for T in TS: b += text(xs(T), Y0 + 20, str(T), 'muted', 14, 'middle')
b += text(X1, Y0 + 40, '温度 T', 'muted', 14, 'end')
for e in range(math.ceil(lo), math.floor(hi) + 1):
    b += line(X0 - 4, ys(10**e), X0, ys(10**e), 'line') + text(X0 - 8, ys(10**e) + 5, {0: '1', -1: '0.1', -2: '0.01', -3: '0.001'}.get(e, f'1e{e}'), 'muted', 13, 'end')
b += text(X0 + 6, Y1 - 12, '软标签梯度的长度', 'muted', 14)
path = lambda arr: ' '.join(f'{"L" if k else "M"}{xs(T):.1f} {ys(g):.1f}' for k, (T, g) in enumerate(zip(Tgrid, arr)))
b += f'<path d="{path(raw)}" {S_("muted", 2.2, "6 4")}/>' + f'<path d="{path(scl)}" {S_("accent", 2.8)}/>'
b += line(X0, ys(LIMIT), X1, ys(LIMIT), 'ok', 1.2, '2 4') + text(X1, ys(LIMIT) - 8, f'|z − v| / N = {LIMIT:.3f}', 'ok', 13, 'end')
for T in (1, 4, 16):
    b += f'<circle cx="{xs(T):.1f}" cy="{ys(GN[T]):.1f}" r="4" {C("muted")}/>' + f'<circle cx="{xs(T):.1f}" cy="{ys(GN[T]*T*T):.1f}" r="4" {C("accent")}/>'
b += text(xs(1.25), ys(0.004), '不乘：按 1/T² 变小', 'muted', 14, 'start')
b += text(xs(2.2), ys(norm(gsoft(2.2)) * 2.2 * 2.2) + 22, '乘 T²：走平', 'accent', 14, 'start')
figs['fig5'] = fig(480, 258, '软标签梯度长度随温度变化，乘与不乘 T 平方', b,
    f'图 5　两个坐标轴都是对数刻度。灰色虚线是软标签梯度本来的长度：T 从 1 到 32，从 {GN[1]:.3f} 掉到 {GN[32]:.5f}。蓝线乘上 T² 之后几乎是平的，并且趋向绿色虚线 {LIMIT:.3f}（第六步推出来的极限）。')

# 图 6：页内训练的分界（N = 60，T = 4）
CLSCOL = ['accent', 'warn', 'ok']
def region(ox, oy, size, grid, pts, title, sub):
    g = int(round(math.sqrt(len(grid)))); c = size / g; d = ['', '', '']
    for rr in range(g):          # 同一行连续同类的格子并成一段，每类一条 path，格子之间不露缝
        k = 0
        while k < g:
            cl = grid[rr * g + k]; e = k
            while e + 1 < g and grid[rr * g + e + 1] == cl: e += 1
            d[cl] += f'M{ox + k*c:.2f} {oy + rr*c:.2f}h{(e-k+1)*c:.2f}v{c+0.3:.2f}h{-(e-k+1)*c:.2f}z'; k = e + 1
    b = ''.join(f'<path d="{dd}" style="fill:var(--{CLSCOL[i]});fill-opacity:0.28"/>' for i, dd in enumerate(d) if dd)
    if pts:
        X, Yp = pts['X'], pts['Y']
        for i in range(len(Yp)):
            x = ox + (X[2*i] + 1.2) / 2.4 * size; y = oy + (1.2 - X[2*i+1]) / 2.4 * size
            b += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" style="fill:var(--{CLSCOL[Yp[i]]});stroke:var(--bg);stroke-width:0.8"/>'
    b += text(ox + size/2, oy + size + 20, title, 'fg', 14, 'middle') + text(ox + size/2, oy + size + 38, sub, 'muted', 13, 'middle')
    return b
s6 = 148
b = region(8, 4, s6, LAB['teacherGrid'], None, '老师（32 单元）', f'错 {pt(LAB["teacherErr"])}')
b += region(166, 4, s6, LAB['gridHard'], LAB['pts'], '硬标签学生', f'错 {N["eh60"]}')
b += region(324, 4, s6, LAB['gridSoft'], LAB['pts'], '软标签学生（T = 4）', f'错 {N["es60"]}')
figs['fig6'] = fig(480, s6 + 46, '老师、硬标签学生、软标签学生在平面上的分界', b,
    f'图 6　三种颜色是三类，背景色是模型把每个位置判成哪一类，圆点是学生拿到的 60 个点。两个学生都是 16 个隐藏单元、同一组初始参数、同样训练 300 步，只有目标不同。软标签学生的分界更贴近老师。')

# 图 7：容量曲线
WD = ['1', '2', '3', '4', '6', '8', '16', '32']
X0, X1, Y0, Y1, emax = 64, 460, 200, 28, 0.55
xs = lambda k: X0 + (X1 - X0) * k / (len(WD) - 1)
ys = lambda e: Y0 - (Y0 - Y1) * math.sqrt(e / emax)
b = line(X0, Y0, X1, Y0, 'line') + line(X0, Y0, X0, Y1 - 6, 'line')
for k, h in enumerate(WD): b += text(xs(k), Y0 + 20, h, 'muted', 14, 'middle')
b += text(X1, Y0 + 40, '学生的隐藏层宽度', 'muted', 14, 'end')
for e in (0.01, 0.05, 0.2, 0.5): b += line(X0 - 4, ys(e), X0, ys(e), 'line') + text(X0 - 8, ys(e) + 5, f'{e*100:.0f}%', 'muted', 13, 'end')
b += text(X0 + 6, Y1 - 12, '验证错误率', 'muted', 14)
te = LAB['teacherErr']
b += line(X0, ys(te), X1, ys(te), 'fg', 1.2, '5 4') + text(X0 + 6, ys(te) + 18, f'老师 {pt(te)}', 'fg', 13)
for f, col in (('eh', 'warn'), ('es', 'ok')):
    pts = [(xs(k), ys(w[h][f])) for k, h in enumerate(WD)]
    b += '<path d="' + ' '.join(f'{"L" if k else "M"}{x:.1f} {y:.1f}' for k, (x, y) in enumerate(pts)) + f'" {S_(col, 2.4)}/>'
    for x, y in pts: b += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" {C(col)}/>'
b += legend(X0 + 150, Y1 + 8, [('硬标签学生', 'warn'), ('软标签学生', 'ok')])
figs['fig7'] = fig(480, 250, '验证错误率随学生隐藏层宽度的变化', b,
    f'图 7　同样 60 个点、T = 4，每个宽度各训练一个硬标签学生和一个软标签学生（纵轴按平方根刻度，小错误率看得清）。宽度 2 到 4，软标签不比硬标签好；宽度 6 起软标签学生一直更好，16 以后贴近老师。')

# 图 8：词元级与序列级蒸馏
b = text(10, 22, '词元级：每个位置对齐老师的整个分布', 'fg', 15, weight=600)
toks = ['17', '×', '3', '=', '51']
for i, t in enumerate(toks):
    x = 14 + i * 50
    b += f'<rect x="{x}" y="36" width="42" height="30" rx="6" {S_("line", 1.5)}/>' + text(x + 21, 57, t, 'muted', 15, 'middle')
b += arrow(272, 51, 300, 51, 'muted', 1.5)
bars_t = [0.55, 0.2, 0.15, 0.1]; bars_s = [0.35, 0.3, 0.2, 0.15]
for j, (pv, qv) in enumerate(zip(bars_t, bars_s)):
    x = 310 + j * 38
    b += rect(x, 76 - pv * 70, 14, pv * 70, 'accent') + rect(x + 16, 76 - qv * 70, 14, qv * 70, 'warn')
b += text(310, 96, '老师 p 与学生 q（示意）', 'muted', 13)
b += text(10, 128, '要老师在每个位置的全部概率（同一个分词器）。损失 KL(p ‖ q)，梯度 q − p。', 'muted', 13)
y0 = 168
b += text(10, y0, '序列级：老师先写出整段回答，学生照着做 SFT', 'fg', 15, weight=600)
b += f'<rect x="14" y="{y0+14}" width="84" height="34" rx="6" {S_("accent", 2)}/>' + text(56, y0 + 37, '老师', 'accent', 15, 'middle')
b += arrow(102, y0 + 31, 136, y0 + 31, 'muted', 1.5)
for i, t in enumerate(['51', '。', '<end>']):
    x = 142 + i * 56
    b += f'<rect x="{x}" y="{y0+14}" width="50" height="34" rx="6" {S_("accent", 1.5)}/>' + text(x + 25, y0 + 37, t, 'accent', 14, 'middle')
b += arrow(316, y0 + 31, 350, y0 + 31, 'muted', 1.5)
b += f'<rect x="356" y="{y0+14}" width="110" height="34" rx="6" {S_("warn", 2)}/>' + text(411, y0 + 37, '学生 SFT', 'warn', 15, 'middle')
b += text(10, y0 + 76, '只要老师输出的文字。每个位置的目标是 one-hot，梯度 q − y。', 'muted', 13)
figs['fig8'] = fig(480, y0 + 90, '词元级蒸馏与序列级蒸馏的对比', b,
    '图 8　上：词元级蒸馏，学生在每个位置对齐老师的整个下一个 token 分布（示意）。下：序列级蒸馏，老师写出的文字当作示范，学生做普通的 SFT，和后训练那一讲第二步一模一样。')

# 图 9：DeepSeek-R1 蒸馏的 AIME 2024 pass@1
ROWS = [('GPT-4o-0513', 'line', 9.3), ('Claude-3.5-Sonnet', 'line', 16.0), ('蒸馏 Qwen-1.5B', 'accent', 28.9), ('蒸馏 Llama-8B', 'accent', 50.4),
        ('蒸馏 Qwen-7B', 'accent', 55.5), ('蒸馏 Qwen-14B', 'accent', 69.7), ('蒸馏 Llama-70B', 'accent', 70.0), ('蒸馏 Qwen-32B', 'accent', 72.6),
        ('Qwen-32B 纯 RL', 'warn', 47.0), ('R1（老师）', 'ok', 79.8)]
b = ''; lw = 150; bwid = 270
for i, (n, col, v) in enumerate(ROWS):
    y = 10 + i * 30
    b += text(lw - 10, y + 17, n, 'muted' if col == 'line' else 'fg', 14, 'end')
    b += rect(lw, y + 4, bwid * v / 100, 18, col)
    b += text(lw + bwid * v / 100 + 6, y + 18, f'{v:.1f}', 'muted' if col == 'line' else col, 14)
figs['fig9'] = fig(480, 10 + len(ROWS) * 30 + 4, 'DeepSeek-R1 蒸馏模型在 AIME 2024 上的 pass@1', b,
    '图 9　AIME 2024 每题答一次的正确率（%）。蓝色是 6 个蒸馏学生，橙色是同一个 Qwen2.5-32B 底座不蒸馏、直接做大规模强化学习，绿色是老师 R1，灰色是两个对照模型。数字来自 DeepSeek-R1 论文表 4、5、6（2026-10-22 核实）。')

# ———— 输出 ————
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', v)
left = re.findall(r'\{\{[a-z0-9:_]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/distillation.md').write_text(src, encoding='utf-8')
print(json.dumps({k: v for k, v in N.items()}, ensure_ascii=False))
