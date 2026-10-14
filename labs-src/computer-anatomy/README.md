# computer-anatomy 实验页源码

`public/labs/computer-anatomy/index.html` 由这里的脚本生成（等距 SVG 图解，基于 Anthropic 的 Anatomy skill 的 kit）。

重新生成：
1. 把 Anatomy skill 的 `kit/` 和 `scripts/` 两个目录复制到本目录（不入库）。
2. `node build.mjs` → 生成 `index.html`，复制到 `public/labs/computer-anatomy/index.html`。
3. 检查：`CHROME_PATH=<chromium> node scripts/lines.mjs index.html --select "#f1-stage"`（f1–f5 各跑一次，应为 `line ends: 0`）。

文件：`fig1`（CPU/GPU）、`fig2`+`fig3`+`sec23`（内存/显存/统一内存，共用滑块）、`fig4`+`sec4`（Docker 集装箱船）、`fig5`+`sec5`（服务器 vs 个人电脑）、`build.mjs`（页面外壳与正文）。
