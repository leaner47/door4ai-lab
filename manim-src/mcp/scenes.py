"""mcp 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm mcp/scenes.py MxN
颜色约定（整讲一致）：没有标准的对接 WARN，MCP / client→server 请求 ACCENT，server 的响应 OK，应用与工具 FG。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *


class MxN(Scene):
    """M 个应用 × N 个工具的乱线，收拢成经过中间插口的 M + N 条线。"""

    def construct(self):
        title = T("没有标准：每对都要写一份对接代码", 34).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        apps = ["聊天应用", "IDE", "终端 Agent", "客服机器人"]
        tools = ["文件", "数据库", "代码仓库", "日历", "邮件", "搜索"]
        m, n = len(apps), len(tools)
        xa, xt = -3.6, 3.6
        ya = [1.5 - i * 1.15 for i in range(m)]
        yt = [2.0 - j * 0.72 for j in range(n)]
        A = VGroup(*[Dot([xa, y, 0], radius=0.08, color=FG) for y in ya])
        B = VGroup(*[Circle(radius=0.08, color=FG, stroke_width=2.5).move_to([xt, y, 0]) for y in yt])
        AL = VGroup(*[T(s, 22, MUTED).next_to(d, LEFT, buff=0.2) for s, d in zip(apps, A)])
        BL = VGroup(*[T(s, 22, MUTED).next_to(d, RIGHT, buff=0.2) for s, d in zip(tools, B)])
        self.play(LaggedStart(*[FadeIn(m) for m in [A, AL, B, BL]], lag_ratio=0.2)); pause(self, 0.3)

        lines = VGroup(*[Line(A[i].get_center(), B[j].get_center(), color=WARN, stroke_width=2, stroke_opacity=0.75) for i in range(m) for j in range(n)])
        self.play(LaggedStart(*[Create(l) for l in lines], lag_ratio=0.04), run_time=2.4)
        cnt = N(f"{m} × {n} = {m * n}", 40, WARN).move_to([-4.2, -3.35, 0])
        self.play(FadeIn(cnt, shift=UP * 0.2)); pause(self)

        # 再加一个工具：每个应用都要多写一份
        y_new = yt[-1] - 0.72
        nb = Circle(radius=0.08, color=FG, stroke_width=2.5).move_to([xt, y_new, 0])
        nl = T("天气", 22, MUTED).next_to(nb, RIGHT, buff=0.2)
        extra = VGroup(*[Line(A[i].get_center(), nb.get_center(), color=WARN, stroke_width=3) for i in range(m)])
        self.play(FadeIn(nb), FadeIn(nl))
        self.play(LaggedStart(*[Create(l) for l in extra], lag_ratio=0.15))
        cnt2 = N(f"{m} × {n + 1} = {m * (n + 1)}", 40, WARN).move_to(cnt)
        self.play(Transform(cnt, cnt2)); pause(self)

        # 收拢：所有乱线变成经过中间插口的线
        hub = RoundedRectangle(width=0.5, height=4.75, corner_radius=0.15, fill_color=ACCENT, fill_opacity=1, stroke_width=0).move_to([0, -0.16, 0])
        hl = N("MCP", 26, ACCENT).next_to(hub, UP, buff=0.12)
        B2 = VGroup(*B, nb)
        left = VGroup(*[Line(A[i].get_center(), [hub.get_left()[0], ya[i], 0], color=ACCENT, stroke_width=3) for i in range(m)])
        right = VGroup(*[Line([hub.get_right()[0], b.get_center()[1], 0], b.get_center(), color=ACCENT, stroke_width=3) for b in B2])
        title2 = T("有 MCP：应用实现一次 client，工具实现一次 server", 34).to_edge(UP, buff=0.4)
        self.play(Transform(title, title2), FadeOut(lines), FadeOut(extra), FadeIn(hub), FadeIn(hl))
        self.play(LaggedStart(*[Create(l) for l in left], lag_ratio=0.1), LaggedStart(*[Create(l) for l in right], lag_ratio=0.1), run_time=1.6)
        cnt3 = N(f"{m} + {n + 1} = {m + n + 1}", 40, ACCENT).move_to(cnt)
        self.play(Transform(cnt, cnt3)); pause(self)

        # 再加一个工具：只多一条线
        note = T("再加一个工具：只多写 1 份 server", 26, OK).move_to([2.6, -3.35, 0])
        self.play(FadeIn(note))
        self.wait(2)


class MCPRoundTrip(Scene):
    """host / client / server 三列：工具怎么被发现、翻译给模型、再被调用。"""

    def construct(self):
        title = T("一次工具调用经过谁的手", 34).to_edge(UP, buff=0.35)
        self.play(Write(title)); pause(self, 0.3)

        xs = {"host": -4.4, "client": 0.0, "server": 4.4}
        heads = VGroup()
        for k, sub in [("host", "AI 应用，连着模型"), ("client", "host 里的连接器"), ("server", "工具的提供方")]:
            box = RoundedRectangle(width=2.6, height=0.95, corner_radius=0.12, stroke_color=MUTED, stroke_width=2, fill_color=BG, fill_opacity=1).move_to([xs[k], 2.45, 0])
            t1 = N(k, 28, FG).move_to(box).shift(UP * 0.17)
            t2 = T(sub, 17, MUTED).move_to(box).shift(DOWN * 0.22)
            heads.add(VGroup(box, t1, t2))
        lanes = VGroup(*[DashedLine([x, 1.95, 0], [x, -3.6, 0], color=LINE, stroke_width=2) for x in xs.values()])
        self.play(FadeIn(heads), Create(lanes)); pause(self, 0.3)

        y = [1.55]

        def msg(a, b, text, color, mono=True, dt=0.56):
            yy = y[0]
            arr = Arrow([xs[a], yy, 0], [xs[b], yy, 0], buff=0.08, color=color, stroke_width=4, max_tip_length_to_length_ratio=0.06)
            lab = (N(text, 21, color) if mono else T(text, 19, color)).next_to(arr, UP, buff=0.04)
            self.play(GrowArrow(arr), FadeIn(lab), run_time=0.8)
            self.wait(0.45)
            y[0] -= dt
            return VGroup(arr, lab)

        rows = VGroup()
        rows.add(msg("host", "client", "列出工具", ACCENT, mono=False))
        rows.add(msg("client", "server", "tools/list", ACCENT))
        rows.add(msg("server", "client", "result: tools[ calculate ]", OK))
        rows.add(msg("client", "host", "工具清单", OK, mono=False))
        pause(self, 0.3)
        tr = T("host 把它翻译成发给模型的 tools 定义；模型生成 tool_use", 20, FG).move_to([0, y[0] + 0.05, 0])
        bg = SurroundingRectangle(tr, color=ACCENT, buff=0.12, corner_radius=0.1, stroke_width=1.5)
        self.play(FadeIn(tr), Create(bg)); y[0] -= 0.7; pause(self)
        rows.add(msg("host", "client", "调 calculate", ACCENT, mono=False))
        rows.add(msg("client", "server", "tools/call  calculate", ACCENT))
        rows.add(msg("server", "client", "result: \"500\"", OK))
        rows.add(msg("client", "host", "结果 → tool_result 给模型", OK, mono=False))
        pause(self)
        end = T("client 与 server 之间每条箭头是一条 JSON-RPC 2.0 消息；模型一条都不发", 24, FG).to_edge(DOWN, buff=0.25)
        self.play(FadeIn(end, shift=UP * 0.2))
        self.wait(3)
