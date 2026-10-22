---
title: "模型是怎么看图的：一张图怎样变成一串 token"
description: "大模型读文字靠 token，看图片也一样。用一张 4 × 4 的小图一步步走完：像素、切块、每块变成向量、位置、图像块互相注意、CLIP 怎么让向量带上意思、投影进大模型、文字 token 怎么去看图上的某一块，最后回到真实模型的规模和它看不清的地方。"
pubDate: 2026-10-22
tags: ["多模态", "ViT", "CLIP", "视觉 token"]
lab: /labs/vision-tokens/
series: ai-mastery
order: 48
---

<!-- 本文由 labs-src/vision-tokens/toy.py 从 article.src.md 生成，图和数字都由脚本算出。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

大模型没有专门「看图」的部分。图片先被切成一个个小方块，每个方块变成一个向量，再换算成和文字 token 同一种格式的「视觉 token」，排在问题前面一起送进模型。之后的事和读文字完全一样：注意力让问题里的词去找图上相关的那几块。

下面用一张能手算的小图，把这条路一步一步走完。

## 第一步：图片在电脑里是一张数字表

屏幕上的一张图，由一格一格的**像素**组成。每个像素存的是颜色。彩色图每个像素有 3 个数：红、绿、蓝各有多亮，通常是 0 到 255 的整数。送进模型之前，一般先除以 255，变成 0 到 1 之间的小数。

为了能手算，我们先只用黑白（灰度）图：每个像素只有 1 个数，0 是黑，1 是白。图也只有 4 × 4 = 16 个像素：

<figure class="fig">
<svg viewBox="0 0 480 236" role="img" aria-label="一张 4 乘 4 的灰度小图，每格写着它的亮度">
<rect x="150.0" y="20.0" width="45" height="45" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="172.5" y="48.1" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="195.0" y="20.0" width="45" height="45" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="217.5" y="48.1" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="240.0" y="20.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="262.5" y="48.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="285.0" y="20.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="307.5" y="48.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="150.0" y="65.0" width="45" height="45" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="172.5" y="93.1" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="195.0" y="65.0" width="45" height="45" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="217.5" y="93.1" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="240.0" y="65.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="262.5" y="93.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="285.0" y="65.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="307.5" y="93.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="150.0" y="110.0" width="45" height="45" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="172.5" y="138.1" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="195.0" y="110.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="217.5" y="138.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="240.0" y="110.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="262.5" y="138.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="285.0" y="110.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="307.5" y="138.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="150.0" y="155.0" width="45" height="45" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="172.5" y="183.1" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="195.0" y="155.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="217.5" y="183.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="240.0" y="155.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="262.5" y="183.1" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="285.0" y="155.0" width="45" height="45" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="307.5" y="183.1" font-size="16" text-anchor="middle" fill="#eee">0</text><text x="240.0" y="220.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">4 × 4 = 16 个像素</text>
</svg>
<figcaption>图 1　贯穿全讲的小图。每个格子是一个像素，格子里的数是亮度：0 是黑，1 是白。</figcaption>
</figure>

这张小图左边是亮的：左上角一块 2 × 2 的白色，下面接一道白色竖杠。这 16 个数会一直用到最后。

真实的照片大得多。一张 1000 × 1000 的彩色照片是 1000 × 1000 × 3 = 3,000,000 个数。模型不会把三百万个数一个一个当成 token，那样序列太长了。第一件事是把它们分组。

## 第二步：切成小方块（patch）

把图切成同样大小的小方块，每块叫一个 **patch**。我们的小图按 2 × 2 切，正好切成 4 块：左上、右上、左下、右下。

每块里有 2 × 2 = 4 个像素。把它们按「先第一行、再第二行」的顺序排成一行，每块就成了 4 个数：

<figure class="fig">
<svg viewBox="0 0 480 230" role="img" aria-label="小图切成四块，每块展开成一行四个数">
<rect x="24.0" y="30.0" width="36" height="36" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="42.0" y="53.6" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="60.0" y="30.0" width="36" height="36" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="78.0" y="53.6" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="110.0" y="30.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="128.0" y="53.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="146.0" y="30.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="164.0" y="53.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="24.0" y="66.0" width="36" height="36" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="42.0" y="89.6" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="60.0" y="66.0" width="36" height="36" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="78.0" y="89.6" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="110.0" y="66.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="128.0" y="89.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="146.0" y="66.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="164.0" y="89.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="24.0" y="116.0" width="36" height="36" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="42.0" y="139.6" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="60.0" y="116.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="78.0" y="139.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="110.0" y="116.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="128.0" y="139.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="146.0" y="116.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="164.0" y="139.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="24.0" y="152.0" width="36" height="36" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="42.0" y="175.6" font-size="16" text-anchor="middle" fill="#111">1</text><rect x="60.0" y="152.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="78.0" y="175.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="110.0" y="152.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="128.0" y="175.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="146.0" y="152.0" width="36" height="36" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="164.0" y="175.6" font-size="16" text-anchor="middle" fill="#eee">0</text><rect x="21.0" y="27.0" width="78.0" height="78.0" rx="6" style="fill:none;stroke:var(--accent);stroke-width:2"/><rect x="107.0" y="27.0" width="78.0" height="78.0" rx="6" style="fill:none;stroke:var(--accent);stroke-width:2"/><rect x="21.0" y="113.0" width="78.0" height="78.0" rx="6" style="fill:none;stroke:var(--accent);stroke-width:2"/><rect x="107.0" y="113.0" width="78.0" height="78.0" rx="6" style="fill:none;stroke:var(--accent);stroke-width:2"/><text x="250.0" y="51.0" font-size="16" text-anchor="end" style="fill:var(--accent)">左上</text><rect x="262.0" y="30.0" width="34" height="34" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="279.0" y="52.2" font-size="15" text-anchor="middle" fill="#111">1</text><rect x="306.0" y="30.0" width="34" height="34" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="323.0" y="52.2" font-size="15" text-anchor="middle" fill="#111">1</text><rect x="350.0" y="30.0" width="34" height="34" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="367.0" y="52.2" font-size="15" text-anchor="middle" fill="#111">1</text><rect x="394.0" y="30.0" width="34" height="34" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="411.0" y="52.2" font-size="15" text-anchor="middle" fill="#111">1</text><text x="250.0" y="93.0" font-size="16" text-anchor="end" style="fill:var(--accent)">右上</text><rect x="262.0" y="72.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="279.0" y="94.2" font-size="15" text-anchor="middle" fill="#eee">0</text><rect x="306.0" y="72.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="323.0" y="94.2" font-size="15" text-anchor="middle" fill="#eee">0</text><rect x="350.0" y="72.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="367.0" y="94.2" font-size="15" text-anchor="middle" fill="#eee">0</text><rect x="394.0" y="72.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="411.0" y="94.2" font-size="15" text-anchor="middle" fill="#eee">0</text><text x="250.0" y="135.0" font-size="16" text-anchor="end" style="fill:var(--accent)">左下</text><rect x="262.0" y="114.0" width="34" height="34" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="279.0" y="136.2" font-size="15" text-anchor="middle" fill="#111">1</text><rect x="306.0" y="114.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="323.0" y="136.2" font-size="15" text-anchor="middle" fill="#eee">0</text><rect x="350.0" y="114.0" width="34" height="34" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="367.0" y="136.2" font-size="15" text-anchor="middle" fill="#111">1</text><rect x="394.0" y="114.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="411.0" y="136.2" font-size="15" text-anchor="middle" fill="#eee">0</text><text x="250.0" y="177.0" font-size="16" text-anchor="end" style="fill:var(--accent)">右下</text><rect x="262.0" y="156.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="279.0" y="178.2" font-size="15" text-anchor="middle" fill="#eee">0</text><rect x="306.0" y="156.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="323.0" y="178.2" font-size="15" text-anchor="middle" fill="#eee">0</text><rect x="350.0" y="156.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="367.0" y="178.2" font-size="15" text-anchor="middle" fill="#eee">0</text><rect x="394.0" y="156.0" width="34" height="34" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="411.0" y="178.2" font-size="15" text-anchor="middle" fill="#eee">0</text><text x="345.0" y="212.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">每块按行展开成 4 个数</text>
</svg>
<figcaption>图 2　按 2 × 2 切成 4 块（蓝框）。每块按「先第一行、再第二行」展开成 4 个数。</figcaption>
</figure>

| 块 | 第一行 | 第二行 | 展开成 4 个数 $p$ |
| --- | --- | --- | --- |
| 左上 | 1　1 | 1　1 | $(1,\ 1,\ 1,\ 1)$ |
| 右上 | 0　0 | 0　0 | $(0,\ 0,\ 0,\ 0)$ |
| 左下 | 1　0 | 1　0 | $(1,\ 0,\ 1,\ 0)$ |
| 右下 | 0　0 | 0　0 | $(0,\ 0,\ 0,\ 0)$ |

一块对图像，就相当于一个 token 对一句话：它是模型处理的最小单位。16 个像素变成了 4 块。

<details class="pause"><summary>停一下：如果按 1 × 1 切（每块只有一个像素），会有几块？每块几个数？</summary>

16 块，每块 1 个数。块数多了 4 倍，序列就长了 4 倍；每块只有一个像素，单看一块什么形状也看不出来。反过来按 4 × 4 切，就只有 1 块、16 个数，整张图挤成一个 token。块切多大，是在「序列多长」和「每块能装多少细节」之间取舍。真实模型常用 14 × 14 或 16 × 16 像素一块。

</details>

## 第三步：每块变成一个向量

4 个数还只是亮度，不是「意思」。模型用一个矩阵 $W_E$ 把每块的 4 个数换算成一个向量 $e$，这一步叫 **patch embedding**：

$$
e = W_E\,p
$$

真实模型里 $W_E$ 是训练出来的，而且输出有上千个数。为了能画在纸上，我们的 $W_E$ 只输出 2 个数，并且直接挑两个好懂的：

$$
W_E = \begin{pmatrix} 0.25 & 0.25 & 0.25 & 0.25 \\ 0.5 & -0.5 & 0.5 & -0.5 \end{pmatrix}
$$

第 1 行把 4 个数各乘 0.25 再加起来，就是 4 个像素的**平均亮度**。第 2 行给左列的两个像素（展开后的第 1、3 个数）乘 0.5，给右列的两个（第 2、4 个数）乘 −0.5，结果是「左列比右列亮多少」。左白右黑时这个数大，所以叫它**竖边**。

矩阵乘向量的算法和注意力那讲一样：矩阵的每一行和向量对应位置相乘，再加起来。拿左下那块 $p = (1,\ 0,\ 1,\ 0)$ 来算。

第 1 行：

$$
\begin{aligned} &0.25 \times 1 + 0.25 \times 0 \\ &\quad + 0.25 \times 1 + 0.25 \times 0 \\ &= 0.25 + 0 + 0.25 + 0 = 0.5 \end{aligned}
$$

第 2 行：

$$
\begin{aligned} &0.5 \times 1 + (-0.5) \times 0 \\ &\quad + 0.5 \times 1 + (-0.5) \times 0 \\ &= 0.5 + 0 + 0.5 + 0 = 1 \end{aligned}
$$

所以左下这块的向量是 $e = (0.5,\ 1)$：亮度一半，竖边很强。它确实是一道竖杠的一段。四块都这样算：

| 块 | $p$ | 亮度（第 1 行） | 竖边（第 2 行） | $e$ |
| --- | --- | --- | --- | --- |
| 左上 | $(1,\ 1,\ 1,\ 1)$ | $0.25 \times 4 = 1$ | $0.5 + 0.5 - 0.5 - 0.5 = 0$ | $(1,\ 0)$ |
| 右上 | $(0,\ 0,\ 0,\ 0)$ | $0$ | $0$ | $(0,\ 0)$ |
| 左下 | $(1,\ 0,\ 1,\ 0)$ | $0.5$ | $1$ | $(0.5,\ 1)$ |
| 右下 | $(0,\ 0,\ 0,\ 0)$ | $0$ | $0$ | $(0,\ 0)$ |

<figure class="fig">
<svg viewBox="0 0 480 290" role="img" aria-label="四块的向量画在亮度和竖边平面上">
<line x1="59.0" y1="230.0" x2="308.5" y2="230.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M319.5 230.0 L309.5 234.5 L309.5 225.5 z" style="fill:var(--line)"/><line x1="110.0" y1="272.5" x2="110.0" y2="40.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M110.0 29.0 L114.5 39.0 L105.5 39.0 z" style="fill:var(--line)"/><text x="319.5" y="220.0" font-size="16" text-anchor="end" style="fill:var(--muted)">亮度</text><text x="118.0" y="31.0" font-size="16" text-anchor="start" style="fill:var(--muted)">竖边</text><line x1="110.0" y1="230.0" x2="269.0" y2="230.0" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><path d="M280.0 230.0 L270.0 234.5 L270.0 225.5 z" style="fill:var(--accent)"/><circle cx="110.0" cy="230.0" r="5" style="fill:var(--accent)"/><line x1="110.0" y1="230.0" x2="190.1" y2="69.8" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><path d="M195.0 60.0 L194.5 71.0 L186.5 67.0 z" style="fill:var(--accent)"/><circle cx="110.0" cy="230.0" r="5" style="fill:var(--accent)"/><text x="280.0" y="254.0" font-size="16" text-anchor="middle" style="fill:var(--accent)">左上 (1, 0)</text><text x="207.0" y="56.0" font-size="16" text-anchor="start" style="fill:var(--accent)">左下 (0.5, 1)</text><text x="120.0" y="282.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--warn)">右上、右下 都是 (0, 0)</text>
</svg>
<figcaption>图 3　每块变成一个 2 维向量：横轴是亮度，纵轴是竖边。右上、右下两块都是全黑，落在同一个点 (0, 0) 上。</figcaption>
</figure>

真实模型的 $W_E$ 不是人挑的，第 1 行不一定是「平均亮度」。训练出来的各行常常像边缘、条纹、颜色斑块的检测器，和我们这两行是同一类东西，只是有上千行。

<details class="pause"><summary>停一下：一块「左黑右白」的竖条，展开是 (0, 1, 0, 1)，它的向量是多少？</summary>

亮度：$0.25 \times (0 + 1 + 0 + 1) = 0.5$。竖边：$0.5 \times 0 - 0.5 \times 1 + 0.5 \times 0 - 0.5 \times 1 = -1$。所以 $e = (0.5,\ -1)$。亮度和左下那块一样，竖边的正负相反：竖边这个数不只说明「有没有竖边」，还说明亮的一侧在哪边。

</details>

## 第四步：两块一模一样怎么办：位置向量

看图 3：右上和右下都是全黑，向量都是 $(0,\ 0)$，落在同一个点上。只看这两个向量，模型分不清哪块在上、哪块在下。

文字也有同样的问题，解决办法也一样：给每个位置配一个**位置向量**，加到这一块的向量上：

$$
h = e + \text{pos}
$$

我们给四个位置配的位置向量是：

| 位置 | 左上 | 右上 | 左下 | 右下 |
| --- | --- | --- | --- | --- |
| $\text{pos}$ | $(-0.1,\ 0.1)$ | $(0.1,\ 0.1)$ | $(-0.1,\ -0.1)$ | $(0.1,\ -0.1)$ |

向量相加就是对应位置的数相加。右上：$(0,\ 0) + (0.1,\ 0.1) = (0.1,\ 0.1)$；右下：$(0,\ 0) + (0.1,\ -0.1) = (0.1,\ -0.1)$。四块逐个加：

| 块 | $e$ | $\text{pos}$ | $h = e + \text{pos}$ |
| --- | --- | --- | --- |
| 左上 | $(1,\ 0)$ | $(-0.1,\ 0.1)$ | $(0.9,\ 0.1)$ |
| 右上 | $(0,\ 0)$ | $(0.1,\ 0.1)$ | $(0.1,\ 0.1)$ |
| 左下 | $(0.5,\ 1)$ | $(-0.1,\ -0.1)$ | $(0.4,\ 0.9)$ |
| 右下 | $(0,\ 0)$ | $(0.1,\ -0.1)$ | $(0.1,\ -0.1)$ |

<figure class="fig">
<svg viewBox="0 0 480 290" role="img" aria-label="加上位置向量之后的四个向量">
<line x1="59.0" y1="230.0" x2="308.5" y2="230.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M319.5 230.0 L309.5 234.5 L309.5 225.5 z" style="fill:var(--line)"/><line x1="110.0" y1="272.5" x2="110.0" y2="40.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M110.0 29.0 L114.5 39.0 L105.5 39.0 z" style="fill:var(--line)"/><text x="319.5" y="252.0" font-size="16" text-anchor="end" style="fill:var(--muted)">亮度</text><text x="118.0" y="31.0" font-size="16" text-anchor="start" style="fill:var(--muted)">竖边</text><line x1="110.0" y1="230.0" x2="252.1" y2="214.2" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><path d="M263.0 213.0 L253.5 218.6 L252.5 209.7 z" style="fill:var(--accent)"/><line x1="110.0" y1="230.0" x2="119.2" y2="220.8" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><path d="M127.0 213.0 L123.1 223.3 L116.7 216.9 z" style="fill:var(--accent)"/><line x1="110.0" y1="230.0" x2="173.5" y2="87.1" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><path d="M178.0 77.0 L178.0 88.0 L169.8 84.4 z" style="fill:var(--accent)"/><line x1="110.0" y1="230.0" x2="119.2" y2="239.2" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><path d="M127.0 247.0 L116.7 243.1 L123.1 236.7 z" style="fill:var(--accent)"/><text x="271.0" y="205.0" font-size="16" text-anchor="start" style="fill:var(--accent)">左上 (0.9, 0.1)</text><text x="190.0" y="81.0" font-size="16" text-anchor="start" style="fill:var(--accent)">左下 (0.4, 0.9)</text><text x="141.0" y="199.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--warn)">右上 (0.1, 0.1)</text><text x="141.0" y="271.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--warn)">右下 (0.1, −0.1)</text>
</svg>
<figcaption>图 4　加上位置向量之后，右上 (0.1, 0.1) 和右下 (0.1, −0.1) 分开了，其他两块只挪了一点。</figcaption>
</figure>

两块全黑的块现在分开了。位置向量取得很小，是因为我们只有 2 个数，内容和位置只能挤在同一个平面里，加大了会把内容盖掉。真实模型的向量有上千个数，位置信息可以放在和内容不同的方向上，互不干扰。

还有一点和文字不同：文字的位置是一维的（第 1 个、第 2 个……），图的位置是二维的（第几行、第几列）。较新的模型会分别编码行和列，比如 Qwen2-VL 的视觉部分用的是二维的旋转位置编码（2D-RoPE）。

## 第五步：块和块互相看：Vision Transformer

到这里，每块还只知道自己那 2 × 2 个像素。左下那块知道「我这里有一段竖边」，却不知道上面接着一大块白色。要让它知道，就让块与块之间做**注意力**：每块按相关程度，从别的块那里取内容加到自己身上。

做法和注意力那讲完全一样：每块算出 $q$、$k$、$v$，点积打分，除以 $\sqrt{d_k}$，softmax 变成份额，按份额把 $v$ 加起来，再接一个 MLP。把这样的一层叠几十层，就是 **Vision Transformer（ViT）**。它不是专门为图设计的新结构，就是读文字用的那个 Transformer。

只有一个地方不同：**遮罩**。

<figure class="fig">
<svg viewBox="0 0 480 200" role="img" aria-label="文字的因果遮罩与图像块的全连接注意力">
<text x="150.0" y="32.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">文字：只能看前面</text><text x="70.0" y="68.0" font-size="15" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="80.0" y="46.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="116.0" y="46.0" width="32.0" height="32.0" rx="3" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><rect x="152.0" y="46.0" width="32.0" height="32.0" rx="3" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><rect x="188.0" y="46.0" width="32.0" height="32.0" rx="3" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="70.0" y="104.0" font-size="15" text-anchor="end" style="fill:var(--fg)">店</text><rect x="80.0" y="82.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="116.0" y="82.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="152.0" y="82.0" width="32.0" height="32.0" rx="3" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><rect x="188.0" y="82.0" width="32.0" height="32.0" rx="3" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="70.0" y="140.0" font-size="15" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="80.0" y="118.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="116.0" y="118.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="152.0" y="118.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="188.0" y="118.0" width="32.0" height="32.0" rx="3" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="70.0" y="176.0" font-size="15" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="80.0" y="154.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="116.0" y="154.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="152.0" y="154.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="188.0" y="154.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><text x="390.0" y="32.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">图像块：互相都能看</text><text x="310.0" y="68.0" font-size="15" text-anchor="end" style="fill:var(--fg)">左上</text><rect x="320.0" y="46.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="356.0" y="46.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="392.0" y="46.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="428.0" y="46.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><text x="310.0" y="104.0" font-size="15" text-anchor="end" style="fill:var(--fg)">右上</text><rect x="320.0" y="82.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="356.0" y="82.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="392.0" y="82.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="428.0" y="82.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><text x="310.0" y="140.0" font-size="15" text-anchor="end" style="fill:var(--fg)">左下</text><rect x="320.0" y="118.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="356.0" y="118.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="392.0" y="118.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="428.0" y="118.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><text x="310.0" y="176.0" font-size="15" text-anchor="end" style="fill:var(--fg)">右下</text><rect x="320.0" y="154.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="356.0" y="154.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="392.0" y="154.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/><rect x="428.0" y="154.0" width="32.0" height="32.0" rx="3" style="fill:var(--accent)"/>
</svg>
<figcaption>图 5　每一行是一个 token 在看谁，蓝色格子表示能看。文字只能看自己和前面；图像块之间没有先后，每块都能看所有块。</figcaption>
</figure>

读文字时，每个 token 只能看自己和前面的 token（因果遮罩），因为模型要一个一个往后生成，不能偷看还没写出来的字。图像块不用生成，也没有先后：左上那块和右下那块谁也不比谁「先」。所以 ViT 里每块都能看所有块。

叠了很多层之后，每块的向量里就不只有自己那几个像素，还有它周围的情况。底下几层的向量大多还是「这里有条竖边」「这里是一片红色」，往上的向量渐渐变成「这是猫耳朵的一部分」「这是一行字的一部分」。

我们的小例子在这一步不再手算，因为每层都和注意力那讲的算法一样。从这里开始，四块的向量就用第四步的 $h$ 往下走。

## 第六步：向量的意思从哪里学来：CLIP

前面一直在说「训练出来的 $W_E$」「训练出来的注意力」。训练要有一个目标。用什么目标，才能让这些向量带上「猫」「竖杠」「一行字」这样的意思？

最常用的办法叫 **CLIP**（OpenAI，2021）。它用的是网上现成的「图片 + 配文」：一张图，加上网页里给它写的那句话。原版 CLIP 收集了 4 亿对。训练目标只有一句话：**配对的图和文字，向量要靠近；不配对的，要离远。**

### 一张图变成一个向量

要比较「图」和「一句话」，先得把整张图变成一个向量。我们用最简单的做法：把四块的向量取平均（真实的 CLIP 会专门留一个汇总用的 token，道理一样）。用不带位置的 $e$ 来算：

$$
\begin{aligned} \bar{e} &= \frac{(1,\ 0) + (0,\ 0) + (0.5,\ 1) + (0,\ 0)}{4} \\ &= \frac{(1.5,\ 1)}{4} = (0.375,\ 0.25) \end{aligned}
$$

用带位置的 $h$ 来算，结果完全一样：四个位置向量加起来是 $(-0.1 + 0.1 - 0.1 + 0.1,\ \ 0.1 + 0.1 - 0.1 - 0.1) = (0,\ 0)$，平均时正好抵消。

### 一批图和一批话

一批训练数据里有好几对。我们用 3 对：

- 图 A：我们的小图，配文「左边亮」。
- 图 B：图 A 左右翻过来，配文「右边亮」。它的四块向量是 $(0,\ 0)$、$(1,\ 0)$、$(0,\ 0)$、$(0.5,\ -1)$，平均是 $(0.375,\ -0.25)$。
- 图 C：16 个像素全是 1，配文「全亮」。每块都是 $(1,\ 0)$，平均是 $(1,\ 0)$。

文字那一边有自己的模型（一个读文字的 Transformer），把每句话变成一个向量。假设它给出：

| 描述 | 文字向量 $t$ |
| --- | --- |
| 左边亮 | $(0.6,\ 0.8)$ |
| 右边亮 | $(0.6,\ -0.8)$ |
| 全亮 | $(1,\ 0)$ |

### 两两打分：余弦相似度

图和文字两两比一下有多接近，用的是**余弦相似度**：两个向量夹角的余弦，方向相同是 1，垂直是 0。算法是先把两个向量都缩成长度 1，再做点积。

图 A 的向量 $(0.375,\ 0.25)$ 的长度是：

$$
\begin{aligned} &\sqrt{0.375^2 + 0.25^2} \\ &= \sqrt{0.140625 + 0.0625} \\ &= \sqrt{0.203125} = 0.4507 \end{aligned}
$$

两个数都除以 0.4507，得到长度为 1 的 $(0.8321,\ 0.5547)$。三个文字向量本来长度就是 1（比如 $0.6^2 + 0.8^2 = 0.36 + 0.64 = 1$），不用再缩。图 A 和三句话的余弦，依次是「左边亮」「右边亮」「全亮」：

$$
\begin{aligned} &0.8321 \times 0.6 + 0.5547 \times 0.8 \\ &= 0.4992 + 0.4438 = 0.943 \end{aligned}
$$

$$
\begin{aligned} &0.8321 \times 0.6 + 0.5547 \times (-0.8) \\ &= 0.4992 - 0.4438 = 0.055 \end{aligned}
$$

$$
0.8321 \times 1 + 0.5547 \times 0 = 0.832
$$

三张图都这样算，排成一张 3 × 3 的表：

<figure class="fig">
<svg viewBox="0 0 480 210" role="img" aria-label="三张图和三句描述两两之间的余弦相似度">
<text x="200.0" y="56.0" font-size="16" text-anchor="middle" style="fill:var(--ok)">「左边亮」</text><text x="300.0" y="56.0" font-size="16" text-anchor="middle" style="fill:var(--ok)">「右边亮」</text><text x="400.0" y="56.0" font-size="16" text-anchor="middle" style="fill:var(--ok)">「全亮」</text><rect x="30.0" y="74.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="74.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="74.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="74.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="83.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="83.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="83.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="83.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="92.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="92.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="92.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="92.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="101.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="101.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="101.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="101.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="110.0" y="98.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">图 A</text><rect x="154.0" y="74.0" width="92.0" height="36.0" rx="6" style="fill:var(--accent)"/><text x="200.0" y="98.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--bg)">0.943</text><rect x="254.0" y="74.0" width="92.0" height="36.0" rx="6" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="300.0" y="98.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.055</text><rect x="354.0" y="74.0" width="92.0" height="36.0" rx="6" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="400.0" y="98.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.832</text><rect x="30.0" y="118.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="118.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="118.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="118.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="127.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="127.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="127.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="127.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="136.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="136.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="136.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="136.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="145.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="145.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="145.0" width="9" height="9" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="145.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="110.0" y="142.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">图 B</text><rect x="154.0" y="118.0" width="92.0" height="36.0" rx="6" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="200.0" y="142.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.055</text><rect x="254.0" y="118.0" width="92.0" height="36.0" rx="6" style="fill:var(--accent)"/><text x="300.0" y="142.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--bg)">0.943</text><rect x="354.0" y="118.0" width="92.0" height="36.0" rx="6" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="400.0" y="142.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.832</text><rect x="30.0" y="162.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="162.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="162.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="162.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="171.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="171.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="171.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="171.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="180.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="180.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="180.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="180.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="189.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="39.0" y="189.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="48.0" y="189.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="57.0" y="189.0" width="9" height="9" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><text x="110.0" y="186.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">图 C</text><rect x="154.0" y="162.0" width="92.0" height="36.0" rx="6" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="200.0" y="186.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.600</text><rect x="254.0" y="162.0" width="92.0" height="36.0" rx="6" style="fill:var(--paper);stroke:var(--line);stroke-width:1"/><text x="300.0" y="186.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.600</text><rect x="354.0" y="162.0" width="92.0" height="36.0" rx="6" style="fill:var(--accent)"/><text x="400.0" y="186.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--bg)">1.000</text><text x="240.0" y="22.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">每格 = 图向量和文字向量的余弦</text>
</svg>
<figcaption>图 6　一批里有 3 张图、3 句描述。对角线（蓝色）是配对的那一格，训练要让它在每一行里最大。</figcaption>
</figure>

### 变成「选对的概率」

每一行可以看成一道选择题：「图 A 配的是哪句话？」CLIP 把这一行的三个余弦变成三个概率，做法是先除以一个**温度** $\tau$，再做 softmax（注意力那讲的 softmax）：

$$
P(\text{第 } j \text{ 句} \mid \text{图 } i) = \frac{e^{\cos_{ij}/\tau}}{\sum_{k} e^{\cos_{ik}/\tau}}
$$

余弦只在 −1 到 1 之间，彼此差得不多。除以一个小的 $\tau$ 就是把差距放大，好让 softmax 分得出高低。原版 CLIP 的 $\tau$ 是训练出来的，起点是 0.07。我们取 $\tau = 0.1$，也就是乘以 10。

图 A 那一行乘以 10，得到 $9.430$、$0.555$、$8.321$。直接取指数数字太大，可以用注意力那讲的一个结论：**每个分数减去同一个数，softmax 的结果不变**。每个都减去最大的 9.430：

| 描述 | $\cos / \tau$ | 减去 9.430 | $e^{(\cdot)}$ | 概率 |
| --- | --- | --- | --- | --- |
| 左边亮 | 9.430 | 0 | 1 | $1 / 1.3297 = 75.2\%$ |
| 右边亮 | 0.555 | −8.875 | 0.00014 | $0.00014 / 1.3297 = 0.01\%$ |
| 全亮 | 8.321 | −1.109 | 0.3297 | $0.3297 / 1.3297 = 24.8\%$ |

（总和 $1 + 0.00014 + 0.3297 = 1.3297$。）

### 损失：训练要让什么变大

图 A 选对的概率是 75.2%。训练的目标是让它尽量接近 100%。衡量离 100% 有多远，用的是**负对数**：

$$
L_A = -\ln 0.752 = 0.285
$$

概率是 100% 时 $-\ln 1 = 0$，没有损失；概率越小，损失越大（50% 时是 0.693，10% 时是 2.303）。三张图的损失取平均，就是这一批的损失。CLIP 还会把这张表竖着再做一遍（「左边亮」这句话配的是哪张图？），两个方向的损失再平均。

然后按梯度下降那讲的办法，把图像这边（$W_E$、ViT 每一层）和文字那边的参数都往「损失变小」的方向挪一点。几亿对图文、成千上万步之后，「猫」的照片和「一只猫」这句话的向量就落到了一起。图像向量的「意思」，就是这样从文字那边借来的。

<details class="pause"><summary>停一下：图 A 输给「全亮」的那 24.8%，是哪里出了问题？</summary>

看图 A 的向量 $(0.375,\ 0.25)$：第 1 个数（亮度）比第 2 个数（竖边）大，它更像「亮」，不够像「左边」。「全亮」的向量 $(1,\ 0)$ 正好只看亮度，所以余弦也不低（0.832）。训练会往两个方向改：让图像这边更看重竖边（比如增大 $W_E$ 第 2 行的数，图 A 的向量就会往「左边亮」$(0.6,\ 0.8)$ 的方向转），也让文字那边把「左边亮」和「全亮」两个向量推开。

</details>

## 第七步：接进大模型：投影成视觉 token

CLIP 训练出来的图像部分（视觉编码器）已经能把图变成有意思的向量。现在要让一个读文字的大模型用上它。

### 为什么不只给一个平均向量

最省事的办法是把整张图平均成一个向量交给大模型。可平均会把位置丢掉：

<figure class="fig">
<svg viewBox="0 0 480 196" role="img" aria-label="两张不同的图，四块向量取平均后得到同一个向量">
<rect x="30.0" y="30.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="60.0" y="30.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="90.0" y="30.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="120.0" y="30.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="60.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="60.0" y="60.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="90.0" y="60.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="120.0" y="60.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="90.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="60.0" y="90.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="90.0" y="90.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="120.0" y="90.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="30.0" y="120.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="60.0" y="120.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="90.0" y="120.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="120.0" y="120.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="210.0" y="30.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="240.0" y="30.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="270.0" y="30.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="300.0" y="30.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="210.0" y="60.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="240.0" y="60.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="270.0" y="60.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="300.0" y="60.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="210.0" y="90.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="240.0" y="90.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="270.0" y="90.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="300.0" y="90.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="210.0" y="120.0" width="30" height="30" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="240.0" y="120.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="270.0" y="120.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="300.0" y="120.0" width="30" height="30" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><text x="90.0" y="178.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">亮块在左上</text><text x="270.0" y="178.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">亮块在右上</text><rect x="370.0" y="62.0" width="96.0" height="56.0" rx="8" style="fill:var(--paper);stroke:var(--warn);stroke-width:2"/><text x="418.0" y="86.0" font-size="13" text-anchor="middle" style="fill:var(--warn)">两张的平均都是</text><text x="418.0" y="108.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">(0.375, 0.25)</text><line x1="336.0" y1="90.0" x2="353.0" y2="90.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M364.0 90.0 L354.0 94.5 L354.0 85.5 z" style="fill:var(--line)"/>
</svg>
<figcaption>图 7　两张图的四块其实一样，只是放的位置不同。四个向量取平均，得到的都是 (0.375, 0.25)。</figcaption>
</figure>

右边那张图，是把左上的白块挪到了右上，其他不动。它的四块向量是 $(0,\ 0)$、$(1,\ 0)$、$(0.5,\ 1)$、$(0,\ 0)$，和图 A 是同样四个向量，只是顺序不同。加起来再除以 4，结果都是 $(0.375,\ 0.25)$。只拿这个平均向量，模型回答不了「白块在左边还是右边」。

所以现在常用的做法（LLaVA 这一类模型）是：**每一块都交给大模型**，四块就是 4 个 token，每个 token 带着自己的位置。

### 投影：换成大模型认得的坐标

视觉编码器的向量和大模型的词向量，是两个模型分别训练出来的，两边的坐标意思不一样，长度也可能不一样（LLaVA-1.5 里视觉向量是 1024 个数，大模型的词向量是 4096 个数）。中间要接一个**投影器** $W_P$，把每块的向量换算到大模型的坐标里：

$$
z = W_P\,h \qquad W_P = \begin{pmatrix} 1 & 1 \\ -1 & 1 \end{pmatrix}
$$

真实的投影器是一个两层的 MLP，这里用一个矩阵代替。$W_P$ 的第 1 行把 $h$ 的两个数加起来，第 2 行用第 2 个数减第 1 个数。以左下那块 $h = (0.4,\ 0.9)$ 为例：

$$
z_1 = 1 \times 0.4 + 1 \times 0.9 = 1.3
$$

$$
z_2 = (-1) \times 0.4 + 1 \times 0.9 = 0.5
$$

四块逐个算：

| 块 | $h$ | $z_1 = h_1 + h_2$ | $z_2 = h_2 - h_1$ | $z$ |
| --- | --- | --- | --- | --- |
| 左上 | $(0.9,\ 0.1)$ | $1.0$ | $-0.8$ | $(1.0,\ -0.8)$ |
| 右上 | $(0.1,\ 0.1)$ | $0.2$ | $0$ | $(0.2,\ 0)$ |
| 左下 | $(0.4,\ 0.9)$ | $1.3$ | $0.5$ | $(1.3,\ 0.5)$ |
| 右下 | $(0.1,\ -0.1)$ | $0$ | $-0.2$ | $(0,\ -0.2)$ |

这 4 个 $z$ 就是 **视觉 token**。对大模型来说，它们和查词表得到的文字 token 向量是同一种东西，可以直接排在一起：

<figure class="fig">
<svg viewBox="0 0 480 124" role="img" aria-label="视觉 token 排在文字 token 前面组成一串">
<rect x="18.0" y="40.0" width="52.0" height="40.0" rx="6" style="fill:var(--paper);stroke:var(--accent);stroke-width:2"/><text x="44.0" y="66.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">左上</text><rect x="74.0" y="40.0" width="52.0" height="40.0" rx="6" style="fill:var(--paper);stroke:var(--accent);stroke-width:2"/><text x="100.0" y="66.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">右上</text><rect x="130.0" y="40.0" width="52.0" height="40.0" rx="6" style="fill:var(--paper);stroke:var(--accent);stroke-width:2"/><text x="156.0" y="66.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">左下</text><rect x="186.0" y="40.0" width="52.0" height="40.0" rx="6" style="fill:var(--paper);stroke:var(--accent);stroke-width:2"/><text x="212.0" y="66.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">右下</text><rect x="242.0" y="40.0" width="52.0" height="40.0" rx="6" style="fill:var(--paper);stroke:var(--warn);stroke-width:2"/><text x="268.0" y="66.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">竖杠</text><rect x="298.0" y="40.0" width="52.0" height="40.0" rx="6" style="fill:var(--paper);stroke:var(--muted);stroke-width:2"/><text x="324.0" y="66.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">在</text><rect x="354.0" y="40.0" width="52.0" height="40.0" rx="6" style="fill:var(--paper);stroke:var(--muted);stroke-width:2"/><text x="380.0" y="66.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">哪</text><rect x="410.0" y="40.0" width="52.0" height="40.0" rx="6" style="fill:var(--paper);stroke:var(--muted);stroke-width:2"/><text x="436.0" y="66.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">？</text><text x="128.0" y="106.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">4 个视觉 token</text><text x="352.0" y="106.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">文字 token</text><text x="240.0" y="24.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">送进大模型的一整串</text>
</svg>
<figcaption>图 8　投影后的 4 个块就是 4 个 token，和问题里的文字 token 排成一串，一起送进大模型。</figcaption>
</figure>

$W_P$ 是怎么来的？LLaVA 的做法分两段训练。第一段把视觉编码器和大模型都冻住不动，只训练投影器，数据是「图 + 一句描述」，目标是让大模型看着视觉 token 写出那句描述。这一段只是教投影器「翻译」。第二段再用「图 + 问题 + 回答」的对话数据，连大模型一起微调，让它学会围绕图回答问题。

## 第八步：文字怎么「看」图上的某一块

现在大模型拿到的一串是：4 个视觉 token，后面跟着问题「竖杠在哪？」。读到「竖杠」这个 token 时，它会用注意力去前面找线索，前面就包括那 4 个视觉 token。

和注意力那讲一样，「竖杠」先算出一个查询 $q$。设它是：

$$
q = (1,\ 1)
$$

为了少一步，假设视觉 token 的键就是它们自己（$k = z$）。打分是 $q$ 和每个 $k$ 的点积：

| 块 | $k = z$ | $q_1 k_1 + q_2 k_2$ | 分数 $s$ |
| --- | --- | --- | --- |
| 左上 | $(1.0,\ -0.8)$ | $1 \times 1.0 + 1 \times (-0.8)$ | $0.2$ |
| 右上 | $(0.2,\ 0)$ | $1 \times 0.2 + 1 \times 0$ | $0.2$ |
| 左下 | $(1.3,\ 0.5)$ | $1 \times 1.3 + 1 \times 0.5$ | $1.8$ |
| 右下 | $(0,\ -0.2)$ | $1 \times 0 + 1 \times (-0.2)$ | $-0.2$ |

除以 $\sqrt{d_k} = \sqrt{2} = 1.414$，再做 softmax：

| 块 | $s / \sqrt{2}$ | $e^{s/\sqrt{2}}$ | 份额 |
| --- | --- | --- | --- |
| 左上 | 0.141 | 1.152 | $1.152 / 6.743 = 17.1\%$ |
| 右上 | 0.141 | 1.152 | $1.152 / 6.743 = 17.1\%$ |
| 左下 | 1.273 | 3.571 | $3.571 / 6.743 = 53.0\%$ |
| 右下 | −0.141 | 0.868 | $0.868 / 6.743 = 12.9\%$ |

（总和 $1.152 + 1.152 + 3.571 + 0.868 = 6.743$；四舍五入后加起来是 100.1%。）

<figure class="fig">
<svg viewBox="0 0 480 224" role="img" aria-label="「竖杠」这个 token 分给四个图像块的注意力份额">
<rect x="40.0" y="30.0" width="40" height="40" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="80.0" y="30.0" width="40" height="40" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="130.0" y="30.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="170.0" y="30.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="40.0" y="70.0" width="40" height="40" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="80.0" y="70.0" width="40" height="40" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="130.0" y="70.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="170.0" y="70.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="40.0" y="120.0" width="40" height="40" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="80.0" y="120.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="130.0" y="120.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="170.0" y="120.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="40.0" y="160.0" width="40" height="40" fill="rgb(255,255,255)" style="stroke:var(--muted);stroke-width:1"/><rect x="80.0" y="160.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="130.0" y="160.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="170.0" y="160.0" width="40" height="40" fill="rgb(0,0,0)" style="stroke:var(--muted);stroke-width:1"/><rect x="40.0" y="30.0" width="80" height="80" rx="4" style="fill:var(--warn);fill-opacity:0.15;stroke:var(--warn);stroke-width:1.9"/><text x="80.0" y="77.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--fg);paint-order:stroke;stroke:var(--bg);stroke-width:4">17.1%</text><rect x="130.0" y="30.0" width="80" height="80" rx="4" style="fill:var(--warn);fill-opacity:0.15;stroke:var(--warn);stroke-width:1.9"/><text x="170.0" y="77.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--fg);paint-order:stroke;stroke:var(--bg);stroke-width:4">17.1%</text><rect x="40.0" y="120.0" width="80" height="80" rx="4" style="fill:var(--warn);fill-opacity:0.48;stroke:var(--warn);stroke-width:3.6"/><text x="80.0" y="167.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--fg);paint-order:stroke;stroke:var(--bg);stroke-width:4">53.0%</text><rect x="130.0" y="120.0" width="80" height="80" rx="4" style="fill:var(--warn);fill-opacity:0.12;stroke:var(--warn);stroke-width:1.6"/><text x="170.0" y="167.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--fg);paint-order:stroke;stroke:var(--bg);stroke-width:4">12.9%</text><text x="290.0" y="60.0" font-size="16" text-anchor="end" style="fill:var(--fg)">左上</text><rect x="300.0" y="44.0" width="35.5" height="22.0" rx="4" style="fill:var(--line)"/><text x="341.5" y="61.0" font-size="16" text-anchor="start" style="fill:var(--muted)">17.1%</text><text x="290.0" y="94.0" font-size="16" text-anchor="end" style="fill:var(--fg)">右上</text><rect x="300.0" y="78.0" width="35.5" height="22.0" rx="4" style="fill:var(--line)"/><text x="341.5" y="95.0" font-size="16" text-anchor="start" style="fill:var(--muted)">17.1%</text><text x="290.0" y="128.0" font-size="16" text-anchor="end" style="fill:var(--fg)">左下</text><rect x="300.0" y="112.0" width="110.0" height="22.0" rx="4" style="fill:var(--warn)"/><text x="416.0" y="129.0" font-size="16" text-anchor="start" style="fill:var(--warn)">53.0%</text><text x="290.0" y="162.0" font-size="16" text-anchor="end" style="fill:var(--fg)">右下</text><rect x="300.0" y="146.0" width="26.7" height="22.0" rx="4" style="fill:var(--line)"/><text x="332.7" y="163.0" font-size="16" text-anchor="start" style="fill:var(--muted)">12.9%</text>
</svg>
<figcaption>图 9　「竖杠」的注意力，橙色越深分得越多。一半以上落在左下那块，也就是竖杠所在的地方。</figcaption>
</figure>

一半以上的注意力落在左下那块，就是竖杠所在的地方。接下来「竖杠」按这些份额取走各块的内容，后面生成回答时就能写出「在左下」。模型「看懂」图上某处，说到底就是这一步：问题里的词，把注意力放到了相关的那几块上。

<details class="pause"><summary>停一下：如果问的是「哪里是黑的」，查询换成 q = (−1, 0)，份额怎么分？</summary>

分数是 $-z_1$：左上 $-1.0$，右上 $-0.2$，左下 $-1.3$，右下 $0$。除以 1.414：$-0.707$、$-0.141$、$-0.919$、$0$。取指数：$0.493$、$0.868$、$0.399$、$1$，总和 $2.760$。份额：左上 17.9%、右上 31.4%、左下 14.5%、右下 36.2%。两块黑的（右上、右下）一共分到 67.6%。同一组视觉 token，问题换了，注意力就落到别的地方。

</details>

## 第九步：回到真实规模

小例子里的每一步，真实模型都有，只是数字大得多。

**LLaVA-1.5**：视觉编码器是 CLIP 的 ViT-L/14，输入图先缩放到 336 × 336。每块 14 × 14 像素，切出 $336 / 14 = 24$ 行、24 列，一共 $24 \times 24 = 576$ 块。每块 14 × 14 个像素、每个像素 3 个数，展开是 $14 \times 14 \times 3 = 588$ 个数，$W_E$ 把它变成 1024 个数。经过 24 层 ViT，再经过两层 MLP 的投影器变成 4096 个数。所以一张图在大模型里就是 576 个 token。

**Qwen2-VL**：视觉编码器约 6.75 亿个参数，也是 14 × 14 像素一块。不同的是，它不把图缩成固定大小，而是按原图大小切；切完之后再把相邻的 2 × 2 块合并成一个 token，所以一个 token 对应 28 × 28 像素。224 × 224 的图是 $(224/28)^2 = 8 \times 8 = 64$ 个视觉 token，论文里写的 66 个，多出来的 2 个是标记「图片从这里开始 / 到这里结束」的特殊 token。

**Claude**：官方文档给的算法同样是 28 × 28 像素一个 token：

$$
\text{token 数} = \left\lceil \frac{\text{宽}}{28} \right\rceil \times \left\lceil \frac{\text{高}}{28} \right\rceil
$$

$\lceil\ \rceil$ 是向上取整（不满一块也算一块）。1000 × 1000 的图：$1000 / 28 = 35.7$，向上取整是 36，$36 \times 36 = 1296$ 个 token。图太大会先等比例缩小：标准档长边最多 1568 px、最多 1568 个 token，1920 × 1080 的截图缩到 1456 × 819，$52 \times 30 = 1560$ 个 token；较新的型号有高分辨率档，长边最多 2576 px、最多 4784 个 token。

<figure class="fig">
<svg viewBox="0 0 480 216" role="img" aria-label="几种真实模型里一张图占多少 token">
<text x="8.0" y="33.0" font-size="15" text-anchor="start" style="fill:var(--fg)">LLaVA-1.5，336 × 336</text><rect x="180.0" y="16.0" width="84.9" height="24.0" rx="4" style="fill:var(--accent)"/><text x="270.9" y="34.0" font-size="15" text-anchor="start" style="fill:var(--accent)">576</text><text x="8.0" y="73.0" font-size="15" text-anchor="start" style="fill:var(--fg)">Qwen2-VL，224 × 224</text><rect x="180.0" y="56.0" width="9.4" height="24.0" rx="4" style="fill:var(--accent)"/><text x="195.4" y="74.0" font-size="15" text-anchor="start" style="fill:var(--accent)">64</text><text x="8.0" y="113.0" font-size="15" text-anchor="start" style="fill:var(--fg)">Claude，1000 × 1000</text><rect x="180.0" y="96.0" width="191.1" height="24.0" rx="4" style="fill:var(--accent)"/><text x="377.1" y="114.0" font-size="15" text-anchor="start" style="fill:var(--accent)">1,296</text><text x="8.0" y="153.0" font-size="15" text-anchor="start" style="fill:var(--fg)">Claude，1920 × 1080</text><rect x="180.0" y="136.0" width="230.0" height="24.0" rx="4" style="fill:var(--accent)"/><text x="416.0" y="154.0" font-size="15" text-anchor="start" style="fill:var(--accent)">1,560</text><text x="8.0" y="193.0" font-size="15" text-anchor="start" style="fill:var(--fg)">一页 A4 中文文字</text><rect x="180.0" y="176.0" width="147.4" height="24.0" rx="4" style="fill:var(--line)"/><text x="333.4" y="194.0" font-size="15" text-anchor="start" style="fill:var(--muted)">约 1,000</text>
</svg>
<figcaption>图 10　一张图占的 token 数。最后一行是对照：一页 A4 的中文文字大约 1,000 个 token（估算）。</figcaption>
</figure>

一张普通截图，就占了一页文字那么多的 token。图像 token 和文字 token 一样占上下文窗口、一样算钱，也一样让注意力的计算量变大。这就是为什么各家都在想办法压缩视觉 token，比如 Qwen2-VL 的 2 × 2 合并，一下就少了四分之三。

前面讲的是「先单独训练视觉编码器，再接进大模型」。也有模型从一开始就把图文混在一起训练（常叫原生多模态），但从图片到视觉 token 的那几步，切块、向量、位置、投影，大体是一样的。

## 第十步：所以它会在哪里看错

知道了图是怎么变成 token 的，就能明白模型在哪些地方容易看错。

**很小的字。** 一张 3840 × 2160 的截图，在标准档里要缩到 1456 × 819，每个方向缩小到原来的 $1456 / 3840 = 0.379$ 倍。原图里 12 px 高的字，缩完只剩 $12 \times 0.379 = 4.5$ px 高；一个 28 px 高的 token 里竖着能塞下 $28 / 4.5 \approx 6$ 行这样的字。几个像素高的笔画，在缩小这一步就已经糊掉了，后面的模型再强也补不回来。所以要让模型读小字，最有效的办法是先把那一块裁出来再发。

**精确的位置和数量。** 位置只是加在向量上的一点信息（第四步），模型对「左边还是右边」「挨着还是隔一格」这类关系，靠的是训练里见过的规律，没有一把真正的尺子。数数也是：注意力把好几块的内容按份额混在一起（第八步），十几个挤在一起的小东西，很难每个只数一次。

**被修改过的常见图。** CLIP 的意思是从配文里学来的（第六步）。一张常见的图稍加改动，比如画了六根手指的手，模型容易照着「见过很多次的样子」回答，而不是照着这张图实际的像素回答。

## 实验里讲了什么

1. **00 一张图就是一张数字表**：点格子改像素，换切块大小，看块数和每块展开的数。
2. **01 每块变成一个向量**：同一张图，实时算出每块的亮度和竖边，打开、关掉位置向量，看相同的块怎么分开。
3. **02 平均会丢掉位置**：打乱四块的位置，平均向量一点不变，四个视觉 token 却不一样。
4. **03 CLIP 怎么打分**：调温度、调文字向量的方向，看 3 × 3 表格、每行的概率和损失怎么变。
5. **04 文字 token 去看图**：换问题，看注意力份额落到哪几块；改图上的像素，份额跟着变。
6. **05 一张图要多少 token**：输入图片尺寸，按 28 × 28 一块算 token 数和缩放；再看小字缩小之后还剩多少像素。

## 和前后两讲的关系

这一讲把前面几讲接在了一起：token 那讲说文字怎么变成 token，这一讲说图片怎么变成 token；块与块之间、文字和图之间用的都是注意力那讲的算法；CLIP 的训练靠的是梯度下降和反向传播；第十步说的「看不清」，和模型评测那讲一样提醒你，分数之外还要看它在哪里出错。

后面 Agent 篇里《AI 怎么浏览网页、操作电脑》那一讲，模型看的截图就是这样变成 token 的，那里的点击坐标换算也建立在这一讲的缩放上。

## 延伸阅读

- Dosovitskiy 等，*An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale*，2020（ViT）。
- Radford 等，*Learning Transferable Visual Models From Natural Language Supervision*，2021（CLIP）。
- Liu 等，*Improved Baselines with Visual Instruction Tuning*，2023（LLaVA-1.5）。
- Wang 等，*Qwen2-VL: Enhancing Vision-Language Model's Perception of the World at Any Resolution*，2024。
- Anthropic，Claude 文档 *Vision*（图像 token 的算法与分辨率上限）。
