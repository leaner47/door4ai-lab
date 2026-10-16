"""__slug__ 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm __slug__/scenes.py Intro
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *


class Intro(Scene):
    """一段只讲一件事。15–60 s。"""

    def construct(self):
        title = T("__这一段讲什么__", 36).to_edge(UP)
        self.play(Write(title)); pause(self)

        # 主角用 ACCENT；同一概念整讲同一种颜色（C_Q / C_K / C_V / WARN / OK）
        a = Arrow(ORIGIN, [2.5, 0.6, 0], buff=0, color=C_Q)
        b = Arrow(ORIGIN, [1.6, 1.8, 0], buff=0, color=C_K)
        self.play(GrowArrow(a)); pause(self, 0.4)
        self.play(GrowArrow(b)); pause(self)

        # 「这个变成那个」用 Transform，而不是删掉重画
        eq1 = M(r"q \cdot k").to_edge(DOWN)
        eq2 = M(r"q \cdot k = \lVert q \rVert \, \lVert k \rVert \cos\theta").to_edge(DOWN)
        self.play(Write(eq1)); pause(self)
        self.play(TransformMatchingTex(eq1, eq2)); pause(self)

        val = N("0.82", 48, ACCENT).next_to(a, RIGHT)
        self.play(FadeIn(val, shift=UP))
        self.wait(1.5)
