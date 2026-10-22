"""后训练一讲的贯穿算例：文章分镜图、文中数字与实验页共用这组数。
运行：python3 labs-src/post-training/toy.py
  → 生成 src/content/blog/post-training.md（把 article.src.md 里的 {{figN}} 与 {{n:名字}} 填好）
  → 写出 labs-src/post-training/toy.json（实验页里的同一组数，抄在实验页开头的 TOY 常量里）
"""
import math, json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def softmax(z):
    m = max(z); e = [math.exp(v - m) for v in z]; s = sum(e); return [v / s for v in e]

# ———— 第一部分：基座模型在「17 × 3 等于多少？」之后，下一个 token 选什么 ————
CAND = ['问', '51', '17', '。']                  # 继续出题 / 直接回答 / 重复题目 / 结束
CAND_NOTE = ['接着出下一道题', '回答', '把题目再抄一遍', '句号，结束']
Z0 = [2.0, 0.5, 1.0, 0.0]                         # 基座模型的分数（logit），示意
TARGET = 1                                        # 示范回答的第一个 token 是「51」
EXPZ = [math.exp(v) for v in Z0]; SUMZ = sum(EXPZ)
P0 = [v / SUMZ for v in EXPZ]
LOSS0 = -math.log(P0[TARGET])
G0 = [P0[i] - (1 if i == TARGET else 0) for i in range(4)]   # 交叉熵对 logit 的梯度 p − y
ETA = 1.0
Z1 = [Z0[i] - ETA * G0[i] for i in range(4)]
P1 = softmax(Z1); LOSS1 = -math.log(P1[TARGET])
# 连续走几步
traj = [(Z0, P0)]
z = Z0[:]
for _ in range(10):
    p = softmax(z); z = [z[i] - ETA * (p[i] - (1 if i == TARGET else 0)) for i in range(4)]
    traj.append((z, softmax(z)))
STEPS_P = [t[1][TARGET] for t in traj]

# ———— 第二部分：一条 SFT 样本，逐 token 的损失 ————
SEQ = [  # (显示的 token, 模型给「正确的这个 token」的概率, 是否属于回答)
    ('<|im_start|>user', 0.01, False), ('17', 0.02, False), (' ×', 0.10, False), (' 3', 0.08, False),
    (' 等于', 0.25, False), ('多少', 0.55, False), ('？', 0.70, False), ('<|im_end|>', 0.04, False),
    ('<|im_start|>assistant', 0.03, False),
    ('51', P0[TARGET], True), ('。', 0.60, True), ('<|im_end|>', 0.05, True),
]
LOSSES = [-math.log(p) for _, p, _ in SEQ]
ANS = [l for l, (_, _, a) in zip(LOSSES, SEQ) if a]
PROMPT = [l for l, (_, _, a) in zip(LOSSES, SEQ) if not a]
LOSS_ALL = sum(LOSSES) / len(LOSSES)
LOSS_ANS = sum(ANS) / len(ANS)
SHARE_PROMPT = sum(PROMPT) / sum(LOSSES)

# ———— 第三部分：可验证奖励 + GRPO 的一组 ————
ANSWERS = ['51', '41', '54', '21']                # 模型给出的最终答案；只有 51 对
ZA = [0.4, 0.2, 0.0, -0.6]                        # SFT 之后，最终答案的分数（示意）
EXPA = [math.exp(v) for v in ZA]; SUMA = sum(EXPA)
PA = [v / SUMA for v in EXPA]
GROUP = ['51', '41', '51', '54']                  # 采样到的 4 个回答（固定下来，便于手算）
R = [1.0 if a == '51' else 0.0 for a in GROUP]
MEAN = sum(R) / len(R)
STD = math.sqrt(sum((r - MEAN) ** 2 for r in R) / len(R))
ADV = [(r - MEAN) / STD for r in R]
# 每个回答 i 的对数概率梯度 = onehot(y_i) − p；乘优势、取平均
UPD = [0.0] * 4
for a, A in zip(GROUP, ADV):
    j = ANSWERS.index(a)
    for k in range(4): UPD[k] += A * ((1 if k == j else 0) - PA[k]) / len(GROUP)
ETA_RL = 1.0
ZA1 = [ZA[k] + ETA_RL * UPD[k] for k in range(4)]
PA1 = softmax(ZA1)

# ———— 文中用到的数字 ————
f2 = lambda v: f'{v:.2f}'
f3 = lambda v: f'{v:.3f}'
pc = lambda v: f'{v*100:.1f}\\%'          # 公式里
pt = lambda v: f'{v*100:.1f}%'            # 正文里
sg = lambda v: (f'+{v:.3f}' if v >= 0 else f'−{-v:.3f}')
N = {
    'e0': f3(EXPZ[0]), 'e1': f3(EXPZ[1]), 'e2': f3(EXPZ[2]), 'e3': f3(EXPZ[3]), 'sum': f3(SUMZ),
    'p0': f3(P0[0]), 'p1': f3(P0[1]), 'p2': f3(P0[2]), 'p3': f3(P0[3]),
    'p0pc': pt(P0[0]), 'p1pc': pt(P0[1]), 'p2pc': pt(P0[2]), 'p3pc': pt(P0[3]),
    'loss0': f3(LOSS0), 'g0': f3(G0[0]), 'g1': f3(-G0[1]), 'g2': f3(G0[2]), 'g3': f3(G0[3]),
    'z10': f3(Z1[0]), 'z11': f3(Z1[1]), 'z12': f3(Z1[2]), 'z13': f3(Z1[3]),
    'q0': f3(P1[0]), 'q1': f3(P1[1]), 'q2': f3(P1[2]), 'q3': f3(P1[3]),
    'q1pc': pt(P1[1]), 'q0pc': pt(P1[0]), 'loss1': f3(LOSS1),
    'step3pc': pt(STEPS_P[3]), 'step5pc': pt(STEPS_P[5]), 'step10pc': pt(STEPS_P[10]),
    'lossall': f3(LOSS_ALL), 'lossans': f3(LOSS_ANS), 'sharepc': pt(SHARE_PROMPT),
    'lsum': f3(sum(LOSSES)), 'lsumans': f3(sum(ANS)), 'lsumprompt': f3(sum(PROMPT)),
    'l_51': f3(LOSSES[9]), 'l_dot': f3(LOSSES[10]), 'l_end': f3(LOSSES[11]), 'l_user': f3(LOSSES[0]), 'l_17': f3(LOSSES[1]),
    'ea0': f3(EXPA[0]), 'ea1': f3(EXPA[1]), 'ea2': f3(EXPA[2]), 'ea3': f3(EXPA[3]), 'suma': f3(SUMA),
    'pa0': f3(PA[0]), 'pa1': f3(PA[1]), 'pa2': f3(PA[2]), 'pa3': f3(PA[3]), 'pa0pc': pt(PA[0]),
    'u0': f3(UPD[0]), 'u1': f3(UPD[1]), 'u2': f3(UPD[2]), 'u3': f3(UPD[3]),
    'za10': f3(ZA1[0]), 'za11': f3(ZA1[1]), 'za12': f3(ZA1[2]), 'za13': f3(ZA1[3]),
    'pb0': f3(PA1[0]), 'pb1': f3(PA1[1]), 'pb2': f3(PA1[2]), 'pb3': f3(PA1[3]), 'pb0pc': pt(PA1[0]),
    'pb3pc': pt(PA1[3]), 'pa3pc': pt(PA[3]), 'pb1pc': pt(PA1[1]), 'pa1pc': pt(PA[1]),
}
# 一组 G 个回答全对或全错（没有学习信号）的概率：p^G + (1 − p)^G
same = lambda p, G: p**G + (1 - p)**G
N.update({'zs_mid4': pt(same(PA[0], 4)), 'zs_mid16': pt(same(PA[0], 16)), 'zs_hard4': pt(same(0.02, 4)), 'zs_hard16': pt(same(0.02, 16)),
          'pa0_4': f'{PA[0]**4:.4f}', 'qa0_4': f'{(1-PA[0])**4:.4f}', 'qa0': f3(1 - PA[0])})
# 损失表（第二部分）
rows = []
for (t, p, a), l in zip(SEQ, LOSSES):
    tok = t.replace('|', '\\|').replace('<', '&lt;').replace('>', '&gt;')
    rows.append(f'| `{t.replace("|", chr(92)+"|")}` | {"回答" if a else "提问"} | {p:.3f} | {l:.3f} |')
N['seqtable'] = '\n'.join(rows)

# ———— SVG 小工具：颜色只用 CSS 变量 ————
def C(v): return f'style="fill:var(--{v})"'
def S_(v, w=2, dash=None): return f'style="stroke:var(--{v});stroke-width:{w}{";stroke-dasharray:"+dash if dash else ""};fill:none"'
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def text(x, y, s, col='fg', size=16, anchor='start', italic=False, weight=None):
    extra = (' font-style="italic"' if italic else '') + (f' font-weight="{weight}"' if weight else '')
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{extra} {C(col)}>{esc(s)}</text>'
def arrow(x1, y1, x2, y2, col, w=2.5):
    ang = math.atan2(y2-y1, x2-x1); L = 10; a = 0.42
    bx, by = x2 - L*math.cos(ang), y2 - L*math.sin(ang)
    p1 = (x2 - L*math.cos(ang-a), y2 - L*math.sin(ang-a)); p2 = (x2 - L*math.cos(ang+a), y2 - L*math.sin(ang+a))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" {S_(col, w)}/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} z" {C(col)}/>')
def rect(x, y, w, h, col, rx=4): return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,1):.1f}" height="{h:.1f}" rx="{rx}" {C(col)}/>'
def fig(w, h, label, body, cap):
    return (f'<figure class="fig">\n<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n{body}\n</svg>\n'
            f'<figcaption>{cap}</figcaption>\n</figure>')

def bars2(labels, title_l, vals_l, title_r, vals_r, hi, fmt=pt, cols=('line', 'line'), hicol='accent', h=40, mx=None):
    """左右两组条形：同一组候选，前后对比。"""
    b = text(80, 24, title_l, 'muted', 16) + text(290, 24, title_r, 'muted', 16)
    mx = mx or max(max(vals_l), max(vals_r))
    for i, t in enumerate(labels):
        y = 44 + i*h
        b += text(68, y + 18, t, 'fg', 16, 'end')
        for x0, vals in ((80, vals_l), (290, vals_r)):
            wv = 120 * vals[i] / mx; col = hicol if i == hi else 'line'
            b += rect(x0, y, wv, 24, col)
            b += text(x0 + wv + 6, y + 18, fmt(vals[i]), hicol if i == hi else 'muted', 16)
    return b

figs = {}
# 图 1：基座模型的下一个 token
b = ''
for i, t in enumerate(CAND):
    y = 14 + i*44
    b += text(54, y + 19, t, 'fg', 17, 'end', weight=600 if i == 0 else None)
    wv = 190 * P0[i] / max(P0); col = 'warn' if i == 0 else ('accent' if i == TARGET else 'line')
    b += rect(66, y, wv, 26, col)
    b += text(66 + wv + 8, y + 19, f'{pt(P0[i])}　{CAND_NOTE[i]}', col if i in (0, TARGET) else 'muted', 16)
figs['fig1'] = fig(480, 14 + 4*44, '基座模型在题目之后对四个候选 token 的概率',
                   b, '图 1　基座模型读完「17 × 3 等于多少？」之后，下一个 token 的四个候选。最可能的是「问」：接着出下一道题（示意数字）。')

# 图 2：对话模板 —— 一串 token，提问灰、回答蓝
def strip(seq, y0, maxw=460, highlight=lambda a: a, show_loss=False):
    b = ''; x = 10; y = y0; lineh = 46
    for t, p, a in seq:
        w = 13 + 9.2 * sum(2 if ord(c) > 255 else 1 for c in t)
        if x + w > maxw + 10: x = 10; y += lineh
        col = 'accent' if highlight(a) else 'line'
        b += f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="32" rx="6" style="fill:none;stroke:var(--{col});stroke-width:{2.2 if highlight(a) else 1.5}"/>'
        b += text(x + w/2, y + 22, t, 'accent' if highlight(a) else 'muted', 15, 'middle')
        x += w + 6
    return b, y + 32
body, yb = strip(SEQ, 12)
figs['fig2'] = fig(480, yb + 10, '对话模板把一问一答写成一串 token', body,
                   '图 2　一问一答被对话模板写成一串 token。灰框是用户的提问，蓝框是助手的回答。<code>&lt;|im_start|&gt;</code>、<code>&lt;|im_end|&gt;</code> 是特殊 token，标出谁在说话、哪里结束（切分是示意）。')

# 图 3：SFT 一步之前与之后
figs['fig3'] = fig(480, 44 + 4*40 + 6, 'SFT 一步之前与之后四个候选的概率',
                   bars2(CAND, '训练前', P0, '走一步之后', P1, TARGET),
                   f'图 3　朝「51」走一步（学习率 1）：「51」从 {pt(P0[1])} 升到 {pt(P1[1])}，其余三个都降。')

# 图 4：逐 token 损失，提问部分可以遮掉
b = ''; mxl = max(LOSSES); bw = 30; gap = 8; x0 = 22; base = 196
for i, ((t, p, a), l) in enumerate(zip(SEQ, LOSSES)):
    x = x0 + i * (bw + gap); hgt = 150 * l / mxl
    col = 'accent' if a else 'line'
    b += rect(x, base - hgt, bw, hgt, col, 3)
    b += text(x + bw/2, base - hgt - 6, f'{l:.1f}', 'accent' if a else 'muted', 14, 'middle')
    lab = {'<|im_start|>user': 'user', '<|im_end|>': 'end', '<|im_start|>assistant': 'asst'}.get(t, t.strip())
    b += text(x + bw/2, base + 20, lab, 'accent' if a else 'muted', 13, 'middle')
xa = x0 + 9 * (bw + gap) - 4
b += f'<line x1="{xa:.1f}" y1="30" x2="{xa:.1f}" y2="{base+28}" {S_("muted", 1.2, "4 4")}/>'
b += text(xa - 8, 22, '提问：不算', 'muted', 15, 'end') + text(xa + 8, 22, '回答：算', 'accent', 15, 'start')
figs['fig4'] = fig(480, base + 34, '一条样本里每个 token 的损失，提问部分灰色、回答部分蓝色', b,
                   f'图 4　每根柱子是一个 token 的损失 −ln <i>p</i>。灰色是提问部分，训练时遮掉；只有右边三根蓝色的计入平均。')

# 图 5：GRPO 一组 —— 4 个回答、奖励、优势
b = text(14, 22, '回答', 'muted', 15) + text(150, 22, '判对错', 'muted', 15) + text(250, 22, '奖励', 'muted', 15) + text(330, 22, '优势 A', 'muted', 15)
for i, (a, r, A) in enumerate(zip(GROUP, R, ADV)):
    y = 40 + i * 44
    col = 'ok' if r > 0 else 'warn'
    b += f'<rect x="10" y="{y}" width="120" height="32" rx="6" style="fill:none;stroke:var(--line);stroke-width:1.5"/>'
    b += text(70, y + 22, f'回答 {i+1}：{a}', 'fg', 15, 'middle')
    b += text(150, y + 22, '对' if r > 0 else '错', col, 16, weight=600)
    b += text(262, y + 22, f'{r:.0f}', 'fg', 16, 'middle')
    cx = 400; wv = 52 * abs(A)
    b += rect(cx if A >= 0 else cx - wv, y + 6, wv, 20, 'ok' if A > 0 else 'warn', 3)
    b += text(cx + (wv + 6 if A >= 0 else -wv - 6), y + 22, f'{A:+.0f}'.replace('-', '−'), 'ok' if A > 0 else 'warn', 16, 'start' if A >= 0 else 'end')
b += f'<line x1="400" y1="36" x2="400" y2="{40+4*44}" {S_("muted", 1.2)}/>'
b += text(14, 40 + 4*44 + 22, f'平均 {MEAN:.1f}，标准差 {STD:.1f}', 'muted', 15)
figs['fig5'] = fig(480, 40 + 4*44 + 32, '同一道题的四个回答、奖励和组内优势', b,
                   '图 5　同一道题采样 4 个回答，程序判对错给奖励，减去组内平均、除以标准差，就是每个回答的优势。高于平均的被加强（绿），低于平均的被削弱（橙）。')

# 图 6：GRPO 一步之前与之后
figs['fig6'] = fig(480, 44 + 4*40 + 6, 'GRPO 一步之前与之后四个答案的概率',
                   bars2(ANSWERS, '更新前', PA, '更新一步之后', PA1, 0, hicol='ok'),
                   f'图 6　更新一步（学习率 1）：答对的「51」从 {pt(PA[0])} 升到 {pt(PA1[0])}。这一组里没有被采到的「21」，分数没动，概率也略降了。')

# 图 7：四个模型的后训练流水线
PIPES = [
    ('InstructGPT · 2022', [('GPT-3', 'line'), ('SFT', 'accent'), ('奖励模型', 'warn'), ('PPO', 'warn')]),
    ('Llama 3 · 2024', [('预训练', 'line'), ('奖励模型', 'warn'), ('SFT', 'accent'), ('DPO', 'warn'), ('× 6 轮', 'muted')]),
    ('Tülu 3 · 2024', [('Llama 3.1', 'line'), ('SFT', 'accent'), ('DPO', 'warn'), ('RLVR', 'ok')]),
    ('DeepSeek-R1 · 2025', [('V3-Base', 'line'), ('SFT', 'accent'), ('RL', 'ok'), ('SFT', 'accent'), ('RL', 'ok')]),
]
b = ''; y = 10
for name, st in PIPES:
    b += text(10, y + 18, name, 'fg', 16, weight=600)
    y += 28; x = 10; bw = 76 if len(st) == 5 else 96; g = (460 - len(st) * bw) / (len(st) - 1)
    for i, (s, col) in enumerate(st):
        filled = col not in ('line', 'muted')
        b += f'<rect x="{x:.1f}" y="{y}" width="{bw}" height="32" rx="6" style="fill:none;stroke:var(--{col});stroke-width:{2.2 if filled else 1.5};{"stroke-dasharray:4 3" if col == "muted" else ""}"/>'
        b += text(x + bw/2, y + 22, s, col if col != 'line' else 'muted', 15, 'middle')
        if i < len(st) - 1: b += arrow(x + bw + 2, y + 16, x + bw + g - 2, y + 16, 'muted', 1.5)
        x += bw + g
    y += 50
figs['fig7'] = fig(480, y - 8, '四个公开模型的后训练流水线', b,
                   '图 7　四个公开模型的后训练顺序（Llama 3 的四步要重复 6 轮）。灰框是起点，蓝是 SFT，橙是用偏好数据的一步，绿是用可验证奖励的强化学习。')

# ———— 输出 ————
toy = {'cand': CAND, 'candNote': CAND_NOTE, 'z0': Z0, 'target': TARGET,
       'seq': SEQ, 'answers': ANSWERS, 'za': ZA, 'group': GROUP}
(HERE / 'toy.json').write_text(json.dumps(toy, ensure_ascii=False))
src = (HERE / 'article.src.md').read_text(encoding='utf-8')
for k, v in figs.items(): src = src.replace('{{' + k + '}}', v)
for k, v in N.items(): src = src.replace('{{n:' + k + '}}', v)
left = re.findall(r'\{\{[a-z0-9:_]+\}\}', src)
assert not left, left
(ROOT / 'src/content/blog/post-training.md').write_text(src, encoding='utf-8')
print(json.dumps({k: v for k, v in N.items() if k != 'seqtable'}, ensure_ascii=False, indent=0))
print('steps p(51):', [round(v, 3) for v in STEPS_P])
