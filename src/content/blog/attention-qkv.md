---
title: "注意力里的 Q、K、V：模型怎么知道「小米」是粮食还是手机"
description: "同一个「小米」，在粮油店里是粮食，在数码店里是手机。用一个能手算的小例子，一步步走完注意力：查询和键、点积、softmax、除以 √d、值向量与残差，最后回到真实的 Qwen3-0.6B。"
pubDate: 2026-10-14
updatedDate: 2026-10-21
tags: ["Transformer", "注意力", "QKV", "Qwen3"]
lab: /labs/attention-qkv/
series: ai-mastery
order: 5
---

<!-- 本文由 labs-src/attention-qkv/toy.py 从 article.src.md 生成，图和数字都由脚本算出。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

一个词的意思要看上下文，而在 Transformer 里，能把上下文带进一个词的只有注意力。它做三件事：给前面每个词打分，把分数变成加起来等于 1 的份额，再按份额把每个词的内容加到自己身上。写成一行公式是：

$$
\operatorname{Attention}(Q,K,V) = \operatorname{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V
$$

这一行里的每个符号，下面都会用一个能手算的小例子一步一步算出来。

## 从一个问题开始

「我在粮油店买了两斤小米」和「我在数码店买了一部小米」。模型读到「小米」时，第一步是查表：词表里每个 token 对应一个固定的向量（embedding）。查表只看 token 本身，不看上下文，所以两句话里的「小米」拿到的是**同一个向量**。

这个向量里两种意思都有。在 Qwen3-0.6B 的嵌入表里，和「小米」最像的向量是大米、米粉、小麦，接着是微软、比亚迪、华为。

把两句话分别送进模型，量两个「小米」向量之间的夹角：查表之后是 0°，过完第 1 层是 16°，到中间几层拉开到 40° 左右。一层里让一个词能「看到」别的词的只有注意力，所以这个夹角是注意力拉开的。下面就拆开它，看它怎么做到。

## 第一步：把问题缩小到能用手算

真实模型里每个向量有上千个数，没法手算，也没法画。我们先做一个缩小版：

- 句子只留 4 个 token：粮油、店、买了、小米。
- 每个向量只有 2 个数。为了好理解，把第 1 个数当作「像手机」的程度，第 2 个数当作「像粮食」的程度。真实模型的向量没有这样的标签，这里只是为了能画在纸上。

| token | 向量 $x$ |
| --- | --- |
| 粮油 | $(0,\ 1)$ |
| 店 | $(0.4,\ 0.2)$ |
| 买了 | $(0.2,\ 0)$ |
| 小米 | $(0.5,\ 0.5)$ |

「小米」是 $(0.5,\ 0.5)$：像手机和像粮食各占一半，这就是查表之后「两种意思都有」的样子。

<figure class="fig">
<svg viewBox="0 0 480 270" role="img" aria-label="四个 token 的向量 x 画在平面上">
<line x1="70.0" y1="240.0" x2="280.0" y2="240.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M291.0 240.0 L281.0 244.5 L281.0 235.5 z" style="fill:var(--line)"/><line x1="70.0" y1="240.0" x2="70.0" y2="30.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M70.0 19.0 L74.5 29.0 L65.5 29.0 z" style="fill:var(--line)"/><text x="291.0" y="262.0" font-size="16" text-anchor="end" style="fill:var(--muted)">像手机</text><text x="78.0" y="21.0" font-size="16" text-anchor="start" style="fill:var(--muted)">像粮食</text><line x1="70.0" y1="240.0" x2="70.0" y2="71.0" style="stroke:var(--muted);stroke-width:2;fill:none"/><path d="M70.0 60.0 L74.5 70.0 L65.5 70.0 z" style="fill:var(--muted)"/><text x="82.0" y="64.0" font-size="16" text-anchor="start" style="fill:var(--muted)">粮油 (0, 1.0)</text><line x1="70.0" y1="240.0" x2="132.2" y2="208.9" style="stroke:var(--muted);stroke-width:2;fill:none"/><path d="M142.0 204.0 L135.0 212.5 L131.0 204.5 z" style="fill:var(--muted)"/><text x="152.0" y="208.0" font-size="16" text-anchor="start" style="fill:var(--muted)">店 (0.4, 0.2)</text><line x1="70.0" y1="240.0" x2="95.0" y2="240.0" style="stroke:var(--muted);stroke-width:2;fill:none"/><path d="M106.0 240.0 L96.0 244.5 L96.0 235.5 z" style="fill:var(--muted)"/><text x="106.0" y="262.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">买了 (0.2, 0)</text><line x1="70.0" y1="240.0" x2="152.2" y2="157.8" style="stroke:var(--fg);stroke-width:3;fill:none"/><path d="M160.0 150.0 L156.1 160.3 L149.7 153.9 z" style="fill:var(--fg)"/><text x="170.0" y="142.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">小米 (0.5, 0.5)</text>
</svg>
<figcaption>图 1　四个 token 的向量 x。横坐标是「像手机」的程度，纵坐标是「像粮食」的程度（示意）。</figcaption>
</figure>

我们的目标：算完注意力之后，「小米」的向量应该往「像粮食」那边偏，因为句子里有「粮油」。这一组数字会一直用到最后。

## 第二步：「小米」把自己变成一个问题

先想一个最直接的办法：拿「小米」的向量 $x$ 去和每个词的 $x$ 比，谁和它像，就多看谁。比「像不像」常用余弦相似度（两个向量夹角的余弦，方向完全相同是 1）。算出来是：小米自己 1.000，店 0.949，粮油 0.707，买了 0.707。

最像「小米」的永远是它自己，其次是方向相近的词。可「小米」需要的不是和自己长得像的词，而是**能说明「我是哪个小米」的词**，也就是「粮油」。所以注意力不直接比 $x$，而是先让每个词把自己的向量换一种说法。

「小米」用一个矩阵 $W_Q$ 把自己的 $x$ 变成**查询** $q$（query），意思是「我在找什么线索」：

$$
q = W_Q\,x
$$

例子里的 $W_Q$ 是：

$$
W_Q = \begin{pmatrix} 1 & 1 \\ 0 & -1.2 \end{pmatrix}
$$

矩阵乘向量的算法是：**矩阵的每一行，和向量对应位置相乘，再加起来**，得到结果的一个数（点积和矩阵乘向量见上一讲，这里的数字也和上一讲相同）。$W_Q$ 有两行，所以 $q$ 有两个数。

第 1 行是 $(1,\ 1)$，和 $x = (0.5,\ 0.5)$ 对应相乘再相加：

$$
1 \times 0.5 + 1 \times 0.5 = 0.5 + 0.5 = 1.0
$$

第 2 行是 $(0,\ -1.2)$，同样做：

$$
0 \times 0.5 + (-1.2) \times 0.5 = 0 - 0.6 = -0.6
$$

所以「小米」的查询是：

$$
q = (1.0,\ -0.6)
$$

「对应位置相乘再相加」这个操作有个名字，叫**点积**，第四步打分时还会用到它。

$W_Q$ 里的数是怎么来的？训练开始时是随机数，训练过程中被一点点调整，调到「拿这个 $q$ 去找，能找到有用的线索」为止。所有 token 共用同一个 $W_Q$。

## 第三步：每个词给自己贴一个标签

被找的一方也要换一种说法。每个词用另一个矩阵 $W_K$ 把自己的 $x$ 变成**键** $k$（key），意思是「我能提供什么线索」：

$$
k = W_K\,x \qquad W_K = \begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}
$$

$W_K$ 的第 1 行 $(1,\ 1)$ 把 $x$ 的两个数加起来，第 2 行 $(1,\ -1)$ 用第 1 个数减第 2 个数。四个词逐个算：

| token | $x$ | 第 1 个数：$x_1 + x_2$ | 第 2 个数：$x_1 - x_2$ | $k$ |
| --- | --- | --- | --- | --- |
| 粮油 | $(0,\ 1)$ | $0 + 1 = 1$ | $0 - 1 = -1$ | $(1,\ -1)$ |
| 店 | $(0.4,\ 0.2)$ | $0.4 + 0.2 = 0.6$ | $0.4 - 0.2 = 0.2$ | $(0.6,\ 0.2)$ |
| 买了 | $(0.2,\ 0)$ | $0.2 + 0 = 0.2$ | $0.2 - 0 = 0.2$ | $(0.2,\ 0.2)$ |
| 小米 | $(0.5,\ 0.5)$ | $0.5 + 0.5 = 1$ | $0.5 - 0.5 = 0$ | $(1,\ 0)$ |

「小米」自己也有一个 $k$，因为它也会被别的词（包括它自己）找。

$q$ 和 $k$ 画在同一个平面上。注意这已经不是「像手机 / 像粮食」的平面了，而是「线索」的平面，两个轴没有现成的名字：

<figure class="fig">
<svg viewBox="0 0 480 300" role="img" aria-label="线索平面里小米的查询 q 和四个 token 的键 k">
<line x1="6.0" y1="150.0" x2="301.0" y2="150.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M312.0 150.0 L302.0 154.5 L302.0 145.5 z" style="fill:var(--line)"/><line x1="150.0" y1="288.0" x2="150.0" y2="53.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M150.0 42.0 L154.5 52.0 L145.5 52.0 z" style="fill:var(--line)"/><line x1="150.0" y1="150.0" x2="262.2" y2="262.2" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><path d="M270.0 270.0 L259.7 266.1 L266.1 259.7 z" style="fill:var(--accent)"/><text x="278.0" y="286.0" font-size="16" text-anchor="start" style="fill:var(--accent)">粮油 (1.0, −1.0)</text><line x1="150.0" y1="150.0" x2="211.6" y2="129.5" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><path d="M222.0 126.0 L213.9 133.4 L211.1 124.9 z" style="fill:var(--accent)"/><text x="230.0" y="120.0" font-size="16" text-anchor="start" style="fill:var(--accent)">店 (0.6, 0.2)</text><line x1="150.0" y1="150.0" x2="166.2" y2="133.8" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><path d="M174.0 126.0 L170.1 136.3 L163.7 129.9 z" style="fill:var(--accent)"/><text x="168.0" y="118.0" font-size="16" text-anchor="end" style="fill:var(--accent)">买了 (0.2, 0.2)</text><line x1="150.0" y1="150.0" x2="259.0" y2="150.0" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><path d="M270.0 150.0 L260.0 154.5 L260.0 145.5 z" style="fill:var(--accent)"/><text x="276.0" y="140.0" font-size="16" text-anchor="start" style="fill:var(--accent)">小米 (1.0, 0)</text><line x1="150.0" y1="150.0" x2="260.6" y2="216.3" style="stroke:var(--warn);stroke-width:3.5;fill:none"/><path d="M270.0 222.0 L259.1 220.7 L263.7 213.0 z" style="fill:var(--warn)"/><text x="280.0" y="244.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--warn)">q (1.0, −0.6)</text>
</svg>
<figcaption>图 2　橙色是「小米」的查询 q，蓝色是每个 token 的键 k。和 q 方向越接近、越长的 k，点积越大。</figcaption>
</figure>

## 第四步：用点积打分

「小米」拿自己的 $q$，和每个词的 $k$ 做点积，得到一个分数 $s$：

$$
s = q \cdot k = q_1 k_1 + q_2 k_2
$$

$q = (1.0,\ -0.6)$，四个分数逐个算：

| token | $k$ | $q_1 k_1$ | $q_2 k_2$ | 分数 $s$ |
| --- | --- | --- | --- | --- |
| 粮油 | $(1,\ -1)$ | $1.0 \times 1 = 1.0$ | $(-0.6) \times (-1) = 0.6$ | $1.6$ |
| 店 | $(0.6,\ 0.2)$ | $1.0 \times 0.6 = 0.6$ | $(-0.6) \times 0.2 = -0.12$ | $0.48$ |
| 买了 | $(0.2,\ 0.2)$ | $1.0 \times 0.2 = 0.2$ | $(-0.6) \times 0.2 = -0.12$ | $0.08$ |
| 小米 | $(1,\ 0)$ | $1.0 \times 1 = 1.0$ | $(-0.6) \times 0 = 0$ | $1.0$ |

点积为什么能当分数？它还可以写成：

$$
q \cdot k = \lVert q \rVert \, \lVert k \rVert \cos\theta
$$

$\lVert q \rVert$、$\lVert k \rVert$ 是两个向量的长度，$\theta$ 是它们的夹角。方向一致时 $\cos\theta = 1$，点积最大；垂直时 $\cos\theta = 0$，点积为 0；方向相反时点积为负。在图 2 里，「粮油」的 $k$ 和 $q$ 方向最接近，长度也最长，所以分数最高。

把两种比法放在一起：

<figure class="fig">
<svg viewBox="0 0 480 210" role="img" aria-label="两种比法：x 的相似度与 q 点乘 k">
<text x="70.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">比 x 的相似度（余弦）</text><text x="290.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">比 q·k（点积）</text><text x="60.0" y="61.0" font-size="16" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="70" y="44" width="83.4" height="24" rx="4" style="fill:var(--line)"/><text x="159.4" y="62.0" font-size="16" text-anchor="start" style="fill:var(--muted)">0.707</text><rect x="290" y="44" width="118.0" height="24" rx="4" style="fill:var(--warn)"/><text x="414.0" y="62.0" font-size="16" text-anchor="start" style="fill:var(--warn)">1.6</text><text x="60.0" y="101.0" font-size="16" text-anchor="end" style="fill:var(--fg)">店</text><rect x="70" y="84" width="111.9" height="24" rx="4" style="fill:var(--line)"/><text x="187.9" y="102.0" font-size="16" text-anchor="start" style="fill:var(--muted)">0.949</text><rect x="290" y="84" width="35.4" height="24" rx="4" style="fill:var(--line)"/><text x="331.4" y="102.0" font-size="16" text-anchor="start" style="fill:var(--muted)">0.48</text><text x="60.0" y="141.0" font-size="16" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="70" y="124" width="83.4" height="24" rx="4" style="fill:var(--line)"/><text x="159.4" y="142.0" font-size="16" text-anchor="start" style="fill:var(--muted)">0.707</text><rect x="290" y="124" width="5.9" height="24" rx="4" style="fill:var(--line)"/><text x="301.9" y="142.0" font-size="16" text-anchor="start" style="fill:var(--muted)">0.08</text><text x="60.0" y="181.0" font-size="16" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="70" y="164" width="118.0" height="24" rx="4" style="fill:var(--warn)"/><text x="194.0" y="182.0" font-size="16" text-anchor="start" style="fill:var(--warn)">1.000</text><rect x="290" y="164" width="73.8" height="24" rx="4" style="fill:var(--line)"/><text x="369.8" y="182.0" font-size="16" text-anchor="start" style="fill:var(--muted)">1.0</text>
</svg>
<figcaption>图 3　左边直接比向量 x：最像「小米」的是它自己。右边用 q 去对 k：分数最高的是「粮油」。</figcaption>
</figure>

直接比 $x$，「粮油」只排并列第三；用 $q$ 去对 $k$，「粮油」排第一。$W_Q$ 和 $W_K$ 的作用就在这里：它们把「长得像」换成了「对我有用」。

<details class="pause"><summary>停一下：如果 <i>W</i><sub>Q</sub> 和 <i>W</i><sub>K</sub> 都是「什么都不改」的矩阵，第一名会是谁？</summary>

「什么都不改」的矩阵是 $\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}$（单位矩阵），乘完之后 $q = x$、$k = x$。分数就变成 $x$ 和 $x$ 的点积。「小米」对自己：$0.5 \times 0.5 + 0.5 \times 0.5 = 0.5$；对「粮油」：$0.5 \times 0 + 0.5 \times 1 = 0.5$；对「店」：$0.5 \times 0.4 + 0.5 \times 0.2 = 0.3$；对「买了」：$0.5 \times 0.2 + 0.5 \times 0 = 0.1$。「小米」自己和「粮油」并列第一，自己挤占了一半的注意力。这就是为什么要有两个专门训练出来的矩阵。

</details>

## 第五步：softmax 把分数变成份额

分数有大有小，还可能是负的。我们要的是**份额**：每个词分到多少，全部加起来正好是 100%。做法叫 softmax（上一讲第十二步算过同一组分数），分两步。

**第 1 步，每个分数取指数** $e^{s}$（$e \approx 2.718$）。指数有两个作用：结果一定是正数；分数大一点，结果就大很多，差距被拉开。

| token | 分数 $s$ | $e^{s}$ |
| --- | --- | --- |
| 粮油 | 1.6 | 4.953 |
| 店 | 0.48 | 1.616 |
| 买了 | 0.08 | 1.083 |
| 小米 | 1.0 | 2.718 |

**第 2 步，每个数除以它们的总和。** 总和是 $4.953 + 1.616 + 1.083 + 2.718 = 10.370$。

$$
w_{\text{粮油}} = \frac{4.953}{10.370} = 0.478 \qquad w_{\text{店}} = \frac{1.616}{10.370} = 0.156
$$

$$
w_{\text{买了}} = \frac{1.083}{10.370} = 0.104 \qquad w_{\text{小米}} = \frac{2.718}{10.370} = 0.262
$$

四个份额 47.8%、15.6%、10.4%、26.2%，加起来是 100%。合起来写成公式：

$$
w_i = \frac{e^{s_i}}{\sum_{j} e^{s_j}}
$$

分母 $\sum_j e^{s_j}$ 就是「所有 $e^{s}$ 的总和」。

<figure class="fig">
<svg viewBox="0 0 480 210" role="img" aria-label="点积分数经过 softmax 变成份额">
<text x="70.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">分数 s</text><text x="290.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">份额 w（softmax 后）</text><text x="60.0" y="61.0" font-size="16" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="70" y="44" width="118.0" height="24" rx="4" style="fill:var(--warn)"/><text x="194.0" y="62.0" font-size="16" text-anchor="start" style="fill:var(--warn)">1.6</text><rect x="290" y="44" width="118.0" height="24" rx="4" style="fill:var(--warn)"/><text x="414.0" y="62.0" font-size="16" text-anchor="start" style="fill:var(--warn)">47.8%</text><text x="60.0" y="101.0" font-size="16" text-anchor="end" style="fill:var(--fg)">店</text><rect x="70" y="84" width="35.4" height="24" rx="4" style="fill:var(--line)"/><text x="111.4" y="102.0" font-size="16" text-anchor="start" style="fill:var(--muted)">0.48</text><rect x="290" y="84" width="38.5" height="24" rx="4" style="fill:var(--line)"/><text x="334.5" y="102.0" font-size="16" text-anchor="start" style="fill:var(--muted)">15.6%</text><text x="60.0" y="141.0" font-size="16" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="70" y="124" width="5.9" height="24" rx="4" style="fill:var(--line)"/><text x="81.9" y="142.0" font-size="16" text-anchor="start" style="fill:var(--muted)">0.08</text><rect x="290" y="124" width="25.8" height="24" rx="4" style="fill:var(--line)"/><text x="321.8" y="142.0" font-size="16" text-anchor="start" style="fill:var(--muted)">10.4%</text><text x="60.0" y="181.0" font-size="16" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="70" y="164" width="73.8" height="24" rx="4" style="fill:var(--line)"/><text x="149.8" y="182.0" font-size="16" text-anchor="start" style="fill:var(--muted)">1.0</text><rect x="290" y="164" width="64.8" height="24" rx="4" style="fill:var(--line)"/><text x="360.8" y="182.0" font-size="16" text-anchor="start" style="fill:var(--muted)">26.2%</text>
</svg>
<figcaption>图 4　左边是分数，右边是 softmax 之后的份额，四个份额加起来是 100%。顺序不变，差距被指数放大。</figcaption>
</figure>

为什么不干脆把 100% 都给分数最高的「粮油」？有两个原因。

第一，线索常常不止一个。在完整的句子里，「粮油」和「店」合起来才说明这是一家粮油店，两个都该分到一些。

第二，训练要靠「微调一点，看结果变不变」。假设训练想让「店」多分一点，把它的分数从 0.48 调到 0.58。用 softmax：$e^{0.58} = 1.786$，总和变成 $10.370 - 1.616 + 1.786 = 10.540$，「店」的份额从 15.6% 变成 $1.786 / 10.540 = 16.9\%$，结果跟着变了。如果只给第一名：调之前「粮油」100%、「店」0%，调之后还是「粮油」100%、「店」0%，结果纹丝不动。结果不变，训练就不知道这一下调得对不对、该往哪边调（用训练的话说，梯度是 0）。

<details class="pause"><summary>停一下：把四个分数都加上 10，份额会变吗？</summary>

不会。每个 $e^{s}$ 都变成 $e^{s+10} = e^{s} \times e^{10}$，分子和分母都乘了同一个 $e^{10}$，约掉之后份额不变。softmax 只看分数之间的**差**，不看分数本身有多大。下一步会用到这一点。

</details>

## 第六步：为什么要除以 $\sqrt{d_k}$

上一个「停一下」说明：份额只取决于分数之间差多少。差 1，指数之后是 $e^{1} \approx 2.7$ 倍；差 11，就是 $e^{11} \approx 60{,}000$ 倍。分数之间的差距一大，份额就几乎全给了第一名，又回到了「只给第一名」。

我们的例子里 $q$、$k$ 只有 2 个数。真实模型里 $q$、$k$ 的长度 $d_k$ 要大得多，Qwen3-0.6B 每个头 $d_k = 128$。点积是 $d_k$ 个乘积加起来，加的项越多，分数散得越开。散开多少？一步一步算。

假设 $q$ 和 $k$ 的每一个数都是随机的，平均值是 0，方差是 1（方差衡量散开的程度；方差是 1，就是一般偏离 0 大约 1）。

**(1) 一个乘积 $q_i k_i$ 的平均值。** $q_i$ 和 $k_i$ 互不相关，乘积的平均值等于平均值的乘积：$0 \times 0 = 0$。

**(2) 一个乘积 $q_i k_i$ 的方差。** 平均值是 0 时，方差就等于「平方的平均值」。$(q_i k_i)^2 = q_i^2 \, k_i^2$，两者互不相关，平均值仍然可以拆开相乘。$q_i$ 的平均值是 0、方差是 1，所以 $q_i^2$ 的平均值是 1；$k_i^2$ 也一样。于是：

$$
\operatorname{Var}(q_i k_i) = \overline{q_i^2} \times \overline{k_i^2} = 1 \times 1 = 1
$$

**(3) $d_k$ 个乘积加起来。** 互不相关的随机数相加，方差直接相加：

$$
\operatorname{Var}(q \cdot k) = \underbrace{1 + 1 + \cdots + 1}_{d_k \text{ 个}} = d_k
$$

**(4) 换成「一般偏离多少」。** 标准差是方差开根号：

$$
\operatorname{std}(q \cdot k) = \sqrt{d_k}
$$

代入 $d_k = 128$：$\sqrt{128} \approx 11.3$。分数之间一般差十几，按上面的算法，第一名的份额会是 $e^{11.3} \approx 80{,}000$ 倍，几乎拿走全部。

解决办法是先把分数除以 $\sqrt{d_k}$，再做 softmax。除完之后标准差变成 $11.3 / 11.3 = 1$，分数之间一般只差 1 左右，份额就能分散开：

$$
\operatorname{std}\!\left(\frac{q\cdot k}{\sqrt{d_k}}\right) = \frac{\sqrt{d_k}}{\sqrt{d_k}} = 1
$$

这一步是原论文专门加的，这个算法也因此叫**缩放点积注意力**。

回到我们的例子，$d_k = 2$，除以 $\sqrt{2} \approx 1.414$（相当于上一讲的温度 $T = \sqrt{2}$）：

| token | 分数 $s$ | $s / \sqrt{2}$ | $e^{s/\sqrt{2}}$ | 份额 |
| --- | --- | --- | --- | --- |
| 粮油 | 1.6 | 1.131 | 3.100 | $3.100 / 7.590 = 40.8\%$ |
| 店 | 0.48 | 0.339 | 1.404 | $1.404 / 7.590 = 18.5\%$ |
| 买了 | 0.08 | 0.057 | 1.058 | $1.058 / 7.590 = 13.9\%$ |
| 小米 | 1.0 | 0.707 | 2.028 | $2.028 / 7.590 = 26.7\%$ |

（$e^{s/\sqrt{2}}$ 的总和是 $3.100 + 1.404 + 1.058 + 2.028 = 7.590$；四个份额四舍五入后加起来是 99.9%。）

<figure class="fig">
<svg viewBox="0 0 480 210" role="img" aria-label="除以根号 2 之前和之后的份额">
<text x="70.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">不缩放</text><text x="290.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">除以 √2 之后</text><text x="60.0" y="61.0" font-size="16" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="70" y="44" width="118.0" height="24" rx="4" style="fill:var(--warn)"/><text x="194.0" y="62.0" font-size="16" text-anchor="start" style="fill:var(--warn)">47.8%</text><rect x="290" y="44" width="118.0" height="24" rx="4" style="fill:var(--warn)"/><text x="414.0" y="62.0" font-size="16" text-anchor="start" style="fill:var(--warn)">40.8%</text><text x="60.0" y="101.0" font-size="16" text-anchor="end" style="fill:var(--fg)">店</text><rect x="70" y="84" width="38.5" height="24" rx="4" style="fill:var(--line)"/><text x="114.5" y="102.0" font-size="16" text-anchor="start" style="fill:var(--muted)">15.6%</text><rect x="290" y="84" width="53.4" height="24" rx="4" style="fill:var(--line)"/><text x="349.4" y="102.0" font-size="16" text-anchor="start" style="fill:var(--muted)">18.5%</text><text x="60.0" y="141.0" font-size="16" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="70" y="124" width="25.8" height="24" rx="4" style="fill:var(--line)"/><text x="101.8" y="142.0" font-size="16" text-anchor="start" style="fill:var(--muted)">10.4%</text><rect x="290" y="124" width="40.3" height="24" rx="4" style="fill:var(--line)"/><text x="336.3" y="142.0" font-size="16" text-anchor="start" style="fill:var(--muted)">13.9%</text><text x="60.0" y="181.0" font-size="16" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="70" y="164" width="64.8" height="24" rx="4" style="fill:var(--line)"/><text x="140.8" y="182.0" font-size="16" text-anchor="start" style="fill:var(--muted)">26.2%</text><rect x="290" y="164" width="77.2" height="24" rx="4" style="fill:var(--line)"/><text x="373.2" y="182.0" font-size="16" text-anchor="start" style="fill:var(--muted)">26.7%</text>
</svg>
<figcaption>图 5　除以 √2 之后，第一名的份额从 47.8% 降到 40.8%，其他 token 分到的更多。</figcaption>
</figure>

2 维时变化不大。真实模型里变化很大：Qwen3-0.6B 第 1 层第 11 个头里，「小米」对前面 7 个 token 的原始分数在 240 到 285 之间，最高和最低差四十多。不缩放，第一名拿走几乎 100%；除以 $\sqrt{128}$ 之后，这个头给「粮油」37%、「买了」25%、「店」16%。

## 第七步：值向量：拿走的是内容

份额决定了「看谁、看多少」。可从每个词那里拿走的东西，不是它的 $k$。每个词还要用第三个矩阵 $W_V$ 算出**值** $v$（value）：

$$
v = W_V\,x \qquad W_V = \begin{pmatrix} 1 & 0 \\ 0 & 2 \end{pmatrix}
$$

$W_V$ 第 1 行 $(1,\ 0)$ 取出 $x$ 的第 1 个数，第 2 行 $(0,\ 2)$ 把第 2 个数乘 2：

| token | $x$ | $v = (x_1,\ 2x_2)$ |
| --- | --- | --- |
| 粮油 | $(0,\ 1)$ | $(0,\ 2)$ |
| 店 | $(0.4,\ 0.2)$ | $(0.4,\ 0.4)$ |
| 买了 | $(0.2,\ 0)$ | $(0.2,\ 0)$ |
| 小米 | $(0.5,\ 0.5)$ | $(0.5,\ 1)$ |

$v$ 和 $x$ 在同一个「像手机 / 像粮食」的平面里，它是这个词要交出去的内容。

为什么 $k$ 和 $v$ 要分开？想想图书馆：$k$ 是书脊上的分类标签，你靠它决定拿哪本；$v$ 是书里的内容，是你真正读进去的东西。在完整的两句话里，「粮油」和「数码」的 $k$ 可以很像（都在说「我是一类店」），这样「小米」两次都能找到店名；它们的 $v$ 却一个带着「卖粮食」，一个带着「卖电子产品」，「小米」读进去的内容就不一样。

## 第八步：按份额加起来，再加回自己身上

用第六步的份额（缩放之后的那组），给每个 $v$ 乘上它的份额：

| token | 份额 $w$ | $w \times v$ |
| --- | --- | --- |
| 粮油 | 0.408 | $0.408 \times (0,\ 2) = (0,\ 0.816)$ |
| 店 | 0.185 | $0.185 \times (0.4,\ 0.4) = (0.074,\ 0.074)$ |
| 买了 | 0.139 | $0.139 \times (0.2,\ 0) = (0.028,\ 0)$ |
| 小米 | 0.267 | $0.267 \times (0.5,\ 1) = (0.134,\ 0.267)$ |

把四行加起来，第 1 个数和第 2 个数分别相加，得到修改量 $\Delta x$：

$$
\Delta x = (0 + 0.074 + 0.028 + 0.134,\ \ 0.816 + 0.074 + 0 + 0.267) = (0.236,\ 1.157)
$$

最后一步是**加**到「小米」原来的向量上，不是替换它：

$$
x' = x + \Delta x = (0.5 + 0.236,\ \ 0.5 + 1.157) = (0.736,\ 1.657)
$$

这种「把修改量加回原来的向量」的做法叫**残差连接**。加的好处是：「小米」原来的意思还在，只是多带上了上下文。

<figure class="fig">
<svg viewBox="0 0 480 330" role="img" aria-label="加权的值向量首尾相接，加到原来的小米向量上">
<line x1="70.0" y1="300.0" x2="233.0" y2="300.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M244.0 300.0 L234.0 304.5 L234.0 295.5 z" style="fill:var(--line)"/><line x1="70.0" y1="300.0" x2="70.0" y2="17.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M70.0 6.0 L74.5 16.0 L65.5 16.0 z" style="fill:var(--line)"/><text x="244.0" y="322.0" font-size="16" text-anchor="end" style="fill:var(--muted)">像手机</text><text x="78.0" y="8.0" font-size="16" text-anchor="start" style="fill:var(--muted)">像粮食</text><line x1="70.0" y1="300.0" x2="142.2" y2="227.8" style="stroke:var(--muted);stroke-width:3;fill:none"/><path d="M150.0 220.0 L146.1 230.3 L139.7 223.9 z" style="fill:var(--muted)"/><text x="160.0" y="238.0" font-size="16" text-anchor="start" style="fill:var(--muted)">x（原来的小米）</text><line x1="150.0" y1="220.0" x2="150.0" y2="100.3" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><path d="M150.0 89.3 L154.5 99.4 L145.5 99.4 z" style="fill:var(--accent)"/><text x="172.0" y="160.7" font-size="16" text-anchor="start" style="fill:var(--accent)">粮油 ×40.8%</text><line x1="150.0" y1="89.3" x2="166.5" y2="56.4" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><path d="M171.4 46.6 L170.9 57.5 L162.9 53.5 z" style="fill:var(--accent)"/><text x="182.7" y="73.9" font-size="16" text-anchor="start" style="fill:var(--accent)">小米 ×26.7%</text><line x1="171.4" y1="46.6" x2="175.4" y2="42.5" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><path d="M183.2 34.7 L179.3 45.0 L172.9 38.7 z" style="fill:var(--accent)"/><line x1="183.2" y1="34.7" x2="176.7" y2="34.7" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><path d="M187.7 34.7 L177.6 39.2 L177.6 30.2 z" style="fill:var(--accent)"/><line x1="70.0" y1="300.0" x2="183.2" y2="44.8" style="stroke:var(--warn);stroke-width:3.5;fill:none"/><path d="M187.7 34.7 L187.7 45.7 L179.5 42.1 z" style="fill:var(--warn)"/><text x="197.7" y="38.7" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--warn)">x′ (0.74, 1.66)</text>
</svg>
<figcaption>图 6　灰色是原来的 x，蓝色是按份额缩小后的各个 v，首尾相接（「店」「买了」两段太短，在箭头末端几乎看不见）；橙色是加完之后的 x′，比原来更偏向「像粮食」。</figcaption>
</figure>

原来的 $x = (0.5,\ 0.5)$ 和横轴的夹角是 45°（像手机和像粮食一样多）。新的 $x' = (0.736,\ 1.657)$，夹角是 $\arctan(1.657 / 0.736) \approx 66°$，明显往「像粮食」那边偏了。偏过去的主要原因是「粮油」：它分到的份额最大，它的 $v$ 又正好指向「像粮食」。

<details class="pause"><summary>停一下：如果句子是「数码店」，「数码」的 <i>x</i> 是 (1, 0)，它的 <i>v</i> 是多少？「小米」会往哪边偏？</summary>

$v = (x_1,\ 2x_2) = (1,\ 0)$，指向「像手机」。如果「数码」也分到最大的份额，$\Delta x$ 里最大的一项就是沿横轴的，「小米」会往「像手机」那边偏。同一个「小米」，因为上下文里的 $v$ 不同，被推向了不同的方向。

</details>

## 合起来：矩阵写法

上面八步是对「小米」一个词做的。实际上句子里每个词都同时这样做一遍。把所有词的 $q$ 按行叠起来，就是矩阵 $Q$；$k$、$v$ 同样叠成 $K$、$V$。于是：

- 第四步「每个 $q$ 和每个 $k$ 做点积」，一次算完就是 $QK^{\top}$（$K^{\top}$ 是把 $K$ 转置，行变成列）。
- 第六步「除以 $\sqrt{d_k}$」和第五步「softmax」，对每一行做一遍。
- 第八步「按份额把 $v$ 加起来」，就是再乘一个 $V$。

这正是开头那一行公式：

$$
\operatorname{Attention}(Q,K,V) = \operatorname{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V
$$

最后的残差 $x' = x + \Delta x$ 写在公式外面，由 Transformer 每一层的结构负责。

## 回到真实模型

真实的 Qwen3-0.6B 做的事和上面完全一样，只是规模不同：每个向量 1024 个数，每个头的 $q$、$k$ 是 128 个数，每层有 16 个头，一共 28 层。每个头有自己的一套 $W_Q$、$W_K$、$W_V$，各找一种线索。上面实验里的数字都来自这个模型的真实输出：第 1 层第 11 个头在两句话里都把最大的一份给了店名；第 1 层里两个「小米」的 $q$ 完全相同（向量相同、位置也相同），变的是前面那些词的 $k$。

## 实验里讲了什么

0. **同一个「小米」。** Qwen3-0.6B 嵌入表里「小米」的最近邻一半是粮食、一半是科技公司；两句话里的「小米」向量夹角逐层变化（另附「长城」：城墙 / 汽车）。
1. **回头看。** 第 1 层第 11 个头里「小米」分给前面每个词的真实份额，两句话都把最大一份给了店名。
2. **相似不等于有用。** 真实数据里余弦相似度第一名是自己，$q\cdot k$ 第一名是店名；第 1 层两个「小米」的 $q$ 实测完全相同。
3. **点积。** 用本文的 4 个 token：转动 $q$，看每个词的 $q\cdot k$ 怎么变。
4. **softmax。** 用本文的分数：拖动「店」的分数，softmax 份额平滑变化，「只给第一名」是台阶。
5. **除以 $\sqrt{d_k}$。** 真实分数缩放前后的份额对比；随机向量验证标准差约为 $\sqrt{d_k}$。
6. **值向量与残差。** 用本文的 $v$ 和份额：加权的 $v$ 首尾相接，加到 $x$ 上得到 $x'$。
7. **真实模型拆解。** Qwen3-0.6B 的 28 层 × 16 个头逐个查看，热力图显示每个头给某个词的份额；从第 4 层起大量份额停在第一个 token 上（attention sink）。

## 和前后两讲的关系

前面两讲讲了 token 怎么进出模型，以及这里用到的数学（点积、矩阵乘向量、softmax）；这一讲拆开其中的注意力，只看一个头。下一讲补上这里没讲的词序：注意力本身分不清谁在前、谁在后，要靠位置编码（RoPE）；再下一讲把多头拆开：为什么要切成几十个头，又为什么让几个查询头共用一组 $k$、$v$（GQA）；然后是注意力后面的 MLP。之后的 KV Cache 一讲建立在这里的 $k$、$v$ 上：生成新 token 时，前面每个词的 $k$、$v$ 不会变，可以存下来反复用。

## 延伸阅读

- Vaswani et al., *Attention Is All You Need* (2017)
- Xiao et al., *Efficient Streaming Language Models with Attention Sinks* (2023)
- Qwen Team, *Qwen3 Technical Report* (2025)
