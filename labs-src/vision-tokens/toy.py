"""「模型是怎么看图的」一讲的贯穿算例：文章分镜图与实验页共用这组数。
运行：python3 labs-src/vision-tokens/toy.py  → 生成 src/content/blog/vision-tokens.md（由 article.src.md 填入图和数字）
"""
import math, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# ———— 贯穿全文的小图：4×4 灰度，0 = 黑，1 = 白 ————
IMG = [[1, 1, 0, 0],
       [1, 1, 0, 0],
       [1, 0, 0, 0],
       [1, 0, 0, 0]]
NAMES = ['左上', '右上', '左下', '右下']
CORNER = [(0, 0), (0, 2), (2, 0), (2, 2)]           # 每块左上角像素的 (行, 列)

def patches(img):
    out = []
    for r, c in CORNER:
        out.append([img[r][c], img[r][c+1], img[r+1][c], img[r+1][c+1]])   # 按行展开：a b / c d
    return out

# 把 4 个数变成 2 个数：亮度 = 平均值；竖边 = (左列 − 右列) / 2
WE = ((0.25, 0.25, 0.25, 0.25), (0.5, -0.5, 0.5, -0.5))
def embed(p): return tuple(sum(w*v for w, v in zip(row, p)) for row in WE)
POS = [(-0.1, 0.1), (0.1, 0.1), (-0.1, -0.1), (0.1, -0.1)]
P = patches(IMG)
E = [embed(p) for p in P]
H = [(e[0]+p[0], e[1]+p[1]) for e, p in zip(E, POS)]
mean = lambda vs: (sum(v[0] for v in vs)/len(vs), sum(v[1] for v in vs)/len(vs))

# ———— CLIP：三张图、三句描述 ————
IMG_B = [row[::-1] for row in IMG]                   # 左右镜像：右边亮
IMG_C = [[1]*4 for _ in range(4)]                    # 全亮
IMG_A2 = [[0, 0, 1, 1], [0, 0, 1, 1], [1, 0, 0, 0], [1, 0, 0, 0]]   # 亮块挪到右上：平均值不变
IMGS = {'A': IMG, 'B': IMG_B, 'C': IMG_C}
CAPS = ['左边亮', '右边亮', '全亮']
TXT = [(0.6, 0.8), (0.6, -0.8), (1.0, 0.0)]
TAU = 0.1
def unit(v): n = math.hypot(*v); return (v[0]/n, v[1]/n)
POOL = {k: mean([embed(p) for p in patches(m)]) for k, m in IMGS.items()}
POOL_A2 = mean([embed(p) for p in patches(IMG_A2)])
COS = {k: [unit(POOL[k])[0]*t[0] + unit(POOL[k])[1]*t[1] for t in TXT] for k in IMGS}
def softmax(xs):
    e = [math.exp(x) for x in xs]; s = sum(e); return e, s, [v/s for v in e]
ROWS = {k: softmax([c/TAU for c in COS[k]]) for k in IMGS}
LOSS = {k: -math.log(ROWS[k][2][i]) for i, k in enumerate(IMGS)}

# ———— 接进大模型：投影 + 文字 token 看图 ————
WP = ((1, 1), (-1, 1))
mv = lambda W, x: (W[0][0]*x[0] + W[0][1]*x[1], W[1][0]*x[0] + W[1][1]*x[1])
Z = [mv(WP, h) for h in H]
Q = (1.0, 1.0)                                       # 「竖杠」这个 token 的查询
SC = [Q[0]*z[0] + Q[1]*z[1] for z in Z]
SCS = [s/math.sqrt(2) for s in SC]
AE, ASUM, AW = softmax(SCS)

# ———— 真实规模 ————
def claude_tokens(w, h, long_edge=1568, cap=1568):
    s = min(1, long_edge/max(w, h)); W, Hh = w*s, h*s
    while math.ceil(W/28)*math.ceil(Hh/28) > cap:
        s *= 0.999; W, Hh = w*s, h*s
    return round(W), round(Hh), math.ceil(W/28)*math.ceil(Hh/28)

# ———— SVG 小工具：颜色只用 CSS 变量（像素本身用固定的黑白灰，图片在深浅两色下应当一样） ————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def arrow(x1, y1, x2, y2, col, w=2.5):
    ang = math.atan2(y2-y1, x2-x1); L = 11; a = 0.42
    bx, by = x2 - L*math.cos(ang), y2 - L*math.sin(ang)
    p1 = (x2 - L*math.cos(ang-a), y2 - L*math.sin(ang-a)); p2 = (x2 - L*math.cos(ang+a), y2 - L*math.sin(ang+a))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{s}</text>'
def rect(x, y, w, h, col, rx=4, stroke=None, sw=1.5):
    st = f'fill:var(--{col})' if col else 'fill:none'
    if stroke: st += f';stroke:var(--{stroke});stroke-width:{sw}'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" style="{st}"/>'
def pix(x, y, s, v, num=True, size=16):
    g = round(255*v); fill = f'rgb({g},{g},{g})'; tc = '#111' if v > 0.5 else '#eee'
    b = f'<rect x="{x:.1f}" y="{y:.1f}" width="{s}" height="{s}" fill="{fill}" style="stroke:var(--muted);stroke-width:1"/>'
    if num: b += f'<text x="{x+s/2:.1f}" y="{y+s/2+size*0.35:.1f}" font-size="{size}" text-anchor="middle" fill="{tc}">{f2(v)}</text>'
    return b
def image(x, y, s, img, num=True, gap=0, size=16):
    b = ''
    for r in range(4):
        for c in range(4):
            gx = gap if c >= 2 else 0; gy = gap if r >= 2 else 0
            b += pix(x + c*s + gx, y + r*s + gy, s, img[r][c], num, size)
    return b
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
def plane(ox, oy, u, xmin, xmax, ymin, ymax, xl, yl, xl_above=False):
    b = arrow(ox + xmin*u, oy, ox + xmax*u + 14, oy, 'line', 1.5) + arrow(ox, oy - ymin*u, ox, oy - ymax*u - 14, 'line', 1.5)
    b += text(ox + xmax*u + 14, oy + (-10 if xl_above else 22), xl, 'muted', 16, 'end') + text(ox + 8, oy - ymax*u - 12, yl, 'muted', 16)
    return b
def f2(v):
    if abs(v) < 0.005: return '0'
    t = f'{v:.3f}'.rstrip('0').rstrip('.')
    return t.replace('-', '−')
def vec(v): return f'({f2(v[0])}, {f2(v[1])})'
pct = lambda v: f'{v*100:.1f}%'

figs = {}
# 图 1：小图本身
b = image(150, 20, 45, IMG)
b += text(150 + 90, 220, '4 × 4 = 16 个像素', 'muted', 16, 'middle')
figs['fig1'] = fig(480, 236, '一张 4 乘 4 的灰度小图，每格写着它的亮度', b,
                   '图 1　贯穿全讲的小图。每个格子是一个像素，格子里的数是亮度：0 是黑，1 是白。')

# 图 2：切成 4 块并展开
b = image(24, 30, 36, IMG, gap=14)
for i, (r, c) in enumerate(CORNER):
    x0 = 24 + c*36 + (14 if c else 0); y0 = 30 + r*36 + (14 if r else 0)
    b += rect(x0 - 3, y0 - 3, 78, 78, None, 6, 'accent', 2)
for i, p in enumerate(P):
    y = 30 + i*42
    b += text(250, y + 21, f'{NAMES[i]}', 'accent', 16, 'end')
    for j, v in enumerate(p):
        b += pix(262 + j*44, y, 34, v, True, 15)
b += text(262 + 2*44 - 5, 30 + 4*42 + 14, '每块按行展开成 4 个数', 'muted', 15, 'middle')
figs['fig2'] = fig(480, 230, '小图切成四块，每块展开成一行四个数', b,
                   '图 2　按 2 × 2 切成 4 块（蓝框）。每块按「先第一行、再第二行」展开成 4 个数。')

# 图 3：每块的向量（没有位置）
def vecplane(vs, labels, cap_label, cap, pos=False):
    ox, oy, u = 110, 230, 170
    b = plane(ox, oy, u, -0.3, 1.15, -0.25, 1.1, '亮度', '竖边', xl_above=not pos)
    offs = {0: (10, 18, 'start'), 1: (12, -6, 'start'), 2: (10, -8, 'start'), 3: (12, 18, 'start')}
    for i, v in enumerate(vs):
        px, py = ox + v[0]*u, oy - v[1]*u
        if math.hypot(*v) > 0.02: b += arrow(ox, oy, px, py, 'accent', 2.4)
        else: b += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" {C("accent")}/>'
    if not pos:
        b += text(ox + 1.0*u, oy + 24, f'左上 {vec(vs[0])}', 'accent', 16, 'middle')
        b += text(ox + 0.5*u + 12, oy - 1.0*u - 4, f'左下 {vec(vs[2])}', 'accent', 16, 'start')
        b += text(ox + 10, oy + 52, '右上、右下 都是 (0, 0)', 'warn', 16, 'start', weight=600)
    else:
        b += text(ox + vs[0][0]*u + 8, oy - vs[0][1]*u - 8, f'左上 {vec(vs[0])}', 'accent', 16, 'start')
        b += text(ox + vs[2][0]*u + 12, oy - vs[2][1]*u + 4, f'左下 {vec(vs[2])}', 'accent', 16, 'start')
        b += text(ox + vs[1][0]*u + 14, oy - vs[1][1]*u - 14, f'右上 {vec(vs[1])}', 'warn', 16, 'start', weight=600)
        b += text(ox + vs[3][0]*u + 14, oy - vs[3][1]*u + 24, f'右下 {vec(vs[3])}', 'warn', 16, 'start', weight=600)
    return fig(480, 290, cap_label, b, cap)
figs['fig3'] = vecplane(E, NAMES, '四块的向量画在亮度和竖边平面上', '图 3　每块变成一个 2 维向量：横轴是亮度，纵轴是竖边。右上、右下两块都是全黑，落在同一个点 (0, 0) 上。')
figs['fig4'] = vecplane(H, NAMES, '加上位置向量之后的四个向量', '图 4　加上位置向量之后，右上 (0.1, 0.1) 和右下 (0.1, −0.1) 分开了，其他两块只挪了一点。', pos=True)

# 图 5：两种遮罩
def mask(x0, y0, s, causal, title, labels):
    b = text(x0 + 2*s, y0 - 12, title, 'muted', 16, 'middle')
    for i in range(4):
        b += text(x0 - 8, y0 + i*s + s/2 + 6, labels[i], 'fg', 15, 'end')
        for j in range(4):
            on = (j <= i) or not causal
            b += rect(x0 + j*s + 2, y0 + i*s + 2, s - 4, s - 4, 'accent' if on else 'paper', 3, None if on else 'line', 1)
    return b
b = mask(78, 44, 36, True, '文字：只能看前面', ['粮油', '店', '买了', '小米'])
b += mask(318, 44, 36, False, '图像块：互相都能看', NAMES)
figs['fig5'] = fig(480, 200, '文字的因果遮罩与图像块的全连接注意力', b,
                   '图 5　每一行是一个 token 在看谁，蓝色格子表示能看。文字只能看自己和前面；图像块之间没有先后，每块都能看所有块。')

# 图 6：平均之后位置丢了
b = image(30, 30, 30, IMG, False) + image(210, 30, 30, IMG_A2, False)
b += text(90, 178, '亮块在左上', 'muted', 16, 'middle') + text(270, 178, '亮块在右上', 'muted', 16, 'middle')
b += rect(370, 62, 96, 56, 'paper', 8, 'warn', 2)
b += text(418, 86, '两张的平均都是', 'warn', 13, 'middle') + text(418, 108, vec(POOL['A']), 'warn', 16, 'middle', weight=600)
b += arrow(336, 90, 364, 90, 'line', 1.5)
figs['fig6'] = fig(480, 196, '两张不同的图，四块向量取平均后得到同一个向量', b,
                   '图 7　两张图的四块其实一样，只是放的位置不同。四个向量取平均，得到的都是 (0.375, 0.25)。')

# 图 7：CLIP 相似度矩阵
b = ''
x0, y0, cw, ch = 150, 70, 100, 44
for j, c in enumerate(CAPS): b += text(x0 + j*cw + cw/2, y0 - 14, f'「{c}」', 'ok', 16, 'middle')
for i, k in enumerate(IMGS):
    b += image(30, y0 + i*ch + 4, 9, IMGS[k], False)
    b += text(110, y0 + i*ch + 28, f'图 {k}', 'fg', 16, 'middle')
    for j in range(3):
        on = i == j
        b += rect(x0 + j*cw + 4, y0 + i*ch + 4, cw - 8, ch - 8, 'accent' if on else 'paper', 6, None if on else 'line', 1)
        b += text(x0 + j*cw + cw/2, y0 + i*ch + 28, f'{COS[k][j]:.3f}', '#fff' if False else ('bg' if on else 'fg'), 16, 'middle', weight=600 if on else None)
b += text(240, 22, '每格 = 图向量和文字向量的余弦', 'muted', 15, 'middle')
figs['fig7'] = fig(480, 210, '三张图和三句描述两两之间的余弦相似度', b,
                   '图 6　一批里有 3 张图、3 句描述。对角线（蓝色）是配对的那一格，训练要让它在每一行里最大。')

# 图 8：序列
toks = [('图', 'accent')]*4 + [('竖杠', 'warn'), ('在', 'muted'), ('哪', 'muted'), ('？', 'muted')]
b = ''
w = 52
for i, (t, col) in enumerate(toks):
    x = 18 + i*(w + 4)
    b += rect(x, 40, w, 40, 'paper', 6, col, 2)
    lab = NAMES[i] if i < 4 else t
    b += text(x + w/2, 66, lab, col if i < 4 else 'fg', 15, 'middle')
b += text(18 + 2*(w+4) - 2, 106, '4 个视觉 token', 'accent', 15, 'middle')
b += text(18 + 6*(w+4) - 2, 106, '文字 token', 'muted', 15, 'middle')
b += text(240, 24, '送进大模型的一整串', 'muted', 15, 'middle')
figs['fig8'] = fig(480, 124, '视觉 token 排在文字 token 前面组成一串', b,
                   '图 8　投影后的 4 个块就是 4 个 token，和问题里的文字 token 排成一串，一起送进大模型。')

# 图 9：注意力份额叠在图上
b = image(40, 30, 40, IMG, False, gap=10)
for i, (r, c) in enumerate(CORNER):
    x0 = 40 + c*40 + (10 if c else 0); y0 = 30 + r*40 + (10 if r else 0)
    b += f'<rect x="{x0:.1f}" y="{y0:.1f}" width="80" height="80" rx="4" style="fill:var(--warn);fill-opacity:{min(0.55, AW[i]*0.9):.2f};stroke:var(--warn);stroke-width:{1+5*AW[i]:.1f}"/>'
    b += f'<text x="{x0+40:.1f}" y="{y0+47:.1f}" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--fg);paint-order:stroke;stroke:var(--bg);stroke-width:4">{pct(AW[i])}</text>'
for i in range(4):
    y = 44 + i*34
    b += text(290, y + 16, NAMES[i], 'fg', 16, 'end')
    b += rect(300, y, 110*AW[i]/max(AW), 22, 'warn' if i == 2 else 'line', 4)
    b += text(306 + 110*AW[i]/max(AW), y + 17, pct(AW[i]), 'warn' if i == 2 else 'muted', 16)
figs['fig9'] = fig(480, 224, '「竖杠」这个 token 分给四个图像块的注意力份额', b,
                   '图 9　「竖杠」的注意力，橙色越深分得越多。一半以上落在左下那块，也就是竖杠所在的地方。')

# 图 10：真实规模的 token 数
real = [('LLaVA-1.5，336 × 336', 576), ('Qwen2-VL，224 × 224', 64), ('Claude，1000 × 1000', claude_tokens(1000, 1000)[2]),
        ('Claude，1920 × 1080', claude_tokens(1920, 1080)[2]), ('一页 A4 中文文字', 1000)]
b = ''
mx = max(v for _, v in real)
for i, (n, v) in enumerate(real):
    y = 16 + i*40
    b += text(8, y + 17, n, 'fg', 15)
    col = 'muted' if i == 4 else 'accent'
    b += rect(180, y, 230*v/mx, 24, 'line' if i == 4 else 'accent', 4)
    b += text(186 + 230*v/mx, y + 18, f'{"约 " if i == 4 else ""}{v:,}', col, 15)
figs['fig10'] = fig(480, 216, '几种真实模型里一张图占多少 token', b,
                    '图 10　一张图占的 token 数。最后一行是对照：一页 A4 的中文文字大约 1,000 个 token（估算）。')

# 供实验页使用的数据
toy = {'img': IMG, 'WE': WE, 'pos': POS, 'txt': TXT, 'caps': CAPS, 'tau': TAU, 'WP': WP, 'q': Q,
       'E': E, 'H': H, 'Z': Z, 'attn': AW, 'cos': COS}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False))

# 文中要用的数字
nums = {
    'cosA': ' / '.join(f'{c:.3f}' for c in COS['A']),
    'pA': ' / '.join(pct(p) for p in ROWS['A'][2]),
}
print('E', E); print('H', H); print('pool', POOL, POOL_A2); print('cos', COS)
for k in IMGS: print(k, [round(x, 3) for x in ROWS[k][0]], round(ROWS[k][1], 3), [round(p, 4) for p in ROWS[k][2]], 'loss', round(LOSS[k], 3))
print('Z', Z, 'SC', SC, 'SCS', [round(s, 3) for s in SCS], 'e', [round(e, 3) for e in AE], round(ASUM, 3), [round(w, 4) for w in AW])
print('claude', claude_tokens(1000, 1000), claude_tokens(1920, 1080), claude_tokens(3840, 2160))

src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
left = re.findall(r'\{\{[a-z0-9]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/vision-tokens.md').write_text(src, encoding='utf-8')
print('ok')
