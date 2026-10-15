# HANDOFF — Door4AI Lab (lab.door4ai.com)

> 这份文件是本项目的唯一交接入口。任何 AI 或人接手时**先读完本文件**，再动手。
> 任何一次工作结束前，**必须**按文末「更新协议」更新本文件并提交。没有更新 HANDOFF 的工作视为未完成。

最后更新：2026-10-14 22:54 America/New_York · 更新者：Claude（会话 session_01QvBhNRgUqPZf8fhAnjTAx7）

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
| 登录/访问控制 | Cloudflare Access（Zero Trust）应用 **Door4AI Lab**：保护 `lab.door4ai.com/ai`、`/resources`、`/posts`、`/labs` 四个路径；策略 **Door4AI Lab students**（Allow，按邮箱白名单，目前只有本人邮箱）；会话 1 个月；登录方式为邮箱一次性验证码（One-time PIN）。首页 `/` 公开。**`*.pages.dev`（生产与预览）不走 Access，由 `functions/_middleware.ts` 把所有请求 301 跳到 `lab.door4ai.com` 同路径**，所以内容只能经登录访问；手动同步请用 `https://lab.door4ai.com/sync-dl?...`。**加学员 = 在该策略的 Emails 列表里加邮箱**（Zero Trust → Access controls → Policies）。不要改 grafana / AI Gateway Admin 那两个应用和「Only me」策略。 |
| 安装包镜像 | R2 桶 `door4ai-lab-dl`（APAC 位置提示，私有），绑定到 Pages 项目为 `DL`；Pages 环境变量 `SYNC_KEY`（手动同步口令，值只在 Cloudflare 设置里）。下载走 `/dl/<app>/<platform>`（在 Access 保护内），状态看 `/dl/manifest.json`；手动同步 `GET /sync-dl?key=<SYNC_KEY>[&app=flclash\|claude\|codex][&force=1]`（/sync-dl 不在 Access 内，靠口令保护）。下载时若某项超过 24h 未同步会在后台自动刷新。 |
| GitHub App | Cloudflare Workers and Pages 已授权仓库：`door4ai-lab`、`door4ai-site`（后者是别的项目，不要动） |
| 自建账号（第 0 期，代码已上线、**默认关闭**） | 开关：Pages 环境变量 `AUTH_ENABLED=1` **且** 绑定了 D1（binding 名 `DB`，库名 `door4ai-lab`）才启用；否则中间件什么都不做，仍由上面的 Cloudflare Access 把关。其他变量：`ADMIN_EMAILS`（逗号分隔，这些邮箱视为拥有全部权益）、`RESEND_API_KEY`（Secret）+ `MAIL_FROM`（发验证码邮件，建议在 Resend 验证 `lab.door4ai.com` 子域，避免动根域名记录）、`TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET`（Secret，登录页人机校验）、`TOTP_ENC_KEY`（Secret，base64 的 32 字节随机数，加密存储两步验证密钥；不设则不提供两步验证；**设了之后不能换，换了已开启两步验证的用户全部失效**）、`ACCESS_TEAM_DOMAIN`（如 `xxx.cloudflareaccess.com`）+ `ACCESS_AUD`（/admin 所在 Access 应用的 AUD Tag）。**后台 `/admin`**：必须在 Access 应用里保护 `/admin` 路径（只放行本人），中间件再验 Access JWT 并核对 `ADMIN_EMAILS`，两层都过才进。表结构 `migrations/0001_init.sql`，用 `npx wrangler d1 execute door4ai-lab --remote --file migrations/0001_init.sql` 建表。启用并验证后，再从 Access 应用里移除 `/ai` `/resources` `/posts` `/labs` `/dl`（顺序反了课程会短暂公开）。**仓库里不能放 wrangler.toml**：它会覆盖控制台里的 `DL`、`SYNC_KEY` 等绑定；本地测试脚本只临时生成、退出即删（已加入 .gitignore）。 |
| 本机副本 | `~/Documents/Agents/door4ai-lab`（Mac），是 GitHub 仓库的 clone |

账号登录：Cloudflare 和 GitHub 都由本人登录；AI 不持有、不输入任何密码。需要 sudo/passkey 验证时交给本人操作。

## 3. 技术栈与目录结构

Astro 5 静态站，无 UI 框架，无 Tailwind。依赖只有 `astro`、`@astrojs/rss`、`@astrojs/sitemap`、`qrcode`（构建时生成 WhatsApp 群二维码 SVG）。

```
door4ai-lab/
├── HANDOFF.md              ← 本文件
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
│   ├── data/community.ts   ← WhatsApp 交流群名称与邀请链接（url 置空 = 全站隐藏入口）
│   ├── components/WhatsAppJoin.astro ← 群入口：card（课程目录顶部，电脑端带二维码）/ inline（课程文章末尾一行）
│   ├── data/resources.ts   ← Resource 页的条目（link.dl = 镜像 id 走 /dl/，link.url = 外链）
│   ├── layouts/Base.astro  ← 全站布局 + 导航 + 全部 CSS；右上角头像按钮下拉菜单（邮箱 / 个人资料 / 外观 / 退出登录，未登录时首项为「登录」），登录状态先调 /api/me（自建账号启用时用它），否则回退到 /cdn-cgi/access/get-identity；全局 `[hidden]{display:none!important}`；prop `full` 让 main 占满宽度（首页用）
│   └── pages/
│       ├── index.astro         ← 首页：只有居中的一句 motto，入口全在导航
│       ├── ai.astro            ← 「AI 从入门到精通」课程目录：series == 'ai-mastery' 的文章按 order 排序
│       ├── resources.astro     ← Resource 资源库，数据来自 src/data/resources.ts
│       ├── admin.astro         ← 后台：概览（注册数、来源与转化、问卷、每日注册）/ 用户（搜索、详情、开通/撤销、强制下线、停用、重置两步验证）/ 渠道码（链接 + 二维码 + 注册/付费统计）/ 操作日志
│       ├── login.astro / account.astro / pricing.astro ← 登录（邮箱验证码 + Passkey + 两步验证）/ 我的账号（两步验证开关、恢复码、Passkey 管理、已购课程、推荐链接、来源问卷）/ 购买页（支付未开放，占位）
│       ├── posts/[...slug].astro ← 文章页；frontmatter 有 lab 时顶部 iframe 嵌入实验
│       └── rss.xml.js
├── functions/              ← Cloudflare Pages Functions（随仓库自动部署）
│   ├── _lib/sources.ts     ← 镜像源：每个 target 的 resolve()（FlClash=GitHub latest；Claude=官方 latest 重定向 + apt 索引；Codex=codex-app-prod/ChatGPT.dmg）
│   ├── _lib/mirror.ts      ← 同步逻辑：解析→下载→流式写入 R2→更新 manifest.json
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
- 实验页开头的标题 + 导语必须带 `class="lab-intro"`，并在 `</head>` 前放嵌入检测片段（照抄现有实验页）：被文章页 iframe 嵌入时自动隐藏，避免和文章标题重复；「全屏打开」时照常显示。

## 4. 已做的关键决定（不要反复讨论）

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
- 首页极简：页眉左右贴屏幕两端（全宽），屏幕中央一句「Attention is all you need」撑满剩余高度；没有标题、介绍或卡片。导航：AI从入门到精通 / Resource / 登录（无「关于」页）。新增板块 = 新增一个页面 + 导航里加一项 + 若需登录则在 Access 应用里加该路径。
- 课程与资源页必须登录才能看（Cloudflare Access），首页公开。
- Resource 页顺序固定：**Codex → Claude → FlClash → door4ai.com**（`src/data/resources.ts` 的数组顺序）。**Resource 页没有页面大标题**（去掉了居中的「Resource」h1）；**每个软件名居中显示**；**不写任何介绍文字**：没有页面导语、没有软件说明段、卡片下方没有版本/大小小字（版本与大小只放在卡片 title 悬停提示里）。`resources.ts` 里的 `note` 字段保留但页面不渲染。每个软件的卡片在一行里平铺（`.cardrow`：flex + 横向滚动 + scroll-snap，放得下时居中，放不下时左右平滑滑动）。**不要再做 3D 转盘**，本人已明确否决。
- Resource 页：每个软件一个分组（标题 + 说明），**每个平台的下载按钮本身是一张 HoloCard 全息卡**：卡面布局：顶部小号软件 logo + 软件名，中间**大号平台图标**（macOS 苹果 / Windows 田字 / Linux 企鹅 / Android 机器人，`public/logos/apple|windows|linux|android.svg`，取自 Font Awesome Free 6，CC BY 4.0），图标下平台名，底部「点击下载」。软件 logo：flclash.png 来自 FlClash 仓库，openai.svg / claude.svg 来自 @lobehub/icons-static-svg（MIT），door4ai.com 的卡片 logo 是文字「AI」（`public/logos/ai-text.svg`，Times New Roman 粗体，本人指定，不用 favicon）。平台→图标的映射在 `resources.astro` 的 `platformLogo()`；没有匹配平台（如 door4ai 的「打开」）时中间放软件 logo。箔纹颜色跟随品牌色：`look` 表里每个软件配 logo / preset / accent（光晕、边框）/ foil（箔片色）/ intensity / tint。**Codex 定稿为黑金**（黑底 + 金色箔纹，accent #9a7a2a，foil #f6d27a，intensity 0.55，tint 0.95），本人明确要求。**箔纹统一用 `shards`（碎片纹）**：本人否决了 glitter 的细碎点阵，Codex / Claude / FlClash 三者纹路必须一致（door4ai.com 用 gold）。着色器新增 `uTint`（data-tint，默认 0.65）把彩虹箔向品牌色拉。卡下小字显示版本 · 大小 · 同步日期。
- **Safari / iOS 注意（全息层只画在卡片左上角一小块）**：真正的原因是 WebKit 的 `texImage2D()` 从 SVG `<img>` 上传纹理时，用的是该 SVG 在页面上**显示尺寸**（170px 海报图）的栅格缓存，而不是 SVG 固有尺寸 630×880，于是整张卡面被塞进纹理左上角约 27%（=170/630）的区域。iPhone `#debug` 数据证明 CSS 盒、drawingBuffer、viewport 全部正确，所以**不是尺寸问题，别再在 CSS/resize 上找**。修法在 `holo-card.js` 的 `img.onload`：先把 SVG `drawImage()` 到一张 630×880 的 2D canvas，再把这张 canvas 交给 `texImage2D`（drawImage 对 SVG 总是按目标尺寸重新渲染）。保留的防御措施：画布缓冲区在标记里固定为 CSS 尺寸 2 倍（`<canvas width height>`），JS 不在首次绘制后改 canvas.width/height。Safari 对 HTML 缓存很顽固，看不到新版本先 ⌘⇧R / iPhone 清站点数据。
- 安装包由本站 R2 镜像、仅登录用户可下（/dl 在 Access 内）。Codex 桌面版已并入新版 ChatGPT 桌面应用：macOS 镜像 `codex-app-prod/ChatGPT.dmg`，Windows 只有 Microsoft Store（不镜像，外链），Linux 为 CLI（外链）。新增镜像目标 = 在 `functions/_lib/sources.ts` 加一个 target，并在 `src/data/resources.ts` 加 `dl:` 按钮。
- **WhatsApp 交流群「AI学习」**：入口放在已登录才能看的页面里（课程目录顶部卡片 + 属于课程的文章末尾一行），不放公开首页、不放 Resource 页，因此不需要改 Access。链接用干净的邀请地址（去掉 `?s=cl&p=i…` 分享参数）。入群需管理员审核（WhatsApp 里设置）。**重置群链接后只需改 `src/data/community.ts` 再推送**，二维码会随构建自动更新。
- 文章页实验 iframe **必须随内容自动长高、不得有内部滚动条**，也不要「全屏打开」条（本人要求）。实验页本身别用 100vh 之类固定高度。
- **右上角账号区（2026-10-14 本人要求，仿常见 SaaS 样式）**：导航链接之后只有一个圆角方形头像按钮（**不要「支持」入口**，本人已明确去掉）；点开下拉菜单：已登录时顶部显示邮箱，下面「个人资料」（仅自建账号启用时显示，链 /account/）、「外观 ›」（展开为 跟随系统 / 浅色 / 深色）、分隔线、「退出登录」；未登录时首项为「登录」。截图里的 Language / View mode 没做（站点只有中文、无其他视图），需要时再加。Esc 和点外部关闭。
- **外观切换**：存 localStorage `d4a-theme`（light / dark，缺省 = 跟随系统），`<head>` 里内联脚本在渲染前设 `<html data-theme>`，避免闪烁。CSS token 写法：`@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){…} }` + `:root[data-theme="dark"]{…}`，**新增的深色样式都要照此两段写**。实验页同源，加载时读同一个键；切换时父页面直接改 iframe 的 `data-theme`（实验页已有 MutationObserver 重绘画布）。
- 课程目录 /ai：每讲左侧大号编号；**目录里不显示文章 description 小字**（本人要求，只留编号、元信息、标题、标签；description 仍用于文章页与 SEO）；第一讲标「从这里开始」；阅读进度只存本机浏览器 localStorage（键 `d4a-read`，文章页打开即记为已读），有已读时显示进度条、「已读」与「下一讲」标记。不做账号级进度。
- 课程顺序：注意力 QKV（order 5）在前，KV Cache（order 10）在后，因为 KV cache 建立在 Q/K/V 概念上。课程目录的「第 N 讲」由 order 排序自动生成。

- **账号与计费（2026-10-14 本人确认）**：自建账号，D1 不用 PG；不设密码，Passkey 为主、邮箱验证码注册与兜底、TOTP 可选（未做）；每账号同一时间只允许 1 个会话，新登录踢掉旧会话；只做买断，不做订阅；买全套包含以后新增的讲；收款复用 door4ai.com 的 pay-api（接口文档待本人提供）；记录注册来源（首次/最后触达 UTM、ref 渠道码、来源问卷）。设计文档：https://claude.ai/code/artifact/9679fc7a-0fe4-4323-86f1-65cbb1cc005f
- 两步验证只在「邮箱验证码登录」时要求；Passkey 登录不需要（Passkey 本身就是强认证）。新注册的第一次登录不要求（还没开）。
- 后台不做自建管理员账号：身份来自 Cloudflare Access + `ADMIN_EMAILS`，所有写操作记 `audit_log`。
- 门禁规则：`/admin/` 走后台校验；`/` `/ai/` `/login/` `/pricing/` 公开；`/resources/` `/dl/` `/account/` 需登录；`/posts/<slug>/` 与对应 `/labs/<name>/` 按文章：`access: free` 登录即可，属于 series 的需要 `series:<name>` 或 `post:<slug>` 权益（或 `all`，或 ADMIN_EMAILS）。

## 5. 当前状态

- [x] 仓库、Pages、域名、首篇文章全部上线（2026-10-13）
- [x] 本机 `~/Documents/Agents/door4ai-lab` 已与 GitHub 同步
- [x] 首页改为入口模块布局；新增 /ai/ 课程目录与 /resources/ 资源库（2026-10-13）
- [x] 安装包镜像上线并验证：12 个文件（FlClash v0.9.0 ×6、Claude 2.37337.1 ×5、Codex/ChatGPT.dmg ×1），登录后点击即下，支持断点续传（2026-10-14）
- [x] 新增《注意力里的 Q、K、V 到底在干什么》+「注意力实验室」六个实验，排为第 1 讲（order 5），KV Cache 顺延为第 2 讲（2026-10-14）
- [x] 新增入门讲《电脑里到底有什么：CPU、GPU、内存、显存与 Docker》+ 五个等距图解实验，排在课程最前（order 2）（2026-10-14）
- [ ] 下一讲：题目未定（候选见第 7 节）
- [ ] 关于页只有两句话，待充实
- [ ] 没有统计/分析（可考虑 Cloudflare Web Analytics，免费，一行脚本）
- [x] 账号系统第 0 期代码完成并推送（默认关闭，线上行为不变）：邮箱验证码注册/登录、Passkey、单会话、注册来源、门禁、登录/账号/购买占位页；本地端到端 22/22 通过（2026-10-14）
- [ ] **启用第 0 期（需本人在 Cloudflare 操作）**：建 D1 `door4ai-lab`（位置选亚太）→ 跑 migrations → Pages 绑定 `DB` → Turnstile 建站点 → Resend 验证 `lab.door4ai.com` 并建 API key → 设环境变量（`ADMIN_EMAILS`、`RESEND_API_KEY`、`MAIL_FROM`、`TURNSTILE_*`，最后 `AUTH_ENABLED=1`）→ 重新部署 → 自测 → 从 Access 移除课程路径
- [ ] 加学员（支付上线前）：启用后台后直接在 /admin「用户 → 开通课程」里填邮箱（对方没注册也行）；未启用后台时执行 `npx wrangler d1 execute door4ai-lab --remote --command "INSERT INTO entitlements (id,user_id,scope,source,starts_at) SELECT lower(hex(randomblob(13))), id, 'series:ai-mastery', 'grant', unixepoch()*1000 FROM users WHERE email='学员邮箱'"`
- [x] 两步验证（TOTP，Apple 密码可直接添加）+ 10 个恢复码 + 防重放；后台 /admin（概览、用户、渠道码、日志）。本地 43/43 + 9/9 通过（2026-10-14）
- [ ] 启用后台：Access 应用加 `/admin` 路径；Pages 设 `ACCESS_TEAM_DOMAIN`、`ACCESS_AUD`；两步验证需设 `TOTP_ENC_KEY`（`openssl rand -base64 32` 生成）
- [ ] 后台还没有：订单列表、退款（第 1 期支付上线时一起做）
- [ ] 第 1 期 买断支付：等本人提供 pay-api 接口文档（签名算法、回调格式、查单/退款接口）
- [ ] 哪几讲免费试听未定（在文章 frontmatter 写 `access: free` 即可）

## 6. 工作日志（倒序，每次工作追加一条）

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
