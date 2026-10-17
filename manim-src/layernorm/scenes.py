"""layernorm 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm layernorm/scenes.py NormalizeVector
颜色约定（整讲一致）：原始向量 / 不做 Norm 用 WARN，Norm 之后 / 主干 用 ACCENT，Post-Norm 用 OK，层 MUTED。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np

X0 = np.array([2.1, -0.4, 3.7, 0.9, -1.2, 5.3, 0.2, 1.6])   # 与实验页 00 相同的 8 维向量
GAMMA, BETA = 1.5, 0.5


def bar_chart(values, color, unit=0.45, width=0.5, gap=0.22):
    """一排条形，底线在 y=0。返回 VGroup(bars)。"""
    bars = VGroup()
    for i, v in enumerate(values):
        h = max(abs(v) * unit, 0.02)
        r = Rectangle(width=width, height=h, stroke_width=0, fill_color=color, fill_opacity=0.9)
        x = (i - (len(values) - 1) / 2) * (width + gap)
        r.move_to([x, (v * unit) / 2, 0])
        bars.add(r)
    return bars


class NormalizeVector(Scene):
    """一个向量：减均值 → 除标准差 → 乘 γ 加 β。"""

    def construct(self):
        title = T("把一个向量拉回同一把尺子", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        unit = 0.45
        origin = DOWN * 0.9
        axis = Line(LEFT * 3.3, RIGHT * 3.3, color=MUTED, stroke_width=2).shift(origin)
        bars = bar_chart(X0, WARN, unit).shift(origin)
        labels = VGroup(*[N(f"{v:g}", 20, FG).next_to(b, UP if v >= 0 else DOWN, buff=0.1) for v, b in zip(X0, bars)])
        name = M(r"x", 40, WARN).next_to(axis, LEFT, buff=0.5)
        self.play(Create(axis), FadeIn(name), LaggedStart(*[GrowFromEdge(b, DOWN if v >= 0 else UP) for v, b in zip(X0, bars)], lag_ratio=0.08))
        self.play(FadeIn(labels)); pause(self)

        # 1. 均值
        mu = X0.mean(); sd = X0.std()
        mline = DashedLine(LEFT * 3.3, RIGHT * 3.3, color=ACCENT, stroke_width=3).shift(origin + UP * mu * unit)
        mlab = VGroup(M(r"\mu =", 30, ACCENT), N(f"{mu:.2f}", 30, ACCENT)).arrange(RIGHT, buff=0.12).next_to(mline, RIGHT, buff=0.25)
        self.play(Create(mline), FadeIn(mlab)); pause(self)
        step1 = T("① 减去均值：整体平移，中心到 0", 28, FG).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(step1, shift=UP * 0.2))
        x1 = X0 - mu
        bars1 = bar_chart(x1, WARN, unit).shift(origin)
        labels1 = VGroup(*[N(f"{v:.2f}", 20, FG).next_to(b, UP if v >= 0 else DOWN, buff=0.1) for v, b in zip(x1, bars1)])
        self.play(Transform(bars, bars1), Transform(labels, labels1), mline.animate.shift(DOWN * mu * unit), FadeOut(mlab), run_time=1.2)
        pause(self)

        # 2. 标准差
        brace = BraceBetweenPoints(origin + LEFT * 3.6, origin + LEFT * 3.6 + UP * sd * unit, direction=LEFT, color=ACCENT)
        slab = VGroup(M(r"\sigma =", 30, ACCENT), N(f"{sd:.2f}", 30, ACCENT)).arrange(RIGHT, buff=0.12).next_to(brace, LEFT, buff=0.15)
        self.play(FadeOut(name), GrowFromCenter(brace), FadeIn(slab)); pause(self, 0.5)
        step2 = T("② 除以标准差：整体缩放，散布变成 1", 28, FG).to_edge(DOWN, buff=0.5)
        self.play(Transform(step1, step2))
        x2 = x1 / sd
        bars2 = bar_chart(x2, ACCENT, unit).shift(origin)
        labels2 = VGroup(*[N(f"{v:.2f}", 20, FG).next_to(b, UP if v >= 0 else DOWN, buff=0.1) for v, b in zip(x2, bars2)])
        brace2 = BraceBetweenPoints(origin + LEFT * 3.6, origin + LEFT * 3.6 + UP * unit, direction=LEFT, color=ACCENT)
        slab2 = N("1", 30, ACCENT).next_to(brace2, LEFT, buff=0.15)
        self.play(Transform(bars, bars2), Transform(labels, labels2), Transform(brace, brace2), Transform(slab, slab2), run_time=1.2)
        pause(self)

        # 3. γ β
        step3 = VGroup(T("③ 乘 γ 加 β：网络自己学的两个旋钮", 28, FG), VGroup(M(r"\gamma =", 26, OK), N(f"{GAMMA:g}", 26, OK), M(r"\;\;\beta =", 26, OK), N(f"{BETA:g}", 26, OK)).arrange(RIGHT, buff=0.1)).arrange(DOWN, buff=0.15).to_edge(DOWN, buff=0.35)
        self.play(Transform(step1, step3), FadeOut(brace), FadeOut(slab), FadeOut(mline))
        x3 = GAMMA * x2 + BETA
        bars3 = bar_chart(x3, OK, unit).shift(origin)
        labels3 = VGroup(*[N(f"{v:.2f}", 20, FG).next_to(b, UP if v >= 0 else DOWN, buff=0.1) for v, b in zip(x3, bars3)])
        self.play(Transform(bars, bars3), Transform(labels, labels3), run_time=1.2)
        pause(self)

        # 公式
        eq = M(r"y = \gamma \cdot \frac{x - \mu}{\sigma} + \beta", 44).next_to(title, DOWN, buff=0.35)
        self.play(Write(eq))
        self.wait(2)


def block(label, color, w=1.3, h=0.6):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.1, stroke_color=color, stroke_width=2.5, fill_color=BG, fill_opacity=1)
    return VGroup(r, T(label, 22, color).move_to(r))


def plus_node(color=FG):
    c = Circle(radius=0.2, stroke_color=color, stroke_width=2.5, fill_color=BG, fill_opacity=1)
    return VGroup(c, M("+", 30, color).move_to(c))


class PrePostNorm(Scene):
    """Post-Norm 把 Norm 放在主干上，Pre-Norm 放在分支里：直达通路有没有。"""

    def construct(self):
        title = T("Norm 放在主干上，还是分支里", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        def column(kind, x0):
            """竖着画 3 层残差块；返回 (VGroup 全部, 主干各段, Norm 块列表, 梯度经过的主干锚点)。"""
            g = VGroup(); trunk = []; norms = []; anchors = []
            y = -2.7
            tag = T("Post-Norm" if kind == "post" else "Pre-Norm", 28, OK if kind == "post" else ACCENT).move_to([x0, y - 0.45, 0])
            g.add(tag)
            cur = [x0, y, 0]
            for i in range(3):
                if kind == "post":
                    # cur → (+) → Norm → next；分支：cur → F → (+)
                    p = plus_node().move_to([x0, y + 0.75, 0])
                    nm = block("Norm", OK).move_to([x0, y + 1.55, 0])
                    seg1 = Line(cur, p.get_bottom(), color=ACCENT, stroke_width=5)
                    seg2 = Line(p.get_top(), nm.get_bottom(), color=ACCENT, stroke_width=5)
                    seg3 = Line(nm.get_top(), [x0, y + 2.2, 0], color=ACCENT, stroke_width=5)
                    f = block("F", MUTED, w=0.9).move_to([x0 + 1.25, y + 0.5, 0])
                    br1 = Line([x0, y + 0.15, 0], [x0 + 1.25, y + 0.15, 0], color=MUTED, stroke_width=2.5)
                    br2 = Line([x0 + 1.25, y + 0.15, 0], f.get_bottom(), color=MUTED, stroke_width=2.5)
                    br3 = Line(f.get_top(), [x0 + 1.25, y + 0.75, 0], color=MUTED, stroke_width=2.5)
                    br4 = Arrow([x0 + 1.25, y + 0.75, 0], p.get_right(), buff=0, color=MUTED, stroke_width=2.5, max_tip_length_to_length_ratio=0.2)
                    g.add(seg1, seg2, seg3, br1, br2, br3, br4, f, p, nm)
                    trunk += [seg1, seg2, seg3]; norms.append(nm); anchors.append(nm)
                else:
                    p = plus_node().move_to([x0, y + 1.55, 0])
                    seg1 = Line(cur, p.get_bottom(), color=ACCENT, stroke_width=5)
                    seg3 = Line(p.get_top(), [x0, y + 2.2, 0], color=ACCENT, stroke_width=5)
                    nm = block("Norm", ACCENT, w=0.95, h=0.5).move_to([x0 + 1.3, y + 0.55, 0])
                    f = block("F", MUTED, w=0.9, h=0.5).move_to([x0 + 1.3, y + 1.2, 0])
                    br1 = Line([x0, y + 0.15, 0], [x0 + 1.3, y + 0.15, 0], color=MUTED, stroke_width=2.5)
                    br2 = Line([x0 + 1.3, y + 0.15, 0], nm.get_bottom(), color=MUTED, stroke_width=2.5)
                    br3 = Line(nm.get_top(), f.get_bottom(), color=MUTED, stroke_width=2.5)
                    br4 = Line(f.get_top(), [x0 + 1.3, y + 1.55, 0], color=MUTED, stroke_width=2.5)
                    br5 = Arrow([x0 + 1.3, y + 1.55, 0], p.get_right(), buff=0, color=MUTED, stroke_width=2.5, max_tip_length_to_length_ratio=0.2)
                    g.add(seg1, seg3, br1, br2, br3, br4, br5, nm, f, p)
                    trunk += [seg1, seg3]; norms.append(nm); anchors.append(p)
                y += 2.2; cur = [x0, y, 0]
            return g, trunk, norms, anchors

        gp, tp, np_, ap = column("post", -4.2)
        gq, tq, nq, aq = column("pre", 1.6)
        # 缩放到画面里（3 层 × 2.2 = 6.6 高）
        both = VGroup(gp, gq).scale(0.72).move_to(DOWN * 0.25)
        self.play(FadeIn(gp)); pause(self, 0.5)
        self.play(FadeIn(gq)); pause(self)

        note1 = T("主干上每层都过一次 Norm", 24, OK).next_to(gp, RIGHT, buff=0.1).shift(UP * 2.0 + RIGHT * 0.1)
        note2 = T("主干一路直通，Norm 只在分支里", 24, ACCENT).next_to(gq, RIGHT, buff=0.1).shift(UP * 2.0 + RIGHT * 0.1)
        self.play(*[Indicate(n, color=OK, scale_factor=1.15) for n in np_], FadeIn(note1)); pause(self, 0.6)
        self.play(*[Indicate(n, color=ACCENT, scale_factor=1.15) for n in nq], FadeIn(note2)); pause(self)
        self.play(FadeOut(note1), FadeOut(note2))

        # 梯度往回走：小球从顶端走到底端，沿途记增益
        head = T("梯度从上往下回传，主干上还剩多少", 28, FG).next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(head)); pause(self, 0.3)

        def run(trunk, norms, factor_tex, color, final_tex, side):
            top = trunk[-1].get_end(); bottom = trunk[0].get_start()
            dot = Dot(top, radius=0.11, color=color)
            self.play(FadeIn(dot, scale=1.6), run_time=0.3)
            tags = VGroup()
            for nm in reversed(norms):
                self.play(dot.animate.move_to(nm.get_center()), run_time=0.45, rate_func=linear)
                t = M(factor_tex, 28, color).next_to(nm, LEFT, buff=0.15)
                self.play(FadeIn(t, shift=LEFT * 0.1), Flash(dot, color=color, line_length=0.15, flash_radius=0.25), run_time=0.4)
                tags.add(t)
            self.play(dot.animate.move_to(bottom), run_time=0.45, rate_func=linear)
            res = M(final_tex, 34, color).move_to([side, bottom[1] + 1.2, 0])
            self.play(FadeIn(res, shift=DOWN * 0.1))
            return dot, tags, res

        dp, tgp, rp = run(tp, ap, r"\times \tfrac{1}{\sigma}", OK, r"\tfrac{1}{\sigma_3}\cdot\tfrac{1}{\sigma_2}\cdot\tfrac{1}{\sigma_1}", -5.6)
        pause(self, 0.4)
        dq, tgq, rq = run(tq, aq, r"\times 1", ACCENT, r"1 \cdot 1 \cdot 1 = 1", 5.2)
        pause(self)
        end = T("Post-Norm 的直达通路每层打一次折，层数一多就没了；Pre-Norm 的直达通路始终是 1", 24, FG).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2)
