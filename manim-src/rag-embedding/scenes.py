"""rag-embedding 的 Manim 动画。渲染方法见 .claude/skills/write-lesson/SKILL.md 第 4 节。
在 manim-src/ 目录里跑：manim -ql --format webm rag-embedding/scenes.py TextToVector
颜色约定（整讲一致）：查询 ACCENT（蓝），文档/片段 C_K（黄），相似/命中 OK（青），无关 MUTED。
"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from door4ai_style import *
import numpy as np


def vec_box(vals, color, cell=0.34):
    """一列小方格表示向量：正值填该颜色，负值填 WARN，深浅 = 大小。"""
    g = VGroup()
    for a in vals:
        c = Square(cell, stroke_width=1, stroke_color=BG)
        c.set_fill(color if a >= 0 else WARN, opacity=min(1, 0.15 + abs(a) * 0.6))
        g.add(c)
    return g.arrange(DOWN, buff=0)


class TextToVector(Scene):
    """句子 → 向量 → 落到空间里：意思相近的句子聚在一起。"""

    def construct(self):
        title = T("一句话变成一个向量", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)

        sents = [("鲜奶开了以后能放多久", C_Q), ("开封的牛奶要冷藏", C_Q), ("机器坏了要怎么报修", C_K), ("设备故障先联系维修", C_K), ("灭火器放在什么地方", C_V)]
        # 与实验页同一种做法得到的方向：三簇大致互相垂直；动画里用示意坐标（单位圆上）
        angles = [20, 40, 112, 128, -62]
        rng = np.random.default_rng(7)

        # 第一句：文字 → 向量
        s0 = T(sents[0][0], 30, sents[0][1]).move_to([-4.3, 1.6, 0])
        self.play(FadeIn(s0, shift=RIGHT * 0.3)); pause(self, 0.5)
        model = RoundedRectangle(width=3.0, height=1.0, corner_radius=0.15, stroke_color=MUTED, stroke_width=2).move_to([0.6, 1.6, 0])
        mt = T("embedding 模型", 24, FG).move_to(model)
        self.play(FadeIn(model), FadeIn(mt)); pause(self, 0.3)
        v0 = vec_box(rng.normal(0, 0.8, 8), sents[0][1]).move_to([3.0, 1.6, 0])
        dims = N("[0.12, −0.40, 0.83, …]", 24, sents[0][1]).next_to(v0, RIGHT, buff=0.25)
        arrow_in = Arrow(s0.get_right(), model.get_left(), buff=0.1, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.25)
        arrow_out = Arrow(model.get_right(), v0.get_left(), buff=0.1, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.25)
        self.play(GrowArrow(arrow_in)); self.play(GrowArrow(arrow_out), FadeIn(v0), FadeIn(dims)); pause(self)
        note = T("固定长度的一串数：真实模型几百到几千维", 26, MUTED).move_to([0, -1.5, 0])
        self.play(FadeIn(note)); pause(self)

        # 收起，换成空间
        self.play(*[FadeOut(m) for m in [s0, model, mt, v0, dims, arrow_in, arrow_out, note]])
        origin = np.array([0.0, -0.9, 0.0]); R = 2.4
        circ = Circle(radius=R, color=LINE, stroke_width=2).move_to(origin)
        ax1 = Line(origin + LEFT * (R + 0.4), origin + RIGHT * (R + 0.4), color=LINE, stroke_width=2)
        ax2 = Line(origin + DOWN * (R + 0.3), origin + UP * (R + 0.3), color=LINE, stroke_width=2)
        cap = T("把向量画成箭头（二维截面）", 24, MUTED).next_to(title, DOWN, buff=0.15)
        self.play(Create(ax1), Create(ax2), Create(circ), FadeIn(cap)); pause(self, 0.3)

        arrows = []
        for (txt, col), ang in zip(sents, angles):
            a = np.deg2rad(ang); tip = origin + np.array([np.cos(a), np.sin(a), 0]) * R * 0.92
            ar = Arrow(origin, tip, buff=0, color=col, stroke_width=4, max_tip_length_to_length_ratio=0.12)
            lab = T(txt, 22, col)
            off = np.array([np.cos(a), np.sin(a), 0]) * 0.25 + (RIGHT if np.cos(a) > 0.2 else LEFT if np.cos(a) < -0.2 else ORIGIN) * (lab.width / 2 + 0.1)
            if abs(np.cos(a)) <= 0.2: off += DOWN * 0.3
            if np.sin(a) < -0.5: off = RIGHT * (lab.width / 2 + 0.25) + UP * 0.1
            lab.move_to(tip + off)
            self.play(GrowArrow(ar), FadeIn(lab), run_time=0.7)
            arrows.append((ar, lab))
            pause(self, 0.25)
        pause(self, 0.4)

        # 夹角 → 余弦
        a0, a1 = np.deg2rad(angles[0]), np.deg2rad(angles[1])
        arc = Arc(radius=1.1, start_angle=a0, angle=a1 - a0, arc_center=origin, color=OK, stroke_width=4)
        th = M(r"\theta", 32, OK).move_to(origin + np.array([np.cos((a0 + a1) / 2), np.sin((a0 + a1) / 2), 0]) * 1.45)
        self.play(Create(arc), FadeIn(th)); pause(self, 0.4)
        f1 = M(r"\cos\theta = \frac{q\cdot d}{\lVert q\rVert\,\lVert d\rVert}", 40).to_corner(DL, buff=0.5)
        self.play(Write(f1)); pause(self)
        res = T("意思相近 → 夹角小 → 余弦接近 1", 26, OK).next_to(f1, UP, buff=0.4).align_to(f1, LEFT)
        self.play(FadeIn(res, shift=UP * 0.2)); pause(self, 0.6)
        a2 = np.deg2rad(angles[2])
        arc2 = Arc(radius=1.5, start_angle=a0, angle=a2 - a0, arc_center=origin, color=WARN, stroke_width=4)
        res2 = T("话题不同 → 接近垂直 → 余弦接近 0", 26, WARN).next_to(f1, UP, buff=0.4).align_to(f1, LEFT)
        self.play(Create(arc2), Transform(res, res2)); self.wait(2)


class RAGPipeline(Scene):
    """RAG 流水线：切块 → 向量化 → 入库 → 查询向量化 → top-k → 进上下文 → 回答。"""

    def construct(self):
        title = T("RAG 流水线", 36).to_edge(UP, buff=0.4)
        self.play(Write(title)); pause(self, 0.4)
        rng = np.random.default_rng(3)

        # —— 离线：文档 → 切块 → 向量 → 库 ——
        off_tag = T("离线：先把资料入库", 24, MUTED).move_to([-6.0, 2.3, 0]).align_to(LEFT * 6.3, LEFT)
        self.play(FadeIn(off_tag))
        doc = Rectangle(width=1.3, height=1.7, stroke_color=C_K, stroke_width=2).move_to([-5.3, 0.9, 0])
        lines = VGroup(*[Line(ORIGIN, RIGHT * 0.9, color=C_K, stroke_width=2) for _ in range(6)]).arrange(DOWN, buff=0.17).move_to(doc)
        dl = T("文档", 22, C_K).next_to(doc, DOWN, buff=0.12)
        self.play(FadeIn(doc), FadeIn(lines), FadeIn(dl)); pause(self, 0.4)

        chunks = VGroup(*[Rectangle(width=1.3, height=0.42, stroke_color=C_K, stroke_width=2, fill_color=C_K, fill_opacity=0.15) for _ in range(3)]).arrange(DOWN, buff=0.14).move_to([-3.1, 0.9, 0])
        cl = T("切块 chunk", 22, C_K).next_to(chunks, DOWN, buff=0.12)
        a1 = Arrow(doc.get_right(), chunks.get_left(), buff=0.1, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.3)
        self.play(GrowArrow(a1), TransformFromCopy(lines, chunks), FadeIn(cl)); pause(self, 0.4)

        vecs = VGroup(*[vec_box(rng.normal(0, 0.8, 5), C_K, 0.22) for _ in range(3)]).arrange(RIGHT, buff=0.22).move_to([-0.9, 0.9, 0])
        vl = T("向量化", 22, C_K).next_to(vecs, DOWN, buff=0.12)
        a2 = Arrow(chunks.get_right(), vecs.get_left(), buff=0.1, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.3)
        self.play(GrowArrow(a2), TransformFromCopy(chunks, vecs), FadeIn(vl)); pause(self, 0.4)

        # 二维的「数据库」图标：上椭圆 + 两条竖边 + 下半椭圆
        c = np.array([1.6, 0.9, 0.0]); rw, rh, hh = 0.7, 0.2, 0.6
        db = VGroup(
            Ellipse(width=2 * rw, height=2 * rh, color=ACCENT, stroke_width=2).move_to(c + UP * hh),
            Line(c + UP * hh + LEFT * rw, c + DOWN * hh + LEFT * rw, color=ACCENT, stroke_width=2),
            Line(c + UP * hh + RIGHT * rw, c + DOWN * hh + RIGHT * rw, color=ACCENT, stroke_width=2),
            Arc(radius=1, start_angle=PI, angle=PI, color=ACCENT, stroke_width=2).stretch(rw, 0).stretch(rh, 1).move_to(c + DOWN * hh + DOWN * rh / 2),
            Arc(radius=1, start_angle=PI, angle=PI, color=ACCENT, stroke_width=2, stroke_opacity=0.5).stretch(rw, 0).stretch(rh, 1).move_to(c + DOWN * rh / 2),
        )
        db_lab = T("向量库", 22, ACCENT).next_to(db, UP, buff=0.12)
        a3 = Arrow(vecs.get_right(), db.get_left(), buff=0.1, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.3)
        self.play(GrowArrow(a3), FadeIn(db), FadeIn(db_lab))
        self.play(vecs.copy().animate.scale(0.4).move_to(db), run_time=0.8); pause(self, 0.6)

        # —— 在线：查询 → 向量 → top-k → 上下文 → 回答 ——
        on_tag = T("在线：每次提问", 24, MUTED).move_to([-6.0, -0.9, 0]).align_to(LEFT * 6.3, LEFT)
        self.play(FadeIn(on_tag))
        q = T("牛奶开封后能放多久？", 24, ACCENT).move_to([-4.6, -1.9, 0])
        self.play(FadeIn(q, shift=RIGHT * 0.3)); pause(self, 0.3)
        qv = vec_box(rng.normal(0, 0.8, 5), ACCENT, 0.22).move_to([-1.6, -1.9, 0])
        qvl = T("查询向量", 22, ACCENT).next_to(qv, DOWN, buff=0.12)
        a4 = Arrow(q.get_right(), qv.get_left(), buff=0.1, color=MUTED, stroke_width=3, max_tip_length_to_length_ratio=0.3)
        self.play(GrowArrow(a4), TransformFromCopy(q, qv), FadeIn(qvl)); pause(self, 0.3)
        a5 = Arrow(qv.get_top(), db.get_bottom(), buff=0.1, color=ACCENT, stroke_width=3, max_tip_length_to_length_ratio=0.2)
        self.play(GrowArrow(a5))
        k_lab = T("按余弦相似度取 top-k", 22, OK).next_to(db, RIGHT, buff=0.3)
        self.play(FadeIn(k_lab))
        hits = VGroup(*[Rectangle(width=1.6, height=0.36, stroke_color=OK, stroke_width=2, fill_color=OK, fill_opacity=0.2) for _ in range(3)]).arrange(DOWN, buff=0.1).move_to([3.0, -1.9, 0])
        a6 = Arrow(db.get_bottom() + RIGHT * 0.3, hits.get_top(), buff=0.1, color=OK, stroke_width=3, max_tip_length_to_length_ratio=0.2)
        self.play(GrowArrow(a6), LaggedStart(*[FadeIn(h, shift=DOWN * 0.2) for h in hits], lag_ratio=0.2)); pause(self, 0.4)

        # 上下文
        ctx = RoundedRectangle(width=2.3, height=2.2, corner_radius=0.12, stroke_color=FG, stroke_width=2).move_to([5.5, -1.3, 0])
        ctx_l = T("上下文", 22, FG).next_to(ctx, UP, buff=0.1)
        sysb = Rectangle(width=1.9, height=0.3, stroke_width=0, fill_color=MUTED, fill_opacity=0.6).move_to(ctx.get_top() + DOWN * 0.35)
        self.play(FadeIn(ctx), FadeIn(ctx_l), FadeIn(sysb))
        hit_copies = VGroup(*[Rectangle(width=1.9, height=0.3, stroke_width=0, fill_color=OK, fill_opacity=0.5) for _ in range(3)]).arrange(DOWN, buff=0.08).next_to(sysb, DOWN, buff=0.08)
        qb = Rectangle(width=1.9, height=0.3, stroke_width=0, fill_color=ACCENT, fill_opacity=0.6).next_to(hit_copies, DOWN, buff=0.08)
        self.play(Transform(hits.copy(), hit_copies)); self.play(FadeIn(qb)); pause(self, 0.5)
        ans = T("模型回答：48 小时内用完", 26, OK).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(ans, shift=UP * 0.2)); self.wait(2)
