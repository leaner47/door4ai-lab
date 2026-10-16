"""residual-connection 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm residual-connection/scenes.py GradientHighway
颜色约定（整讲一致）：普通网络 WARN，残差 / 主干 ACCENT，层 MUTED，修正量 OK。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np


def layer_box(label, w=0.95, h=0.75):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.12, stroke_color=MUTED, stroke_width=2, fill_color=BG, fill_opacity=1)
    t = N(label, 26, FG).move_to(r)
    return VGroup(r, t)


class GradientHighway(Scene):
    """梯度往回传：普通网络层层打折；残差网络总有一条导数为 1 的直达通路。"""

    def construct(self):
        title = T("梯度往回传，还剩多少", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        n = 6
        # —— 普通网络 ——
        tag1 = T("普通网络", 26, WARN).move_to([-5.6, 1.6, 0])
        boxes = VGroup(*[layer_box(f"{i + 1}") for i in range(n)]).arrange(RIGHT, buff=0.55).move_to([0.6, 1.6, 0])
        links = VGroup(*[Arrow(boxes[i].get_right(), boxes[i + 1].get_left(), buff=0.05, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.3) for i in range(n - 1)])
        self.play(FadeIn(tag1), LaggedStart(*[FadeIn(b) for b in boxes], lag_ratio=0.1), Create(links)); pause(self, 0.4)

        vals = [1 * 0.5 ** k for k in range(n)]
        lab = N("1", 28, WARN).next_to(boxes[-1], DOWN, buff=0.25)
        labs = VGroup(lab)
        self.play(FadeIn(lab, shift=UP * 0.2))
        factor = T("每层导数 × 0.5", 24, WARN).next_to(boxes, UP, buff=0.3)
        self.play(FadeIn(factor))
        for k in range(1, n):
            i = n - 1 - k
            new = N(f"{vals[k]:.3g}", 28, WARN).set_opacity(max(0.6, vals[k] ** 0.3)).next_to(boxes[i], DOWN, buff=0.25)
            self.play(TransformFromCopy(lab, new), run_time=0.45)
            lab = new; labs.add(new)
        pause(self, 0.3)
        warn = T("到第 1 层只剩 3%：前面的层学不动", 24, WARN).next_to(lab, DOWN, buff=0.25).align_to(boxes, LEFT)
        self.play(FadeIn(warn)); pause(self)

        # —— 残差网络 ——
        tag2 = T("残差网络", 26, ACCENT).move_to([-5.6, -1.4, 0])
        boxes2 = boxes.copy().move_to([0.6, -1.4, 0])
        links2 = VGroup(*[Arrow(boxes2[i].get_right(), boxes2[i + 1].get_left(), buff=0.05, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.3) for i in range(n - 1)])
        skips = VGroup(*[CurvedArrow(boxes2[i].get_left() + LEFT * 0.22 + UP * 0.05, boxes2[i].get_right() + RIGHT * 0.22 + UP * 0.05, angle=-PI * 0.75, color=ACCENT, stroke_width=3, tip_length=0.15) for i in range(n)])
        self.play(FadeIn(tag2), FadeIn(boxes2), Create(links2)); pause(self, 0.3)
        self.play(LaggedStart(*[Create(s) for s in skips], lag_ratio=0.1))
        f2 = T("每层导数 = 1 + 分支导数", 24, ACCENT).next_to(boxes2, DOWN, buff=0.35)
        self.play(FadeIn(f2)); pause(self)

        hw = Line(boxes2[-1].get_bottom() + DOWN * 0.15, boxes2[0].get_bottom() + DOWN * 0.15, color=ACCENT, stroke_width=8)
        self.play(Create(hw), run_time=1.4)
        one = N("1", 30, ACCENT).next_to(hw, LEFT, buff=0.2)
        self.play(FadeIn(one, scale=1.4)); pause(self)

        # —— 展开乘积 ——
        self.play(*[FadeOut(m) for m in [tag1, boxes, links, labs, factor, warn, f2, hw, one]],
                  VGroup(tag2, boxes2, links2, skips).animate.shift(UP * 3.0))
        eq1 = M(r"(1+a)(1+b)(1+c)", 46).move_to(DOWN * 0.3)
        self.play(Write(eq1)); pause(self)
        eq2 = MathTex(r"=", r"1", r"+ a + b + c", r"+ ab + ac + bc + abc", font_size=46, color=FG).move_to(DOWN * 0.3)
        eq2[1].set_color(ACCENT)
        self.play(TransformMatchingShapes(eq1, eq2)); pause(self)
        note = T("每一项是一条通路；那个 1 是一条一层都不经过的直达通路", 26, FG).next_to(eq2, DOWN, buff=0.5)
        box = SurroundingRectangle(eq2[1], color=ACCENT, buff=0.12)
        self.play(Create(box), FadeIn(note))
        self.wait(2)


class ResidualStream(Scene):
    """Transformer 的残差流：一条主干贯穿所有层，每层读一点、写回一点修正。"""

    def construct(self):
        title = T("残差流：每层只往主干上加一点", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        y0 = -1.6
        stream = Arrow([-6.4, y0, 0], [6.4, y0, 0], buff=0, color=ACCENT, stroke_width=10, max_tip_length_to_length_ratio=0.03)
        sl = T("残差流", 24, ACCENT).next_to(stream.get_start(), UP, buff=0.15).shift(RIGHT * 0.5)
        self.play(GrowArrow(stream), FadeIn(sl)); pause(self, 0.3)

        rng = np.random.default_rng(3)
        vec = rng.normal(0, 1, 6)

        def column(v, x):
            cells = VGroup()
            for k, a in enumerate(v):
                c = Square(0.32, stroke_width=1, stroke_color=BG)
                c.set_fill(ACCENT if a >= 0 else WARN, opacity=min(1, 0.15 + abs(a) * 0.45))
                cells.add(c)
            cells.arrange(DOWN, buff=0).move_to([x, y0, 0])
            return cells

        xs = [-5.0, -2.6, -0.2, 2.2, 4.6]
        col = column(vec, xs[0])
        tok = T("一个 token 的向量", 22, MUTED).next_to(col, DOWN, buff=0.2)
        self.play(FadeIn(col), FadeIn(tok)); pause(self)
        self.play(FadeOut(tok))

        names = ["注意力", "MLP", "注意力", "MLP"]
        for i, name in enumerate(names):
            xm = (xs[i] + xs[i + 1]) / 2
            box = layer_box(name, w=1.5, h=0.8).move_to([xm, 1.2, 0])
            box[1].become(T(name, 24, FG).move_to(box[0]))
            rd = Arrow([xm - 0.35, y0 + 1.1, 0], [xm - 0.35, 0.75, 0], buff=0, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.2)
            wr = Arrow([xm + 0.35, 0.75, 0], [xm + 0.35, y0 + 1.1, 0], buff=0, color=OK, stroke_width=3, max_tip_length_to_length_ratio=0.2)
            plus = M("+", 40, OK).move_to([xm + 0.35, y0 + 0.9, 0]).shift(RIGHT * 0.3)
            rt = 1.0 if i == 0 else 0.6
            self.play(FadeIn(box), run_time=rt * 0.6)
            if i == 0:
                lab_r = T("读", 22, MUTED).next_to(rd, LEFT, buff=0.1)
                lab_w = T("写回修正", 22, OK).next_to(wr, RIGHT, buff=0.1)
                self.play(GrowArrow(rd), FadeIn(lab_r)); self.play(GrowArrow(wr), FadeIn(lab_w), FadeIn(plus))
            else:
                self.play(GrowArrow(rd), run_time=rt * 0.5); self.play(GrowArrow(wr), FadeIn(plus), run_time=rt * 0.5)
            delta = rng.normal(0, 0.35, 6)
            vec = vec + delta
            new = column(vec, xs[i + 1])
            self.play(TransformFromCopy(col, new), run_time=rt)
            col = new
            if i == 0:
                self.play(FadeOut(lab_r), FadeOut(lab_w))
        pause(self)
        end = T("原来的信息一直留在主干上，第 30 层也读得到第 1 层写下的东西", 24, FG).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2)
