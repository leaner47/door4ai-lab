"""Door4AI Lab 的 Manim 统一风格：配色、字体、常用小工具。

每个场景文件开头：
    import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from door4ai_style import *
"""
from manim import *
import manimpango

# —— 画布 ——
BG = "#111214"            # 与网站深色卡片同色；视频在深浅两种页面上都放在圆角深色块里
config.background_color = BG
config.frame_rate = 30

# —— 配色：同一个概念整讲始终用同一种颜色 ——
FG = "#e8e6df"            # 正文
MUTED = "#9aa1ab"         # 次要
LINE = "#2a2d31"          # 网格 / 分隔
ACCENT = "#6f9cf0"        # 主角（与网站强调色一致）
C_Q, C_K, C_V = "#6f9cf0", "#f2b84b", "#5fc9a8"   # 蓝 / 黄 / 青：三类主要对象
WARN = "#e07a5f"          # 误差、警告
OK = "#5fc9a8"

# —— 字体：中文苹方（Mac）→ Noto Sans CJK（Linux）；拉丁与数字用 Times New Roman ——
_fonts = set(manimpango.list_fonts())
ZH = next((f for f in ["PingFang SC", "Noto Sans CJK SC", "Heiti SC", "Microsoft YaHei"] if f in _fonts), "sans-serif")
EN = next((f for f in ["Times New Roman", "Liberation Serif", "DejaVu Serif"] if f in _fonts), "serif")


def T(s: str, size: float = 32, color: str = FG, **kw) -> Text:
    """中文/混排文字（Pango 渲染，不走 LaTeX）。"""
    return Text(s, font=ZH, font_size=size, color=color, **kw)


def N(s: str, size: float = 32, color: str = FG, **kw) -> Text:
    """纯数字 / 英文标签，用 Times New Roman。"""
    return Text(s, font=EN, font_size=size, color=color, **kw)


def M(tex: str, size: float = 40, color: str = FG, **kw) -> MathTex:
    """公式（LaTeX）。Python 里用原始字符串 r"..."。"""
    return MathTex(tex, font_size=size, color=color, **kw)


def pause(scene: Scene, t: float = 0.8):
    """3b1b 节奏：一次只动一个东西，动画之间停一下。"""
    scene.wait(t)
