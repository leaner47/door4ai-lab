"""trace-eval 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm trace-eval/scenes.py TraceTree
颜色约定（整讲一致，与实验页相同）：任务 / 轮次 MUTED，模型调用 ACCENT，工具调用 C_K（黄），出错 WARN，检查 / 通过 OK。
TraceTree 的数据与实验页 00 的示例 trace 完全一致（并行排布，单位 ms）。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *

# (id, 父 id, 树里显示的名字, 类型, 开始 ms, 结束 ms)
SPANS = [
    ("root", None, "invoke_agent", "agent", 0, 9270),
    ("t1", "root", "第 1 轮", "turn", 0, 3400),
    ("c1", "t1", "chat", "chat", 20, 1670),
    ("x1", "t1", "get_weather 北京", "tool", 1690, 2380),
    ("x2", "t1", "get_weather 上海", "err", 1690, 2690),
    ("x3", "t1", "get_weather 上海 重试", "tool", 2700, 3390),
    ("t2", "root", "第 2 轮", "turn", 3400, 5830),
    ("c2", "t2", "chat", "chat", 3420, 5010),
    ("a1", "t2", "air_quality 北京", "tool", 5030, 5440),
    ("a2", "t2", "air_quality 上海", "tool", 5030, 5820),
    ("t3", "root", "第 3 轮", "turn", 5830, 9170),
    ("c3", "t3", "chat", "chat", 5850, 9160),
    ("g1", "root", "output_check", "guard", 9170, 9240),
]
COL = {"agent": MUTED, "turn": MUTED, "chat": ACCENT, "tool": C_K, "err": WARN, "guard": OK}
DEPTH = {"root": 0}
for sid, par, *_ in SPANS:
    if par:
        DEPTH[sid] = DEPTH[par] + 1


class TraceTree(Scene):
    """一次运行逐步长成 span 树，右边甘特图同时展开。"""

    def construct(self):
        title = T("一次 Agent 运行 = 一棵 span 树", 34).to_edge(UP, buff=0.3)
        self.play(Write(title)); pause(self, 0.4)

        T_END = 9270
        gx0, gx1 = -1.2, 6.6                    # 甘特图横向范围
        top, rh = 2.55, 0.37                    # 第一行 y 与行高
        X = lambda ms: gx0 + ms / T_END * (gx1 - gx0)

        axis = Line([gx0, top + 0.32, 0], [gx1, top + 0.32, 0], color=LINE, stroke_width=2)
        ticks = VGroup(*[N(f"{s} s", 18, MUTED).move_to([X(s * 1000), top + 0.52, 0]) for s in range(0, 10, 2)])
        self.play(Create(axis), FadeIn(ticks), run_time=0.6)

        rows = {}
        def row(i, sid, name, kind, s, e):
            y = top - i * rh
            d = DEPTH[sid]
            dot = Square(0.13, stroke_width=0, fill_color=COL[kind], fill_opacity=1)
            lab = T(name, 19, FG if kind not in ("agent", "turn") else MUTED)
            VGroup(dot, lab).arrange(RIGHT, buff=0.12)
            grp = VGroup(dot, lab)
            grp.move_to([-6.6 + d * 0.32, y, 0], aligned_edge=LEFT)
            bar = Rectangle(width=max(0.03, X(e) - X(s)), height=0.22, stroke_width=0,
                            fill_color=COL[kind], fill_opacity=0.5 if kind in ("agent", "turn") else 1)
            bar.move_to([X(s), y, 0], aligned_edge=LEFT)
            rows[sid] = (grp, bar)
            return grp, bar

        # 按时间顺序「长出来」：每个 span 出现时，树里加一行，甘特条从左往右伸到它的结束时刻
        order = [("root",), ("t1",), ("c1",), ("x1", "x2"), ("x3",), ("t2",), ("c2",), ("a1", "a2"), ("t3",), ("c3",), ("g1",)]
        idx = {sid: i for i, (sid, *_) in enumerate(SPANS)}
        info = {sid: (name, kind, s, e) for sid, _, name, kind, s, e in SPANS}
        for k, group in enumerate(order):
            anims = []
            for sid in group:
                name, kind, s, e = info[sid]
                g, b = row(idx[sid], sid, name, kind, s, e)
                anims += [FadeIn(g, shift=RIGHT * 0.2), GrowFromEdge(b, LEFT)]
            rt = 0.5 if info[group[0]][1] in ("agent", "turn") else min(1.4, 0.35 + (info[group[0]][3] - info[group[0]][2]) / 3000)
            self.play(*anims, run_time=rt)
            if group == ("x1", "x2"):
                tag = T("超时 1000 ms", 18, WARN).next_to(rows["x2"][1], RIGHT, buff=0.12)
                self.play(FadeIn(tag), run_time=0.4)
        pause(self)

        # 只看最终回答看不到的东西：出错与重试
        box = SurroundingRectangle(VGroup(rows["x2"][1], rows["x3"][1]), color=WARN, buff=0.06)
        self.play(Create(box))
        note1 = T("最终回答是对的，但中途超时重试了一次：整轮慢了 1 s", 22, WARN).to_edge(DOWN, buff=0.75)
        self.play(FadeIn(note1, shift=UP * 0.2)); pause(self, 1.2)

        # 最慢、最贵的是最后一轮 chat
        box2 = SurroundingRectangle(rows["c3"][1], color=ACCENT, buff=0.06)
        note2 = T("最慢也最贵：第 3 轮 chat，3.31 s，236 个输出 token", 22, ACCENT).to_edge(DOWN, buff=0.75)
        self.play(ReplacementTransform(box, box2), FadeOut(note1), FadeIn(note2)); pause(self, 1.2)

        summary = T("模型调用占墙钟时间 71%，工具 27%，总计 9.27 s", 22, FG).to_edge(DOWN, buff=0.25)
        self.play(FadeIn(summary, shift=UP * 0.2))
        self.wait(2)


# 回归测试：30 题，与实验页 04「改 prompt」完全一致
V1 = "11111000" "111101" "111110" "11011" "10010"
V2 = "11101100" "111110" "001010" "11011" "11111"
CATS = [("天气查询", 0, 8), ("单位换算", 8, 14), ("多步比较", 14, 20), ("拒答与安全", 20, 25), ("输出格式", 25, 30)]


class RegressionGrid(Scene):
    """两版在同一套 eval 集上的逐题结果：总分相同，逐题却变了 10 道。"""

    def construct(self):
        title = T("改了 prompt：总分没变，就是没变吗", 34).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        n, cw, ch = 30, 0.34, 0.46
        x0 = -n * cw / 2 + cw / 2 - 0.75
        y1, y2 = 1.5, 0.55

        def cells(bits, y, fade=False):
            g = VGroup()
            for i, b in enumerate(bits):
                c = RoundedRectangle(width=cw - 0.06, height=ch, corner_radius=0.05, stroke_width=0,
                                     fill_color=OK if b == "1" else WARN, fill_opacity=1)
                c.move_to([x0 + i * cw, y, 0]); g.add(c)
            return g

        l1 = N("v1", 26, MUTED).move_to([x0 - 0.65, y1, 0])
        l2 = N("v2", 26, MUTED).move_to([x0 - 0.65, y2, 0])
        g1 = cells(V1, y1)
        self.play(FadeIn(l1), LaggedStart(*[FadeIn(c, scale=0.6) for c in g1], lag_ratio=0.03), run_time=1.4)
        cats = VGroup()
        for name, a, b in CATS:
            ln = Line([x0 + a * cw - cw / 2 + 0.04, y2 - 0.45, 0], [x0 + (b - 1) * cw + cw / 2 - 0.04, y2 - 0.45, 0], color=MUTED, stroke_width=2)
            cats.add(VGroup(ln, T(name, 17, MUTED).next_to(ln, DOWN, buff=0.08)))
        self.play(FadeIn(cats), run_time=0.6)

        s1 = N("21 / 30", 30, FG).move_to([5.5, y1, 0])
        self.play(FadeIn(s1)); pause(self, 0.4)

        # v2 先整排复制 v1，再逐格变成新结果
        g2 = g1.copy()
        self.play(FadeIn(l2), g2.animate.shift(DOWN * (y1 - y2)), run_time=0.8)
        flips = [i for i in range(n) if V1[i] != V2[i]]
        self.play(*[g2[i].animate.set_fill(OK if V2[i] == "1" else WARN) for i in flips], run_time=1.0)
        s2 = N("21 / 30", 30, FG).move_to([5.5, y2, 0])
        self.play(FadeIn(s2)); pause(self)
        same = T("总分一样", 24, FG).next_to(VGroup(s1, s2), DOWN, buff=0.15)
        self.play(FadeIn(same)); pause(self, 0.6)

        # 标出变了的题：↓ 过→挂，↑ 挂→过
        marks = VGroup()
        for i in flips:
            up = V2[i] == "1"
            marks.add(SurroundingRectangle(g2[i], color=OK if up else WARN, buff=0.05, stroke_width=4))
        self.play(LaggedStart(*[Create(m) for m in marks], lag_ratio=0.08), run_time=1.4)
        pause(self)

        # 四格计数
        pp = sum(1 for i in range(n) if V1[i] == "1" and V2[i] == "1")
        pf = sum(1 for i in range(n) if V1[i] == "1" and V2[i] == "0")
        fp = sum(1 for i in range(n) if V1[i] == "0" and V2[i] == "1")
        ff = n - pp - pf - fp
        def cell(txt, num, col):
            r = RoundedRectangle(width=2.7, height=0.95, corner_radius=0.1, stroke_color=col, stroke_width=2, fill_color=BG, fill_opacity=1)
            t = VGroup(T(txt, 20, col), N(str(num), 34, col)).arrange(RIGHT, buff=0.25).move_to(r)
            return VGroup(r, t)
        grid = VGroup(cell("都过", pp, MUTED), cell("过 → 挂", pf, WARN), cell("挂 → 过", fp, OK), cell("都挂", ff, MUTED)).arrange_in_grid(2, 2, buff=0.18)
        grid.move_to([-2.4, -2.1, 0])
        self.play(FadeIn(grid, shift=UP * 0.2)); pause(self)

        msg = VGroup(
            T("多步比较退化 3 道，输出格式修好 3 道", 22, FG),
            T("看逐题差异，而不是只看总分", 24, ACCENT),
        ).arrange(DOWN, buff=0.25, aligned_edge=LEFT).next_to(grid, RIGHT, buff=0.6)
        self.play(Indicate(grid[1], color=WARN, scale_factor=1.06), FadeIn(msg[0]))
        pause(self, 0.6)
        self.play(FadeIn(msg[1], shift=UP * 0.15))
        self.wait(2)
