"""注意力一讲的贯穿算例：文章分镜图与实验 03/04/06 共用这组数。
运行：python3 labs-src/attention-qkv/toy.py  → 生成 src/content/blog/attention-qkv.md（由 article.src.md 填入图和数字）
"""
import math, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

T = ['粮油', '店', '买了', '小米']
X = {'粮油': (0.0, 1.0), '店': (0.4, 0.2), '买了': (0.2, 0.0), '小米': (0.5, 0.5)}   # (像手机, 像粮食)
WQ = ((1, 1), (0, -1.2)); WK = ((1, 1), (1, -1)); WV = ((1, 0), (0, 2))
mv = lambda W, x: (W[0][0]*x[0] + W[0][1]*x[1], W[1][0]*x[0] + W[1][1]*x[1])
q = mv(WQ, X['小米'])
K = {t: mv(WK, X[t]) for t in T}
V = {t: mv(WV, X[t]) for t in T}
S = {t: q[0]*K[t][0] + q[1]*K[t][1] for t in T}
COS = {t: (X['小米'][0]*X[t][0] + X['小米'][1]*X[t][1]) / math.hypot(*X['小米']) / math.hypot(*X[t]) for t in T}
def softmax(d):
    e = {t: math.exp(v) for t, v in d.items()}; s = sum(e.values()); return e, s, {t: e[t]/s for t in d}
E1, SUM1, W1 = softmax(S)
SS = {t: S[t]/math.sqrt(2) for t in T}
E2, SUM2, W2 = softmax(SS)
D = (sum(W2[t]*V[t][0] for t in T), sum(W2[t]*V[t][1] for t in T))
XP = (X['小米'][0] + D[0], X['小米'][1] + D[1])

# ———— SVG 小工具：颜色只用 CSS 变量 ————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def arrow(fid, x1, y1, x2, y2, col, w=2.5):
    ang = math.atan2(y2-y1, x2-x1); L = 11; a = 0.42
    bx, by = x2 - L*math.cos(ang), y2 - L*math.sin(ang)
    p1 = (x2 - L*math.cos(ang-a), y2 - L*math.sin(ang-a)); p2 = (x2 - L*math.cos(ang+a), y2 - L*math.sin(ang+a))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{s}</text>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
def plane(ox, oy, unit, xmax, ymax, xl, yl):
    b = arrow('', ox, oy, ox + xmax*unit + 14, oy, 'line', 1.5) + arrow('', ox, oy, ox, oy - ymax*unit - 14, 'line', 1.5)
    b += text(ox + xmax*unit + 14, oy + 22, xl, 'muted', 16, 'end') + text(ox + 8, oy - ymax*unit - 12, yl, 'muted', 16)
    return b
def f2(v):
    if abs(v) < 0.005: return '0'
    t = f'{v:.2f}'.rstrip('0')
    t = t + '0' if t.endswith('.') else t
    return t.replace('-', '−')
pct = lambda v: f'{v*100:.1f}%'

figs = {}
# 图 1：意思平面里的 4 个 x
ox, oy, u = 70, 240, 180
b = plane(ox, oy, u, 1.15, 1.15, '像手机', '像粮食')
lab_pos = {'粮油': (12, 4, 'start'), '店': (10, 4, 'start'), '买了': (0, 22, 'middle'), '小米': (10, -8, 'start')}
for t in T:
    x, y = X[t]; px, py = ox + x*u, oy - y*u; col = 'fg' if t == '小米' else 'muted'
    b += arrow('', ox, oy, px, py, col, 3 if t == '小米' else 2)
    dx, dy, an = lab_pos[t]; b += text(px + dx, py + dy, f'{t} ({f2(x)}, {f2(y)})', col, 16, an, weight=600 if t == '小米' else None)
figs['fig1'] = fig(480, 270, '四个 token 的向量 x 画在平面上', b, '图 1　四个 token 的向量 x。横坐标是「像手机」的程度，纵坐标是「像粮食」的程度（示意）。')

# 图 2：线索平面里的 q 和 4 个 k
ox, oy, u = 150, 150, 120
b = arrow('', ox - 1.2*u, oy, ox + 1.35*u, oy, 'line', 1.5) + arrow('', ox, oy + 1.15*u, ox, oy - 0.9*u, 'line', 1.5)
kp = {'粮油': (8, 16, 'start'), '店': (8, -6, 'start'), '买了': (-6, -8, 'end'), '小米': (6, -10, 'start')}
for t in T:
    k = K[t]; px, py = ox + k[0]*u, oy - k[1]*u
    b += arrow('', ox, oy, px, py, 'accent', 2.2)
    dx, dy, an = kp[t]; b += text(px + dx, py + dy, f'{t} ({f2(k[0])}, {f2(k[1])})', 'accent', 16, an)
px, py = ox + q[0]*u, oy - q[1]*u
b += arrow('', ox, oy, px, py, 'warn', 3.5)
b += text(px + 10, py + 22, f'q ({f2(q[0])}, {f2(q[1])})', 'warn', 16, 'start', weight=600)
figs['fig2'] = fig(480, 300, '线索平面里小米的查询 q 和四个 token 的键 k', b, '图 2　橙色是「小米」的查询 q，蓝色是每个 token 的键 k。和 q 方向越接近、越长的 k，点积越大。')

# 图 3：两种比法的条形对比
def bars(title_l, vals_l, fmt_l, title_r, vals_r, fmt_r, hi_l, hi_r, h=40):
    b = text(70, 24, title_l, 'muted', 16) + text(290, 24, title_r, 'muted', 16)
    for i, t in enumerate(T):
        y = 44 + i*h
        b += text(60, y + 17, t, 'fg', 16, 'end')
        for x0, vals, fmt, hi, mx in ((70, vals_l, fmt_l, hi_l, max(vals_l.values())), (290, vals_r, fmt_r, hi_r, max(vals_r.values()))):
            wv = 118*vals[t]/mx; col = 'warn' if t == hi else 'line'
            b += f'<rect x="{x0}" y="{y}" width="{max(wv,1):.1f}" height="24" rx="4" {C(col)}/>'
            b += text(x0 + wv + 6, y + 18, fmt(vals[t]), 'warn' if t == hi else 'muted', 16)
    return b
figs['fig3'] = fig(480, 44 + 4*40 + 6, '两种比法：x 的相似度与 q 点乘 k', bars('比 x 的相似度（余弦）', COS, lambda v: f'{v:.3f}', '比 q·k（点积）', S, f2, '小米', '粮油'),
                   '图 3　左边直接比向量 x：最像「小米」的是它自己。右边用 q 去对 k：分数最高的是「粮油」。')

# 图 4：softmax 前后
figs['fig4'] = fig(480, 44 + 4*40 + 6, '点积分数经过 softmax 变成份额', bars('分数 s', S, f2, '份额 w（softmax 后）', W1, pct, '粮油', '粮油'),
                   '图 4　左边是分数，右边是 softmax 之后的份额，四个份额加起来是 100%。顺序不变，差距被指数放大。')

# 图 5：缩放前后
figs['fig5'] = fig(480, 44 + 4*40 + 6, '除以根号 2 之前和之后的份额', bars('不缩放', W1, pct, f'除以 √2 之后', W2, pct, '粮油', '粮油'),
                   '图 5　除以 √2 之后，第一名的份额从 47.8% 降到 40.8%，其他 token 分到的更多。')

# 图 6：加权的 v 首尾相接，加到 x 上
ox, oy, u = 70, 300, 160
b = plane(ox, oy, u, 1.0, 1.75, '像手机', '像粮食')
x = X['小米']; px, py = ox + x[0]*u, oy - x[1]*u
b += arrow('', ox, oy, px, py, 'muted', 3) + text(px + 10, py + 18, 'x（原来的小米）', 'muted', 16)
cur = list(x)
order = sorted(T, key=lambda t: -W2[t])
small = []
for t in order:
    d = (W2[t]*V[t][0], W2[t]*V[t][1])
    if math.hypot(*d) < 0.01: continue
    a = (ox + cur[0]*u, oy - cur[1]*u); cur = [cur[0] + d[0], cur[1] + d[1]]; c2 = (ox + cur[0]*u, oy - cur[1]*u)
    b += arrow('', a[0], a[1], c2[0], c2[1], 'accent', 2.2)
    if math.hypot(*d) * u < 30: small.append((t, c2)); continue
    mx, my = (a[0] + c2[0])/2, (a[1] + c2[1])/2
    b += text(mx + 22, my + 6, f'{t} ×{W2[t]*100:.1f}%', 'accent', 16, 'start')
ex, ey = ox + XP[0]*u, oy - XP[1]*u
b += arrow('', ox, oy, ex, ey, 'warn', 3.5) + text(ex + 10, ey + 4, f"x′ ({XP[0]:.2f}, {XP[1]:.2f})", 'warn', 16, 'start', weight=600)
figs['fig6'] = fig(480, 330, '加权的值向量首尾相接，加到原来的小米向量上', b, '图 6　灰色是原来的 x，蓝色是按份额缩小后的各个 v，首尾相接（「店」「买了」两段太短，在箭头末端几乎看不见）；橙色是加完之后的 x′，比原来更偏向「像粮食」。')

# 供实验页使用的数据
toy = {'tokens': T, 'x': X, 'WQ': WQ, 'WK': WK, 'WV': WV, 'q': q, 'k': K, 'v': V, 's': S}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False))

# 填充文章
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
left = re.findall(r'\{\{[a-z0-9]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/attention-qkv.md').write_text(src, encoding='utf-8')
print('ok', {t: round(W2[t], 3) for t in T}, 'x′', tuple(round(v, 3) for v in XP))
