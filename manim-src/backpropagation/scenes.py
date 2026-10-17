"""backpropagation 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm backpropagation/scenes.py ChainRule
颜色约定（整讲一致）：前向值 ACCENT（节点下方），反向梯度 WARN（节点上方），局部导数 C_K（黄），节点 MUTED。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *


def node(label, w=1.25, h=0.72, size=34):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.12, stroke_color=MUTED, stroke_width=2, fill_color=BG, fill_opacity=1)
    t = M(label, size, FG).move_to(r)
    return VGroup(r, t)


def edge(a, b, color=MUTED, w=3):
    return Arrow(a.get_right(), b.get_left(), buff=0.08, color=color, stroke_width=w, max_tip_length_to_length_ratio=0.12)


class ChainRule(Scene):
    """链式法则沿计算图回传：数字从右往左流，每过一条边乘上局部导数。"""

    def construct(self):
        title = T("链式法则在计算图上往回走", 36).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.3)
        formula = M(r"y = (a \cdot b + c)^2", 38).next_to(title, DOWN, buff=0.2)
        self.play(FadeIn(formula)); pause(self, 0.4)

        # —— 图 ——
        pos = {"a": [-5.3, 1.3, 0], "b": [-5.3, -0.9, 0], "u": [-2.0, 0.2, 0], "c": [-2.0, -2.0, 0], "v": [1.3, -0.9, 0], "y": [4.6, -0.9, 0]}
        labels = {"a": "a", "b": "b", "c": "c", "u": r"u = a \cdot b", "v": r"v = u + c", "y": r"y = v^2"}
        nd = {k: node(labels[k], w=1.9 if k in "uvy" else 1.1, size=32).move_to(p) for k, p in pos.items()}
        edges = {("a", "u"): edge(nd["a"], nd["u"]), ("b", "u"): edge(nd["b"], nd["u"]), ("u", "v"): edge(nd["u"], nd["v"]), ("c", "v"): edge(nd["c"], nd["v"]), ("v", "y"): edge(nd["v"], nd["y"])}
        self.play(LaggedStart(*[FadeIn(n) for n in nd.values()], lag_ratio=0.08), LaggedStart(*[GrowArrow(e) for e in edges.values()], lag_ratio=0.08))
        pause(self, 0.4)

        # —— 前向：值在节点下方（ACCENT）——
        fwd = T("前向：从左到右算出每个节点的值", 26, ACCENT).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(fwd))
        vals = {"a": "2", "b": "3", "c": "1", "u": "6", "v": "7", "y": "49"}
        vt = {k: N(vals[k], 30, ACCENT).next_to(nd[k], DOWN, buff=0.1) for k in vals}
        self.play(*[FadeIn(vt[k], shift=UP * 0.2) for k in ["a", "b", "c"]]); pause(self, 0.3)
        for k, src in [("u", ["a", "b"]), ("v", ["u", "c"]), ("y", ["v"])]:
            self.play(*[Indicate(vt[s], color=ACCENT, scale_factor=1.15) for s in src], run_time=0.5)
            self.play(FadeIn(vt[k], shift=LEFT * 0.3), run_time=0.5)
        pause(self)

        # —— 反向：梯度从 y 往回流（WARN，节点上方），每条边乘上局部导数（C_K）——
        bwd = T("反向：从 y 出发往回走，每过一条边乘上这条边的局部导数", 26, WARN).to_edge(DOWN, buff=0.4)
        self.play(FadeOut(fwd), FadeIn(bwd))
        gt = {"y": N("1", 30, WARN).next_to(nd["y"], UP, buff=0.12)}
        g_lab = M(r"\partial y/\partial y = 1", 24, WARN).next_to(gt["y"], UP, buff=0.08)
        self.play(FadeIn(gt["y"], scale=1.5), FadeIn(g_lab)); pause(self, 0.5)
        self.play(FadeOut(g_lab))
        grads = {"y": "1", "v": "14", "u": "14", "c": "14", "a": "42", "b": "28"}

        def flow(frm, to, local_tex, local_val, side=UP):
            e = edges[(to, frm)]
            lab = M(local_tex, 24, C_K).next_to(e, side, buff=0.1)
            self.play(e.animate.set_color(WARN), FadeIn(lab), run_time=0.5)
            mov = gt[frm].copy()
            tmp = M(rf"{grads[frm]} \times {local_val}", 26, WARN).next_to(e, -side, buff=0.1)
            self.play(Transform(mov, tmp), run_time=0.55); pause(self, 0.35)
            gt[to] = N(grads[to], 30, WARN).next_to(nd[to], UP, buff=0.12)
            self.play(Transform(mov, gt[to]), run_time=0.45)
            self.remove(mov); self.add(gt[to])

        flow("y", "v", r"\times\, 2v = 14", "14"); pause(self, 0.3)
        flow("v", "u", r"\times\, 1", "1")
        flow("v", "c", r"\times\, 1", "1", side=DOWN); pause(self, 0.3)
        flow("u", "a", r"\times\, b = 3", "3")
        flow("u", "b", r"\times\, a = 2", "2", side=DOWN); pause(self)

        # —— 总结：∂y/∂a 是沿途局部导数的乘积 ——
        self.play(FadeOut(bwd))
        eq = MathTex(r"\partial y/\partial a", "=", r"2v", r"\cdot", "1", r"\cdot", "b", "=", r"14 \cdot 1 \cdot 3", "=", "42", font_size=38, color=FG).to_edge(DOWN, buff=0.4)
        for i in (2, 4, 6):
            eq[i].set_color(C_K)
        eq[10].set_color(WARN)
        self.play(Write(eq)); pause(self)
        box = SurroundingRectangle(gt["a"], color=WARN, buff=0.1)
        self.play(Create(box))
        self.wait(2)


class Backward2Layer(Scene):
    """两层网络 2→3→1：一次前向、一次反向，13 个参数的梯度全部算出。"""

    def construct(self):
        title = T("一次前向、一次反向", 36).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.3)

        # —— 网络 ——
        xs = [node(r"x_1").move_to([-5.0, 0.5, 0]), node(r"x_2").move_to([-5.0, -1.5, 0])]
        hs = [node(r"h_1").move_to([-1.3, 1.1, 0]), node(r"h_2").move_to([-1.3, -0.5, 0]), node(r"h_3").move_to([-1.3, -2.1, 0])]
        yh = node(r"\hat y").move_to([2.4, -0.5, 0])
        L = node(r"L", w=1.0).move_to([5.3, -0.5, 0])
        e1 = VGroup(*[edge(x, h, w=2) for h in hs for x in xs])
        e2 = VGroup(*[edge(h, yh, w=2) for h in hs])
        e3 = edge(yh, L, w=2)
        w1 = M(r"W_1,\ b_1", 26, MUTED).move_to([-3.4, 2.3, 0])
        w2 = M(r"W_2,\ b_2", 26, MUTED).move_to([3.2, 2.3, 0])
        lossf = M(r"L = \tfrac12(\hat y - y)^2,\ \ y = 1", 24, MUTED).next_to(L, UP, buff=0.25)
        self.play(FadeIn(VGroup(*xs, *hs, yh, L)), GrowArrow(e3), LaggedStart(*[GrowArrow(e) for e in [*e1, *e2]], lag_ratio=0.03), FadeIn(w1), FadeIn(w2), FadeIn(lossf))
        pause(self, 0.4)

        # —— 前向 ——
        fwd = T("前向：z = W₁x + b₁，h = ReLU(z)，一路算到损失，记下每个节点的局部导数", 24, ACCENT).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(fwd))
        vx = [N("1", 28, ACCENT).next_to(xs[0], DOWN, buff=0.08), N("2", 28, ACCENT).next_to(xs[1], DOWN, buff=0.08)]
        self.play(*[FadeIn(v, shift=UP * 0.2) for v in vx]); pause(self, 0.3)
        zt = [M(r"z_1 = 0.1", 22, ACCENT), M(r"z_2 = 0.6", 22, ACCENT), M(r"z_3 = -0.2", 22, ACCENT)]
        ht = [N("0.1", 28, ACCENT), N("0.6", 28, ACCENT), N("0", 28, ACCENT)]
        for i in range(3):
            zt[i].next_to(hs[i], UP, buff=0.08)
            ht[i].next_to(hs[i], DOWN, buff=0.08)
        self.play(LaggedStart(*[FadeIn(z, shift=LEFT * 0.2) for z in zt], lag_ratio=0.15)); pause(self, 0.3)
        self.play(LaggedStart(*[FadeIn(h, shift=UP * 0.2) for h in ht], lag_ratio=0.15)); pause(self, 0.3)
        vy = N("-0.12", 28, ACCENT).next_to(yh, DOWN, buff=0.08)
        vL = N("0.6272", 28, ACCENT).next_to(L, DOWN, buff=0.08)
        self.play(FadeIn(vy, shift=LEFT * 0.2)); self.play(FadeIn(vL, shift=LEFT * 0.2)); pause(self)

        # —— 反向 ——
        bwd = T("反向：梯度从损失往回流", 24, WARN).to_edge(DOWN, buff=0.4)
        self.play(FadeOut(fwd), FadeIn(bwd))
        gy = M(r"\delta = \hat y - y = -1.12", 24, WARN).next_to(yh, UP, buff=0.12)
        self.play(e3.animate.set_color(WARN), FadeIn(gy, shift=LEFT * 0.3)); pause(self, 0.5)

        # ∂L/∂W2 = δ hᵀ（外积），∂L/∂h = W2ᵀ δ
        gW2 = MathTex(r"\frac{\partial L}{\partial W_2} = \delta\, h^{\mathsf T} = [-0.112,\ -0.672,\ 0]", font_size=26, color=WARN).move_to([3.2, 2.3, 0])
        self.play(Transform(w2, gW2)); pause(self, 0.6)
        gh = [M(r"\partial L/\partial h_1 = -0.896", 22, WARN), M(r"\partial L/\partial h_2 = 0.56", 22, WARN), M(r"\partial L/\partial h_3 = -0.336", 22, WARN)]
        for i in range(3):
            gh[i].next_to(hs[i], UP, buff=0.08)
        ghl = M(r"\partial L/\partial h = W_2^{\mathsf T}\delta", 26, WARN).move_to([0.6, -2.5, 0])
        self.play(e2.animate.set_color(WARN), *[Transform(zt[i], gh[i]) for i in range(3)], FadeIn(ghl)); pause(self, 0.6)

        # 过 ReLU：z3 < 0，梯度截断为 0
        note = T("z₃ < 0，ReLU 的局部导数是 0：传到 h₃ 的梯度在这里截断", 24, WARN).to_edge(DOWN, buff=0.4)
        gz3 = M(r"\partial L/\partial z_3 = 0", 22, WARN).next_to(hs[2], UP, buff=0.08)
        cross = Cross(zt[2], stroke_color=WARN, stroke_width=4, scale_factor=0.7)
        self.play(FadeOut(bwd), FadeIn(note), Create(cross)); pause(self, 0.6)
        self.play(FadeOut(cross), Transform(zt[2], gz3), FadeOut(ghl)); pause(self, 0.4)
        self.play(FadeOut(note), FadeIn(bwd))

        # ∂L/∂W1 = δ1 xᵀ（外积，3×2）
        gW1 = MathTex(r"\frac{\partial L}{\partial W_1} = \delta_1\, x^{\mathsf T} =", r"\begin{bmatrix} -0.896 & -1.792 \\ 0.56 & 1.12 \\ 0 & 0 \end{bmatrix}", font_size=26, color=WARN).move_to([-3.4, 2.4, 0])
        self.play(e1.animate.set_color(WARN), Transform(w1, gW1)); pause(self, 0.8)
        gx = [N("-0.56", 24, WARN).next_to(xs[0], UP, buff=0.08), N("0.4928", 24, WARN).next_to(xs[1], UP, buff=0.08)]
        self.play(*[FadeIn(g, shift=LEFT * 0.3) for g in gx]); pause(self)

        end = T("一次反向，13 个参数的梯度全部到手；每一步只是「上游梯度 × 局部导数」", 24, FG).to_edge(DOWN, buff=0.4)
        self.play(FadeOut(bwd), FadeIn(end))
        self.wait(2)
