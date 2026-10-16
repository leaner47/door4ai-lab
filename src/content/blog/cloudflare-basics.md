---
title: "Cloudflare 是做什么的：一张全球网络上的五类功能"
description: "Cloudflare 站在网站和访问者之间，先帮网站加速和挡攻击，后来又让开发者直接在它的网络上写代码、存数据、跑 AI。按网络与性能、应用安全、开发者平台、Zero Trust、实用工具五类讲清每个模块，最后给出常见场景的组合与选型。"
pubDate: 2026-10-16
tags: ["入门", "工具", "Cloudflare", "部署", "网络"]
series: ai-mastery
order: 3.5
---

## 导读

Cloudflare 是一张覆盖全球 300 多个城市的网络。它站在网站和访问者之间，先帮网站加速和挡攻击，后来又让开发者直接在这张网上写代码、存数据、跑 AI。你现在看的这个课程网站，就托管在 Cloudflare 上。

读完这一讲，你应该能：

1. 理解 Cloudflare 的核心工作方式：反向代理 + 全球边缘网络。
2. 按五大类说出主要模块及其用途。
3. 为博客、API、内网服务等常见场景选出合适的组合。
4. 了解在中国大陆使用时的限制。

### 核心概念：反向代理

把域名的 DNS 交给 Cloudflare，并打开「橙色云朵」（代理模式）之后，访问者的请求不再直接到达你的服务器（称为「源站」），而是先到达离访问者最近的 Cloudflare 节点（称为「边缘」）。边缘节点在这里依次做三件事：

1. **安全检查**：是攻击就拦下。
2. **缓存命中**：有现成副本就直接返回。
3. **边缘计算**：如果配了 Workers，就在这里运行代码。

只有这三步都处理不了的请求，才会回到源站。理解了这条链路，后面每个模块其实都是在这条链路上的某一步「加功能」。

<figure class="cf-flow">
<svg viewBox="0 0 360 424" role="img" aria-label="大多数请求在边缘就被处理，只有剩下的才回源" font-size="13">
<defs><marker id="cf-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--muted)"/></marker></defs>
<rect x="30" y="12" width="140" height="40" rx="8" fill="none" stroke="var(--muted)" stroke-width="1.25"/>
<text x="100" y="36.5" text-anchor="middle" font-weight="700" fill="var(--fg)">访问者</text>
<rect x="8" y="76" width="344" height="252" rx="10" fill="var(--accent-soft)" fill-opacity=".55" stroke="var(--accent)" stroke-width="2"/>
<text x="114" y="100" font-weight="700" fill="var(--fg)">Cloudflare 边缘节点</text>
<g fill="none" stroke="var(--muted)" stroke-width="1.25">
<path d="M100 52V112" marker-end="url(#cf-arrow)"/>
<path d="M100 152V184" marker-end="url(#cf-arrow)"/>
<path d="M100 224V256" marker-end="url(#cf-arrow)"/>
<path d="M100 296V360" marker-end="url(#cf-arrow)"/>
<path d="M170 132H200" marker-end="url(#cf-arrow)"/>
<path d="M170 204H200" marker-end="url(#cf-arrow)"/>
<path d="M170 276H200" marker-end="url(#cf-arrow)"/>
<rect x="30" y="112" width="140" height="40" rx="8" stroke-width="1.25"/>
<rect x="30" y="184" width="140" height="40" rx="8" stroke-width="1.25"/>
<rect x="30" y="256" width="140" height="40" rx="8" stroke-width="1.25"/>
<rect x="30" y="360" width="140" height="40" rx="8" stroke-width="1.25"/>
<rect x="200" y="112" width="140" height="40" rx="8" stroke-dasharray="4 3"/>
<rect x="200" y="184" width="140" height="40" rx="8" stroke-dasharray="4 3"/>
<rect x="200" y="256" width="140" height="40" rx="8" stroke-dasharray="4 3"/>
</g>
<g text-anchor="middle" fill="var(--fg)">
<text x="100" y="136.5" font-weight="700">① 安全检查</text>
<text x="100" y="208.5" font-weight="700">② 缓存</text>
<text x="100" y="280.5" font-weight="700">③ Workers</text>
<text x="100" y="384.5" font-weight="700">源站</text>
<text x="270" y="136.5" font-size="12.5">是攻击：拦下</text>
<text x="270" y="208.5" font-size="12.5">命中：直接返回</text>
<text x="270" y="280.5" font-size="12.5">代码生成响应</text>
</g>
<text x="112" y="350" font-size="12" fill="var(--muted)">三步都没处理：回源</text>
<text x="182" y="384.5" font-size="12" fill="var(--muted)">你的服务器</text>
</svg>
<figcaption>请求从上往下走：虚线框是在边缘就结束的三种结局，只有三步都不处理的请求才到达源站。</figcaption>
</figure>

**类比**：Cloudflare 像一栋大楼的前台。访客先到前台，前台核查身份（安全），常见问题当场回答（缓存），能办的业务直接办（Workers），实在办不了才打电话叫楼上的你（源站）。

## 一、网络与性能：让网站更快

这一类模块解决一个问题：让用户更快、更稳定地拿到内容。DNS 是入口，CDN 是主力，其余是锦上添花。

### DNS：互联网的电话簿

**解决什么**：把 `lab.door4ai.com` 这样的域名翻译成服务器 IP。

- Cloudflare 是全球最快的权威 DNS 之一，免费版就能用。
- 每条记录有一朵「云」：**橙色 = 代理**（流量经过 Cloudflare，享受 CDN 和安全），**灰色 = 仅 DNS**（只解析，流量直连源站）。
- 把域名的 NS 记录指向 Cloudflare，是使用大部分其他功能的前提。

### CDN 与缓存：把内容搬到用户家门口

**解决什么**：源站在美国，欧洲用户访问慢。CDN 把图片、JS、CSS 等静态文件复制到各地节点，用户就近取用。

- **缓存命中（HIT）**：边缘节点有副本，直接返回；**未命中（MISS）**：去源站取，顺便存一份。
- 默认只缓存静态文件，HTML 需要用 Cache Rules 手动开启。
- 改了文件却看不到更新时，用 **Purge Cache** 清除缓存。
- 好处有二：用户更快，源站压力和带宽费用更低。

### 其他性能模块

| 模块 | 解决什么问题 | 一句话原理 | 谁需要 |
| --- | --- | --- | --- |
| Argo Smart Routing | 公网回源路径拥堵 | 在 Cloudflare 自己的骨干网里实时选最快路径 | 动态内容多、用户全球分布的站（付费） |
| Load Balancing | 单台服务器挂了站就挂了 | 在多个源站间分流，健康检查失败自动切换 | 有多台服务器的业务（付费） |
| Speed 优化 | 前端资源太大太慢 | 图片压缩、HTTP/3、Early Hints 等 | 所有网站，很多是一键开关 |
| Registrar | 域名续费被加价 | 按批发成本价卖域名，不加价 | 任何要买或转移域名的人 |

**小结**：DNS 决定流量是否进入 Cloudflare，CDN 决定多少请求不必回源。对个人项目来说，免费的 DNS + CDN 已经够用。

## 二、应用安全：让网站不被打

网站一旦公开，就会面对三类威胁：用流量压垮你（DDoS）、用恶意请求攻破你（注入、XSS）、用机器人薅羊毛（刷接口、抓数据、撞库登录）。这一类模块正好对应这三层。

| 威胁层 | 模块 | 做什么 | 免费版可用 |
| --- | --- | --- | --- |
| 流量层 | DDoS 防护 | 自动识别并吸收大流量攻击，不限量 | 是 |
| 流量层 | Rate Limiting | 限制单个 IP 或单个路径的请求频率 | 有基础规则 |
| 应用层 | WAF（Web 应用防火墙） | 按规则检查请求内容，拦截 SQL 注入、XSS 等攻击；可写自定义规则 | 有自定义规则，托管规则集需付费 |
| 应用层 | SSL/TLS | 提供免费 HTTPS 证书并自动续期，加密传输 | 是 |
| 身份层 | Bot Management | 区分好机器人（搜索引擎）和坏机器人（爬虫、刷单） | 有简化版 Bot Fight Mode |
| 身份层 | Turnstile | 替代图片验证码的人机验证，大多数用户无需点击 | 是，可用在任何网站 |

### SSL/TLS 的四种模式（新手最常踩的坑）

SSL 模式决定了「访客 → Cloudflare」和「Cloudflare → 源站」这两段是否加密。

| 模式 | 访客 → Cloudflare | Cloudflare → 源站 | 何时使用 |
| --- | --- | --- | --- |
| Off | 不加密 | 不加密 | 不建议 |
| Flexible | 加密 | 不加密 | 源站没有证书时的临时方案；容易引发重定向循环 |
| Full | 加密 | 加密，不验证证书 | 源站用自签证书时 |
| Full (Strict) | 加密 | 加密并验证证书 | **推荐**，可配合免费的 Origin CA 证书 |

> 常见错误：源站已经强制 HTTPS，却把模式设为 Flexible，浏览器就会报「重定向次数过多」。

### WAF 自定义规则举例

- 只允许中国和美国的 IP 访问 `/admin` 路径。
- 对宣称是 Googlebot 但未通过验证的请求直接拦截。
- 登录接口对可疑流量弹出「托管质询」（Managed Challenge）。

**小结**：对个人网站，免费的 DDoS 防护 + SSL Full (Strict) + 几条 WAF 自定义规则已经是不错的基线。有表单的页面，再加上 Turnstile（本站的登录页就用了它）。

## 三、开发者平台：在边缘上写应用

这是 Cloudflare 近几年最重要的转变：它不再只是「帮你代理流量」，而是让你**把整个应用部署在它的全球网络上**。可以把它理解为一套完整的云平台，竞品是 AWS Lambda、Vercel 和 Supabase。

### 计算

| 模块 | 是什么 | 典型用途 |
| --- | --- | --- |
| Workers | 边缘 Serverless 函数，用 JS/TS 写（也支持 Python、Rust/WASM），基于 V8 隔离环境，冷启动几乎为零 | API、重写请求、A/B 测试、全栈应用后端 |
| Pages | 静态站点和前端框架托管，连上 Git 自动构建部署。官方正引导新项目改用 Workers 的静态资源功能 | 博客、文档站、Astro/Next.js 前端 |
| Durable Objects | 带状态的 Worker 实例：每个对象全球唯一，自带存储 | 聊天室、协同编辑、WebSocket、游戏房间 |
| Workflows | 可靠的多步骤流程编排，失败自动重试，可以暂停数天 | 订单处理、AI 长任务链 |
| Queues | 消息队列，前端先应答，后台慢慢处理 | 发邮件、视频处理、削峰 |
| Cron Triggers | 定时触发 Worker | 每日报表、定时抓取 |
| Containers | 在 Cloudflare 网络上跑 Docker 容器 | Workers 跑不了的重计算、非 JS 语言服务 |

### 存储

| 模块 | 数据模型 | 一致性 | 最适合 |
| --- | --- | --- | --- |
| R2 | 对象存储，兼容 S3 API | 强一致 | 图片、视频、备份、数据集；最大卖点是**出口流量免费** |
| D1 | 基于 SQLite 的关系数据库 | 强一致（主库），可加只读副本 | 小到中型应用的业务数据 |
| KV | 全球分布的键值存储 | 最终一致（写入传播有秒级延迟） | 配置、功能开关、缓存等读多写少的数据 |
| Durable Objects 存储 | 每个对象自带的 SQLite | 强一致 | 需要协调的状态，如计数器、房间 |
| Hyperdrive | 不存数据，是连接池 + 查询缓存 | 取决于你的数据库 | 让 Workers 高效访问已有的 Postgres/MySQL |

> 选型口诀：**文件用 R2，表格用 D1，配置用 KV，协作用 DO，老库用 Hyperdrive。**

### AI

| 模块 | 做什么 |
| --- | --- |
| Workers AI | 在 Cloudflare 的 GPU 上调用开源模型（Llama、Mistral、Whisper、嵌入模型等），按用量计费 |
| Vectorize | 向量数据库，存嵌入向量做语义检索，是 RAG 的核心组件 |
| AI Gateway | 架在 OpenAI、Anthropic 等模型 API 前面的代理层：缓存、限流、日志、重试、切换备用模型、统计成本 |
| AI Search（原 AutoRAG） | 托管的 RAG 流水线：把 R2 里的文档自动切块、嵌入、索引、检索 |
| Agents SDK | 在 Workers + Durable Objects 上构建有状态 AI Agent 的框架，也支持部署远程 MCP 服务器 |

### 媒体

| 模块 | 做什么 |
| --- | --- |
| Images | 图片存储、按 URL 参数实时裁剪和缩放、自动转 WebP/AVIF |
| Stream | 视频上传、转码、自适应码率播放、直播 |
| Realtime（原 Calls） | 基于 WebRTC 的实时音视频基础设施 |

**小结**：一个典型全栈应用可以完全跑在 Cloudflare 上。前端用 Pages 或 Workers 静态资源，API 用 Workers，数据用 D1 + R2，AI 功能用 Workers AI + Vectorize。配置和部署都通过命令行工具 `wrangler` 完成。本站就是这样搭的：页面在 Pages 上，账号数据在 D1，安装包镜像在 R2。

## 四、Zero Trust：保护内部网络

前三类保护的是「对外公开」的网站，这一类保护的是「只给自己人用」的服务。**零信任（Zero Trust）**的意思是：不再因为「在公司内网」就信任你，每一次访问都要验证「你是谁、用什么设备、能不能访问这个应用」。它的目标是取代传统 VPN。

| 模块 | 做什么 | 个人能用吗 |
| --- | --- | --- |
| Tunnel（cloudflared） | 在内网机器上跑一个客户端，**主动向外**连到 Cloudflare。不开端口、不需要公网 IP，就能把内网服务发布到一个域名上 | 能，免费 |
| Access | 给应用加一道身份门：要求 Google 登录、邮箱验证码、GitHub 等认证通过后才放行 | 能，小团队免费 |
| Gateway | 安全 Web 网关：在 DNS 和 HTTP 层过滤，管控设备能访问哪些网站，拦截钓鱼和恶意软件 | 能 |
| WARP | 设备客户端。个人版加密并优化上网流量；企业版把设备接入 Zero Trust，可以访问私有网段 | 能 |
| Browser Isolation | 网页在云端浏览器里运行，本地只接收渲染结果，恶意代码碰不到电脑 | 主要面向企业 |
| CASB / DLP | 扫描 SaaS 应用的配置风险，防止敏感数据外泄 | 企业 |
| Magic Transit / Magic WAN | 保护企业整个 IP 网段免受 DDoS；用 Cloudflare 网络替代传统 MPLS 专线连接各分支机构 | 企业 |

### Tunnel + Access：最值得学的组合

场景：家里有一台服务器跑着管理后台，没有公网 IP，也不想对外开端口，但希望在外面能安全访问。

1. 在服务器上安装 `cloudflared`，创建一条 Tunnel。
2. 把域名 `admin.example.com` 映射到内网地址，如 `http://localhost:8080`。
3. 在 Access 里为这个域名建一条策略：只允许你自己的邮箱登录。
4. 此后任何人访问这个域名，都要先在 Cloudflare 登录页通过验证，请求才会经隧道到达你的服务器。

结果：服务器对公网完全「隐形」，攻击者连要打的 IP 都找不到。

**小结**：企业用这一套替代 VPN；个人开发者至少应该学会 Tunnel + Access，这是发布家庭服务器和内部工具最安全、也最省事的方式。

## 五、其他实用工具

这些模块不属于前面任何一类，但大多免费、上手快，很适合个人开发者。

| 模块 | 做什么 | 典型用法 |
| --- | --- | --- |
| Email Routing | 把 `任意名@你的域名` 的来信转发到 Gmail 等邮箱，只收不发 | 对外公开 `hello@你的域名`，实际收在 Gmail |
| Web Analytics | 不用 Cookie、不追踪个人的访问统计，给出页面浏览量、来源、Core Web Vitals | 博客流量统计，替代 Google Analytics |
| Zaraz | 把 GA、广告像素等第三方脚本搬到边缘加载，减轻浏览器负担 | 营销网站提速 |
| 1.1.1.1 | 面向个人的公共 DNS 解析服务，主打速度快和不记录查询日志；另有 1.1.1.2（拦截恶意软件）和 1.1.1.3（加拦成人内容） | 把电脑或路由器的 DNS 改成 1.1.1.1 |
| Radar | 公开的互联网趋势数据：流量、攻击、断网、AI 爬虫占比等 | 做研究、写文章时查数据 |

**小结**：Email Routing 和 Web Analytics 是个人站长的「必开项」，开启只需几分钟，而且全免费。

## 六、实战：场景组合与选型

学模块是为了组合。下表是五个常见场景的推荐搭配。

| 场景 | 推荐组合 | 关键理由 |
| --- | --- | --- |
| 个人博客 / 文档站 | Registrar + DNS + Pages（或 Workers 静态资源）+ Web Analytics + Email Routing | 全免费，Git push 即发布 |
| 全栈 Web 应用 | Workers + D1 + R2 + KV，有登录表单加 Turnstile | 无服务器运维，按量付费 |
| AI 应用（RAG / Agent） | Workers + Workers AI 或 AI Gateway + Vectorize + R2 + Durable Objects | 模型调用、检索、状态都在一个平台 |
| 发布家庭服务器 / 内部工具 | Tunnel + Access | 不开端口、不要公网 IP，带身份验证 |
| 已有服务器的业务站 | DNS（橙色云）+ CDN + WAF + SSL Full (Strict) | 不改代码，就能加速和防攻击 |

### 中国大陆访问注意事项

- **没有大陆节点**：免费和普通付费套餐的流量，对大陆用户通常从香港、日本或美西节点返回，延迟和稳定性不稳定，高峰时段尤其明显。
- **China Network**：Cloudflare 与京东云合作提供大陆节点，但仅限企业版，并要求域名已完成 ICP 备案。
- **部分域名可能被干扰**：如 `*.workers.dev`、`*.pages.dev`，在大陆可能无法访问或不稳定。面向大陆用户时，务必绑定自己的域名。
- **取舍建议**：读者主要在海外，放心用；读者主要在大陆，可考虑「备案域名 + 国内 CDN」，或大陆/海外分线解析。

### 选型决策路径

1. 先问：这是**公开服务**还是**内部服务**？内部 → 第四类（Tunnel + Access）。
2. 公开服务：**已经有服务器**吗？有 → 第一、二类（代理 + 安全）。
3. 没有服务器，从零开始 → 第三类：纯静态用 Pages，有后端用 Workers，再按数据类型选存储。
4. 最后检查：用户在哪里？大陆用户多 → 看上面的注意事项。

## 课后练习

**概念题**

1. 橙色云和灰色云的区别是什么？哪种情况下 WAF 不生效？
2. 源站已强制 HTTPS，浏览器却报「重定向次数过多」，最可能是哪个设置错了？
3. 为什么 KV 不适合存银行账户余额？应该改用什么？
4. Tunnel 为什么不需要公网 IP？

**选型题**

5. 你要做一个「上传 PDF → 向 AI 提问」的小应用，写出所需的 Cloudflare 模块并说明每个的作用。
6. 一个面向大陆中学生的学习网站，是否适合用 Cloudflare 免费版？给出理由和替代方案。

**动手题**

- [ ] 用 `npm create cloudflare@latest` 创建一个 Worker，返回访问者所在的国家（提示：`request.cf.country`）。
- [ ] 给你的域名开启 Email Routing，并把一个地址转发到自己的邮箱。
- [ ] 用 Tunnel 把本机一个 `localhost` 服务发布到子域名，再用 Access 限制为只有你的邮箱可以登录。

<details>
<summary>参考答案要点</summary>

① 灰色云流量不经过 Cloudflare，所以 WAF 和 CDN 都不生效。② SSL 模式设为了 Flexible。③ KV 是最终一致的，可能读到旧值，应改用 D1 或 Durable Objects。④ 连接是由内网的 cloudflared 主动向外建立的。⑤ R2（存 PDF）+ Workers AI（嵌入和问答）+ Vectorize（检索）+ Workers（API），或直接用 AI Search。⑥ 不太适合，大陆访问不稳定；建议用备案域名 + 国内 CDN。

</details>

## 术语表

| 术语 | 解释 |
| --- | --- |
| 源站（Origin） | 你自己的服务器，内容的原始来源 |
| 边缘（Edge） | Cloudflare 分布在全球、离用户最近的节点 |
| 回源 | 边缘没有缓存时，去源站取内容 |
| 反向代理 | 代表服务器接收请求的中间层，访问者看不到真实服务器 |
| Serverless | 不管理服务器，只写函数，按执行次数计费 |
| 冷启动 | 函数很久没被调用后，再次调用时的启动延迟 |
| 最终一致 | 写入后各节点要过一段时间才读到新值 |
| 出口费用（Egress） | 数据从云平台传出去时收的流量费 |
| RAG | 检索增强生成：先检索相关资料，再交给大模型回答 |
| Zero Trust | 不默认信任任何网络位置，每次访问都验证身份 |
| wrangler | Cloudflare 开发者平台的命令行工具 |

延伸阅读：[Cloudflare 官方文档](https://developers.cloudflare.com/)。产品名称和免费额度变化较快，以官网为准。
