"""multihead-gqa 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm multihead-gqa/scenes.py SplitHeads
颜色约定（整讲一致）：Q 头 C_Q，K C_K，V C_V，各头 / 各组用 HEAD_COLORS 区分，强调 ACCENT。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *

HEAD_COLORS = ["#6f9cf0", "#f2b84b", "#5fc9a8", "#e07a5f"]
GROUP_COLORS = ["#6f9cf0", "#c39bd3", "#e07a5f", "#8fd16a"]   # GQA 的组：避开 K（黄）V（青）


def cells(n, color, size=0.42, opacity=0.9):
    g = VGroup(*[Square(size, stroke_color=BG, stroke_width=2).set_fill(color, opacity) for _ in range(n)])
    return g.arrange(RIGHT, buff=0)


class SplitHeads(Scene):
    """一个长向量切成 h 段，各自做注意力，再拼回来乘 W_O。"""

    def construct(self):
        title = T("多头：切开，各算各的，再拼回来", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        d, h = 16, 4
        per = d // h
        vec = cells(d, ACCENT).move_to(UP * 1.9)
        lab = T("一个 token 的向量 x（d = 16 维）", 24, MUTED).next_to(vec, DOWN, buff=0.2)
        self.play(FadeIn(vec), FadeIn(lab)); pause(self)

        # 上色：每 4 维属于一个头
        self.play(*[vec[i].animate.set_fill(HEAD_COLORS[i // per], 0.9) for i in range(d)], FadeOut(lab))
        pause(self, 0.4)

        # 切开：四段分开、下移
        parts = VGroup(*[VGroup(*vec[k * per:(k + 1) * per]) for k in range(h)])
        xs = [-4.8, -1.6, 1.6, 4.8]
        self.play(*[parts[k].animate.move_to([xs[k], 0.9, 0]) for k in range(h)], run_time=1.2)
        tags = VGroup(*[T(f"头 {k + 1}：{per} 维", 22, HEAD_COLORS[k]).next_to(parts[k], UP, buff=0.18) for k in range(h)])
        self.play(LaggedStart(*[FadeIn(t) for t in tags], lag_ratio=0.15)); pause(self, 0.4)

        # 每个头单独做注意力
        boxes = VGroup(*[RoundedRectangle(width=2.4, height=0.8, corner_radius=0.12, stroke_color=HEAD_COLORS[k], stroke_width=2.5).move_to([xs[k], -0.4, 0]) for k in range(h)])
        btxt = VGroup(*[T("注意力", 22, FG).move_to(boxes[k]) for k in range(h)])
        arrows = VGroup(*[Arrow(parts[k].get_bottom(), boxes[k].get_top(), buff=0.08, color=HEAD_COLORS[k], stroke_width=3, max_tip_length_to_length_ratio=0.3) for k in range(h)])
        self.play(LaggedStart(*[AnimationGroup(GrowArrow(arrows[k]), Create(boxes[k]), FadeIn(btxt[k])) for k in range(h)], lag_ratio=0.2))
        note = T("每个头有自己的 Q、K、V，得到一张自己的注意力分布", 24, MUTED).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(note)); pause(self)

        # 输出：每段变成新的值（换个深浅）
        outs = VGroup(*[cells(per, HEAD_COLORS[k], opacity=0.5).move_to([xs[k], -1.65, 0]) for k in range(h)])
        oar = VGroup(*[Arrow(boxes[k].get_bottom(), outs[k].get_top(), buff=0.08, color=HEAD_COLORS[k], stroke_width=3, max_tip_length_to_length_ratio=0.3) for k in range(h)])
        self.play(LaggedStart(*[AnimationGroup(GrowArrow(oar[k]), FadeIn(outs[k], shift=DOWN * 0.2)) for k in range(h)], lag_ratio=0.15))
        pause(self)

        # 拼接回 16 维
        self.play(FadeOut(VGroup(parts, tags, boxes, btxt, arrows, oar)), FadeOut(note))
        concat = VGroup(*outs)
        self.play(concat.animate.arrange(RIGHT, buff=0).move_to(UP * 1.2), run_time=1.2)
        ctag = T("拼接：又是 16 维", 24, FG).next_to(concat, UP, buff=0.25)
        self.play(FadeIn(ctag)); pause(self, 0.5)

        # 乘 W_O 混合
        wo = RoundedRectangle(width=2.0, height=0.8, corner_radius=0.12, stroke_color=ACCENT, stroke_width=2.5).move_to(DOWN * 0.2)
        wot = M(r"\times\, W_O", 36, ACCENT).move_to(wo)
        a1 = Arrow(concat.get_bottom(), wo.get_top(), buff=0.08, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.3)
        self.play(GrowArrow(a1), Create(wo), Write(wot))
        mixed = cells(d, ACCENT).move_to(DOWN * 1.6)
        a2 = Arrow(wo.get_bottom(), mixed.get_top(), buff=0.08, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.3)
        self.play(GrowArrow(a2), TransformFromCopy(concat, mixed), run_time=1.2)
        mtag = T("各头的发现混在一起，加回残差流", 24, FG).next_to(mixed, DOWN, buff=0.25)
        self.play(FadeIn(mtag)); pause(self)

        param = T("W_Q、W_K、W_V、W_O 合计 4 × d × d：切成几个头，参数一个不多", 26, OK).to_edge(DOWN, buff=0.3)
        self.play(FadeOut(mtag), FadeIn(param, shift=UP * 0.2))
        self.wait(2)


class GroupedKV(Scene):
    """8 个 Q 头：MHA 各有一组 K、V，逐步合并成 GQA 的 2 组。"""

    def construct(self):
        title = T("GQA：几个 Q 头共用一组 K、V", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        h = 8
        qs = VGroup(*[Square(0.55, stroke_width=0).set_fill(C_Q, 0.95) for _ in range(h)]).arrange(RIGHT, buff=0.35).move_to(UP * 1.7)
        qlab = T("Q 头", 24, C_Q).next_to(qs, LEFT, buff=0.35)
        self.play(FadeIn(qs), FadeIn(qlab)); pause(self, 0.3)

        y_kv = -0.9

        def kv_group(g):
            """g 组 K/V，每组居中在它负责的 Q 头下方。"""
            per = h // g
            grp = VGroup()
            for k in range(g):
                cx = (qs[k * per].get_center()[0] + qs[(k + 1) * per - 1].get_center()[0]) / 2
                kk = Rectangle(width=0.55, height=0.32, stroke_width=0).set_fill(C_K, 0.95)
                vv = Rectangle(width=0.55, height=0.32, stroke_width=0).set_fill(C_V, 0.95)
                pair = VGroup(kk, vv).arrange(DOWN, buff=0.06).move_to([cx, y_kv, 0])
                grp.add(pair)
            return grp

        def links(g, kv):
            per = h // g
            return VGroup(*[Line(qs[i].get_bottom(), kv[i // per].get_top(), color=GROUP_COLORS[i // per] if g < h else MUTED, stroke_width=2.5) for i in range(h)])

        def cache_bar(g):
            full = 6.0
            bar = Rectangle(width=full * g / h, height=0.32, stroke_width=0).set_fill(ACCENT, 0.9)
            bar.move_to([-3.0 + full * g / h / 2, -2.6, 0])
            return bar

        kvlab = VGroup(T("K", 22, C_K), T("V", 22, C_V)).arrange(DOWN, buff=0.12)

        kv = kv_group(8)
        ln = links(8, kv)
        kvlab.next_to(kv, LEFT, buff=0.35)
        self.play(LaggedStart(*[FadeIn(p) for p in kv], lag_ratio=0.08), FadeIn(kvlab))
        self.play(Create(ln))
        name = T("MHA：8 组 K、V", 28, FG).move_to([0, -1.85, 0])
        self.play(FadeIn(name))
        frame = Rectangle(width=6.0, height=0.32, stroke_color=MUTED, stroke_width=1.5).move_to([0, -2.6, 0])
        bar = cache_bar(8)
        clab = T("KV cache", 22, MUTED).next_to(frame, LEFT, buff=0.3)
        ratio = N("1", 30, ACCENT).next_to(frame, RIGHT, buff=0.3)
        self.play(Create(frame), FadeIn(bar), FadeIn(clab), FadeIn(ratio)); pause(self)

        for g, txt, r in [(4, "GQA：4 组，每组 2 个 Q 头", "1/2"), (2, "GQA：2 组，每组 4 个 Q 头", "1/4")]:
            kv2, ln2 = kv_group(g), None
            ln2 = links(g, kv2)
            per = h // g
            # 同组的 K/V 合并成一组（GQA 论文用组内平均做初始化）
            self.play(*[ReplacementTransform(VGroup(*kv[k * (len(kv) // g):(k + 1) * (len(kv) // g)]), kv2[k]) for k in range(g)],
                      Transform(ln, ln2), run_time=1.3)
            kv = kv2
            self.play(*[qs[i].animate.set_fill(GROUP_COLORS[i // per], 0.95) for i in range(h)],
                      Transform(name, T(txt, 28, FG).move_to(name)),
                      Transform(bar, cache_bar(g)), Transform(ratio, N(r, 30, ACCENT).next_to(frame, RIGHT, buff=0.3)))
            pause(self)

        avg = T("合并方法：把同组原来的 K、V 头取平均，再少量继续训练", 24, MUTED).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(avg, shift=UP * 0.2)); pause(self, 1.2)
        end = T("Q 头一个没少；要缓存的 K、V 只剩 1/4", 26, OK).to_edge(DOWN, buff=0.3)
        self.play(ReplacementTransform(avg, end))
        self.wait(2)
