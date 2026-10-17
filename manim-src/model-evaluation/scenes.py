"""model-evaluation 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm model-evaluation/scenes.py Perplexity
颜色约定（整讲一致）：概率 / 困惑度 ACCENT，榜单分数 WARN，真实能力 OK。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np


def bars(ps, x0, y0, w=0.55, gap=0.15, hmax=5.6, color=ACCENT, opacity=1.0):
    g = VGroup()
    for i, p in enumerate(ps):
        h = max(0.02, p * hmax)
        r = Rectangle(width=w, height=h, stroke_width=0, fill_color=color, fill_opacity=opacity)
        r.move_to([x0 + i * (w + gap), y0 + h / 2, 0])
        g.add(r)
    return g


class Perplexity(Scene):
    """交叉熵 → 2^H → 等效选项数：困惑度就是「在多少个等概率选项里猜」。"""

    def construct(self):
        title = T("困惑度：模型在多少个选项里犹豫", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        V = 8
        logits = np.array([2.1, 1.2, 0.9, 0.2, -0.3, -0.8, -1.4, -2.0])
        p = np.exp(logits) / np.exp(logits).sum()
        H = float(-(p * np.log2(p)).sum())
        ppl = 2 ** H

        base_y = -1.3
        base = Line([-3.2, base_y, 0], [2.6, base_y, 0], color=LINE, stroke_width=2)
        b = bars(p, -2.9, base_y)
        lab = T("下一个 token 的概率分布（8 个候选）", 24, MUTED).next_to(base, DOWN, buff=0.3)
        self.play(Create(base), LaggedStart(*[GrowFromEdge(r, DOWN) for r in b], lag_ratio=0.08), FadeIn(lab)); pause(self)

        # 每根柱子标 p_i
        nums = VGroup(*[N(f"{x:.2f}", 18, MUTED).next_to(r, UP, buff=0.08) for x, r in zip(p, b)])
        self.play(FadeIn(nums)); pause(self, 0.5)

        # 熵
        eq_h = M(r"H = -\sum_i p_i \log_2 p_i", 40).move_to([3.9, 1.3, 0])
        self.play(Write(eq_h)); pause(self, 0.6)
        val_h = M(rf"H = {H:.2f}\ \text{{bit}}", 40, ACCENT).move_to(eq_h)
        self.play(TransformMatchingShapes(eq_h, val_h)); pause(self)

        # 2^H
        eq_p = M(r"\mathrm{PPL} = 2^{H}", 40).next_to(val_h, DOWN, buff=0.5)
        self.play(Write(eq_p)); pause(self, 0.6)
        val_p = M(rf"\mathrm{{PPL}} = 2^{{{H:.2f}}} = {ppl:.1f}", 40, ACCENT).move_to(eq_p)
        self.play(TransformMatchingShapes(eq_p, val_p)); pause(self)

        # 柱子变成 ppl 个等高柱（最后一根按小数截断）
        n_full = int(np.floor(ppl)); frac = ppl - n_full
        uni = bars([1 / ppl] * (n_full + 1), -2.9, base_y)
        last = uni[-1]
        last.stretch_to_fit_width(last.width * max(frac, 0.05)).align_to(uni[-2], LEFT).shift(RIGHT * (uni[-2].width + 0.15))
        last.set_fill(opacity=0.45)
        lab2 = T(f"相当于在 {ppl:.1f} 个等概率选项里猜", 24, ACCENT).next_to(base, DOWN, buff=0.3)
        self.play(FadeOut(nums), Transform(b, uni), Transform(lab, lab2)); pause(self)

        note = T("分布越平，PPL 越接近候选数；越尖，越接近 1", 26, FG).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(2)


class Goodhart(Scene):
    """指标与目标：针对榜单优化之后，分数继续涨，真实能力不再跟着涨。"""

    def construct(self):
        title = T("Goodhart：指标一旦成为目标，就不再是好指标", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        ax = Axes(x_range=[0, 10, 1], y_range=[0, 1.05, 0.25], x_length=10, y_length=4.2,
                  axis_config={"color": MUTED, "stroke_width": 2, "include_ticks": False, "include_tip": False}).shift(DOWN * 0.35)
        xl = T("训练 / 调参投入", 22, MUTED).next_to(ax.x_axis.get_right(), UP, buff=0.12).shift(LEFT * 0.9)
        yl = T("高", 22, MUTED).next_to(ax.y_axis.get_top(), LEFT, buff=0.15)
        self.play(Create(ax), FadeIn(xl), FadeIn(yl)); pause(self, 0.3)

        t_split = 4.5

        def real(x):
            return 0.9 * (1 - np.exp(-x / 2.4)) - (0.03 * (x - t_split) if x > t_split else 0)

        def score(x):
            base = 0.9 * (1 - np.exp(-x / 2.4))
            return base + (0.0 if x <= t_split else 0.02 * (x - t_split))

        c_real = ax.plot(real, x_range=[0, t_split], color=OK, stroke_width=5)
        c_score = ax.plot(score, x_range=[0, t_split], color=WARN, stroke_width=5)
        l_score = T("榜单分数", 24, WARN).next_to(ax.c2p(2.6, score(2.6)), UP, buff=0.3)
        l_real = T("真实能力", 24, OK).next_to(ax.c2p(2.6, real(2.6)), DOWN, buff=0.3)
        self.play(Create(c_score), Create(c_real), run_time=2)
        self.play(FadeIn(l_score), FadeIn(l_real)); pause(self)
        same = T("一开始两条线重合：分数高 = 能力强", 26, FG).to_edge(DOWN, buff=0.25)
        self.play(FadeIn(same)); pause(self)

        vline = DashedLine(ax.c2p(t_split, 0), ax.c2p(t_split, 1), color=MUTED, dash_length=0.12)
        vl = T("开始针对榜单优化", 22, MUTED).next_to(vline.get_top(), UP, buff=0.1)
        self.play(Create(vline), FadeIn(vl)); pause(self, 0.5)

        c_real2 = ax.plot(real, x_range=[t_split, 10], color=OK, stroke_width=5)
        c_score2 = ax.plot(score, x_range=[t_split, 10], color=WARN, stroke_width=5)
        self.play(Create(c_score2), Create(c_real2), run_time=2.5)
        gap = DoubleArrow(ax.c2p(10, real(10)), ax.c2p(10, score(10)), buff=0, color=WARN, stroke_width=3, tip_length=0.15)
        gl = T("虚高", 22, WARN).next_to(gap, RIGHT, buff=0.08)
        self.play(GrowFromCenter(gap), FadeIn(gl),
                  l_score.animate.next_to(ax.c2p(8.4, score(8.4)), UP, buff=0.2),
                  l_real.animate.next_to(ax.c2p(8.4, real(8.4)), DOWN, buff=0.2)); pause(self)

        end = T("刷题、背答案、挑最好的一次提交：分数在涨，能力没涨", 26, FG).to_edge(DOWN, buff=0.25)
        self.play(Transform(same, end))
        self.wait(2)
