# HANDOFF — Door4AI Lab (lab.door4ai.com)

> 这份文件是本项目的唯一交接入口。任何 AI 或人接手时**先读完本文件**，再动手。
> 任何一次工作结束前，**必须**按文末「更新协议」更新本文件并提交。没有更新 HANDOFF 的工作视为未完成。

最后更新：2026-10-13 20:32 America/New_York · 更新者：Claude（会话 session_017nqPj8MzXKK8YfLau84Y55）

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
│   ├── data/resources.ts   ← Resource 页的条目（分 section，每条 title/url/note）
│   ├── layouts/Base.astro  ← 全站布局 + 全部 CSS（颜色 token、字体、深浅色、入口卡片）
│   └── pages/
│       ├── index.astro         ← 首页 = 门厅：项目名 + 入口模块（Course / Resource）
│       ├── ai.astro            ← 「AI 从入门到精通」课程目录：series == 'ai-mastery' 的文章按 order 排序
│       ├── resources.astro     ← Resource 资源库，数据来自 src/data/resources.ts
│       ├── posts/[...slug].astro ← 文章页；frontmatter 有 lab 时顶部 iframe 嵌入实验
│       ├── about.astro
│       └── rss.xml.js
└── public/
    ├── favicon.svg
    └── labs/<name>/index.html  ← 独立实验页，完整 HTML，自带全部 CSS/JS
```

### 写一篇新文章的标准流程
1. 实验页：写成单文件 HTML（内联 CSS/JS，可用 cdnjs 等 CDN 加载库），放到 `public/labs/<slug>/index.html`。
2. 文章：`src/content/blog/<slug>.md`，frontmatter 写 `lab: /labs/<slug>/`；属于课程的写 `series: ai-mastery` 和 `order: <数字>`（10、20、30… 留空隙便于插入）。不写 series 的文章不会出现在课程目录里。
   - 加资源：编辑 `src/data/resources.ts`，不需要新建页面。
3. 本地 `npm run build` 必须通过。
4. commit → push `main` → 等 1–2 分钟 → 打开 https://lab.door4ai.com 验证文章页和实验页都能打开。
5. 更新本文件第 5、6 节。

### 实验页设计规范（沿用第一篇）
- 颜色用 CSS token（`--bg --paper --fg --muted --line --accent --warn --ok`），深浅色都要定义，`body` 必须有显式背景色。
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
- 首页是「门厅」而不是文章流：只放项目名和入口模块。目前两个入口：「AI 从入门到精通」（课程，按讲排序）和「Resource」（资源库）。新增板块 = 新增一张入口卡片 + 一个页面。

## 5. 当前状态

- [x] 仓库、Pages、域名、首篇文章全部上线（2026-10-13）
- [x] 本机 `~/Documents/Agents/door4ai-lab` 已与 GitHub 同步
- [x] 首页改为入口模块布局；新增 /ai/ 课程目录与 /resources/ 资源库（2026-10-13）
- [ ] 第 2 讲：题目未定
- [ ] Resource 目前只有 7 条，随课程扩充
- [ ] 关于页只有两句话，待充实
- [ ] 没有统计/分析（可考虑 Cloudflare Web Analytics，免费，一行脚本）
- [ ] 没有评论、订阅、付费墙——课程售卖形态未定，先积累内容

## 6. 工作日志（倒序，每次工作追加一条）

- **2026-10-13 · Claude** — 首页重构为门厅（项目名 + Course / Resource 两个入口卡片）；新增 `src/pages/ai.astro`（课程目录）、`src/pages/resources.astro` + `src/data/resources.ts`（资源库，7 条）；schema 加 `series`/`order`；导航改为 AI从入门到精通 / Resource / 关于。本地 build 通过，push 后线上验证通过。

- **2026-10-13 · Claude** — 从零搭建：Astro 骨架、首篇文章 + KV Cache 实验室、推送到 GitHub、Cloudflare Pages 接入、绑定 lab.door4ai.com、验证上线。创建本 HANDOFF 与 CLAUDE.md / AGENTS.md。

## 7. 下一步建议（接手者可直接挑一个做）

1. 第二篇实验文章。候选：Attention 可视化（q·k 点积 → softmax → 加权和，逐步动画）；Tokenizer 实验（BPE 合并过程逐步演示）；LoRA 低秩微调为什么省参数（和 MLA 的低秩思想一脉相承）。
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
