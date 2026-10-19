"""agent-loop 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm agent-loop/scenes.py WhileLoop
颜色约定（整讲一致）：模型输出 / tool_use ACCENT，工具结果 OK，思考 C_K（黄），退出 / 最终回答 FG。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import manimpango

_f = set(manimpango.list_fonts())
MONO = next((f for f in ["Menlo", "DejaVu Sans Mono", "Noto Sans Mono", "Liberation Mono"] if f in _f), "monospace")


def C(s, size=24, color=FG):
    # Manim 的 Text 会吞掉行首空格：缩进由调用方按层级平移
    return Text(s.lstrip(" "), font=MONO, font_size=size, color=color)


def msg_box(label, color):
    t = C(label, 18, FG)
    r = RoundedRectangle(width=t.width + 0.3, height=0.42, corner_radius=0.08, stroke_color=color, stroke_width=2, fill_color=color, fill_opacity=0.18).move_to(t)
    return VGroup(r, t)


class WhileLoop(Scene):
    """while True 循环与 messages 数组并排：每转一圈，数组长一截。"""

    def construct(self):
        title = T("Agent = 模型 + 工具 + 一个 while 循环", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        lines = [
            ("while True:", FG),
            ("    out = model(messages)", ACCENT),
            ("    messages.append(out)", FG),
            ("    if not out.tool_use:", FG),
            ("        break", FG),
            ("    r = run_tool(out.tool_use)", OK),
            ("    messages.append(r)", FG),
        ]
        code = VGroup(*[C(s, 24, c) for s, c in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        for s_, l in zip([s for s, _ in lines], code):
            l.shift(RIGHT * 0.28 * (len(s_) - len(s_.lstrip(" "))) / 4 * 1.7)
        code.to_edge(LEFT, buff=0.5).shift(DOWN * 0.3)
        self.play(LaggedStart(*[FadeIn(l, shift=RIGHT * 0.2) for l in code], lag_ratio=0.12)); pause(self)

        # 右侧：messages 数组
        head = C("messages = [", 22, MUTED).move_to([1.1, 2.3, 0], aligned_edge=LEFT)
        self.play(FadeIn(head))
        stack = VGroup()
        top = head.get_bottom() + DOWN * 0.15

        def push(label, color):
            b = msg_box(label, color)
            b.next_to(top if len(stack) == 0 else stack[-1], DOWN, buff=0.1).align_to(head, LEFT).shift(RIGHT * 0.3)
            stack.add(b)
            return b

        cursor = SurroundingRectangle(code[0], color=C_K, buff=0.08, stroke_width=2)
        self.play(Create(cursor), FadeIn(push("user: 北京和上海哪个更热？", MUTED)))
        pause(self, 0.5)

        rounds = [("assistant: tool_use 查北京温度", "tool_result: 22 °C"),
                  ("assistant: tool_use 查上海温度", "tool_result: 26 °C")]
        loop_tag = T("第 1 圈", 26, C_K).next_to(code, DOWN, buff=0.5).align_to(code, LEFT)
        self.play(FadeIn(loop_tag))
        for k, (a, r) in enumerate(rounds):
            if k:
                new_tag = T(f"第 {k + 1} 圈", 26, C_K).move_to(loop_tag)
                self.play(Transform(cursor, SurroundingRectangle(code[0], color=C_K, buff=0.08, stroke_width=2)), Transform(loop_tag, new_tag), run_time=0.5)
            self.play(Transform(cursor, SurroundingRectangle(code[1], color=C_K, buff=0.08, stroke_width=2)), run_time=0.5)
            self.play(Transform(cursor, SurroundingRectangle(code[2], color=C_K, buff=0.08, stroke_width=2)), FadeIn(push(a, ACCENT), shift=UP * 0.15), run_time=0.7)
            self.play(Transform(cursor, SurroundingRectangle(code[3], color=C_K, buff=0.08, stroke_width=2)), run_time=0.4)
            self.play(Transform(cursor, SurroundingRectangle(code[5], color=C_K, buff=0.08, stroke_width=2)), run_time=0.5)
            self.play(Transform(cursor, SurroundingRectangle(code[6], color=C_K, buff=0.08, stroke_width=2)), FadeIn(push(r, OK), shift=UP * 0.15), run_time=0.7)
            pause(self, 0.4)

        new_tag = T("第 3 圈", 26, C_K).move_to(loop_tag)
        self.play(Transform(cursor, SurroundingRectangle(code[0], color=C_K, buff=0.08, stroke_width=2)), Transform(loop_tag, new_tag), run_time=0.5)
        self.play(Transform(cursor, SurroundingRectangle(code[1], color=C_K, buff=0.08, stroke_width=2)), run_time=0.5)
        self.play(Transform(cursor, SurroundingRectangle(code[2], color=C_K, buff=0.08, stroke_width=2)), FadeIn(push("assistant: 上海更热，高 4 °C", ACCENT), shift=UP * 0.15), run_time=0.7)
        self.play(Transform(cursor, SurroundingRectangle(code[3], color=C_K, buff=0.08, stroke_width=2)), run_time=0.4)
        self.play(Transform(cursor, SurroundingRectangle(code[4], color=WARN, buff=0.08, stroke_width=2)), run_time=0.5)
        tail = C("]", 22, MUTED).next_to(stack[-1], DOWN, buff=0.1).align_to(head, LEFT)
        self.play(FadeIn(tail))
        end = T("没有 tool_use 就 break：数组每圈长两条，每圈都整个重发", 24, FG).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(2)


class ReActTrace(Scene):
    """Thought → Action → Observation 三色交替往下长。"""

    def construct(self):
        title = T("ReAct：先想，再做，再看结果", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        rows = [
            ("Question", "北京和上海现在哪个更热？差多少？", MUTED),
            ("Thought 1", "要比较两个城市，先查北京的温度。", C_K),
            ("Action 1", "get_temperature[北京]", ACCENT),
            ("Observation 1", "22 °C", OK),
            ("Thought 2", "北京查到了，再查上海。", C_K),
            ("Action 2", "get_temperature[上海]", ACCENT),
            ("Observation 2", "26 °C", OK),
            ("Thought 3", "上海 26 °C，北京 22 °C，上海更热 4 °C。", C_K),
            ("Action 3", "Finish[上海更热，高 4 °C]", FG),
        ]
        x_key, x_val, y0, dy = -6.0, -3.0, 2.3, 0.52
        group = VGroup()
        for i, (k, v, col) in enumerate(rows):
            key = C(k + ":", 22, col).move_to([x_key, y0 - i * dy, 0], aligned_edge=LEFT)
            val = T(v, 22, FG).move_to([x_val, y0 - i * dy, 0], aligned_edge=LEFT)
            line = VGroup(key, val)
            group.add(line)

        legend = VGroup(T("Thought = 模型写推理", 22, C_K), T("Action = 模型发 tool_use", 22, ACCENT), T("Observation = harness 回填工具结果", 22, OK)).arrange(RIGHT, buff=0.7).to_edge(DOWN, buff=0.35)

        self.play(FadeIn(group[0], shift=RIGHT * 0.2)); pause(self, 0.5)
        self.play(FadeIn(legend))
        brace_label = None
        for r in range(2):
            base = 1 + r * 3
            for j in range(3):
                self.play(FadeIn(group[base + j], shift=RIGHT * 0.2), run_time=0.6)
                pause(self, 0.3)
            br = Brace(VGroup(*group[base:base + 3]), RIGHT, buff=0.3, color=MUTED)
            lab = T(f"循环第 {r + 1} 圈", 22, MUTED).next_to(br, RIGHT, buff=0.15)
            self.play(GrowFromCenter(br), FadeIn(lab), run_time=0.6); pause(self, 0.4)
        self.play(FadeIn(group[7], shift=RIGHT * 0.2), run_time=0.6); pause(self, 0.3)
        self.play(FadeIn(group[8], shift=RIGHT * 0.2), run_time=0.6)
        box = SurroundingRectangle(group[8], color=WARN, buff=0.1, stroke_width=2)
        fin = T("Finish = 没有 tool_use，循环退出", 22, WARN).next_to(box, DOWN, buff=0.15).align_to(box, LEFT)
        self.play(Create(box), FadeIn(fin))
        self.wait(2)
