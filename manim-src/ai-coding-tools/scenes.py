"""ai-coding-tools 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm ai-coding-tools/scenes.py AgentEditLoop
颜色约定（整讲一致）：读 C_Q 蓝，改 C_K 黄，跑 C_V 青，看结果 FG；新增行 OK，删除行 / 报错 WARN。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *

MONO = next((f for f in ["Menlo", "DejaVu Sans Mono", "Liberation Mono"] if f in manimpango.list_fonts()), "monospace")


def C(s, size=20, color=FG):
    """等宽代码 / 终端文字。"""
    return Text(s, font=MONO, font_size=size, color=color)


def panel(w, h, title, x, y, fill=BG):
    box = RoundedRectangle(width=w, height=h, corner_radius=0.15, stroke_color=LINE, stroke_width=2, fill_color=fill, fill_opacity=1).move_to([x, y, 0])
    t = T(title, 20, MUTED).next_to(box, UP, buff=0.12).align_to(box, LEFT)
    return VGroup(box, t)


class AgentEditLoop(Scene):
    """读 → 改 → 跑 → 看结果 → 再改：AI 编程工具的工作循环。"""

    def construct(self):
        title = T("AI 改代码：一个循环", 36).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        # —— 左：文件树 ——
        tree_p = panel(3.0, 3.0, "项目文件夹", -5.25, 0.9)
        names = ["index.html", "style.css", "app.js", "tests/"]
        rows = VGroup(*[C(n, 20) for n in names]).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
        rows.move_to(tree_p[0]).align_to(tree_p[0], LEFT).shift(RIGHT * 0.35)
        self.play(FadeIn(tree_p), LaggedStart(*[FadeIn(r) for r in rows], lag_ratio=0.12)); pause(self, 0.7)

        # —— 中：循环 ——
        cx, cy, R = -0.6, 0.55, 1.75
        stages = [("读文件", C_Q, 90), ("改文件", C_K, 0), ("跑命令", C_V, -90), ("看结果", FG, 180)]
        nodes = VGroup()
        for name, col, ang in stages:
            p = np.array([cx + R * np.cos(np.radians(ang)), cy + R * np.sin(np.radians(ang)), 0])
            box = RoundedRectangle(width=1.55, height=0.68, corner_radius=0.2, stroke_color=col, stroke_width=3, fill_color=BG, fill_opacity=1).move_to(p)
            nodes.add(VGroup(box, T(name, 24, col).move_to(p)))
        arcs = VGroup()
        for i in range(4):
            a0, a1 = stages[i][2], stages[(i + 1) % 4][2]
            if a1 > a0: a1 -= 360
            arc = Arc(radius=R, start_angle=np.radians(a0 - 22), angle=np.radians((a1 + 22) - (a0 - 22)), arc_center=[cx, cy, 0], color=MUTED, stroke_width=3)
            arc.add_tip(tip_length=0.18)
            arcs.add(arc)
        core = T("模型", 26, FG).move_to([cx, cy, 0])
        self.play(FadeIn(core), LaggedStart(*[FadeIn(n) for n in nodes], lag_ratio=0.15), run_time=1.2)
        self.play(LaggedStart(*[Create(a) for a in arcs], lag_ratio=0.2), run_time=1.2); pause(self, 0.7)

        # —— 右：改动 / 终端 ——
        diff_p = panel(4.5, 1.75, "diff", 4.55, 1.85)
        term_p = panel(4.5, 2.25, "终端", 4.55, -1.0, fill="#0d1117")
        self.play(FadeIn(diff_p), FadeIn(term_p)); pause(self, 0.2)

        hl = SurroundingRectangle(rows[2], color=C_Q, buff=0.08, corner_radius=0.06)

        def focus(i, rt=0.5):
            return Indicate(nodes[i], color=stages[i][1], scale_factor=1.12, run_time=rt)

        # 1 读
        self.play(focus(0), Create(hl)); pause(self, 0.7)
        # 2 改：一行红一行绿
        d1 = VGroup(C('+ <button id="theme-toggle">', 15, OK), C("+ getElementById('theme-btn')", 15, OK)).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        d1.move_to(diff_p[0]).align_to(diff_p[0], LEFT).shift(RIGHT * 0.2)
        self.play(focus(1), hl.animate.set_color(C_K), FadeIn(d1, shift=RIGHT * 0.2)); pause(self, 0.7)
        # 3 跑
        tl = VGroup(C("$ npm test", 18, FG), C("✗ TypeError: btn is null", 18, WARN), C("  at app.js:4", 18, WARN)).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        tl.move_to(term_p[0]).align_to(term_p[0], LEFT).shift(RIGHT * 0.2)
        self.play(focus(2), FadeIn(tl[0]))
        self.play(FadeIn(tl[1:], shift=UP * 0.1)); pause(self, 0.7)
        # 4 看结果
        why = T("id 写错了：应该是 theme-toggle", 22, FG).next_to(nodes, DOWN, buff=0.45)
        self.play(focus(3), FadeIn(why, shift=UP * 0.15)); pause(self, 1.2)

        # 再转一圈
        again = T("再改", 22, C_K).next_to(nodes[1], DOWN, buff=0.12)
        d2 = VGroup(C("- getElementById('theme-btn')", 15, WARN), C("+ getElementById('theme-toggle')", 15, OK)).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        d2.move_to(d1).align_to(d1, LEFT)
        self.play(focus(1), FadeIn(again), Transform(d1, d2)); pause(self, 0.7)
        t2 = VGroup(C("$ npm test", 18, FG), C("✓ 2 passed", 18, OK)).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        t2.move_to(tl).align_to(tl, LEFT).align_to(tl, UP)
        self.play(focus(2), FadeOut(tl), FadeIn(t2)); pause(self, 0.7)
        ok = T("测试通过：停下来，交给你看 diff", 22, OK).move_to(why)
        self.play(focus(3), FadeOut(again), Transform(why, ok)); pause(self, 1.2)

        end = T("模型 + 读 / 改 / 跑 的工具 + 循环 = Agent", 26, FG).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2)
