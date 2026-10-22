---
title: "向量、矩阵乘法与 softmax：读懂大模型需要的全部数学"
description: "不需要学过线性代数和概率。用 4 个 token、每个 2 个数的小例子，从头算到尾：向量是一支箭头，点积量两个方向有多一致，矩阵乘向量就是逐行做点积，线性层是 Wx + b，softmax 把分数变成概率，温度改变它的尖平，对数把乘法变成加法。读完这一讲，下一讲注意力里的每个式子都不会再卡住。"
pubDate: 2026-10-22
tags: ["入门", "数学", "向量", "矩阵", "softmax"]
lab: /labs/vectors-softmax/
series: ai-mastery
order: 4.5
---

<!-- 本文由 labs-src/vectors-softmax/toy.py 从 article.src.md 生成，图和数字都由脚本算出。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

大模型里的数学只有几样东西反复出现：**向量**（一串数，可以画成一支箭头）、**点积**（两串数逐项相乘再相加，量两个方向有多一致）、**矩阵乘向量**（拿矩阵的每一行和向量做一次点积）、**softmax**（把一串分数变成加起来等于 1 的概率）、**对数**（把很多个概率相乘变成相加）。上一讲说的 Embedding、输出投影、温度采样，下一讲的注意力，全都由这几样拼成。这一讲用同一组小数字，把每一样从头算一遍。

## 第一步：向量就是一串数

上一讲说过，每个 token 进了模型，先查表换成一串数。这串数就叫**向量**。Llama-3-8B 里每个 token 换成 4096 个数，GPT-2 里是 768 个。

4096 个数没法手算，也没法画。这一讲先用一个缩小版，一直用到最后：

- 只有 4 个 token：粮油、店、买了、小米。
- 每个向量只有 2 个数。为了好理解，把第 1 个数当作「像手机」的程度，第 2 个数当作「像粮食」的程度。真实模型的向量没有这样的标签，这里只是为了能画在纸上。

| token | 向量 |
| --- | --- |
| 粮油 | $(0,\ 1)$ |
| 店 | $(0.4,\ 0.2)$ |
| 买了 | $(0.2,\ 0)$ |
| 小米 | $(0.5,\ 0.5)$ |

向量一般用一个小写斜体字母表示，比如「小米」的向量记作 $x = (0.5,\ 0.5)$。里面的第 1 个数记作 $x_1 = 0.5$，第 2 个数记作 $x_2 = 0.5$，右下角的小数字叫**下标**，表示「第几个」。向量里有几个数，就说它是几**维**的：$x$ 是 2 维的，Llama-3-8B 的向量是 4096 维的。

## 第二步：2 维向量可以画成一支箭头

2 个数正好对应平面上的一个位置：第 1 个数是往右走多少，第 2 个数是往上走多少。从原点出发画一支箭头指到那个位置，就是这个向量的图。

<figure class="fig">
<svg viewBox="0 0 480 280" role="img" aria-label="向量 (0.5, 0.5) 画成从原点出发的箭头">
<line x1="70.0" y1="250.0" x2="418.0" y2="250.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M429.0 250.0 L419.0 254.5 L419.0 245.5 z" style="fill:var(--line)"/><line x1="70.0" y1="250.0" x2="70.0" y2="52.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M70.0 41.0 L74.5 51.0 L65.5 51.0 z" style="fill:var(--line)"/><text x="429.0" y="272.0" font-size="16" text-anchor="end" style="fill:var(--muted)">像手机</text><text x="78.0" y="43.0" font-size="16" text-anchor="start" style="fill:var(--muted)">像粮食</text><line x1="220.0" y1="246.0" x2="220.0" y2="254.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="220.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0.5</text><line x1="370.0" y1="246.0" x2="370.0" y2="254.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="370.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><line x1="66.0" y1="100.0" x2="74.0" y2="100.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="105.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.5</text><line x1="70.0" y1="250.0" x2="220.0" y2="250.0" style="stroke:var(--muted);stroke-width:1.5;stroke-dasharray:5 4;fill:none"/><line x1="220.0" y1="250.0" x2="220.0" y2="100.0" style="stroke:var(--muted);stroke-width:1.5;stroke-dasharray:5 4;fill:none"/><text x="145.0" y="240.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">向右 0.5</text><text x="230.0" y="181.0" font-size="16" text-anchor="start" style="fill:var(--muted)">向上 0.5</text><line x1="70.0" y1="250.0" x2="212.2" y2="107.8" style="stroke:var(--accent);stroke-width:3;fill:none"/><path d="M220.0 100.0 L216.1 110.3 L209.7 103.9 z" style="fill:var(--accent)"/><text x="232.0" y="94.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--accent)">小米 (0.5, 0.5)</text>
</svg>
<figcaption>图 1　两个数 (0.5, 0.5) 就是一支箭头：从原点出发，向右走 0.5，再向上走 0.5。箭头的长度是 0.707。</figcaption>
</figure>

箭头有两样东西：**方向**和**长度**。

长度怎么算？图 1 里，往右 0.5、往上 0.5、箭头本身，正好围成一个直角三角形，箭头是斜边。用勾股定理（斜边的平方 = 两条直角边的平方和）：

$$
\begin{aligned}
\lVert x \rVert &= \sqrt{x_1^2 + x_2^2} = \sqrt{0.5^2 + 0.5^2} \\
&= \sqrt{0.25 + 0.25} = \sqrt{0.5} \approx 0.707
\end{aligned}
$$

$\lVert x \rVert$ 是「向量 $x$ 的长度」的写法，两边各两条竖线。

四个 token 画在一起：

<figure class="fig">
<svg viewBox="0 0 480 270" role="img" aria-label="四个 token 的向量画成四支箭头">
<line x1="70.0" y1="240.0" x2="280.0" y2="240.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M291.0 240.0 L281.0 244.5 L281.0 235.5 z" style="fill:var(--line)"/><line x1="70.0" y1="240.0" x2="70.0" y2="30.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M70.0 19.0 L74.5 29.0 L65.5 29.0 z" style="fill:var(--line)"/><text x="291.0" y="262.0" font-size="16" text-anchor="end" style="fill:var(--muted)">像手机</text><text x="78.0" y="21.0" font-size="16" text-anchor="start" style="fill:var(--muted)">像粮食</text><line x1="70.0" y1="240.0" x2="70.0" y2="71.0" style="stroke:var(--accent);stroke-width:2;fill:none"/><path d="M70.0 60.0 L74.5 70.0 L65.5 70.0 z" style="fill:var(--accent)"/><text x="82.0" y="64.0" font-size="16" text-anchor="start" style="fill:var(--accent)">粮油 (0, 1)</text><line x1="70.0" y1="240.0" x2="132.2" y2="208.9" style="stroke:var(--accent);stroke-width:2;fill:none"/><path d="M142.0 204.0 L135.0 212.5 L131.0 204.5 z" style="fill:var(--accent)"/><text x="152.0" y="208.0" font-size="16" text-anchor="start" style="fill:var(--accent)">店 (0.4, 0.2)</text><line x1="70.0" y1="240.0" x2="95.0" y2="240.0" style="stroke:var(--accent);stroke-width:2;fill:none"/><path d="M106.0 240.0 L96.0 244.5 L96.0 235.5 z" style="fill:var(--accent)"/><text x="106.0" y="262.0" font-size="16" text-anchor="middle" style="fill:var(--accent)">买了 (0.2, 0)</text><line x1="70.0" y1="240.0" x2="152.2" y2="157.8" style="stroke:var(--accent);stroke-width:3;fill:none"/><path d="M160.0 150.0 L156.1 160.3 L149.7 153.9 z" style="fill:var(--accent)"/><text x="170.0" y="142.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--accent)">小米 (0.5, 0.5)</text>
</svg>
<figcaption>图 2　四个 token、四支箭头。横坐标当作「像手机」的程度，纵坐标当作「像粮食」的程度（示意，真实模型的向量没有这种标签）。</figcaption>
</figure>

「粮油」笔直朝上（只像粮食），「买了」平躺在横轴上（只有一点像手机），「小米」斜着朝右上（两样各占一半）。

**4096 维也是同一回事。** 我们画不出 4096 个方向互相垂直的坐标轴，但算法完全一样：长度是 4096 个数各自平方、加起来、再开根号。下面每一步都是这样：先在 2 维里算清楚、画清楚，再说一句「多少维都照此算」。

## 第三步：点积：逐项相乘，再加起来

两个向量 $a$、$b$ 的**点积**，写作 $a \cdot b$（中间一个圆点），算法是：第 1 个数和第 1 个数相乘，第 2 个数和第 2 个数相乘，再把乘积加起来。

$$
a \cdot b = a_1 b_1 + a_2 b_2
$$

结果是**一个数**，不是向量。

拿「小米」$(0.5,\ 0.5)$ 和「粮油」$(0,\ 1)$ 算：

$$
\begin{aligned}
\text{小米} \cdot \text{粮油} &= 0.5 \times 0 + 0.5 \times 1 \\
&= 0 + 0.5 = 0.5
\end{aligned}
$$

「小米」和另外三个 token 逐个算：

| 和谁做点积 | 第 1 项 | 第 2 项 | 点积 |
| --- | --- | --- | --- |
| 粮油 $(0,\ 1)$ | $0.5 \times 0 = 0$ | $0.5 \times 1 = 0.5$ | $0.5$ |
| 店 $(0.4,\ 0.2)$ | $0.5 \times 0.4 = 0.2$ | $0.5 \times 0.2 = 0.1$ | $0.3$ |
| 买了 $(0.2,\ 0)$ | $0.5 \times 0.2 = 0.1$ | $0.5 \times 0 = 0$ | $0.1$ |
| 小米自己 $(0.5,\ 0.5)$ | $0.5 \times 0.5 = 0.25$ | $0.5 \times 0.5 = 0.25$ | $0.5$ |

向量有 $n$ 个数时，就是 $n$ 项乘积相加。用求和号 $\sum$ 写成：

$$
a \cdot b = \sum_{i=1}^{n} a_i\, b_i
$$

$\sum_{i=1}^{n}$ 读作「把 $i$ 从 1 到 $n$ 的每一项加起来」。$n = 2$ 时它就是上面那个式子；$n = 4096$ 时是 4096 项乘积相加，算法不变。

两个向量的数一样多，才能做点积。2 维和 3 维的向量没有「对应位置」可乘，不能做点积。

## 第四步：点积的几何意义：方向越一致，点积越大

点积这样算出来的一个数，在图上是什么意思？看「小米」和「粮油」：

<figure class="fig">
<svg viewBox="0 0 480 280" role="img" aria-label="小米向量在粮油方向上的投影是 0.5">
<line x1="120.0" y1="250.0" x2="303.0" y2="250.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M314.0 250.0 L304.0 254.5 L304.0 245.5 z" style="fill:var(--line)"/><line x1="120.0" y1="250.0" x2="120.0" y2="47.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M120.0 36.0 L124.5 46.0 L115.5 46.0 z" style="fill:var(--line)"/><text x="314.0" y="272.0" font-size="16" text-anchor="end" style="fill:var(--muted)">像手机</text><text x="128.0" y="38.0" font-size="16" text-anchor="start" style="fill:var(--muted)">像粮食</text><line x1="120.0" y1="250.0" x2="120.0" y2="61.0" style="stroke:var(--muted);stroke-width:2.5;fill:none"/><path d="M120.0 50.0 L124.5 60.0 L115.5 60.0 z" style="fill:var(--muted)"/><text x="110.0" y="64.0" font-size="16" text-anchor="end" style="fill:var(--muted)">粮油 (0, 1)</text><line x1="220.0" y1="150.0" x2="120.0" y2="150.0" style="stroke:var(--warn);stroke-width:1.5;stroke-dasharray:5 4;fill:none"/><line x1="120.0" y1="250.0" x2="120.0" y2="150.0" style="stroke:var(--warn);stroke-width:6;fill:none"/><text x="110.0" y="206.0" font-size="16" text-anchor="end" style="fill:var(--warn)">投影 0.5</text><line x1="120.0" y1="250.0" x2="212.2" y2="157.8" style="stroke:var(--accent);stroke-width:3;fill:none"/><path d="M220.0 150.0 L216.1 160.3 L209.7 153.9 z" style="fill:var(--accent)"/><text x="230.0" y="156.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--accent)">小米 (0.5, 0.5)</text><path d="M152.5 217.5 A46 46 0 0 0 120.0 204.0" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="146.0" y="192.0" font-size="16" text-anchor="start" style="fill:var(--fg)">45°</text>
</svg>
<figcaption>图 3　从「小米」箭头的尖端向「粮油」那条线做垂线，落在 0.5 处（橙色）。点积 = 粮油的长度 1 × 投影 0.5 = 0.5。两支箭头的夹角是 45°。</figcaption>
</figure>

从「小米」箭头的尖端，向「粮油」那条线画一条垂线，落点离原点 0.5。这一段叫「小米」在「粮油」方向上的**投影**，意思是「小米」有多少是朝着「粮油」的方向走的。而点积正好是：

$$
\begin{aligned}
\text{小米} \cdot \text{粮油} &= \lVert \text{粮油} \rVert \times \text{投影} \\
&= 1 \times 0.5 = 0.5
\end{aligned}
$$

这对任何两个向量都成立（可以用余弦定理证明，这里不展开；实验 01 里随便拖两支箭头都能验证）。投影的长度又可以用夹角 $\theta$ 来算：直角三角形里，斜边是 $\lVert a \rVert$，挨着夹角的那条直角边就是投影，等于 $\lVert a \rVert \cos\theta$。这正是余弦 $\cos$ 的定义：直角三角形里，挨着这个角的直角边 ÷ 斜边。夹角 0° 时 $\cos$ 是 1，90° 时是 0，180° 时是 −1。代进去：

$$
a \cdot b = \lVert a \rVert\, \lVert b \rVert \cos\theta
$$

验算一下：$\lVert \text{小米} \rVert \approx 0.707$，$\lVert \text{粮油} \rVert = 1$，夹角 45°，$\cos 45° \approx 0.707$：

$$
0.707 \times 1 \times 0.707 \approx 0.5
$$

和逐项相乘算出来的 0.5 一样。

这个式子说明，点积大小由三样东西决定：两个长度，和夹角的余弦。长度不变时，只看方向：

<figure class="fig">
<svg viewBox="0 0 480 258" role="img" aria-label="同向、垂直、反向三种情况下的点积">
<line x1="5.0" y1="120.0" x2="155.0" y2="120.0" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="80.0" y1="195.0" x2="80.0" y2="45.0" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="80.0" y1="120.0" x2="121.7" y2="78.3" style="stroke:var(--ok);stroke-width:2.5;fill:none"/><path d="M129.5 70.5 L125.6 80.8 L119.2 74.4 z" style="fill:var(--ok)"/><line x1="80.0" y1="120.0" x2="107.2" y2="92.8" style="stroke:var(--accent);stroke-width:3.5;fill:none"/><path d="M115.0 85.0 L111.1 95.3 L104.7 88.9 z" style="fill:var(--accent)"/><text x="80.0" y="222.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--fg)">同向</text><text x="80.0" y="246.0" font-size="16" text-anchor="middle" style="fill:var(--ok)">点积 0.707</text><line x1="165.0" y1="120.0" x2="315.0" y2="120.0" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="240.0" y1="195.0" x2="240.0" y2="45.0" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="240.0" y1="120.0" x2="198.3" y2="78.3" style="stroke:var(--fg);stroke-width:2.5;fill:none"/><path d="M190.5 70.5 L200.8 74.4 L194.4 80.8 z" style="fill:var(--fg)"/><line x1="240.0" y1="120.0" x2="267.2" y2="92.8" style="stroke:var(--accent);stroke-width:3.5;fill:none"/><path d="M275.0 85.0 L271.1 95.3 L264.7 88.9 z" style="fill:var(--accent)"/><text x="240.0" y="222.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--fg)">垂直</text><text x="240.0" y="246.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">点积 0</text><line x1="325.0" y1="120.0" x2="475.0" y2="120.0" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="400.0" y1="195.0" x2="400.0" y2="45.0" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="400.0" y1="120.0" x2="358.3" y2="161.7" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><path d="M350.5 169.5 L354.4 159.2 L360.8 165.6 z" style="fill:var(--warn)"/><line x1="400.0" y1="120.0" x2="427.2" y2="92.8" style="stroke:var(--accent);stroke-width:3.5;fill:none"/><path d="M435.0 85.0 L431.1 95.3 L424.7 88.9 z" style="fill:var(--accent)"/><text x="400.0" y="222.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--fg)">反向</text><text x="400.0" y="246.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">点积 −0.707</text>
</svg>
<figcaption>图 4　蓝色都是「小米」(0.5, 0.5)，另一支箭头长度都是 1，只改方向。同向时点积最大（0.707），垂直时为 0，反向时为负。</figcaption>
</figure>

- 方向相同（夹角 0°）：$\cos\theta = 1$，点积最大，就是两个长度相乘。
- 互相垂直（夹角 90°）：$\cos\theta = 0$，点积为 0。
- 方向相反（夹角 180°）：$\cos\theta = -1$，点积是负的，而且最小。

所以点积可以当作「两个向量有多一致」的打分：越一致分越高，无关为 0，相反为负。下一讲注意力给每个词打分，用的就是点积。

## 第五步：余弦相似度：只比方向，不比长度

点积有个问题：它同时受长度影响。把「粮油」的向量拉长成 $(0,\ 2)$，方向没变，和「小米」的点积却从 0.5 变成 $0.5 \times 0 + 0.5 \times 2 = 1.0$。

如果只想比方向，就把两个长度除掉，剩下的正是 $\cos\theta$。这叫**余弦相似度**：

$$
\cos\theta = \frac{a \cdot b}{\lVert a \rVert\, \lVert b \rVert}
$$

它一定在 −1 到 1 之间：1 是方向完全相同，0 是垂直，−1 是完全相反。

「小米」和每个 token 的余弦相似度，先算出每个向量的长度：$\lVert \text{店} \rVert = \sqrt{0.4^2 + 0.2^2} = \sqrt{0.2} \approx 0.447$，$\lVert \text{买了} \rVert = \sqrt{0.2^2 + 0^2} = 0.200$，「粮油」长度是 1，「小米」是 0.707。

| 和谁比 | 点积 | 两个长度相乘 | 余弦相似度 | 夹角 |
| --- | --- | --- | --- | --- |
| 粮油 | $0.5$ | $0.707 \times 1 = 0.707$ | $0.5 / 0.707 = 0.707$ | $45°$ |
| 店 | $0.3$ | $0.707 \times 0.447 = 0.316$ | $0.3 / 0.316 = 0.949$ | $18.4°$ |
| 买了 | $0.1$ | $0.707 \times 0.200 = 0.1414$ | $0.1 / 0.1414 = 0.707$ | $45°$ |
| 小米自己 | $0.5$ | $0.707 \times 0.707 = 0.5$ | $0.5 / 0.5 = 1.000$ | $0°$ |

按点积排，「粮油」和「小米自己」并列第一；按余弦相似度排，「店」第二（方向和「小米」只差 18.4°），「粮油」和「买了」并列第三（都差 45°）。「买了」点积小，只是因为它短。

找「意思相近的词」时常用余弦相似度（Agent 篇 RAG 那一讲会用到），因为一个词向量的长短往往和意思无关。

<details class="pause"><summary>停一下：把「小米」换成 (1, 1)，方向不变、长度翻倍。它和「粮油」的点积、余弦相似度各变成多少？</summary>

点积：$1 \times 0 + 1 \times 1 = 1$，翻了一倍。

余弦相似度：$\lVert (1,\ 1) \rVert = \sqrt{2} \approx 1.414$，所以 $\cos\theta = 1 / (1.414 \times 1) = 0.707$，不变。

长度只影响点积，不影响余弦相似度。

</details>

## 第六步：矩阵乘向量：每一行做一次点积

**矩阵**是排成长方形的一张数表。有 $m$ 行、$n$ 列，就说它是 $m \times n$ 的。矩阵一般用大写斜体字母表示。下面这个矩阵我们记作 $W_Q$（名字里的 $Q$ 下一讲再解释，这里只把它当成一个 $2 \times 2$ 的数表）：

$$
W_Q = \begin{pmatrix} 1 & 1 \\ 0 & -1.2 \end{pmatrix}
$$

**矩阵乘向量**的算法：拿矩阵的**每一行**，和向量做一次点积，得到结果的一个数。矩阵有几行，结果就有几个数。

拿 $W_Q$ 乘「小米」的 $x = (0.5,\ 0.5)$。向量在矩阵乘法里习惯竖着写：

$$
W_Q\,x = \begin{pmatrix} 1 & 1 \\ 0 & -1.2 \end{pmatrix} \begin{pmatrix} 0.5 \\ 0.5 \end{pmatrix}
$$

第 1 行是 $(1,\ 1)$，和 $x$ 做点积：

$$
1 \times 0.5 + 1 \times 0.5 = 0.5 + 0.5 = 1.0
$$

第 2 行是 $(0,\ -1.2)$，和 $x$ 做点积：

$$
\begin{aligned}
&0 \times 0.5 + (-1.2) \times 0.5 \\
&= 0 - 0.6 = -0.6
\end{aligned}
$$

两个结果竖着排，就是乘出来的向量：

$$
W_Q\,x = \begin{pmatrix} 1.0 \\ -0.6 \end{pmatrix}
$$

<figure class="fig">
<svg viewBox="0 0 480 236" role="img" aria-label="矩阵的每一行和向量做点积，得到结果的一个数">
<text x="4.0" y="58.0" font-size="16" text-anchor="start" style="fill:var(--muted)">第 1 行</text><rect x="72.0" y="20.0" width="52.0" height="30.0" rx="4" style="fill:var(--warn);fill-opacity:0.18"/><text x="98.0" y="41.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">1</text><rect x="128.0" y="20.0" width="52.0" height="30.0" rx="4" style="fill:var(--warn);fill-opacity:0.18"/><text x="154.0" y="41.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">1</text><text x="98.0" y="75.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0</text><text x="154.0" y="75.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">−1.2</text><path d="M76 18 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M176 18 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="196.0" y="58.0" font-size="18" text-anchor="middle" style="fill:var(--muted)">×</text><rect x="218.0" y="20.0" width="52.0" height="30.0" rx="4" style="fill:var(--accent);fill-opacity:0.18"/><text x="244.0" y="41.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--accent)">0.5</text><rect x="218.0" y="54.0" width="52.0" height="30.0" rx="4" style="fill:var(--accent);fill-opacity:0.18"/><text x="244.0" y="75.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--accent)">0.5</text><path d="M222 18 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M266 18 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="296.0" y="58.0" font-size="18" text-anchor="middle" style="fill:var(--muted)">=</text><rect x="318.0" y="20.0" width="52.0" height="30.0" rx="4" style="fill:var(--warn);fill-opacity:0.18"/><text x="344.0" y="41.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">1.0</text><text x="344.0" y="75.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">−0.6</text><path d="M322 18 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M366 18 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="70.0" y="110.0" font-size="15" text-anchor="start" style="fill:var(--warn)">1 × 0.5 + 1 × 0.5 = 1.0</text><text x="4.0" y="168.0" font-size="16" text-anchor="start" style="fill:var(--muted)">第 2 行</text><text x="98.0" y="151.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">1</text><text x="154.0" y="151.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">1</text><rect x="72.0" y="164.0" width="52.0" height="30.0" rx="4" style="fill:var(--warn);fill-opacity:0.18"/><text x="98.0" y="185.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">0</text><rect x="128.0" y="164.0" width="52.0" height="30.0" rx="4" style="fill:var(--warn);fill-opacity:0.18"/><text x="154.0" y="185.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">−1.2</text><path d="M76 128 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M176 128 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="196.0" y="168.0" font-size="18" text-anchor="middle" style="fill:var(--muted)">×</text><rect x="218.0" y="130.0" width="52.0" height="30.0" rx="4" style="fill:var(--accent);fill-opacity:0.18"/><text x="244.0" y="151.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--accent)">0.5</text><rect x="218.0" y="164.0" width="52.0" height="30.0" rx="4" style="fill:var(--accent);fill-opacity:0.18"/><text x="244.0" y="185.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--accent)">0.5</text><path d="M222 128 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M266 128 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="296.0" y="168.0" font-size="18" text-anchor="middle" style="fill:var(--muted)">=</text><text x="344.0" y="151.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">1.0</text><rect x="318.0" y="164.0" width="52.0" height="30.0" rx="4" style="fill:var(--warn);fill-opacity:0.18"/><text x="344.0" y="185.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">−0.6</text><path d="M322 128 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M366 128 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="70.0" y="220.0" font-size="15" text-anchor="start" style="fill:var(--warn)">0 × 0.5 + (−1.2) × 0.5 = −0.6</text>
</svg>
<figcaption>图 5　上：矩阵第 1 行（橙）和向量（蓝）做点积，得到结果的第 1 个数 1.0。下：第 2 行做同样的事，得到 −0.6。</figcaption>
</figure>

所以矩阵乘向量不是新东西，就是**连续做几次点积**。$m$ 行的矩阵，做 $m$ 次。

几何上看，矩阵把一支箭头变成了另一支箭头：$(0.5,\ 0.5)$ 本来朝右上，乘完变成 $(1.0,\ -0.6)$，朝右下。模型里的矩阵就是这样，把一个向量换成另一种「说法」。矩阵里的数从哪来？训练开始时是随机数，训练过程中一点点调出来（梯度下降那一讲会讲怎么调）。

## 第七步：形状规则：$(m \times n)$ 乘 $(n)$ 得 $(m)$

矩阵不一定是方的。下面这个矩阵有 4 行、2 列，每一行恰好是一个 2 维向量（它们是怎么来的，第八步会算出来）：

$$
K = \begin{pmatrix} 1 & -1 \\ 0.6 & 0.2 \\ 0.2 & 0.2 \\ 1 & 0 \end{pmatrix}
$$

拿它乘刚才算出的 $(1.0,\ -0.6)$。每一行都是 2 个数，向量也是 2 个数，所以每一行都能和它做点积：

| 第几行 | 这一行 | 和 $(1.0,\ -0.6)$ 做点积 | 结果 |
| --- | --- | --- | --- |
| 1 | $(1,\ -1)$ | $1 \times 1.0 + (-1) \times (-0.6) = 1.0 + 0.6$ | $1.6$ |
| 2 | $(0.6,\ 0.2)$ | $0.6 \times 1.0 + 0.2 \times (-0.6) = 0.6 - 0.12$ | $0.48$ |
| 3 | $(0.2,\ 0.2)$ | $0.2 \times 1.0 + 0.2 \times (-0.6) = 0.2 - 0.12$ | $0.08$ |
| 4 | $(1,\ 0)$ | $1 \times 1.0 + 0 \times (-0.6) = 1.0 + 0$ | $1.0$ |

4 行，做 4 次点积，得到 4 个数 $(1.6,\ 0.48,\ 0.08,\ 1.0)$。这 4 个数我们一会儿当作 4 个 token 的分数，用到最后。

<figure class="fig">
<svg viewBox="0 0 480 192" role="img" aria-label="4 行 2 列的矩阵乘 2 个数的向量，得到 4 个数">
<rect x="71.0" y="35.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><rect x="101.0" y="35.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><rect x="71.0" y="65.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><rect x="101.0" y="65.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><rect x="71.0" y="95.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><rect x="101.0" y="95.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><rect x="71.0" y="125.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><rect x="101.0" y="125.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><text x="100.0" y="178.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--accent)">4 × 2</text><text x="155.0" y="100.0" font-size="20" text-anchor="middle" style="fill:var(--muted)">×</text><rect x="181.0" y="65.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><rect x="181.0" y="95.0" width="28.0" height="28.0" rx="3" style="fill:var(--accent);fill-opacity:0.22;stroke:var(--accent);stroke-width:1.5"/><text x="195.0" y="148.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--accent)">2</text><text x="240.0" y="100.0" font-size="20" text-anchor="middle" style="fill:var(--muted)">=</text><rect x="271.0" y="35.0" width="28.0" height="28.0" rx="3" style="fill:var(--warn);fill-opacity:0.22;stroke:var(--warn);stroke-width:1.5"/><rect x="271.0" y="65.0" width="28.0" height="28.0" rx="3" style="fill:var(--warn);fill-opacity:0.22;stroke:var(--warn);stroke-width:1.5"/><rect x="271.0" y="95.0" width="28.0" height="28.0" rx="3" style="fill:var(--warn);fill-opacity:0.22;stroke:var(--warn);stroke-width:1.5"/><rect x="271.0" y="125.0" width="28.0" height="28.0" rx="3" style="fill:var(--warn);fill-opacity:0.22;stroke:var(--warn);stroke-width:1.5"/><text x="285.0" y="178.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">4</text><text x="100.0" y="24.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">每行 2 个数</text><text x="320.0" y="84.0" font-size="15" text-anchor="start" style="fill:var(--muted)">4 行 → 4 个点积</text><text x="320.0" y="108.0" font-size="15" text-anchor="start" style="fill:var(--muted)">→ 4 个数</text>
</svg>
<figcaption>图 6　矩阵有 4 行，每行 2 个数；向量也是 2 个数，所以每一行都能和它做点积。做 4 次，得到 4 个数。中间的「2」必须对上。</figcaption>
</figure>

一般的规则：

$$
\underbrace{W}_{m \times n}\ \underbrace{x}_{n} = \underbrace{y}_{m}
$$

- 矩阵的**列数** $n$ 必须等于向量的长度 $n$，因为每一行要和向量逐项相乘，两边的数必须一样多。
- 结果的长度等于矩阵的**行数** $m$，因为每一行出一个数。

对不上就不能乘。比如 $4 \times 2$ 的矩阵乘一个 3 维向量：每一行只有 2 个数，向量有 3 个数，第 3 个数没有对象可乘。实验 03 是一个形状检查器，输错形状它会告诉你哪一维对不上。

<details class="pause"><summary>停一下：一个 3 × 2 的矩阵乘一个 2 维向量，结果有几个数？反过来，2 × 3 的矩阵能乘 2 维向量吗？</summary>

$3 \times 2$ 乘 2 维：列数 2 等于向量长度 2，可以乘；有 3 行，结果是 3 个数。

$2 \times 3$ 乘 2 维：列数是 3，向量只有 2 个数，对不上，不能乘。

</details>

## 第八步：矩阵乘矩阵：一次乘很多个向量

第七步里那个 $4 \times 2$ 的 $K$，是用另一个矩阵 $W_K$ 分别乘 4 个 token 的向量得来的：

$$
W_K = \begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}
$$

一个一个乘当然可以。但把 4 个向量竖着排成 4 列，拼成一个 $2 \times 4$ 的矩阵，记作 $X$，4 列依次是粮油、店、买了、小米：

$$
X = \begin{pmatrix} 0 & 0.4 & 0.2 & 0.5 \\ 1 & 0.2 & 0 & 0.5 \end{pmatrix}
$$

就能一次写完：

$$
W_K\,X = \begin{pmatrix} 1 & 0.6 & 0.2 & 1 \\ -1 & 0.2 & 0.2 & 0 \end{pmatrix}
$$

**矩阵乘矩阵，就是左边的矩阵对右边的每一列各做一次「矩阵乘向量」**，结果也按列排好。第 1 列「粮油」$(0,\ 1)$：

$$
\begin{pmatrix} 1 \times 0 + 1 \times 1 \\ 1 \times 0 + (-1) \times 1 \end{pmatrix} = \begin{pmatrix} 1 \\ -1 \end{pmatrix}
$$

<figure class="fig">
<svg viewBox="0 0 480 186" role="img" aria-label="一个 2 乘 2 矩阵同时乘 4 个向量">
<text x="26.0" y="63.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">1</text><text x="62.0" y="63.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">1</text><text x="26.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">1</text><text x="62.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">−1</text><path d="M14 40 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M74 40 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="92.0" y="80.0" font-size="18" text-anchor="middle" style="fill:var(--muted)">×</text><rect x="106.0" y="42.0" width="40.0" height="30.0" rx="4" style="fill:var(--accent);fill-opacity:0.18"/><text x="126.0" y="63.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--accent)">0</text><text x="170.0" y="63.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.4</text><text x="214.0" y="63.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.2</text><text x="258.0" y="63.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.5</text><rect x="106.0" y="76.0" width="40.0" height="30.0" rx="4" style="fill:var(--accent);fill-opacity:0.18"/><text x="126.0" y="97.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--accent)">1</text><text x="170.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.2</text><text x="214.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0</text><text x="258.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.5</text><path d="M110 40 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M274 40 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="291.0" y="80.0" font-size="18" text-anchor="middle" style="fill:var(--muted)">=</text><rect x="304.0" y="42.0" width="38.0" height="30.0" rx="4" style="fill:var(--warn);fill-opacity:0.18"/><text x="323.0" y="63.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">1</text><text x="365.0" y="63.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.6</text><text x="407.0" y="63.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.2</text><text x="449.0" y="63.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">1</text><rect x="304.0" y="76.0" width="38.0" height="30.0" rx="4" style="fill:var(--warn);fill-opacity:0.18"/><text x="323.0" y="97.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">−1</text><text x="365.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.2</text><text x="407.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0.2</text><text x="449.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0</text><path d="M308 40 h-6 v68 h6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><path d="M464 40 h6 v68 h-6" style="stroke:var(--fg);stroke-width:1.5;fill:none"/><text x="126.0" y="30.0" font-size="14" text-anchor="middle" style="fill:var(--accent)">粮油</text><text x="170.0" y="30.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">店</text><text x="214.0" y="30.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">买了</text><text x="258.0" y="30.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">小米</text><text x="44.0" y="140.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">2 × 2</text><text x="192.0" y="140.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">2 × 4</text><text x="386.0" y="140.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">2 × 4</text><text x="8.0" y="172.0" font-size="15" text-anchor="start" style="fill:var(--warn)">第 1 列：(1 × 0 + 1 × 1,  1 × 0 + (−1) × 1) = (1, −1)</text>
</svg>
<figcaption>图 7　把 4 个 token 的向量竖着排成 4 列，就是一个 2 × 4 矩阵。左边的矩阵对每一列各做一次「矩阵乘向量」，结果也排成 4 列。高亮的是第 1 列「粮油」。</figcaption>
</figure>

结果矩阵里第 $i$ 行、第 $j$ 列的那个数，就是左边第 $i$ 行和右边第 $j$ 列的点积。例如结果的第 2 行第 2 列（$0.2$）= 左边第 2 行 $(1,\ -1)$ 和右边第 2 列 $(0.4,\ 0.2)$ 的点积 $= 0.4 - 0.2 = 0.2$。

把结果的 4 列横过来、每列变成一行，就是第七步的 $K$。这种「行变成列」的操作叫**转置**，在字母右上角加一个 $\top$ 表示，比如 $K^{\top}$。

形状规则和第七步一样，只是右边多了几列：

$$
\underbrace{A}_{m \times n}\ \underbrace{B}_{n \times p} = \underbrace{C}_{m \times p}
$$

左边的列数和右边的行数（中间的 $n$）必须相同；结果的行数取左边的，列数取右边的。我们的例子是 $(2 \times 2)(2 \times 4) = (2 \times 4)$。

为什么要拼成矩阵一起乘？结果和一个一个乘完全一样，但 GPU 一次能同时算成千上万个乘法，拼在一起才能让它们同时开工（硬件那一讲说过 GPU 擅长的正是这种大批量的乘加）。

## 第九步：线性层：$y = Wx + b$

神经网络里最常见的一层叫**线性层**，就是「矩阵乘向量，再加一个向量」：

$$
y = W x + b
$$

- $x$：输入向量，$n$ 个数。
- $W$：权重矩阵，$m \times n$。
- $b$：**偏置**（bias），一个 $m$ 维向量，乘完之后整体挪一下。
- $y$：输出向量，$m$ 个数。

用 $W_Q$ 当 $W$，再取 $b = (0.2,\ 0.4)$。$W_Q\,x$ 第六步已经算过，是 $(1.0,\ -0.6)$，再逐项加上 $b$：

$$
\begin{aligned}
y &= \begin{pmatrix} 1.0 \\ -0.6 \end{pmatrix} + \begin{pmatrix} 0.2 \\ 0.4 \end{pmatrix} \\
&= \begin{pmatrix} 1.0 + 0.2 \\ -0.6 + 0.4 \end{pmatrix} = \begin{pmatrix} 1.2 \\ -0.2 \end{pmatrix}
\end{aligned}
$$

<figure class="fig">
<svg viewBox="0 0 480 300" role="img" aria-label="线性层先乘矩阵再加偏置">
<line x1="65.0" y1="160.0" x2="330.5" y2="160.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M341.5 160.0 L331.5 164.5 L331.5 155.5 z" style="fill:var(--line)"/><line x1="110.0" y1="272.5" x2="110.0" y2="44.5" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M110.0 33.5 L114.5 43.5 L105.5 43.5 z" style="fill:var(--line)"/><line x1="185.0" y1="156.0" x2="185.0" y2="164.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="185.0" y="151.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0.5</text><line x1="260.0" y1="156.0" x2="260.0" y2="164.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="260.0" y="151.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><line x1="106.0" y1="85.0" x2="114.0" y2="85.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="102.0" y="90.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.5</text><line x1="106.0" y1="235.0" x2="114.0" y2="235.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="102.0" y="240.0" font-size="14" text-anchor="end" style="fill:var(--muted)">−0.5</text><line x1="110.0" y1="160.0" x2="177.2" y2="92.8" style="stroke:var(--accent);stroke-width:3;fill:none"/><path d="M185.0 85.0 L181.1 95.3 L174.7 88.9 z" style="fill:var(--accent)"/><text x="195.0" y="81.0" font-size="16" text-anchor="start" style="fill:var(--accent)"><tspan font-style="italic">x</tspan> (0.5, 0.5)</text><line x1="110.0" y1="160.0" x2="250.6" y2="244.3" style="stroke:var(--warn);stroke-width:2;stroke-dasharray:6 5;fill:none"/><path d="M260.0 250.0 L249.1 248.7 L253.7 241.0 z" style="fill:var(--warn)"/><text x="254.0" y="272.0" font-size="16" text-anchor="end" style="fill:var(--warn)"><tspan font-style="italic">W</tspan><tspan font-style="italic">x</tspan> (1.0, −0.6)</text><line x1="260.0" y1="250.0" x2="285.1" y2="199.8" style="stroke:var(--muted);stroke-width:2;fill:none"/><path d="M290.0 190.0 L289.5 201.0 L281.5 197.0 z" style="fill:var(--muted)"/><text x="285.0" y="238.0" font-size="16" text-anchor="start" style="fill:var(--muted)">+<tspan font-style="italic">b</tspan></text><line x1="110.0" y1="160.0" x2="279.1" y2="188.2" style="stroke:var(--warn);stroke-width:3;fill:none"/><path d="M290.0 190.0 L279.4 192.8 L280.8 183.9 z" style="fill:var(--warn)"/><text x="300.0" y="194.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--warn)"><tspan font-style="italic">y</tspan> (1.2, −0.2)</text>
</svg>
<figcaption>图 8　蓝色是输入 x。先乘矩阵得到虚线的 Wx = (1.0, −0.6)，再整体挪一下 b = (0.2, 0.4)，得到橙色的 y = (1.2, −0.2)。</figcaption>
</figure>

**参数量**：训练要调的数，是 $W$ 里的 $m \times n$ 个，加上 $b$ 里的 $m$ 个：

$$
\text{参数量} = m \times n + m
$$

我们的小例子：$2 \times 2 + 2 = 6$ 个。

真实模型里的两个例子，形状都来自公开配置：

- GPT-2 每一层的 FFN，第一个线性层把 768 维升到 3072 维，带偏置：$768 \times 3072 + 3072 = 2{,}362{,}368$ 个参数。
- Llama-3-8B 最后的输出投影（上一讲第 3 站），把 4096 维的向量变成词表里 128,256 个 token 各自的分数，不带偏置：$128{,}256 \times 4096 = 525{,}336{,}576$ 个参数，约 5.3 亿。形状是 $(128{,}256 \times 4096)$ 乘 $(4096)$，得到 $(128{,}256)$：词表里每个 token 一个分数。

不少新模型的线性层不带 $b$（Llama 系列就不带），那就是 $y = Wx$。下一讲注意力里的 $W_Q$、$W_K$、$W_V$ 都是这样的线性层。

## 第十步：分数要变成概率

上一讲最后一站：模型给词表里每个 token 一个分数（logit），然后要从中**抽**一个出来。抽之前得先把分数变成**概率**：每个都不是负数，全部加起来等于 1（100%）。

就用第七步算出的 4 个分数，当作 4 个候选 token 的分数：

| token | 粮油 | 店 | 买了 | 小米 |
| --- | --- | --- | --- | --- |
| 分数 $s$ | 1.6 | 0.48 | 0.08 | 1.0 |

最直接的想法：每个分数除以总和。总和是 $1.6 + 0.48 + 0.08 + 1.0 = 3.16$，粮油分到 $1.6 / 3.16 = 50.6\%$，店 $15.2\%$，买了 $2.5\%$，小米 $31.6\%$。看起来能用。

但分数可以是负的。把 4 个分数都减去 1，变成 $(0.6,\ -0.52,\ -0.92,\ 0)$：排名没变，彼此的差距也没变，只是整体往下挪了 1。总和变成 $-0.84$，再除一次：粮油得到 $0.6 / (-0.84) = -71.4\%$，店得到 $-0.52 / (-0.84) = 61.9\%$。概率成了负数，分数最高的反而最小，完全不能用。

所以需要一个办法：先把每个分数变成**正数**，而且分数越大、变出来的数越大，再除以总和。这个办法就是取指数。

## 第十一步：指数函数：把任何数变成正数

**指数函数**写作 $e^{s}$：一个固定的数 $e \approx 2.718$，自乘 $s$ 次。$e^{1} = 2.718$，$e^{2} = 2.718 \times 2.718 \approx 7.389$；$e^{0} = 1$；负数次方是倒数，$e^{-1} = 1 / 2.718 \approx 0.368$。$s$ 可以是小数，计算器上有 $e^{x}$ 键。

<figure class="fig">
<svg viewBox="0 0 480 290" role="img" aria-label="指数函数曲线上标出四个分数">
<line x1="40.0" y1="262.0" x2="445.0" y2="262.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M456.0 262.0 L446.0 266.5 L446.0 257.5 z" style="fill:var(--line)"/><line x1="211.4" y1="268.0" x2="211.4" y2="29.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M211.4 18.0 L215.9 28.0 L206.9 28.0 z" style="fill:var(--line)"/><text x="454" y="284" font-size="16" text-anchor="end" font-style="italic" style="fill:var(--muted)">s</text><text x="219.42857142857142" y="28" font-size="16" style="fill:var(--muted)"><tspan font-style="italic">e</tspan><tspan font-size="11" dy="-7" font-style="italic">s</tspan></text><line x1="97.1" y1="258.0" x2="97.1" y2="266.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="97.1" y="282.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">−1</text><line x1="325.7" y1="258.0" x2="325.7" y2="266.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="325.7" y="282.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><line x1="440.0" y1="258.0" x2="440.0" y2="266.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="440.0" y="282.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2</text><line x1="207.4" y1="220.2" x2="215.4" y2="220.2" style="stroke:var(--line);stroke-width:1.5;fill:none"/><polyline points="40.0,252.7 43.3,252.4 46.7,252.1 50.0,251.8 53.3,251.5 56.7,251.2 60.0,250.9 63.3,250.6 66.7,250.2 70.0,249.9 73.3,249.5 76.7,249.1 80.0,248.8 83.3,248.4 86.7,248.0 90.0,247.5 93.3,247.1 96.7,246.7 100.0,246.2 103.3,245.8 106.7,245.3 110.0,244.8 113.3,244.3 116.7,243.8 120.0,243.2 123.3,242.7 126.7,242.1 130.0,241.5 133.3,240.9 136.7,240.3 140.0,239.6 143.3,239.0 146.7,238.3 150.0,237.6 153.3,236.8 156.7,236.1 160.0,235.3 163.3,234.5 166.7,233.7 170.0,232.9 173.3,232.0 176.7,231.1 180.0,230.2 183.3,229.3 186.7,228.3 190.0,227.3 193.3,226.3 196.7,225.2 200.0,224.2 203.3,223.0 206.7,221.9 210.0,220.7 213.3,219.5 216.7,218.2 220.0,216.9 223.3,215.6 226.7,214.2 230.0,212.8 233.3,211.3 236.7,209.8 240.0,208.3 243.3,206.7 246.7,205.1 250.0,203.4 253.3,201.7 256.7,199.9 260.0,198.0 263.3,196.1 266.7,194.2 270.0,192.2 273.3,190.1 276.7,188.0 280.0,185.8 283.3,183.5 286.7,181.2 290.0,178.8 293.3,176.4 296.7,173.8 300.0,171.2 303.3,168.5 306.7,165.8 310.0,162.9 313.3,160.0 316.7,157.0 320.0,153.9 323.3,150.7 326.7,147.4 330.0,144.0 333.3,140.5 336.7,136.9 340.0,133.2 343.3,129.4 346.7,125.5 350.0,121.4 353.3,117.3 356.7,113.0 360.0,108.6 363.3,104.0 366.7,99.3 370.0,94.5 373.3,89.6 376.7,84.5 380.0,79.2 383.3,73.8 386.7,68.2 390.0,62.5 393.3,56.6 396.7,50.5 400.0,44.3 403.3,37.8" style="stroke:var(--fg);stroke-width:2.5;fill:none"/><circle cx="394.3" cy="54.9" r="5" style="fill:var(--warn)"/><text x="382.3" y="58.9" font-size="15" text-anchor="end" style="fill:var(--warn)">粮油 4.953</text><circle cx="266.3" cy="194.4" r="5" style="fill:var(--accent)"/><text x="276.3" y="218.4" font-size="15" text-anchor="start" style="fill:var(--accent)">店 1.616</text><circle cx="220.6" cy="216.7" r="5" style="fill:var(--accent)"/><text x="204.6" y="206.7" font-size="15" text-anchor="end" style="fill:var(--accent)">买了 1.083</text><circle cx="325.7" cy="148.3" r="5" style="fill:var(--accent)"/><text x="313.7" y="140.3" font-size="15" text-anchor="end" style="fill:var(--accent)">小米 2.718</text>
</svg>
<figcaption>图 9　黑线是指数函数 eˢ：永远在横轴上方，越往右涨得越快。四个点是四个分数取指数之后的值，最右边橙色的是「粮油」。</figcaption>
</figure>

从图上能看出它的两个性质，正好是我们要的：

1. **永远是正数。** 曲线始终在横轴上方。$s$ 再负，$e^{s}$ 也只是很接近 0，不会变成 0 或负数。
2. **越往右涨得越快，而且只看差距。** 两个分数差 $d$，取指数之后是 $e^{d}$ 倍，不管它们本身多大：

$$
\frac{e^{a}}{e^{b}} = e^{a-b}
$$

「粮油」1.6 和「小米」1.0 差 0.6，取指数之后 $4.953 / 2.718 = e^{0.6} \approx 1.82$ 倍。差距 0.6 变成了 1.82 倍；差距越大，倍数涨得越快。

4 个分数逐个取指数：

| token | 分数 $s$ | $e^{s}$ |
| --- | --- | --- |
| 粮油 | 1.6 | 4.953 |
| 店 | 0.48 | 1.616 |
| 买了 | 0.08 | 1.083 |
| 小米 | 1.0 | 2.718 |

## 第十二步：softmax：取指数，再除以总和

现在 4 个数都是正的了，除以总和就是概率。总和：

$$
\begin{aligned}
&4.953 + 1.616 + 1.083 + 2.718 \\
&= 10.370
\end{aligned}
$$

每个除以总和：

$$
\begin{aligned}
p_{\text{粮油}} &= \frac{4.953}{10.370} = 0.478 \\[4pt]
p_{\text{店}} &= \frac{1.616}{10.370} = 0.156 \\[4pt]
p_{\text{买了}} &= \frac{1.083}{10.370} = 0.104 \\[4pt]
p_{\text{小米}} &= \frac{2.718}{10.370} = 0.262
\end{aligned}
$$

即 $47.8\%$、$15.6\%$、$10.4\%$、$26.2\%$，加起来是 100%。为什么一定是 100%？因为 4 个分子加起来正好是分母，$\frac{a}{a+b+c+d} + \cdots + \frac{d}{a+b+c+d} = \frac{a+b+c+d}{a+b+c+d} = 1$。

这两步合起来叫 **softmax**。写成公式，第 $i$ 个的概率是：

$$
p_i = \frac{e^{s_i}}{\sum_{j} e^{s_j}}
$$

分子是自己的 $e^{s}$，分母 $\sum_j e^{s_j}$ 是所有 $e^{s}$ 的总和。

<figure class="fig">
<svg viewBox="0 0 480 210" role="img" aria-label="分数、取指数之后、除以总和之后">
<text x="70.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">分数 <tspan font-style="italic">s</tspan></text><text x="60.0" y="61.0" font-size="16" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="70.0" y="44.0" width="80.0" height="24.0" rx="4" style="fill:var(--warn)"/><text x="156.0" y="62.0" font-size="15" text-anchor="start" style="fill:var(--warn)">1.6</text><text x="60.0" y="101.0" font-size="16" text-anchor="end" style="fill:var(--fg)">店</text><rect x="70.0" y="84.0" width="24.0" height="24.0" rx="4" style="fill:var(--line)"/><text x="100.0" y="102.0" font-size="15" text-anchor="start" style="fill:var(--muted)">0.48</text><text x="60.0" y="141.0" font-size="16" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="70.0" y="124.0" width="4.0" height="24.0" rx="4" style="fill:var(--line)"/><text x="80.0" y="142.0" font-size="15" text-anchor="start" style="fill:var(--muted)">0.08</text><text x="60.0" y="181.0" font-size="16" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="70.0" y="164.0" width="50.0" height="24.0" rx="4" style="fill:var(--line)"/><text x="126.0" y="182.0" font-size="15" text-anchor="start" style="fill:var(--muted)">1.0</text><text x="210.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">eˢ</text><rect x="210.0" y="44.0" width="80.0" height="24.0" rx="4" style="fill:var(--warn)"/><text x="296.0" y="62.0" font-size="15" text-anchor="start" style="fill:var(--warn)">4.953</text><rect x="210.0" y="84.0" width="26.1" height="24.0" rx="4" style="fill:var(--line)"/><text x="242.1" y="102.0" font-size="15" text-anchor="start" style="fill:var(--muted)">1.616</text><rect x="210.0" y="124.0" width="17.5" height="24.0" rx="4" style="fill:var(--line)"/><text x="233.5" y="142.0" font-size="15" text-anchor="start" style="fill:var(--muted)">1.083</text><rect x="210.0" y="164.0" width="43.9" height="24.0" rx="4" style="fill:var(--line)"/><text x="259.9" y="182.0" font-size="15" text-anchor="start" style="fill:var(--muted)">2.718</text><text x="340.0" y="24.0" font-size="16" text-anchor="start" style="fill:var(--muted)">份额</text><rect x="340.0" y="44.0" width="80.0" height="24.0" rx="4" style="fill:var(--warn)"/><text x="426.0" y="62.0" font-size="15" text-anchor="start" style="fill:var(--warn)">47.8%</text><rect x="340.0" y="84.0" width="26.1" height="24.0" rx="4" style="fill:var(--line)"/><text x="372.1" y="102.0" font-size="15" text-anchor="start" style="fill:var(--muted)">15.6%</text><rect x="340.0" y="124.0" width="17.5" height="24.0" rx="4" style="fill:var(--line)"/><text x="363.5" y="142.0" font-size="15" text-anchor="start" style="fill:var(--muted)">10.4%</text><rect x="340.0" y="164.0" width="43.9" height="24.0" rx="4" style="fill:var(--line)"/><text x="389.9" y="182.0" font-size="15" text-anchor="start" style="fill:var(--muted)">26.2%</text>
</svg>
<figcaption>图 10　从左到右：分数 → 取指数（都变成正数，差距拉大）→ 除以总和（加起来是 100%）。排名始终不变。</figcaption>
</figure>

再看刚才「都减去 1」那组分数。取指数之后，每个 $e^{s-1} = e^{s} \times e^{-1}$，分子分母都乘了同一个 $e^{-1}$，约掉之后概率和原来**一模一样**。这正是我们想要的：整体挪动分数不应该改变结果，softmax 只看分数之间的差。

名字的意思：它是一个「软」的取最大值（max）。只取最大值会把 100% 给第一名、其他全是 0；softmax 让第一名拿得最多，其他也按差距分到一些。

<details class="pause"><summary>停一下：4 个分数都一样（比如都是 0.7），softmax 之后各是多少？</summary>

每个 $e^{0.7}$ 都相同，记作 $a$。每个概率都是 $a / (a + a + a + a) = 1/4 = 25\%$。分数没有差距，概率就平分。分数的具体大小（0.7 还是 100）无关紧要。

</details>

## 第十三步：温度：先除以 $T$，再 softmax

上一讲实验 06 有一个「温度」滑块。它做的事情只有一步：把每个分数先除以温度 $T$，再做 softmax：

$$
p_i = \frac{e^{s_i / T}}{\sum_{j} e^{s_j / T}}
$$

**$T = 0.5$**：分数除以 0.5 等于乘 2，变成 $(3.2,\ 0.96,\ 0.16,\ 2.0)$。取指数得 $(24.533,\ 2.612,\ 1.174,\ 7.389)$，总和 35.707，概率是 $68.7\%$、$7.3\%$、$3.3\%$、$20.7\%$。

**$T = 2$**：分数减半，变成 $(0.8,\ 0.24,\ 0.04,\ 0.5)$，概率是 $36.0\%$、$20.5\%$、$16.8\%$、$26.7\%$。

为什么会这样？还是「只看差距」：「粮油」和「小米」原来差 0.6。$T = 0.5$ 时差距变成 $0.6 / 0.5 = 1.2$，倍数是 $e^{1.2} \approx 3.32$；$T = 2$ 时差距变成 $0.6 / 2 = 0.3$，倍数只有 $e^{0.3} \approx 1.35$。

<figure class="fig">
<svg viewBox="0 0 480 244" role="img" aria-label="同一组分数在四种温度下的份额">
<text x="62" y="24" font-size="16" text-anchor="middle" style="fill:var(--fg)"><tspan font-style="italic">T</tspan> = 0.5</text><rect x="16.0" y="59.5" width="18.0" height="130.5" rx="3" style="fill:var(--warn)"/><text x="25.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">粮</text><rect x="40.0" y="176.1" width="18.0" height="13.9" rx="3" style="fill:var(--line)"/><text x="49.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">店</text><rect x="64.0" y="183.8" width="18.0" height="6.2" rx="3" style="fill:var(--line)"/><text x="73.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">买</text><rect x="88.0" y="150.7" width="18.0" height="39.3" rx="3" style="fill:var(--line)"/><text x="97.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">小</text><text x="62.0" y="232.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">粮油 68.7%</text><text x="180" y="24" font-size="16" text-anchor="middle" style="fill:var(--fg)"><tspan font-style="italic">T</tspan> = 1</text><rect x="134.0" y="99.3" width="18.0" height="90.7" rx="3" style="fill:var(--warn)"/><text x="143.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">粮</text><rect x="158.0" y="160.4" width="18.0" height="29.6" rx="3" style="fill:var(--line)"/><text x="167.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">店</text><rect x="182.0" y="170.2" width="18.0" height="19.8" rx="3" style="fill:var(--line)"/><text x="191.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">买</text><rect x="206.0" y="140.2" width="18.0" height="49.8" rx="3" style="fill:var(--line)"/><text x="215.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">小</text><text x="180.0" y="232.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">粮油 47.8%</text><text x="298" y="24" font-size="16" text-anchor="middle" style="fill:var(--fg)"><tspan font-style="italic">T</tspan> = √2 ≈ 1.41</text><rect x="252.0" y="112.4" width="18.0" height="77.6" rx="3" style="fill:var(--warn)"/><text x="261.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">粮</text><rect x="276.0" y="154.9" width="18.0" height="35.1" rx="3" style="fill:var(--line)"/><text x="285.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">店</text><rect x="300.0" y="163.5" width="18.0" height="26.5" rx="3" style="fill:var(--line)"/><text x="309.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">买</text><rect x="324.0" y="139.2" width="18.0" height="50.8" rx="3" style="fill:var(--line)"/><text x="333.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">小</text><text x="298.0" y="232.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">粮油 40.8%</text><text x="416" y="24" font-size="16" text-anchor="middle" style="fill:var(--fg)"><tspan font-style="italic">T</tspan> = 2</text><rect x="370.0" y="121.6" width="18.0" height="68.4" rx="3" style="fill:var(--warn)"/><text x="379.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">粮</text><rect x="394.0" y="151.0" width="18.0" height="39.0" rx="3" style="fill:var(--line)"/><text x="403.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">店</text><rect x="418.0" y="158.0" width="18.0" height="32.0" rx="3" style="fill:var(--line)"/><text x="427.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">买</text><rect x="442.0" y="139.4" width="18.0" height="50.6" rx="3" style="fill:var(--line)"/><text x="451.0" y="208.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">小</text><text x="416.0" y="232.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">粮油 36.0%</text>
</svg>
<figcaption>图 11　同一组分数，除以不同的温度 T 再做 softmax。T 越小，第一名（橙）越高、分布越尖；T 越大，四根柱子越接近。柱下的字是「粮、店、买、小」。</figcaption>
</figure>

- $T < 1$：差距放大，分布变尖，第一名越来越多。$T$ 趋近 0 时，第一名接近 100%，每次都抽到同一个。
- $T = 1$：就是原来的 softmax。
- $T > 1$：差距缩小，分布变平，排在后面的也常被抽到，生成的文字更随机。

图里还有一个 $T = \sqrt{2} \approx 1.41$：「粮油」从 47.8% 降到 $40.8\%$。记住这一组数，下一讲注意力里会再遇到它。

<details class="pause"><summary>停一下：温度会改变 4 个候选的排名吗？</summary>

不会。所有分数除以同一个正数 $T$，大的还是大的，取指数之后顺序也不变。温度只改变第一名和后面差多少，不改变谁是第一名。所以温度调到接近 0，抽到的总是原来分数最高的那个。

</details>

## 第十四步：算 softmax 时先减去最大值

上面说过，所有分数同时减去一个数，softmax 的结果不变。实际写程序时，总是**先减去最大值**再取指数。

用我们的分数试一下。最大值是 1.6，都减去 1.6，变成 $(0,\ -1.12,\ -1.52,\ -0.6)$。取指数得 $(1.000,\ 0.326,\ 0.219,\ 0.549)$，总和 2.094。粮油的概率 $1 / 2.094 = 47.8\%$，和原来一样，其他三个也一样。

结果一样，为什么要多此一举？因为计算机能存的数有上限。大模型常用的 32 位浮点数（float32）最大约 $3.4 \times 10^{38}$，$e^{s}$ 超过它就存不下，变成「无穷大」。算一下这个上限对应多大的 $s$：$e^{s} = 3.4 \times 10^{38}$ 时 $s = \ln(3.4 \times 10^{38}) \approx 88.72$（$\ln y$ 是自然对数，意思是「$e$ 的多少次方等于 $y$」，最后一步细讲）。也就是说，分数超过 88.72，$e^{s}$ 就溢出了。16 位浮点数（float16）最大只有 65,504，$s$ 超过 $\ln 65504 \approx 11.09$ 就溢出。

分数真会这么大吗？会。下一讲会看到，Qwen3-0.6B 里一个注意力头的原始分数在 240 到 285 之间。把我们的分数乘 100 模拟一下：$(160,\ 48,\ 8,\ 100)$。$e^{160} \approx 3.1 \times 10^{69}$，float32 存不下，变成无穷大；分子分母都是无穷大，无穷大除以无穷大没有意义，程序得到 NaN（「不是一个数」），后面的计算全部报废。

先减去最大值 160，分数变成 $(0,\ -112,\ -152,\ -60)$：最大的一个取指数正好是 $e^{0} = 1$，其他都小于 1，绝不会溢出。结果是粮油接近 100%，这才是这组分数真正的 softmax。实验 05 可以切换 float32 和 float16，看减与不减的区别。

## 第十五步：对数：把乘法变成加法

**对数**是指数的反操作。$e^{s} = y$，那么 $s = \ln y$，读作「$y$ 的自然对数」，意思是「$e$ 的多少次方等于 $y$」。例如 $e^{0} = 1$，所以 $\ln 1 = 0$；$e^{1} = 2.718$，所以 $\ln 2.718 = 1$。

「粮油」的概率是 0.478，它的对数：

$$
\ln 0.478 \approx -0.738
$$

意思是 $e^{-0.738} \approx 0.478$。0 到 1 之间的数，对数都是负的：

<figure class="fig">
<svg viewBox="0 0 480 290" role="img" aria-label="对数函数 ln p 在 0 到 1 之间的曲线">
<line x1="60.0" y1="30.0" x2="455.0" y2="30.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M466.0 30.0 L456.0 34.5 L456.0 25.5 z" style="fill:var(--line)"/><line x1="60.0" y1="24.0" x2="60.0" y2="263.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><path d="M60.0 274.0 L55.5 264.0 L64.5 264.0 z" style="fill:var(--line)"/><text x="464" y="22" font-size="16" text-anchor="end" font-style="italic" style="fill:var(--muted)">p</text><text x="70" y="270" font-size="16" style="fill:var(--muted)">ln <tspan font-style="italic">p</tspan></text><line x1="255.0" y1="26.0" x2="255.0" y2="34.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="255.0" y="20.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0.5</text><line x1="450.0" y1="26.0" x2="450.0" y2="34.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="450.0" y="20.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><line x1="56.0" y1="84.8" x2="64.0" y2="84.8" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="52.0" y="89.8" font-size="14" text-anchor="end" style="fill:var(--muted)">−1</text><line x1="56.0" y1="139.5" x2="64.0" y2="139.5" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="52.0" y="144.5" font-size="14" text-anchor="end" style="fill:var(--muted)">−2</text><line x1="56.0" y1="194.3" x2="64.0" y2="194.3" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="52.0" y="199.3" font-size="14" text-anchor="end" style="fill:var(--muted)">−3</text><line x1="56.0" y1="249.0" x2="64.0" y2="249.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="52.0" y="254.0" font-size="14" text-anchor="end" style="fill:var(--muted)">−4</text><polyline points="67.8,244.2 69.7,232.2 71.6,222.4 73.5,214.1 75.4,206.8 77.4,200.4 79.3,194.7 81.2,189.5 83.1,184.8 85.0,180.4 86.9,176.4 88.8,172.7 90.7,169.1 92.6,165.8 94.6,162.7 96.5,159.8 98.4,157.0 100.3,154.3 102.2,151.8 104.1,149.4 106.0,147.0 107.9,144.8 109.8,142.7 111.8,140.6 113.7,138.6 115.6,136.7 117.5,134.8 119.4,133.1 121.3,131.3 123.2,129.6 125.1,128.0 127.0,126.4 129.0,124.9 130.9,123.4 132.8,121.9 134.7,120.5 136.6,119.1 138.5,117.8 140.4,116.5 142.3,115.2 144.2,113.9 146.2,112.7 148.1,111.5 150.0,110.3 151.9,109.2 153.8,108.0 155.7,106.9 157.6,105.9 159.5,104.8 161.4,103.7 163.4,102.7 165.3,101.7 167.2,100.7 169.1,99.8 171.0,98.8 172.9,97.9 174.8,97.0 176.7,96.1 178.6,95.2 180.5,94.3 182.5,93.4 184.4,92.6 186.3,91.8 188.2,90.9 190.1,90.1 192.0,89.3 193.9,88.5 195.8,87.8 197.7,87.0 199.7,86.2 201.6,85.5 203.5,84.8 205.4,84.0 207.3,83.3 209.2,82.6 211.1,81.9 213.0,81.2 214.9,80.5 216.9,79.9 218.8,79.2 220.7,78.6 222.6,77.9 224.5,77.3 226.4,76.6 228.3,76.0 230.2,75.4 232.1,74.8 234.1,74.2 236.0,73.6 237.9,73.0 239.8,72.4 241.7,71.8 243.6,71.3 245.5,70.7 247.4,70.1 249.3,69.6 251.3,69.0 253.2,68.5 255.1,67.9 257.0,67.4 258.9,66.9 260.8,66.3 262.7,65.8 264.6,65.3 266.5,64.8 268.5,64.3 270.4,63.8 272.3,63.3 274.2,62.8 276.1,62.3 278.0,61.8 279.9,61.4 281.8,60.9 283.7,60.4 285.7,60.0 287.6,59.5 289.5,59.0 291.4,58.6 293.3,58.1 295.2,57.7 297.1,57.2 299.0,56.8 300.9,56.4 302.9,55.9 304.8,55.5 306.7,55.1 308.6,54.7 310.5,54.2 312.4,53.8 314.3,53.4 316.2,53.0 318.1,52.6 320.1,52.2 322.0,51.8 323.9,51.4 325.8,51.0 327.7,50.6 329.6,50.2 331.5,49.8 333.4,49.4 335.3,49.1 337.3,48.7 339.2,48.3 341.1,47.9 343.0,47.6 344.9,47.2 346.8,46.8 348.7,46.5 350.6,46.1 352.5,45.7 354.4,45.4 356.4,45.0 358.3,44.7 360.2,44.3 362.1,44.0 364.0,43.6 365.9,43.3 367.8,43.0 369.7,42.6 371.6,42.3 373.6,41.9 375.5,41.6 377.4,41.3 379.3,41.0 381.2,40.6 383.1,40.3 385.0,40.0 386.9,39.7 388.8,39.3 390.8,39.0 392.7,38.7 394.6,38.4 396.5,38.1 398.4,37.8 400.3,37.5 402.2,37.2 404.1,36.9 406.0,36.5 408.0,36.2 409.9,35.9 411.8,35.6 413.7,35.4 415.6,35.1 417.5,34.8 419.4,34.5 421.3,34.2 423.2,33.9 425.2,33.6 427.1,33.3 429.0,33.0 430.9,32.8 432.8,32.5 434.7,32.2 436.6,31.9 438.5,31.6 440.4,31.4 442.4,31.1 444.3,30.8 446.2,30.5 448.1,30.3 450.0,30.0" style="stroke:var(--fg);stroke-width:2.5;fill:none"/><circle cx="246.4" cy="70.4" r="5" style="fill:var(--warn)"/><text x="256.4" y="90.4" font-size="15" text-anchor="start" style="fill:var(--warn)"><tspan font-style="italic">p</tspan> = 0.478，ln <tspan font-style="italic">p</tspan> = −0.738</text><circle cx="79.5" cy="194.1" r="5" style="fill:var(--accent)"/><text x="89.5" y="200.1" font-size="15" text-anchor="start" style="fill:var(--accent)"><tspan font-style="italic">p</tspan> = 0.05，ln <tspan font-style="italic">p</tspan> = −2.996</text>
</svg>
<figcaption>图 12　概率 p 在 0 到 1 之间时，ln p 都是负数：p = 1 时正好是 0，p 越小越往下掉。橙色点是「粮油」的份额 0.478。</figcaption>
</figure>

对数最重要的性质：**乘积的对数，等于对数的和**。

$$
\ln(a \times b) = \ln a + \ln b
$$

为什么？设 $a = e^{u}$、$b = e^{v}$，那么 $a \times b = e^{u} \times e^{v} = e^{u+v}$（$e$ 自乘 $u$ 次再自乘 $v$ 次，一共 $u + v$ 次）。两边取对数，$\ln(a \times b) = u + v = \ln a + \ln b$。

这在大模型里很有用。模型一句话生成 100 个 token，整句话的概率是 100 个概率**相乘**。假设每个都是 0.478：

$$
0.478^{100} \approx 8.8 \times 10^{-33}
$$

小到 float32 也快存不下了：float32 能表示的最小正数约 $1.4 \times 10^{-45}$，在 float32 里一路乘 0.478，乘到第 141 次就变成 0，信息全丢。取对数就变成 100 个对数**相加**：

$$
\ln\left(0.478^{100}\right) = 100 \times \ln 0.478 \approx -73.8
$$

$-73.8$ 是个普普通通的数，存起来毫无压力。所以程序里通常不存概率本身，而存概率的对数。

对数和 softmax 还能合在一起算。对 softmax 的公式取对数，除法变成减法：

$$
\ln p_i = s_i - \ln \sum_{j} e^{s_j}
$$

代入「粮油」：$\ln \sum_j e^{s_j} = \ln 10.370 \approx 2.339$，所以 $\ln p_{\text{粮油}} = 1.6 - 2.339 = -0.739$，和直接算 $\ln 0.478$ 一样（差在最后一位是四舍五入）。

**为后面铺一句路**：训练时，模型要让「正确答案」的概率尽量大。常用的做法是把 $-\ln p$（正确 token 概率的对数，取负号）当作要减小的「损失」。正确答案的概率是 0.478 时，损失是 0.738；提高到 0.9，损失降到 0.105；只有 0.01，损失是 4.61。这叫**交叉熵**，后训练那一讲会细讲。

## 合起来：一张对照表

| 这一讲的东西 | 写法 | 在大模型里出现在哪 |
| --- | --- | --- |
| 向量 | $x = (x_1,\ \dots,\ x_n)$ | 每个 token 的 embedding、每层的输入输出 |
| 点积 | $a \cdot b = \sum_i a_i b_i$ | 注意力给每个词打分 |
| 余弦相似度 | $\dfrac{a \cdot b}{\lVert a \rVert\, \lVert b \rVert}$ | 找意思相近的词、RAG 检索 |
| 矩阵乘向量 | $(m \times n)(n) \to (m)$ | 每一个线性层 |
| 线性层 | $y = Wx + b$，参数 $mn + m$ | 注意力的 $W_Q$、$W_K$、$W_V$，FFN，输出投影 |
| softmax | $p_i = \dfrac{e^{s_i}}{\sum_j e^{s_j}}$ | 注意力的份额、下一个 token 的概率 |
| 温度 | $s_i / T$ 再 softmax | 采样时控制随机程度 |
| 对数 | $\ln(ab) = \ln a + \ln b$ | 句子的概率、交叉熵损失 |

## 实验里讲了什么

1. **两支箭头**：拖动两支 2 维箭头，看点积、长度、夹角和余弦相似度怎么跟着变，投影随手画出来。
2. **矩阵乘向量逐行高亮**：改矩阵和向量里的数，一行一行走，看每一行的点积变成结果里的哪个数，箭头怎么被变成另一支箭头。
3. **形状检查器**：随便填两个形状，检查能不能乘、乘出来什么形状；输错时指出哪一维对不上。再算线性层的参数量，带上 GPT-2、Llama-3-8B 的真实形状。
4. **softmax 与温度**：拖 4 个分数和温度 $T$，看取指数、除以总和两步的每个数；和「直接除以总和」对照；按概率真的抽 100 次。
5. **数值稳定性**：把分数放大到几百，在 float64、float32、float16 下对照「直接取指数」和「先减最大值」，看溢出和 NaN 在哪里出现。
6. **对数**：概率连乘在 float32 里多少步变成 0，对数相加始终正常；再看 $-\ln p$ 怎么随正确答案的概率变化。

## 和前后两讲的关系

上一讲讲了 token 怎么进出模型：查表变成向量，一层层变换，最后投影成分数、softmax、采样。这一讲把其中用到的数学单独拿出来，一步一步算清楚。下一讲注意力会把这里的东西全部用上：第六步的 $W_Q\,x = (1.0,\ -0.6)$、第八步的 $W_K$、第七步的 4 个分数 $(1.6,\ 0.48,\ 0.08,\ 1.0)$、第十二步的 47.8%、第十三步 $T = \sqrt{2}$ 时的 40.8%，都会原样再出现一次，到那时你会知道它们各自是什么意思。

## 延伸阅读

- 3Blue1Brown，《线性代数的本质》系列视频（向量、矩阵乘法的几何直观）
- Goodfellow, Bengio, Courville, *Deep Learning* (2016)，第 2 章「线性代数」与第 4.1 节（softmax 的数值稳定性）
