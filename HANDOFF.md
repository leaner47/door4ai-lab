# HANDOFF — Door4AI Lab (lab.door4ai.com)

> 这份文件是本项目的唯一交接入口。任何 AI 或人接手时**先读完本文件**，再动手。
> 任何一次工作结束前，**必须**按文末「更新协议」更新本文件并提交。没有更新 HANDOFF 的工作视为未完成。

最后更新：2026-10-22 13:20 America/New_York · 更新者：Claude（会话 session_017BBX6F9xKreqTAVSmrMzpE）

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
| 登录/访问控制 | **自建账号系统（2026-10-14 起生效）**：邮箱验证码 / Passkey / 可选两步验证，每账号 1 个会话，门禁规则见第 4 节。旧 Access 应用「Door4AI Lab」及其学员白名单已删除。**加学员 = 后台 /admin →「用户 → 开通课程」**。Cloudflare Access 只保留应用 **Door4AI Lab Admin**（`lab.door4ai.com/admin` + `/api/admin`，策略 Only me）。`*.pages.dev` 仍由 `functions/_middleware.ts` 301 到 `lab.door4ai.com`。不要改 grafana / AI Gateway Admin 两个应用和「Only me」策略。 |
| 安装包镜像 | R2 桶 `door4ai-lab-dl`（APAC 位置提示，私有），绑定到 Pages 项目为 `DL`；Pages 环境变量 `SYNC_KEY`（手动同步口令，值只在 Cloudflare 设置里）。下载走 `/dl/<app>/<platform>`（在 Access 保护内），状态看 `/dl/manifest.json`；手动同步 `GET /sync-dl?key=<SYNC_KEY>[&app=flclash\|claude\|codex][&force=1]`（/sync-dl 不在 Access 内，靠口令保护）。下载时若某项超过 24h 未同步会在后台自动刷新。 |
| GitHub App | Cloudflare Workers and Pages 已授权仓库：`door4ai-lab`、`door4ai-site`（后者是别的项目，不要动） |
| 自建账号（第 0 期，代码已上线、**默认关闭**） | 开关：Pages 环境变量 `AUTH_ENABLED=1` **且** 绑定了 D1（binding 名 `DB`，库名 `door4ai-lab`）才启用；否则中间件什么都不做，仍由上面的 Cloudflare Access 把关。其他变量：`ADMIN_EMAILS`（逗号分隔，这些邮箱视为拥有全部权益）、`RESEND_API_KEY`（Secret）+ `MAIL_FROM`（发验证码邮件，建议在 Resend 验证 `lab.door4ai.com` 子域，避免动根域名记录）、`TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET`（Secret，登录页人机校验）、`TOTP_ENC_KEY`（Secret，base64 的 32 字节随机数，加密存储两步验证密钥；不设则不提供两步验证；**设了之后不能换，换了已开启两步验证的用户全部失效**）、`ACCESS_TEAM_DOMAIN`（如 `xxx.cloudflareaccess.com`）+ `ACCESS_AUD`（/admin 所在 Access 应用的 AUD Tag）。**后台 `/admin`**：必须在 Access 应用里保护 `/admin` 路径（只放行本人），中间件再验 Access JWT 并核对 `ADMIN_EMAILS`，两层都过才进。表结构 `migrations/0001_init.sql`，用 `npx wrangler d1 execute door4ai-lab --remote --file migrations/0001_init.sql` 建表。启用并验证后，再从 Access 应用里移除 `/ai` `/resources` `/posts` `/labs` `/dl`（顺序反了课程会短暂公开）。**仓库里不能放 wrangler.toml**：它会覆盖控制台里的 `DL`、`SYNC_KEY` 等绑定；本地测试脚本只临时生成、退出即删（已加入 .gitignore）。 |
| 本机副本 | `~/Documents/Agents/door4ai-lab`（Mac），是 GitHub 仓库的 clone |

账号登录：Cloudflare 和 GitHub 都由本人登录；AI 不持有、不输入任何密码。需要 sudo/passkey 验证时交给本人操作。

## 3. 技术栈与目录结构

Astro 5 静态站，无 UI 框架，无 Tailwind。依赖只有 `astro`、`@astrojs/rss`、`@astrojs/sitemap`、`qrcode`（构建时生成 WhatsApp 群二维码 SVG），以及公式排版用的 `remark-math` + `rehype-katex` + `katex@0.16.47`。

**公式（2026-10-19 起）**：文章 markdown 里写 LaTeX，行内 `$...$`、独立 `$$...$$`，构建时由 rehype-katex 渲染；**正文里的美元金额必须写成 `\$`**（否则会被当成公式）。实验页用本站自带的 KaTeX：`<link rel="stylesheet" href="/vendor/katex/katex.min.css">` + `/vendor/katex/katex.min.js` + `auto-render.min.js`，分隔符 `\( \)`（行内）与 `\[ \]`（独立），JS 里拼出的公式用 `katex.renderToString`。`public/vendor/katex/` 是从 `node_modules/katex/dist` 复制的（只留 woff2 字体，CSS 里删了 woff/ttf 引用），**版本必须与 rehype-katex 依赖的 katex 一致**（现为 0.16.47；版本不一致时文章里的上下标会错位）。升级 rehype-katex 后要重新复制。

```
door4ai-lab/
├── HANDOFF.md              ← 本文件
├── .claude/skills/write-lesson/ ← 项目专用 skill「写一讲教材」：SKILL.md + templates/（lab.html、scene.py、article.md）
├── manim-src/              ← Manim 动画源码：door4ai_style.py（统一配色/字体/工具函数）、manim.cfg、<slug>/scenes.py；渲染缓存 media/ 不入库
├── CLAUDE.md / AGENTS.md   ← 指向本文件的强制说明（给各家 AI 工具读）
├── README.md               ← 面向人的简短说明
├── astro.config.mjs        ← site: https://lab.door4ai.com, sitemap（排除 /login/ /account/）
├── migrations/0001_init.sql ← D1 全部表（账号、Passkey、会话、来源、商品、订单、支付、权益、审计）
├── scripts/gen-access-map.mjs ← 构建前运行：从文章 frontmatter 生成 functions/_lib/access-map.ts（门禁用）
├── scripts/test-auth.sh + test-auth-e2e.mjs + test-admin-jwt.mjs ← 账号系统本地测试：端到端 43 项（Passkey 虚拟验证器、单会话踢下线、两步验证与防重放、恢复码、后台开通/撤销/下线/渠道码）+ Access JWT 校验 9 项。运行：`CHROMIUM_PATH=… bash scripts/test-auth.sh`
├── src/
│   ├── content.config.ts   ← 文章 schema：title, description, pubDate, updatedDate?, tags[], lab?, series?, order?, access?（free = 登录即可看；不写则课程文章需购买）
│   ├── content/blog/*.md   ← 文章正文（markdown）
│   ├── components/HoloCard.astro ← 全息卡片（移植自 React Bits HoloCard，MIT + Commons Clause）；卡面是由 props 生成的 SVG
│   ├── scripts/holo-card.js / .css ← HoloCard 的 WebGL 着色器与交互（原版去 React 化）
│   ├── data/course.ts      ← 课程分篇（基础篇 / 模型篇），按 order 区间自动归篇；新开一篇在这里加
│   ├── data/community.ts   ← WhatsApp 交流群名称与邀请链接（url 置空 = 全站隐藏入口）
│   ├── components/WhatsAppJoin.astro ← 群入口：menu（头像下拉菜单里的可展开项，电脑端带二维码，登录后才显示）/ inline（课程文章末尾一行）
│   ├── data/resources.ts   ← Resource 页的条目（link.dl = 镜像 id 走 /dl/，link.url = 外链）
│   ├── layouts/Base.astro  ← 全站布局 + 导航 + 全部 CSS；右上角头像按钮下拉菜单（邮箱 / 个人资料 / 外观 / 退出登录，未登录时首项为「登录」），登录状态先调 /api/me（自建账号启用时用它），否则回退到 /cdn-cgi/access/get-identity；全局 `[hidden]{display:none!important}`；prop `full` 让 main 占满宽度（首页用）
│   └── pages/
│       ├── index.astro         ← 首页：只有居中的一句 motto，入口全在导航
│       ├── ai/apply.astro      ← /ai/apply/「AI账号申请」：学员填表 + 我的申请；管理员看全部并改状态（同一页）
│       ├── ai.astro            ← 「AI 从入门到精通」课程目录：series == 'ai-mastery' 的文章按 order 排序
│       ├── resources.astro     ← Resource 资源库，数据来自 src/data/resources.ts
│       ├── admin.astro         ← 后台：概览（注册数、来源与转化、问卷、每日注册）/ 用户（搜索、详情、开通/撤销、强制下线、停用、重置两步验证）/ 渠道码（链接 + 二维码 + 注册/付费统计）/ 操作日志
│       ├── login.astro / account.astro / pricing.astro ← 登录（邮箱验证码 + Passkey + 两步验证）/ 我的账号（两步验证开关、恢复码、Passkey 管理、已购课程、推荐链接、来源问卷）/ 购买页（支付未开放，占位）
│       ├── posts/[...slug].astro ← 文章页；frontmatter 有 lab 时整宽无边框嵌入实验（实验自带标题），下面接正文
│       └── rss.xml.js
├── functions/              ← Cloudflare Pages Functions（随仓库自动部署）
│   ├── _lib/sources.ts     ← 镜像源：每个 target 的 resolve()（FlClash=GitHub latest；Claude=官方 latest 重定向 + apt 索引；Codex=codex-app-prod/ChatGPT.dmg）
│   ├── _lib/mirror.ts      ← 同步逻辑：解析→下载→流式写入 R2→更新 manifest.json
│   ├── ai/apply/api.ts     ← AI账号申请接口（GET 列表 / POST 提交 / PATCH 管理员改状态），记录存 R2 `DL` 的 `apply/<id>.json`
│   ├── dl/[[path]].ts      ← /dl/manifest.json 与 /dl/<app>/<platform> 下载（支持 Range 断点续传）
│   ├── sync-dl.ts          ← 手动同步入口
│   ├── _middleware.ts      ← pages.dev 跳转 + 自建账号门禁（AUTH_ENABLED 时）+ 注册来源 Cookie
│   ├── _lib/auth/          ← totp（RFC 6238 + AES-GCM 加密存储 + 恢复码）、mfa（邮箱验证码后的第二步票据）、admin（Access JWT 校验）、util（ID/哈希/Cookie/限流）、session（单会话、用户、权益）、attribution、gate（路径→要求）、webauthn、mail（Resend）、turnstile
│   ├── _lib/access-map.ts  ← 自动生成，勿手改
│   └── api/auth/*、api/me/*、api/admin/* ← otp / verify / mfa / logout / config / passkey 四个端点；me、me/passkeys/[id]、me/survey、me/totp/[setup|enable|disable|recovery]；admin/[stats|users|user|grant|revoke|ban|logout|totp-reset|channels|channel|audit|whoami]
└── public/
    ├── favicon.svg
    └── labs/<name>/index.html  ← 独立实验页，完整 HTML，自带全部 CSS/JS
```

### 写一篇新文章的标准流程
**本人提出一个问题要写成教材时，按项目 skill `.claude/skills/write-lesson/SKILL.md` 做**（一小步一小步的图文讲解 + 实验页 + 上线 + 更新本文件；不做视频）。样板：注意力一讲——`labs-src/<slug>/toy.py` 算出贯穿全文的小例子、生成静态 SVG 图，并把 `article.src.md` 里的 `{{figN}}` 填好写到 `src/content/blog/<slug>.md`；改文章改 `article.src.md` 后重跑 `python3 labs-src/<slug>/toy.py`，不要直接改生成的 .md。实验页的玩具实验用同一组数字。下面是简版：
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
- **有实验的文章页 = 实验页本身的样子**（2026-10-15 本人要求，参照单独打开实验页的截图）：不加边框/底色/外框，iframe 占满页面宽度、随内容自动长高；文章页不再渲染自己的日期/标题/简介/标签（标题保留为读屏用的 `sr-only` h1），开头就是实验页自己的 eyebrow + 大标题 + 导语；实验下面接文章正文（`.post-body`，宽度与实验 `.wrap` 对齐：max 892px、左右 16px）。实验页标题区仍带 `class="lab-intro"` 和嵌入检测片段（`html.embedded` 类 + 读 `d4a-theme`），但**嵌入时不再隐藏**。没有实验的文章仍是原来的标题 + 正文版式。

## 4. 已做的关键决定（不要反复讨论）

- **Manim 可视化（2026-10-16）**：动画源码放 `manim-src/<slug>/scenes.py`，统一导入 `manim-src/door4ai_style.py`（背景 `#111214`、强调色 `#6f9cf0`、中文苹方/Noto CJK、数字 Times New Roman）。产物 `public/videos/<slug>/<Scene>.webm` + 同名 `.png` 海报，用 `<figure class="clip"><video …>` 嵌入文章或实验页（`Base.astro` 与实验页模板都有 `.clip` 样式）。渲染在云端工作区装 Manim（Python 3.12 + `libpango1.0-dev` + `dvisvgm`，步骤见 skill）；本人 Mac 的 `~/.venvs/manim` 不在可用 shell 里。参考文档：claude.ai 项目里的 `manim/使用说明.md`。
- **【总规矩】公式按标准数学排版**（2026-10-19 本人要求：公式一定要跟平时书写见到的一样，不要让用户去想式子写出来是什么样子）：用 KaTeX 写成教科书里的样子（分数线、上下标、根号、求和号、斜体变量），不要用 `QKᵀ/√d`、`W<sub>Q</sub>·x`、`e^s / Σ e^s` 这类纯文本或 HTML 拼法。SVG 图里的变量用斜体 tspan（`mt()` 小工具），带下标的用 baseline 偏移。窄屏放不下的长公式拆成两行（`aligned` 或两个独立公式）。写法见第 3 节。**现有其他讲的 HTML 公式尚未迁移**（见第 5 节待办）。
- **【总规矩】图文为主、一小步一小步讲（2026-10-21 本人纠正）**：「3b1b 风格」指画面风格——图干净、同一概念同一颜色、文章里的图与实验交互图同一套画法——**不是插视频**。本人偏好图文：学习需要思考，思考需要停顿。讲解要细到读者不用自己推演：一步只引入一个新东西、推导不跳步、每个公式配真实数字算例且整讲沿用同一组数字、先具体后一般、每步配一张静态分镜图（内联 SVG，颜色只用 CSS 变量）、关键处可放 `<details class="pause">` 「停一下」。完整规范见 skill `write-lesson` 第 4、5 节，模板 `templates/figure.svg`。`Base.astro` 已加 `--warn/--ok` 色、`figure.fig`（最宽 760px、最高一屏 62%）与 `details.pause` 样式。**新课不再做 Manim 视频**；现有各讲里的视频与讲解粒度待按新标准改写（见第 5 节）。
- **【总规矩】不用横线分隔内容**（2026-10-17 本人：线分割太生硬，深色背景下尤其难看）：页面分段、列表项之间靠留白区分；需要强调某一项时用圆角浅底（`var(--paper)`）而不是加线。页眉、页脚、课程列表、翻页、Resource 分组都已去掉分隔线。表格行线、菜单内分隔、卡片外框不算分隔线。
- **【总规矩】科学单位一律用英文缩写**（2026-10-16 本人要求）：s、ms、μs、m、km、kg、Hz、W 等，数字与单位空一格（`300 s`、`204 km/ms`、`1 TB/s`、`token/s`）；正文、实验页、JS 拼出的读数、Manim 画面都一样。「秒级」这类量级说法可保留。
- **【总规矩】教材里不出现指向本人的个人信息**（2026-10-16 本人要求）：不用本人所在/家乡城市（如扬州、高邮、波士顿）、学校、真名、GitHub 用户名、邮箱、自家设备/服务器等做例子。需要城市就用北京、上海、合肥、纽约这类中性城市；需要用户名用 `your-name`；本站域名 `lab.door4ai.com` 作为课程网站自身的例子可以用。
- **【总规矩】保持简洁，不要主动加说明性小字**（2026-10-16 本人明确要求）：不加 eyebrow 小标签、副标题、导语/说明句、计数（如「第一篇 · 4 讲」）、注释类灰字，除非本人要求进一步补充说明。新页面、新组件默认只放标题和必要内容。
- `door4ai-lab.pages.dev` 及预览地址一律跳转到 `lab.door4ai.com`（代码里的中间件实现，不在控制台配置），避免绕过登录。
- 术语「token」直接用英文，不译成「词」「词元」。
- 课程顺序：硬件入门讲（computer-anatomy，order 2）放在注意力（order 5）之前，作为零基础第一课。
- 生成型实验页（由脚本产出的 HTML）把生成脚本放在 `labs-src/<slug>/`，产物仍放 `public/labs/<slug>/index.html`。
- 域名用子域名 `lab.door4ai.com`（door4ai.com 根域名有正在运行的业务；matrix-tech-inyz.com 留给公司）。
- 博客放子域名而非 `blog.`，取 `lab` 呼应「实验室」定位。
- 不加 license；仓库 public。
- 用 Astro + Cloudflare Pages，不自建服务器。
- 实验页用独立 HTML + iframe 嵌入，而不是做成 Astro 组件——便于把同一个 HTML 作为 Claude artifact 预览、也便于全屏分享。
- **Resource 页只放本人指定的内容**（目前：FlClash、Codex、Claude 的下载入口 + door4ai.com）。下载链接必须同时覆盖 macOS 和 Windows，有 Linux 版的也要列出。不要往里放论文、教程等「推荐阅读」。
- **首页只有一句「Attention is *all* you need」**（2026-10-14 本人要求）：没有页眉、导航、头像菜单和页脚（`Base` 的 `bare` prop），整页是一个指向 `/ai/` 的链接，点任意位置进入课程目录。不要再往首页加任何东西。顶部导航只有「AI从入门到精通」；**Resource 入口在右上角头像菜单里**（本人要求，不放顶部导航），登录/退出也在头像菜单里（无「关于」页）。新增板块 = 新增一个页面 + 导航里加一项 + 若需登录则在 Access 应用里加该路径。
- 课程与资源页必须登录才能看（Cloudflare Access），首页公开。
- Resource 页顺序固定：**Codex → Claude → FlClash → door4ai.com**（`src/data/resources.ts` 的数组顺序）。**Resource 页没有页面大标题**（去掉了居中的「Resource」h1）；**每个软件名居中显示**；**不写任何介绍文字**：没有页面导语、没有软件说明段、卡片下方没有版本/大小小字（版本与大小只放在卡片 title 悬停提示里）。`resources.ts` 里的 `note` 字段保留但页面不渲染。每个软件的卡片在一行里平铺（`.cardrow`：flex + 横向滚动 + scroll-snap，放得下时居中，放不下时左右平滑滑动）。**不要再做 3D 转盘**，本人已明确否决。
- Resource 页：每个软件一个分组（标题 + 说明），**每个平台的下载按钮本身是一张 HoloCard 全息卡**：卡面布局：顶部小号软件 logo + 软件名，中间**大号平台图标**（macOS 苹果 / Windows 田字 / Linux 企鹅 / Android 机器人，`public/logos/apple|windows|linux|android.svg`，取自 Font Awesome Free 6，CC BY 4.0），图标下平台名，底部「点击下载」。软件 logo：flclash.png 来自 FlClash 仓库，openai.svg / claude.svg 来自 @lobehub/icons-static-svg（MIT），door4ai.com 的卡片 logo 是文字「AI」（`public/logos/ai-text.svg`，Times New Roman 粗体，本人指定，不用 favicon）。平台→图标的映射在 `resources.astro` 的 `platformLogo()`；没有匹配平台（如 door4ai 的「打开」）时中间放软件 logo。箔纹颜色跟随品牌色：`look` 表里每个软件配 logo / preset / accent（光晕、边框）/ foil（箔片色）/ intensity / tint。**Codex 定稿为黑金**（黑底 + 金色箔纹，accent #9a7a2a，foil #f6d27a，intensity 0.55，tint 0.95），本人明确要求。**箔纹统一用 `shards`（碎片纹）**：本人否决了 glitter 的细碎点阵，Codex / Claude / FlClash 三者纹路必须一致（door4ai.com 用 gold）。着色器新增 `uTint`（data-tint，默认 0.65）把彩虹箔向品牌色拉。卡下小字显示版本 · 大小 · 同步日期。
- **Safari / iOS 注意（全息层只画在卡片左上角一小块）**：真正的原因是 WebKit 的 `texImage2D()` 从 SVG `<img>` 上传纹理时，用的是该 SVG 在页面上**显示尺寸**（170px 海报图）的栅格缓存，而不是 SVG 固有尺寸 630×880，于是整张卡面被塞进纹理左上角约 27%（=170/630）的区域。iPhone `#debug` 数据证明 CSS 盒、drawingBuffer、viewport 全部正确，所以**不是尺寸问题，别再在 CSS/resize 上找**。修法在 `holo-card.js` 的 `img.onload`：先把 SVG `drawImage()` 到一张 630×880 的 2D canvas，再把这张 canvas 交给 `texImage2D`（drawImage 对 SVG 总是按目标尺寸重新渲染）。保留的防御措施：画布缓冲区在标记里固定为 CSS 尺寸 2 倍（`<canvas width height>`），JS 不在首次绘制后改 canvas.width/height。Safari 对 HTML 缓存很顽固，看不到新版本先 ⌘⇧R / iPhone 清站点数据。
- 安装包由本站 R2 镜像、仅登录用户可下（/dl 在 Access 内）。Codex 桌面版已并入新版 ChatGPT 桌面应用：macOS 镜像 `codex-app-prod/ChatGPT.dmg`，Windows 只有 Microsoft Store（不镜像，外链），Linux 为 CLI（外链）。新增镜像目标 = 在 `functions/_lib/sources.ts` 加一个 target，并在 `src/data/resources.ts` 加 `dl:` 按钮。
- **WhatsApp 交流群「AI学习」**：**入口在右上角头像菜单里**（「WhatsApp 交流群 ›」，点开显示二维码 + 加入按钮；手机宽度只显示按钮；只在登录后显示）+ 属于课程的文章末尾一行。课程目录页不再放群卡片（本人要求移进菜单）。链接用干净的邀请地址（去掉 `?s=cl&p=i…` 分享参数）。入群需管理员审核（WhatsApp 里设置）。**重置群链接后只需改 `src/data/community.ts` 再推送**，二维码会随构建自动更新。
- 文章页实验 iframe **必须随内容自动长高、不得有内部滚动条**，也不要「全屏打开」条（本人要求）。实验页本身别用 100vh 之类固定高度。
- **右上角账号区（2026-10-14 本人要求，仿常见 SaaS 样式）**：导航链接之后只有一个圆角方形头像按钮（**不要「支持」入口**，本人已明确去掉）；点开下拉菜单：已登录时顶部显示邮箱，下面「个人资料」（仅自建账号启用时显示，链 /account/）、「Resource」（链 /resources/，登录与否都显示）、「AI账号申请」（链 /ai/apply/）、「WhatsApp 交流群 ›」（登录后才显示）、「外观 ›」（展开为 跟随系统 / 浅色 / 深色）、分隔线、「退出登录」；未登录时首项为「登录」。截图里的 Language / View mode 没做（站点只有中文、无其他视图），需要时再加。Esc 和点外部关闭。
- **外观切换**：存 localStorage `d4a-theme`（light / dark，缺省 = 跟随系统），`<head>` 里内联脚本在渲染前设 `<html data-theme>`，避免闪烁。CSS token 写法：`@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){…} }` + `:root[data-theme="dark"]{…}`，**新增的深色样式都要照此两段写**。实验页同源，加载时读同一个键；切换时父页面直接改 iframe 的 `data-theme`（实验页已有 MutationObserver 重绘画布）。
- **AI账号申请（2026-10-14 本人要求）**：学员申请 ChatGPT / Claude 等账号（选项：ChatGPT Plus / ChatGPT Pro / Claude Pro / Claude Max / Gemini Advanced / 其他，选项列表在 `functions/ai/apply/api.ts` 与 `src/pages/ai/apply.astro` 两处，改时同步）。必填：账号、用途（≥10 字）、WhatsApp 或微信；备注可选；邮箱取登录身份（Access 的 `cf-access-authenticated-user-email` 头，自建账号启用后取会话）。同一邮箱 24h 最多 5 条。状态：待处理 / 已开通 / 未通过 + 一句回复（学员可见）。**管理员 = Pages 环境变量 `ADMIN_EMAILS` 里的邮箱**，同一页面看到全部申请并改状态；（已随账号系统启用设好）；也可在 R2 桶 `door4ai-lab-dl` 的 `apply/` 前缀下直接看 JSON。路径放在 `/ai/` 下是为了直接受现有 Access 保护；`gate.ts` 加了 `ai/apply → 需登录`。D1 开通后可把 R2 记录迁成表。没有邮件通知（Resend 未配置）。
- **排版统一（2026-10-16 本人要求「新章节多了，优化整体排版」）**：
  - **图形不能比屏幕大（2026-10-16 本人反馈 14 寸 MacBook Pro 上实验占比太大）**：所有实验页 `</body>` 前有一段「图形尺寸上限」脚本——每张图按宽高比收窄居中，高度 ≤ 视口 62%（最多 620px；在文章 iframe 里取外层视口），画布尺寸变了会触发一次 `resize` 让实验重画。文章正文里的 `.clip` 视频用 CSS 同样封顶。文字仍铺满。新实验页从 skill 模板起步自带这段，不要删。
  - **版面铺满（2026-10-16 本人要求）**：文字从左到右铺满，不设 max-width（不要 68ch / 892px 之类），只留左右页边距 `clamp(16px,3vw,40px)`，与页眉「Door4AI Lab」左边线对齐。`Base` 的 `main`、文章页 `.post-body`、所有实验页 `.wrap`（computer-anatomy 是 `main`）都按此。**新实验页 `.wrap{box-sizing:border-box;padding-inline:clamp(16px,3vw,40px);padding-block:40px 80px}`，开头 = `.eyebrow` + `h1`（`clamp(28px,5vw,40px)`，700）+ `.lede`，都带 `lab-intro` 类。** 表单页（登录、账号、购买、AI账号申请的表单）保留自己的窄宽度。
  - 课程目录按篇分组（**每篇只显示篇名**，没有「第 N 篇 · M 讲」、副标题和说明；页面顶部也没有 COURSE 和导语，只有大标题 + 学习记录面板）：`src/data/course.ts` 的 `PARTS`（order < 4 基础篇：电脑、网络、Git、Cloudflare；其余模型篇）。讲号全课程连续编号。
  - 文章页：有实验 → 整宽实验（自带标题）+ 正文；没实验 → 同一版心的标题区（eyebrow = 标签用 · 连接，h1 冒号后换行，lede = description）+ 正文。两种都不显示日期。
  - 每讲末尾：WhatsApp 一行 + 「← 上一讲 / 下一讲 →」翻页卡（同 series 按 order）。
- 课程目录 /ai：**每讲只显示大号编号 + 标题**（2026-10-16 本人要求：不要「第 N 讲 · 日期 · 含实验」元信息行、不要「从这里开始 / 已读 / 下一讲」标签、不要文章标签，也不要 description）。**不再有「已读」概念**（不记 d4a-read、编号不变灰不高亮）。顶部是 GitHub 贡献图式的「学习记录」面板：localStorage `d4a-activity` = {本地日期: 次数}，文章页每打开一次 +1，**重复读也算**；格子深浅 0 / 1 / 2–3 / 4–6 / 7+；汇总「过去一年学习 X 次 · Y 天 · 连续 Z 天」。只存本机浏览器，不做账号级记录。 面板宽度 = 格子宽度（`width:fit-content`），不铺满整行。
- 课程顺序：网络讲（internet-basics，order 2.5）放在硬件讲之后、Git 讲之前：先懂电脑，再懂电脑怎么连网，再讲 Git/GitHub。order 可以用小数插队。
- 网络讲的 DNS 污染部分直接点名「防火长城」（2026-10-15 本人决定），只讲原理和可观察的现象，不提供翻墙教程。
- 课程顺序：Token 讲（tokenizer-llm，order 4）放在硬件讲（2）和注意力讲（5）之间：先知道文字怎么变成 token、模型整体怎么跑，再拆开注意力。
- 课程顺序：数学讲（vectors-softmax，order 4.5）放在 Token 讲与注意力讲之间（2026-10-22 本人指定）：给没学过线性代数和概率的读者补齐点积、矩阵形状、softmax。**它的贯穿算例与注意力讲 `labs-src/attention-qkv/toy.py` 完全相同**（4 个 token、x、W_Q、W_K，分数 1.6 / 0.48 / 0.08 / 1.0，T = √2 即注意力的 ÷√d_k），改其中一讲的数字时两讲要一起改。
- 需要大数据表的实验（如分词器词表）把打包好的 JS 放在实验页同目录（`public/labs/<slug>/xxx.js`），同源、受同样的门禁保护；不依赖外部 CDN，国内访问更稳。
- 课程顺序：注意力 QKV（order 5）在前，KV Cache（order 10）在后，因为 KV cache 建立在 Q/K/V 概念上。
- 课程顺序（2026-10-22 本人指定）：推理服务（13）在量化（12）与 MoE（15）之间；过拟合（22）在梯度下降（20）与残差（25）之间；分布式训练（39）在 Scaling Laws（38）与 LoRA（40）之间；蒸馏（44）在推理模型（43）与模型评测（45）之间；扩散模型（50）为模型篇最后一讲；Agent 安全预定 132（Trace 与 Eval 130 与网关 135 之间）。
- 课程顺序：残差连接（order 25）紧接梯度下降（20）：讲深网络为什么训不动。
- 课程顺序：梯度下降（order 20）放在 KV Cache 之后：前面几讲讲推理，从这一讲开始讲训练（参数从哪来）；后续训练相关的讲（反向传播、LoRA 等）接在 20 之后。课程目录的「第 N 讲」由 order 排序自动生成。
- **MCP 讲按 2026-07-28 规范写**（2026-10-19 已核对官方 changelog）：无状态，去掉了 `initialize` 握手与 `Mcp-Session-Id`，新增 `server/discover`，结果必带 `resultType`，Streamable HTTP 请求必带 `Mcp-Method` / `Mcp-Name` 头；实验 01 可切回 2025-11-25 握手式对照。规范再更新时改 `public/labs/mcp/` 与文章。
- **课程文章里的表格与行内代码**（2026-10-19）：`Base.astro` 里 `.prose table` 在 ≤720px 时变为块级、表内横向滚动；行内 `code` 允许任意处断行（`overflow-wrap:anywhere`），避免长 API 名把手机页面撑宽。
- **课程三篇结构（2026-10-16 本人决定）**：基础篇（order < 4）→ 模型篇（4 ≤ order < 99）→ **Agent 篇（order ≥ 99）**（2026-10-22 起由 ≥ 100 改为 ≥ 99：`prompt-engineering` 排 99，作为 Agent 篇第一讲；`src/data/course.ts` 模型篇 `until: 99`）。Agent 篇的骨架参考了市面上一门 Agent 工程课的目录顺序（工具调用 → Loop → 上下文/记忆 → RAG → MCP → 流式 → Trace/Eval → 网关与编排 → 框架全景），采用的是"先手写、后看框架"的顺序，**不吸收**它的 Node/前端工程内容。本人决定：先立项写出全部讲，缺什么等他自学时发现再补；模型篇先补齐（反向传播 30、LayerNorm 35、LoRA 40、模型评测 45）再写 Agent 篇。

- **账号与计费（2026-10-14 本人确认）**：自建账号，D1 不用 PG；不设密码，Passkey 为主、邮箱验证码注册与兜底、TOTP 可选（未做）；每账号同一时间只允许 1 个会话，新登录踢掉旧会话；只做买断，不做订阅；买全套包含以后新增的讲；收款复用 door4ai.com 的 pay-api（接口文档待本人提供）；记录注册来源（首次/最后触达 UTM、ref 渠道码、来源问卷）。设计文档：https://claude.ai/code/artifact/9679fc7a-0fe4-4323-86f1-65cbb1cc005f
- 两步验证只在「邮箱验证码登录」时要求；Passkey 登录不需要（Passkey 本身就是强认证）。新注册的第一次登录不要求（还没开）。
- 后台不做自建管理员账号：身份来自 Cloudflare Access + `ADMIN_EMAILS`，所有写操作记 `audit_log`。
- 门禁规则：`/admin/` 走后台校验；`/` `/ai/` `/login/` `/pricing/` 公开；`/resources/` `/dl/` `/account/` 需登录；`/posts/<slug>/` 与对应 `/labs/<name>/` 按文章：`access: free` 登录即可，属于 series 的需要 `series:<name>` 或 `post:<slug>` 权益（或 `all`，或 ADMIN_EMAILS）。

## 5. 当前状态

- [ ] **按新标准改写现有各讲**（2026-10-21 本人反馈：步骤不够细、需要读者自行推演的地方多；不要视频）：本人定为全部、按课程顺序逐讲改。样板「注意力 Q、K、V」已完成（2026-10-21），**等本人看过样板再改其余各讲**；其余约 24 讲仍有 `figure class="clip"` 视频与 `manim-src/` 源，改到哪讲删哪讲的。

- [x] 仓库、Pages、域名、首篇文章全部上线（2026-10-13）
- [x] 本机 `~/Documents/Agents/door4ai-lab` 已与 GitHub 同步
- [x] 首页改为入口模块布局；新增 /ai/ 课程目录与 /resources/ 资源库（2026-10-13）
- [x] 安装包镜像上线并验证：12 个文件（FlClash v0.9.0 ×6、Claude 2.37337.1 ×5、Codex/ChatGPT.dmg ×1），登录后点击即下，支持断点续传（2026-10-14）
- [x] 新增《注意力里的 Q、K、V 到底在干什么》+「注意力实验室」六个实验，排为第 1 讲（order 5），KV Cache 顺延为第 2 讲（2026-10-14）
- [x] 注意力讲重写为一词多义主线 + Qwen3-0.6B 真实数据（00–07 八个实验 + 动画 ScaledDotProduct）；多头、参数量、MLP 移出，新增《MLP：注意力之后，每个词自己查一查》(order 8，4 实验)；全站接入 KaTeX（2026-10-19）
- [ ] 其他各讲里用 HTML/Unicode 拼的公式迁移到 KaTeX（本人要求公式按标准排版；目前只有 attention-qkv、mlp 两讲已迁移）
- [x] 新增入门讲《电脑里到底有什么：CPU、GPU、内存、显存与 Docker》+ 五个等距图解实验，排在课程最前（order 2）（2026-10-14）
- [x] 新增《Token 是什么：一句话是怎么进出大模型的》+「Token 实验室」七个实验（00–06），排为第 2 讲（order 4，在硬件讲与注意力讲之间）（2026-10-14）
- [x] 新增入门讲《Git 和 GitHub：代码的时光机与云端仓库》+「Git 实验室」五个实验，排为 order 3（硬件讲之后、Token 讲之前）（2026-10-15）
- [x] 新增入门讲《我们是怎么连上互联网的：IP、DNS、路由与 DNS 污染》+「网络实验室」七部分（00 比方 + 01–06 实验），order 2.5（2026-10-15）
- [x] 新增纯文字讲《Cloudflare 是做什么的：一张全球网络上的五类功能》（order 3.5，网络讲(2.5)与 Git 讲之后、Token 讲之前；无实验页，正文内嵌一张请求路径 SVG 图）（2026-10-16）
- [x] 新增《梯度下降是什么：模型是怎么把参数一点点调对的》+「梯度下降实验室」五个实验 + 两段 Manim 动画（Descent1D、Gradient2D），order 20，排在 KV Cache 之后，作为训练相关内容的第一讲（2026-10-16）
- [x] 新增《残差连接为什么必不可少：深网络是怎么训得动的》+「残差连接实验室」00–04 + 两段 Manim 动画（GradientHighway、ResidualStream），order 25，梯度下降之后（2026-10-16）
- [x] 模型篇补齐 4 讲（2026-10-16）：《反向传播是怎么算梯度的》(order 30，5 实验 + 2 动画)、《LayerNorm 为什么必需》(35，6 实验 + 2 动画)、《LoRA 为什么省参数》(40，6 实验 + 2 动画)、《模型怎么评测》(45，6 实验 + 2 动画)
- [x] Agent 篇前三讲（2026-10-19）：《大模型怎么调用工具》(order 100，6 实验 + 2 动画)、《Agent Loop》(105，6 实验 + 2 动画)、《上下文窗口是 Agent 的工作记忆》(110，6 实验 + 2 动画)
- [x] Agent 篇第 4–7 讲（2026-10-19）：《Embedding 与 RAG》(115)、《MCP》(120)、《流式输出》(125)、《Trace 与 Eval》(130)，各 6 实验 + 2 动画
- [x] 课程规划 14 讲全部上线（2026-10-19）：最后一批《AI 写代码是怎么回事》(3.8，5 实验 + 1 动画)、《多模型网关与多 Agent 编排》(135，6 实验 + 2 动画)、《Agent 框架全景》(140，纯文字)
- [x] 模型篇补充四讲（2026-10-19）：《多头注意力与 GQA》(order 7)、《模型量化》(12)、《MoE 混合专家》(15)、《RLHF 与偏好对齐》(42)，各 6 实验 + 2 动画
- [x] 新增《Harness 是什么：模型外面那层替它动手的程序》（order 107，Agent Loop 之后、上下文窗口之前，作为 Agent 篇总纲；5 实验 + 2 动画）；RLHF 讲末尾加「Agent 的强化学习」一节 + 实验 06（2026-10-19）
- [x] 新增《Scaling Laws：模型、数据、算力该怎么配》（order 38，预训练之后、LoRA 之前；按新标准图文写，8 张分镜图 + 实验 01–06；无视频）（2026-10-22）
- [x] 新增《后训练是什么：只会续写的基座模型，是怎么变成助手的》（order 41，LoRA 之后、RLHF 之前；按新标准图文写，贯穿算例「17 × 3」，7 张分镜图 + 实验 01–05；无视频）（2026-10-22）
- [x] 新增《推理模型：为什么让模型多想一会儿，答案会更好》（order 43，RLHF 之后、模型评测之前；按新标准图文写，贯穿算例「12 个一箱 × 3 箱 − 7」，9 张分镜图 + 实验 01–06；无视频）（2026-10-22）
- [x] 新增《Prompt 工程：怎么跟模型把话说清楚》（order 99，Agent 篇第一讲；按新标准图文写，贯穿算例「网店评论分好评 / 中评 / 差评」，8 张分镜图 + 实验 01–05；无视频）（2026-10-22）
- [x] 新增《AI 怎么浏览网页、操作电脑：眼睛、手和权限》（order 122，MCP 之后、流式输出之前；5 实验 + 1 动画）（2026-10-19）
- [x] 新增《向量、矩阵乘法与 softmax：读懂大模型需要的全部数学》（order 4.5，Token 讲之后、注意力讲之前；按新标准图文写，15 步、12 张分镜图、5 个「停一下」+ 6 个实验，无视频）（2026-10-22）
- [x] 新增《模型是怎么看图的：一张图怎样变成一串 token》（order 48，模型篇最后一讲；按新标准图文写，10 张分镜图 + 6 个实验，无视频）（2026-10-22）
- [x] 新增《位置编码与 RoPE：注意力怎么知道谁在前谁在后》（order 6，注意力讲之后、多头 GQA 讲之前；按新标准图文写，沿用注意力讲的四个 token，11 张分镜图 + 实验 01–05；无视频）（2026-10-22）
- [x] 新增《预训练是什么：模型是怎么从一大堆文字里学会说话的》（order 37，LayerNorm 之后、Scaling Laws(38) 与 LoRA 之前；按新标准图文写，贯穿算例「我爱吃米饭。」+ 7 token bigram，13 张分镜图、3 个「停一下」+ 实验 01–06，含页内真实训练的字符级小模型；无视频）（2026-10-22）
- [x] 并行补写模型篇三讲（2026-10-22，按新标准图文写，无视频）：《推理服务：一张卡怎么同时伺候几百个用户》(order 13，12 张分镜图 + 实验 01–05)、《过拟合与泛化：模型背熟了训练题，为什么还是会考砸》(22，17 张分镜图 + 实验 01–07)、《分布式训练：一张卡放不下的模型是怎么训出来的》(39，12 张分镜图 + 实验 01–05)
- [x] 并行补写第二批（2026-10-22，按新标准图文写，无视频）：《蒸馏：小模型怎么向大模型学》(order 44，9 张分镜图 + 实验 01–05，含页内老师→学生 MLP 真训)、《扩散模型：AI 是怎么从一片噪声里画出图的》(50，模型篇最后一讲，15 张分镜图 + 实验 01–06，含页内小网络真训与解析最优预测对照)
- [ ] **Agent 安全（agent-security，order 132）未完成**：写手中途一次回复被安全分类器拦下，主会话没有让别的写手接着生成，等本人决定重写（可收窄为防御分层与权限设计）还是不做。半成品（model.js、article.src.md 草稿）未入库，只在当时会话的临时目录里。
- [ ] reasoning-models（43）末段写「下一讲讲模型评测」，蒸馏（44）插入后已不准，由负责该讲的窗口改（本批未碰该讲文件）。
- [ ] 待补查（第一批并行写手标注的）：推理服务讲的 H100 3.35 TB/s 只对照了第三方汇总页；INT8 按每权重 8.125 位（组 128 + FP16 scale）是写手自设；Orca / SGLang 论文出处凭记忆。分布式训练讲 405B 气泡 48%（假设 m = 16）与每卡 6.7 GB 是推算；激活值 34sbh 按 GPT 结构，对 Llama 为量级估算
- [ ] 待补查（写手凭记忆、未找到原文出处）：RLHF 讲里 GPT-3 预训练 300 B token、InstructGPT 每题 4–9 个回答排序、Llama 2 双奖励模型与四档评分；量化讲的困惑度表来自单作者预印本（arXiv 2601.14277），如需更强出处可删
- [ ] 本人自学时发现缺口再补
- [ ] 关于页只有两句话，待充实
- [ ] 没有统计/分析（可考虑 Cloudflare Web Analytics，免费，一行脚本）
- [x] 账号系统第 0 期代码完成并推送（默认关闭，线上行为不变）：邮箱验证码注册/登录、Passkey、单会话、注册来源、门禁、登录/账号/购买占位页；本地端到端 22/22 通过（2026-10-14）
- [x] **启用账号系统**（2026-10-14，Claude 在内置浏览器操作，登录由本人完成）：D1 `door4ai-lab`（APAC，id 34ef8e2c-d102-4a24-9acd-7f209f4ce41e）建表 17 张并绑定 `DB`；Turnstile 小组件「Door4AI Lab login」（主机名 door4ai.com，含子域）；Access 新应用「Door4AI Lab Admin」保护 `lab.door4ai.com/admin` 与 `/api/admin`，策略 Only me；Resend 用已验证的 door4ai.com 发信（发件人 login@door4ai.com，API key「door4ai-lab login codes」仅发送权限、仅 door4ai.com）；Pages 变量：AUTH_ENABLED=1、ADMIN_EMAILS、MAIL_FROM、TURNSTILE_SITE_KEY、ACCESS_TEAM_DOMAIN、ACCESS_AUD 为文本，RESEND_API_KEY、TURNSTILE_SECRET、TOTP_ENC_KEY 为 Secret。Cloudflare Email Sending 需 Workers 付费版，未开。
- [x] 本人线上登录验证通过（邮箱验证码，注册 + 欢迎页 + 问卷），随后经本人同意删除旧 Access 应用「Door4AI Lab」；匿名访问课程 / 实验页已确认跳转本站登录页，课程目录公开（2026-10-14）
- [x] `SYNC_KEY` 已改为 Secret（值不变）（2026-10-14）
- [ ] 加学员（支付上线前）：启用后台后直接在 /admin「用户 → 开通课程」里填邮箱（对方没注册也行）；未启用后台时执行 `npx wrangler d1 execute door4ai-lab --remote --command "INSERT INTO entitlements (id,user_id,scope,source,starts_at) SELECT lower(hex(randomblob(13))), id, 'series:ai-mastery', 'grant', unixepoch()*1000 FROM users WHERE email='学员邮箱'"`
- [x] 两步验证（TOTP，Apple 密码可直接添加）+ 10 个恢复码 + 防重放；后台 /admin（概览、用户、渠道码、日志）。本地 43/43 + 9/9 通过（2026-10-14）
- [ ] 启用后台：Access 应用加 `/admin` 路径；Pages 设 `ACCESS_TEAM_DOMAIN`、`ACCESS_AUD`；两步验证需设 `TOTP_ENC_KEY`（`openssl rand -base64 32` 生成）
- [x] 第 1 期 买断支付代码完成并上线（2026-10-15，已合入 main）：课程站直连支付宝（本人决定，不经 pay-api / yz-pay）；电脑走 `alipay.trade.page.pay`、手机走 `alipay.trade.wap.pay`；异步通知验签 + 金额核对 + 幂等开通；回跳页轮询、通知丢失时主动查单补单；后台「订单」（筛选、退款并收回权限）与「渠道 → 价格」（默认价 + 渠道专属价）。**价格按学员首次触达的渠道码定，注册后固定**（本人：抖音来的 399，中小学家长群来的 1299 等）。本地模拟支付宝端到端 30/30，账号 43/43、JWT 9/9 全过。
- [x] 线上 D1 已执行 `migrations/0002_payments.sql`（2026-10-15，本人授权，Claude 经控制台会话执行；默认价 399 已种入）
- [ ] 支付宝凭据（本人提供，设为 Pages **Secret**）：`ALIPAY_APP_ID`、`ALIPAY_PRIVATE_KEY`（应用私钥）、`ALIPAY_PUBLIC_KEY`（**支付宝公钥**，不是应用公钥），在 ECS `/etc/yz-pay.env`。需确认：应用是「公钥模式」不是「证书模式」；已签约「电脑网站支付」「手机网站支付」。三个变量不全时购买页显示「在线购买即将开放」，不影响其它功能。
- [ ] 上线前：/admin 建渠道码（如抖音、家长群）并设价；先用 0.01 元真实付一笔 + 后台退款走通。
- [ ] 可选：对账定时任务（Pages 没有 cron，需单独 Worker）。
- [ ] 哪几讲免费试听未定（在文章 frontmatter 写 `access: free` 即可）

## 6. 工作日志（倒序，每次工作追加一条）

- **2026-10-22 · Claude（session_017BBX6F9xKreqTAVSmrMzpE，并行写课第二批）** — 新增 `distillation`（44；贯穿算例「猫图」老师 logits (4, 1, 0, −5)、学生 (2, 0, 1, −3)、T = 4；推出乘 T²；DeepSeek-R1 约 80 万条 SFT 样本与六个学生的 AIME 分数按 arXiv 2501.12948 v1 核对；Gemma 2 蒸馏；生成：`labs-src/distillation/` 先 `build.py` → `node run_lab.mjs` → `toy.py`）与 `diffusion-models`（50；两像素「图」两团数据、4 步玩具调度 ᾱ = 0.9 / 0.72 / 0.36 / 0.09；DDPM T = 1000、β 10⁻⁴–0.02，SD v1 8 倍下采样 4 通道、CFG 7.5 / 50 步，DiT、流匹配、FLUX.2 2026-10-22 核实；生成：`node labs-src/diffusion-models/mc.mjs` → `python3 labs-src/diffusion-models/toy.py`）。衔接句：model-evaluation（上一讲改称蒸馏；「模型篇的最后一讲接着讲模型怎么看图」→「后面接着讲模型怎么看图」）、vision-tokens 的 article.src.md 加一句引出扩散（重跑 toy.py）。agent-security 未完成（见第 5 节）。`npm run build` 通过；全部 43 篇文章页 1440 浅色 / 390 深色无横向滚动、无脚本错误；个人信息检索 0。

- **2026-10-22 · Claude（session_017BBX6F9xKreqTAVSmrMzpE，主会话派 3 个子 agent 并行写，第一批）** — 新增三讲，均按 write-lesson 第 4、5 节写（toy.py/build 脚本生成文章与分镜图，实验页由模板起步、保留图形尺寸上限脚本，关键数字在 node 里用页内同一份代码核对）：`inference-serving`（13，贯穿算例 H100 SXM 跑 Llama-3-8B BF16、1000 token 上下文；屋顶线 / 静态与连续批处理 / PagedAttention / prefix caching / 投机解码 / 吞吐与延迟；vLLM 0.32.0、SGLang 0.5.22、TensorRT-LLM 1.3 移除 TensorRT 后端，2026-10-22 核实；生成：`labs-src/inference-serving/toy.py`）、`overfitting`（22，y = sin 2πx + 噪声 σ = 0.25、三组各 10 点；多项式 / 偏差方差 / L2 / 早停 / dropout 页内 MLP 真训 / 样本数 / 双下降（勒让德基最小范数）；生成：`node labs-src/overfitting/build.mjs`，文章与实验页都由它出）、`distributed-training`（39，Llama-3-8B 每参数 16 B → 128.5 GB、环形 all-reduce、ZeRO 1/2/3、张量并行手算、流水线气泡、3D 并行、Llama 3 405B 表 4 配置核算；生成：`labs-src/distributed-training/toy.py` + `build_lab.py`）。衔接句最小改动：weight-quantization、mixture-of-experts、gradient-descent、residual-connection、lora 的 .md，pretraining 的 article.src.md（重跑 toy.py，仅变一行）。scaling-laws（38）与 reasoning-models（43）由另一窗口在写，未碰；分布式训练讲里按「上一讲 Scaling Laws」称呼。`npm run build` 通过；dist 静态服务下全部 39 篇文章页 1440 浅色 / 390 深色 scrollWidth == innerWidth、无脚本错误；个人信息检索 0。

- **2026-10-22 · Claude（session_011Magq82ckm1tyvEFLBiWRD）** — 按本人要求用 write-lesson 写 Scaling Laws 一讲。新增 `scaling-laws`（order 38）：`labs-src/scaling-laws/toy.py` 算出整讲数字、生成 8 张 SVG（y = Wx 前向 6 条连线 / 反向两件事 / 6N 拆成三块 + Llama-3-8B 卡时 / Kaplan 幂律普通 vs 对数坐标 / 固定 5.76e23 算力的 U 形与两项代价 / 加推理后最省模型随推理量变化 / 涌现 p 与 p⁵ / 六个公开模型 N–D 散点），填进 `article.src.md`（`{{figN}}` 与 `{{n:名字}}`）写出 `src/content/blog/scaling-laws.md`。正文：N、D、C 与 FLOPS → 2 × 3 小网络前向 2N（x = (1, 2, 3)，y = (7, 5)）→ 反向 ① Wᵀg = (1, −1, 1)、② g xᵀ（跨 token 累加）共 4N → C ≈ 6ND（Llama-3-8B 7.23e23；忽略的注意力项 13.4%）→ 卡时（H100 989.5 TFLOPS 稠密；100% 20.3 万、40% 50.7 万，官方 130 万 → 有效 15.6%）→ Kaplan L(N) = (Nc/N)^0.076（每 ×10 乘 0.839，取对数成直线、斜率验算 −0.076；N ∝ C^0.73）→ Chinchilla L = E + A/N^α + B/D^β，**用 Besiroglu 2024 重新拟合的系数**（E 1.8172、A 482.01、B 2085.43、α 0.3478、β 0.3658；原论文系数推出约 59 个/参数、与 20 不一致，实验 03 可切换）；同一算力三种花法 280B / 70B / 8B → L 1.9933 / 1.9745 / 2.0247；求导推出谷底条件 βB/D^β = αA/N^α 与 N_opt 公式，代入得 72.2B、1.33 T、18.4 个/参数，指数 0.513 / 0.487 → 过训练：C 总 = 6ND训 + 2ND推，目标 = Llama-3-8B 配置的损失 2.0218，推理 0 / 1e12 / 1e13 / 1e14 时最省 33.9B / 23.3B / 13.5B / 8.75B（19 / 43 / 192 / 1139 个/参数），1e14 时 8B 只比最优多 2.4%；Meta 原话 Chinchilla 最优约 200B token、训到 15 T 仍对数线性提升 → 涌现：Wei 2022（定义、三位数加法约 2.3e22 FLOPs、CoT 约 1e23）vs Schaeffer 2023（p⁵ 示意表、>92% 来自两种打分、编辑距离平滑），再加 Du 2024 损失阈值 → 公开模型表（GPT-3 / Gopher / Chinchilla / Llama-3-8B / 70B / 3.1-405B 的 N、D、D/N、6ND、官方 C、卡时、反推利用率 20% / — / — / 16% / 28% / 35%）；4 个「停一下」。实验页 `public/labs/scaling-laws/`（手写单文件，画布宽度随容器变）：01 6ND 计算器（预设、H100/A100/V100、利用率、卡数，和官方卡时对照）/ 02 幂律拖 α、普通 / 对数坐标 / 03 给定算力拖 N 的 U 形（两组系数）/ 04 加推理的总运算曲线 / 05 涌现：全对、token 准确率、编辑距离三种打分 × 答案长度 / 06 公开模型散点，点选看明细。事实 2026-10-22 查证：Kaplan 2020（α 0.076、Nc 8.8e13、6N、0.73/0.27、768–1.5B 参数）、Chinchilla 论文（表 2 指数、5.76e23、400+ 模型、MMLU 67.6 vs 60.0）、Besiroglu 2024 系数、Llama 3 模型卡（15T+、1.3M / 6.4M H100 卡时）、Llama 3.1 模型卡（405B 30.84M）、Llama 3 报告（405B、15.6 T、3.8e25、MFU 38–43%、402B / 16.55 T）、Meta 发布文（200B token、对数线性、2 × 24K GPU）、Patterson 2021（GPT-3 10,000 V100 × 14.8 天）、H100 数据表（1979 含稀疏）、Sardana & Frankle 2023、Wei 2022、Schaeffer 2023、Du 2024。衔接：`lora.md` 末段加「上一讲 Scaling Laws」（预训练讲已在另一会话写好指向本讲）。本地 build 47 页通过；1512 浅色 / 390 深色文章与实验页无横向滚动、KaTeX 无报错、长公式已拆行、无脚本错误；个人信息检索 0。

- **2026-10-22 · Claude（session_01SNn1T5c286bGhv3ALJ1Rff）** — 按本人要求用 write-lesson 写推理模型一讲。新增 `reasoning-models`（order 43）：`labs-src/reasoning-models/toy.py` 算出整讲数字、生成 9 张 SVG（Wei 2022 GSM8K 直接答 vs 思维链 / 直接答 1 次前向 vs 分步答 22 个 token 各 1 次前向 / 串行层数 32 vs 704 / k = 5 二项分布 / 投票正确率随 k（p = 0.6、0.4）/ best-of-N 四条线：上限、验证器不被骗、被骗 25%（蒙特卡洛，固定种子）、多数投票 / 固定预算下小模型 14 倍次数投票 vs 大模型（示意）/ GRPO 一组短长回答的优势 / 三种答法的 token 与等待时间），填进 `article.src.md` 写出 `src/content/blog/reasoning-models.md`。正文：思维链（每 token 约 2N FLOP、Llama-3-8B 32 层，中间结果写下来供后面读；句点对照无效）→ 自洽性（k = 3、5 手算二项分布，p < 0.5 越投越错，错答案分散时 p = 0.4 也有用）→ best-of-N（1 − (1 − p)^N 上限、会被骗的验证器极限 p / (p + (1 − p)q)）→ 测试时计算 vs 训练（Snell 2024 的 k = M + 3(M − 1)D_pre/D_inf 逐步推导，M = 14 时 R = 1、22、0.16 分别为 53、15.8、258）→ 推理模型怎么训（引用后训练讲的 RLVR/GRPO，R1-Zero 模板与规则奖励、AIME 15.6% → 71.0%、cons@64 86.7%、修订版 77.9%、aha moment 原话、语言混杂与 R1 补法；GRPO 一组手算说明长度为何变长）→ 代价（845 token/回答、每天百万次 $8,450 vs $30；想太多 2 + 3；何时不值得多想）→ 现状表（OpenAI reasoning.effort、Claude adaptive thinking + effort、Gemini thinking_level、DeepSeek thinking + reasoning_effort、百炼 enable_thinking + thinking_budget，2026-10-22 查各家文档）；4 个「停一下」。实验页 `public/labs/reasoning-models/` 由 `labs-src/reasoning-models/build.py` 拼出（模板 head/尾部脚本 + `lab.body.html` + `lab.js`）：01 直接答 vs 分步答玩具模型（每次前向一步运算，1–5 步）/ 02 多数投票计算器（二项分布精确值，错答案相同 / 各不相同）/ 03 best-of-N + 有噪声验证器（蒙特卡洛 4000 次，可抽一组看挑中谁）/ 04 思考成本计算器 / 05 固定预算取舍（示意）/ 06 GRPO 让思考变长（示意，五档长度，可加长度惩罚；数字已在 node 里跑过核对 note）。事实 2026-10-22 查证：Wei 表 1（PaLM 540B 17.9 → 56.9、GPT-3 175B 15.6 → 46.9）、Kojima 10.4 → 40.7、Wang 56.5 → 74.4、Brown 15.9% → 56%、Snell 公式与结论、o1 AIME 74 / 83 / 93、R1 v1 与修订版、Chen 2024（13 遍、1953%、92%、R1 ASDIV 845 token）。衔接：`rlhf-alignment.md` 末段改为下一讲推理模型、再下一讲评测；`model-evaluation.md` 末段补「上一讲推理模型」。本地 build 42 页通过；1512 浅色 / 390 深色文章与实验页无横向滚动、公式不溢出、无脚本错误；个人信息检索 0。

- **2026-10-22 · Claude（session_01YFhhfqKLw4J3zvSgTz1aps）** — 按本人要求用 write-lesson 写预训练一讲。新增 `pretraining`（order 37）：`labs-src/pretraining/toy.py` 定义贯穿算例（7 个 token 的词表、「我爱吃米饭。」5 个位置、bigram 分数表、两句话一批、SGD 学习率 4），算出全部数字、生成 13 张 SVG，把 `article.src.md` 的 `{{figN}}` / `{{n:名字}}` 填好写到 `src/content/blog/pretraining.md`；**实验页也由脚本生成**：`lab.src.html` + `charlm.js`（字符级 bigram / 小 MLP：手写前向、交叉熵、反向、AdamW，种子固定）+ `corpus.txt`（自编约 670 字中文小语料，最后一句作验证集）→ `public/labs/pretraining/index.html`；`run_lab.mjs` 在 node 里用同一份代码训练，文章里的损失曲线与生成文本表来自它，Chromium 里跑出的结果逐字一致。正文：拆样本（n − 1）→ 因果遮罩 → softmax 一个位置 → 从整句概率连乘推到 −ln p 取平均 → 困惑度 = 几何平均的倒数 → 一个训练步（数值微分验证 p − y、「米」行梯度表、更新后「粥」升「饭」几乎不动）→ 损失下限 2 ln 2 / 10 → 数据来源 / FineWeb 清洗流程 / Jaccard + MinHash 证明 + 14×8 分桶曲线 / GPT-3 配比表与 Llama 3 配比、退火 → warmup + cosine（Adam 第一步 = ±η 的推导；带噪声碗的稳态方差 V = ησ²/(a(2 − ηa)) 推导）→ 页内小模型（MLP 验证损失第 225 步最低后上升 = 背原文）→ 学到了什么、为什么只会续写。实验：01 拆样本 + 遮罩 / 02 交叉熵计算器 / 03 bigram 一个训练步 / 04 真实训练（模型、调度、峰值学习率可选，可从任意开头生成）/ 05 学习率调度 + 带噪声碗恒定 vs 余弦 / 06 GPT-3 与 Llama 3 配比。事实 2026-10-22 查证：Llama 3 报告第 3 节（15.6 T token、清洗与三层去重、50/25/17/8 配比、退火 24.0% / 6.4%、405B 峰值 8e-5、预热 8000 步、余弦到 8e-7、120 万步、batch 4M→8M→16M）、FineWeb 论文（96 快照、36 T → 20 T → 15 T、MinHash 5-gram 112 哈希 14×8、全局去重仅剩约 4 T 反而更差、FineWeb-Edu 1.3 T）、GPT-3 表 2.2。衔接：`layernorm.md` 末段改为下一讲预训练；`lora.md` 两处改指预训练；`post-training`（article.src.md 重跑）开头与交叉熵处改指预训练一讲。本地 build 45 页通过；1512 浅色 / 390 深色无横向滚动、KaTeX 公式无溢出、无脚本错误（仅本地静态服务下 /api/me 等 404）；个人信息检索 0。

- **2026-10-22 · Claude（session_017Fwc1rzTkWkiTuLbPY9ZSq）** — 按本人要求用 write-lesson 写数学讲。新增 `vectors-softmax`（order 4.5，模型篇第一讲）：`labs-src/vectors-softmax/toy.py` 定义贯穿算例（**与注意力讲同一组数**：粮油 (0, 1)、店 (0.4, 0.2)、买了 (0.2, 0)、小米 (0.5, 0.5)；W_Q x = (1.0, −0.6)；W_K 乘 2 × 4 的 X 得 K；K 乘 (1.0, −0.6) 得分数 1.6 / 0.48 / 0.08 / 1.0；softmax 47.8 / 15.6 / 10.4 / 26.2 %；T = 0.5 / 2 / √2；线性层 b = (0.2, 0.4)），生成 12 张 SVG 并把 `article.src.md` 的 `{{figN}}`、`{{n:名字}}` 填好写到 `src/content/blog/vectors-softmax.md`。正文 15 步：向量 → 箭头与长度 → 点积 → 投影与 ‖a‖‖b‖cos θ → 余弦相似度 → 矩阵乘向量（逐行点积）→ 形状规则 (m × n)(n) → (m) → 矩阵乘矩阵与转置 → 线性层 y = Wx + b 与参数量（GPT-2 FFN 768 → 3072 带偏置 2,362,368；Llama-3-8B 输出投影 128,256 × 4096 = 525,336,576）→ 为什么不能直接除以总和 → 指数 → softmax → 温度 → 减最大值（float32 溢出点 88.72、float16 11.09）→ 对数（0.478 在 float32 里连乘第 141 次变 0、log-softmax、交叉熵只点到）；5 个「停一下」。实验页由 `labs-src/vectors-softmax/build.py` 拼出（模板样式 + `lab.body.html` + `lab.script.js`）：01 拖两支箭头（点积、投影、夹角）/ 02 矩阵乘向量逐行高亮 / 03 形状检查器 + 线性层参数量（四个真实预设）/ 04 softmax + 温度 + 直接除以总和对照 + 抽 100 次 / 05 float64 / float32 / float16 下直接取指数 vs 先减最大值（每步按精度舍入，float16 用自写舍入）/ 06 float32 连乘与对数相加。衔接：`attention-qkv` 的 `article.src.md` 加三处「见上一讲」（矩阵乘向量、softmax、÷√2 = 温度 √2）并改「和前后两讲的关系」，重跑 toy.py（只有这几处变化）；`tokenizer-llm.md` 末段改为先接本讲。本地 build 42 页通过；1512 浅色 / 390 深色无横向滚动、KaTeX 无报错、无脚本错误，390 宽长公式已拆行；实验关键读数（56 倍 float32 溢出、7 倍 float16 溢出、第 141 次变 0）在 Chromium 里核对；个人信息检索 0。

- **2026-10-22 · Claude（session_01BU4u8x4TdPeBZqiM9RuSf3）** — 本人要求写 Prompt 工程一讲。新增 `prompt-engineering`（order 99，Agent 篇第一讲，工具调用之前）；`src/data/course.ts` 模型篇 `until` 100 → 99（课程目录已确认它排在 Agent 篇第一位），第 4 节「Agent 篇 order ≥ 100」同步改为 ≥ 99。`labs-src/prompt-engineering/toy.py` 定义贯穿算例（耳机网店评论分类，第一条评论「快递第二天就到了……左耳就没声了」应判差评），token 数由 `count_tokens.mjs` 调同源 `/labs/tokenizer-llm/tiktoken.js`（o200k）在 node 里真实计数（好版本 ChatML 整串 227 = 5 特殊 + 6 角色名 + 2 换行 + 系统提示 184 + 用户 30；系统提示四块 30/25/87/42），生成 8 张 SVG 并由 `article.src.md` 生成文章（4 个「停一下」）。正文七节：消息列表 → 对话模板（ChatML / Llama 3 / Harmony 对照表，Harmony 角色优先级）→ 系统提示四块（角色、任务、规则、输出格式）与「给理由」→ 少样本（示意偏差模型 z = s + α·n/k + β·[最后一个]，四种示例安排，同样 3 个示例只换顺序答案就变；过度模仿）→ 结构化输出（JSON Schema、六种常见格式错误、各家 API 参数表、受约束解码手算 0.46/0.72 = 0.639）→ 先分析再回答（字段顺序 reason 在前）与提示链 → 三个坑（指令冲突、Lost in the Middle、否定指令）→ 10 道测试题两版对比（示例数据，标准误 0.095，McNemar p = 0.375，放大到 100 题 2.4 × 10⁻⁵）。**实验页由 toy.py 生成**：skill 模板的头尾 + `labs-src/prompt-engineering/lab.body.html`，并把 `toy.json` 写成页内 TOY 常量（改实验页改 lab.body.html 后重跑脚本）。实验：01 对话模板拼装器（三种模板，o200k 逐段计数，可带前一轮）/ 02 检查清单（页内规则，标明不是 AI 评分）/ 03 少样本偏差示意（追加 / 删除 / 打乱示例，枚举全部顺序看几种判对）/ 04 JSON 解析 + schema 校验（六种错误一键切换）+ 受约束解码屏蔽与 1000 次抽样 / 05 10 题对比表（示例数据，点格子改结果，题目放大 ×3 / ×10）。事实 2026-10-22 查证：Anthropic `output_config.format`（GA，`output_format` 已弃用，beta 头 `structured-outputs-2025-11-13`）、OpenAI Responses `text.format` + `strict`、Gemini Interactions API `response_format`（`mime_type` + `schema`）、Qwen3 ChatML 模板、Llama 3 格式、Harmony 特殊 token 与优先级、Anthropic 提示文档（正面指令、给理由、3–5 个示例、长文档放前面最多 30%、4.6 起不支持 prefill）、Kojima 2022（17.7% → 78.7%，10.4% → 40.7%）、Wei 2022（PaLM 540B GSM8K 58%）。衔接：`tool-calling.md`「和前后两讲的关系」改为承接本讲。本地 build 42 页通过；1512 浅色 / 390 深色无横向滚动、KaTeX 无报错、无脚本错误，五个实验逐项点过；个人信息检索 0。

- **2026-10-22 · Claude（session_014tDUqdaiQ99Ldxb23D7ZMj）** — 本人要求写位置编码一讲。新增 `positional-encoding`（order 6）：`labs-src/positional-encoding/toy.py` 沿用注意力讲的 x、W_Q、W_K、W_V（另加 4 个示意位置向量 p 与玩具 RoPE θ = 10°），算出整讲数字、表格与 11 张 SVG（打乱前后份额 / 加 p 后份额 / 正弦热力图 / 两根指针 / q 转 30° / 一起转点积不变 / (3,0) 与 (13,10) 同分 / 单频率周期 / 多频率叠加 / Llama 3 底数下 64 对在 8192 内转的圈数 / PI、NTK-aware、YaRN 每对转速倍数），填 `article.src.md` 的 `{{figN}}`、`{{tab_*}}`、`{{n:名字}}` 生成 `src/content/blog/positional-encoding.md`。正文六步：打乱词序结果不变（x′ ≈ (0.74, 1.66) 两句相同）→ 可学习绝对位置（三个毛病，GPT-2 1024 × 768）→ 正弦编码（d = 4 手算、挪 k 格 = 转固定角度推导、加法式四项展开）→ RoPE（旋转公式推导、点积只看 m − n 的角度推法与矩阵推法、(3,0) 与 (13,10) 都是 1.186）→ 多频率（θ_i = b^{−2i/d}，周期 36 的问题、两对验算、远程衰减）→ 长上下文（Llama 3 底数 50 万、L = 8192 时 29 对没转满一圈；PI / NTK-aware（改底数后中间各对仍稍超出，第 35 对 1.85 倍）/ YaRN 分段 + 温度）+ Llama 3 / 3.1 配置表；6 个「停一下」。实验页 `public/labs/positional-encoding/`：01 六种词序 × 三种位置做法 / 02 正弦热力图 + 8 根指针 + PE·PE 只看 k / 03 RoPE 旋转盘 + 分数随位置差曲线 / 04 多频率平均 cos 与每对 cos 小柱 / 05 五种做法下每对训练与测试圈数（橙色 = 没见过的角度）。窄屏改为上下排，公式在 390 宽全部不溢出（长式用 aligned 拆行）。事实 2026-10-22 查证：Llama 3 8B config（rope_theta 500000、8192）、Llama 3.1 8B config（131072、rope_scaling llama3 factor 8 / low 1 / high 4 / original 8192）、Llama 3 论文（底数 500,000，6 阶段约 800B token 扩到 128K）、RoFormer（2021-04）、PI（Chen 等 2023，LLaMA 7B–65B 到 32768，1000 步内）、YaRN（α = 1、β = 32，√(1/t) = 0.1 ln s + 1，Llama 2 7B/13B 到 128K，400 + 200 步）、NTK-aware（bloc97，r/LocalLLaMA，2023）。衔接：`attention-qkv` 的 article.src.md 末段「下一讲」改为位置编码（重跑 toy.py），`multihead-gqa.md`「和前后两讲的关系」加一句承接 RoPE。本地 build 42 页通过；1512 浅色 / 390 深色无横向滚动、KaTeX 无报错、无脚本错误；个人信息检索 0。

- **2026-10-22 · Claude（session_01VqMoFiGixz3RVrE6UJ4jAo）** — 本人问「模型是如何理解图像的」后要求写成教材。新增 `vision-tokens`（order 48，模型评测之后、Agent 篇之前），按 write-lesson 新标准（图文、一小步一小步、无视频）：`labs-src/vision-tokens/toy.py` 定义贯穿算例（4 × 4 灰度小图 → 2 × 2 切块 → $W_E$ 取「亮度 / 竖边」两行得 e → 位置向量 ±0.1 让两块全黑的块分开 → CLIP：三图三句、余弦 0.943/0.055/0.832、τ = 0.1、图 A 选对 75.2%、损失 0.285 → 平均向量丢位置（两张图平均都是 (0.375, 0.25)）→ 投影 W_P → 「竖杠」q = (1, 1) 的注意力 17.1/17.1/53.0/12.9 %），生成 10 张 SVG 分镜图并由 `article.src.md` 生成 `src/content/blog/vision-tokens.md`（4 个「停一下」）。实验页 `public/labs/vision-tokens/`（手写，数字与 toy.py 一致）：00 可点改像素 + 切块大小 / 01 e 与位置向量 / 02 打乱四块平均不变 / 03 CLIP 3 × 3 表（温度、文字向量方向可调）/ 04 三种问题的注意力份额 / 05 Claude 视觉 token 计算器（28 × 28、标准 / 高分辨率两档，二分求最大缩放）+ 小字缩小演示（canvas 真缩放）。真实规模数字 2026-10-22 查证：Claude Vision 文档（⌈w/28⌉ × ⌈h/28⌉，1000² → 1296，1920 × 1080 → 1456 × 819 → 1560，高分辨率 2576 / 4784）、Qwen2-VL 论文（675M ViT、patch 14、2 × 2 合并、224² → 66 token、2D-RoPE）；LLaVA-1.5（ViT-L/14-336、576 token、两层 MLP 投影）与 CLIP（4 亿对、τ 起点 0.07）凭已知出处。衔接：`model-evaluation.md` 末段「到模型篇这里结束」改为接本讲，`tool-calling.md` 模型篇回顾加「模型怎么看图」。本地 build 40 页通过；1512 浅色 / 390 深色无横向滚动、无脚本错误、KaTeX 无报错，390 宽长公式已拆行；个人信息检索 0。

- **2026-10-22 · Claude（session_01NAqoDkgqfsGCL6jcYnjuSJ）** — 本人问「什么是后训练」后要求写成教材。新增 `post-training`（order 41）：`labs-src/post-training/toy.py` 算出整讲数字并生成 7 张 SVG（基座模型下一个 token 分布 / 对话模板 token 串 / SFT 一步前后 / 逐 token 损失与遮罩 / GRPO 一组的奖励与优势 / GRPO 一步前后 / 四个模型的流水线），把 `article.src.md` 里的 `{{figN}}` 与 `{{n:名字}}`（数字占位符，新做法）填好写到 `src/content/blog/post-training.md`。正文八步：基座只会续写 → ChatML 对话模板 → SFT 交叉熵与梯度 p − y 推导 + 手算一步 → 损失遮罩（提问占全部损失 80.1%）→ LIMA 与遗忘 → 偏好对齐（指向下一讲）→ RLVR/GRPO（组内优势、∑A = 0 让梯度只剩第一项、手算一步 35.0% → 51.9%、全对全错组 p^G + (1 − p)^G）→ InstructGPT / Llama 3 / Tülu 3 / DeepSeek-R1 流水线；3 个「停一下」。实验页 `public/labs/post-training/`：01 SFT 走步 / 02 损失遮罩（可逐 token 切换）/ 03 GRPO 一组（真实采样，第一组固定为文中的 51、41、51、54）/ 04 三道难度不同的题做 200 步 GRPO + p^G + (1 − p)^G 曲线 / 05 四条流水线；画布宽度随容器变（窄屏改为上下排）。事实 2026-10-22 查证：Tülu 3 SFT 939,344 个 prompt、DPO 354,192 对、RLVR 用 GSM8K/MATH/IFEval；Llama 3 预训练约 15 T token、后训练 6 轮；DeepSeek-R1 冷启动数千条、重新 SFT 约 60 万 + 20 万条 2 epoch。衔接：`lora.md` 末段改为下一讲后训练，`rlhf-alignment.md` 开头与「和前后两讲的关系」改为承接本讲。本地 build 40 页通过；1512 浅色 / 390 深色无横向滚动、公式不溢出、无脚本错误；个人信息检索 0。

- **2026-10-22 · Claude（session_01QvBhNRgUqPZf8fhAnjTAx7）** — 本人反馈左右页边距很糟糕（大屏上只有 40px，一行一千四百多 px）。正文与实验页边距由 `clamp(16px,3vw,40px)` 改为 `clamp(18px,9vw - 16px,200px)`（390 宽 ≈ 19px，1512 宽 ≈ 120px，1920 宽 ≈ 157px）：`Base.astro` 页眉 / main / 页脚 / `.post-body` / 资源页，全部 28 个实验页 `.wrap`，skill 与实验页模板。本地检查 1512、1920、390 宽：实验标题与正文左边缘对齐，无横向滚动。随后本人要求顶部和底部不需要这么大的页边距：页眉 `header.site`、页脚 `footer.site` 改回 `clamp(16px,3vw,40px)`。

- **2026-10-21 · Claude（session_01QvBhNRgUqPZf8fhAnjTAx7）** — 按新标准重写样板讲 `attention-qkv`：新增 `labs-src/attention-qkv/toy.py`（贯穿全文的四词小例子「粮油 店 买了 小米」，二维 x、W_Q/W_K/W_V、分数 1.6/0.48/0.08/1.0、softmax 47.8/15.6/10.4/26.2 %、÷√2 后 40.8/18.5/13.9/26.7 %、x′≈(0.74, 1.66)；生成 6 张 SVG 图）与 `article.src.md`（八步：缩小问题 → q → k → 点积 → softmax → 除以 √d_k（方差推导 + Qwen 实测）→ v → 加权求和与残差，每步手算表格 + 3 个「停一下」），生成 `src/content/blog/attention-qkv.md`。实验 03/04/06 改用同一组数字（去掉原来的缩放系数 G=0.55）。删除 `public/videos/attention-qkv/` 与 `manim-src/attention-qkv/`。skill 第 5 节补「标准做法」与 `<summary>` 里不能用 `$…$`。本地 build 通过；1512 浅色 / 390 深色无横向滚动、表格不溢出、无脚本错误。

- **2026-10-21 · Claude** — 按本人纠正改写 skill `write-lesson`：去掉「Manim 视频」，改为图文（静态分镜 SVG，与实验同一套画法）；新增第 4 节「一小步一小步讲清楚」写作规范（8 条）；新增 `templates/figure.svg` 示范图，更新文章与实验页模板。`Base.astro` 补 `--warn/--ok` 主题色（原来只有实验页有），加 `.prose figure.fig` 与 `details.pause` 样式。用临时文章验证 1512 / 390 宽、深浅两色显示正常后删除。

- **2026-10-20 · Claude（session_01ViBoemAJxz2CQYEKk8rBUY）** — 本人反馈多头讲实验 01 的热力图大到一屏看不完：`public/labs/multihead-gqa/index.html` 把六个缩略图改为 3 × 2，与选中头的大热力图并排（`.duo`），大图 viewBox 收紧到网格本身；两张图同高 = min(外层视口 50%, 460px)，并排放不下时按容器宽度一起缩小，手机宽度上下排。两张图加 `data-nofit`，页尾「图形尺寸上限」脚本跳过带此属性的图。大图标签字号 14 → 17。Chromium 检查 1512 × 860 / 1000 × 780 整个实验一屏可见、390 宽无横向滚动、无脚本错误。

- **2026-10-19 · Claude（session_01RbNocXbB6CzayVPYBwkwdY）** — 本人问 Token 实验 01（字母级 BPE）里的数字怎么来的，要求把说明补进去。`public/labs/tokenizer-llm/index.html`：(1) 实验 01 导语加一句：默认语料 low 5 / lower 2 / newest 6 / widest 3 是给定词频，出自 Sennrich 等 2016 BPE 论文；(2) 片段对列表不再在并列次数中间截断（保留与第 7 名同分的全部），其余的写「另有 N 对，各 X 次」；(3) note 下加可展开的「这些数字是怎么算出来的」（`#how1`，随当前状态实时生成）：每一对的加权次数拆成「newest 6 + widest 3 = 9」、合并时打平的规则（取先出现的一对）、词表 = 初始字母 + 合并出的 token（不再单独出现的字母仍在词表里）、总 token 数 = 各词片段数 × 频次之和，以及与合并前的差 = 各规则次数之和（首尾重叠的对如 aaaa 时说明为何不等）。`src/content/blog/tokenizer-llm.md` 实验列表第 1 项补一句。云端 clone build 39 页通过；Chromium 1440 浅色 / 390 深色无横向滚动、无脚本错误，用默认语料、合并到底、aaaa/banana 三种情况核对过数字。

- **2026-10-19 · Claude（session_01MmDJEcUExCaMurhqYeS9sy）** — 按本人要求写完另一会话提出的 122 讲。新增 `browser-computer-use`（order 122）：文章 `src/content/blog/browser-computer-use.md`；实验页 `public/labs/browser-computer-use/` 的核心是一个用 srcdoc iframe 嵌入的真实 1280 × 800 模拟商城网页（`shopHTML(o)` 可开关：改 id、只剩图标的按钮、截图后才弹出的横幅、四种藏法的注入）。00 页面文字 / 元素清单（按 Playwright MCP 写法自建可访问性快照，`ref=eN`）/ 截图三种看法，文字由 o200k 计数，截图按 Claude 视觉文档 ⌈w/28⌉ × ⌈h/28⌉、标准档长边 1568 & 1568 token、高分辨率档 2576 & 4784 token / 01 在缩小后的截图上点击，三种坐标换算，`elementFromPoint` 查点中什么 / 02 JS、元素编号、截图坐标三种做法真实执行搜索，三种网页变化各让一种失败（执行用的 iframe 是 fixed + opacity 0，放到屏幕外会导致 hit-test 失灵；表单处理函数不能叫 `go`，会被同名按钮遮住）/ 03 8 个动作 × 5 层保护 / 04 注入四种藏法 × 四条通道（真实 DOM 检查）、三种措辞 × 规则检测器。动画 `manim-src/browser-computer-use/scenes.py` → `public/videos/browser-computer-use/ScreenshotClickLoop`。事实 2026-10-19 查证：Claude Vision 与 Computer use 文档（工具集 17 个动作、约 4,500 token 开销、推荐分辨率）、Playwright MCP 快照格式、Claude for Chrome（2025-08-25：123 个用例，23.6% → 11.2%，浏览器特有攻击 35.7% → 0）。衔接：`mcp.md` 末段预告本讲、`streaming.md`「上一讲 MCP」改为第 120 讲。本地 build 39 页通过；Chromium 1440 浅色 / 390 深色无横向滚动、无脚本错误、KaTeX 无报错；个人信息检索 0。

- **2026-10-19 · Claude（session_01MmDJEcUExCaMurhqYeS9sy）** — 本人问「什么是 harness」后要求写成一讲（位置由 Claude 定：107，作为 Agent 篇总纲）。(1) 新增 `agent-harness`（order 107）：文章 `src/content/blog/agent-harness.md`；实验页 `public/labs/agent-harness/`：00 页内迷你 harness（虚拟文件系统、grep / bash / edit / run_tests、o200k 计数、8K 窗口减 2K 输出预留），可关掉循环 / 工具执行 / 错误回填 / 上下文管理 / 权限确认，各自坏法不同（日志 75 行、两次搜索才会撑爆窗口，数字已在 Chromium 里核对）/ 01 14 个动作分「程序 / 再调一次模型」/ 02 按需加载（真实分词器；可切 Anthropic 文中 58 个工具约 55K token 的实测平均）/ 03 整份重写、`str_replace`、`apply_patch` 三个真解析器（apply_patch 按 Codex 的逐级放宽匹配）+ 四种注入错误 / 04 相邻两轮请求逐 token 最长公共前缀，三个打碎缓存的开关。复用同源 `/labs/tokenizer-llm/tiktoken.js`。动画 `manim-src/agent-harness/scenes.py` → `public/videos/agent-harness/{HarnessLayers,ModelInsideHarness}`。(2) `rlhf-alignment` 加一节「从一问一答到多步任务：Agent 的强化学习」（DeepSWE、Search-R1 屏蔽对照、Claude 3.7 Sonnet 系统卡第 6 节）+ 实验 06（三种做法的策略，GRPO 组内优势真实计算；仓库测试可改时改测试文件概率升到 99%+、真实通过率 2%，隐藏测试时学会认真改）；该实验页首次引入 KaTeX，只渲染 `#s6`，旧的 HTML 公式仍待迁移。(3) 衔接：`agent-loop.md` 末段指向 107、`context-window.md` 两处「上一讲」改为第 105 讲并回扣 harness、`agent-frameworks.md` 回顾段加 107。本地 build 38 页通过；Chromium 1440 浅色 / 390 深色无横向滚动、iframe 自动长高、无脚本错误、KaTeX 无报错；个人信息检索 0。

- **2026-10-19 · Claude（session_01CwRcH6yXZUA6quuw1MJimQ）** — 本人看了一个讲 QKV 的抖音视频后要求重写注意力讲，并要求「公式一定要跟平时书写见到的一样」。(1) **全站接入 KaTeX**：`astro.config.mjs` 加 remark-math + rehype-katex；`Base.astro` 引 `/vendor/katex/katex.min.css` 与 `.prose .katex*` 样式；`public/vendor/katex/`（0.16.47）；`context-window.md`、`gateway-orchestration.md` 里的美元金额改成 `\$`。(2) **`attention-qkv` 重写**（order 5 不变，标题改为《注意力里的 Q、K、V：模型怎么知道「小米」是粮食还是手机》）：例子统一为「我在粮油店买了两斤小米 / 我在数码店买了一部小米」（另附「长城」城墙 / 汽车一组），实验 00 嵌入表最近邻 + 两个「小米」逐层夹角 / 01 第 1 层第 11 头真实份额 / 02 余弦相似度 vs q·k（第 1 层两个「小米」的 q 实测完全相同）/ 03 二维点积示意 / 04 softmax vs 只给第一名（梯度）/ 05 真实分数缩放前后 + 随机向量验证 √d / 06 v 与残差二维示意 / 07 28 层 × 16 头浏览器 + 热力图（attention sink）；数据 `public/labs/attention-qkv/qwen-data.js`，生成脚本 `labs-src/attention-qkv/`（`qwen_attn.py` 手算第 1 层 Q/K（含 q_norm、RoPE、GQA 展开）与 transformers 输出对照误差 < 1e-4；`emb.py` 嵌入最近邻）。动画 `manim-src/attention-qkv/scenes.py` → `public/videos/attention-qkv/ScaledDotProduct`。权重由本人 Mac 的内置浏览器从 Hugging Face 分 5 段下载后传到云端（云端与 Mac 的 shell 都连不上 HF），用后已删除。(3) 原来的多头 / 参数构成 / MLP 三个实验移出：多头已由同日另一会话的 `multihead-gqa`(7) 覆盖；新增 **`mlp`(order 8)**：00 参数构成（加 Qwen3-0.6B）/ 01 ReLU、SiLU、GELU 与 SwiGLU / 02 与门 / 03 Qwen3-0.6B 每层激活差别最大的神经元及其 W_down 列的最近词（第 9 层 #2190 → 面粉、米饭、淀粉），数据 `public/labs/mlp/mlp-data.js`，脚本 `labs-src/mlp/`。衔接句：`multihead-gqa.md` 末段改为「下一讲 MLP，再下一讲 KV Cache」，并去掉「QKV 那讲提到了多头和 W_O」。本地 build 37 页通过；两个实验页 1440 浅色 / 390 深色无横向滚动、无脚本错误、KaTeX 无报错；个人信息检索 0。

- **2026-10-19 · Claude** — 模型篇补充四讲（第 7 节原「之后可补」四题）：`multihead-gqa`（7：00 切头参数不变 / 01 构造头 + 随机头的注意力热力图 / 02 拼接与 W_O，两种写法数值相等 / 03 MHA→GQA→MQA 分组 / 04 KV cache 计算器（Llama-2-70B、Llama-3-8B/70B config 核实）/ 05 decode 读 KV 的带宽时间；动画 SplitHeads、GroupedKV）、`weight-quantization`（12：00 FP32/FP16/BF16 位模式（DataView 真转换）/ 01 位数与对称性 / 02 按张量、按通道、按组 / 03 矩阵乘误差 RTN vs 简化 AWQ / 04 模型 × 精度 × 显卡的显存与 token/s / 05 小 MLP 量化；动画 FloatBits、QuantGrid）、`mixture-of-experts`（15：00 路由 top-k / 01 负载均衡三种训练方式真训练 / 02 容量因子蒙特卡洛 / 03 总参数 vs 激活参数（Mixtral 8x7B、DeepSeek-V3、DeepSeek-V4-Flash 逐项核对官方数字；V4-Flash 发布月份各来源不一，只写年份）/ 04 稠密 vs MoE 不同 batch 读权重量 / 05 小型 MoE 真训练；动画 RouterTopK、TotalVsActive）、`rlhf-alignment`（42：00 Bradley–Terry 拟合 / 01 奖励模型学到长度偏好 / 02 奖励黑客 / 03 KL 惩罚与解析解对照 / 04 DPO 与 RLHF 结果一致（差 1e-15）/ 05 InstructGPT、Llama 2 三段式；动画 PreferencePair、RLHFLoop）。衔接句最小改动：`attention-qkv.md`（下一讲改为多头）、`gradient-descent.md`（前面几讲加上量化、MoE）、`lora.md`（下一讲改为 RLHF）、`model-evaluation.md`（上一讲改为对齐）；`public/labs/attention-qkv/` 实验 05 note 里「上一讲 KV cache」笔误改为「后面 KV Cache 那讲」。本地 build 36 页通过；全部 28 讲 1440 浅色 / 390 深色无横向滚动、无脚本错误；个人信息检索 0。

- **2026-10-19 · Claude** — 最后一批三讲上线，14 讲规划全部完成：`ai-coding-tools`（基础篇 3.8：00 一次 AI 改代码的示意回放（每步 diff 页内真实计算）/ 01 页内 LCS 行级 diff，可编辑 / 02 三种权限模式 × 12 条命令 / 03 Git 安全网：页内真跑测试，commit 与否的回退结果，blob 哈希与 git 一致 / 04 需求检查清单打分；动画 AgentEditLoop；Codex、Cursor 形态取自第三方资料，表格只写大致形态）、`gateway-orchestration`（135：00 三档模型路由与级联成本 / 01 降级与重试蒙特卡洛 / 02 响应缓存与 prompt cache / 03 orchestrator-worker 甘特图 / 04 上下文隔离 / 05 依赖度与拆分收益（示意）；动画 GatewayRouting、OrchestratorWorkers；引 Anthropic 多 Agent 研究系统一文的 4× / 15× token 数字，并说明同等工作量下多 Agent 反而更省）、`agent-frameworks`（140，纯文字：手写 vs 框架 SVG 图、同一 Agent 三种框架写法、LangChain / LangGraph / LlamaIndex / Claude Agent SDK / OpenAI Agents SDK 两张对照表，API 名以 2026-10-19 的 PyPI 源码核实，查不到的格子写「—」）。修了全站一处手机版问题：宽表格与长行内代码会撑出横向滚动（见第 4 节）。本地 build 32 页通过；全部 24 讲 1440 浅色 / 390 深色无横向滚动、无脚本错误；个人信息检索 0。

- **2026-10-19 · Claude** — Agent 篇第 4–7 讲上线（四个子任务并行，主会话统一检查）：`rag-embedding`（115：被限流中断的草稿补完；00 页内 LSA（TF-IDF + SVD，24 维）向量 / 01 切块与答案被切断 / 02 top-k 召回 / 03 BM25、向量、RRF 混合 / 04 片段位置 × 片段数（沿用上一讲 Lost in the Middle 示意曲线）/ 05 rerank（启发式，已标明）；embedding 模型表 2026-10-19 查证）、`mcp`（120：按 2026-07-28 规范，页内两个真的迷你 MCP server 处理 JSON-RPC；00 M×N→M+N / 01 报文时序（可切 2025-11-25 握手式、stdio / Streamable HTTP）/ 02 MCP 工具→模型 tools→tools/call 字段流转 / 03 手发请求看真实响应与错误码 / 04 审批策略 / 05 工具说明里的提示注入（示意）；动画 MxN、MCPRoundTrip）、`streaming`（125：00 TTFT 与总时长 / 01 setTimeout 真推送的 SSE，Anthropic / OpenAI 两种格式，o200k 真分词 / 02 随机字节切块下三种解析器对照，TextDecoder stream 正确 / 03 input_json_delta 拼接 / 04 按 token/s 真打字 / 05 ReadableStream + AbortController 取消；流式格式 2026-10-19 核对官方文档）、`trace-eval`（130：00 span 树 + 甘特图 / 01 耗时成本归因 / 02 结果、轨迹、单步三层判分 / 03 LLM 裁判位置与长度偏差蒙特卡洛——交换顺序判两次不提高期望分，改讲「一致结论更可靠」/ 04 30 题回归矩阵 + McNemar / 05 拦截规则引擎；示例数据已标明）。注：Manim 产物实际落在 `manim-src/media/{videos,images}/scenes/`（按模块名），不是 `<slug>/`。本地 build 29 页通过；headless Chromium 1440 浅色 / 390 深色无横向滚动、iframe 自动长高、无脚本错误；个人信息检索 0。`wip/rag-embedding` 分支已无用，可删。

- **2026-10-19 · Claude** — Agent 篇前三讲上线：`tool-calling`（100：00 一次 tool call 的来回，Anthropic / OpenAI 两种报文可切换，页内真实执行计算器与单位换算 / 01 工具定义占多少 token，**复用同源 `/labs/tokenizer-llm/tiktoken.js`**（移动该文件需同步改这里）/ 02 页内 JSON Schema 校验器与 is_error 重试 / 03 串行 vs 并行时间线 / 04 长结果截断与摘要 / 05 工具选择示意树；动画 ToolCallLoop、SchemaToText）、`agent-loop`（105：00 最小循环与 messages 数组增长 / 01 token 二次方累积与 prompt cache / 02 终止与预算 / 03 失败处理蒙特卡洛 / 04 workflow vs agent / 05 ReAct 轨迹阅读器；动画 WhileLoop、ReActTrace；引 Anthropic《Building effective agents》）、`context-window`（110：00 窗口预算条 / 01 Llama-3-70B KV cache 与注意力 n² 代价 / 02 Lost in the Middle 示意曲线（拟合 Liu et al. 2023 实测点）/ 03 截断、滚动、摘要三种压缩 / 04 持久记忆两次会话 / 05 prompt cache 费用；动画 ContextBudget、MemoryLayers；各家上下文长度为 2026-10-16 查证）。三讲首次在课程文章里用 fenced code。`rag-embedding` 写手中途被限流中断，草稿留在本地未入库。本地 build 25 页通过；headless Chromium 检查 1440 浅色 / 390 深色无横向滚动、iframe 自动长高、无脚本错误；个人信息检索 0。

- **2026-10-17 · Claude** — 按本人反馈去掉分隔线：课程列表改为无线条、悬停整行圆角浅底且整行可点；页眉下边线、页脚上边线、翻页上边线、Resource 分组上边线删除。改 `Base.astro`。第 4 节加总规矩，skill 同步。

- **2026-10-17 · Claude** — 按本人反馈学习记录面板太宽：`.act` 改为 `width:fit-content`（正好包住 53 周格子，约 796px，左对齐；窄屏仍可横向滑动）。改 `Base.astro`。

- **2026-10-16 · Claude** — 模型篇补齐四讲（四个子任务并行写，主会话统一检查上线）：`backpropagation`（order 30：页内标量 autograd，00 计算图逐步流动 / 01 单链三法一致 / 02 两层网络 13 个梯度与中心差分逐项对照 / 03 数值微分 vs 反向传播代价 / 04 深链连乘；动画 ChainRule、Backward2Layer）、`layernorm`（35：00 归一化不变性 / 01 残差流范数随层数 / 02 token 范数分布 / 03 LN vs RMSNorm / 04 三种设计真实反向梯度 / 05 可用学习率范围；动画 NormalizeVector、PrePostNorm；小网络里 Post-Norm 并不吃亏，文章如实写并引 Xiong 2020）、`lora`（40：00 秩 / 01 参数计数器 / 02 真实微调 ΔW 的 SVD / 03 全量 vs LoRA r=1,2,4 / 04 合并与切换 / 05 Llama-3-8B 逐矩阵 LoRA 参数表；动画 LowRankUpdate、RankIntuition）、`model-evaluation`（45：00 困惑度 / 01 n-gram 困惑度 / 02 pass@k / 03 数据污染 / 04 Elo / 05 小 eval 集；动画 Perplexity、Goodhart；首个在课程文章里用 markdown 表格的讲）。关键数字都在 node 里用同一份页内逻辑核对过（见各讲 note）。四个实验页补上了同日另一会话加的「图形尺寸上限」脚本。本地 build 22 页通过；headless Chromium 检查 /ai 与四个文章页 1440 浅色 / 390 深色无横向滚动、iframe 自动长高、无脚本错误；个人信息检索 0。

- **2026-10-16 · Claude** — 课程立项：`src/data/course.ts` 的 PARTS 加「Agent 篇」（order ≥ 100，模型篇改为 < 100）；第 4 节记录三篇结构的决定，第 7 节写入 14 讲的 slug / order 规划（基础篇 1、模型篇 4、Agent 篇 9）。各讲正在分批写，写完逐讲追加日志。

- **2026-10-16 · Claude** — 按本人反馈（14 寸屏上实验图过大）给 8 个实验页（含 `labs-src/computer-anatomy/build.mjs` 与 skill 模板）加「图形尺寸上限」脚本，`Base.astro` 的 `.clip` 视频加同样上限；skill 与第 3 节写入规则。1512 × 860 下各讲最大图高 ≤ 533px（原来最高 1134px），390 宽无横向滚动、无脚本错误。

- **2026-10-16 · Claude** — 按本人「什么是残差连接 → 写成教材」新增一讲：`src/content/blog/residual-connection.md`（series ai-mastery，**order 25**）+ 实验页 `public/labs/residual-connection/index.html`。实验里内嵌一个手写的小型 MLP（宽 16，按批前向/反向 + Adam，普通 = ReLU(Wh+b) He 初始化；残差 = h + W·ReLU(h) + b，分支按 1/√L 缩小），任务拟合 sin 5x + 0.5 sin 13x：00 两种网络 / 01 初始化时各层梯度大小（100 层普通网络第 1 层约为最后一层的 1e-5）/ 02 各层不同输入的平均余弦相似度 + 最后一层热力图（普通趋于 1）/ 03 6 / 30 / 100 层实时训练对比（100 层普通网络误差停在目标方差 0.728）/ 04 训练两个 30 层网络后逐层跳过看误差（页面加载后自动在后台分块训练）。这些数字先在 node 里用同一份代码验证过。Manim：`manim-src/residual-connection/scenes.py` → `public/videos/residual-connection/`。梯度下降一讲末尾改为衔接本讲。本地 build 通过；headless Chromium 检查 1440 浅色 / 390 深色无横向滚动、无脚本错误。

- **2026-10-16 · Claude** — 按本人「什么是梯度下降 → 写成教材」用 skill `write-lesson` 新增一讲：`src/content/blog/gradient-descent.md`（series ai-mastery，**order 20**，KV Cache 之后；公式用 HTML/Unicode 写，站点无 KaTeX，`Base.astro` 加 `.prose p.formula`）+ 实验页 `public/labs/gradient-descent/index.html`：01 一维曲线（碗 / 起伏两坑，切线 + 步子，可点选出发点）/ 02 ½ax² 上学习率 × 曲率，四种收敛情形与 2/a 上限（解析算步数）/ 03 圆碗、窄谷（κ=50）、Rosenbrock 上 GD、Momentum(β 0.9)、Adam 同时出发，各方法学习率在读数里标明，可调倍数 / 04 40 点拟合直线（种子固定的生成数据，MSE 梯度，最小二乘最优点与发散临界 2/λmax 由数据算出）/ 05 200 点、学习率 0.01、相同样本预算下 batch 1/8/32/200 的路线与损失曲线。Manim 源码 `manim-src/gradient-descent/scenes.py`，产物 `public/videos/gradient-descent/{Descent1D,Gradient2D}.{webm,png}`。本地 build 通过；headless Chromium 检查 1440 浅色 / 390 深色无横向滚动、无脚本错误。

- **2026-10-16 · Claude** — 按本人要求：(1) 文字铺满版面——去掉 `Base.astro`、`WhatsAppJoin.astro`、六个实验页（含 `labs-src/computer-anatomy/build.mjs`）和实验页模板里的 68ch / 892px 限制，页边距统一 `clamp(16px,3vw,40px)`；(2) 科学单位改英文缩写——internet-basics 文章与实验（km/ms、ms、s）、computer-anatomy 实验与生成脚本（TB/s、GB/s、s/ms/μs、token/s）。两条规则写进第 4 节与 skill `write-lesson`。检查 7 讲 1440 / 390 宽左边线与页眉对齐、无横向滚动、实验页无脚本错误。

- **2026-10-16 · Claude** — 按本人要求新建项目专用 skill `.claude/skills/write-lesson/`（问题 → 文章 + 实验页 + Manim 动画 → 上线 + 更新 HANDOFF，含三份模板）；新增 `manim-src/door4ai_style.py`、`manim-src/manim.cfg`；`Base.astro` 加 `.prose figure.clip` 视频样式；`.gitignore` 忽略 Manim 缓存。在云端装 Manim v0.22.0 实测：模板动画（中文、公式、配色）与实验页模板（深浅色、390px）均正常。

- **2026-10-16 · Claude** — 按本人要求隐去教材中的个人信息：网络实验「你在」改为 北京 / 合肥 / 纽约（默认北京，坐标同步，路由图节点扬州→合肥），文中「扬州到洛杉矶」改「上海到洛杉矶」（北京往返约 99 ms 会与「100 ms 以上」矛盾）；Git 实验示例仓库 `leaner47/demo` → `your-name/demo`。全量检索 src/content、public/labs、labs-src 已无扬州/波士顿/leaner47。第 4 节加「不出现个人信息」总规矩。

- **2026-10-16 · Claude** — 按本人要求去掉说明性小字：课程目录的 COURSE、导语、每篇的「第 N 篇 · M 讲」/副标题/说明、学习面板的「记录只保存在这台设备的浏览器里」；AI账号申请页的 APPLY 与说明句。`course.ts` 删 sub/desc 字段，`Base.astro` 删对应样式。第 4 节加「不主动加说明性小字」总规矩。

- **2026-10-16 · Claude** — 按本人要求学习面板去掉「已读」、重复读也算：文章页改为每次打开当天 +1（旧的 {日期: [讲]} 自动换算成次数，删 d4a-read）；`ai.astro` 汇总改为「学习 X 次 · Y 天 · 连续 Z 天」，删除已读/下一讲编号状态（`Base.astro` 对应样式）。本地用模拟数据验证计数、换算与连续天数。

- **2026-10-16 · Claude** — 按本人要求把课程目录顶部的进度条换成 GitHub 贡献图式的「学习记录」面板：文章页新增按天记录 `d4a-activity`，`ai.astro` 生成 53 周网格，`Base.astro` 删 `.progress` 样式、加 `.act*`。用模拟数据检查 1440 / 390 宽、深浅色、空记录状态。

- **2026-10-16 · Claude** — 按本人要求课程目录每讲去掉元信息行（第 N 讲 / 日期 / 含实验）、徽标（从这里开始 / 已读 / 下一讲）和标签，只留编号 + 标题，编号与标题垂直居中。改 `ai.astro`、`Base.astro`。

- **2026-10-16 · Claude** — 整体排版统一：新增 `src/data/course.ts`（分篇），`ai.astro` 按篇分组；`posts/[...slug].astro` 统一 full 布局，无实验文章改为与实验页一致的标题区，加上一讲/下一讲；`Base.astro` 的 `main` 版心改 892/16，新增 `.part*`、`.post-head`、`.pager` 样式；五个实验页 `.wrap` 改 892 border-box；computer-anatomy（含 `labs-src/.../build.mjs`）版心 860、h1 统一到 40px、补 eyebrow。本地检查 7 讲标题左边线全部 290px（1440 宽）、390px 无横向滚动、深浅色。

- **2026-10-16 · Claude** — 按本人要求把「Cloudflare 入门教材」（先在 Claude 文档里写成）加到网站：新增 `src/content/blog/cloudflare-basics.md`（series ai-mastery，order 3.5，无 lab，五大类模块 + 场景选型 + 大陆访问注意 + 练习（答案用 `<details>` 折叠）+ 术语表；导读里内嵌竖排请求路径 SVG，颜色用站点 token）；`Base.astro` 给 `.prose` 加 `figure.cf-flow` / `figcaption` / `details` 样式。本地临时副本 build 通过；headless Chromium 检查 1280 浅色 / 390 深色无横向滚动、图在深浅色下可读。注：order 用了小数 3.5，schema 是 z.number()，排序正常。

- **2026-10-15 · Claude** — 按本人要求把聊天里讲的「DNS 污染 / 路由 / 怎么连上互联网」做成课程一讲：`src/content/blog/internet-basics.md`（series ai-mastery，order 2.5）+ 实验页 `public/labs/internet-basics/index.html`：00 四个比方 / 01 出发地→服务器的环节链与距离延迟（真实城市坐标 + 光纤 204 km/ms + 绕远系数滑块）/ 02 IPv4 位串与地址段分类 + NAT 表（示例公网 IP 203.0.113.7）/ 03 DNS 逐级查询分步演示（含缓存命中）/ 04 十个城市的路由网络，Dijkstra 最短路径，可点线挖断、点节点看路由表、traceroute 输出 / 05 DNS 污染时序图（运营商 DNS、8.8.8.8、DoH、代理 fake-ip 四种方式 × 普通/被封域名；时间取自 04 的图）/ 06 打开网页的来回次数（TLS1.2/1.3/HTTP3、DNS 缓存、对比 CDN）。窄屏下路由图用单独的竖排坐标。本地 build 通过；headless Chromium 检查 1000 浅色 / 390 深色、无横向滚动、无脚本错误，文章页 iframe 自动长高。直接推 main（本人同意）。

- **2026-10-15 · Claude** — 按本人要求文章页实验去掉外框，改成和单独打开实验页一样：`posts/[...slug].astro` 有 lab 时用 `full` 布局、整宽 iframe、不渲染文章自己的标题区；`Base.astro` 删 `.lab-frame`，加 `.lab-embed` / `.post-body` / `.sr-only`；五个实验页（及 `labs-src/computer-anatomy/build.mjs`）删掉嵌入时隐藏标题的样式。本地检查 1440 / 390 宽、深浅色、正文与实验左对齐。

- **2026-10-15 · Claude** — 经本人授权在线上 D1 执行 0002 迁移（核对：orders 新增 7 列、默认价 ai-mastery@default 399），随后把分支 `payments` 合入 main 上线。等本人在 Pages 设支付宝三个 Secret。

- **2026-10-15 · Claude** — 支付第 1 期写完，推到分支 `payments`（未合入 main，等线上 D1 迁移）。新增 `functions/_lib/pay/{alipay,orders}.ts`（纯 WebCrypto 的 RSA2 签名/验签，PKCS#1 私钥自动转 PKCS#8；响应签名按原文子串校验）、`functions/api/pay/{price,checkout,order}.ts`、`functions/api/pay/alipay/notify.ts`、`src/pages/pay/return.astro`、`migrations/0002_payments.sql`；后台加订单、退款、价格接口与页面；`scripts/mock-alipay.mjs` 模拟支付宝网关，`scripts/test-pay-e2e.mjs` 30 项（渠道定价、验签、重复通知幂等、伪造/改金额通知被拒、查单补单、手机 wap、退款收回权限）。修了 `test-auth-e2e` 里强制下线一项的时序竞争。

- **2026-10-14 · Claude** — 按本人要求把 Pages 变量 `SYNC_KEY` 从明文改为 Secret（值不变），本次提交触发重新部署使其生效。

- **2026-10-14 · Claude** — 本人在 Safari 完成线上注册登录（验证码邮件由 Resend 从 login@door4ai.com 发出）。经本人确认删除 Access 应用「Door4AI Lab」（含 Door4AI Lab students 白名单）；外部检查：/posts、/labs 未登录跳 /login/，/ai/ 公开，/admin 仍在 Access 后。

- **2026-10-14 · Claude** — 在 Cloudflare / Resend 控制台启用账号系统（见第 5 节）。D1 表通过控制台 Console 执行 0001 的 SQL 建立。推这条提交以触发带新环境变量的部署。

- **2026-10-14 · Claude** — 新增「AI账号申请」：头像菜单加入口；`src/pages/ai/apply.astro`（表单 + 我的申请 / 管理员全部申请与改状态）；`functions/ai/apply/api.ts`（R2 存储、校验、24h 限 5 条、管理员 PATCH）；`gate.ts` 加 `ai/apply` 需登录。本地 wrangler pages dev（R2 本地 + 模拟 Access 头）端到端验证：未登录 401、校验报错、学员提交、非管理员 PATCH 403、管理员改状态与回复、深浅色与 390px。

- **2026-10-14 · Claude** — Git 讲（order 3）插到了硬件讲与 Token 讲之间，Token 讲文末「上一讲讲的显存和带宽」改为「第 1 讲」。Mac 本地副本已与 main 同步。

- **2026-10-15 · Claude** — 按本人要求新增入门讲《Git 和 GitHub：代码的时光机与云端仓库》（`src/content/blog/git-github.md`，series ai-mastery，order 3）+ 实验页 `public/labs/git-github/index.html`：00 Git 与 GitHub 的区别 / 01 工作区→暂存区→仓库（含真实格式的 `git status` 输出、点旧提交看快照）/ 02 SHA-1 指纹（页内实现 SHA-1，blob 哈希与 `git hash-object` 逐位一致，已用 `hello\n` → ce01362… 验证）+ 提交链 parent 哈希连锁变化 / 03 分支与合并提交图（fast-forward 与合并提交两种情况）/ 04 你、GitHub、同学三方 clone/commit/push/pull，含 push 被拒（fetch first）与 pull 生成合并提交 / 05 Pull Request 十步演示 + PR 卡片；末尾 Git vs GitHub 对比表与命令速查。`access-map.ts` 随构建重新生成。本地 build 通过；headless Chromium 检查 1000px 浅色 / 390px 深色、无横向滚动、无脚本错误。注意：Mac 连接文件夹里 astro build 清理 dist 时需要删除权限，本次在临时副本里构建。

- **2026-10-14 · Claude** — 按本人要求把课程目录顶部的 WhatsApp 群卡片移进头像菜单：`WhatsAppJoin.astro` 的 card 改为 menu 变体（可展开，二维码 + 加入按钮，`data-signed-in` 登录后显示），`Base.astro` 引入并通用化展开逻辑，`ai.astro` 删卡片。文章末尾一行保留。

- **2026-10-14 · Claude** — 新文章《Token 是什么：一句话是怎么进出大模型的》（`src/content/blog/tokenizer-llm.md`，series ai-mastery，**order 4**，排在硬件讲之后、注意力讲之前）+ 实验页 `public/labs/tokenizer-llm/index.html`：00 真实分词器（GPT-2 `gpt2` 与 GPT-4o `o200k_base`，色块 + 字节碎片 + 编号）/ 01 字母级 BPE 逐步训练（语料可改、可后退、自动播放）/ 02 用学到的规则切新词 / 03 在浏览器里对约 500 字中文语料训练字节级 BPE，拖合并次数看字节→字→词 / 04 GPT-2 small、Llama-3-8B、Llama-3-70B 五站流水线（形状与参数占比按公开架构参数计算）/ 05 Prefill 与 Decode 动画 + KV Cache 增长 / 06 温度与 top-p（logits 来自同一段语料上的字级 3-gram，采样部分与真模型一致）。分词器打包为同目录 `tiktoken.js`（js-tiktoken 1.0.21 lite + gpt2 + o200k_base 词表，esbuild IIFE，2.9 MB / gzip 1.4 MB，暴露 `window.TK`，加载完发 `tk-ready` 事件）。SVG 按实际宽度布局（`vw()`），手机上流水线改为单列。本地 build 通过；headless Chromium 检查 1200 / 390 宽、深浅色、各实验交互、文章页 iframe 自动长高、无横向滚动。从云端会话推送；Mac 本地副本需 `git pull`。

- **2026-10-14 · Claude** — 按本人要求首页只留「Attention is all you need」：`Base.astro` 新增 `bare` prop（不渲染页眉、页脚），`index.astro` 整页改为指向 `/ai/` 的链接。

- **2026-10-14 · Claude** — 按本人要求把 Resource 从顶部导航移进头像下拉菜单（个人资料之后、外观之前）。改 `Base.astro`。

- **2026-10-14 · Claude** — 按本人要求整个去掉右上角「支持」入口（`Base.astro` 的链接与样式）。WhatsApp 群卡片的 `#community` 锚点保留。

- **2026-10-14 · Claude** — 线上检查发现账号系统关闭时 `/admin/` 空壳页面可公开访问（无数据，接口均返回 503）。中间件改为：未启用时 `/admin` 一律 404。测试 43/43 + 9/9。

- **2026-10-14 · Claude** — 账号系统：两步验证 + 后台。新增 `functions/_lib/auth/{totp,mfa,admin}.ts`、`functions/api/auth/mfa.ts`、`functions/api/me/totp/[action].ts`、`functions/api/admin/[[path]].ts`、`src/pages/admin.astro`；login / account 页加两步验证界面（二维码、「添加到 Apple 密码」otpauth 链接、恢复码）；中间件 `/admin` 走 Access JWT + ADMIN_EMAILS。无需新表（复用 0001 的 totp_factors、recovery_codes、channels、audit_log；第二步票据存 webauthn_challenges kind='mfa'）。测试扩到端到端 43 项 + JWT 9 项，全过；合并了另一会话的新版页眉（账号菜单已接 /api/me），测试改查 `#acct-email`。线上仍为关闭状态。

- **2026-10-14 · Claude** — 按本人要求去掉右上角「支持」前的问号图标，只留文字（手机上也显示文字）。改 `Base.astro`。

- **2026-10-14 · Claude** — 右上角改为「支持 + 头像下拉菜单」，并加站点级外观切换（跟随系统 / 浅色 / 深色）。改 `Base.astro`（token 支持 data-theme、head 早期脚本、菜单结构与脚本，兼容 /api/me 与 Access 两种登录）、`WhatsAppJoin.astro`（卡片 id=community、深色规则改两段写法）、三个实验页及 `labs-src/computer-anatomy/build.mjs`（加载时读 `d4a-theme`）。本地 build 通过；Playwright 模拟登录检查菜单、子菜单、切深色后文章页与 iframe 同步、390px 无横向滚动、Esc 关闭。

- **2026-10-14 · Claude** — 账号系统第 0 期：新增 `migrations/0001_init.sql`（15 张表 + 限流、挑战值表）、`functions/_lib/auth/*`、`functions/api/auth/*`、`functions/api/me/*`、中间件门禁与来源 Cookie、构建前生成 `access-map.ts`、`/login/` `/account/` `/pricing/` 三页、导航改调 /api/me；依赖加 `@simplewebauthn/server|browser@13`。全部由 `AUTH_ENABLED=1` + D1 绑定开启，未开启时线上行为与之前一致（本地验证：课程页直通、API 返回 503、pages.dev 跳转正常）。本地 `scripts/test-auth.sh` 端到端 22/22 通过；修了一个全局问题：页面 CSS 的 display 会覆盖 `hidden` 属性，Base.astro 加 `[hidden]{display:none!important}`。

- **2026-10-14 · Claude** — 按本人要求：文章页里的实验 iframe 不再是固定高度的内部滚动区，改为随内容自动长高（同源，`posts/[...slug].astro` 里的 `data-autosize` 脚本量 contentDocument.scrollHeight + ResizeObserver；`scrolling="no"`），整页只有一个滚动条。

- **2026-10-14 · Claude** — 按本人要求去掉文章页实验框顶部的「可交互实验 / 全屏打开 ↗」条（`posts/[...slug].astro`），实验 iframe 直接嵌入即可交互。

- **2026-10-14 · Claude** — 按本人要求去掉课程目录 /ai 每讲标题下的 description 小字（`ai.astro`）。

- **2026-10-14 · Claude** — 按本人要求修订设计：计费只保留买断（去掉月卡/年卡订阅及相关字段）；防共享改为每账号同时只允许 1 个会话，新登录踢掉旧会话。未改代码。

- **2026-10-14 · Claude** — door4ai.com 卡片 logo 改为文字「AI」（新增 `public/logos/ai-text.svg`，`look` 表指向它，scale 0.5）。

- **2026-10-14 · Claude** — 加 WhatsApp 交流群入口：`src/data/community.ts`、`src/components/WhatsAppJoin.astro`（WhatsApp 绿按钮 + 构建时生成的二维码，手机宽度隐藏二维码、按钮通栏直接唤起 App）、`public/logos/whatsapp.svg`（Font Awesome Free，CC BY 4.0）；`ai.astro` 顶部卡片、`posts/[...slug].astro` 课程文章末尾一行；新增依赖 `qrcode`。本地 build 通过，深浅色 + 390px 无横向滚动检查通过。

- **2026-10-14 · Claude** — 按本人要求修订设计文档：不设密码，改为 Passkey（WebAuthn）主登录 + 邮箱验证码兜底 + 可选 TOTP（Apple 密码 App 可存）；新增注册来源归因（首次/最后触达、UTM、ref 渠道码）；说明数据库选 D1 而非 PG 的理由。未改代码。

- **2026-10-14 · Claude** — 按本人要求把 Codex、Claude 闪卡的 preset 从 glitter（细碎点阵）改为 shards，与 FlClash 纹路一致（`resources.astro` 的 `look` 表）。

- **2026-10-14 · Claude** — Safari/iPhone 全息层左上角小块：第四次修复，定位到根因是 WebKit 从 SVG `<img>` 上传 WebGL 纹理时用显示尺寸的栅格缓存（见第 4 节「Safari / iOS 注意」）。`holo-card.js` 改为先 drawImage 到 630×880 的 2D canvas 再上传。Chromium 本地验证正常；`resources.astro` 里 `#debug` 覆盖层暂留，待本人 iPhone 确认后删除。

- **2026-10-14 · Claude** — 按本人要求出了「lab.door4ai.com 账号与支付系统设计」文档（链接见第 5 节）：邮箱验证码登录、D1 十张表、买断/订阅统一为 entitlement、pay-api 适配器 + 回调幂等 + 对账 Worker、中间件替换 Access 的迁移顺序、四期上线计划。pay-api.door4ai.com 从云端和 Mac 出口都访问不到（403），接口细节列为待确认。未改代码。

- **2026-10-14 · Claude** — Safari 左上角小块问题复现（间歇）：第三次修复，画布缓冲区改为标记里固定 2x 尺寸，JS 不再改缓冲区尺寸。

- **2026-10-14 · Claude** — 全站设计修整：(1) 导航改为 flex + gap，修复手机上换行后首项缩进；(2) 三个实验页的标题/导语加 `.lab-intro`，嵌入文章页时隐藏、收紧顶部留白（computer-anatomy 同步改了 `labs-src/.../build.mjs`）；(3) HoloCard 卡面小字放大（软件名 54、平台副标 50、「点击下载」48，SVG 单位）；(4) 课程目录重做为大号编号 + 「从这里开始」/「已读」/「下一讲」标记 + 本机阅读进度条，文章页写入 localStorage。改 `Base.astro`、`ai.astro`、`posts/[...slug].astro`、`HoloCard.astro`、三个实验页。本地 build 通过，headless Chromium 检查 390px 无横向滚动、深浅色。

- **2026-10-14 · Claude** — Codex 卡改为黑金配色（HoloCard 新增 intensity / tint props，look 表可按软件调）。

- **2026-10-14 · Claude** — Safari 全息层问题经本人截图确认已修复（显式像素尺寸 + 平铺布局），删除 `?debug` 调试覆盖层。

- **2026-10-14 · Claude** — 去掉 Resource 页顶部的 eyebrow + h1；加 `?debug=1` 调试覆盖层（打印第一张卡与画布的尺寸）用于排查 Safari 全息层只画在左上角的问题（撤掉 3D 后仍存在）。

- **2026-10-14 · Claude** — 发现 `door4ai-lab.pages.dev` 不经过 Access、课程内容可匿名访问。新增 `functions/_middleware.ts`：hostname 以 `.pages.dev` 结尾的请求 301 到 `lab.door4ai.com` 同路径（含查询参数）。tsc 与 build 通过，上线后验证。

- **2026-10-14 · Claude** — Resource 页软件名改为居中。

- **2026-10-14 · Claude** — 按本人要求：「token」一词不翻译。computer-anatomy 实验页与文章里的「词/秒」「生成每个词」改为「token/秒」「生成每个 token」（`labs-src/computer-anatomy/sec23.mjs` 重新生成）。

- **2026-10-14 · Claude** — 按本人要求去掉 Resource 页所有介绍性文字：页面导语、各软件说明段、卡片下的版本/大小小字；版本信息改为卡片悬停提示。


- **2026-10-14 · Claude** — 新文章《电脑里到底有什么：CPU、GPU、内存、显存与 Docker》（`src/content/blog/computer-anatomy.md`，series ai-mastery，**order 2**，排在注意力之前，作为零基础入门讲）+ 实验页 `public/labs/computer-anatomy/index.html`：五张可交互等距实物图（Anatomy skill 风格）——Fig1 CPU/GPU 芯片并行 vs 串行赛跑；Fig2 主板+显卡，模型大小滑块填充显存/内存颗粒并给出带宽上限 token/s；Fig3 M4 Max 式统一内存封装（与 Fig2 共用滑块对比）；Fig4 Docker 集装箱船+龙门吊装卸；Fig5 机柜服务器 vs 书桌个人电脑+对比表。数字取公开规格（4090 82.6 TFLOPS / 1008 GB/s，DDR5 双通道 89.6 GB/s，M4 Max 546 GB/s）。生成脚本放 `labs-src/computer-anatomy/`（kit 不入库，见其 README）。本地 build 通过；headless Chromium 检查桌面、390px 无横向滚动、深浅色、线端检查 0。从云端会话推送。
- **2026-10-14 · Claude** — 按本人要求撤掉 3D 转盘，卡片改为一排平铺 + 横向平滑滚动（CSS scroll-snap，无 JS）；删除 `circular-carousel.js`。去掉 3D 容器后 Safari 的画布尺寸问题应随之消失（待本人确认）。

- **2026-10-14 · Claude** — Safari 全息层只占左上角小块：第二次修复，holo-card.js 的 resize() 现在把卡片、rotor、face、img、canvas 全部钉成显式像素尺寸（Safari 对 3D 容器里百分比高度解析异常）。

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

1. **课程规划（2026-10-16 立项，2026-10-19 全部写完上线）**：
   - 基础篇：`ai-coding-tools` 3.8 AI Coding 入门（Claude Code / Codex 怎么用，接 Resource 页）
   - 模型篇：`backpropagation` 30 反向传播 · `layernorm` 35 LayerNorm · `lora` 40 LoRA · `model-evaluation` 45 模型评测
   - Agent 篇：`tool-calling` 100 工具调用 · `agent-loop` 105 Agent Loop 与 ReAct · `context-window` 110 上下文与记忆 · `rag-embedding` 115 Embedding 与 RAG · `mcp` 120 MCP · `streaming` 125 流式输出（SSE）· `trace-eval` 130 Trace 与 Eval · `gateway-orchestration` 135 多模型网关与多 Agent 编排 · `agent-frameworks` 140 框架全景（纯文字）
   - 补充（2026-10-22）：`post-training` 41 后训练总览 · `scaling-laws` 38 Scaling Laws · `pretraining` 37 预训练 · `positional-encoding` 6 位置编码与 RoPE · `reasoning-models` 43 推理模型
   - 补充（2026-10-22）：`prompt-engineering` 99 Prompt 工程（Agent 篇第一讲）
   - 补充（2026-10-22 已写）：`vision-tokens` 48 模型怎么看图
   - 补充（2026-10-22 已写，并行）：`inference-serving` 13 推理服务 · `overfitting` 22 过拟合与泛化 · `distributed-training` 39 分布式训练 · `distillation` 44 蒸馏 · `diffusion-models` 50 扩散模型（`agent-security` 132 未完成）
   - 补充（2026-10-22 已写）：`vectors-softmax` 4.5 向量、矩阵乘法与 softmax（数学讲）
   - 补充（2026-10-19 已写）：`multihead-gqa` 7 · `weight-quantization` 12 · `mixture-of-experts` 15 · `rlhf-alignment` 42 · `agent-harness` 107 · `browser-computer-use` 122
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
