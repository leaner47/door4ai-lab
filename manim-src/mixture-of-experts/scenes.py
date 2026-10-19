"""mixture-of-experts 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm mixture-of-experts/scenes.py RouterTopK
颜色约定（整讲一致）：token 向量 C_Q，被选中的专家 / 激活 ACCENT，共享专家 OK，未选中 MUTED，权重 C_K。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np


def vec_column(vals, x, y, cell=0.3, color=C_Q):
    cells = VGroup()
    for a in vals:
        c = Square(cell, stroke_width=1, stroke_color=BG)
        c.set_fill(color if a >= 0 else WARN, opacity=min(1, 0.2 + abs(a) * 0.5))
        cells.add(c)
    return cells.arrange(DOWN, buff=0).move_to([x, y, 0])


def box(label, w=1.3, h=0.55, color=MUTED, size=22):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.1, stroke_color=color, stroke_width=2, fill_color=BG, fill_opacity=1)
    return VGroup(r, T(label, size, FG).move_to(r))


class RouterTopK(Scene):
    """一个 token 进路由器：打分 → softmax → 取 top-2 → 只算这两个专家 → 按权重加起来。"""

    def construct(self):
        title = T("路由器：每个 token 只送给 k 个专家", 36).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        rng = np.random.default_rng(2)
        x = rng.normal(0, 1, 6)
        tok = vec_column(x, -6.0, 0)
        tl = T("token 向量 x", 22, C_Q).next_to(tok, DOWN, buff=0.2)
        self.play(FadeIn(tok), FadeIn(tl)); pause(self, 0.4)

        router = box("路由器", w=1.5, h=0.9, color=C_K, size=26).move_to([-4.0, 0, 0])
        a1 = Arrow(tok.get_right(), router.get_left(), buff=0.1, color=MUTED, stroke_width=3)
        self.play(GrowArrow(a1), FadeIn(router))
        f1 = T("x · W", 22, MUTED).next_to(router, UP, buff=0.15)
        self.play(FadeIn(f1)); pause(self, 0.4)

        # 8 个分数 → softmax 柱
        scores = np.array([0.4, 2.1, -0.6, 0.2, 1.3, -1.0, 0.1, -0.3])
        p = np.exp(scores) / np.exp(scores).sum()
        x0, base = -2.4, -1.1
        bars = VGroup()
        for i, v in enumerate(p):
            b = Rectangle(width=0.32, height=max(0.03, v * 4), stroke_width=0, fill_color=MUTED, fill_opacity=1)
            b.move_to([x0 + i * 0.45, base + b.height / 2, 0])
            bars.add(b)
        nums = VGroup(*[N(f"{i + 1}", 20, MUTED).next_to(bars[i], DOWN, buff=0.12).set_y(base - 0.22) for i in range(8)])
        pl = T("softmax 概率（8 个专家）", 22, FG).move_to([x0 + 1.6, 1.75, 0])
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.08), FadeIn(nums), FadeIn(pl)); pause(self)

        top = [1, 4]
        self.play(*[bars[i].animate.set_fill(ACCENT) for i in top], *[nums[i].animate.set_color(ACCENT) for i in top])
        tk = T("取最大的 2 个", 22, ACCENT).move_to([x0 + 1.6, -1.85, 0])
        self.play(FadeIn(tk)); pause(self, 0.5)
        g = p[top] / p[top].sum()
        gl = VGroup(*[N(f"{g[j]:.2f}", 22, C_K).next_to(bars[i], UP, buff=0.1) for j, i in enumerate(top)])
        gn = T("重新归一化成权重 g", 22, C_K).next_to(tk, DOWN, buff=0.12)
        self.play(FadeIn(gl), FadeIn(gn)); pause(self)

        # 专家列
        ex = VGroup(*[box(f"专家 {i + 1}", w=1.35, h=0.48, size=20) for i in range(8)]).arrange(DOWN, buff=0.12).move_to([2.6, -0.35, 0])
        self.play(LaggedStart(*[FadeIn(e) for e in ex], lag_ratio=0.05))
        arrows = VGroup()
        for j, i in enumerate(top):
            arr = Arrow(gl[j].get_right(), ex[i].get_left(), buff=0.12, color=ACCENT, stroke_width=2 + 5 * g[j])
            arrows.add(arr)
        self.play(*[ex[i][0].animate.set_stroke(ACCENT, 3) for i in top], *[GrowArrow(a) for a in arrows])
        idle = T("其余 6 个：这个 token 一次乘法都不做", 20, MUTED).next_to(ex, DOWN, buff=0.15)
        self.play(*[ex[i].animate.set_opacity(0.35) for i in range(8) if i not in top], FadeIn(idle)); pause(self)

        # 输出加权求和
        o1 = vec_column(rng.normal(0, 1, 6), 4.6, 1.0, cell=0.24, color=ACCENT)
        o2 = vec_column(rng.normal(0, 1, 6), 4.6, -1.0, cell=0.24, color=ACCENT)
        self.play(TransformFromCopy(ex[top[0]], o1), TransformFromCopy(ex[top[1]], o2))
        w1 = N(f"× {g[0]:.2f}", 22, C_K).next_to(o1, RIGHT, buff=0.12)
        w2 = N(f"× {g[1]:.2f}", 22, C_K).next_to(o2, RIGHT, buff=0.12)
        self.play(FadeIn(w1), FadeIn(w2)); pause(self, 0.4)
        y = vec_column(g[0] * rng.normal(0, 1, 6) + g[1] * rng.normal(0, 1, 6), 6.3, 0, cell=0.3, color=ACCENT)
        plus = M("+", 40, FG).move_to([5.75, 0, 0])
        self.play(FadeIn(plus), TransformFromCopy(VGroup(o1, o2), y))
        yl = T("输出", 22, ACCENT).next_to(y, DOWN, buff=0.2)
        self.play(FadeIn(yl))
        eq = M(r"y = \sum_{i \in \text{top-}k} g_i \, E_i(x)", 40, FG).to_edge(DOWN, buff=0.3)
        self.play(FadeOut(idle), Write(eq))
        self.wait(2)


class TotalVsActive(Scene):
    """DeepSeek-V3 的一层：256 个路由专家 + 1 个共享专家，一个 token 只亮 8 + 1 块；batch 一大，亮的是并集。"""

    def construct(self):
        title = T("总参数很多，每个 token 只用一小部分", 36).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.3)

        n, cols, s = 256, 16, 0.3
        grid = VGroup(*[Square(s - 0.05, stroke_width=0, fill_color=LINE, fill_opacity=1) for _ in range(n)])
        grid.arrange_in_grid(rows=16, cols=cols, buff=0.05).move_to([-3.7, -0.35, 0])
        shared = Square(s * 2, stroke_width=0, fill_color=OK, fill_opacity=0.35).next_to(grid, RIGHT, buff=0.35).align_to(grid, DOWN)
        sl = T("共享专家", 20, OK).next_to(shared, UP, buff=0.12)
        gl = T("DeepSeek-V3 一层：256 个路由专家", 22, MUTED).next_to(grid, UP, buff=0.15)
        self.play(LaggedStart(*[FadeIn(c) for c in grid], lag_ratio=0.004, run_time=1.6), FadeIn(gl))
        self.play(FadeIn(shared), FadeIn(sl)); pause(self, 0.4)

        rx = 1.6
        info = VGroup(
            T("每个 token：8 个路由专家 + 1 个共享专家", 22, FG),
            T("总参数 671B，要全部放进显存", 22, MUTED),
            T("激活参数 37B，决定每个 token 的计算量", 22, ACCENT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        info.move_to([rx + 1.6, 1.2, 0]).align_to([rx - 0.9, 0, 0], LEFT)
        rng = np.random.default_rng(5)
        self.play(FadeIn(info[0]))
        for t in range(4):
            pick = rng.choice(n, 8, replace=False)
            self.play(*[grid[i].animate.set_fill(ACCENT, 1) for i in pick], shared.animate.set_fill(OK, 1), run_time=0.35)
            self.wait(0.35)
            self.play(*[grid[i].animate.set_fill(LINE, 1) for i in pick], shared.animate.set_fill(OK, 0.35), run_time=0.25)
        self.play(FadeIn(info[1]), FadeIn(info[2])); pause(self)

        # batch：64 个 token 的并集
        bl = VGroup(T("同时 decode 64 个 token：", 22, FG), T("要读的是它们选中专家的并集", 22, FG)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        bl.align_to(info, LEFT).set_y(-0.5)
        self.play(FadeIn(bl))
        used = set()
        cnt = N("0", 44, ACCENT)
        cnt.align_to(info, LEFT).set_y(-1.6)
        ph = N("256", 44, ACCENT).move_to(cnt, aligned_edge=LEFT)
        cl = T("/ 256 个专家被用到", 22, MUTED).next_to(ph, RIGHT, buff=0.2)
        self.play(FadeIn(cnt), FadeIn(cl))
        for t in range(64):
            pick = rng.choice(n, 8, replace=False)
            new = [i for i in pick if i not in used]
            used.update(pick)
            nc = N(str(len(used)), 44, ACCENT).move_to(ph, aligned_edge=LEFT)
            self.play(*[grid[i].animate.set_fill(ACCENT, 1) for i in new], Transform(cnt, nc), run_time=0.09 if t > 6 else 0.3)
        pause(self)
        end = T("期望值 256 × [1 − (248/256)⁶⁴] ≈ 222", 22, C_K).next_to(ph, DOWN, buff=0.3).align_to(info, LEFT)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2.5)
