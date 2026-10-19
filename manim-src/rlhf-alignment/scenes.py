"""rlhf-alignment 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm rlhf-alignment/scenes.py PreferencePair
颜色约定（整讲一致）：被选中的回答 OK，没选中的 WARN，奖励分数 C_K，策略 ACCENT，参考模型 MUTED，KL 绳子 WARN。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np


def card(lines, w=4.6, h=1.5, color=MUTED, size=22):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.15, stroke_color=color, stroke_width=2.5, fill_color=BG, fill_opacity=1)
    t = VGroup(*[T(s, size, FG) for s in lines]).arrange(DOWN, buff=0.12, aligned_edge=LEFT).move_to(r)
    return VGroup(r, t)


class PreferencePair(Scene):
    """两个回答 → 人选一个 → 奖励模型打分 → 分数差过 sigmoid 变成概率。"""

    def construct(self):
        title = T("一对回答，怎么变成一个概率", 36).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        q = T("问：用一句话解释光合作用。", 26, MUTED).next_to(title, DOWN, buff=0.35)
        self.play(FadeIn(q))
        a = card(["回答 A", "植物用光能把二氧化碳和水", "变成糖和氧气。"]).move_to([-3.2, 0.9, 0])
        b = card(["回答 B", "光合作用是一个非常复杂的", "过程，涉及很多……"]).move_to([3.2, 0.9, 0])
        self.play(FadeIn(a, shift=UP * 0.2), FadeIn(b, shift=UP * 0.2)); pause(self)

        # 人选一个
        who = T("标注员选 A", 26, OK).move_to([0, 0.9, 0])
        self.play(FadeIn(who), a[0].animate.set_stroke(OK, 4), b[0].animate.set_stroke(WARN, 2.5).set_opacity(0.6))
        pause(self)

        # 奖励模型给两个分数
        rm = RoundedRectangle(width=3.0, height=0.8, corner_radius=0.15, stroke_color=C_K, stroke_width=2.5).move_to([0, -1.0, 0])
        rml = T("奖励模型", 26, C_K).move_to(rm)
        self.play(FadeOut(who), Create(rm), FadeIn(rml))
        ar1 = Arrow(a.get_bottom(), rm.get_left() + UP * 0.1, buff=0.1, color=MUTED, stroke_width=3)
        ar2 = Arrow(b.get_bottom(), rm.get_right() + UP * 0.1, buff=0.1, color=MUTED, stroke_width=3)
        self.play(GrowArrow(ar1), GrowArrow(ar2))
        ra = M(r"r_A = 1.2", 36, C_K).move_to([-3.2, -2.1, 0])
        rb = M(r"r_B = 0.2", 36, C_K).move_to([3.2, -2.1, 0])
        self.play(TransformFromCopy(rml, ra), TransformFromCopy(rml, rb)); pause(self)

        # 分数差 → sigmoid
        diff = M(r"r_A - r_B = 1.0", 40, C_K).move_to([0, -2.1, 0])
        self.play(TransformMatchingShapes(VGroup(ra.copy(), rb.copy()), diff), FadeOut(ra), FadeOut(rb)); pause(self)
        keep = diff
        self.play(*[FadeOut(m) for m in [q, a, b, rm, rml, ar1, ar2]], keep.animate.move_to([-3.9, 1.4, 0]))

        ax = Axes(x_range=[-5, 5, 1], y_range=[0, 1, 0.5], x_length=6.4, y_length=3.4,
                  axis_config={"color": MUTED, "stroke_width": 2, "include_ticks": False}).move_to([2.2, -0.6, 0])
        lab0 = N("0", 24, MUTED).next_to(ax.c2p(0, 0), DOWN, buff=0.15)
        l1 = N("1", 24, MUTED).next_to(ax.c2p(-5, 1), LEFT, buff=0.15)
        l5 = N("0.5", 24, MUTED).next_to(ax.c2p(-5, 0.5), LEFT, buff=0.15)
        curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=ACCENT, stroke_width=4)
        self.play(Create(ax), FadeIn(lab0, l1, l5)); self.play(Create(curve), run_time=1.4)
        sg = M(r"\sigma(x) = \frac{1}{1+e^{-x}}", 36, ACCENT).next_to(ax, UP, buff=0.15).shift(LEFT * 0.4)
        self.play(FadeIn(sg)); pause(self)

        x = ValueTracker(0)
        dot = always_redraw(lambda: Dot(ax.c2p(x.get_value(), 1 / (1 + np.exp(-x.get_value()))), color=C_K, radius=0.1))
        vl = always_redraw(lambda: DashedLine(ax.c2p(x.get_value(), 0), ax.c2p(x.get_value(), 1 / (1 + np.exp(-x.get_value()))), color=C_K, stroke_width=2))
        self.play(FadeIn(dot), FadeIn(vl))
        self.play(x.animate.set_value(1.0), run_time=1.2)
        hl = DashedLine(ax.c2p(-5, 0.731), ax.c2p(1, 0.731), color=C_K, stroke_width=2)
        p = M(r"P(A \succ B) = 0.73", 40, OK).move_to([-3.9, 0.3, 0])
        self.play(Create(hl), FadeIn(p, shift=UP * 0.2)); pause(self)

        note = T("分差越大越确定；分差为 0 时五五开", 26, FG).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(note))
        self.play(x.animate.set_value(3.0), run_time=1.0)
        self.play(x.animate.set_value(0.0), run_time=1.0)
        self.play(x.animate.set_value(1.0), run_time=0.8)
        self.wait(1.5)


class RLHFLoop(Scene):
    """策略生成 → 奖励模型打分 → 更新策略；一根 KL 绳子把策略拴在参考模型附近。"""

    def construct(self):
        title = T("RLHF：往高分走，但别离开参考模型太远", 34).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        # 右上：三步循环
        steps = ["策略生成回答", "奖励模型打分", "更新策略"]
        cols = [ACCENT, C_K, ACCENT]
        pos = [[3.6, 1.7, 0], [5.4, 0.0, 0], [3.6, -1.7, 0]]
        boxes = VGroup()
        for s, c, p in zip(steps, cols, pos):
            r = RoundedRectangle(width=2.6, height=0.75, corner_radius=0.15, stroke_color=c, stroke_width=2.5, fill_color=BG, fill_opacity=1).move_to(p)
            boxes.add(VGroup(r, T(s, 22, FG).move_to(r)))
        loop = VGroup(
            CurvedArrow(boxes[0].get_right() + DOWN * 0.1, boxes[1].get_top(), angle=-PI / 3, color=MUTED, stroke_width=3, tip_length=0.18),
            CurvedArrow(boxes[1].get_bottom(), boxes[2].get_right() + UP * 0.1, angle=-PI / 3, color=MUTED, stroke_width=3, tip_length=0.18),
            CurvedArrow(boxes[2].get_left(), boxes[0].get_left(), angle=-PI / 2.2, color=MUTED, stroke_width=3, tip_length=0.18),
        )
        self.play(LaggedStart(*[FadeIn(b) for b in boxes], lag_ratio=0.2), Create(loop)); pause(self)

        # 左：一维的「策略空间」，越往右奖励越高
        base_y = -1.2
        line = Line([-6.2, base_y, 0], [1.6, base_y, 0], color=LINE, stroke_width=3)
        rew = Arrow([-2.5, -2.4, 0], [1.6, -2.4, 0], buff=0, color=C_K, stroke_width=4, max_tip_length_to_length_ratio=0.06)
        rewl = T("奖励模型给分越高", 22, C_K).next_to(rew, UP, buff=0.1)
        self.play(Create(line), GrowArrow(rew), FadeIn(rewl))
        ref = Dot([-5.4, base_y, 0], color=MUTED, radius=0.14)
        refl = T("参考模型", 22, MUTED).next_to(ref, UP, buff=0.2)
        self.play(FadeIn(ref), FadeIn(refl))

        px = ValueTracker(-5.4)

        def spring():
            x0, x1 = -5.4, px.get_value()
            if x1 - x0 < 0.05:
                return VMobject()
            n = 14
            pts = [[x0, base_y, 0]]
            for i in range(1, n):
                pts.append([x0 + (x1 - x0) * i / n, base_y + (0.18 if i % 2 else -0.18), 0])
            pts.append([x1, base_y, 0])
            stretch = (x1 - x0) / 6
            return VMobject(stroke_color=WARN, stroke_width=2 + 3 * stretch).set_points_as_corners(pts)

        rope = always_redraw(spring)
        pol = always_redraw(lambda: Dot([px.get_value(), base_y, 0], color=ACCENT, radius=0.17))
        poll = always_redraw(lambda: T("策略", 22, ACCENT).next_to(pol, DOWN, buff=0.2))
        self.add(rope); self.play(FadeIn(pol), FadeIn(poll)); pause(self, 0.4)

        ropel = T("KL 绳子", 22, WARN).move_to([-4.3, 0.0, 0])
        hl = SurroundingRectangle(boxes[2], color=ACCENT, buff=0.06)
        # 每一轮：奖励往右拉，绳子往回拉，越拉越紧，步子越来越小
        targets = [-3.9, -2.9, -2.3, -2.0, -1.85]
        for k, t in enumerate(targets):
            rt = 0.9 if k < 2 else 0.6
            for i in range(3):
                self.play(Indicate(boxes[i], color=cols[i], scale_factor=1.06), run_time=rt * 0.35)
            self.play(px.animate.set_value(t), run_time=rt)
            if k == 1:
                self.play(FadeIn(ropel))
        pause(self)

        stop = T("奖励往右拉，KL 往回拉，两股力在这里平衡", 24, FG).move_to([-2.3, 0.9, 0])
        self.play(FadeIn(stop, shift=UP * 0.2)); pause(self)
        eq = M(r"\max_{\pi}\; \mathbb{E}_{\pi}[\,r\,] \;-\; \beta\, \mathrm{KL}(\pi \,\|\, \pi_{\mathrm{ref}})", 40, FG).to_edge(DOWN, buff=0.3)
        eq.shift(LEFT * 1.0)
        self.play(FadeOut(rew), FadeOut(rewl), Write(eq))
        self.wait(2)
