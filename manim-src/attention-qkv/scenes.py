"""attention-qkv 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm attention-qkv/scenes.py ScaledDotProduct
颜色约定（整讲一致）：查询 q = C_Q，键 k = C_K，值 v = C_V，份额 / 结果 = WARN。
数字是 Qwen3-0.6B 第 1 层第 11 个头的真实输出（labs-src/attention-qkv/qwen_attn.py 生成）。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np

TOKS = ["我在", "粮油", "店", "买了", "两", "斤", "小米"]
RAW = [258.11, 285.26, 275.93, 280.94, 240.15, 252.87, 276.05]


def softmax(a):
    a = np.array(a); e = np.exp(a - a.max()); return e / e.sum()


class ScaledDotProduct(Scene):
    """「小米」回头看：q·k 打分 → 除以 √d_k → softmax → 按份额加 v。"""

    def construct(self):
        title = T("「小米」怎么从前文拿信息", 34).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.3)

        boxes = VGroup()
        for i, t in enumerate(TOKS):
            r = RoundedRectangle(width=1.35, height=0.62, corner_radius=0.1, stroke_width=2,
                                 stroke_color=WARN if i == 6 else MUTED, fill_color=BG, fill_opacity=1)
            boxes.add(VGroup(r, T(t, 26).move_to(r)))
        boxes.arrange(RIGHT, buff=0.3).move_to(UP * 1.9)
        self.play(LaggedStart(*[FadeIn(b, shift=UP * 0.15) for b in boxes], lag_ratio=0.08)); pause(self, 0.3)

        # —— 查询与键 ——
        q = M(r"q", 40, C_Q).next_to(boxes[6], UP, buff=0.18)
        ks = VGroup(*[M(rf"k_{{{i + 1}}}", 34, C_K).next_to(boxes[i], DOWN, buff=0.25) for i in range(7)])
        self.play(FadeIn(q, shift=DOWN * 0.15))
        self.play(LaggedStart(*[FadeIn(k) for k in ks], lag_ratio=0.06)); pause(self, 0.3)

        f1 = M(r"s_j = q\cdot k_j", 44).move_to(UP * 0.2)
        self.play(Write(f1))
        sc = VGroup(*[N(f"{v:.0f}", 28, C_K).move_to(ks[i]) for i, v in enumerate(RAW)])
        self.play(*[ReplacementTransform(ks[i], sc[i]) for i in range(7)], FadeOut(q)); pause(self, 0.5)

        note = T("128 维的点积，分数有几百", 24, MUTED).next_to(f1, DOWN, buff=0.3)
        self.play(FadeIn(note)); pause(self, 0.6)

        # —— 缩放 ——
        f2 = M(r"\frac{s_j}{\sqrt{d_k}} = \frac{s_j}{\sqrt{128}}", 44).move_to(UP * 0.2)
        scaled = [v / np.sqrt(128) for v in RAW]
        sc2 = VGroup(*[N(f"{v:.1f}", 28, C_K).move_to(sc[i]) for i, v in enumerate(scaled)])
        self.play(TransformMatchingTex(f1, f2), FadeOut(note))
        self.play(*[Transform(sc[i], sc2[i]) for i in range(7)]); pause(self, 0.5)

        # —— softmax ——
        w = softmax(scaled)
        f3 = M(r"w_j = \frac{e^{s_j/\sqrt{d_k}}}{\sum_i e^{s_i/\sqrt{d_k}}}", 42).move_to(UP * 0.25)
        self.play(TransformMatchingShapes(f2, f3))
        base_y = -3.0
        bars = VGroup(); labs = VGroup()
        for i, p in enumerate(w):
            h = max(0.04, 3.4 * p)
            b = Rectangle(width=0.9, height=h, stroke_width=0, fill_color=WARN, fill_opacity=0.95 if i == 1 else 0.55)
            b.move_to([boxes[i].get_center()[0], base_y + h / 2, 0])
            bars.add(b)
            labs.add(N(f"{round(p * 100)}%", 26, FG).next_to(b, UP, buff=0.08))
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.06), run_time=1.2)
        self.play(FadeIn(labs)); pause(self, 0.4)
        tip = T("份额加起来 = 100%，最大的一份给了「粮油」", 24, WARN).to_edge(DOWN, buff=0.2)
        self.play(FadeIn(tip)); pause(self, 1.0)

        # —— 加权求和 v ——
        self.play(FadeOut(VGroup(bars, labs, tip, sc, f3)))
        f4 = M(r"x' = x + \sum_j w_j\, v_j", 44).move_to(UP * 0.4 + LEFT * 3.2)
        self.play(Write(f4)); pause(self, 0.4)
        origin = np.array([-0.5, -3.4, 0])
        x_vec = Arrow(origin, origin + np.array([2.0, 2.0, 0]), buff=0, color=MUTED, stroke_width=5)
        xl = M("x", 34, MUTED).next_to(x_vec.get_end(), RIGHT, buff=0.1)
        self.play(GrowArrow(x_vec), FadeIn(xl))
        vs = [np.array([-0.1, 0.9, 0]), np.array([0.08, 0.1, 0]), np.array([0.02, -0.04, 0]), np.array([-0.05, 0.25, 0])]
        ws = [w[1], w[2], w[3], w[5]]
        cur = x_vec.get_end(); arrs = VGroup()
        for v, p in zip(vs, ws):
            d = v * p * 4.0
            if np.linalg.norm(d) < 0.03:
                continue
            a = Arrow(cur, cur + d, buff=0, color=C_V, stroke_width=4, max_tip_length_to_length_ratio=0.35)
            arrs.add(a); cur = cur + d
        self.play(LaggedStart(*[GrowArrow(a) for a in arrs], lag_ratio=0.3))
        xp = Arrow(origin, cur, buff=0, color=WARN, stroke_width=6)
        xpl = M("x'", 36, WARN).next_to(xp.get_end(), UP, buff=0.1)
        self.play(GrowArrow(xp), FadeIn(xpl)); pause(self, 0.4)
        fin = T("「小米」带上了「粮油店」的信息", 26, WARN).next_to(f4, DOWN, buff=0.5)
        self.play(FadeIn(fin)); pause(self, 1.2)

        # —— 合成一行 ——
        self.play(FadeOut(VGroup(x_vec, xl, arrs, xp, xpl, fin, boxes, f4)))
        eq = M(r"\operatorname{Attention}(Q,K,V)=\operatorname{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V", 46)
        self.play(Write(eq), run_time=1.6); pause(self, 1.5)
