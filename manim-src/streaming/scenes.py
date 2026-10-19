"""streaming 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm streaming/scenes.py TTFTvsTotal
颜色约定（整讲一致）：非流式 WARN，流式 / 到达的 token ACCENT，排队 MUTED，prefill C_K，事件边界（空行）OK。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *

MONO = next((f for f in ["Noto Sans Mono CJK SC", "DejaVu Sans Mono", "Liberation Mono"] if f in manimpango.list_fonts()), "monospace")


def C(s, size=20, color=FG, **kw):
    """等宽代码文字（中英混排）。"""
    return Text(s, font=MONO, font_size=size, color=color, **kw)


class TTFTvsTotal(Scene):
    """同一次生成：非流式最后一刻一整块到达；流式在 TTFT 后一小块一小块到达。"""

    def construct(self):
        title = T("同一次生成，两种交给你的方式", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        # 示例数字（与实验 00 默认值一致）：排队 0.2 s，prefill 2000 token ÷ 5000 token/s = 0.4 s，输出 500 token @ 60 token/s
        q, pf, total = 0.2, 0.4, 0.6 + 499 / 60          # total ≈ 8.92 s
        ttft = q + pf
        X0, X1 = -4.6, 6.2
        X = lambda t: X0 + (X1 - X0) * t / 9.5

        axis = NumberLine(x_range=[0, 9, 1], length=(X1 - X0) * 9 / 9.5, color=MUTED, include_numbers=False, stroke_width=2)
        axis.move_to([(X(0) + X(9)) / 2, -2.6, 0])
        nums = VGroup(*[N(f"{t} s", 20, MUTED).next_to(axis.n2p(t), DOWN, buff=0.15) for t in range(0, 10, 3)])
        self.play(Create(axis), FadeIn(nums)); pause(self, 0.3)

        ys = [1.2, -0.9]
        tags = VGroup(T("非流式", 28, WARN).move_to([-5.9, ys[0], 0]), T("流式", 28, ACCENT).move_to([-5.9, ys[1], 0]))
        self.play(FadeIn(tags)); pause(self, 0.3)

        h = 0.55
        def bar(t0, t1, y, color, op=1.0):
            return Rectangle(width=max(0.02, X(t1) - X(t0)), height=h, stroke_width=0, fill_color=color, fill_opacity=op).move_to([(X(t0) + X(t1)) / 2, y, 0])

        # 两边服务器做的事一模一样：排队 + prefill
        pre = VGroup()
        for y in ys:
            pre.add(bar(0, q, y, MUTED, 0.6), bar(q, ttft, y, C_K, 0.85))
        lq = T("排队", 20, MUTED).next_to(pre[0], UP, buff=0.12).shift(LEFT * 0.1)
        lp = T("prefill", 20, C_K).next_to(pre[1], UP, buff=0.12).shift(RIGHT * 0.35)
        self.play(LaggedStart(*[GrowFromEdge(b, LEFT) for b in pre], lag_ratio=0.15), FadeIn(lq), FadeIn(lp)); pause(self, 0.4)

        # 扫过时间：流式一路到达小块，非流式什么也看不到
        dashed = DashedVMobject(Rectangle(width=X(total) - X(ttft), height=h, color=MUTED, stroke_width=2).move_to([(X(ttft) + X(total)) / 2, ys[0], 0]), num_dashes=60)
        hidden = T("服务器在生成，你什么也看不到", 22, MUTED).move_to(dashed)
        now = ValueTracker(ttft)
        cursor = always_redraw(lambda: DashedLine([X(now.get_value()), 2.1, 0], [X(now.get_value()), -2.45, 0], color=FG, stroke_width=2, dash_length=0.08))
        n_ticks = 60
        ticks = VGroup(*[Line([X(ttft + i * (total - ttft) / (n_ticks - 1)), ys[1] - h / 2, 0], [X(ttft + i * (total - ttft) / (n_ticks - 1)), ys[1] + h / 2, 0], color=ACCENT, stroke_width=3) for i in range(n_ticks)])
        for tk in ticks: tk.set_opacity(0)
        def upd(m):
            t = now.get_value()
            for i, tk in enumerate(m):
                ti = ttft + i * (total - ttft) / (n_ticks - 1)
                tk.set_opacity(1 if ti <= t + 1e-6 else 0)
        ticks.add_updater(upd)
        self.add(ticks, cursor)
        self.play(Create(dashed), FadeIn(hidden), run_time=0.8)

        f1 = VGroup(T("首字", 22, ACCENT), N(f"{ttft:.1f} s", 24, ACCENT)).arrange(RIGHT, buff=0.1).next_to([X(ttft), ys[1] - h / 2, 0], DOWN, buff=0.25)
        self.play(FadeIn(f1, shift=UP * 0.2), run_time=0.5)
        self.play(now.animate.set_value(total), run_time=6, rate_func=linear)
        ticks.clear_updaters()

        block = Rectangle(width=0.18, height=h + 0.2, stroke_width=0, fill_color=WARN, fill_opacity=1).move_to([X(total), ys[0], 0])
        f2 = VGroup(T("首字", 22, WARN), N(f"{total:.1f} s", 24, WARN)).arrange(RIGHT, buff=0.1).next_to(block, DOWN, buff=0.25)
        self.play(FadeIn(block, scale=1.6), FadeIn(f2, shift=UP * 0.2)); pause(self)
        self.play(FadeOut(cursor))

        # 终点对齐，差的只是首字
        brace = BraceBetweenPoints([X(ttft), ys[0] + h / 2 + 0.1, 0], [X(total), ys[0] + h / 2 + 0.1, 0], direction=UP, color=OK)
        btxt = T("流式让你早看到这么久", 22, OK).next_to(brace, UP, buff=0.1)
        self.play(FadeOut(lq), FadeOut(lp), GrowFromCenter(brace), FadeIn(btxt)); pause(self)

        f = T("TTFT ≈ 排队 + prompt 长度 ÷ prefill 速度", 26, FG).to_edge(DOWN, buff=0.25)
        self.play(Write(f))
        self.wait(2)


class SSEFrames(Scene):
    """字节流被空行切成一个个事件，事件里的文字增量再拼成句子。"""

    def construct(self):
        title = T("字节流 → 事件 → 句子", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        parts = ["流式输出", "让回答", "边生成边显示。"]
        lines = []
        for p in parts:
            lines.append(("event: content_block_delta", MUTED))
            lines.append(('data: {…,"delta":{"type":"text_delta","text":"' + p + '"}}', FG))
            lines.append(("", FG))
        rows = VGroup()
        for s, col in lines:
            rows.add(C(s, 20, col) if s else Rectangle(width=0.1, height=0.18, stroke_opacity=0, fill_opacity=0))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.16).move_to([-1.6, -0.2, 0])

        cap = T("服务器往一个不关闭的 HTTP 响应里一段段写文本", 24, MUTED).next_to(rows, UP, buff=0.4).align_to(rows, LEFT)
        self.play(FadeIn(cap)); pause(self, 0.3)

        # 1) 字节按任意大小的块到达：一行行地「冒」出来
        import random
        random.seed(4)
        for r in rows:
            if isinstance(r, Rectangle):
                continue
            n = len(r); k = 0
            while k < n:
                step = random.randint(6, 18)
                self.play(FadeIn(r[k:k + step]), run_time=0.12, rate_func=linear)
                k += step
        pause(self)

        # 2) 空行是事件边界
        blanks = VGroup()
        for i in range(2, len(rows), 3):
            y = rows[i].get_center()[1]
            blanks.add(Line([rows.get_left()[0], y, 0], [rows.get_left()[0] + 1.2, y, 0], color=OK, stroke_width=6))
        bl = T("空行 = 一个事件结束", 24, OK).next_to(blanks[-1], RIGHT, buff=0.3)
        self.play(LaggedStart(*[Create(b) for b in blanks], lag_ratio=0.2), FadeIn(bl)); pause(self)

        boxes = VGroup(*[SurroundingRectangle(VGroup(rows[i], rows[i + 1]), color=ACCENT, buff=0.1, corner_radius=0.08) for i in range(0, len(rows), 3)])
        self.play(LaggedStart(*[Create(b) for b in boxes], lag_ratio=0.25)); pause(self)

        # 3) 每个框变成一个解析好的事件
        evs = VGroup(*[VGroup(C("text_delta", 20, ACCENT), C('"' + p + '"', 24, FG)).arrange(RIGHT, buff=0.25) for p in parts])
        evs.arrange(DOWN, aligned_edge=LEFT, buff=0.75).move_to([4.6, -0.2, 0])
        self.play(FadeOut(cap), FadeOut(bl), FadeOut(blanks),
                  VGroup(rows, boxes).animate.scale(0.72).to_edge(LEFT, buff=0.4))
        self.play(LaggedStart(*[TransformFromCopy(boxes[i], evs[i]) for i in range(3)], lag_ratio=0.3)); pause(self)

        # 4) 文字增量拼成句子
        sent = T("".join(parts), 40, FG).to_edge(DOWN, buff=0.7)
        pieces = VGroup()
        idx = 0
        for p in parts:
            pieces.add(sent[idx:idx + len(p)]); idx += len(p)
        for i in range(3):
            self.play(TransformFromCopy(evs[i][1], pieces[i]), run_time=0.8)
        pause(self, 0.4)
        und = Underline(sent, color=ACCENT, buff=0.1)
        note = T("前端看到的「一个字一个字蹦出来」", 24, ACCENT).next_to(und, DOWN, buff=0.15)
        self.play(Create(und), FadeIn(note))
        self.wait(2)
