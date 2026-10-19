"""tool-calling 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm tool-calling/scenes.py ToolCallLoop

颜色约定（整讲一致）：
  模型 ACCENT（蓝）  程序 C_K（黄）  工具结果 OK（青）  用户 MUTED
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *


def card(title, body, color, w=3.5, h=1.25, ts=22, bs=20):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.1,
                         stroke_color=color, stroke_width=2.5, fill_color=BG, fill_opacity=1)
    t = N(title, ts, color).move_to(r.get_top() + DOWN * 0.26)
    b = T(body, bs, FG).move_to(r.get_center() + DOWN * 0.22)
    if b.width > w - 0.3:
        b.scale((w - 0.3) / b.width)
    return VGroup(r, t, b)


class ToolCallLoop(Scene):
    """一次 tool call 的完整来回：模型只生成，程序才执行。"""

    def construct(self):
        title = T("一次 tool call 的来回", 36).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        # 两条泳道：模型（云端）/ 程序（你的代码）
        y_m, y_p = 1.45, -1.55
        lane_m = DashedLine([-6.6, y_m + 1.0, 0], [6.6, y_m + 1.0, 0], color=LINE, stroke_width=2)
        lane_p = DashedLine([-6.6, y_p - 1.0, 0], [6.6, y_p - 1.0, 0], color=LINE, stroke_width=2)
        tag_m = T("模型（只会生成 token）", 22, ACCENT).next_to(lane_m, UP, buff=0.12).align_to(lane_m, LEFT)
        tag_p = T("你的程序（真正执行）", 22, C_K).next_to(lane_p, DOWN, buff=0.12).align_to(lane_p, LEFT)
        self.play(Create(lane_m), Create(lane_p), FadeIn(tag_m), FadeIn(tag_p)); pause(self, 0.4)

        xs = [-4.7, -1.6, 1.6, 4.7]

        # ① 程序发请求：问题 + 工具定义
        c1 = card("请求", "问题 + 工具定义", C_K, w=3.0, h=1.2).move_to([xs[0], y_p, 0])
        self.play(FadeIn(c1, shift=UP * 0.2)); pause(self, 0.4)
        a1 = Arrow(c1.get_top(), [xs[0], y_m - 0.65, 0], buff=0.08, color=MUTED, stroke_width=4,
                   max_tip_length_to_length_ratio=0.12)
        self.play(GrowArrow(a1)); pause(self, 0.3)

        # ② 模型生成 tool_use
        c2 = card("tool_use", "name / input", ACCENT, w=3.2, h=1.2).move_to([xs[1], y_m, 0])
        gen = T("生成，不是执行", 20, ACCENT).next_to(c2, UP, buff=0.15)
        self.play(TransformFromCopy(c1, c2), run_time=1.1)
        self.play(FadeIn(gen)); pause(self)

        # ③ 回到程序：解析、校验、真的跑
        a2 = Arrow(c2.get_bottom(), [xs[1], y_p + 0.65, 0], buff=0.08, color=MUTED, stroke_width=4,
                   max_tip_length_to_length_ratio=0.12)
        c3 = card("执行", "解析 → 校验 → 跑", C_K, w=3.2, h=1.2).move_to([xs[1], y_p, 0])
        self.play(GrowArrow(a2)); self.play(FadeIn(c3, shift=UP * 0.2)); pause(self, 0.5)
        run = N("get_weather(city=\"上海\")", 22, C_K).next_to(c3, DOWN, buff=0.2)
        self.play(FadeIn(run)); pause(self, 0.6)

        # ④ tool_result 回填
        c4 = card("tool_result", "24 °C，多云", OK, w=3.0, h=1.2).move_to([xs[2], y_p, 0])
        self.play(TransformFromCopy(c3, c4), FadeOut(run), run_time=1.0); pause(self, 0.4)
        a3 = Arrow(c4.get_top(), [xs[2], y_m - 0.65, 0], buff=0.08, color=OK, stroke_width=4,
                   max_tip_length_to_length_ratio=0.12)
        back = T("作为一条新消息接在对话后面", 20, OK).next_to(a3, RIGHT, buff=0.15)
        if back.width > 4.4:
            back.scale(4.4 / back.width)
        self.play(GrowArrow(a3), FadeIn(back)); pause(self)

        # ⑤ 模型根据结果说最终回答
        self.play(FadeOut(back), FadeOut(gen))
        c5 = card("最终回答", "上海现在 24 °C", ACCENT, w=3.2, h=1.2).move_to([xs[3], y_m, 0])
        self.play(TransformFromCopy(c4, c5), run_time=1.1); pause(self, 0.5)

        end = T("模型两次都只是生成文本；中间那一步才是执行", 24, FG).to_edge(DOWN, buff=0.28)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2)


class SchemaToText(Scene):
    """工具定义怎么变成上下文里的 token：schema 被序列化、切碎、和消息挤同一个窗口。"""

    def construct(self):
        title = T("工具定义是上下文里的 token", 36).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.4)

        lines = [
            '{ "name": "get_weather",',
            '  "description": "查询某个城市当前的天气…",',
            '  "input_schema": {',
            '    "type": "object",',
            '    "properties": { "city": { "type": "string" } },',
            '    "required": ["city"] } }',
        ]
        code = VGroup(*[N(s, 24, FG) for s in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        code.scale(min(1.0, 10.4 / code.width)).move_to([0, 1.3, 0])
        box = SurroundingRectangle(code, color=C_K, buff=0.25, corner_radius=0.1)
        lab = T("你写在请求里的工具定义", 22, C_K).next_to(box, UP, buff=0.18)
        self.play(FadeIn(lab), Create(box), LaggedStart(*[FadeIn(l) for l in code], lag_ratio=0.12), run_time=2.2)
        pause(self)

        # 切成 token：一排小方块
        n = 34
        cells = VGroup()
        for i in range(n):
            c = RoundedRectangle(width=0.3, height=0.34, corner_radius=0.05,
                                 stroke_color=C_K, stroke_width=1.5,
                                 fill_color=C_K, fill_opacity=0.35)
            cells.add(c)
        cells.arrange(RIGHT, buff=0.055).move_to([0, -0.35, 0])
        arrow = Arrow(box.get_bottom(), cells.get_top() + UP * 0.25, buff=0.1,
                      color=MUTED, stroke_width=4, max_tip_length_to_length_ratio=0.14)
        tok = T("序列化后切成 token", 22, MUTED).next_to(arrow, RIGHT, buff=0.2)
        self.play(GrowArrow(arrow), FadeIn(tok)); pause(self, 0.3)
        self.play(LaggedStart(*[FadeIn(c, scale=0.6) for c in cells], lag_ratio=0.04), run_time=1.6)
        cnt = N("82 token", 30, C_K).next_to(cells, DOWN, buff=0.3)
        self.play(FadeIn(cnt)); pause(self)

        # 和消息挤同一个窗口
        self.play(FadeOut(lab), FadeOut(box), FadeOut(code), FadeOut(arrow), FadeOut(tok),
                  VGroup(cells, cnt).animate.shift(UP * 2.3).scale(0.9))
        bar = RoundedRectangle(width=11.6, height=0.62, corner_radius=0.08,
                               stroke_color=LINE, stroke_width=2, fill_opacity=0).move_to([0, -0.9, 0])
        wl = T("每一轮请求的上下文窗口", 22, MUTED).next_to(bar, UP, buff=0.2)
        self.play(Create(bar), FadeIn(wl)); pause(self, 0.3)

        segs, x = VGroup(), bar.get_left()[0]
        for w, col, name in [(1.9, C_K, "工具定义"), (1.2, WARN, "系统提示"), (3.4, MUTED, "历史消息"), (2.6, OK, "tool_result")]:
            r = Rectangle(width=w, height=0.62, stroke_width=0, fill_color=col, fill_opacity=0.75)
            r.move_to([x + w / 2, -0.9, 0]); x += w
            t = T(name, 19, col).next_to(r, DOWN, buff=0.18)
            if t.width > w + 0.5:
                t.scale((w + 0.5) / t.width)
            segs.add(VGroup(r, t))
        for g in segs:
            self.play(FadeIn(g[0]), FadeIn(g[1]), run_time=0.5)
        pause(self, 0.5)

        end = T("工具越多、说明越长，每一轮都要重付这笔 token", 24, FG).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2)
