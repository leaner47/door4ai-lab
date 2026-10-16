"""gradient-descent 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm gradient-descent/scenes.py Descent1D
颜色约定（整讲一致）：参数/当前点 ACCENT，梯度与步子 WARN，谷底 OK。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np


class Descent1D(Scene):
    """一维：斜率 → 反方向迈一步 → 重复，步子自己变小。"""

    def construct(self):
        title = T("看斜率，往下走一步", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        ax = Axes(x_range=[-3, 3, 1], y_range=[0, 9, 3], x_length=9, y_length=4.6,
                  axis_config={"color": MUTED, "include_ticks": False}).shift(DOWN * 0.55)
        f = lambda x: x ** 2
        df = lambda x: 2 * x
        curve = ax.plot(f, x_range=[-3, 3], color=FG, stroke_width=3)
        lx = M("x", 34, MUTED).next_to(ax.x_axis, RIGHT, buff=0.15)
        ly = M("L", 34, MUTED).next_to(ax.y_axis, UP, buff=0.15)
        self.play(Create(ax), Create(curve), FadeIn(lx), FadeIn(ly)); pause(self, 0.4)

        x = ValueTracker(2.6)
        dot = always_redraw(lambda: Dot(ax.c2p(x.get_value(), f(x.get_value())), radius=0.11, color=ACCENT))
        self.play(FadeIn(dot, scale=1.6)); pause(self, 0.4)

        def tangent():
            x0 = x.get_value(); y0 = f(x0); k = df(x0); h = 0.8
            return Line(ax.c2p(x0 - h, y0 - k * h), ax.c2p(x0 + h, y0 + k * h), color=WARN, stroke_width=4)
        tan = always_redraw(tangent)
        slope_lbl = T("斜率为正：往右是上坡", 26, WARN).to_corner(UR, buff=0.5).shift(DOWN * 0.9)
        self.play(Create(tan), FadeIn(slope_lbl)); pause(self)

        eq = M(r"x \leftarrow x - \eta \, L'(x)", 42).to_corner(UL, buff=0.5).shift(DOWN * 0.9)
        self.play(Write(eq)); pause(self)

        eta = 0.15
        trail = VGroup()
        for i in range(7):
            x0 = x.get_value(); x1 = x0 - eta * df(x0)
            arr = Arrow(ax.c2p(x0, 0), ax.c2p(x1, 0), buff=0, color=WARN, stroke_width=5,
                        max_tip_length_to_length_ratio=0.35)
            ghost = Dot(ax.c2p(x0, f(x0)), radius=0.06, color=ACCENT, fill_opacity=0.45)
            trail.add(ghost); self.add(ghost)
            rt = 0.9 if i < 2 else 0.45
            self.play(GrowArrow(arr), run_time=rt * 0.6)
            self.play(x.animate.set_value(x1), FadeOut(arr), run_time=rt)
            if i == 1:
                self.play(Transform(slope_lbl, T("越靠近谷底，斜率越小，步子越小", 26, WARN).move_to(slope_lbl).align_to(slope_lbl, RIGHT)))
        pause(self)

        bottom = T("斜率接近 0：停在谷底", 28, OK).next_to(ax.c2p(0, 0), UP, buff=1.6)
        self.play(FadeIn(bottom, shift=UP * 0.2))
        self.wait(1.5)


class Gradient2D(Scene):
    """二维：梯度垂直于等高线，沿 −∇L 一步步下到谷底。"""

    def construct(self):
        title = T("两个参数：梯度是一支箭", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        # L(w, b) = 0.5 * (w^2 + 6 b^2)，椭圆等高线
        a, c = 1.0, 6.0
        L = lambda w, b: 0.5 * (a * w * w + c * b * b)
        grad = lambda w, b: np.array([a * w, c * b])
        plane = NumberPlane(x_range=[-4, 4, 1], y_range=[-2.2, 2.2, 1], x_length=8.6, y_length=4.75,
                            background_line_style={"stroke_color": LINE, "stroke_width": 1, "stroke_opacity": 0.6},
                            axis_config={"stroke_color": MUTED, "stroke_width": 1.5}).shift(DOWN * 0.5)
        self.play(Create(plane), run_time=1)

        levels = [0.25, 0.75, 1.5, 2.5, 3.75, 5.25, 7.0]
        rings = VGroup()
        for i, lv in enumerate(levels):
            rw, rb = np.sqrt(2 * lv / a), np.sqrt(2 * lv / c)
            e = ParametricFunction(lambda t, rw=rw, rb=rb: plane.c2p(rw * np.cos(t), rb * np.sin(t)), t_range=[0, TAU],
                                   color=interpolate_color(ManimColor(OK), ManimColor(MUTED), i / (len(levels) - 1)), stroke_width=2)
            rings.add(e)
        lab = T("等高线：同一圈上损失相同", 24, MUTED).to_corner(UR, buff=0.4).shift(DOWN * 0.85)
        self.play(LaggedStart(*[Create(r) for r in rings], lag_ratio=0.12), FadeIn(lab), run_time=2); pause(self)

        p = np.array([-3.2, 1.3])
        dot = Dot(plane.c2p(*p), radius=0.1, color=ACCENT)
        self.play(FadeIn(dot, scale=1.6)); pause(self, 0.4)

        g = grad(*p); gu = g / np.linalg.norm(g)
        up = Arrow(plane.c2p(*p), plane.c2p(*(p + gu * 1.3)), buff=0, color=MUTED, stroke_width=5)
        up_l = M(r"\nabla L", 34, MUTED).next_to(up.get_end(), UP, buff=0.1)
        self.play(GrowArrow(up), FadeIn(up_l)); pause(self, 0.5)
        self.play(Transform(lab, T("梯度垂直于等高线，指向上坡最陡处", 24, MUTED).to_corner(UR, buff=0.4).shift(DOWN * 0.85))); pause(self)

        down = Arrow(plane.c2p(*p), plane.c2p(*(p - gu * 1.3)), buff=0, color=WARN, stroke_width=6)
        down_l = M(r"-\nabla L", 34, WARN).next_to(down.get_end(), DOWN, buff=0.1)
        self.play(ReplacementTransform(up.copy(), down), FadeIn(down_l)); pause(self, 0.5)
        self.play(FadeOut(up), FadeOut(up_l), FadeOut(down), FadeOut(down_l))

        eq = M(r"(w, b) \leftarrow (w, b) - \eta \, \nabla L", 38).to_corner(UL, buff=0.4).shift(DOWN * 0.85)
        self.play(Write(eq)); pause(self, 0.5)

        eta = 0.3
        path = [p.copy()]
        for _ in range(22):
            path.append(path[-1] - eta * grad(*path[-1]))
        for i in range(1, len(path)):
            seg = Line(plane.c2p(*path[i - 1]), plane.c2p(*path[i]), color=ACCENT, stroke_width=3)
            rt = 0.5 if i < 5 else 0.18
            self.play(Create(seg), dot.animate.move_to(plane.c2p(*path[i])), run_time=rt)
        pause(self)
        end = T("在陡的方向来回弹，在缓的方向慢慢挪", 26, FG).next_to(plane, DOWN, buff=0.15)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(1.8)
