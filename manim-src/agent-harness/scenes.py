"""agent-harness 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm agent-harness/scenes.py HarnessLayers
颜色约定（整讲一致）：模型 ACCENT，harness 部件 C_K（黄），环境 / 工具结果 OK，警告 WARN。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import manimpango

_f = set(manimpango.list_fonts())
MONO = next((f for f in ["Menlo", "DejaVu Sans Mono", "Noto Sans Mono", "Liberation Mono"] if f in _f), "monospace")


def C(s, size=22, color=FG):
    return Text(s, font=MONO, font_size=size, color=color)


def chip(label, color, size=24, w=None):
    t = T(label, size, FG)
    r = RoundedRectangle(width=(w or t.width + 0.4), height=t.height + 0.3, corner_radius=0.1,
                         stroke_color=color, stroke_width=2, fill_color=color, fill_opacity=0.16).move_to(t)
    return VGroup(r, t)


class HarnessLayers(Scene):
    """模型在中间，harness 一圈部件包着它，最外面是环境。一次工具调用从里往外走，再把结果带回来。"""

    def construct(self):
        title = T("Agent = 模型 + Harness", 38).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        model = VGroup(Circle(radius=0.85, color=ACCENT, fill_color=ACCENT, fill_opacity=0.18, stroke_width=3),
                       T("模型", 32, FG)).move_to(LEFT * 3.2 + DOWN * 0.3)
        cap = T("只会：读一段文字，写一段文字", 22, MUTED).next_to(model, DOWN, buff=0.3)
        self.play(FadeIn(model), FadeIn(cap)); pause(self)

        # harness 一圈部件
        frame = RoundedRectangle(width=6.6, height=5.0, corner_radius=0.3, stroke_color=C_K, stroke_width=2.5).move_to(model)
        hlabel = T("Harness（一段程序）", 24, C_K).next_to(frame, UP, buff=0.08).align_to(frame, LEFT).shift(RIGHT * 0.2)
        names = ["循环", "工具执行", "上下文管理", "权限", "状态与记忆"]
        pos = [UP * 1.85, RIGHT * 2.35 + UP * 0.55, RIGHT * 2.35 + DOWN * 1.15, DOWN * 2.0, LEFT * 2.2 + UP * 0.9]
        parts = VGroup(*[chip(n, C_K, 22).move_to(model.get_center() + p) for n, p in zip(names, pos)])
        self.play(FadeOut(cap), Create(frame), FadeIn(hlabel))
        self.play(LaggedStart(*[FadeIn(p, scale=0.9) for p in parts], lag_ratio=0.15)); pause(self)

        # 环境
        env = VGroup(*[chip(n, OK, 22, w=1.7) for n in ["文件", "终端", "网页"]]).arrange(DOWN, buff=0.45).move_to(RIGHT * 5.4 + DOWN * 0.3)
        elabel = T("环境", 24, OK).next_to(env, UP, buff=0.25)
        self.play(FadeIn(env, shift=LEFT * 0.2), FadeIn(elabel)); pause(self)

        # 一次工具调用
        req = C('tool_use: grep("8080")', 20, ACCENT).next_to(model, DOWN, buff=0.12)
        self.play(FadeIn(req, shift=UP * 0.1)); pause(self, 0.4)
        perm, exe, ctx = parts[3], parts[1], parts[2]
        self.play(req.animate.scale(0.8).next_to(perm, RIGHT, buff=0.15), run_time=0.8)
        ok = T("放行", 20, OK).next_to(perm, LEFT, buff=0.15)
        self.play(Indicate(perm, color=C_K), FadeIn(ok)); pause(self, 0.3)
        self.play(FadeOut(ok), req.animate.next_to(exe, LEFT, buff=0.1), run_time=0.8)
        self.play(Indicate(exe, color=C_K))
        self.play(req.animate.next_to(env[1], LEFT, buff=0.1), run_time=0.8)
        self.play(Indicate(env[1], color=OK))
        res = C("tool_result: 78 行，3,439 token", 18, OK).next_to(env[1], DOWN, buff=0.25).shift(LEFT * 1.6)
        self.play(FadeOut(req), FadeIn(res, shift=LEFT * 0.2)); pause(self, 0.4)
        self.play(res.animate.next_to(ctx, DOWN, buff=0.12), run_time=0.9)
        self.play(Indicate(ctx, color=C_K))
        small = C("tool_result: 只留相关的几行", 18, OK).move_to(res)
        self.play(Transform(res, small)); pause(self, 0.4)
        self.play(res.animate.scale(0.9).next_to(model, DOWN, buff=0.15), run_time=0.9)
        loop = parts[0]
        again = T("再调一次模型", 20, C_K).next_to(loop, RIGHT, buff=0.15)
        self.play(Indicate(loop, color=C_K), FadeIn(again), Indicate(model[0], color=ACCENT)); pause(self)

        self.play(FadeOut(res), FadeOut(again))
        sum_ = T("模型做决定；harness 把决定变成动作，并管住边界", 26, FG).to_edge(DOWN, buff=0.35)
        self.play(Write(sum_)); pause(self, 2.0)


class ModelInsideHarness(Scene):
    """上下文快满时，harness 暂停主循环，另开一次模型调用写摘要，再用摘要替换掉旧历史。"""

    def construct(self):
        title = T("Harness 是程序，但有时会再调一次模型", 34).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        L, R, Y, H = -6.0, 6.0, 0.9, 0.7
        bar = Rectangle(width=R - L, height=H, stroke_color=MUTED, stroke_width=1.5).move_to([(L + R) / 2, Y, 0])
        limit_x = L + (R - L) * 0.85
        thr_x = L + (R - L) * 0.6
        lim = DashedLine([limit_x, Y + 0.6, 0], [limit_x, Y - 0.6, 0], color=WARN)
        thr = DashedLine([thr_x, Y + 0.6, 0], [thr_x, Y - 0.6, 0], color=C_K)
        lab = VGroup(T("窗口上限", 18, WARN).next_to(lim, UP, buff=0.05), T("压缩阈值 60%", 18, C_K).next_to(thr, UP, buff=0.05))
        wlab = T("上下文窗口", 22, MUTED).next_to(bar, LEFT, buff=0.15).shift(UP * 0.7).align_to(bar, LEFT)
        self.play(Create(bar), FadeIn(wlab), Create(lim), Create(thr), FadeIn(lab)); pause(self, 0.4)

        # 依次填入的块
        spec = [("系统提示", MUTED, 1.0), ("工具", MUTED, 0.8), ("第 1–10 轮", ACCENT, 1.5), ("工具结果", OK, 1.6), ("第 11–20 轮", ACCENT, 1.5), ("工具结果", OK, 1.4), ("21 轮", ACCENT, 0.9)]
        blocks = VGroup()
        x = L
        for name, col, w in spec:
            r = Rectangle(width=w, height=H, stroke_width=0, fill_color=col, fill_opacity=0.55).move_to([x + w / 2, Y, 0])
            t = T(name, 15, FG).move_to(r)
            if t.width > w - 0.08: t.scale_to_fit_width(w - 0.12)
            blocks.add(VGroup(r, t)); x += w
        loop_lab = T("主循环在跑：每转一圈追加一段", 22, ACCENT).move_to([0, -0.6, 0])
        self.play(FadeIn(loop_lab))
        for b in blocks:
            self.play(FadeIn(b, shift=RIGHT * 0.2), run_time=0.45)
        pause(self, 0.3)

        # 程序判断：超过阈值
        code = C("if tokens > 0.6 * limit:  compact()", 22, C_K).move_to([0, -0.6, 0])
        self.play(Transform(loop_lab, code)); pause(self)
        paused = T("主循环暂停", 22, WARN).move_to([0, -1.25, 0])
        self.play(FadeIn(paused)); pause(self, 0.4)

        # 另开一次模型调用
        sub = VGroup(Circle(radius=0.55, color=ACCENT, fill_color=ACCENT, fill_opacity=0.18, stroke_width=3), T("模型", 22, FG)).move_to([-2.0, -2.5, 0])
        sublab = T("再调一次：把旧历史写成摘要", 22, FG).next_to(sub, RIGHT, buff=0.3)
        self.play(FadeIn(sub), FadeIn(sublab))
        old = VGroup(*blocks[2:6])
        self.play(Indicate(old, color=C_K, scale_factor=1.03))
        copies = old.copy()
        self.play(copies.animate.scale(0.3).move_to(sub), run_time=1.0)
        self.play(FadeOut(copies))
        summ = VGroup(Rectangle(width=1.3, height=H, stroke_width=0, fill_color=C_K, fill_opacity=0.55), T("摘要", 15, FG))
        summ[1].move_to(summ[0])
        summ.next_to(sub, UP, buff=0.2)
        self.play(FadeIn(summ, shift=UP * 0.1)); pause(self, 0.3)

        # 用摘要替换旧历史
        start = blocks[1][0].get_right()[0]
        self.play(FadeOut(old), summ.animate.move_to([start + 0.65, Y, 0]), run_time=1.0)
        last = blocks[6]
        self.play(last.animate.move_to([start + 1.3 + last[0].width / 2, Y, 0]))
        pause(self, 0.3)
        self.play(FadeOut(sub), FadeOut(sublab), FadeOut(paused),
                  Transform(loop_lab, T("主循环继续", 22, ACCENT).move_to([0, -0.6, 0])))
        pause(self, 0.4)

        sum_ = VGroup(T("什么时候压缩：程序按规则决定", 24, C_K), T("摘要里留什么：交给模型判断", 24, ACCENT)).arrange(DOWN, buff=0.2).to_edge(DOWN, buff=0.45)
        self.play(FadeIn(sum_, shift=UP * 0.1)); pause(self, 2.0)
