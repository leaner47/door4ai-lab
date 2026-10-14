# Door4AI Lab — lab.door4ai.com

Astro 静态博客，每篇文章可挂一个可交互实验页。

## 本地开发
```bash
npm install
npm run dev        # http://localhost:4321
npm run build      # 输出到 dist/
```

## 写文章
- 文章放 `src/content/blog/<slug>.md`，frontmatter 字段：`title` `description` `pubDate` `tags` `lab`（可选，实验页路径）。
- 实验页是独立 HTML，放 `public/labs/<name>/index.html`，文章里用 `lab: /labs/<name>/` 引用，会以 iframe 嵌入并提供全屏链接。

## 部署到 Cloudflare（一次性）
1. 把本目录推到 GitHub 仓库（如 `door4ai-lab`）。
2. Cloudflare Dashboard → Compute → Workers & Pages → Create → Pages → Connect to Git → 选该仓库。
   - Framework preset: **Astro**
   - Build command: `npm run build`
   - Build output directory: `dist`
3. 部署成功后 → 该 Pages 项目 → Custom domains → Add → 填 `lab.door4ai.com`。
   Cloudflare 会自动在 door4ai.com 的 DNS 里加一条 CNAME，几分钟后 HTTPS 生效。

之后每次 `git push` 自动重新部署。
