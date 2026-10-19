"""context-window 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm context-window/scenes.py ContextBudget
颜色约定（与实验页一致）：系统提示 ACCENT、工具定义 C_K、历史消息 MUTED、工具结果 C_V、检索片段 紫、超出窗口 WARN。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *

RAG = "#a78bfa"


def block(w, color, label, h=0.9, size=24):
    r = Rectangle(width=w, height=h, stroke_width=0, fill_color=color, fill_opacity=0.95)
    t = T(label, size, "#111214").move_to(r)
    if t.width > w - 0.15:
        t.scale((w - 0.15) / t.width)
    return VGroup(r, t)


class ContextBudget(Scene):
    """一条长度有限的窗口，被五种内容依次填满；最后一块挤不进去，只能先把旧历史压成摘要。"""

    def construct(self):
        title = T("上下文窗口：一条长度有限的带子", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        W = 11.0
        x0 = -W / 2
        y = 0.6
        frame = Rectangle(width=W, height=1.0, stroke_color=MUTED, stroke_width=2).move_to([0, y, 0])
        frame.set_stroke(opacity=0.9)
        cap = T("窗口上限 32K token", 24, MUTED).next_to(frame, UP, buff=0.15).align_to(frame, RIGHT)
        self.play(Create(frame), FadeIn(cap)); pause(self, 0.4)

        # 32K 的带子上，各块按 token 数等比例占宽
        items = [
            ("系统提示", 2000, ACCENT),
            ("工具定义", 6000, C_K),
            ("历史消息", 12000, MUTED),
            ("工具结果", 7000, C_V),
            ("检索片段", 3000, RAG),
        ]
        total_tok = 32000
        scale = W / total_tok
        blocks = VGroup()
        cursor = x0
        for name, tok, col in items:
            b = block(tok * scale, col, name).move_to([cursor + tok * scale / 2, y, 0])
            n = N(f"{tok // 1000}K", 22, FG).next_to(b, DOWN, buff=0.12)
            blocks.add(VGroup(b, n))
            self.play(FadeIn(b, shift=RIGHT * 0.4), FadeIn(n), run_time=0.55)
            cursor += tok * scale
        pause(self, 0.6)
        used = T("已用 30K，只剩 2K", 24, FG).next_to(frame, DOWN, buff=0.8)
        self.play(FadeIn(used)); pause(self)

        # 新一轮：又来一个 5K 的工具结果，挤不进去
        new_tok = 5000
        newb = block(new_tok * scale, C_V, "新的工具结果").move_to([cursor + new_tok * scale / 2, y, 0])
        nn = N("5K", 22, FG).next_to(newb, DOWN, buff=0.12)
        self.play(FadeOut(used), FadeIn(newb, shift=RIGHT * 0.4), FadeIn(nn), run_time=0.7)
        over_w = (cursor + new_tok * scale) - (x0 + W)
        over = Rectangle(width=over_w, height=0.9, stroke_width=0, fill_color=WARN, fill_opacity=1).move_to([x0 + W + over_w / 2, y, 0])
        warn = T("超出 3K：这一次调用直接报错", 26, WARN).next_to(frame, DOWN, buff=0.8)
        self.play(FadeIn(over), FadeIn(warn)); pause(self, 1.2)

        # 办法：把早期历史压成摘要，腾出位置
        hist = blocks[2]
        sum_tok = 2000
        sumb = block(sum_tok * scale, MUTED, "摘要").move_to([hist[0].get_left()[0] + sum_tok * scale / 2, y, 0])
        sn = N("2K", 22, FG).next_to(sumb, DOWN, buff=0.12)
        fix = T("把 12K 的早期历史压成 2K 摘要", 26, ACCENT).next_to(frame, DOWN, buff=0.8)
        shift = (12000 - sum_tok) * scale
        self.play(FadeOut(warn), FadeIn(fix))
        self.play(
            Transform(hist, VGroup(sumb, sn)),
            blocks[3].animate.shift(LEFT * shift), blocks[4].animate.shift(LEFT * shift),
            VGroup(newb, nn).animate.shift(LEFT * shift),
            FadeOut(over),
            run_time=1.4,
        )
        pause(self, 0.6)
        end = T("窗口不会变大，只能决定留什么、丢什么", 28, FG).next_to(frame, DOWN, buff=1.5)
        self.play(FadeOut(fix), FadeIn(end, shift=UP * 0.2))
        self.wait(2)


class MemoryLayers(Scene):
    """记忆的三层：窗口内的工作记忆、跨会话的持久记忆、按需检索的外部知识。"""

    def construct(self):
        title = T("记忆的三层", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        cx = -1.9

        def layer(name, sub, color, yy, w=6.2):
            r = RoundedRectangle(width=w, height=1.15, corner_radius=0.15, stroke_color=color, stroke_width=3, fill_color=BG, fill_opacity=1).move_to([cx, yy, 0])
            t1 = T(name, 27, color).move_to(r).shift(UP * 0.21)
            t2 = T(sub, 19, FG).move_to(r).shift(DOWN * 0.25)
            return VGroup(r, t1, t2)

        top = layer("工作记忆：上下文窗口", "每次调用都看见；有上限，越长越贵", ACCENT, 1.75)
        mid = layer("持久记忆：文件 / 数据库", "跨会话；只写要紧的几行", C_K, -0.25)
        bot = layer("外部知识：文档库", "无限量；每次只取相关的片段", C_V, -2.25)

        self.play(FadeIn(top, shift=UP * 0.2)); pause(self, 0.6)
        tok = T("会话一结束就清空", 22, MUTED).next_to(top, RIGHT, buff=0.35)
        self.play(FadeIn(tok)); pause(self, 0.8)

        self.play(FadeIn(mid, shift=UP * 0.2)); pause(self, 0.4)
        # 写：会话末尾从窗口写到文件；读：下次开头从文件读回（都在两层之间的空隙里）
        xw, xr = cx - 2.2, cx + 0.6
        yt, ym = top[0].get_bottom()[1], mid[0].get_top()[1]
        wr = Arrow([xw, yt, 0], [xw, ym, 0], buff=0.06, color=C_K, stroke_width=4, max_tip_length_to_length_ratio=0.3)
        rd = Arrow([xr, ym, 0], [xr, yt, 0], buff=0.06, color=C_K, stroke_width=4, max_tip_length_to_length_ratio=0.3)
        lw = T("会话结束前写", 20, C_K).next_to(wr, RIGHT, buff=0.12)
        lr = T("下次开始时读", 20, C_K).next_to(rd, RIGHT, buff=0.12)
        self.play(GrowArrow(wr), FadeIn(lw)); pause(self, 0.4)
        self.play(GrowArrow(rd), FadeIn(lr)); pause(self, 0.8)

        self.play(FadeIn(bot, shift=UP * 0.2)); pause(self, 0.4)
        # 检索：从窗口发问到文档库，只带回几段（走在三层的右侧外面）
        xq = top[0].get_right()[0] + 0.45
        yb = bot[0].get_top()[1]
        q = Arrow([xq, yt, 0], [xq, yb + 0.1, 0], buff=0.0, color=C_V, stroke_width=4, max_tip_length_to_length_ratio=0.08)
        back = Arrow([xq + 0.55, yb + 0.1, 0], [xq + 0.55, yt, 0], buff=0.0, color=C_V, stroke_width=4, max_tip_length_to_length_ratio=0.08)
        lq = T("按问题检索", 20, C_V).next_to(back, RIGHT, buff=0.15).shift(DOWN * 0.7)
        lb = T("只带回几段", 20, C_V).next_to(back, RIGHT, buff=0.15).shift(UP * 0.7)
        self.play(FadeOut(tok), GrowArrow(q), FadeIn(lq)); pause(self, 0.3)
        self.play(GrowArrow(back), FadeIn(lb)); pause(self, 0.8)

        end = T("窗口里只放现在要用的；其余的，写下来或留在外面按需取", 26, FG).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2)
