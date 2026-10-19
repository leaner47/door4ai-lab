"""weight-quantization 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm weight-quantization/scenes.py FloatBits
颜色约定（整讲一致）：符号 WARN，指数 C_K（黄），尾数 ACCENT（蓝）；权重点 ACCENT，格点 C_K，离群值 WARN。
"""
import sys, pathlib, struct; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np


# —— 真实位模式（与实验页同一套舍入：就近、平局取偶）——
def bits32(v):
    return format(struct.unpack(">I", struct.pack(">f", v))[0], "032b")


def bits_bf16(v):
    x = struct.unpack(">I", struct.pack(">f", v))[0]
    r = ((x + 0x7FFF + ((x >> 16) & 1)) >> 16) & 0xFFFF
    return format(r, "016b"), struct.unpack(">f", struct.pack(">I", r << 16))[0]


def bits_fp16(v):
    a = np.array([v], dtype=np.float32)
    with np.errstate(over="ignore"):
        h = a.astype(np.float16)
    return format(int(h.view(np.uint16)[0]), "016b"), float(h[0])


CELL, GAP, SEG_GAP = 0.3, 0.045, 0.16


def bit_row(bits, ne, y, x0=-5.2):
    """一排比特格子：第 0 位符号，接着 ne 位指数，其余尾数。"""
    cells = VGroup()
    x = x0
    for i, b in enumerate(bits):
        col = WARN if i == 0 else C_K if i <= ne else ACCENT
        sq = RoundedRectangle(width=CELL, height=0.42, corner_radius=0.05, stroke_width=0, fill_color=col, fill_opacity=0.28)
        sq.move_to([x + CELL / 2, y, 0])
        t = N(b, 20, col).move_to(sq)
        cells.add(VGroup(sq, t))
        x += CELL + GAP + (SEG_GAP if i in (0, ne) else 0)
    return cells


def header(name, val, y, x0=-5.2):
    g = VGroup(N(name, 28, FG), T("读回", 22, MUTED), N(val, 26, FG)).arrange(RIGHT, buff=0.25)
    g.move_to([0, y, 0]).align_to([x0, 0, 0], LEFT)
    return g


def fmt(v):
    if v == float("inf"):
        return "∞"
    return f"{v:.11g}"


class FloatBits(Scene):
    """一个数拆成符号、指数、尾数；FP32 截掉后 16 位尾数就是 BF16；FP16 指数少，范围小。"""

    def construct(self):
        title = T("一个数在内存里：符号 · 指数 · 尾数", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        v = 0.1
        num = N("0.1", 56, FG).move_to([0, 1.2, 0])
        self.play(FadeIn(num, shift=DOWN * 0.2)); pause(self, 0.5)

        b32 = bits32(v)
        y32 = 1.75
        h32 = header("FP32", fmt(float(np.float32(v))), y32 + 0.55)
        r32 = bit_row(b32, 8, y32)
        self.play(FadeOut(num, shift=UP * 0.3), LaggedStart(*[FadeIn(c, shift=DOWN * 0.1) for c in r32], lag_ratio=0.03, run_time=1.6))
        self.play(FadeIn(h32)); pause(self, 0.4)

        # 三段的含义
        segs = [(r32[0:1], WARN, "符号 1 位"), (r32[1:9], C_K, "指数 8 位：范围"), (r32[9:], ACCENT, "尾数 23 位：精度")]
        braces = VGroup()
        for grp, col, txt in segs:
            br = Brace(grp, DOWN, buff=0.08, color=col)
            lb = T(txt, 22, col).next_to(br, DOWN, buff=0.1)
            braces.add(VGroup(br, lb))
        braces[0][1].shift(LEFT * 0.25)
        self.play(LaggedStart(*[FadeIn(b) for b in braces], lag_ratio=0.4)); pause(self)
        formula = M(r"(-1)^{s}\times 2^{\,e-127}\times 1.m", 40).move_to([0, -0.4, 0])
        self.play(Write(formula)); pause(self, 1.2)
        self.play(FadeOut(braces), FadeOut(formula))

        # BF16：截掉后 16 位（再舍入）
        bbf, vbf = bits_bf16(v)
        ybf = 0.15
        copy = r32.copy()
        self.play(copy.animate.shift(DOWN * (y32 - ybf)), run_time=0.9)
        cut = copy[16:]
        self.play(cut.animate.set_opacity(0.15), run_time=0.6)
        cross = T("截掉后 16 位尾数", 22, MUTED).next_to(cut, DOWN, buff=0.12)
        self.play(FadeIn(cross)); pause(self, 0.4)
        rbf = bit_row(bbf, 8, ybf)
        hbf = header("BF16", fmt(vbf), ybf + 0.55)
        self.play(FadeOut(cut), FadeOut(cross), ReplacementTransform(copy[:16], rbf), FadeIn(hbf))
        note = T("指数还是 8 位：范围和 FP32 一样大，有效数字少了", 22, C_K).next_to(rbf, RIGHT, buff=0.3)
        if note.get_right()[0] > 6.9:
            note.next_to(rbf, DOWN, buff=0.15).align_to(rbf, LEFT)
        self.play(FadeIn(note)); pause(self)

        # FP16：1 + 5 + 10
        b16, v16 = bits_fp16(v)
        y16 = -1.55
        r16 = bit_row(b16, 5, y16)
        h16 = header("FP16", fmt(v16), y16 + 0.55)
        self.play(FadeOut(note), LaggedStart(*[FadeIn(c, shift=DOWN * 0.1) for c in r16], lag_ratio=0.03, run_time=1.0), FadeIn(h16))
        note16 = T("指数只有 5 位：尾数多 3 位，范围却小得多", 22, C_K).next_to(r16, RIGHT, buff=0.3)
        self.play(FadeIn(note16)); pause(self, 1.2)
        self.play(FadeOut(note16))

        # 换成 70000：范围的差别
        v2 = 70000.0
        n2 = N("70000", 48, FG).move_to([4.6, 0.45, 0])
        self.play(FadeIn(n2, shift=LEFT * 0.2))
        b16b, v16b = bits_fp16(v2)
        bbfb, vbfb = bits_bf16(v2)
        new32, new16, newbf = bit_row(bits32(v2), 8, y32), bit_row(b16b, 5, y16), bit_row(bbfb, 8, ybf)
        nh32, nhbf, nh16 = header("FP32", fmt(v2), y32 + 0.55), header("BF16", fmt(vbfb), ybf + 0.55), header("FP16", fmt(v16b), y16 + 0.55)
        nh16[2].set_color(WARN); nhbf[2].set_color(OK)
        self.play(Transform(r32, new32), Transform(rbf, newbf), Transform(r16, new16),
                  Transform(h32, nh32), Transform(hbf, nhbf), Transform(h16, nh16), run_time=1.4)
        pause(self, 0.6)
        end = VGroup(
            T("FP16 最大只能到 65504，70000 存进去就成了 ∞", 24, WARN),
            T("BF16 读回 70144：差一点，但装得下。所以大模型训练和推理多用 BF16", 24, OK),
        ).arrange(DOWN, buff=0.18, aligned_edge=LEFT).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(end[0], shift=UP * 0.15)); pause(self, 0.6)
        self.play(FadeIn(end[1], shift=UP * 0.15))
        self.wait(2.2)


class QuantGrid(Scene):
    """4 位量化：连续分布的权重吸附到 16 个格点上；一个离群值把格子撑宽。"""

    def construct(self):
        title = T("4 位量化：每个权重吸附到 16 个格点之一", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        rng = np.random.default_rng(7)
        vals = np.clip(rng.normal(0, 1, 140), -2.9, 2.9)
        ys = rng.uniform(0.35, 1.9, len(vals))
        LEFT_X, RIGHT_X, Y0 = -6.0, 6.0, -0.5

        def mapper(lo, hi):
            return lambda v: LEFT_X + (v - lo) / (hi - lo) * (RIGHT_X - LEFT_X)

        lo, hi = float(vals.min()), float(vals.max())
        X = mapper(lo, hi)
        axis = Line([LEFT_X - 0.2, Y0, 0], [RIGHT_X + 0.2, Y0, 0], color=MUTED, stroke_width=2)
        dots = VGroup(*[Dot([X(v), Y0 + y, 0], radius=0.055, color=ACCENT) for v, y in zip(vals, ys)])
        cap = T("140 个权重（近似正态分布）", 24, MUTED).next_to(axis, DOWN, buff=0.5)
        self.play(Create(axis), LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.01, run_time=1.6), FadeIn(cap))
        pause(self)

        # 16 个格点：在 [min, max] 之间等距
        def grid(lo, hi):
            Xg = mapper(lo, hi)
            sc = (hi - lo) / 15
            lines = VGroup(*[Line([Xg(lo + k * sc), Y0 - 0.12, 0], [Xg(lo + k * sc), Y0 + 2.15, 0], color=C_K, stroke_width=2, stroke_opacity=0.75) for k in range(16)])
            labels = VGroup(*[N(str(k), 18, C_K).move_to([Xg(lo + k * sc), Y0 - 0.32, 0]) for k in range(16)])
            return lines, labels, sc

        lines, labels, sc = grid(lo, hi)
        self.play(FadeOut(cap), LaggedStart(*[Create(l) for l in lines], lag_ratio=0.05, run_time=1.2), FadeIn(labels))
        scl = VGroup(T("相邻格点的距离 = scale", 24, C_K)).next_to(axis, DOWN, buff=0.75)
        self.play(FadeIn(scl)); pause(self)

        def snap(lo, sc, X):
            return [d.animate.move_to([X(lo + round((v - lo) / sc) * sc), d.get_center()[1], 0]) for d, v in zip(dots, vals)]

        self.play(*snap(lo, sc, X), run_time=1.6); pause(self, 0.4)
        msg = T("每个权重只存一个 0–15 的整数：4 位；整组共用 scale 和 zero", 26, FG).next_to(axis, DOWN, buff=0.75)
        self.play(ReplacementTransform(scl, msg)); pause(self, 1.4)

        # 离群值：一个大数把格子撑宽
        out_v = 9.5
        X2 = mapper(lo, out_v)
        back = [d.animate.move_to([X2(v), Y0 + y, 0]) for d, v, y in zip(dots, vals, ys)]
        outlier = Dot([X2(out_v), Y0 + 1.0, 0], radius=0.09, color=WARN)
        lines2, labels2, sc2 = grid(lo, out_v)
        msg2 = T("加入一个离群值：范围被撑宽，scale 变大", 26, WARN).next_to(axis, DOWN, buff=0.75)
        self.play(*back, FadeIn(outlier, scale=2), Transform(lines, lines2), Transform(labels, labels2), ReplacementTransform(msg, msg2), run_time=1.8)
        pause(self, 0.6)
        self.play(*snap(lo, sc2, X2), outlier.animate.move_to([X2(out_v), Y0 + 1.0, 0]), run_time=1.6)
        used = len(set(int(round((v - lo) / sc2)) for v in vals)) + 1
        msg3 = T(f"其余 140 个权重挤进 {used - 1} 个格点，16 个格点只用上了 {used} 个", 26, WARN).next_to(axis, DOWN, buff=0.75)
        self.play(ReplacementTransform(msg2, msg3))
        self.wait(2.5)
