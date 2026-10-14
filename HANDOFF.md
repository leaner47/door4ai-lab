# HANDOFF — Door4AI Lab (lab.door4ai.com)

> 这份文件是本项目的唯一交接入口。任何 AI 或人接手时**先读完本文件**，再动手。
> 任何一次工作结束前，**必须**按文末「更新协议」更新本文件并提交。没有更新 HANDOFF 的工作视为未完成。

最后更新：2026-10-14 18:20 America/New_York · 更新者：Claude（会话 session_01DR5LFdGneALqpA1WLAEDZS）

---

## 1. 项目是什么

- **目标**：周业闰（Yerun Zhou，GitHub `leaner47`）的个人 AI 教学博客。每篇文章配一个可交互实验页（拖滑块、改参数、看真实计算），而不是静态示意图。
- **商业意图**：内容将来打包成付费课程出售。因此仓库 **不加任何开源 license**（保留所有权利）。仓库目前是 public，若内容量上来后可考虑转 private。
- **语言**：全部中文；英文和数字字体用 Times New Roman，中文用苹方/黑体（PingFang SC → Heiti SC → Microsoft YaHei → Noto Sans SC）。
- **第一篇文章**：《KV Cache 为什么能压、怎么压》，含「KV Cache 压缩实验室」五个交互实验（量化网格 / 注意力容忍度 / K-V 分组热力图 / 显存计算器 / MLA 低秩）。

## 2. 基础设施（已全部搭好，可用）

| 项 | 值 |
|---|---|
| 线上地址 | https://lab.door4ai.com （也可 https://door4ai-lab.pages.dev） |
| 代码仓库 | https://github.com/leaner47/door4ai-lab ，生产分支 `main` |
| 托管 | Cloudflare Pages，项目名 `door4ai-lab`，账号 ID `7d240087365af7f41b02e5fd0d25b474` |
| 构建 | Framework preset: None；Build command `npm run build`；Output `dist`；Node 22 |
| 部署触发 | push 到 `main` 自动构建部署，约 1–2 分钟 |
| DNS | `door4ai.com` zone 内一条 CNAME：`lab` → `door4ai-lab.pages.dev`（Proxied）。**其余记录（admin/api/app/grafana/pay-api/@ 等）属于 door4ai.com 上正在运行的其他业务，绝对不要动。** |
| 登录/访问控制 | Cloudflare Access（Zero Trust）应用 **Door4AI Lab**：保护 `lab.door4ai.com/ai`、`/resources`、`/posts`、`/labs` 四个路径；策略 **Door4AI Lab students**（Allow，按邮箱白名单，目前只有本人邮箱）；会话 1 个月；登录方式为邮箱一次性验证码（One-time PIN）。首页 `/` 公开。**加学员 = 在该策略的 Emails 列表里加邮箱**（Zero Trust → Access controls → Policies）。不要改 grafana / AI Gateway Admin 那两个应用和「Only me」策略。 |
| 安装包镜像 | R2 桶 `door4ai-lab-dl`（APAC 位置提示，私有），绑定到 Pages 项目为 `DL`；Pages 环境变量 `SYNC_KEY`（手动同步口令，值只在 Cloudflare 设置里）。下载走 `/dl/<app>/<platform>`（在 Access 保护内），状态看 `/dl/manifest.json`；手动同步 `GET /sync-dl?key=<SYNC_KEY>[&app=flclash\|claude\|codex][&force=1]`（/sync-dl 不在 Access 内，靠口令保护）。下载时若某项超过 24h 未同步会在后台自动刷新。 |
| GitHub App | Cloudflare Workers and Pages 已授权仓库：`door4ai-lab`、`door4ai-site`（后者是别的项目，不要动） |
| 本机副本 | `~/Documents/Agents/door4ai-lab`（Mac），是 GitHub 仓库的 clone |

账号登录：Cloudflare 和 GitHub 都由本人登录；AI 不持有、不输入任何密码。需要 sudo/passkey 验证时交给本人操作。

## 3. 技术栈与目录结构

Astro 5 静态站，无 UI 框架，无 Tailwind。依赖只有 `astro`、`@astrojs/rss`、`@astrojs/sitemap`。

```
door4ai-lab/
├── HANDOFF.md              ← 本文件
├── CLAUDE.md / AGENTS.md   ← 指向本文件的强制说明（给各家 AI 工具读）
├── README.md               ← 面向人的简短说明
├── astro.config.mjs        ← site: https://lab.door4ai.com, sitemap
├── src/
│   ├── content.config.ts   ← 文章 schema：title, description, pubDate, updatedDate?, tags[], lab?, series?, order?
│   ├── content/blog/*.md   ← 文章正文（markdown）
│   ├── components/HoloCard.astro ← 全息卡片（移植自 React Bits HoloCard，MIT + Commons Clause）；卡面是由 props 生成的 SVG
│   ├── scripts/holo-card.js / .css ← HoloCard 的 WebGL 着色器与交互（原版去 React 化）
│   ├── scripts/circular-carousel.js ← 3D 转盘（仿 React Bits CircularCarousel 自写）：拖动/惯性/吸附/点侧卡转到正面；少于 12 张时按弧形排列并限制转动范围
│   ├── data/resources.ts   ← Resource 页的条目（link.dl = 镜像 id 走 /dl/，link.url = 外链）
│   ├── layouts/Base.astro  ← 全站布局 + 导航 + 全部 CSS；导航右侧「登录/退出」由脚本调 /cdn-cgi/access/get-identity 判断；prop `full` 让 main 占满宽度（首页用）
│   └── pages/
│       ├── index.astro         ← 首页：只有居中的一句 motto，入口全在导航
│       ├── ai.astro            ← 「AI 从入门到精通」课程目录：series == 'ai-mastery' 的文章按 order 排序
│       ├── resources.astro     ← Resource 资源库，数据来自 src/data/resources.ts
│       ├── posts/[...slug].astro ← 文章页；frontmatter 有 lab 时顶部 iframe 嵌入实验
│       └── rss.xml.js
├── functions/              ← Cloudflare Pages Functions（随仓库自动部署）
│   ├── _lib/sources.ts     ← 镜像源：每个 target 的 resolve()（FlClash=GitHub latest；Claude=官方 latest 重定向 + apt 索引；Codex=codex-app-prod/ChatGPT.dmg）
│   ├── _lib/mirror.ts      ← 同步逻辑：解析→下载→流式写入 R2→更新 manifest.json
│   ├── dl/[[path]].ts      ← /dl/manifest.json 与 /dl/<app>/<platform> 下载（支持 Range 断点续传）
│   └── sync-dl.ts          ← 手动同步入口
└── public/
    ├── favicon.svg
    └── labs/<name>/index.html  ← 独立实验页，完整 HTML，自带全部 CSS/JS
```

### 写一篇新文章的标准流程
1. 实验页：写成单文件 HTML（内联 CSS/JS，可用 cdnjs 等 CDN 加载库），放到 `public/labs/<slug>/index.html`。
2. 文章：`src/content/blog/<slug>.md`，frontmatter 写 `lab: /labs/<slug>/`；属于课程的写 `series: ai-mastery` 和 `order: <数字>`（10、20、30… 留空隙便于插入）。不写 series 的文章不会出现在课程目录里。
   - 加资源：编辑 `src/data/resources.ts`，不需要新建页面。**Resource 页只放本人明确指定的条目，AI 不得自行添加。**
3. 本地 `npm run build` 必须通过。
4. commit → push `main` → 等 1–2 分钟 → 打开 https://lab.door4ai.com 验证文章页和实验页都能打开。
5. 更新本文件第 5、6 节。

### 实验页设计规范（沿用第一篇）
- 颜色用 CSS token（`--bg --paper --fg --muted --line --accent --warn --ok`），深浅色都要定义，`body` 必须有显式背景色。**背景色定稿：深色 `#000` 纯黑（卡片 `#111214`），浅色 `#f7f3ea` 米白（卡片 `#fffdf8`）**，站点和实验页保持一致。
- 字体栈同上（Times New Roman 在前，中文回退到苹方/黑体）。
- 每个实验 = 控件条（滑块/分段按钮）→ 画图区（SVG 或 canvas）→ 读数行（大数字 + 小标签）→ 一句「注意看什么」的 note。
- 真实计算，不画假数据；数值用公开架构参数（如 Llama-3-70B：80 层 × 8 KV 头 × 128 维）。
- 手机宽度（~400px）不能横向滚动。

## 4. 已做的关键决定（不要反复讨论）

- 域名用子域名 `lab.door4ai.com`（door4ai.com 根域名有正在运行的业务；matrix-tech-inyz.com 留给公司）。
- 博客放子域名而非 `blog.`，取 `lab` 呼应「实验室」定位。
- 不加 license；仓库 public。
- 用 Astro + Cloudflare Pages，不自建服务器。
- 实验页用独立 HTML + iframe 嵌入，而不是做成 Astro 组件——便于把同一个 HTML 作为 Claude artifact 预览、也便于全屏分享。
- **Resource 页只放本人指定的内容**（目前：FlClash、Codex、Claude 的下载入口 + door4ai.com）。下载链接必须同时覆盖 macOS 和 Windows，有 Linux 版的也要列出。不要往里放论文、教程等「推荐阅读」。
- 首页极简：页眉左右贴屏幕两端（全宽），屏幕中央一句「Attention is all you need」撑满剩余高度；没有标题、介绍或卡片。导航：AI从入门到精通 / Resource / 登录（无「关于」页）。新增板块 = 新增一个页面 + 导航里加一项 + 若需登录则在 Access 应用里加该路径。
- 课程与资源页必须登录才能看（Cloudflare Access），首页公开。
- Resource 页顺序固定：**Codex → Claude → FlClash → door4ai.com**（`src/data/resources.ts` 的数组顺序）。每个软件的卡片在一行里以 3D 转盘（`.ccar`）排列：拖动旋转、惯性、松手吸附、点击侧边卡转到正面、正面卡点击即下载、键盘左右键可切换。**初始正面是该软件的第一张 macOS 卡**（`data-start`），超过 ±80° 的卡隐藏。
- Resource 页：每个软件一个分组（标题 + 说明），**每个平台的下载按钮本身是一张 HoloCard 全息卡**：卡面布局：顶部小号软件 logo + 软件名，中间**大号平台图标**（macOS 苹果 / Windows 田字 / Linux 企鹅 / Android 机器人，`public/logos/apple|windows|linux|android.svg`，取自 Font Awesome Free 6，CC BY 4.0），图标下平台名，底部「点击下载」。软件 logo：flclash.png 来自 FlClash 仓库，openai.svg / claude.svg 来自 @lobehub/icons-static-svg（MIT），door4ai.svg 即本站 favicon。平台→图标的映射在 `resources.astro` 的 `platformLogo()`；没有匹配平台（如 door4ai 的「打开」）时中间放软件 logo。箔纹颜色跟随品牌色：`look` 表里每个软件配 logo / preset / accent（光晕、边框）/ foil（箔片色），着色器新增 `uTint`（data-tint，默认 0.65）把彩虹箔向品牌色拉。卡下小字显示版本 · 大小 · 同步日期。
- 安装包由本站 R2 镜像、仅登录用户可下（/dl 在 Access 内）。Codex 桌面版已并入新版 ChatGPT 桌面应用：macOS 镜像 `codex-app-prod/ChatGPT.dmg`，Windows 只有 Microsoft Store（不镜像，外链），Linux 为 CLI（外链）。新增镜像目标 = 在 `functions/_lib/sources.ts` 加一个 target，并在 `src/data/resources.ts` 加 `dl:` 按钮。
- 课程顺序：注意力 QKV（order 5）在前，KV Cache（order 10）在后，因为 KV cache 建立在 Q/K/V 概念上。课程目录的「第 N 讲」由 order 排序自动生成。

## 5. 当前状态

- [x] 仓库、Pages、域名、首篇文章全部上线（2026-10-13）
- [x] 本机 `~/Documents/Agents/door4ai-lab` 已与 GitHub 同步
- [x] 首页改为入口模块布局；新增 /ai/ 课程目录与 /resources/ 资源库（2026-10-13）
- [x] 安装包镜像上线并验证：12 个文件（FlClash v0.9.0 ×6、Claude 2.37337.1 ×5、Codex/ChatGPT.dmg ×1），登录后点击即下，支持断点续传（2026-10-14）
- [x] 新增《注意力里的 Q、K、V 到底在干什么》+「注意力实验室」六个实验，排为第 1 讲（order 5），KV Cache 顺延为第 2 讲（2026-10-14）
- [ ] 下一讲：题目未定（候选见第 7 节）
- [ ] 关于页只有两句话，待充实
- [ ] 没有统计/分析（可考虑 Cloudflare Web Analytics，免费，一行脚本）
- [ ] 没有评论、订阅、付费墙——课程售卖形态未定，先积累内容

## 6. 工作日志（倒序，每次工作追加一条）

- **2026-10-14 · Claude** — 新文章《注意力里的 Q、K、V 到底在干什么》（`src/content/blog/attention-qkv.md`，series ai-mastery，order 5）+ 实验页 `public/labs/attention-qkv/index.html`：00 箭头直觉 / 01 Q·K 二维对齐 + 因果遮罩 / 02 softmax 与 √d（真实随机高斯向量）/ 03 加权求和 V 与残差 / 04 多头弧线 / 05 头合并 + GPT-3、Llama-3-70B、Llama-3-8B 参数构成计算 / 06 MLP 与「迈克尔·乔丹」与门。按 3Blue1Brown 讲法。本地 build 通过，Playwright 检查桌面与 400px 无横向滚动、深浅色正常。因本人 Mac 中途断开，从云端会话直接推送；Mac 本地副本里有这两个文件的未跟踪副本（内容相同），pull 前删掉即可。

- **2026-10-14 · Claude** — 转盘初始居中到 macOS 卡；修复拖动失灵（卡片是 <a>+<img>，原生拖拽会取消指针事件，现在 dragstart 已阻止）；侧后方卡片隐藏、弧度放宽（min-slots 16）。针对 Safari 全息层只画在左上角小块的问题：画布尺寸改为从卡片元素本身量取并在加载后多次重测（待本人在 Safari 复核）。

- **2026-10-14 · Claude** — 卡面主图标改为平台图标（Apple / Windows / Linux Tux / Android，Font Awesome Free），软件 logo 缩小到顶部；HoloCard.astro 新增 `platformLogo` prop。

- **2026-10-14 · Claude** — 每个软件的卡片改为一行 3D 转盘（`src/scripts/circular-carousel.js`，仿 React Bits CircularCarousel：拖动/惯性/吸附/侧卡点击转正/弧形布局），顺序调整为 Codex、Claude、FlClash、door4ai.com；卡宽 170。本地 Playwright 验证拖动与初始居中。

- **2026-10-14 · Claude** — 卡面改为 logo 为主：加入 `public/logos/`（FlClash 官方图标、OpenAI / Claude 图标取自 lobehub icons 包、door4ai 用本站 favicon），HoloCard.astro 在构建时把 logo 内嵌进卡面 SVG；着色器加 `uTint` 让箔纹颜色贴合各品牌色（FlClash 蓝、Codex 银白、Claude 橙、door4ai 蓝金）。

- **2026-10-14 · Claude** — 按本人澄清改为「下载按钮即全息卡」：HoloCard.astro 支持 `href`（整卡是链接）、kicker/foot 文案；resources.astro 改为分组 + 卡片行。
- **2026-10-14 · Claude** — Resource 页改为 React Bits 风格的 HoloCard 全息卡片：把 HoloCard 的 WebGL 着色器与弹簧动画移植成无框架版本（`src/scripts/holo-card.js`），新建 `src/components/HoloCard.astro`（卡面 SVG 自动生成），`resources.astro` 改为卡片网格 + 卡下按钮；本地 Playwright 截图验证 4 张卡都渲染出全息效果。

- **2026-10-14 · Claude** — 镜像首次全量同步完成并在登录态下验证下载（206 Range、正确文件名）。途中修复：GitHub 匿名 API 在 Cloudflare 出口 IP 上会 403 → FlClash 改由 `/releases/latest` 重定向解析版本、API 仅用于 sha256 且带 10 分钟缓存；claude.ai 的 latest 重定向不接受 HEAD → 改 GET 后立即取消正文。Resource 页对无语义版本号（Codex 只有 ETag）显示「最新」。

- **2026-10-14 · Claude** — 安装包镜像上线：开通 R2、建桶 `door4ai-lab-dl`、绑定 `DL`、设 `SYNC_KEY`；新增 Pages Functions（/dl、/sync-dl）；Resource 按钮改为本站下载并显示版本/大小/同步日期；Access 应用加 `/dl` 路径。Codex 发现已并入 ChatGPT 桌面应用，按此处理。

- **2026-10-14 · Claude** — Resource 平台按钮去掉 ↗ 箭头（`src/pages/resources.astro`）。

- **2026-10-13 · Claude** — (1) 登录门禁：新建 Cloudflare Access 应用「Door4AI Lab」保护 /ai /resources /posts /labs，策略「Door4AI Lab students」仅放行本人邮箱，会话 1 个月；导航「关于」改为「登录」，登录后显示邮箱 + 退出；删除 about.astro。(2) 布局：页眉/页脚全宽贴两端，首页 motto 用 flex 撑满剩余视口，字号上限提到 96px。

- **2026-10-13 · Claude** — 背景色改为深色纯黑 / 浅色米白（Base.astro 与 KV 实验页同步）。

- **2026-10-13 · Claude** — 首页再简化：去掉 h1 和两张入口卡片，屏幕中央只剩居中的「Attention is all you need」（all 为斜体强调色）；入口统一走右上角导航。删除 `.hero/.entries/.entry` 样式，新增 `.motto-only/.motto`。

- **2026-10-13 · Claude** — 首页标题下的介绍段和 eyebrow 删除，只保留一句 motto「Attention is ALL you need」（`src/pages/index.astro`，样式 `.hero .motto`）。

- **2026-10-13 · Claude** — 按本人要求重做 Resource：删掉自行添加的论文/教程，只保留 FlClash、Codex、Claude 三个下载入口（各列 macOS / Windows / Linux，FlClash 另有 Android）和 door4ai.com。链接经核实（FlClash GitHub releases latest；Codex 桌面应用 chatgpt.com/codex，Linux 为 CLI；Claude 官方直链 + Linux beta 文档）。改 `src/data/resources.ts`、`src/pages/resources.astro`、Base.astro 样式、首页卡片文案。

- **2026-10-13 · Claude** — 首页重构为门厅（项目名 + Course / Resource 两个入口卡片）；新增 `src/pages/ai.astro`（课程目录）、`src/pages/resources.astro` + `src/data/resources.ts`（资源库，7 条）；schema 加 `series`/`order`；导航改为 AI从入门到精通 / Resource / 关于。本地 build 通过，push 后线上验证通过。

- **2026-10-13 · Claude** — 从零搭建：Astro 骨架、首篇文章 + KV Cache 实验室、推送到 GitHub、Cloudflare Pages 接入、绑定 lab.door4ai.com、验证上线。创建本 HANDOFF 与 CLAUDE.md / AGENTS.md。

## 7. 下一步建议（接手者可直接挑一个做）

1. 下一篇实验文章。Attention 已完成。候选：Tokenizer 实验（BPE 合并过程逐步演示）；LoRA 低秩微调为什么省参数（和 MLA 的低秩思想一脉相承）。
2. 给文章列表加按 tag 过滤。
3. 加 Cloudflare Web Analytics。

---

## 更新协议（强制）

每次工作结束前，接手的 AI 必须：

1. 更新顶部「最后更新」时间和更新者。
2. 第 5 节「当前状态」：勾掉完成项，补新待办。
3. 第 6 节「工作日志」：在最上方追加一条，格式 `**日期 · 谁** — 做了什么、改了哪些文件、线上是否验证`。
4. 若改了基础设施（DNS、Pages 设置、仓库授权、依赖版本），同步改第 2、3 节。
5. 若做了新的方向性决定，写进第 4 节。
6. 把 HANDOFF.md 和代码一起 commit、push 到 `main`。

本人（周业闰）口头或书面要求的变更优先级高于本文件；但变更后仍须回写本文件。
