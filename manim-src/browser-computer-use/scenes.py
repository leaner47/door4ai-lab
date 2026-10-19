"""browser-computer-use 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm browser-computer-use/scenes.py ScreenshotClickLoop
颜色约定：模型 ACCENT，harness / 程序 C_K（黄），屏幕与执行结果 OK，点歪 / 警告 WARN。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import manimpango

_f = set(manimpango.list_fonts())
MONO = next((f for f in ["Menlo", "DejaVu Sans Mono", "Noto Sans Mono", "Liberation Mono"] if f in _f), "monospace")


def C(s, size=20, color=FG):
    return Text(s, font=MONO, font_size=size, color=color)


def mock_screen(w=5.2, h=3.25):
    """一块简化的网页：顶栏 + 搜索框 + 两行商品卡片，每张卡片右边一个按钮。"""
    frame = RoundedRectangle(width=w, height=h, corner_radius=0.08, stroke_color=MUTED, stroke_width=2, fill_color="#f7f7f7", fill_opacity=1)
    bar = Rectangle(width=w, height=0.38, stroke_width=0, fill_color="#1f2a44", fill_opacity=1).align_to(frame, UP)
    box = Rectangle(width=1.4, height=0.2, stroke_width=0, fill_color=WHITE, fill_opacity=1).move_to(bar).shift(RIGHT * 1.35)
    go = Rectangle(width=0.32, height=0.2, stroke_width=0, fill_color="#f2b84b", fill_opacity=1).next_to(box, RIGHT, buff=0.06)
    cards, btns = VGroup(), VGroup()
    for r in range(2):
        for c in range(3):
            card = RoundedRectangle(width=1.5, height=0.85, corner_radius=0.05, stroke_color="#cccccc", stroke_width=1, fill_color=WHITE, fill_opacity=1)
            card.move_to(frame.get_corner(UL) + RIGHT * (0.95 + c * 1.65) + DOWN * (1.0 + r * 1.05))
            b = Rectangle(width=0.42, height=0.22, stroke_width=0, fill_color="#1f5fd1", fill_opacity=1).move_to(card).shift(RIGHT * 0.45)
            cards.add(card); btns.add(b)
    return VGroup(frame, bar, box, go, cards, btns), btns


class ScreenshotClickLoop(Scene):
    """截图 → 模型输出坐标 → 程序换算并点击 → 页面变化 → 再截图。"""

    def construct(self):
        title = T("看着截图点一下，就是一圈 Agent 循环", 34).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        screen, btns = mock_screen()
        screen.move_to(LEFT * 3.6 + DOWN * 0.4)
        slab = T("屏幕（逻辑 1280 × 800）", 20, MUTED).next_to(screen, DOWN, buff=0.15)
        model = VGroup(Circle(radius=0.75, color=ACCENT, fill_color=ACCENT, fill_opacity=0.18, stroke_width=3), T("模型", 28, FG)).move_to(RIGHT * 4.4 + DOWN * 0.4)
        self.play(FadeIn(screen), FadeIn(slab), FadeIn(model)); pause(self, 0.3)

        # 1. 截图：闪一下，缩小成一张小图飞向模型
        step = T("① 程序截图，缩小到 1024 × 640", 24, C_K).move_to(UP * 2.15)
        flash = screen[0].copy().set_fill(WHITE, opacity=0.6).set_stroke(width=0)
        self.play(FadeIn(step), FadeIn(flash, run_time=0.15)); self.play(FadeOut(flash, run_time=0.3))
        shot = screen.copy()
        self.play(shot.animate.scale(0.32).move_to(model.get_left() + LEFT * 1.2), run_time=1.0)
        tok = T("约 851 个视觉 token", 18, MUTED).next_to(shot, DOWN, buff=0.12)
        self.play(FadeIn(tok)); pause(self, 0.4)
        self.play(FadeOut(shot), FadeOut(tok), Indicate(model[0], color=ACCENT)); pause(self, 0.3)

        # 2. 模型输出坐标（截图里的坐标）
        step2 = T("② 模型：在截图上点 (937, 156)", 24, ACCENT).move_to(step)
        out = C("left_click [937, 156]", 22, ACCENT).next_to(model, DOWN, buff=0.3)
        self.play(Transform(step, step2), FadeIn(out, shift=UP * 0.1)); pause(self, 0.5)

        # 3. 程序换算
        step3 = T("③ 程序换算回屏幕坐标", 24, C_K).move_to(step)
        conv = M(r"(937,\,156)\times\frac{1280}{1024}=(1171,\,195)", 30, C_K).move_to(RIGHT * 0.9 + DOWN * 2.6)
        self.play(Transform(step, step3), out.animate.move_to(conv.get_center() + UP * 0.7))
        self.play(Write(conv)); pause(self, 0.6)

        # 4. 点击：落在第三张卡片的按钮上
        target = btns[2]
        ring = Circle(radius=0.16, color=OK, stroke_width=4).move_to(target)
        step4 = T("④ 程序在屏幕上真的点下去", 24, OK).move_to(step)
        self.play(Transform(step, step4), FadeOut(out))
        self.play(Create(ring), target.animate.set_fill(OK), run_time=0.6)
        badge = T("已加入购物车", 16, OK).next_to(target, DOWN, buff=0.08)
        self.play(FadeIn(badge)); pause(self, 0.5)

        # 5. 再截图：下一圈
        step5 = T("⑤ 页面变了，再截一张图，进入下一圈", 24, C_K).move_to(step)
        arc = CurvedArrow(screen.get_top() + UP * 0.1 + RIGHT * 1.6, model.get_top() + UP * 0.1, angle=-PI / 3, color=C_K)
        self.play(Transform(step, step5), Create(arc)); pause(self, 0.8)

        # 不换算会怎样
        self.play(FadeOut(arc), FadeOut(ring), FadeOut(badge), target.animate.set_fill("#1f5fd1"))
        warn = T("如果程序忘了换算：直接点 (937, 156)", 24, WARN).move_to(step)
        wrong_pt = screen[0].get_corner(UL) + RIGHT * (937 / 1280 * screen[0].width) + DOWN * (156 / 800 * screen[0].height)
        cross = VGroup(Line(LEFT * 0.14, RIGHT * 0.14, color=WARN, stroke_width=5), Line(UP * 0.14, DOWN * 0.14, color=WARN, stroke_width=5)).move_to(wrong_pt)
        self.play(Transform(step, warn), FadeOut(conv))
        self.play(FadeIn(cross, scale=1.5))
        miss = T("点在卡片空白处，什么也没发生", 22, WARN).next_to(slab, DOWN, buff=0.25)
        self.play(FadeIn(miss)); pause(self, 1.0)

        self.play(FadeOut(cross), FadeOut(miss))
        sum_ = T("模型只写下坐标；截图、换算、点击，全是程序做的", 26, FG).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(sum_, shift=UP * 0.1)); pause(self, 2.0)
