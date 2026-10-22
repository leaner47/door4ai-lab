"""推理服务一讲的贯穿算例：文章分镜图、文中数字与实验页共用这组数。
运行：python3 labs-src/inference-serving/toy.py
  → 生成 src/content/blog/inference-serving.md（把 article.src.md 里的 {{figN}} 与 {{n:名字}} 填好）
  → 写出 labs-src/inference-serving/toy.json（实验页 core 脚本用同一组常量，check_lab.mjs 逐项核对）

贯穿算例：一张 H100 SXM 跑 Llama-3-8B（BF16），每个用户的对话已有 1000 个 token。
规格（2026-10 核实）：H100 SXM 80 GB HBM3、3.35 TB/s、BF16 稠密 989.4 TFLOPS（NVIDIA 规格表）。
Llama-3-8B：8,030,261,248 个参数，32 层，8 个 KV 头 × 128 维，隐藏维 4096（Meta config.json）。
"""
import math, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# ———— 硬件与模型 ————
BW = 3.35e12          # B/s
PEAK = 989.4e12       # FLOP/s，BF16 稠密
MEM = 80e9            # B
NP = 8_030_261_248    # 参数个数
WB = 2 * NP           # BF16 权重字节
LAYERS, KVH, HD, DM = 32, 8, 128, 4096
KV_TOK = 2 * LAYERS * KVH * HD * 2      # 每个 token 的 K 和 V，BF16：131072 B
CTX = 1000

def step(B, L=CTX, g=1, wbytes=WB):
    """decode 一步：B 个用户，每人上下文 L，每人这一步算 g 个位置（投机解码验证时 g = γ + 1）。"""
    by = wbytes + B * L * KV_TOK
    fl = 2 * NP * B * g + 4 * L * DM * LAYERS * B * g
    tm, tc = by / BW, fl / PEAK
    return max(tm, tc), tm, tc, by, fl

T1, TM1, TC1, BY1, FL1 = step(1, 0)    # 第一步：先不算 KV cache
RIDGE = PEAK / BW
BMAX = int((MEM - WB) // (CTX * KV_TOK))
I_LIMIT = (2 * NP + 4 * CTX * DM * LAYERS) / (CTX * KV_TOK)   # B → ∞ 时的算术强度
TAB_B = [1, 8, 64, 256, BMAX]
TAB = [(B,) + step(B) for B in TAB_B]
SLA = 50                                  # token/s / 用户
B_SLA = int((BW / SLA - WB) // (CTX * KV_TOK))

# ———— 批处理：8 个请求，4 个槽 ————
REQ = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
OUT = [7, 2, 3, 8, 2, 6, 4, 3]
SLOTS = 4
def static_batch(L, S):
    t = 0; spans = []
    for i in range(0, len(L), S):
        b = L[i:i + S]
        for j, l in enumerate(b): spans.append((j, t, t + l))
        t += max(b)
    return t, spans
def cont_batch(L, S):
    free = [0] * S; spans = []
    for l in L:
        j = min(range(S), key=lambda k: free[k]); s = free[j]
        spans.append((j, s, s + l)); free[j] = s + l
    return max(e for _, _, e in spans), spans
ST_T, ST_SP = static_batch(OUT, SLOTS)
CB_T, CB_SP = cont_batch(OUT, SLOTS)
TOT_OUT = sum(OUT)

# ———— KV cache：预留 vs 分页（小例子） ————
MAXLEN = 12; LENS = [5, 9, 3]; BLK = 4; POOL = 36
RES_USED = sum(LENS); RES_ALLOC = MAXLEN * len(LENS)
PG_BLOCKS = [math.ceil(l / BLK) for l in LENS]; PG_ALLOC = sum(PG_BLOCKS) * BLK
# 真实规模：块 16 个 token
VB = 16
BLOCK_BYTES = VB * KV_TOK

# ———— prefix cache ————
SYS, OWN = 800, 200
SHARED_BLOCKS = SYS // VB
B_PREFIX = int((MEM - WB - SYS * KV_TOK) // (OWN * KV_TOK))
def prefill_time(n, prefix=0):
    """一次 prefill n 个新 token，前面已缓存 prefix 个。注意力：每个新位置看前面全部位置，约 n·prefix + n²/2 对，每对 Q·K 与加权 V 共 4 次运算 × 4096 维 × 32 层。"""
    pairs = n * prefix + n * n / 2
    fl = 2 * NP * n + 4 * pairs * DM * LAYERS
    return max(fl / PEAK, (WB + (n + prefix) * KV_TOK) / BW), fl / PEAK, (WB + (n + prefix) * KV_TOK) / BW
PF_FULL = prefill_time(CTX)[0]; PF_OWN, PF_OWN_C, PF_OWN_M = prefill_time(OWN, SYS)

# ———— 投机解码 ————
TOK3 = ['饭', '粥', '面']
P = [0.6, 0.3, 0.1]; Q = [0.5, 0.2, 0.3]
ALPHA = sum(min(a, b) for a, b in zip(P, Q))
RES = [max(a - b, 0) for a, b in zip(P, Q)]; RS = sum(RES); RESN = [v / RS for v in RES]
GAM = 4; C = 0.05
def exp_len(a, g): return (1 - a ** (g + 1)) / (1 - a) if a < 1 else g + 1
def speedup(a, g, c): return exp_len(a, g) / (g * c + 1)
E4 = exp_len(ALPHA, GAM); SP4 = speedup(ALPHA, GAM, C)
PK = [ALPHA ** k * (1 - ALPHA) for k in range(GAM)] + [ALPHA ** GAM]
BEST_G = max(range(1, 13), key=lambda g: speedup(ALPHA, g, C))
def spec_speed(B, a=ALPHA, g=GAM, c=C):
    td = step(B)[0]; tv = step(B, g=g + 1)[0]
    return exp_len(a, g) * td / (tv + g * c * td), td, tv
SPB1 = spec_speed(1); SPBS = spec_speed(B_SLA)

# ———— 数字格式 ————
def f(v, d=2):
    s = f'{v:,.{d}f}'
    return s.replace('-', '−')
def pct(v, d=1): return f'{v * 100:.{d}f}%'
N = {}
N['w_gb'] = f(WB / 1e9)
N['t1_ms'] = f(TM1 * 1e3)
N['fl1_g'] = f(FL1 / 1e9)
N['tc1_ms'] = f(TC1 * 1e3, 4)
N['tc1_us'] = f(TC1 * 1e6, 1)
N['util_w1'] = pct(TC1 / TM1, 2)
N['seq64'] = f(64 * TM1 * 1e3, 1)
N['tok1'] = f(1 / TM1, 0)
N['ratio1'] = f(TM1 / TC1, 0)
N['ridge'] = f(RIDGE, 0)
N['kv_tok'] = f(KV_TOK, 0)
N['kv_user_mb'] = f(CTX * KV_TOK / 1e6, 1)
N['kv_user_gb'] = f(CTX * KV_TOK / 1e9, 4)
N['bmax'] = str(BMAX)
N['free_gb'] = f((MEM - WB) / 1e9)
N['ilim'] = f(I_LIMIT, 0)
for B, t, tm, tc, by, fl in TAB:
    k = str(B)
    N[f'by{k}'] = f(by / 1e9); N[f't{k}'] = f(t * 1e3); N[f'tot{k}'] = f(B / t, 0); N[f'per{k}'] = f(1 / t, 1)
    N[f'tc{k}'] = f(tc * 1e3, 2); N[f'util{k}'] = pct(tc / t); N[f'kvgb{k}'] = f(B * CTX * KV_TOK / 1e9)
N['bsla'] = str(B_SLA)
t_s = step(B_SLA)[0]
N['tsla'] = f(t_s * 1e3); N['totsla'] = f(B_SLA / t_s, 0); N['persla'] = f(1 / t_s, 1)
N['st_t'] = str(ST_T); N['cb_t'] = str(CB_T); N['tot_out'] = str(TOT_OUT)
N['st_slots'] = str(ST_T * SLOTS); N['cb_slots'] = str(CB_T * SLOTS)
N['st_util'] = pct(TOT_OUT / (ST_T * SLOTS)); N['cb_util'] = pct(TOT_OUT / (CB_T * SLOTS))
N['st_avg'] = f(sum(e for _, _, e in ST_SP) / len(OUT), 3); N['cb_avg'] = f(sum(e for _, _, e in CB_SP) / len(OUT), 3)
N['res_waste'] = pct((RES_ALLOC - RES_USED) / RES_ALLOC); N['pg_waste'] = pct((PG_ALLOC - RES_USED) / PG_ALLOC)
N['block_mb'] = f(BLOCK_BYTES / 2**20, 0)
N['waste_avg'] = pct((VB - 1) / 2 / CTX, 2)
N['shared_mb'] = f(SYS * KV_TOK / 1e6, 1); N['own_mb'] = f(OWN * KV_TOK / 1e6, 1)
N['b_prefix'] = f(B_PREFIX, 0); N['shared_blocks'] = str(SHARED_BLOCKS)
N['pf_full'] = f(PF_FULL * 1e3, 1); N['pf_own'] = f(PF_OWN * 1e3, 1)
N['pf_save'] = pct(1 - PF_OWN / PF_FULL)
N['pf_own_c'] = f(PF_OWN_C * 1e3, 1); N['pf_own_m'] = f(PF_OWN_M * 1e3, 1)
# 只算权重时 batch 64
_t, _tm, _tc, _by, _fl = step(64, 0)
N['nk64_fl'] = f(_fl / 1e12, 2); N['nk64_tc'] = f(_tc * 1e3, 2); N['nk64_tot'] = f(64 / _t, 0)
# INT4（按组 128，每个权重约 4.125 位）
I4 = NP * 4.125 / 8
N['int4_gb'] = f(I4 / 1e9); N['int4_ms'] = f(I4 / BW * 1e3); N['int4_tok'] = f(BW / I4, 0)
# 投机解码：batch 1 时验证 5 个位置
_v = step(1, g=GAM + 1)
N['v1_ms'] = f(_v[0] * 1e3); N['v1_tc'] = f(_v[2] * 1e3, 3); N['d1_ms'] = f(step(1)[0] * 1e3)
N['attn_g'] = f(4 * CTX * DM * LAYERS / 1e9, 2); N['fl_tok_g'] = f((2 * NP + 4 * CTX * DM * LAYERS) / 1e9, 2)
N['res_alloc'] = str(RES_ALLOC); N['res_used'] = str(RES_USED); N['pg_alloc'] = str(PG_ALLOC)
N['alpha'] = f(ALPHA, 1); N['e4'] = f(E4, 4); N['sp4'] = f(SP4, 2); N['best_g'] = str(BEST_G)
N['sp_best'] = f(speedup(ALPHA, BEST_G, C), 2)
N['spb1'] = f(SPB1[0], 2); N['spbs'] = f(SPBS[0], 2)
N['spbs_td'] = f(SPBS[1] * 1e3, 1); N['spbs_tv'] = f(SPBS[2] * 1e3, 1)
N['spbs_tot'] = f((SPBS[2] + GAM * C * SPBS[1]) * 1e3, 1)

# ———— SVG 小工具：颜色只用 CSS 变量 ————
def C_(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:" + dash if dash else ""};fill:none"'
def arrow(x1, y1, x2, y2, col, w=2.2):
    ang = math.atan2(y2 - y1, x2 - x1); L = 10; a = 0.42
    bx, by = x2 - L * math.cos(ang), y2 - L * math.sin(ang)
    p1 = (x2 - L * math.cos(ang - a), y2 - L * math.sin(ang - a)); p2 = (x2 - L * math.cos(ang + a), y2 - L * math.sin(ang + a))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C_(col)}/>')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C_(col)}>{s}</text>'
def rect(x, y, w, h, fill=None, stroke=None, rx=3, sw=1.5, op=None):
    st = f'fill:var(--{fill})' if fill else 'fill:none'
    if stroke: st += f';stroke:var(--{stroke});stroke-width:{sw}'
    if op is not None: st += f';fill-opacity:{op}'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{h:.1f}" rx="{rx}" style="{st}"/>'
def line(x1, y1, x2, y2, col='line', w=1.5, dash=None):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {S_(col, w, dash)}/>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')

figs = {}

# 图 1：batch 1 时一步的时间账
b = text(20, 28, '生成 1 个 token（batch 1）', 'muted', 16)
x0, wmax = 130, 250
b += text(120, 74, '读权重', 'fg', 16, 'end') + rect(x0, 56, wmax, 26, 'accent') + text(x0 + wmax + 8, 75, f'{N["t1_ms"]} ms', 'accent', 16)
wc = wmax * TC1 / TM1
b += text(120, 124, '计算', 'fg', 16, 'end') + rect(x0, 106, max(wc, 1.5), 26, 'warn') + text(x0 + 10, 125, f'{N["tc1_ms"]} ms', 'warn', 16)
b += text(20, 172, f'计算单元有 {pct(1 - TC1 / TM1, 2)} 的时间在等数据', 'muted', 16)
figs['fig1'] = fig(480, 190, 'batch 为 1 时读权重与计算各花多少时间', b,
                   f'图 1　Llama-3-8B 在 H100 上生成 1 个 token：把 {N["w_gb"]} GB 权重从显存读一遍要 {N["t1_ms"]} ms，真正的乘加只要 {N["tc1_ms"]} ms，橙条细到几乎看不见。')

# 图 2：屋顶线（对数坐标）
ox, oy, W2, H2 = 70, 260, 380, 220
xlo, xhi, ylo, yhi = -0.3, 3.3, 12.0, 15.3     # log10：强度 0.5–2000，算力 1–2000 TFLOPS
X = lambda v: ox + (math.log10(v) - xlo) / (xhi - xlo) * W2
Y = lambda v: oy - (math.log10(v) - ylo) / (yhi - ylo) * H2
b = line(ox, oy, ox + W2, oy) + line(ox, oy, ox, oy - H2)
for v in [1, 10, 100, 1000]:
    b += line(X(v), oy, X(v), oy + 5, 'line') + text(X(v), oy + 22, f'{v:,}', 'muted', 14, 'middle')
for v, lab in [(1e12, '1'), (1e13, '10'), (1e14, '100'), (1e15, '1000')]:
    b += line(ox - 5, Y(v), ox, Y(v)) + text(ox - 8, Y(v) + 5, lab, 'muted', 14, 'end')
b += text(ox + W2, oy + 44, '算术强度（FLOP/B）', 'muted', 15, 'end') + text(ox - 8, oy - H2 - 10, 'TFLOPS', 'muted', 15, 'start')
xs = [10 ** (xlo + i * (xhi - xlo) / 200) for i in range(201)]
pts = ' '.join(f'{X(v):.1f},{Y(min(PEAK, v * BW)):.1f}' for v in xs)
b += f'<polyline points="{pts}" {S_("fg", 2.5)}/>'
b += text(X(RIDGE) + 6, Y(PEAK) - 8, f'拐点 {N["ridge"]}', 'fg', 15)
b += text(X(6), Y(6 * BW) + 34, '带宽限制', 'muted', 15, 'start')
for B in [1, 16, 64]:
    t, tm, tc, by, fl = step(B, 0); I = fl / by; perf = fl / t
    b += f'<circle cx="{X(I):.1f}" cy="{Y(perf):.1f}" r="5.5" {C_("accent")}/>' + text(X(I) + 8, Y(perf) + 18, f'B = {B}', 'accent', 15)
figs['fig2'] = fig(480, 320, '屋顶线：算术强度与可达到的算力', b,
                   f'图 2　H100 的屋顶线（两轴都是对数刻度）。拐点左边，速度由带宽决定，越往右越快；拐点 {N["ridge"]} 右边，算力用满，再往右也不会更快。蓝点是只算权重时 batch 1、16、64 的位置。')

# 图 3：一步要读的字节，B = 64
b = text(20, 28, f'batch 64，每人上下文 {CTX} 个 token：一步要读的字节', 'muted', 16)
tot = WB + 64 * CTX * KV_TOK; sc = 440 / tot
b += rect(20, 50, WB * sc, 34, 'accent') + text(20 + WB * sc / 2, 73, f'权重 {N["w_gb"]} GB', 'bg', 15, 'middle')
xk = 20 + WB * sc
b += rect(xk, 50, 64 * CTX * KV_TOK * sc, 34, 'warn', rx=3)
for i in range(1, 8):
    xx = xk + i * 8 * CTX * KV_TOK * sc
    b += line(xx, 50, xx, 84, 'bg', 1.2)
b += text(xk + 64 * CTX * KV_TOK * sc / 2, 108, f'64 份 KV cache，共 {N["kvgb64"]} GB', 'warn', 15, 'middle')
b += text(20, 140, f'合计 {N["by64"]} GB ÷ 3.35 TB/s = {N["t64"]} ms', 'fg', 16)
figs['fig3'] = fig(480, 158, 'batch 64 时一步要读的权重与 KV cache', b,
                   f'图 3　蓝色的权重 64 个人共用，读一遍就够；橙色的 KV cache 每人一份，有几个人就要读几份。')

# 图 4：总吞吐与单用户速度随 batch 变化
ox, oy, W4, H4 = 70, 250, 360, 200
Bs = list(range(1, BMAX + 1))
tot_max = 22000
X4 = lambda B: ox + B / 500 * W4
Yl = lambda v: oy - v / tot_max * H4
Yr = lambda v: oy - v / 220 * H4
b = line(ox, oy, ox + W4, oy) + line(ox, oy, ox, oy - H4) + line(ox + W4, oy, ox + W4, oy - H4)
for v in [0, 100, 200, 300, 400, 500]: b += text(X4(v), oy + 20, str(v), 'muted', 14, 'middle')
for v in [0, 10000, 20000]: b += text(ox - 6, Yl(v) + 5, f'{v // 1000}k' if v else '0', 'accent', 14, 'end')
for v in [0, 100, 200]: b += text(ox + W4 + 6, Yr(v) + 5, str(v), 'warn', 14, 'start')
b += text(ox + W4 / 2, oy + 40, 'batch（同时服务的用户数）', 'muted', 15, 'middle')
b += f'<polyline points="{" ".join(f"{X4(B):.1f},{Yl(B / step(B)[0]):.1f}" for B in Bs)}" {S_("accent", 2.5)}/>'
b += f'<polyline points="{" ".join(f"{X4(B):.1f},{Yr(1 / step(B)[0]):.1f}" for B in Bs)}" {S_("warn", 2.5)}/>'
b += line(X4(BMAX), oy, X4(BMAX), oy - H4, 'muted', 1.5, '5 4') + text(X4(BMAX) - 6, oy - 10, f'显存满 {BMAX}', 'muted', 14, 'end')
b += text(X4(170), Yl(170 / step(170)[0]) - 14, '整卡 token/s', 'accent', 15, 'end')
b += text(X4(260), Yr(1 / step(260)[0]) + 26, '每个用户 token/s', 'warn', 15, 'start')
figs['fig4'] = fig(480, 300, '总吞吐与每个用户的速度随 batch 的变化', b,
                   f'图 4　蓝线（左轴）是整张卡每秒出的 token 数，橙线（右轴）是每个用户每秒拿到的 token 数。batch 越大，总量越多，每个人越慢。')

# 图 5、6：静态与连续批处理时间线
def timeline(T, spans, title, hi_idle=True):
    cw, ch, x0, y0 = 28, 34, 62, 44
    b = text(20, 26, title, 'muted', 16)
    for s in range(SLOTS):
        b += text(x0 - 10, y0 + s * ch + 22, f'槽 {s + 1}', 'muted', 14, 'end')
        for t in range(14):
            b += rect(x0 + t * cw + 1, y0 + s * ch + 3, cw - 2, ch - 6, None, 'line', 3, 1)
    for i, (sl, s, e) in enumerate(spans):
        col = 'accent' if i < 4 else 'ok'
        b += rect(x0 + s * cw + 1, y0 + sl * ch + 3, (e - s) * cw - 2, ch - 6, col, rx=4)
        b += text(x0 + s * cw + 9, y0 + sl * ch + 22, f'{REQ[i]}', 'bg', 15, 'start', weight=600)
    for t in range(14):
        if t % 2 == 1: b += text(x0 + t * cw + cw / 2, y0 + SLOTS * ch + 18, str(t + 1), 'muted', 13, 'middle')
    b += line(x0 + T * cw, y0 - 4, x0 + T * cw, y0 + SLOTS * ch + 2, 'warn', 2.5)
    b += text(x0 + T * cw + 4, y0 + SLOTS * ch + 38, f'第 {T} 步全部完成', 'warn', 15, 'start' if T < 11 else 'end')
    return b
figs['fig5'] = fig(480, 230, '静态批处理的时间线', timeline(ST_T, ST_SP, '静态批处理：一批全部结束，下一批才进来'),
                   f'图 5　横轴是 decode 的步数，每一步每个槽出 1 个 token。蓝色是第一批 A–D，绿色是第二批 E–H。空着的格子就是槽在白等：B 第 2 步就说完了，它的槽要空等到第 8 步。')
figs['fig6'] = fig(480, 230, '连续批处理的时间线', timeline(CB_T, CB_SP, '连续批处理：谁说完了，下一步就有人补进来'),
                   f'图 6　同样 8 个请求、同样 4 个槽。B 第 2 步说完，第 3 步 E 就补进它的槽；空格子只剩最后收尾的几格。')

# 图 7：预留 vs 分页
def kvrow(y, title, mode):
    cw = 11.6; x0 = 20; gap = 4
    b = text(x0, y - 8, title, 'muted', 15)
    cols = ['accent', 'warn', 'ok']
    if mode == 'res':
        x = x0
        for i, l in enumerate(LENS):
            for t in range(MAXLEN):
                used = t < l
                b += rect(x + t * cw, y, cw - 1.5, 26, cols[i] if used else None, None if used else 'line', 2, 1.2)
            b += text(x + MAXLEN * cw / 2, y + 46, f'{REQ[i]}：用 {l}，占 {MAXLEN}', cols[i], 14, 'middle')
            x += MAXLEN * cw
    else:
        x = x0; owner = []
        for i, nb in enumerate(PG_BLOCKS):
            for k in range(nb): owner.append((i, k))
        for blk in range(POOL // BLK):
            bx = x0 + blk * (BLK * cw + gap)
            if blk < len(owner):
                i, k = owner[blk]; n = min(BLK, LENS[i] - k * BLK)
                for t in range(BLK):
                    b += rect(bx + t * cw, y, cw - 1.5, 26, cols[i] if t < n else None, None if t < n else 'line', 2, 1.2)
            else:
                for t in range(BLK): b += rect(bx + t * cw, y, cw - 1.5, 26, None, 'line', 2, 1.2)
                b += ''
        nb = PG_ALLOC // BLK; bw = BLK * cw + gap
        b += text(x0 + nb * bw / 2, y + 46, f'用了 {nb} 块', 'fg', 14, 'middle')
        b += text(x0 + (nb + POOL // BLK) * bw / 2, y + 46, f'空出 {(POOL - PG_ALLOC) // BLK} 块给新请求', 'ok', 14, 'middle')
    return b
b = kvrow(36, f'按最大长度预留（每个请求先占 {MAXLEN} 格）', 'res') + kvrow(140, f'分页（每块 {BLK} 格，用到才给）', 'pg')
figs['fig7'] = fig(480, 200, '预留整段空间与分页分配 KV cache 的对比', b,
                   f'图 7　一共 {POOL} 格显存，每格存 1 个 token 的 K、V。上：三个请求各占 {MAXLEN} 格，实际只用了 {RES_USED} 格，空框是被占着又没用上的。下：分页以后同样三个请求只占 {PG_ALLOC} 格，空框只出现在每个请求的最后一块里。')

# 图 8：块表
b = text(20, 26, '请求 B 的块表', 'muted', 16)
phys_of_B = [5, 1, 7]
cw = 12.4
for k in range(3):
    y = 50 + k * 44
    n = min(BLK, LENS[1] - k * BLK)
    b += text(20, y + 19, f'逻辑块 {k}', 'fg', 15)
    for t in range(BLK):
        b += rect(100 + t * cw, y, cw - 1.5, 26, 'warn' if t < n else None, None if t < n else 'line', 2, 1.2)
    lo, hi = k * BLK + 1, min((k + 1) * BLK, LENS[1])
    b += text(100 + BLK * cw + 10, y + 19, f'token {lo}–{hi}' if hi > lo else f'token {lo}', 'muted', 14)
    b += text(268, y + 19, '→', 'muted', 16)
    b += rect(288, y - 2, 64, 30, None, 'line', 4, 1.2) + text(320, y + 19, str(phys_of_B[k]), 'warn', 16, 'middle', weight=600)
# 显存里的物理块
b += text(380, 26, '显存', 'muted', 16)
for j in range(9):
    y = 36 + j * 17
    isB = j in phys_of_B
    b += rect(390, y, 70, 14, 'warn' if isB else 'line', None, 2, op=1 if isB else 0.6)
    b += text(384, y + 12, str(j), 'muted', 12, 'end')
figs['fig8'] = fig(480, 200, '块表把逻辑块映射到显存里不连续的物理块', b,
                   f'图 8　请求 B 有 9 个 token，分成 3 个逻辑块；块表记着每个逻辑块放在显存的第几号物理块（5、1、7），三块不需要挨在一起。最后一块只用了 1 格。')

# 图 9：前缀共享
b = text(20, 26, '两个用户，同一段系统提示', 'muted', 16)
def blocks(y, name, own_col):
    s = text(20, y + 19, name, 'fg', 15)
    for k in range(3): s += rect(80 + k * 52, y, 48, 26, 'accent', rx=3, op=0.85)
    s += text(80 + 3 * 52 + 4, y + 19, '…', 'muted', 16)
    for k in range(2): s += rect(80 + 3 * 52 + 22 + k * 52, y, 48, 26, own_col, rx=3, op=0.85)
    return s
b += blocks(50, '用户 1', 'warn') + blocks(150, '用户 2', 'ok')
for k in range(3):
    b += line(104 + k * 52, 80, 104 + k * 52, 146, 'accent', 1.5, '4 3')
b += text(236, 118, f'前 {N["shared_blocks"]} 块哈希相同 → 同一份物理块', 'accent', 14, 'start')
b += text(80 + 3 * 52 + 22, 44, '各自的问题', 'muted', 14)
figs['fig9'] = fig(480, 196, '两个请求共享前缀的 KV 块', b,
                   f'图 9　蓝色是 {SYS} 个 token 的系统提示（{N["shared_blocks"]} 块），两个用户一模一样，算一次、存一份；橙色和绿色是各自的问题，各存各的。')

# 图 10：p 与 q 的重叠 = α
b = text(20, 26, '大模型 p（蓝框）与小模型 q（橙框）', 'muted', 16)
ox, oy, hs = 70, 200, 230
for i, t in enumerate(TOK3):
    x = ox + i * 130
    hp, hq, hm = P[i] * hs, Q[i] * hs, min(P[i], Q[i]) * hs
    b += rect(x, oy - hm, 90, hm, 'ok', rx=2, op=0.35)
    b += rect(x, oy - hp, 42, hp, None, 'accent', 2, 2.5) + rect(x + 48, oy - hq, 42, hq, None, 'warn', 2, 2.5)
    b += text(x + 21, oy - hp - 8, f'{P[i]:.1f}', 'accent', 15, 'middle') + text(x + 69, oy - hq - 8, f'{Q[i]:.1f}', 'warn', 15, 'middle')
    b += text(x + 45, oy + 22, t, 'fg', 16, 'middle')
b += line(ox - 10, oy, ox + 3 * 130, oy)
b += text(20, 252, f'绿色 = 两者取小 = {min(P[0],Q[0]):.1f} + {min(P[1],Q[1]):.1f} + {min(P[2],Q[2]):.1f} = {ALPHA:.1f} = 接受率 α', 'ok', 15)
figs['fig10'] = fig(480, 266, '大模型与小模型的分布及其重叠部分', b,
                    f'图 10　三个候选 token 上的两个分布。每个 token 取两者中较小的那一截（绿色）加起来就是接受率 α。')

# 图 11：猜 γ = 4 个，接受到第几个就停
b = text(20, 26, f'猜 γ = {GAM} 个，每个独立地以 α = {ALPHA:.1f} 被接受', 'muted', 16)
for k in range(GAM + 1):
    y = 44 + k * 38
    for i in range(GAM):
        col = 'ok' if i < k else ('warn' if i == k else 'line')
        b += rect(30 + i * 40, y, 34, 26, col if i <= k else None, None if i <= k else 'line', 3, 1.2, op=0.85 if i <= k else None)
        if i == k and k < GAM: b += text(30 + i * 40 + 17, y + 19, '✗', 'bg', 15, 'middle', weight=700)
        if i < k: b += text(30 + i * 40 + 17, y + 19, '✓', 'bg', 15, 'middle', weight=700)
    b += rect(30 + GAM * 40 + 8, y, 34, 26, 'accent', rx=3, op=0.85) + text(30 + GAM * 40 + 25, y + 19, '+1', 'bg', 14, 'middle', weight=700)
    b += text(240, y + 19, f'概率 {PK[k]:.4f}'.rstrip('0').rstrip('.'), 'muted', 14) + text(345, y + 19, f'得到 {k + 1} 个 token', 'fg', 14)
figs['fig11'] = fig(480, 240, '投机解码一轮可能出现的五种结果', b,
                    f'图 11　绿色是被接受的猜测，橙色是第一个被拒的，之后的猜测全部作废；蓝色「+1」是大模型这一轮自己给出的那个 token（被拒时是修正的，全接受时是多送的）。')

# 图 12：加速比随 γ
ox, oy, W12, H12 = 60, 230, 380, 190
gs = list(range(0, 13))
X12 = lambda g: ox + g / 12 * W12
Y12 = lambda v: oy - v / 5 * H12
b = line(ox, oy, ox + W12, oy) + line(ox, oy, ox, oy - H12)
for g in [0, 2, 4, 6, 8, 10, 12]: b += text(X12(g), oy + 20, str(g), 'muted', 14, 'middle')
for v in [0, 1, 2, 3, 4, 5]: b += text(ox - 6, Y12(v) + 5, str(v), 'muted', 14, 'end')
b += line(ox, Y12(1), ox + W12, Y12(1), 'line', 1.2, '4 3')
b += text(ox + W12, oy + 40, '猜测长度 γ', 'muted', 15, 'end')
b += f'<polyline points="{" ".join(f"{X12(g):.1f},{Y12(exp_len(ALPHA, g)):.1f}" for g in gs)}" {S_("accent", 2.2)}/>'
b += f'<polyline points="{" ".join(f"{X12(g):.1f},{Y12(speedup(ALPHA, g, C)):.1f}" for g in gs)}" {S_("warn", 2.5)}/>'
b += text(X12(8), Y12(exp_len(ALPHA, 8)) - 14, '每轮期望得到的 token', 'accent', 14, 'middle')
b += text(X12(9.5), Y12(speedup(ALPHA, 9.5, C)) + 22, f'加速比（c = {C}）', 'warn', 14, 'middle')
b += f'<circle cx="{X12(GAM):.1f}" cy="{Y12(SP4):.1f}" r="5" {C_("warn")}/>' + text(X12(GAM), Y12(SP4) - 12, N['sp4'], 'warn', 14, 'middle')
figs['fig12'] = fig(480, 280, '期望长度与加速比随猜测长度的变化', b,
                    f'图 12　α = {ALPHA:.1f}。蓝线是每轮期望得到的 token 数，越猜越多但越来越平；橙线再扣掉小模型的成本，在 γ = {BEST_G} 附近最高，之后反而下降。')

# ———— 导出给实验页核对 ————
toy = {'BW': BW, 'PEAK': PEAK, 'MEM': MEM, 'NP': NP, 'KV_TOK': KV_TOK, 'CTX': CTX, 'BMAX': BMAX, 'B_SLA': B_SLA,
       'tab': {str(B): {'t_ms': t * 1e3, 'tot': B / t, 'per': 1 / t} for B, t, *_ in TAB},
       'OUT': OUT, 'ST_T': ST_T, 'CB_T': CB_T, 'ST_AVG': sum(e for _, _, e in ST_SP) / 8, 'CB_AVG': sum(e for _, _, e in CB_SP) / 8,
       'ALPHA': ALPHA, 'E4': E4, 'SP4': SP4, 'BEST_G': BEST_G, 'B_PREFIX': B_PREFIX, 'PF_FULL_ms': PF_FULL * 1e3, 'PF_OWN_ms': PF_OWN * 1e3,
       'SPBS': SPBS[0]}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False, indent=1))

src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', v)
left = re.findall(r'\{\{[^}]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/inference-serving.md').write_text(src, encoding='utf-8')
print(json.dumps({k: N[k] for k in sorted(N)}, ensure_ascii=False, indent=0))
