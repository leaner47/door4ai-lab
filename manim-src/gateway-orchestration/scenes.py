"""gateway-orchestration 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm gateway-orchestration/scenes.py GatewayRouting
颜色约定（整讲一致）：网关 / 主 Agent ACCENT，小档 C_V，大档 C_K，备用 MUTED→FG，故障 WARN，结论 OK。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *


def box(label, w, h, color, size=26, fill=0.12):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.15, stroke_color=color, stroke_width=3,
                         fill_color=color, fill_opacity=fill)
    t = T(label, size, FG).move_to(r)
    return VGroup(r, t)


def caption(s, color=FG):
    return T(s, 26, color).to_edge(DOWN, buff=0.45)


class GatewayRouting(Scene):
    """请求流进网关，被分流到不同模型；一个模型挂了，流量切到备用；相同请求直接从缓存返回。"""

    def construct(self):
        title = T("网关：所有请求先过这一层", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        app = box("应用", 1.6, 1.0, MUTED).move_to([-5.4, 0, 0])
        gw = box("网关", 1.7, 3.4, ACCENT, 30).move_to([-1.9, 0, 0])
        small = box("小模型", 2.0, 0.9, C_V, 24).move_to([2.6, 1.7, 0])
        big = box("大模型", 2.0, 0.9, C_K, 24).move_to([2.6, 0.2, 0])
        backup = box("备用模型", 2.0, 0.9, MUTED, 24).move_to([2.6, -1.4, 0])
        self.play(FadeIn(app), FadeIn(gw)); pause(self, 0.3)
        self.play(LaggedStart(FadeIn(small), FadeIn(big), lag_ratio=0.3)); pause(self, 0.3)

        pipe = Line(app.get_right(), gw.get_left(), color=MUTED, stroke_width=3)
        to_s = Line(gw.get_right(), small.get_left(), color=C_V, stroke_width=3)
        to_b = Line(gw.get_right(), big.get_left(), color=C_K, stroke_width=3)
        self.play(Create(pipe), Create(to_s), Create(to_b))

        def send(kinds, run=2.4):
            """kinds: 每个请求去哪：'s' 小模型 / 'b' 大模型 / 'k' 备用 / 'c' 缓存命中。"""
            anims = []
            for i, k in enumerate(kinds):
                col = {"s": C_V, "b": C_K, "k": FG, "c": OK}[k]
                d = Dot(app.get_right(), radius=0.09, color=col)
                if k == "c":
                    path = VMobject().set_points_as_corners([app.get_right(), gw.get_left() + RIGHT * 0.3, app.get_right() + DOWN * 0.25])
                else:
                    tgt = {"s": small, "b": big, "k": backup}[k].get_left()
                    path = VMobject().set_points_as_corners([app.get_right(), gw.get_left(), gw.get_right(), tgt])
                anims.append(Succession(Wait(i * 0.22), MoveAlongPath(d, path, run_time=1.2, rate_func=linear), FadeOut(d, run_time=0.15)))
            self.play(*anims, run_time=run)

        cap = caption("按难度路由：简单的给小模型，难的给大模型")
        self.play(FadeIn(cap))
        send("sbsssbss", 3.0); pause(self, 0.4)

        # 大模型挂了
        cross = Cross(big[0], stroke_color=WARN, stroke_width=6)
        err = T("超时 / 429", 24, WARN).next_to(big, RIGHT, buff=0.2)
        cap2 = caption("大模型超时或被限流", WARN)
        self.play(Create(cross), FadeIn(err), Transform(cap, cap2)); pause(self, 0.4)
        to_k = Line(gw.get_right(), backup.get_left(), color=FG, stroke_width=3)
        self.play(FadeIn(backup), Create(to_k), to_b.animate.set_stroke(opacity=0.2))
        cap3 = caption("降级：难的请求切到备用模型，应用这边什么都不用改")
        self.play(Transform(cap, cap3))
        send("skssksk", 3.0); pause(self, 0.4)

        # 缓存
        cache = box("缓存", 1.1, 0.6, OK, 22).move_to(gw.get_bottom() + UP * 0.55)
        cap4 = caption("一字不差的请求：网关直接从缓存返回，不调模型", OK)
        self.play(FadeIn(cache), Transform(cap, cap4))
        send("csckcs", 2.8); pause(self, 0.4)

        # 记账
        ledger = VGroup(T("统一记账", 22, ACCENT), T("统一 trace", 22, ACCENT)).arrange(DOWN, buff=0.15).next_to(gw, UP, buff=0.15)
        self.play(FadeOut(title), FadeIn(ledger, shift=DOWN * 0.2))
        self.wait(2)


class OrchestratorWorkers(Scene):
    """主 Agent 拆出三个子任务，三个子 Agent 各用干净上下文并行做，只把结论交回。"""

    def construct(self):
        title = T("主 Agent 拆任务，子 Agent 并行做", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        lead = box("主 Agent", 2.4, 0.9, ACCENT, 26).move_to([0, 2.2, 0])
        task = T("任务：比较三家云厂商的 GPU 价格", 24, MUTED).next_to(lead, DOWN, buff=0.2)
        self.play(FadeIn(lead), FadeIn(task)); pause(self)

        xs = [-4.2, 0, 4.2]
        names = ["厂商 A", "厂商 B", "厂商 C"]
        subs, cards = VGroup(), VGroup()
        for x, nm in zip(xs, names):
            cards.add(box(nm, 1.6, 0.6, C_V, 22, 0.08).move_to([x, 0.8, 0]))
            subs.add(box("子 Agent", 1.9, 0.8, C_V, 24).move_to([x, -0.2, 0]))
        self.play(FadeOut(task), LaggedStart(*[TransformFromCopy(lead, c) for c in cards], lag_ratio=0.2)); pause(self, 0.4)
        self.play(LaggedStart(*[FadeIn(s, shift=DOWN * 0.2) for s in subs], lag_ratio=0.15))
        cap = caption("每个子 Agent 从干净的上下文开始，并行工作")
        self.play(FadeIn(cap))

        # 各自的上下文条：并行长高
        base_y = -1.1
        bars = VGroup(*[Rectangle(width=0.7, height=0.05, stroke_width=0, fill_color=C_V, fill_opacity=0.8)
                        .move_to([x, base_y, 0], aligned_edge=UP) for x in xs])
        self.play(FadeIn(bars))
        heights = [1.7, 1.3, 1.9]
        self.play(*[b.animate.stretch_to_fit_height(h, about_edge=UP) for b, h in zip(bars, heights)], run_time=2.2, rate_func=linear)
        lab = T("各自的工具结果", 22, MUTED).next_to(bars[2], RIGHT, buff=0.2)
        self.play(FadeIn(lab)); pause(self)

        # 只交回结论
        concl = VGroup(*[box("结论", 1.0, 0.45, OK, 20, 0.15).move_to([x, base_y - 0.3, 0]) for x in xs])
        cap2 = caption("做完只交回一段结论，工具结果留在子 Agent 那里", OK)
        self.play(*[ReplacementTransform(b, c) for b, c in zip(bars, concl)], FadeOut(lab), Transform(cap, cap2)); pause(self, 0.4)
        targets = VGroup(*[concl[i].copy().scale(0.8) for i in range(3)]).arrange(RIGHT, buff=0.15).next_to(lead, RIGHT, buff=0.3)
        self.play(*[concl[i].animate.move_to(targets[i]).scale(0.8) for i in range(3)], FadeOut(cards), run_time=1.4)
        pause(self, 0.3)
        cap3 = caption("主 Agent 只读三段结论，再写最终答案")
        ans = box("最终答案", 2.2, 0.7, ACCENT, 24, 0.25).move_to([0, 1.0, 0])
        self.play(Transform(cap, cap3), FadeOut(subs))
        self.play(TransformFromCopy(VGroup(lead, concl), ans)); pause(self)

        cost = T("代价：token 成倍、协调开销、交接时会丢信息", 26, WARN).next_to(ans, DOWN, buff=0.8)
        self.play(FadeIn(cost, shift=UP * 0.2))
        self.wait(2)
