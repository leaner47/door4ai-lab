"""lora 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm lora/scenes.py LowRankUpdate
颜色约定（整讲一致）：冻结的 W 用 WARN，LoRA 的 B、A 与 ΔW 用 ACCENT，次要文字 MUTED。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np


def heat(M, side, col_pos=ACCENT, col_neg=WARN):
    """把矩阵画成热力图：正数蓝、负数橙，深浅按 |v|/max。"""
    rows, cols = M.shape
    m = np.abs(M).max() or 1
    cw = side / max(rows, cols)
    g = VGroup()
    for i in range(rows):
        for j in range(cols):
            v = M[i, j] / m
            sq = Square(cw, stroke_width=0.5, stroke_color=BG).set_fill(col_pos if v >= 0 else col_neg, opacity=min(1, abs(v)))
            sq.move_to([(j - (cols - 1) / 2) * cw, -(i - (rows - 1) / 2) * cw, 0])
            g.add(sq)
    return g


class LowRankUpdate(Scene):
    """W + B·A：一个大矩阵旁边长出两个瘦长矩阵，乘起来变成同样大小的修正，叠到 W 上。"""

    def construct(self):
        title = T("LoRA：冻住 W，只学一个低秩修正", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        d, r = 4096, 8
        S = 3.0                           # W 的边长（像素比例按真实 d : r 画，r 太细时取最小 0.08）
        rw = max(S * r / d, 0.08)

        W = Square(S, stroke_color=WARN, stroke_width=3, fill_color=WARN, fill_opacity=0.25).move_to([-3.6, -0.3, 0])
        wl = N("W", 40, FG).move_to(W)
        wd = VGroup(T("4096 × 4096", 24, WARN), T("16.8 M 个参数", 24, WARN)).arrange(DOWN, buff=0.08).next_to(W, DOWN, buff=0.25)
        self.play(FadeIn(W), FadeIn(wl)); self.play(FadeIn(wd)); pause(self)

        frozen = T("冻结：微调时一个数都不动", 24, MUTED).next_to(W, UP, buff=0.25)
        lock = Rectangle(width=S + 0.3, height=S + 0.3, stroke_color=MUTED, stroke_width=2).move_to(W)
        lock.set_stroke(opacity=0.6)
        self.play(Create(lock), FadeIn(frozen)); pause(self)

        plus = M("+", 48, FG).next_to(W, RIGHT, buff=0.45)
        self.play(FadeIn(plus))

        B = Rectangle(width=rw, height=S, stroke_color=ACCENT, stroke_width=3, fill_color=ACCENT, fill_opacity=0.5).next_to(plus, RIGHT, buff=0.45)
        B.align_to(W, DOWN)
        bl = N("B", 36, ACCENT).next_to(B, UP, buff=0.15)
        bd = T("4096 × 8", 22, ACCENT).next_to(B, DOWN, buff=0.2)
        self.play(GrowFromEdge(B, DOWN), FadeIn(bl), FadeIn(bd)); pause(self, 0.5)

        times = M(r"\times", 40, FG).next_to(B, RIGHT, buff=0.4)
        A = Rectangle(width=S, height=rw, stroke_color=ACCENT, stroke_width=3, fill_color=ACCENT, fill_opacity=0.5).next_to(times, RIGHT, buff=0.4)
        A.set_y(W.get_y())
        al = N("A", 36, ACCENT).next_to(A, UP, buff=0.15)
        ad = T("8 × 4096", 22, ACCENT).next_to(A, DOWN, buff=0.2)
        self.play(FadeIn(times), GrowFromEdge(A, LEFT), FadeIn(al), FadeIn(ad)); pause(self)

        cnt = T("B、A 一共 8 × (4096 + 4096) = 65 536 个参数，是 W 的 0.39%", 26, ACCENT).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(cnt, shift=UP * 0.2)); pause(self, 1.2)

        # B·A 乘起来：变成和 W 一样大的 ΔW（虚线框），再叠到 W 上
        dW = Square(S, stroke_color=ACCENT, stroke_width=3, fill_color=ACCENT, fill_opacity=0.18).move_to(A.get_center() + LEFT * 0.0)
        dW.set_x((B.get_x() + A.get_x()) / 2 + 0.3)
        dW.set_y(W.get_y())
        dl = M(r"\Delta W = B A", 36, ACCENT).next_to(dW, UP, buff=0.15)
        dd = T("4096 × 4096，和 W 一样大", 22, ACCENT).next_to(dW, DOWN, buff=0.2)
        self.play(FadeOut(cnt), FadeOut(times), FadeOut(bl), FadeOut(al), FadeOut(bd), FadeOut(ad),
                  ReplacementTransform(VGroup(B, A), dW), FadeIn(dl), FadeIn(dd)); pause(self)

        self.play(FadeOut(lock), FadeOut(frozen), FadeOut(plus), FadeOut(dl), FadeOut(dd), FadeOut(wd),
                  dW.animate.move_to(W.get_center()))
        self.play(VGroup(W, wl, dW).animate.move_to([0, 0.2, 0]))
        sumlab = M(r"W' = W + B A", 44, FG).next_to(W, DOWN, buff=0.35)
        self.play(FadeIn(sumlab, shift=UP * 0.2)); pause(self)
        end = T("训练时只更新 B、A；推理时合并进 W，形状不变，速度不变", 26, FG).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2)


class RankIntuition(Scene):
    """秩 1 矩阵 = 一列乘一行；叠加 r 个就是秩 r。"""

    def construct(self):
        title = T("秩 1 矩阵：一列数乘一行数", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        rng = np.random.default_rng(5)
        n = 8
        us = rng.normal(0, 1, (4, n)); vs = rng.normal(0, 1, (4, n))

        side = 2.4
        u = heat(us[0][:, None], side).move_to([-4.2, -0.4, 0])
        ul = M("u", 36, FG).next_to(u, UP, buff=0.2)
        ud = T("8 个数", 22, MUTED).next_to(u, DOWN, buff=0.2)
        v = heat(vs[0][None, :], side).move_to([-1.4, 1.3, 0])
        vl = M(r"v^{\mathsf T}", 36, FG).next_to(v, UP, buff=0.2)
        vd = T("8 个数", 22, MUTED).next_to(v, DOWN, buff=0.15)
        self.play(FadeIn(u), FadeIn(ul), FadeIn(ud)); pause(self, 0.4)
        self.play(FadeIn(v), FadeIn(vl), FadeIn(vd)); pause(self, 0.4)

        M0 = np.outer(us[0], vs[0])
        outer = heat(M0, side).move_to([-1.4, -0.9, 0])
        eq = M("=", 36, FG).next_to(outer, LEFT, buff=0.3)
        ol = M(r"u\,v^{\mathsf T}", 36, FG).next_to(outer, RIGHT, buff=0.4)
        od = T("64 个格子，只由 16 个数决定", 24, MUTED).next_to(ol, DOWN, buff=0.2).align_to(ol, LEFT)
        # 用「一行是 v 的倍数」的方式生成：逐行从 v 复制下来
        self.play(FadeIn(eq))
        self.play(LaggedStart(*[TransformFromCopy(v, VGroup(*[outer[i * n + j] for j in range(n)])) for i in range(n)], lag_ratio=0.12), run_time=2.0)
        self.play(FadeIn(ol), FadeIn(od)); pause(self, 0.6)
        note = T("每一行都是同一行 v 的倍数：倍数是 u 里对应的那个数", 24, FG).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(note, shift=UP * 0.2)); pause(self, 1.2)

        # 叠加 r 个
        self.play(FadeOut(VGroup(u, ul, ud, v, vl, vd, eq, ol, od, note)), outer.animate.scale(0.7).move_to([-5.2, 0.4, 0]))
        t2 = T("叠加 r 个秩 1 矩阵 = 秩 r 的矩阵", 36).to_edge(UP, buff=0.4)
        self.play(Transform(title, t2)); pause(self, 0.3)

        small = side * 0.7
        tiles = [outer]
        xs = [-5.2, -2.6, 0.0, 2.6]
        acc = M0.copy()
        labs = VGroup(N("u1v1ᵀ", 24, MUTED).next_to(outer, UP, buff=0.15))
        self.play(FadeIn(labs[0]))
        res = heat(acc, small).move_to([5.0, 0.4, 0])
        rl = T("秩 1", 26, ACCENT).next_to(res, DOWN, buff=0.2)
        eqs = M("=", 32, FG).move_to([3.95, 0.4, 0])
        self.play(FadeIn(eqs), TransformFromCopy(outer, res), FadeIn(rl)); pause(self, 0.5)
        pluses = VGroup()
        for k in range(1, 4):
            Mk = np.outer(us[k], vs[k])
            tk = heat(Mk, small).move_to([xs[k], 0.4, 0])
            lk = N(f"u{k + 1}v{k + 1}ᵀ", 24, MUTED).next_to(tk, UP, buff=0.15)
            pl = M("+", 32, FG).move_to([(xs[k - 1] + xs[k]) / 2, 0.4, 0])
            acc = acc + Mk
            new = heat(acc, small).move_to(res)
            nl = T(f"秩 {k + 1}", 26, ACCENT).next_to(new, DOWN, buff=0.2)
            self.play(FadeIn(pl), FadeIn(tk), FadeIn(lk), run_time=0.6)
            self.play(Transform(res, new), Transform(rl, nl), run_time=0.7)
            pluses.add(pl); labs.add(lk); tiles.append(tk)
            pause(self, 0.3)
        cnt = T("4 个外积：4 × (8 + 8) = 64 个数；一个随便的 8 × 8 矩阵也要 64 个", 24, MUTED).to_edge(DOWN, buff=0.9)
        cnt2 = T("d = 4096 时：r × 8192 对 16.8 M，r 越小越省", 26, ACCENT).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(cnt)); pause(self, 0.5)
        self.play(FadeIn(cnt2, shift=UP * 0.2))
        self.wait(2)
