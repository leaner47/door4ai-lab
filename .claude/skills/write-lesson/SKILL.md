---
name: write-lesson
description: 把本人提出的一个问题（如「X 是什么」「为什么 Y」「Z 怎么工作」）写成 lab.door4ai.com 课程「AI 从入门到精通」的一讲教材：文章 + 可交互实验页 + Manim 动画，构建、上线并更新 HANDOFF。仅用于 door4ai-lab 项目。
---

# 写一讲教材（door4ai-lab 专用）

本人在这个项目里提出一个问题时，把它写成课程里的一讲：**文章（讲清楚）+ 实验页（亲手试）+ Manim 动画（看它动起来）**，最后上线。

开始前必须先完整读 `HANDOFF.md`（项目强制规定）。它和本人当下的要求优先于本文件。

## 0. 定题（动手前用一两句话跟本人确认，除非问题已经很明确）

- **slug**：英文短横线，如 `gradient-descent`。
- **标题**：沿用现有风格「问题：一句话点题」，例：`Token 是什么：一句话是怎么进出大模型的`。
- **order**：看 `src/content/blog/*.md` 现有 order，插在逻辑上该在的位置（可用小数，如 3.5）。
- **分篇**：`src/data/course.ts` 的 `PARTS` 按 order 区间自动归篇（order < 4 基础篇，其余模型篇）。不属于现有任何一篇时才新开一篇，先问本人。
- 和前后讲的衔接：这一讲依赖哪讲、又为哪讲铺路。

## 1. 先研究，后动笔

- 概念要准确。涉及现状、版本、价格、规格的内容先查证（WebSearch），不凭记忆写。
- 数字用真实公开参数（如 Llama-3-70B：80 层 × 8 KV 头 × 128 维；RTX 4090 1008 GB/s），实验里做真实计算，不画假数据。
- 讲法参照 3Blue1Brown：先给直觉画面，再给公式；一次只引入一个新东西。

## 2. 硬规矩（违反就是返工）

- **全中文**；`token` 等约定术语不翻译（见 HANDOFF 第 4 节）。
- **不出现指向本人的信息**：不用本人城市（扬州、高邮、波士顿等）、学校、真名、GitHub 用户名、邮箱、自家设备。需要例子就用北京、上海、合肥、纽约，用户名用 `your-name`。
- **简洁**：不加没被要求的说明小字（eyebrow 以外的副标题、导语式灰字、计数、注释）。实验页开头只放 `.eyebrow` + `h1` + `.lede` 三样（这是实验页规范的一部分）。
- 字体：拉丁与数字 Times New Roman，中文苹方 / 黑体。
- **科学单位一律用英文缩写**：s、ms、μs、ns、m、km、kg、g、Hz、W 等，数字与单位之间空一格（`300 s`、`204 km/ms`、`1 TB/s`、`token/s`）。正文、实验页文字、JS 拼出的读数、Manim 画面里都一样。「秒级」这类量级说法可以保留中文。
- **不用横线分隔内容**：段落、小节、列表项之间靠留白；要突出某一块用圆角浅底（`var(--paper)`），不加 `border-top/bottom` 分隔线（表格行线、卡片外框除外）。
- **文字铺满版面**：不给段落、列表、导语设 `max-width`（不要 68ch 之类），只留左右页边距 `clamp(16px,3vw,40px)`（与页眉对齐）。表单可以有自己的宽度。
- 手机宽度 390px 不能横向滚动；深浅两色都要能看。

## 3. 实验页 `public/labs/<slug>/index.html`

单文件 HTML（内联 CSS/JS，库只从 cdnjs 等 CDN 加载）。从 `templates/lab.html` 复制起步，它已经包含：

- 设计 token（`--bg --paper --fg --muted --line --accent --warn --ok`，深色 `#000` / 卡片 `#111214`，浅色 `#f7f3ea` / 卡片 `#fffdf8`），跟随 `<html data-theme>` 与系统深浅色。
- 图形尺寸上限脚本（`</body>` 前那段「图形尺寸上限」）：每张图（`.lab` 里的 svg/canvas、figure 里的图、`.clip` 视频）按自身宽高比收窄并居中，高度不超过视口 62%（最多 620px，嵌在文章 iframe 里时取外层页面的视口），文字、控件、读数照样铺满。**不要删**；画布高度若由代码按宽度计算，要监听 `resize` 重画（脚本改了尺寸会触发一次 resize）。在 1512 × 860（MacBook Pro 14 寸）下检查每张图都不超过一屏的 62%。
- 嵌入检测与主题同步脚本（`html.embedded`、读 `localStorage` 的 `d4a-theme`）。**不要删。**
- 版心 `.wrap{box-sizing:border-box;padding-inline:clamp(16px,3vw,40px)}`（不设 max-width，随窗口铺满），开头 `header.lab-intro`。

每个实验 = 编号小标题 `<h2><span class="n">01</span>…</h2>` → 一两段说明 → `.lab` 卡片（控件条 → 画图区 SVG/canvas → 读数行）→ 一句「注意看什么」的 `.note`。一般 4–6 个实验，从直觉到细节递进。

## 4. Manim 动画（可视化）

参考项目文档 `manim/使用说明.md`。只给**动起来才讲得清**的东西做动画：公式推导、向量/矩阵变换、过程演化（训练迭代、数据流过网络）。能用滑块交互讲清的放实验页，不重复做动画。每讲 1–3 段，每段 15–60 s。

**源码**：`manim-src/<slug>/scenes.py`，从 `templates/scene.py` 复制。开头导入 `manim-src/door4ai_style.py`，它统一了背景 `#111214`、配色（`ACCENT/C_Q/C_K/C_V/WARN/OK`）、字体（`T()` 中文、`N()` 数字英文、`M()` 公式）。同一个概念整讲始终用同一种颜色；用 `Transform` 表现「这个变成那个」；动画之间 `pause(self)`；不用 Pi creatures。

**渲染**（在云端工作区做；本人 Mac 上的 Manim 不在可用的 shell 里）：

```bash
# 一次性环境（每个新会话做一次；manimpango 需要 pango 头文件，Python 用 3.12）
apt-get install -y -q libpango1.0-dev libcairo2-dev pkg-config dvisvgm
python3.12 -m venv "$SCRATCH/mvenv" && "$SCRATCH/mvenv/bin/pip" install -q manim
# 渲染（在 manim-src/ 目录里跑，manim.cfg 在这里）
cd manim-src
"$SCRATCH/mvenv/bin/manim" -ql --format webm <slug>/scenes.py SceneName   # 预览
"$SCRATCH/mvenv/bin/manim" -s -ql <slug>/scenes.py SceneName              # 末帧 PNG，用 Read 看一眼
"$SCRATCH/mvenv/bin/manim" -qh --format webm <slug>/scenes.py SceneName   # 正式 1080p
"$SCRATCH/mvenv/bin/manim" -qh -s <slug>/scenes.py SceneName              # 海报帧
```

`$SCRATCH` 是会话的 scratchpad 目录。渲染失败时看 `manim/使用说明.md` 第 8 节排错表（缺 `dvisvgm`、LaTeX 转义 `r"\pi"`、改了不生效加 `--disable_caching`）。

**产物**：复制到 `public/videos/<slug>/<SceneName>.webm` 和 `.png`（海报）。单个 webm 尽量 < 5 MB（Cloudflare Pages 单文件上限 25 MB）。`media/` 缓存不入库（已在 `.gitignore`）。

**嵌入**：

- 文章正文里：
  ```html
  <figure class="clip"><video src="/videos/<slug>/SceneName.webm" poster="/videos/<slug>/SceneName.png" controls loop muted playsinline preload="metadata"></video></figure>
  ```
- 实验页里：同样的 `<figure class="clip">`，`templates/lab.html` 已带 `.clip` 样式。
- 交付前用 `-s` 导出的末帧 PNG 逐段看一遍：文字不出画、不重叠、颜色符合规矩。

## 5. 文章 `src/content/blog/<slug>.md`

从 `templates/article.md` 复制。frontmatter 必填：`title / description / pubDate / tags / lab / series: ai-mastery / order`。正文结构沿用现有各讲：

1. `## 一句话版本`：一段话说清本质。
2. 2–4 个讲解小节，必要处嵌 Manim 动画。
3. `## 实验里讲了什么`：按实验编号逐条一句话。
4. `## 和前后两讲的关系`。
5. `## 延伸阅读`（可选，只放可靠出处）。

文章页会自动把实验整宽嵌在最上面（实验自带标题），正文接在下面，末尾自动出现 WhatsApp 一行和上一讲 / 下一讲。不要自己再写这些。

## 6. 检查与上线

1. `npm run build` 必须通过（会顺带重新生成 `functions/_lib/access-map.ts`，一起提交）。
2. 本地起 `dist/` 静态服务，用 Playwright（`executablePath: '/opt/pw-browsers/chromium'`）截图并亲眼看：1440 宽与 390 宽、深浅两色；文章页、实验页、课程目录。检查 `scrollWidth` 不超过视口、控制台无报错、视频能加载。
3. 全文再检索一遍个人信息（`扬州|高邮|波士顿|leaner47|周业闰|Yerun`），必须为 0。
4. 按 HANDOFF「更新协议」更新第 5、6 节（新决定写进第 4 节），与代码一起 commit，`git pull --rebase` 后 push `main`（常有其他会话同时在推）。
5. 等 1–2 分钟，用 `gh api repos/leaner47/door4ai-lab/commits/<sha>/check-runs` 确认 Cloudflare Pages 成功。
6. 把 HANDOFF.md 同步到 claude.ai 项目文档 `door4ai-lab/HANDOFF.md`；本人 Mac 上的副本 `~/Documents/Agents/door4ai-lab` 若已连接，`git pull --ff-only` 同步。

## 7. 回复本人

简短：这一讲叫什么、排在第几讲、有几个实验和几段动画、已上线。不复述过程。
