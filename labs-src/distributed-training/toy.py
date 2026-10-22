"""分布式训练一讲的贯穿算例：文章分镜图、文中数字与实验页共用这组数。
运行：python3 labs-src/distributed-training/toy.py
  → 生成 src/content/blog/distributed-training.md（把 article.src.md 里的 {{figN}} 与 {{n:名字}} 填好）
  → 写出 toy.json（check_lab.mjs 用实验页里同一份计算代码核对这些数）
单位：GB = 10^9 B；带宽 GB/s = 10^9 B/s。
"""
import math, json, pathlib, re, struct
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
N = {}          # 文中数字：{{n:名字}}
def put(k, v): N[k] = v; return v
def g(v, nd=1): return f'{v:,.{nd}f}'
GB = 1e9

# ———— 1. 模型：按 config.json 的架构数参数 ————
MODELS = {
    'Llama-3-8B':   dict(L=32,  h=4096,  ffn=14336, a=32,  kv=8, V=128256),
    'Llama-3-70B':  dict(L=80,  h=8192,  ffn=28672, a=64,  kv=8, V=128256),
    'Llama-3-405B': dict(L=126, h=16384, ffn=53248, a=128, kv=8, V=128256),
}
def count(m):
    hd = m['h'] // m['a']
    attn = m['h'] * m['h'] * 2 + m['h'] * m['kv'] * hd * 2       # q、o 各 h×h；k、v 各 h×(kv·hd)
    mlp = 3 * m['h'] * m['ffn']                                   # gate、up、down
    norm = 2 * m['h']
    layer = attn + mlp + norm
    emb = m['V'] * m['h'] * 2                                     # 输入嵌入 + 输出层（不共享）
    return dict(attn=attn, mlp=mlp, norm=norm, layer=layer, emb=emb, total=layer * m['L'] + emb + m['h'])
for k, m in MODELS.items(): m.update(count(m))
M8 = MODELS['Llama-3-8B']; P8 = M8['total']
put('p8', f'{P8:,}'); put('p8b', g(P8 / 1e9, 2))
put('attn8', f"{M8['attn']:,}"); put('mlp8', f"{M8['mlp']:,}"); put('layer8', f"{M8['layer']:,}"); put('emb8', f"{M8['emb']:,}")
put('layers8', f"{M8['layer'] * 32:,}")

# ———— 2. 每参数字节：混合精度 Adam（ZeRO 论文 2Ψ + 2Ψ + KΨ，K = 12）————
B_W, B_G, B_MASTER, B_M, B_V = 2, 2, 4, 4, 4
W8 = P8 * B_W / GB; put('w8', g(W8)); put('g8', g(P8 * B_G / GB)); put('o8', g(P8 * 4 / GB))
put('opt8', g(P8 * 12 / GB)); put('tot8', g(P8 * 16 / GB)); put('wg8', g(P8 * 4 / GB))
put('wgmv8', g(P8 * 12 / GB))
put('h100_need', g(P8 * 16 / GB / 80, 2))

# ———— 3. BF16 精度：1 附近的间距 ————
def bf16(x):   # 截成 bf16：取 float32 的高 16 位（四舍五入到最近偶数）
    b = struct.unpack('>I', struct.pack('>f', x))[0]
    b = (b + 0x7FFF + ((b >> 16) & 1)) & 0xFFFF0000
    return struct.unpack('>f', struct.pack('>I', b))[0]
def f32(x): return struct.unpack('>f', struct.pack('>f', x))[0]
UPD = 0.0003
assert bf16(1 + UPD) == 1.0 and f32(1 + UPD) != 1.0
put('bf_gap', '0.0078125'); put('bf_half', '0.00390625')
put('f32_after', f'{f32(1 + UPD):.7f}')
# 连加 100 次
acc_bf = 1.0
for _ in range(100): acc_bf = bf16(acc_bf + UPD)
acc_32 = 1.0
for _ in range(100): acc_32 = f32(acc_32 + UPD)
put('bf100', g(acc_bf, 4)); put('f100', g(acc_32, 4))

# ———— 4. 激活值（Korthikanti 等 2022，每层 sbh(34 + 5as/h) 字节，16 位存储）————
s, b, h, L, a = 8192, 1, 4096, 32, 32
put('sbh', f'{s * b * h:,}')
ACT_LAYER = 34 * s * b * h; ACT_S2 = 5 * a * s * s * b
put('act_layer', g(ACT_LAYER / GB, 2)); put('act_all', g(ACT_LAYER * L / GB))
put('act_s2_layer', g(ACT_S2 / GB, 1)); put('act_s2_all', g((ACT_LAYER + ACT_S2) * L / GB, 0))
put('ratio_s2', g(5 * a * s / h, 0))
RC_LAYER = 2 * s * b * h
put('rc_layer', g(RC_LAYER / 1e6, 0)); put('rc_all', g(RC_LAYER * L / GB, 2))
put('act_ratio', g(ACT_LAYER / RC_LAYER, 0))
put('tot8_act', g(P8 * 16 / GB + ACT_LAYER * L / GB))

# ———— 5. 计算量：每参数每 token 前向 2、反向 4 次浮点运算 ————
FLOP_SEQ = 6 * P8 * s
put('flop_seq', f'{FLOP_SEQ:.3e}'.replace('e+14', ' \\times 10^{14}'))
TFL = 400e12     # Llama 3 报告 16K 卡时每卡 400 TFLOPs
T_SEQ = FLOP_SEQ / TFL; put('t_seq', g(T_SEQ, 2))

# ———— 6. 数据并行玩具：y = w x，4 个数据点、4 张卡 ————
DATA = [(1, 2), (2, 3), (3, 7), (4, 7)]; W0 = 1.0
GR = [2 * (W0 * x - y) * x for x, y in DATA]
GFULL = sum(GR) / 4
put('dp_avg', g(GFULL, 1))

# ———— 7. 环形 all-reduce 玩具：4 张卡、每张 4 个梯度 ————
G0 = [[1, 0, 2, 1], [2, 1, 0, 3], [0, 3, 1, 2], [1, 2, 1, 0]]
NR = 4
def ring(G):
    n = len(G); st = [r[:] for r in G]; hist = [([r[:] for r in st], [])]
    for k in range(n - 1):                 # reduce-scatter：第 k 步，卡 i 把块 (i − k) mod n 发给 i + 1，对方加上
        sends = [(i, (i - k) % n, st[i][(i - k) % n]) for i in range(n)]
        for i, c, v in sends: st[(i + 1) % n][c] += v
        hist.append(([r[:] for r in st], [((i + 1) % n, c) for i, c, _ in sends]))
    for k in range(n - 1):                 # all-gather：第 k 步，卡 i 把块 (i + 1 − k) mod n 发给 i + 1，对方覆盖
        sends = [(i, (i + 1 - k) % n, st[i][(i + 1 - k) % n]) for i in range(n)]
        for i, c, v in sends: st[(i + 1) % n][c] = v
        hist.append(([r[:] for r in st], [((i + 1) % n, c) for i, c, _ in sends]))
    return hist
HIST = ring(G0)
SUMS = [sum(G0[i][c] for i in range(NR)) for c in range(NR)]
assert all(r == SUMS for r in HIST[-1][0])
put('ring_sum', ', '.join(str(v) for v in SUMS))
# 通信量与时间
def ring_bytes(S, n): return 2 * (n - 1) / n * S
def ring_time(S, n, B): return ring_bytes(S, n) / B
NVL, NET = 450e9, 50e9   # NVLink 每方向 450 GB/s；RoCE/IB 400 Gbps = 50 GB/s
GRAD8 = P8 * 2
put('grad8', g(GRAD8 / GB, 2))
put('dp_send', g(ring_bytes(GRAD8, 8) / GB, 2))
put('dp_nvl', g(ring_time(GRAD8, 8, NVL) * 1e3, 1)); put('dp_net', g(ring_time(GRAD8, 8, NET) * 1e3, 0))
put('naive_send', g(7 * GRAD8 / GB, 1))
put('naive_nvl', g(2 * 7 * GRAD8 / NVL * 1e3, 0))

# ———— 8. ZeRO：Ψ 个参数，N_d 张卡 ————
def zero(psi, nd, stage, K=12):
    return [(2 + 2 + K) * psi, (2 + 2) * psi + K * psi / nd, 2 * psi + (2 + K) * psi / nd, (2 + 2 + K) * psi / nd][stage]
Z8 = [zero(P8, 8, st) / GB for st in range(4)]
for st in range(4): put(f'z8_{st}', g(Z8[st]))
ZP = [zero(7.5e9, 64, st) / GB for st in range(4)]
put('zp0', g(ZP[0], 0)); put('zp1', g(ZP[1])); put('zp2', g(ZP[2])); put('zp3', g(ZP[3], 2))
put('z3_act', g(Z8[3] + (RC_LAYER * L + ACT_LAYER) / GB)); put('rc_tot', g((RC_LAYER * L + ACT_LAYER) / GB, 1))
put('z3_noact', g(Z8[3] + ACT_LAYER * L / GB))

# ———— 9. 张量并行玩具：x(1×2) · A(2×4) → ReLU → · B(4×2) ————
X = [1, 2]
A = [[1, 0, -1, -2], [0, 1, 1, 0.5]]
Bm = [[1, 0], [0, 1], [1, 1], [2, -1]]
relu = lambda v: max(0, v)
def vecmat(x, M): return [sum(x[i] * M[i][j] for i in range(len(x))) for j in range(len(M[0]))]
Z = vecmat(X, A); R = [relu(v) for v in Z]; Y = vecmat(R, Bm)
Z0_, Z1_ = Z[:2], Z[2:]
R0, R1 = [relu(v) for v in Z0_], [relu(v) for v in Z1_]
Y0 = vecmat(R0, Bm[:2]); Y1 = vecmat(R1, Bm[2:])
assert [Y0[j] + Y1[j] for j in range(2)] == Y
# 错误切法：按行切 A（每张卡拿 x 的一个数和 A 的一行），各自 ReLU 再相加
P0 = [X[0] * v for v in A[0]]; P1 = [X[1] * v for v in A[1]]
WR = [relu(p) + relu(q) for p, q in zip(P0, P1)]
assert WR != R
def fv(v): return '(' + ',\\ '.join(fm(t) for t in v) + ')'
def fm(t): return (str(int(t)) if float(t).is_integer() else str(t)).replace('-', '-')
TPN = dict(Z=Z, R=R, Y=Y, Y0=Y0, Y1=Y1, P0=P0, P1=P1, WR=WR)
put('tp_z', fv(Z)); put('tp_r', fv(R)); put('tp_y', fv(Y)); put('tp_y0', fv(Y0)); put('tp_y1', fv(Y1))
put('tp_p0', fv(P0)); put('tp_p1', fv(P1)); put('tp_wr', fv(WR))
# Llama-3-8B 张量并行 t = 8 的通信
ACTMSG = s * b * h * 2
put('tp_msg', g(ACTMSG / 1e6, 1))
NAR = 4 * L
put('tp_nar', NAR)
T_AR_NVL = ring_time(ACTMSG, 8, NVL); T_AR_NET = ring_time(ACTMSG, 8, NET)
put('tp_ar_nvl', g(T_AR_NVL * 1e3, 2)); put('tp_ar_net', g(T_AR_NET * 1e3, 2))
put('tp_tot_nvl', g(T_AR_NVL * NAR * 1e3, 0)); put('tp_tot_net', g(T_AR_NET * NAR * 1e3, 0))
T_SEQ8 = T_SEQ / 8; put('t_seq8', g(T_SEQ8 * 1e3, 0))
put('tp_frac_nvl', g(T_AR_NVL * NAR / T_SEQ8 * 100, 0)); put('tp_frac_net', g(T_AR_NET * NAR / T_SEQ8, 1))
put('dp_frac_net', g(ring_time(GRAD8, 8, NET) / T_SEQ * 100, 0))

# ———— 10. 流水线：p 段、m 个微批次，气泡 = (p − 1)/(m + p − 1) ————
def bubble(p, m): return (p - 1) / (m + p - 1)
for m_ in (1, 4, 16, 32): put(f'bub4_{m_}', g(bubble(4, m_) * 100, 1))

# ———— 11. Llama 3 405B（报告表 4，2026-10 核实）————
M405 = MODELS['Llama-3-405B']; P405 = M405['total']
put('p405', g(P405 / 1e9, 1)); put('p405_full', f'{P405:,}')
put('s405', g(P405 * 16 / 1e12, 2)); put('cards405', g(P405 * 16 / 80e9, 0))
TP, CP, PP, DP = 8, 1, 16, 128
put('ll_gpus', f'{TP * CP * PP * DP:,}')
put('ll_tokens', f'{8192 * 16 * DP:,}')
PG = P405 / (TP * PP); put('ll_pergpu', g(PG / 1e9, 2))
put('ll_w', g(PG * 2 / GB, 2)); put('ll_rest', g(PG * 14 / DP / GB, 2)); put('ll_states', g(PG * (2 + 14 / DP) / GB, 1))
FL = 6 * P405 * 15.6e12; put('ll_flops', f'{FL:.2e}')
put('ll_days', g(3.8e25 / (16384 * 400e12) / 86400, 0))
put('ll_card_days', g(30.84e6 / 16384 / 24, 0))
put('ll_card_tflops', g(3.8e25 / (30.84e6 * 3600) / 1e12, 0))
put('ll_bub', g(bubble(16, 16) * 100, 0))
put('ll_layers_per', g(126 / 16, 2))
put('ll_int_h', g(54 * 24 / 466, 1)); put('ll_unexp_h', g(54 * 24 / 419, 1))
P70 = MODELS['Llama-3-70B']['total']; put('p70', g(P70 / 1e9, 2)); put('s70', g(P70 * 16 / GB, 0)); put('c70', g(P70 * 16 / GB / 80, 1))
put('pp8_64', g(bubble(8, 64) * 100, 2)); put('pp8_63', g(bubble(8, 63) * 100, 2))

# ======================== SVG ========================
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def arrow(x1, y1, x2, y2, col, w=2.2):
    ang = math.atan2(y2-y1, x2-x1); Lh = 9; aa = 0.45
    bx, by = x2 - Lh*math.cos(ang), y2 - Lh*math.sin(ang)
    p1 = (x2 - Lh*math.cos(ang-aa), y2 - Lh*math.sin(ang-aa)); p2 = (x2 - Lh*math.cos(ang+aa), y2 - Lh*math.sin(ang+aa))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>')
def text(x, y, st, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{st}</text>'
def rect(x, y, w, hh, col, rx=3, op=None, stroke=None):
    o = f' fill-opacity="{op}"' if op is not None else ''
    sk = f';stroke:var(--{stroke});stroke-width:1.5' if stroke else ''
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{hh:.1f}" rx="{rx}" style="fill:var(--{col}){sk}"{o}/>'
def box(x, y, w, hh, col, rx=4, w_=1.5):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{hh:.1f}" rx="{rx}" {S_(col, w_)}/>'
def fig(w, hh, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {hh}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')
figs = {}
COLW, COLG, COLO, COLA = 'accent', 'warn', 'ok', 'muted'   # 权重 / 梯度 / 优化器状态 / 激活值：整讲同色

# 图 1：一个参数的 16 个字节
cw = 26; x0 = 32; b_ = ''
groups = [('权重', 'BF16', 2, COLW), ('梯度', 'BF16', 2, COLG), ('主权重', 'FP32', 4, COLO), ('一阶矩 m', 'FP32', 4, COLO), ('二阶矩 v', 'FP32', 4, COLO)]
i = 0
for name, fmt, n, col in groups:
    gx = x0 + i * cw
    for j in range(n): b_ += rect(gx + j * cw + 1.5, 46, cw - 3, 34, col, 3)
    mid = gx + n * cw / 2
    b_ += text(mid, 106, name, col, 16, 'middle') + text(mid, 128, fmt, 'muted', 15, 'middle') + text(mid, 150, f'{n} B', 'fg', 16, 'middle')
    i += n
for k in range(17):
    if k in (0, 2, 4, 8, 12, 16): b_ += f'<line x1="{x0 + k*cw:.1f}" y1="38" x2="{x0 + k*cw:.1f}" y2="88" {S_("muted", 1.2)}/>'
b_ += text(x0, 26, '一个可训练参数，每格 1 字节', 'muted', 16)
b_ += text(x0 + 16 * cw, 26, '共 16 B', 'fg', 16, 'end', weight=600)
figs['fig1'] = fig(480, 166, '一个参数在混合精度 Adam 训练里占的 16 个字节',
                   b_, '图 1　蓝色是推理也要的 BF16 权重；橙色是反向传播算出的梯度；绿色三块是优化器要的状态，都用 FP32 存。')

# 图 2：BF16 与 FP32 在 1 附近的刻度
lo, hi = 0.990, 1.0105
X0, X1 = 40, 450
px = lambda v: X0 + (v - lo) / (hi - lo) * (X1 - X0)
b_ = text(X0, 34, 'BF16 能表示的数', 'accent', 16)
y1 = 70
b_ += f'<line x1="{X0}" y1="{y1}" x2="{X1}" y2="{y1}" {S_("muted", 1.5)}/>'
ticks = [1 - 2**-8 * k for k in range(0, 3)] + [1 + 2**-7 * k for k in range(1, 2)]
for v in ticks:
    if lo <= v <= hi: b_ += f'<line x1="{px(v):.1f}" y1="{y1-10}" x2="{px(v):.1f}" y2="{y1+10}" {S_("accent", 2.5)}/>'
b_ += text(px(1), y1 + 30, '1', 'accent', 16, 'middle') + text(px(1 + 2**-7), y1 + 30, '1.0078125', 'accent', 16, 'middle')
b_ += text(px(1 - 2**-8), y1 + 30, '0.996', 'accent', 15, 'middle') + text(px(1 - 2**-7), y1 + 30, '0.992', 'accent', 15, 'middle')
v = 1 + UPD
b_ += f'<circle cx="{px(v):.1f}" cy="{y1}" r="5" {C("warn")}/>'
b_ += arrow(px(v), y1 - 12, px(1) + 3, y1 - 12, 'warn', 2) + text(px(v) + 8, y1 - 16, '1.0003 舍回 1', 'warn', 16)
y2 = 160
b_ += text(X0, y2 - 36, 'FP32 能表示的数（刻度密到画不出来）', 'ok', 16)
b_ += f'<line x1="{X0}" y1="{y2}" x2="{X1}" y2="{y2}" {S_("ok", 7)}/>'
b_ += f'<circle cx="{px(v):.1f}" cy="{y2}" r="5" {C("warn")}/>' + text(px(v) + 8, y2 + 26, '1.0003 留得住', 'warn', 16)
b_ += text(px(1), y2 + 26, '1', 'ok', 16, 'middle')
figs['fig2'] = fig(480, 200, 'BF16 和 FP32 在 1 附近的刻度，以及加上 0.0003 之后的结果',
                   b_, '图 2　BF16 在 1 和 1.0078125 之间没有别的数，1.0003 只能舍回 1，这一步更新就丢了。FP32 在同一段里有 65,536 个刻度。')

# 图 3：Llama-3-8B 的账，叠成一根条
def stackbar(y, segs, scale, x0=40, hh=30, labels=True):
    out = ''; x = x0
    for name, val, col in segs:
        w = val * scale
        out += rect(x + 1, y, w - 2, hh, col, 3)
        if labels and w > 24: out += text(x + w / 2, y + hh / 2 + 5.5, name, 'bg', 15, 'middle')
        x += w
    return out, x
sc = 400 / 140
b_ = ''
for t in (0, 40, 80, 120):
    b_ += text(40 + t * sc, 200, f'{t} GB', 'muted', 15, 'middle')
b_ += f'<line x1="{40 + 80*sc:.1f}" y1="36" x2="{40 + 80*sc:.1f}" y2="182" {S_("fg", 1.8, "6 4")}/>'
b_ += text(40, 30, '推理：只要权重', 'muted', 16)
bb, xe = stackbar(42, [('', W8, COLW)], sc, labels=False); b_ += bb + text(xe + 8, 63, f'{N["w8"]} GB', 'fg', 16)
b_ += text(40, 104, '训练：混合精度 Adam', 'muted', 16)
bb, xe = stackbar(116, [('权重', W8, COLW), ('梯度', W8, COLG), ('主权重', 2 * W8, COLO), ('m', 2 * W8, COLO), ('v', 2 * W8, COLO)], sc); b_ += bb
b_ += text(xe - 2, 104, f'{N["tot8"]} GB', 'fg', 16, 'end', weight=600)
b_ += text(40 + 80 * sc + 6, 36 + 14, '一张 H100：80 GB', 'fg', 15)
figs['fig3'] = fig(480, 212, 'Llama-3-8B 推理与训练的显存对比，虚线是一张 H100 的 80 GB',
                   b_, '图 3　同一个 Llama-3-8B，推理只要 16.1 GB；训练要 128.5 GB，还没算激活值，已经超过一张 80 GB 的卡（虚线）。')

# 图 4：每层存什么（不重算 vs 全部重算），画 8 层示意
b_ = ''
def layers_row(y0, label, per, extra=None):
    out = text(40, y0 - 70, label, 'muted', 16)
    for k in range(8):
        x = 60 + k * 50
        hh = per * 50
        out += rect(x, y0 - hh, 30, hh, COLA, 3)
        out += box(x - 4, y0 + 4, 38, 18, 'line', 3) + text(x + 15, y0 + 18, f'{k+1}', 'muted', 13, 'middle')
    return out
b_ += layers_row(110, f'不重算：每层存 {N["act_layer"]} GB', 1.0)
b_ += layers_row(230, f'全部重算：每层只存输入 {N["rc_layer"]} MB', 2 / 34)
# 重算时，反向到第 6 层，临时把它的激活值算回来
x6 = 60 + 5 * 50
b_ += rect(x6, 230 - 50, 30, 50, COLA, 3, op=0.35, stroke='warn')
b_ += text(x6 + 40, 196, '反向到这一层时', 'warn', 15) + text(x6 + 40, 214, '临时重算出来', 'warn', 15)
b_ += text(440, 160 + 4, '…共 32 层', 'muted', 15, 'end')
figs['fig4'] = fig(480, 262, '不重算与全部重算时，每层留给反向传播的激活值',
                   b_, '图 4　灰色柱是每层为反向传播留着的激活值（画了前 8 层）。全部重算时每层只留一个输入，反向走到哪层，就用它把那一层的激活值临时算回来（橙框）。')

# 图 5：数据并行，4 张卡各一个数据点
b_ = ''
for k, ((x, y), gr) in enumerate(zip(DATA, GR)):
    bx = 20 + k * 115
    b_ += box(bx, 30, 100, 104, 'muted', 6)
    b_ += text(bx + 50, 22, f'卡 {k}', 'muted', 15, 'middle')
    b_ += text(bx + 50, 56, 'w = 1', COLW, 16, 'middle', italic=False)
    b_ += text(bx + 50, 82, f'({x}, {y})', 'fg', 16, 'middle')
    b_ += text(bx + 50, 120, f'g = {gr:g}'.replace('-', '−'), COLG, 16, 'middle', weight=600)
    b_ += arrow(bx + 50, 138, 240 + (bx + 50 - 240) * 0.25, 176, 'warn', 1.8)
b_ += rect(110, 180, 260, 36, 'paper', 6) + box(110, 180, 260, 36, 'warn', 6)
b_ += text(240, 204, f'平均 (−2 − 4 − 24 − 24)/4 = {GFULL:g}'.replace('-', '−'), COLG, 16, 'middle', weight=600)
figs['fig5'] = fig(480, 228, '数据并行：四张卡各有一份完整的 w，各算一个数据点的梯度，再求平均',
                   b_, '图 5　四张卡上的 w 一模一样（蓝色），各吃一个数据点，各算出一个梯度（橙色），平均之后是 −13.5，和一张卡吃下全部 4 个点算出来的完全相同。')

# 图 6 / 7：环形 all-reduce
def rg(rows):
    out = ''
    for st, recv, done, y0, lab in rows:
        out += text(14, y0 + 20, lab, 'muted', 15)
        for gi in range(NR):
            gx = 96 + gi * 96
            out += box(gx - 3, y0 - 3, 4 * 21 + 6, 34, 'muted', 5, 1)
            for c in range(NR):
                cx = gx + c * 21
                col = 'warn' if (gi, c) in recv else ('ok' if (gi, c) in done else None)
                if col: out += rect(cx + 1, y0, 19, 28, col, 3, op=0.2)
                out += text(cx + 10.5, y0 + 20, str(st[gi][c]), col or 'fg', 15, 'middle', weight=600 if col else None)
    return out
ys = [34 + k * 46 for k in range(4)]
head = ''.join(text(96 + gi * 96 + 42, 20, f'卡 {gi}', 'muted', 15, 'middle') for gi in range(NR))
DONE_RS = {(gi, (gi + 1) % NR) for gi in range(NR)}
rows = []
for k, lab in enumerate(['开始', '第 1 步', '第 2 步', '第 3 步']):
    st, recv = HIST[k]
    rows.append((st, [] if k == 3 else recv, DONE_RS if k == 3 else set(), ys[k], lab))
figs['fig6'] = fig(480, 34 + 4 * 46, '环形 all-reduce 的前半段 reduce-scatter：三步之后每张卡各有一块的总和',
                   head + rg(rows), '图 6　每张卡有 4 个梯度（4 块）。每一步每张卡把一块发给右边的卡（卡 3 发给卡 0），对方加到自己那一块上；橙色是这一步刚加过的块。三步之后，每张卡各有一块是 4 张卡的总和（绿色）。')
rows = []; done = set(DONE_RS)
for k, lab in enumerate(['第 4 步', '第 5 步', '第 6 步']):
    st, recv = HIST[4 + k]
    rows.append((st, set(recv), set(done), ys[k], lab)); done |= set(recv)
figs['fig7'] = fig(480, 34 + 3 * 46, '环形 all-reduce 的后半段 all-gather：再三步，每张卡都有全部总和',
                   head + rg(rows), '图 7　后半段照样每步往右传一块，但对方不再相加，而是直接换成收到的总和（橙色是这一步刚换的，绿色是已经到位的）。再走三步，四张卡都是 4, 6, 4, 6，all-reduce 完成。')

# 图 8：ZeRO 三个阶段，Llama-3-8B，8 张卡，每张卡的显存
sc = 400 / 140
b_ = ''
names = ['普通数据并行', 'ZeRO-1：切优化器状态', 'ZeRO-2：再切梯度', 'ZeRO-3：再切权重']
for st in range(4):
    y = 30 + st * 52
    nd = 8
    w_ = W8 if st < 3 else W8 / nd
    g_ = W8 if st < 2 else W8 / nd
    o_ = 6 * W8 if st < 1 else 6 * W8 / nd
    b_ += text(40, y, names[st], 'muted', 15)
    bb, xe = stackbar(y + 8, [('', w_, COLW), ('', g_, COLG), ('', o_, COLO)], sc, hh=22, labels=False)
    b_ += bb + text(min(xe + 8, 380), y + 25, f'{Z8[st]:.1f} GB', 'fg', 16, 'start' if xe < 372 else 'end', weight=600)
for t in (0, 40, 80, 120):
    b_ += text(40 + t * sc, 30 + 4 * 52 + 4, f'{t} GB', 'muted', 15, 'middle')
b_ += f'<line x1="{40 + 80*sc:.1f}" y1="14" x2="{40 + 80*sc:.1f}" y2="{30 + 4*52 - 14}" {S_("fg", 1.8, "6 4")}/>'
b_ += text(40 + 80 * sc + 6, 14, '80 GB', 'fg', 15)
figs['fig8'] = fig(480, 30 + 4 * 52 + 14, 'ZeRO 三个阶段下，Llama-3-8B 用 8 张卡训练时每张卡的模型状态显存',
                   b_, '图 8　Llama-3-8B、8 张卡，每张卡存的模型状态（不含激活值）。蓝色权重、橙色梯度、绿色优化器状态，每一阶段多切一样，切下来的那样只剩 1/8。')

# 图 9：张量并行，第一个矩阵按列切
def mat(x, y, M, cols=None, rows=None, cw=34, ch=28):
    out = ''
    for i, r in enumerate(M):
        for j, v in enumerate(r):
            col = (cols[j] if cols else None) or (rows[i] if rows else None)
            if col: out += rect(x + j * cw + 1, y + i * ch + 1, cw - 2, ch - 2, col, 3, op=0.18)
            out += text(x + j * cw + cw / 2, y + i * ch + 19, fm(v).replace('-', '−'), col or 'fg', 15, 'middle')
    out += box(x - 2, y - 2, len(M[0]) * cw + 4, len(M) * ch + 4, 'muted', 3, 1)
    return out
GA, GB_ = 'accent', 'ok'
b_ = text(20, 22, '完整算一遍', 'muted', 15)
b_ += text(20, 58, 'x', 'fg', 16, italic=True) + mat(40, 40, [X])
b_ += text(122, 58, '×', 'muted', 16)
b_ += text(150, 30, 'A', 'fg', 16, italic=True) + mat(140, 40, A, cols=[GA, GA, GB_, GB_])
b_ += text(290, 58, '=', 'muted', 16)
b_ += mat(308, 40, [Z], cols=[GA, GA, GB_, GB_], cw=34)
b_ += text(20, 130, 'ReLU', 'muted', 15) + text(140, 130, '把负数换成 0', 'muted', 15)
b_ += mat(308, 112, [R], cols=[GA, GA, GB_, GB_], cw=34)
b_ += arrow(376, 74, 376, 108, 'muted', 1.5)
b_ += text(20, 180, '切开：卡 0 拿 A 的前两列，卡 1 拿后两列', 'muted', 15)
b_ += text(20, 218, '卡 0', GA, 16) + mat(70, 200, [X]) + text(148, 218, '×', 'muted', 16) + mat(166, 200, [r[:2] for r in A], cols=[GA, GA]) + text(244, 218, '=', 'muted', 16) + mat(262, 200, [Z0_], cols=[GA, GA]) + text(340, 218, 'ReLU', 'muted', 15) + mat(384, 200, [R0], cols=[GA, GA])
b_ += text(20, 314, '卡 1', GB_, 16) + mat(70, 296, [X]) + text(148, 314, '×', 'muted', 16) + mat(166, 296, [r[2:] for r in A], cols=[GB_, GB_]) + text(244, 314, '=', 'muted', 16) + mat(262, 296, [Z1_], cols=[GB_, GB_]) + text(340, 314, 'ReLU', 'muted', 15) + mat(384, 296, [R1], cols=[GB_, GB_])
figs['fig9'] = fig(480, 360, '张量并行第一步：把矩阵 A 按列切成两半，两张卡各算一半',
                   b_, '图 9　上面是一张卡完整算的结果。下面把 A 按列切开：卡 0（蓝）算出前两个数，卡 1（绿）算出后两个数，各自做完 ReLU，拼起来和上面一模一样，中间不用通信。')

# 图 10：第二个矩阵按行切，最后相加
b_ = text(20, 22, '卡 0：自己那两个数 × B 的前两行', GA, 15)
b_ += mat(30, 36, [R0], cols=[GA, GA]) + text(108, 54, '×', 'muted', 16) + mat(126, 36, Bm[:2], rows=[GA, GA]) + text(204, 54, '=', 'muted', 16) + mat(222, 36, [Y0], cols=[GA, GA])
b_ += text(20, 122, '卡 1：自己那两个数 × B 的后两行', GB_, 15)
b_ += mat(30, 136, [R1], cols=[GB_, GB_]) + text(108, 154, '×', 'muted', 16) + mat(126, 136, Bm[2:], rows=[GB_, GB_]) + text(204, 154, '=', 'muted', 16) + mat(222, 136, [Y1], cols=[GB_, GB_])
b_ += arrow(296, 52, 350, 92, 'warn', 2) + arrow(296, 152, 350, 112, 'warn', 2)
b_ += text(362, 84, 'all-reduce', 'warn', 15) + text(362, 104, '相加', 'warn', 15)
b_ += mat(362, 116, [Y], cw=34)
b_ += text(362, 168, '= 一张卡算的', 'muted', 15) + text(362, 188, f'y = {N["tp_y"].replace(",\\ ", ", ")}', 'fg', 15)
figs['fig10'] = fig(480, 206, '张量并行第二步：矩阵 B 按行切，两张卡的部分结果相加',
                    b_, '图 10　B 按行切：每张卡只用自己手里那两个数，乘 B 里对应的两行，得到一个「部分和」。两个部分和相加（一次 all-reduce），就是完整的 y。')

# 图 11：流水线甘特图，p = 4，m = 1 与 m = 4
def gantt(y0, p, m, unit, label, x0=60):
    out = text(x0 - 50, y0 - 10, label, 'muted', 15)
    rowh = 24
    # GPipe：先全部前向，再全部反向；前向 1 格，反向 2 格
    for st in range(p):
        y = y0 + st * rowh
        out += text(x0 - 8, y + 17, f'卡 {st}', 'muted', 14, 'end')
        out += rect(x0, y + 2, (m + p - 1) * 3 * unit, rowh - 4, 'muted', 2, op=0.16)
        for k in range(m):
            t = st + k
            out += rect(x0 + t * unit + 0.8, y + 2, unit - 1.6, rowh - 4, 'accent', 2)
            if unit >= 14: out += text(x0 + t * unit + unit / 2, y + 17, str(k + 1), 'bg', 13, 'middle')
        for k in range(m):
            t = (m + p - 1) + (p - 1 - st) + k        # 反向从最后一段开始
            out += rect(x0 + t * unit + (t - (m + p - 1)) * unit + 0.8, y + 2, 2 * unit - 1.6, rowh - 4, 'warn', 2)
            if unit >= 14: out += text(x0 + t * unit + (t - (m + p - 1)) * unit + unit, y + 17, str(k + 1), 'bg', 13, 'middle')
    return out
b_ = gantt(30, 4, 1, 32, f'm = 1：气泡 {N["bub4_1"]}%')
b_ += gantt(158, 4, 4, 19, f'm = 4：气泡 {N["bub4_4"]}%')
b_ += arrow(60, 272, 460, 272, 'muted', 1.2) + text(460, 290, '时间', 'muted', 14, 'end')
figs['fig11'] = fig(480, 296, '流水线并行的甘特图：4 段流水线，1 个和 4 个微批次',
                    b_, '图 11　4 张卡各放 1/4 的层。蓝格是前向（数字是第几个微批次），橙格是反向（约为前向的 2 倍长），浅灰是空等的「气泡」。批次切成 4 个微批次后，空等的比例从 75% 降到 42.9%。')

# 图 12：3D 并行：Llama 3 405B 的 16,384 张卡
b_ = ''
sw = 23.5
for rep, y in ((0, 40), (1, 104), (2, 168)):
    b_ += text(14, y + 26, f'副本 {rep + 1}' if rep < 2 else '副本 128', 'muted', 14)
    for sv in range(16):
        x = 76 + sv * sw
        b_ += box(x, y, sw - 4, 38, 'muted', 3, 1)
        for gg in range(8):
            gx = x + 2.5 + (gg % 2) * 8.5; gy = y + 3 + (gg // 2) * 8.2
            b_ += rect(gx, gy, 7, 6.6, 'accent', 1.2)
b_ += text(76 + 8 * sw, 160, '⋮', 'muted', 18, 'middle')
b_ += text(76, 26, '一台服务器 = 8 张卡，张量并行 TP = 8（NVLink）', 'accent', 14)
b_ += arrow(76, 90, 76 + 16 * sw - 4, 90, 'ok', 1.8) + text(76 + 8 * sw, 100, '', 'ok', 14, 'middle')
b_ += text(76 + 16 * sw - 4, 236, '一行 16 台：流水线 PP = 16，一行是一个完整模型', 'ok', 14, 'end')
b_ += arrow(468, 44, 468, 204, 'warn', 1.8)
b_ += text(76, 256, '共 128 行：数据并行 DP = 128，8 × 16 × 128 = 16,384 张卡', 'warn', 14)
figs['fig12'] = fig(480, 268, 'Llama 3 405B 的 3D 并行：一台服务器内张量并行，一行 16 台流水线，128 行数据并行',
                    b_, '图 12　Llama 3 405B 主训练阶段的切法（报告表 4）。每个小方块是一张 H100，蓝色方块 8 个一组在同一台服务器里。')

# ———— 写出 ————
toy = dict(P8=P8, P70=MODELS['Llama-3-70B']['total'], P405=P405, Z8=Z8, ZP=ZP,
           act_layer=ACT_LAYER, rc_layer=RC_LAYER, dp_nvl_ms=ring_time(GRAD8, 8, NVL) * 1e3, dp_net_ms=ring_time(GRAD8, 8, NET) * 1e3,
           tp_ar_nvl_ms=T_AR_NVL * 1e3, ring_sums=SUMS, tp=TPN, bub=[bubble(4, m_) for m_ in (1, 4, 16)],
           ll=dict(gpus=TP*CP*PP*DP, tokens=8192*16*DP, states_gb=PG * (2 + 14 / DP) / GB))
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False, indent=1))
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', str(v))
left = re.findall(r'\{\{[^}]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/distributed-training.md').write_text(src, encoding='utf-8')
print(json.dumps(N, ensure_ascii=False, indent=0))
