---
title: "Scaling Laws：模型、数据、算力该怎么配"
description: "训练一个模型要算多少次？先从一层 3 × 2 的小网络数起，推出 C ≈ 6ND：前向 2、反向 4。再看 Kaplan 的发现：损失随参数、数据、算力按幂律下降，在对数坐标上是一条直线；Chinchilla 把它改成一个两项相加的公式，求导推出给定算力时参数和数据应该同比例增长，约每个参数 20 个 token。最后解释 Llama 3 为什么故意过训练，涌现能力是真的还是度量造成的，并用 GPT-3、Chinchilla、Llama 3 的公开数字核算一遍。"
pubDate: 2026-10-22
tags: ["训练", "预训练", "Scaling Laws", "Chinchilla", "算力"]
lab: /labs/scaling-laws/
series: ai-mastery
order: 38
---

<!-- 本文由 labs-src/scaling-laws/toy.py 从 article.src.md 生成，图和数字都由脚本算出。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

训练一个大模型，要先决定三件事：模型多大（参数量 $N$）、读多少数据（训练 token 数 $D$）、花多少算力（$C$，总共做多少次浮点运算）。三者之间有一个很准的账：$C \approx 6ND$。**Scaling Laws**（规模定律）说的是另一件事：模型的损失随 $N$、$D$、$C$ 的增大**按幂律平稳下降**，在对数坐标上是一条直线，所以可以先用小模型试，再外推出大模型的结果。

由此能回答一个很实际的问题：**算力固定，钱该花在更大的模型上，还是更多的数据上？** 2020 年 Kaplan 等人的答案是「主要花在模型上」；2022 年 Chinchilla 改正了它：两者**同比例**增长，大约每个参数配 20 个 token。而今天的模型又故意偏离这个比例、用远多于 20 倍的数据训小模型，原因是上线后每生成一个 token 都要再付一次算力。

这一讲从一个 6 个参数的小网络开始，一步一步算到 Llama 3。

## 先认识三个量

- **$N$：参数量**。模型里需要训练的数字一共有多少个。Llama-3-8B 的 $N$ 约是 80 亿，记作 8B（B = billion，十亿）。
- **$D$：训练 token 数**。训练时模型一共读了多少个 token（Token 那一讲讲过 token 是什么）。Llama 3 读了约 15 T 个（T = trillion，万亿）。
- **$C$：训练算力**。整个训练一共做了多少次浮点运算，单位是 FLOP（一次加法或一次乘法算 1 次）。这个数非常大，所以用科学计数法写，比如 $3.14 \times 10^{23}$。

还有一个量要分清：**FLOPS**（末尾大写 S）是**每秒**能做多少次浮点运算，是显卡的速度。$C$ 是总量，FLOPS 是速度，总量除以速度就是时间。

下面先回答第一个问题：给定 $N$ 和 $D$，$C$ 是多少。

## 第一步：前向，每个参数 2 次运算

取最小的例子：一层线性变换 $y = Wx$。输入 $x$ 有 3 个数，输出 $y$ 有 2 个数，所以 $W$ 是一个 2 行 3 列的矩阵，有 $2 \times 3 = 6$ 个参数，$N = 6$。

具体的数：

$$
W = \begin{pmatrix} 1 & 0 & 2 \\ 0 & 1 & 1 \end{pmatrix}, \qquad x = \begin{pmatrix} 1 \\ 2 \\ 3 \end{pmatrix}
$$

第一个输出是 $W$ 第一行和 $x$ 逐个相乘再加起来：

$$
\begin{aligned}
y_1 &= 1 \times 1 + 0 \times 2 + 2 \times 3 \\
&= 1 + 0 + 6 = 7
\end{aligned}
$$

第二个输出用第二行：

$$
\begin{aligned}
y_2 &= 0 \times 1 + 1 \times 2 + 1 \times 3 \\
&= 0 + 2 + 3 = 5
\end{aligned}
$$

<figure class="fig">
<svg viewBox="0 0 480 248" role="img" aria-label="一层 y = Wx 的前向：3 个输入、2 个输出、6 条连线">
<line x1="114.0" y1="50.0" x2="355.1" y2="83.8" style="stroke:var(--accent);stroke-width:1.6;fill:none"/><path d="M364.0 85.0 L355.4 87.5 L356.4 80.2 z" style="fill:var(--accent)"/><line x1="114.0" y1="120.0" x2="355.1" y2="86.2" style="stroke:var(--accent);stroke-width:1.6;fill:none"/><path d="M364.0 85.0 L356.4 89.8 L355.4 82.5 z" style="fill:var(--accent)"/><line x1="114.0" y1="190.0" x2="355.7" y2="88.5" style="stroke:var(--accent);stroke-width:1.6;fill:none"/><path d="M364.0 85.0 L357.8 91.6 L355.0 84.8 z" style="fill:var(--accent)"/><line x1="114.0" y1="50.0" x2="355.7" y2="151.5" style="stroke:var(--accent);stroke-width:1.6;fill:none"/><path d="M364.0 155.0 L355.0 155.2 L357.8 148.4 z" style="fill:var(--accent)"/><line x1="114.0" y1="120.0" x2="355.1" y2="153.8" style="stroke:var(--accent);stroke-width:1.6;fill:none"/><path d="M364.0 155.0 L355.4 157.5 L356.4 150.2 z" style="fill:var(--accent)"/><line x1="114.0" y1="190.0" x2="355.1" y2="156.2" style="stroke:var(--accent);stroke-width:1.6;fill:none"/><path d="M364.0 155.0 L356.4 159.8 L355.4 152.5 z" style="fill:var(--accent)"/><circle cx="90.0" cy="50.0" r="22" style="fill:var(--paper)"/><circle cx="90.0" cy="50.0" r="22" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="90.0" y="56.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">1</text><circle cx="90.0" cy="120.0" r="22" style="fill:var(--paper)"/><circle cx="90.0" cy="120.0" r="22" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="90.0" y="126.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">2</text><circle cx="90.0" cy="190.0" r="22" style="fill:var(--paper)"/><circle cx="90.0" cy="190.0" r="22" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="90.0" y="196.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">3</text><circle cx="390.0" cy="85.0" r="22" style="fill:var(--paper)"/><circle cx="390.0" cy="85.0" r="22" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="390.0" y="91.0" font-size="17" text-anchor="middle" style="fill:var(--accent)">7</text><circle cx="390.0" cy="155.0" r="22" style="fill:var(--paper)"/><circle cx="390.0" cy="155.0" r="22" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="390.0" y="161.0" font-size="17" text-anchor="middle" style="fill:var(--accent)">5</text><rect x="178.0" y="51.5" width="22.0" height="18.0" rx="4" style="fill:var(--bg)"/><text x="189.0" y="65.5" font-size="14" text-anchor="middle" style="fill:var(--accent)">1</text><rect x="178.0" y="100.5" width="22.0" height="18.0" rx="4" style="fill:var(--bg)"/><text x="189.0" y="114.5" font-size="14" text-anchor="middle" style="fill:var(--accent)">0</text><rect x="178.0" y="149.5" width="22.0" height="18.0" rx="4" style="fill:var(--bg)"/><text x="189.0" y="163.5" font-size="14" text-anchor="middle" style="fill:var(--accent)">2</text><rect x="178.0" y="72.5" width="22.0" height="18.0" rx="4" style="fill:var(--bg)"/><text x="189.0" y="86.5" font-size="14" text-anchor="middle" style="fill:var(--accent)">0</text><rect x="178.0" y="121.5" width="22.0" height="18.0" rx="4" style="fill:var(--bg)"/><text x="189.0" y="135.5" font-size="14" text-anchor="middle" style="fill:var(--accent)">1</text><rect x="178.0" y="170.5" width="22.0" height="18.0" rx="4" style="fill:var(--bg)"/><text x="189.0" y="184.5" font-size="14" text-anchor="middle" style="fill:var(--accent)">1</text><text x="90.0" y="236.0" font-size="16" text-anchor="middle" style="fill:var(--muted)"><tspan font-style="italic">x</tspan></text><text x="240.0" y="236.0" font-size="16" text-anchor="middle" style="fill:var(--accent)"><tspan font-style="italic">W</tspan>（6 个参数）</text><text x="390.0" y="236.0" font-size="16" text-anchor="middle" style="fill:var(--muted)"><tspan font-style="italic">y</tspan> = <tspan font-style="italic">W</tspan><tspan font-style="italic">x</tspan></text>
</svg>
<figcaption>图 1　前向：每条连线是一个参数，线上的数字是它的值。输入 (1, 2, 3) 沿 6 条线流到右边，得到 (7, 5)。每条线做一次乘法，再把乘积加进右边的和里。</figcaption>
</figure>

数一下做了多少次运算。每个输出要 3 次乘法（一个参数一次），再把 3 个乘积加起来要 2 次加法。两个输出一共 $6$ 次乘法、$4$ 次加法，合计 $10$ 次。

乘法正好是 6 次，等于参数个数：**每个参数做一次乘法**。加法是 4 次，比 6 少，因为每一行的第一个乘积不用加。如果输入不是 3 个数而是 4096 个，每行要 4096 次乘法、4095 次加法，两者几乎一样多。所以真实模型里可以说：**每个参数一次乘法、一次加法，前向每个 token 约 $2N$ 次运算**。

MoE 那一讲说过「每 token 计算量 ≈ 2 × 激活参数」，就是这里的 $2N$。

## 第二步：反向，每个参数 4 次运算

反向传播那一讲讲过：反向时，每一层从上面收到损失对它输出的梯度（上游梯度），要做两件事。设上游梯度是

$$
g = \frac{\partial L}{\partial y} = \begin{pmatrix} 1 \\ -1 \end{pmatrix}
$$

**第 ① 件：把梯度传给上一层**，也就是算损失对输入 $x$ 的梯度。$x_1$ 通过 $W_{11}$ 影响 $y_1$、通过 $W_{21}$ 影响 $y_2$，按链式法则把两条路的贡献加起来：

$$
\begin{aligned}
\frac{\partial L}{\partial x_1} &= W_{11}\, g_1 + W_{21}\, g_2 \\
&= 1 \times 1 + 0 \times (-1) = 1
\end{aligned}
$$

另外两个同样算：

$$
\begin{aligned}
\frac{\partial L}{\partial x_2} &= 0 \times 1 + 1 \times (-1) = -1 \\
\frac{\partial L}{\partial x_3} &= 2 \times 1 + 1 \times (-1) = 1
\end{aligned}
$$

写成矩阵就是 $\frac{\partial L}{\partial x} = W^{\top} g$。数一下：还是每个参数一次乘法，6 次乘法、3 次加法。和前向一样，规模大时是 $2N$。

**第 ② 件：算每个参数自己的梯度**，这是梯度下降要用的。参数 $W_{ij}$ 只出现在 $y_i$ 里，而且是乘以 $x_j$，所以 $y_i$ 对它的导数就是 $x_j$，再乘上游梯度：

$$
\frac{\partial L}{\partial W_{ij}} = g_i\, x_j
$$

比如 $\frac{\partial L}{\partial W_{13}} = g_1 x_3 = 1 \times 3 = 3$，$\frac{\partial L}{\partial W_{21}} = g_2 x_1 = (-1) \times 1 = -1$。6 个参数各算一次乘法：

$$
\frac{\partial L}{\partial W} = g\,x^{\top} = \begin{pmatrix} 1 & 2 & 3 \\ -1 & -2 & -3 \end{pmatrix}
$$

<figure class="fig">
<svg viewBox="0 0 480 240" role="img" aria-label="反向的两件事：把梯度传回输入，算出每个参数的梯度">
<line x1="208.0" y1="82.0" x2="92.7" y2="52.2" style="stroke:var(--warn);stroke-width:1.5;fill:none"/><path d="M84.0 50.0 L92.9 48.5 L91.0 55.6 z" style="fill:var(--warn)"/><line x1="208.0" y1="82.0" x2="92.7" y2="112.7" style="stroke:var(--warn);stroke-width:1.5;fill:none"/><path d="M84.0 115.0 L91.0 109.3 L92.9 116.4 z" style="fill:var(--warn)"/><line x1="208.0" y1="82.0" x2="91.1" y2="174.4" style="stroke:var(--warn);stroke-width:1.5;fill:none"/><path d="M84.0 180.0 L88.2 172.0 L92.7 177.8 z" style="fill:var(--warn)"/><line x1="208.0" y1="148.0" x2="91.1" y2="55.6" style="stroke:var(--warn);stroke-width:1.5;fill:none"/><path d="M84.0 50.0 L92.7 52.2 L88.2 58.0 z" style="fill:var(--warn)"/><line x1="208.0" y1="148.0" x2="92.7" y2="117.3" style="stroke:var(--warn);stroke-width:1.5;fill:none"/><path d="M84.0 115.0 L92.9 113.6 L91.0 120.7 z" style="fill:var(--warn)"/><line x1="208.0" y1="148.0" x2="92.7" y2="177.8" style="stroke:var(--warn);stroke-width:1.5;fill:none"/><path d="M84.0 180.0 L91.0 174.4 L92.9 181.5 z" style="fill:var(--warn)"/><circle cx="60.0" cy="50.0" r="20" style="fill:var(--paper)"/><circle cx="60.0" cy="50.0" r="20" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="60.0" y="56.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">1</text><circle cx="60.0" cy="115.0" r="20" style="fill:var(--paper)"/><circle cx="60.0" cy="115.0" r="20" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="60.0" y="121.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">−1</text><circle cx="60.0" cy="180.0" r="20" style="fill:var(--paper)"/><circle cx="60.0" cy="180.0" r="20" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="60.0" y="186.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">1</text><circle cx="230.0" cy="82.0" r="20" style="fill:var(--paper)"/><circle cx="230.0" cy="82.0" r="20" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="230.0" y="88.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">1</text><circle cx="230.0" cy="148.0" r="20" style="fill:var(--paper)"/><circle cx="230.0" cy="148.0" r="20" style="stroke:var(--muted);stroke-width:2;fill:none"/><text x="230.0" y="154.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">−1</text><text x="145.0" y="228.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">① 传给上一层</text><rect x="300.0" y="70.0" width="48.0" height="40.0" rx="5" style="fill:none;stroke:var(--warn);stroke-width:1.4"/><text x="324.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">1</text><rect x="352.0" y="70.0" width="48.0" height="40.0" rx="5" style="fill:none;stroke:var(--warn);stroke-width:1.4"/><text x="376.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">2</text><rect x="404.0" y="70.0" width="48.0" height="40.0" rx="5" style="fill:none;stroke:var(--warn);stroke-width:1.4"/><text x="428.0" y="97.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">3</text><rect x="300.0" y="114.0" width="48.0" height="40.0" rx="5" style="fill:none;stroke:var(--warn);stroke-width:1.4"/><text x="324.0" y="141.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">−1</text><rect x="352.0" y="114.0" width="48.0" height="40.0" rx="5" style="fill:none;stroke:var(--warn);stroke-width:1.4"/><text x="376.0" y="141.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">−2</text><rect x="404.0" y="114.0" width="48.0" height="40.0" rx="5" style="fill:none;stroke:var(--warn);stroke-width:1.4"/><text x="428.0" y="141.0" font-size="16" text-anchor="middle" style="fill:var(--warn)">−3</text><text x="324.0" y="60.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><text x="376.0" y="60.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2</text><text x="428.0" y="60.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">3</text><text x="290.0" y="97.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1</text><text x="290.0" y="141.0" font-size="14" text-anchor="end" style="fill:var(--muted)">−1</text><text x="290.0" y="60.0" font-size="13" text-anchor="end" style="fill:var(--muted)"><tspan font-style="italic">g</tspan>＼<tspan font-style="italic">x</tspan></text><text x="376.0" y="228.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">② 每个参数的梯度</text>
</svg>
<figcaption>图 2　反向：右边两个输出收到上游传来的梯度 (1, −1)。① 沿原来的 6 条线倒着走，每条线一次乘一次加，得到传给上一层的梯度 (1, −1, 1)；② 每个参数的梯度 = 它右端的梯度 × 它左端的输入，6 个参数各算一次。</figcaption>
</figure>

为什么这里也算 $2N$？因为训练时一批里有很多个 token，每个 token 都会算出一份 $g_i x_j$，要把它们**加起来**才是这一批的梯度。所以每个 token、每个参数是一次乘法加一次加法，6 个参数就是 12 次，即 $2N$。

两件事合起来，反向每个 token 约 $4N$ 次运算，正好是前向的 2 倍。

<details class="pause"><summary>停一下：模型训好以后拿来用（只生成，不再训练），每个 token 要多少次运算？</summary>

只做前向，不做反向，所以是 $2N$，是训练时每个 token 的三分之一。8B 模型每生成一个 token 约 $1.6 \times 10^{10}$ 次运算。后面讲「过训练」时会用到这个数。

</details>

## 第三步：合起来就是 6ND

每个 token：前向 $2N$，反向 $4N$，一共

$$
2N + 4N = 6N
$$

训练读了 $D$ 个 token，每个都要做一遍，所以总算力是

$$
C \approx 6ND
$$

<figure class="fig">
<svg viewBox="0 0 480 248" role="img" aria-label="每个 token 的计算量 6N 和 Llama-3-8B 换算成的 H100 卡时">
<rect x="20.0" y="30.0" width="124.0" height="34.0" rx="5" style="fill:var(--accent)"/><text x="82.0" y="53.0" font-size="17" text-anchor="middle" style="fill:var(--bg)">2<tspan font-style="italic">N</tspan></text><text x="82.0" y="88.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">前向</text><rect x="148.0" y="30.0" width="124.0" height="34.0" rx="5" style="fill:var(--warn)"/><text x="210.0" y="53.0" font-size="17" text-anchor="middle" style="fill:var(--bg)">2<tspan font-style="italic">N</tspan></text><text x="210.0" y="88.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">反向 ①</text><rect x="276.0" y="30.0" width="124.0" height="34.0" rx="5" style="fill:var(--warn)"/><text x="338.0" y="53.0" font-size="17" text-anchor="middle" style="fill:var(--bg)">2<tspan font-style="italic">N</tspan></text><text x="338.0" y="88.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">反向 ②</text><text x="414.0" y="53.0" font-size="18" text-anchor="start" style="fill:var(--fg)">= 6<tspan font-style="italic">N</tspan></text><text x="20.0" y="20.0" font-size="14" text-anchor="start" style="fill:var(--muted)">每个 token</text><text x="110.0" y="143.0" font-size="15" text-anchor="end" style="fill:var(--muted)">利用率 100%</text><rect x="120.0" y="124.0" width="46.8" height="26.0" rx="4" style="fill:var(--line)"/><text x="172.8" y="143.0" font-size="15" text-anchor="start" style="fill:var(--muted)">20.3 万</text><text x="110.0" y="183.0" font-size="15" text-anchor="end" style="fill:var(--muted)">利用率 40%</text><rect x="120.0" y="164.0" width="117.0" height="26.0" rx="4" style="fill:var(--accent)"/><text x="243.0" y="183.0" font-size="15" text-anchor="start" style="fill:var(--accent)">50.7 万</text><text x="110.0" y="223.0" font-size="15" text-anchor="end" style="fill:var(--muted)">官方报告</text><rect x="120.0" y="204.0" width="300.0" height="26.0" rx="4" style="fill:var(--fg)"/><text x="426.0" y="223.0" font-size="15" text-anchor="start" style="fill:var(--fg)">130.0 万</text><text x="20.0" y="114.0" font-size="14" text-anchor="start" style="fill:var(--muted)">Llama-3-8B 的 H100 卡时</text>
</svg>
<figcaption>图 3　上：每个 token 要算 6<i>N</i> 次浮点运算，前向 2<i>N</i>，反向两件事各 2<i>N</i>。下：Llama-3-8B 的 7.23 × 10<sup>23</sup> 次运算换成 H100 卡时；官方报告的 130 万卡时，相当于平均只用上了峰值的 15.6%。</figcaption>
</figure>

代入 Llama-3-8B：$N = 8.03 \times 10^{9}$（按它的配置把每个矩阵的参数加起来），$D = 1.5 \times 10^{13}$（官方说「超过 15 T token」）：

$$
\begin{aligned}
C &\approx 6 \times 8.03 \times 10^{9} \times 1.5 \times 10^{13} \\
&= 7.23 \times 10^{23} \ \text{FLOPs}
\end{aligned}
$$

这个公式忽略了三样东西，都比较小：

1. **注意力里 $q \cdot k$ 和加权求和**。它们算的是 token 和 token 之间的乘积，不对应参数，所以不在 $2N$ 里。Kaplan 等人给的估计是每 token 前向多 $2\, n_{\text{layer}}\, n_{\text{ctx}}\, d$ 次（层数 × 上下文长度 × 宽度 × 2）。Llama-3-8B 是 32 层、上下文 8192、宽度 4096，算出来是 $2.15 \times 10^{9}$，而 $2N = 1.61 \times 10^{10}$，多出约 13.4%。上下文越长，这一项越大。
2. **LayerNorm、激活函数、softmax** 这些逐个元素的运算，每个 token 只有几万到几十万次，和几十亿的 $2N$ 比可以忽略。
3. **优化器更新参数**。每一**步**更新一次，不是每个 token 一次。一步通常处理几百万个 token，摊到每个 token 上几乎为零。

所以 $6ND$ 是一个偏低一点、但足够准的估计。论文和技术报告里大都用它。

## 第四步：换成 GPU 卡时

有了总运算次数，除以显卡速度就是时间。H100 做 BF16 矩阵乘法的峰值是 989.5 TFLOPS，即每秒 $9.895 \times 10^{14}$ 次（NVIDIA 数据表写的 1979 TFLOPS 是按「稀疏」算的，正常训练用不上，要减半）。

如果一张 H100 一直跑满峰值：

$$
\frac{7.23 \times 10^{23}}{9.895 \times 10^{14}} = 7.30 \times 10^{8} \ \text{s}
$$

一小时是 3600 s，除一下是 202,880 卡时，约 20.3 万 卡时。也就是 1 张卡跑 20 万小时，或 1 万张卡跑 20 小时。

实际上显卡不可能一直跑满：要等数据从显存搬进来，要和别的卡通信，还有一些不是矩阵乘法的运算。实际算力占峰值的比例叫 **MFU**（Model FLOPs Utilization，模型算力利用率）。Llama 3 技术报告里 405B 模型的 MFU 是 38%–43%。按 40% 算，卡时要除以 0.4：

$$
\frac{202{,}880}{0.4} \approx 507{,}201 \ \text{卡时}
$$

Meta 的官方模型卡给的是 **130 万 H100 卡时**，比 50 万多出一倍半。反过来算，130 万卡时里平均只用上了峰值的

$$
\frac{202{,}880}{1{,}300{,}000} = 15.6\%
$$

原因模型卡没有拆开写。可以想到的有：8B 这样的小模型分到上万张卡上，每张卡上的矩阵太小，通信占比大，MFU 比 405B 低；训练中途出故障、重启、回退到检查点；卡时里可能还算了调试和评测。所以 **$6ND$ 算的是「最少要做的运算」，真实账单通常是它的 2–3 倍**。

<details class="pause"><summary>停一下：同样 1.3 × 10<sup>6</sup> 卡时，如果用 1 万张 H100 同时训，要训多少天？</summary>

$1.3 \times 10^{6}$ 卡时除以 $10^{4}$ 张卡，是 130 小时，约 5.4 天。Meta 说 Llama 3 是在两个各 2.4 万张 GPU 的集群上训的，8B 和 70B 一共 770 万卡时，所以整个预训练前后要几周。

</details>

## Kaplan 2020：损失按幂律下降

现在换一个问题：花了这么多算力，模型能好多少？

先说「好」用什么量。模型评测那一讲讲过，训练时看的是**损失**：模型给正确的下一个 token 的概率取负对数，在一大段没训练过的文本上取平均，单位是 nat（自然对数下的信息量）。损失越低越好，它的指数就是困惑度。

2020 年，OpenAI 的 Kaplan 等人训练了从 768 个到 15 亿个参数的一批模型（$N$ 不算嵌入表），发现损失和参数量之间有一个很简单的关系：

$$
L(N) = \left(\frac{N_c}{N}\right)^{\alpha_N}
$$

其中 $\alpha_N \approx 0.076$，$N_c \approx 8.8 \times 10^{13}$。

先把数代进去看。$N = 10^{9}$（1B）时：

$$
\begin{aligned}
L(10^{9}) &= \left(\frac{8.8 \times 10^{13}}{10^{9}}\right)^{0.076} \\
&= (88000)^{0.076} = 2.376
\end{aligned}
$$

$N = 10^{10}$（10B）时，括号里的数变成 8800：

$$
L(10^{10}) = (8800)^{0.076} = 1.994
$$

参数多了 10 倍，损失从 2.376 降到 1.994。两者的比是

$$
\frac{1.994}{2.376} = 10^{-0.076} = 0.839
$$

这个比和从哪个 $N$ 开始无关：把公式里的 $N$ 换成 $10N$，括号里的数变成原来的 $1/10$，整体就乘上 $10^{-0.076}$。所以**参数每乘 10，损失就乘 0.839，降 16.1%**；参数每翻一倍，损失乘 $2^{-0.076} = 0.949$，降 5.1%。这就是「幂律」的意思：每乘同样的倍数，损失降同样的比例。

### 为什么在对数坐标上是直线

两边取自然对数，幂变成乘法，除法变成减法：

$$
\ln L = \alpha_N \ln N_c - \alpha_N \ln N
$$

把 $\ln N$ 看成横坐标、$\ln L$ 看成纵坐标，这就是一条直线：斜率是 $-\alpha_N = -0.076$，截距是 $\alpha_N \ln N_c$。用上面两个点验证一下：

$$
\begin{aligned}
\frac{\ln 1.994 - \ln 2.376}{\ln 10^{10} - \ln 10^{9}} &= \frac{0.6903 - 0.8653}{23.026 - 20.723} \\
&= -0.076
\end{aligned}
$$

<figure class="fig">
<svg viewBox="0 0 480 222" role="img" aria-label="同一条幂律在普通坐标和对数坐标下">
<line x1="46.0" y1="174.0" x2="206.0" y2="174.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="46.0" y1="24.0" x2="46.0" y2="174.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><path d="M46.0 48.2 L46.4 92.2 L46.8 100.1 L47.2 104.5 L47.6 107.6 L48.0 110.0 L48.4 111.9 L48.8 113.5 L49.2 114.8 L49.6 116.0 L50.0 117.1 L50.4 118.0 L50.8 118.9 L51.2 119.7 L51.6 120.4 L52.0 121.1 L52.4 121.7 L52.8 122.3 L53.2 122.8 L53.6 123.3 L54.0 123.8 L54.4 124.3 L54.8 124.7 L55.2 125.1 L55.6 125.5 L56.0 125.9 L56.4 126.3 L56.8 126.6 L57.2 127.0 L57.6 127.3 L58.0 127.6 L58.4 127.9 L58.8 128.2 L59.2 128.5 L59.6 128.8 L60.0 129.0 L60.4 129.3 L60.8 129.5 L61.2 129.8 L61.6 130.0 L62.0 130.2 L62.4 130.4 L62.8 130.7 L63.2 130.9 L63.6 131.1 L64.0 131.3 L64.4 131.5 L64.8 131.7 L65.2 131.9 L65.6 132.0 L66.0 132.2 L66.4 132.4 L66.8 132.6 L67.2 132.7 L67.6 132.9 L68.0 133.1 L68.4 133.2 L68.8 133.4 L69.2 133.5 L69.6 133.7 L70.0 133.8 L70.4 134.0 L70.8 134.1 L71.2 134.3 L71.6 134.4 L72.0 134.5 L72.4 134.7 L72.8 134.8 L73.2 134.9 L73.6 135.0 L74.0 135.2 L74.4 135.3 L74.8 135.4 L75.2 135.5 L75.6 135.6 L76.0 135.8 L76.4 135.9 L76.8 136.0 L77.2 136.1 L77.6 136.2 L78.0 136.3 L78.4 136.4 L78.8 136.5 L79.2 136.6 L79.6 136.7 L80.0 136.8 L80.4 136.9 L80.8 137.0 L81.2 137.1 L81.6 137.2 L82.0 137.3 L82.4 137.4 L82.8 137.5 L83.2 137.6 L83.6 137.7 L84.0 137.8 L84.4 137.9 L84.8 138.0 L85.2 138.0 L85.6 138.1 L86.0 138.2 L86.4 138.3 L86.8 138.4 L87.2 138.5 L87.6 138.5 L88.0 138.6 L88.4 138.7 L88.8 138.8 L89.2 138.9 L89.6 138.9 L90.0 139.0 L90.4 139.1 L90.8 139.2 L91.2 139.2 L91.6 139.3 L92.0 139.4 L92.4 139.5 L92.8 139.5 L93.2 139.6 L93.6 139.7 L94.0 139.7 L94.4 139.8 L94.8 139.9 L95.2 139.9 L95.6 140.0 L96.0 140.1 L96.4 140.1 L96.8 140.2 L97.2 140.3 L97.6 140.3 L98.0 140.4 L98.4 140.5 L98.8 140.5 L99.2 140.6 L99.6 140.6 L100.0 140.7 L100.4 140.8 L100.8 140.8 L101.2 140.9 L101.6 140.9 L102.0 141.0 L102.4 141.1 L102.8 141.1 L103.2 141.2 L103.6 141.2 L104.0 141.3 L104.4 141.4 L104.8 141.4 L105.2 141.5 L105.6 141.5 L106.0 141.6 L106.4 141.6 L106.8 141.7 L107.2 141.7 L107.6 141.8 L108.0 141.8 L108.4 141.9 L108.8 141.9 L109.2 142.0 L109.6 142.0 L110.0 142.1 L110.4 142.1 L110.8 142.2 L111.2 142.2 L111.6 142.3 L112.0 142.3 L112.4 142.4 L112.8 142.4 L113.2 142.5 L113.6 142.5 L114.0 142.6 L114.4 142.6 L114.8 142.7 L115.2 142.7 L115.6 142.8 L116.0 142.8 L116.4 142.9 L116.8 142.9 L117.2 143.0 L117.6 143.0 L118.0 143.0 L118.4 143.1 L118.8 143.1 L119.2 143.2 L119.6 143.2 L120.0 143.3 L120.4 143.3 L120.8 143.4 L121.2 143.4 L121.6 143.4 L122.0 143.5 L122.4 143.5 L122.8 143.6 L123.2 143.6 L123.6 143.7 L124.0 143.7 L124.4 143.7 L124.8 143.8 L125.2 143.8 L125.6 143.9 L126.0 143.9 L126.4 143.9 L126.8 144.0 L127.2 144.0 L127.6 144.1 L128.0 144.1 L128.4 144.1 L128.8 144.2 L129.2 144.2 L129.6 144.2 L130.0 144.3 L130.4 144.3 L130.8 144.4 L131.2 144.4 L131.6 144.4 L132.0 144.5 L132.4 144.5 L132.8 144.5 L133.2 144.6 L133.6 144.6 L134.0 144.7 L134.4 144.7 L134.8 144.7 L135.2 144.8 L135.6 144.8 L136.0 144.8 L136.4 144.9 L136.8 144.9 L137.2 144.9 L137.6 145.0 L138.0 145.0 L138.4 145.0 L138.8 145.1 L139.2 145.1 L139.6 145.1 L140.0 145.2 L140.4 145.2 L140.8 145.2 L141.2 145.3 L141.6 145.3 L142.0 145.3 L142.4 145.4 L142.8 145.4 L143.2 145.4 L143.6 145.5 L144.0 145.5 L144.4 145.5 L144.8 145.6 L145.2 145.6 L145.6 145.6 L146.0 145.7 L146.4 145.7 L146.8 145.7 L147.2 145.8 L147.6 145.8 L148.0 145.8 L148.4 145.8 L148.8 145.9 L149.2 145.9 L149.6 145.9 L150.0 146.0 L150.4 146.0 L150.8 146.0 L151.2 146.1 L151.6 146.1 L152.0 146.1 L152.4 146.1 L152.8 146.2 L153.2 146.2 L153.6 146.2 L154.0 146.3 L154.4 146.3 L154.8 146.3 L155.2 146.4 L155.6 146.4 L156.0 146.4 L156.4 146.4 L156.8 146.5 L157.2 146.5 L157.6 146.5 L158.0 146.5 L158.4 146.6 L158.8 146.6 L159.2 146.6 L159.6 146.7 L160.0 146.7 L160.4 146.7 L160.8 146.7 L161.2 146.8 L161.6 146.8 L162.0 146.8 L162.4 146.8 L162.8 146.9 L163.2 146.9 L163.6 146.9 L164.0 147.0 L164.4 147.0 L164.8 147.0 L165.2 147.0 L165.6 147.1 L166.0 147.1 L166.4 147.1 L166.8 147.1 L167.2 147.2 L167.6 147.2 L168.0 147.2 L168.4 147.2 L168.8 147.3 L169.2 147.3 L169.6 147.3 L170.0 147.3 L170.4 147.4 L170.8 147.4 L171.2 147.4 L171.6 147.4 L172.0 147.5 L172.4 147.5 L172.8 147.5 L173.2 147.5 L173.6 147.6 L174.0 147.6 L174.4 147.6 L174.8 147.6 L175.2 147.7 L175.6 147.7 L176.0 147.7 L176.4 147.7 L176.8 147.7 L177.2 147.8 L177.6 147.8 L178.0 147.8 L178.4 147.8 L178.8 147.9 L179.2 147.9 L179.6 147.9 L180.0 147.9 L180.4 148.0 L180.8 148.0 L181.2 148.0 L181.6 148.0 L182.0 148.0 L182.4 148.1 L182.8 148.1 L183.2 148.1 L183.6 148.1 L184.0 148.2 L184.4 148.2 L184.8 148.2 L185.2 148.2 L185.6 148.2 L186.0 148.3 L186.4 148.3 L186.8 148.3 L187.2 148.3 L187.6 148.4 L188.0 148.4 L188.4 148.4 L188.8 148.4 L189.2 148.4 L189.6 148.5 L190.0 148.5 L190.4 148.5 L190.8 148.5 L191.2 148.5 L191.6 148.6 L192.0 148.6 L192.4 148.6 L192.8 148.6 L193.2 148.7 L193.6 148.7 L194.0 148.7 L194.4 148.7 L194.8 148.7 L195.2 148.8 L195.6 148.8 L196.0 148.8 L196.4 148.8 L196.8 148.8 L197.2 148.9 L197.6 148.9 L198.0 148.9 L198.4 148.9 L198.8 148.9 L199.2 149.0 L199.6 149.0 L200.0 149.0 L200.4 149.0 L200.8 149.0 L201.2 149.1 L201.6 149.1 L202.0 149.1 L202.4 149.1 L202.8 149.1 L203.2 149.2 L203.6 149.2 L204.0 149.2 L204.4 149.2 L204.8 149.2 L205.2 149.2 L205.6 149.3 L206.0 149.3" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><line x1="41.0" y1="149.0" x2="46.0" y2="149.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="38.0" y="154.0" font-size="14" text-anchor="end" style="fill:var(--muted)">2</text><line x1="41.0" y1="99.0" x2="46.0" y2="99.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="38.0" y="104.0" font-size="14" text-anchor="end" style="fill:var(--muted)">3</text><line x1="41.0" y1="49.0" x2="46.0" y2="49.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="38.0" y="54.0" font-size="14" text-anchor="end" style="fill:var(--muted)">4</text><line x1="46.0" y1="174.0" x2="46.0" y2="179.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="46.0" y="195.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0</text><line x1="126.0" y1="174.0" x2="126.0" y2="179.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="126.0" y="195.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">5B</text><line x1="206.0" y1="174.0" x2="206.0" y2="179.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="206.0" y="195.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10B</text><text x="126.0" y="214.0" font-size="14" text-anchor="middle" style="fill:var(--muted)"><tspan font-style="italic">N</tspan>（普通刻度）</text><text x="14.0" y="16.0" font-size="14" text-anchor="start" style="fill:var(--muted)"><tspan font-style="italic">L</tspan></text><line x1="296.0" y1="174.0" x2="456.0" y2="174.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="296.0" y1="24.0" x2="296.0" y2="174.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><path d="M296.0 39.5 L297.0 40.1 L298.0 40.7 L299.0 41.3 L300.0 41.9 L301.0 42.5 L302.0 43.1 L303.0 43.7 L304.0 44.3 L305.0 44.9 L306.0 45.5 L307.0 46.1 L308.0 46.7 L309.0 47.3 L310.0 47.9 L311.0 48.5 L312.0 49.1 L313.0 49.7 L314.0 50.3 L315.0 50.9 L316.0 51.5 L317.0 52.1 L318.0 52.7 L319.0 53.3 L320.0 53.9 L321.0 54.5 L322.0 55.1 L323.0 55.7 L324.0 56.3 L325.0 56.9 L326.0 57.5 L327.0 58.1 L328.0 58.7 L329.0 59.3 L330.0 59.8 L331.0 60.4 L332.0 61.0 L333.0 61.6 L334.0 62.2 L335.0 62.8 L336.0 63.4 L337.0 64.0 L338.0 64.6 L339.0 65.2 L340.0 65.8 L341.0 66.4 L342.0 67.0 L343.0 67.6 L344.0 68.2 L345.0 68.8 L346.0 69.4 L347.0 70.0 L348.0 70.6 L349.0 71.2 L350.0 71.8 L351.0 72.4 L352.0 73.0 L353.0 73.6 L354.0 74.2 L355.0 74.8 L356.0 75.4 L357.0 76.0 L358.0 76.6 L359.0 77.2 L360.0 77.8 L361.0 78.4 L362.0 79.0 L363.0 79.6 L364.0 80.2 L365.0 80.8 L366.0 81.4 L367.0 82.0 L368.0 82.5 L369.0 83.1 L370.0 83.7 L371.0 84.3 L372.0 84.9 L373.0 85.5 L374.0 86.1 L375.0 86.7 L376.0 87.3 L377.0 87.9 L378.0 88.5 L379.0 89.1 L380.0 89.7 L381.0 90.3 L382.0 90.9 L383.0 91.5 L384.0 92.1 L385.0 92.7 L386.0 93.3 L387.0 93.9 L388.0 94.5 L389.0 95.1 L390.0 95.7 L391.0 96.3 L392.0 96.9 L393.0 97.5 L394.0 98.1 L395.0 98.7 L396.0 99.3 L397.0 99.9 L398.0 100.5 L399.0 101.1 L400.0 101.7 L401.0 102.3 L402.0 102.9 L403.0 103.5 L404.0 104.1 L405.0 104.6 L406.0 105.2 L407.0 105.8 L408.0 106.4 L409.0 107.0 L410.0 107.6 L411.0 108.2 L412.0 108.8 L413.0 109.4 L414.0 110.0 L415.0 110.6 L416.0 111.2 L417.0 111.8 L418.0 112.4 L419.0 113.0 L420.0 113.6 L421.0 114.2 L422.0 114.8 L423.0 115.4 L424.0 116.0 L425.0 116.6 L426.0 117.2 L427.0 117.8 L428.0 118.4 L429.0 119.0 L430.0 119.6 L431.0 120.2 L432.0 120.8 L433.0 121.4 L434.0 122.0 L435.0 122.6 L436.0 123.2 L437.0 123.8 L438.0 124.4 L439.0 125.0 L440.0 125.6 L441.0 126.2 L442.0 126.8 L443.0 127.3 L444.0 127.9 L445.0 128.5 L446.0 129.1 L447.0 129.7 L448.0 130.3 L449.0 130.9 L450.0 131.5 L451.0 132.1 L452.0 132.7 L453.0 133.3 L454.0 133.9 L455.0 134.5 L456.0 135.1" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><line x1="291.0" y1="134.7" x2="296.0" y2="134.7" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="288.0" y="139.7" font-size="14" text-anchor="end" style="fill:var(--muted)">2</text><line x1="291.0" y1="79.4" x2="296.0" y2="79.4" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="288.0" y="84.4" font-size="14" text-anchor="end" style="fill:var(--muted)">3</text><line x1="291.0" y1="40.1" x2="296.0" y2="40.1" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="288.0" y="45.1" font-size="14" text-anchor="end" style="fill:var(--muted)">4</text><line x1="296.0" y1="174.0" x2="296.0" y2="179.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="296.0" y="195.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">6</tspan></text><line x1="376.0" y1="174.0" x2="376.0" y2="179.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="376.0" y="195.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">8</tspan></text><line x1="456.0" y1="174.0" x2="456.0" y2="179.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="456.0" y="195.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">10</tspan></text><circle cx="416.0" cy="111.2" r="4.5" style="fill:var(--warn)"/><circle cx="456.0" cy="135.1" r="4.5" style="fill:var(--warn)"/><text x="410.0" y="99.2" font-size="14" text-anchor="end" style="fill:var(--warn)">2.38</text><text x="454.0" y="123.1" font-size="14" text-anchor="end" style="fill:var(--warn)">1.99</text><text x="376.0" y="214.0" font-size="14" text-anchor="middle" style="fill:var(--muted)"><tspan font-style="italic">N</tspan>（对数刻度）</text><text x="264.0" y="16.0" font-size="14" text-anchor="start" style="fill:var(--muted)"><tspan font-style="italic">L</tspan>（对数刻度）</text>
</svg>
<figcaption>图 4　同一条曲线 <i>L</i> = (<i>N</i><sub>c</sub>/<i>N</i>)<sup>0.076</sup>。左边是普通刻度：大部分变化挤在最左边，看不出规律。右边两个轴都取对数：变成一条直线，参数每乘 10，损失乘 0.839（橙色两点）。</figcaption>
</figure>

直线的好处是**可以外推**：用一批小模型把直线画出来，延长它，就能在真正花大钱之前，估出大模型会到多低的损失。

Kaplan 等人对数据量和算力也找到了同样形式的规律：

- 只限制数据：$L(D) = (D_c / D)^{0.095}$，$D_c \approx 5.4 \times 10^{13}$ token
- 只限制算力（每份算力都用在最合适的模型上）：$L(C) = (C_c / C)^{0.050}$

三个指数都很小：要让损失降一半，参数得乘 $2^{1/0.076} \approx 9000$ 倍。这就是为什么模型规模一直往上翻几十倍、几百倍。

注意这些数字是在他们的数据集（WebText2）和分词器上测的，常数 $N_c$、$D_c$ 换了数据就会变，不同论文的损失值不能直接比。能比的是**直线的形状**。

### Kaplan 给出的配法

Kaplan 等人还回答了「算力翻倍该怎么花」：最优参数量 $N \propto C^{0.73}$，数据量 $D \propto C^{0.27}$。算力乘 10，参数乘 $10^{0.73} \approx 5.4$，数据只乘 $10^{0.27} \approx 1.9$。结论是：**钱主要花在更大的模型上**。

同年的 GPT-3 基本就是这样做的：175B 参数，只读了 300B token，每个参数不到 2 个 token。

## Chinchilla 2022：参数和数据同比例增长

2022 年，DeepMind 的 Hoffmann 等人训练了 400 多个模型（7000 万到 160 多亿参数，50 亿到 5000 亿 token），得出不同的结论。Chinchilla 论文指出的主要差别是：Kaplan 的实验里所有模型用同一个训练长度和学习率计划，数据量不同的点是从同一次训练的中间检查点取的，而学习率还没降下来的中间检查点，损失偏高；Chinchilla 让学习率计划的长度和每次训练的 token 数匹配，每个点都是真正训完的。这样测出来，数据的作用比 Kaplan 估的大得多。

### 一个两项相加的公式

他们把损失写成三项：

$$
L(N, D) = E + \frac{A}{N^{\alpha}} + \frac{B}{D^{\beta}}
$$

一项一项看：

- $E$：**再大的模型、再多的数据也去不掉的损失**。语言本身有随机性，下一个词本来就不唯一。
- $\frac{A}{N^{\alpha}}$：**模型太小的代价**。参数越多，这一项越小。
- $\frac{B}{D^{\beta}}$：**数据太少的代价**。数据越多，这一项越小。

这一讲用的系数是 2024 年 Besiroglu 等人从原论文的图里重新取点拟合出来的：

$$
\begin{aligned}
&E = 1.8172, \quad A = 482.01, \\
&B = 2085.43, \quad \alpha = 0.3478, \\
&\beta = 0.3658
\end{aligned}
$$

原论文给的是另一组（$E = 1.69$，$A = 406.4$，$B = 410.7$，$\alpha = 0.34$，$\beta = 0.28$）。重新拟合的原因是：原来那组系数推出的最优比例约是每个参数 59 个 token，和论文自己另外两种方法得出的约 20 对不上；重新拟合后的这组和 20 一致。实验 03 可以在两组之间切换。

和 Kaplan 一样，这些数只在他们的数据和分词器上成立，用来看形状和比例，不用来预测别的模型的损失值。

### 算力固定，只剩一个变量

现在固定算力。取 Chinchilla 论文里的预算 $C = 5.76 \times 10^{23}$ FLOPs，这也是 DeepMind 前一个模型 Gopher（280B）的训练算力。

由 $C = 6ND$，一旦选定 $N$，数据量就定了：

$$
D = \frac{C}{6N}
$$

于是 $L$ 只剩一个变量 $N$。拿三种花法来算：

**花法一：280B 参数**（Gopher 的大小）。数据量：

$$
D = \frac{5.76 \times 10^{23}}{6 \times 2.8 \times 10^{11}} = 3.43 \times 10^{11}
$$

每个参数只分到 1.2 个 token。两项代价分别是 $A / N^{\alpha} = 0.0503$、$B / D^{\beta} = 0.1258$，损失 $L = 1.8172 + 0.0503 + 0.1258 = 1.9933$。模型那一项已经很小，数据那一项是大头。

**花法二：70B 参数**（Chinchilla 的大小）。$D = 1.37 \times 10^{12}$，每个参数 20 个 token。两项分别是 0.0815、0.0758，几乎一样大，损失 $L = 1.9745$。

**花法三：8B 参数**。$D = 1.20 \times 10^{13}$，每个参数 1500 个 token。数据那一项降到 0.0343，但模型那一项涨到 0.1733，损失 $L = 2.0247$。

<figure class="fig">
<svg viewBox="0 0 480 262" role="img" aria-label="算力固定时，损失随参数量的 U 形曲线">
<line x1="54.0" y1="218.0" x2="450.0" y2="218.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="54.0" y1="22.0" x2="54.0" y2="218.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="49.0" y1="218.0" x2="54.0" y2="218.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="46.0" y="223.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.0</text><line x1="49.0" y1="163.6" x2="54.0" y2="163.6" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="46.0" y="168.6" font-size="14" text-anchor="end" style="fill:var(--muted)">0.1</text><line x1="54.0" y1="163.6" x2="450.0" y2="163.6" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="49.0" y1="109.1" x2="54.0" y2="109.1" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="46.0" y="114.1" font-size="14" text-anchor="end" style="fill:var(--muted)">0.2</text><line x1="54.0" y1="109.1" x2="450.0" y2="109.1" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="49.0" y1="54.7" x2="54.0" y2="54.7" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="46.0" y="59.7" font-size="14" text-anchor="end" style="fill:var(--muted)">0.3</text><line x1="54.0" y1="54.7" x2="450.0" y2="54.7" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="136.1" y1="218.0" x2="136.1" y2="223.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="136.1" y="239.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10B</text><line x1="293.0" y1="218.0" x2="293.0" y2="223.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="293.0" y="239.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">100B</text><line x1="450.0" y1="218.0" x2="450.0" y2="223.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="450.0" y="239.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1T</text><path d="M54.0 85.3 L56.5 87.0 L59.0 88.6 L61.4 90.2 L63.9 91.8 L66.4 93.4 L68.8 95.0 L71.3 96.5 L73.8 98.1 L76.3 99.6 L78.8 101.0 L81.2 102.5 L83.7 104.0 L86.2 105.4 L88.7 106.8 L91.1 108.2 L93.6 109.6 L96.1 110.9 L98.5 112.3 L101.0 113.6 L103.5 114.9 L106.0 116.2 L108.5 117.5 L110.9 118.7 L113.4 120.0 L115.9 121.2 L118.3 122.4 L120.8 123.6 L123.3 124.8 L125.8 126.0 L128.2 127.1 L130.7 128.3 L133.2 129.4 L135.7 130.5 L138.2 131.6 L140.6 132.7 L143.1 133.8 L145.6 134.8 L148.0 135.9 L150.5 136.9 L153.0 137.9 L155.5 138.9 L158.0 139.9 L160.4 140.9 L162.9 141.9 L165.4 142.8 L167.8 143.8 L170.3 144.7 L172.8 145.6 L175.3 146.5 L177.8 147.4 L180.2 148.3 L182.7 149.2 L185.2 150.0 L187.7 150.9 L190.1 151.7 L192.6 152.6 L195.1 153.4 L197.5 154.2 L200.0 155.0 L202.5 155.8 L205.0 156.6 L207.5 157.3 L209.9 158.1 L212.4 158.9 L214.9 159.6 L217.3 160.3 L219.8 161.1 L222.3 161.8 L224.8 162.5 L227.2 163.2 L229.7 163.9 L232.2 164.5 L234.7 165.2 L237.2 165.9 L239.6 166.5 L242.1 167.2 L244.6 167.8 L247.0 168.4 L249.5 169.1 L252.0 169.7 L254.5 170.3 L257.0 170.9 L259.4 171.5 L261.9 172.1 L264.4 172.6 L266.8 173.2 L269.3 173.8 L271.8 174.3 L274.3 174.9 L276.8 175.4 L279.2 175.9 L281.7 176.5 L284.2 177.0 L286.7 177.5 L289.1 178.0 L291.6 178.5 L294.1 179.0 L296.5 179.5 L299.0 180.0 L301.5 180.5 L304.0 180.9 L306.5 181.4 L308.9 181.9 L311.4 182.3 L313.9 182.8 L316.3 183.2 L318.8 183.6 L321.3 184.1 L323.8 184.5 L326.2 184.9 L328.7 185.3 L331.2 185.7 L333.7 186.1 L336.2 186.5 L338.6 186.9 L341.1 187.3 L343.6 187.7 L346.0 188.1 L348.5 188.5 L351.0 188.8 L353.5 189.2 L356.0 189.6 L358.4 189.9 L360.9 190.3 L363.4 190.6 L365.8 191.0 L368.3 191.3 L370.8 191.6 L373.3 192.0 L375.8 192.3 L378.2 192.6 L380.7 192.9 L383.2 193.3 L385.7 193.6 L388.1 193.9 L390.6 194.2 L393.1 194.5 L395.5 194.8 L398.0 195.1 L400.5 195.3 L403.0 195.6 L405.5 195.9 L407.9 196.2 L410.4 196.5 L412.9 196.7 L415.3 197.0 L417.8 197.3 L420.3 197.5 L422.8 197.8 L425.2 198.0 L427.7 198.3 L430.2 198.5 L432.7 198.8 L435.2 199.0 L437.6 199.3 L440.1 199.5 L442.6 199.7 L445.0 200.0 L447.5 200.2 L450.0 200.4" style="stroke:var(--muted);stroke-width:2;stroke-dasharray:5 4;fill:none"/><path d="M54.0 205.0 L56.5 204.8 L59.0 204.6 L61.4 204.4 L63.9 204.3 L66.4 204.1 L68.8 203.9 L71.3 203.7 L73.8 203.5 L76.3 203.3 L78.8 203.1 L81.2 202.9 L83.7 202.7 L86.2 202.5 L88.7 202.3 L91.1 202.1 L93.6 201.9 L96.1 201.7 L98.5 201.5 L101.0 201.2 L103.5 201.0 L106.0 200.8 L108.5 200.5 L110.9 200.3 L113.4 200.1 L115.9 199.8 L118.3 199.6 L120.8 199.3 L123.3 199.1 L125.8 198.8 L128.2 198.6 L130.7 198.3 L133.2 198.1 L135.7 197.8 L138.2 197.5 L140.6 197.3 L143.1 197.0 L145.6 196.7 L148.0 196.4 L150.5 196.1 L153.0 195.8 L155.5 195.5 L158.0 195.2 L160.4 194.9 L162.9 194.6 L165.4 194.3 L167.8 194.0 L170.3 193.7 L172.8 193.3 L175.3 193.0 L177.8 192.7 L180.2 192.3 L182.7 192.0 L185.2 191.7 L187.7 191.3 L190.1 190.9 L192.6 190.6 L195.1 190.2 L197.5 189.8 L200.0 189.5 L202.5 189.1 L205.0 188.7 L207.5 188.3 L209.9 187.9 L212.4 187.5 L214.9 187.1 L217.3 186.7 L219.8 186.3 L222.3 185.8 L224.8 185.4 L227.2 185.0 L229.7 184.5 L232.2 184.1 L234.7 183.6 L237.2 183.2 L239.6 182.7 L242.1 182.2 L244.6 181.8 L247.0 181.3 L249.5 180.8 L252.0 180.3 L254.5 179.8 L257.0 179.3 L259.4 178.8 L261.9 178.2 L264.4 177.7 L266.8 177.2 L269.3 176.6 L271.8 176.1 L274.3 175.5 L276.8 174.9 L279.2 174.4 L281.7 173.8 L284.2 173.2 L286.7 172.6 L289.1 172.0 L291.6 171.4 L294.1 170.7 L296.5 170.1 L299.0 169.5 L301.5 168.8 L304.0 168.2 L306.5 167.5 L308.9 166.8 L311.4 166.1 L313.9 165.4 L316.3 164.7 L318.8 164.0 L321.3 163.3 L323.8 162.6 L326.2 161.8 L328.7 161.1 L331.2 160.3 L333.7 159.6 L336.2 158.8 L338.6 158.0 L341.1 157.2 L343.6 156.4 L346.0 155.5 L348.5 154.7 L351.0 153.9 L353.5 153.0 L356.0 152.1 L358.4 151.3 L360.9 150.4 L363.4 149.5 L365.8 148.5 L368.3 147.6 L370.8 146.7 L373.3 145.7 L375.8 144.8 L378.2 143.8 L380.7 142.8 L383.2 141.8 L385.7 140.8 L388.1 139.7 L390.6 138.7 L393.1 137.6 L395.5 136.5 L398.0 135.5 L400.5 134.3 L403.0 133.2 L405.5 132.1 L407.9 130.9 L410.4 129.8 L412.9 128.6 L415.3 127.4 L417.8 126.2 L420.3 125.0 L422.8 123.7 L425.2 122.5 L427.7 121.2 L430.2 119.9 L432.7 118.6 L435.2 117.3 L437.6 115.9 L440.1 114.5 L442.6 113.2 L445.0 111.8 L447.5 110.3 L450.0 108.9" style="stroke:var(--warn);stroke-width:2;stroke-dasharray:5 4;fill:none"/><path d="M54.0 72.3 L56.5 73.8 L59.0 75.2 L61.4 76.7 L63.9 78.1 L66.4 79.5 L68.8 80.9 L71.3 82.2 L73.8 83.6 L76.3 84.9 L78.8 86.2 L81.2 87.4 L83.7 88.7 L86.2 89.9 L88.7 91.1 L91.1 92.3 L93.6 93.5 L96.1 94.6 L98.5 95.7 L101.0 96.8 L103.5 97.9 L106.0 99.0 L108.5 100.0 L110.9 101.1 L113.4 102.1 L115.9 103.1 L118.3 104.0 L120.8 105.0 L123.3 105.9 L125.8 106.8 L128.2 107.7 L130.7 108.6 L133.2 109.5 L135.7 110.3 L138.2 111.2 L140.6 112.0 L143.1 112.8 L145.6 113.5 L148.0 114.3 L150.5 115.0 L153.0 115.8 L155.5 116.5 L158.0 117.2 L160.4 117.8 L162.9 118.5 L165.4 119.1 L167.8 119.8 L170.3 120.4 L172.8 121.0 L175.3 121.5 L177.8 122.1 L180.2 122.7 L182.7 123.2 L185.2 123.7 L187.7 124.2 L190.1 124.7 L192.6 125.2 L195.1 125.6 L197.5 126.1 L200.0 126.5 L202.5 126.9 L205.0 127.3 L207.5 127.7 L209.9 128.0 L212.4 128.4 L214.9 128.7 L217.3 129.0 L219.8 129.3 L222.3 129.6 L224.8 129.9 L227.2 130.2 L229.7 130.4 L232.2 130.6 L234.7 130.9 L237.2 131.1 L239.6 131.2 L242.1 131.4 L244.6 131.6 L247.0 131.7 L249.5 131.9 L252.0 132.0 L254.5 132.1 L257.0 132.2 L259.4 132.2 L261.9 132.3 L264.4 132.3 L266.8 132.4 L269.3 132.4 L271.8 132.4 L274.3 132.4 L276.8 132.4 L279.2 132.3 L281.7 132.3 L284.2 132.2 L286.7 132.1 L289.1 132.0 L291.6 131.9 L294.1 131.8 L296.5 131.6 L299.0 131.5 L301.5 131.3 L304.0 131.1 L306.5 130.9 L308.9 130.7 L311.4 130.5 L313.9 130.2 L316.3 129.9 L318.8 129.7 L321.3 129.4 L323.8 129.1 L326.2 128.8 L328.7 128.4 L331.2 128.1 L333.7 127.7 L336.2 127.3 L338.6 126.9 L341.1 126.5 L343.6 126.1 L346.0 125.6 L348.5 125.2 L351.0 124.7 L353.5 124.2 L356.0 123.7 L358.4 123.2 L360.9 122.6 L363.4 122.1 L365.8 121.5 L368.3 120.9 L370.8 120.3 L373.3 119.7 L375.8 119.1 L378.2 118.4 L380.7 117.7 L383.2 117.0 L385.7 116.3 L388.1 115.6 L390.6 114.9 L393.1 114.1 L395.5 113.3 L398.0 112.5 L400.5 111.7 L403.0 110.9 L405.5 110.0 L407.9 109.1 L410.4 108.2 L412.9 107.3 L415.3 106.4 L417.8 105.5 L420.3 104.5 L422.8 103.5 L425.2 102.5 L427.7 101.5 L430.2 100.4 L432.7 99.4 L435.2 98.3 L437.6 97.2 L440.1 96.0 L442.6 94.9 L445.0 93.7 L447.5 92.5 L450.0 91.3" style="stroke:var(--accent);stroke-width:3;fill:none"/><text x="442.8" y="189.7" font-size="14" text-anchor="end" style="fill:var(--muted)">模型太小</text><text x="60.5" y="194.5" font-size="14" text-anchor="start" style="fill:var(--warn)">数据太少</text><circle cx="363.2" cy="122.1" r="5" style="fill:var(--accent)"/><text x="363.2" y="110.1" font-size="14" text-anchor="middle" style="fill:var(--fg)">Gopher 280B</text><circle cx="268.7" cy="132.4" r="5" style="fill:var(--accent)"/><text x="268.7" y="120.4" font-size="14" text-anchor="middle" style="fill:var(--fg)">Chinchilla 70B</text><circle cx="120.9" cy="105.0" r="5" style="fill:var(--accent)"/><text x="120.9" y="93.0" font-size="14" text-anchor="middle" style="fill:var(--fg)">8B</text><text x="14.0" y="14.0" font-size="14" text-anchor="start" style="fill:var(--muted)"><tspan font-style="italic">L</tspan> − <tspan font-style="italic">E</tspan></text><text x="252.0" y="254.0" font-size="14" text-anchor="middle" style="fill:var(--muted)"><tspan font-style="italic">N</tspan>（对数刻度）</text>
</svg>
<figcaption>图 5　算力固定为 Gopher 的预算 5.76 × 10<sup>23</sup> FLOPs。横轴是参数量 <i>N</i>，数据量随之定为 <i>D</i> = <i>C</i>/(6<i>N</i>)。灰虚线是「模型太小」的那一项，橙虚线是「数据太少」的那一项，蓝线是两项之和。三个点是三种花法：最低的是 70B。</figcaption>
</figure>

同一笔算力，70B 最好，比 280B 低 0.0189，比 8B 低 0.0503。看图：$N$ 往左，灰线（模型太小）上升；$N$ 往右，橙线（数据太少）上升；两者之和是一个 U 形，谷底在两条线差不多高的地方。

<details class="pause"><summary>停一下：损失差 0.02 听起来很小，值得在意吗？</summary>

值得。在这条曲线上，损失再降 0.02，要多花不少算力。拿 Kaplan 的 $L(C)$ 粗算：$L$ 正比于 $C^{-0.05}$，从 2.00 降到 1.98 是降 1%，算力要乘 $(2.00/1.98)^{1/0.05} \approx 1.22$。也就是说，选错比例相当于白扔了约五分之一的算力。Chinchilla 用 Gopher 四分之一的参数、同样的算力，在 MMLU 上从 60.0% 提高到 67.6%。

</details>

### 求出谷底

谷底就是 $L$ 对 $N$ 的导数等于 0 的地方。先把 $D = C/(6N)$ 代进 $L$，第三项变成：

$$
\frac{B}{D^{\beta}} = B \left(\frac{C}{6}\right)^{-\beta} N^{\beta}
$$

（$D^{-\beta} = (C/6)^{-\beta} N^{\beta}$，因为 $D$ 里的 $N$ 在分母上，取负的幂次后到了分子上。）现在 $L$ 是：

$$
L(N) = E + A\, N^{-\alpha} + B \left(\frac{C}{6}\right)^{-\beta} N^{\beta}
$$

对 $N$ 求导。$E$ 是常数，导数为 0；$N^{-\alpha}$ 的导数是 $-\alpha N^{-\alpha - 1}$；$N^{\beta}$ 的导数是 $\beta N^{\beta - 1}$：

$$
\begin{aligned}
\frac{dL}{dN} = &-\alpha A\, N^{-\alpha-1} \\
&+ \beta B \left(\frac{C}{6}\right)^{-\beta} N^{\beta-1}
\end{aligned}
$$

令它等于 0，把第一项移到右边：

$$
\beta B \left(\frac{C}{6}\right)^{-\beta} N^{\beta-1} = \alpha A\, N^{-\alpha-1}
$$

两边同乘 $N$，再把 $(C/6)^{-\beta} N^{\beta}$ 换回 $D^{-\beta}$：

$$
\beta\, \frac{B}{D^{\beta}} = \alpha\, \frac{A}{N^{\alpha}}
$$

这一行就是谷底的条件，意思很直观：**在最优点，「数据太少的代价」和「模型太小的代价」之比等于 $\alpha : \beta$**。$\alpha$ 和 $\beta$ 差不多大，所以最优点上两项差不多大，就是图 5 里两条虚线相交的附近。验证一下花法二：$0.3658 \times 0.0758$ 和 $0.3478 \times 0.0815$ 都约是 0.028。

再解出 $N$。回到上一行（移项后的那一行），两边同时除以 $N^{\beta - 1}$ 和 $\alpha A$：右边剩下 $N^{-\alpha-1}$ 除以 $N^{\beta-1}$，指数相减；左边剩下 $\frac{\beta B}{\alpha A}(C/6)^{-\beta}$。左右对调写成：

$$
\begin{aligned}
N^{-\alpha-1-(\beta-1)} &= N^{-(\alpha+\beta)} \\
&= \frac{\beta B}{\alpha A} \left(\frac{C}{6}\right)^{-\beta}
\end{aligned}
$$

两边取 $-1/(\alpha+\beta)$ 次方：

$$
N_{\text{opt}} = \left(\frac{\alpha A}{\beta B}\right)^{\frac{1}{\alpha+\beta}} \left(\frac{C}{6}\right)^{\frac{\beta}{\alpha+\beta}}
$$

代入数字。第一个括号：

$$
\begin{aligned}
\frac{\alpha A}{\beta B} &= \frac{0.3478 \times 482.01}{0.3658 \times 2085.43} \\
&= \frac{167.6}{762.8} = 0.2198
\end{aligned}
$$

取 $1/(0.3478 + 0.3658) = 1/0.7136$ 次方，得 0.1196。第二个括号：$C/6 = 9.60 \times 10^{22}$，指数是 $\beta/(\alpha+\beta) = 0.3658/0.7136 = 0.513$，算出来是 $6.039 \times 10^{11}$。相乘：

$$
\begin{aligned}
N_{\text{opt}} &= 0.1196 \times 6.039 \times 10^{11} \\
&= 7.22 \times 10^{10}
\end{aligned}
$$

也就是约 72.2B 参数，对应的数据量 $D = C/(6N) = 1.33 \times 10^{12}$，每个参数 18.4 个 token。Chinchilla 实际选了 70B 参数、1.4 T token，就在这个谷底附近。

### 为什么是「同比例」

看 $N_{\text{opt}}$ 公式里 $C$ 的指数：$\beta/(\alpha+\beta) = 0.513$。数据量 $D = C/(6N)$，它的指数就是 $1 - 0.513 = \alpha/(\alpha+\beta) = 0.487$。两个指数都约等于 0.5：

$$
N_{\text{opt}} \propto C^{0.51}, \qquad D_{\text{opt}} \propto C^{0.49}
$$

算力乘 10，参数乘 $10^{0.513} = 3.26$，数据乘 $10^{0.487} = 3.07$，**两者涨得一样快**，所以它们的比值 $D/N$ 几乎不变，一直在 20 左右。这就是常说的 **Chinchilla 比例：每个参数约 20 个 token**。论文用三种不同方法估，参数的指数分别是 0.50、0.49、0.46，都接近 0.5；Kaplan 的 0.73 偏得很远。

<details class="pause"><summary>停一下：按这个比例，GPT-3 那笔算力（3.14 × 10<sup>23</sup>）应该怎么花？</summary>

每个参数 20 个 token，就是 $D = 20N$。代入 $C = 6ND = 120 N^2$：

$$
\begin{aligned}
N &= \sqrt{\frac{3.14 \times 10^{23}}{120}} \\
&= \sqrt{2.62 \times 10^{21}} \approx 5.1 \times 10^{10}
\end{aligned}
$$

约 51B 参数、1 T token。GPT-3 用了 175B 参数、300B token，参数多了 3 倍多，数据少了 3 倍多。

</details>

## 为什么现在的模型故意「过训练」

Chinchilla 比例回答的是：**只算训练的钱，怎样最省**。但模型训出来是要用的。上线以后，每生成一个 token 都要做一次前向，约 $2N$ 次运算：

- 8B 模型：每 token $2 \times 8.03 \times 10^{9} = 1.61 \times 10^{10}$ 次
- 70B 模型：每 token $2 \times 7.06 \times 10^{10} = 1.41 \times 10^{11}$ 次

70B 每个 token 的推理开销是 8B 的 8.8 倍。一个模型一生要生成几万亿、几十万亿个 token，这笔账很快就超过训练本身。

Meta 在发布 Llama 3 时写道：对 8B 模型，Chinchilla 最优的训练量约是 200B token；但他们一直训到 15 T，8B 和 70B 的效果都还在按对数线性继续提升。8B 每个参数读了 $15 \times 10^{12} / 8.03 \times 10^{9} \approx$ 1868 个 token，是 Chinchilla 比例的 93 倍。

### 把推理算进总账

Sardana 和 Frankle（2023）把这件事写成一个优化问题：**定一个要达到的损失，让「训练 + 推理」的总运算最少**。总运算是：

$$
C_{\text{总}} = \underbrace{6 N D_{\text{训}}}_{\text{训练}} + \underbrace{2 N D_{\text{推}}}_{\text{推理}}
$$

$D_{\text{推}}$ 是模型上线后一共要生成的 token 数。

目标损失取 Llama-3-8B 这个配置（8.03B 参数、15 T token）在上面公式里的值：$L = 2.0218$。对每一个 $N$，从 $L(N, D) = 2.0218$ 反解出需要的训练数据：

$$
D_{\text{训}}(N) = \left(\frac{B}{2.0218 - E - A / N^{\alpha}}\right)^{1/\beta}
$$

（把 $L$ 公式里的 $B/D^{\beta}$ 单独留在一边，再开 $\beta$ 次方。）分母必须大于 0，所以模型至少要 4.96B 参数，小于这个数，读再多的数据也到不了这个损失。然后对 $N$ 逐个试，找总运算最小的那个：

| 一生推理 token 数 | 最省的 $N$ | 训练 token | 每参数 token | 训练运算 | 推理运算 |
| --- | --- | --- | --- | --- | --- |
| 0 | 33.9B | 646B | 19 | 1.31 × 10<sup>23</sup> | 0 |
| $10^{12}$ | 23.3B | 996B | 43 | 1.39 × 10<sup>23</sup> | 4.66 × 10<sup>22</sup> |
| $10^{13}$ | 13.5B | 2.58T | 192 | 2.09 × 10<sup>23</sup> | 2.69 × 10<sup>23</sup> |
| $10^{14}$ | 8.75B | 9.97T | 1,139 | 5.23 × 10<sup>23</sup> | 1.75 × 10<sup>24</sup> |

<figure class="fig">
<svg viewBox="0 0 480 244" role="img" aria-label="把推理算进总成本后，最省的模型大小随推理量变化">
<line x1="60.0" y1="196.0" x2="440.0" y2="196.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="60.0" y1="26.0" x2="60.0" y2="196.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="60.0" y1="196.0" x2="60.0" y2="201.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="60.0" y="217.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">10</tspan></text><line x1="136.0" y1="196.0" x2="136.0" y2="201.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="136.0" y="217.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">11</tspan></text><line x1="212.0" y1="196.0" x2="212.0" y2="201.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="212.0" y="217.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">12</tspan></text><line x1="288.0" y1="196.0" x2="288.0" y2="201.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="288.0" y="217.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">13</tspan></text><line x1="364.0" y1="196.0" x2="364.0" y2="201.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="364.0" y="217.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">14</tspan></text><line x1="440.0" y1="196.0" x2="440.0" y2="201.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="440.0" y="217.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">15</tspan></text><line x1="55.0" y1="196.0" x2="60.0" y2="196.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="52.0" y="201.0" font-size="14" text-anchor="end" style="fill:var(--muted)">5B</text><line x1="55.0" y1="144.8" x2="60.0" y2="144.8" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="52.0" y="149.8" font-size="14" text-anchor="end" style="fill:var(--muted)">10B</text><line x1="55.0" y1="93.6" x2="60.0" y2="93.6" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="52.0" y="98.6" font-size="14" text-anchor="end" style="fill:var(--muted)">20B</text><line x1="55.0" y1="26.0" x2="60.0" y2="26.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="52.0" y="31.0" font-size="14" text-anchor="end" style="fill:var(--muted)">50B</text><path d="M60.0 55.2 L69.5 55.5 L79.0 55.6 L88.5 56.0 L98.0 56.4 L107.5 56.9 L117.0 57.5 L126.5 58.4 L136.0 59.6 L145.5 61.0 L155.0 62.8 L164.5 64.9 L174.0 67.5 L183.5 70.5 L193.0 74.1 L202.5 78.1 L212.0 82.4 L221.5 87.1 L231.0 92.1 L240.5 97.2 L250.0 102.4 L259.5 107.6 L269.0 112.9 L278.5 118.0 L288.0 122.8 L297.5 127.5 L307.0 132.1 L316.5 136.5 L326.0 140.5 L335.5 144.4 L345.0 148.1 L354.5 151.5 L364.0 154.7 L373.5 157.6 L383.0 160.4 L392.5 163.1 L402.0 165.5 L411.5 167.7 L421.0 169.9 L430.5 171.8 L440.0 173.6" style="stroke:var(--accent);stroke-width:3;fill:none"/><line x1="60.0" y1="161.0" x2="440.0" y2="161.0" style="stroke:var(--warn);stroke-width:1.4;stroke-dasharray:5 4;fill:none"/><text x="66.0" y="154.0" font-size="14" text-anchor="start" style="fill:var(--warn)">Llama-3-8B</text><circle cx="212.0" cy="82.4" r="5" style="fill:var(--accent)"/><text x="220.0" y="73.4" font-size="13" text-anchor="start" style="fill:var(--fg)">23.3B · 43 个/参数</text><circle cx="288.0" cy="122.8" r="5" style="fill:var(--accent)"/><text x="296.0" y="113.8" font-size="13" text-anchor="start" style="fill:var(--fg)">13.5B · 192 个/参数</text><circle cx="364.0" cy="154.7" r="5" style="fill:var(--accent)"/><text x="356.0" y="138.7" font-size="13" text-anchor="end" style="fill:var(--fg)">8.7B · 1,139 个/参数</text><text x="250.0" y="236.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">一生要服务的推理 token 数</text><text x="12.0" y="16.0" font-size="14" text-anchor="start" style="fill:var(--muted)">最省的 N</text>
</svg>
<figcaption>图 6　目标是同一个损失（Llama-3-8B 的 2.0218）。横轴是模型上线后一共要生成的 token 数，纵轴是训练 + 推理总运算最少的那个模型的大小。推理越多，最优模型越小、每个参数分到的训练 token 越多；到 10<sup>14</sup> 时最优就落在 8B 附近。</figcaption>
</figure>

读这张表：

- 第一行不算推理，最省的是 33.9B 参数、每参数 19 个 token，就是 Chinchilla 比例。达到同一个损失，Llama-3-8B 的训练运算是它的 5.5 倍。**只看训练，过训练很浪费。**
- 推理越多，最省的模型越小，训练数据越多。到 $10^{14}$ 个推理 token（比如每天生成 1000 亿 token、用上近 3 年），最省的是 8.75B、每参数 1,139 个 token，已经和 Llama-3-8B 差不多；8B 的总运算只比最优多 2.4%。

所以过训练不是不懂 Chinchilla，而是**把推理也算进去之后的最优**。小模型还有算力之外的好处：一张卡就放得下、响应快，这些在上面的式子里都没算。

代价是：过训练的收益递减。8B 从 Chinchilla 的 0.2 T 训到 15 T，数据多了 75 倍，损失只降一点点；而且好的训练数据总量是有限的，不能无限往上加。

## 涌现能力：真的，还是度量造成的

前面说损失随规模**平稳**下降。但人们在下游任务上常看到另一种曲线：小模型一直接近 0 分，到某个规模突然跳起来。这叫**涌现能力**（emergent abilities）。

### 一方：Wei 等人 2022

Wei 等人把涌现定义为：**小模型没有、大模型有的能力，而且不能从小模型的表现外推出来**。他们收集了几十个例子。比如 GPT-3 做三位数加减法，训练算力在约 $2.3 \times 10^{22}$ FLOPs（13B 参数）以下时接近随机，过了这个点准确率明显上升；思维链提示（让模型先写推理再答）对数学应用题的帮助，要到约 $10^{23}$ FLOPs 的模型才出现，更小的模型用了也没有帮助。

他们的论点是：如果能力会突然出现，那么只看小模型就无法预知大模型会做什么，这对研究和安全都很重要。

### 另一方：Schaeffer 等人 2023

Schaeffer、Miranda 和 Koyejo 的论文题目就是问题：《大模型的涌现能力是海市蜃楼吗？》他们的看法是：**突变常常不是模型造成的，而是打分方式造成的**。

先看一个最简单的例子。答案有 5 个 token，按「完全对才算对」（exact match）打分。设模型每个 token 猜对的概率是 $p$，而且各 token 相互独立，那么整题全对的概率是

$$
P(\text{全对}) = p^{5}
$$

假设 $p$ 随模型变大平稳上升（下面是示意数字）：

| 参数量 | 每个 token 对的概率 $p$ | 5 个全对 $p^5$ |
| --- | --- | --- |
| $10^{8}$ | 0.301 | 0.002 |
| $10^{9}$ | 0.736 | 0.216 |
| $10^{10}$ | 0.925 | 0.676 |
| $10^{11}$ | 0.980 | 0.905 |

算一行：$0.736^5 = 0.736 \times 0.736 \times 0.736 \times 0.736 \times 0.736 = 0.216$。$p$ 从 30.1% 到 73.6% 涨了一大截，但 $p^5$ 从 0.2% 只到 21.6%；等 $p$ 到了 92.5%，$p^5$ 才到 67.6%。画在对数坐标上：

<figure class="fig">
<svg viewBox="0 0 480 248" role="img" aria-label="同一组输出用两种度量：每个 token 的准确率平滑上升，整题全对看起来突然出现">
<line x1="54.0" y1="202.0" x2="450.0" y2="202.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="54.0" y1="22.0" x2="54.0" y2="202.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="49.0" y1="202.0" x2="54.0" y2="202.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="46.0" y="207.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0%</text><line x1="49.0" y1="112.0" x2="54.0" y2="112.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="46.0" y="117.0" font-size="14" text-anchor="end" style="fill:var(--muted)">50%</text><line x1="54.0" y1="112.0" x2="450.0" y2="112.0" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="49.0" y1="22.0" x2="54.0" y2="22.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="46.0" y="27.0" font-size="14" text-anchor="end" style="fill:var(--muted)">100%</text><line x1="54.0" y1="22.0" x2="450.0" y2="22.0" style="stroke:var(--line);stroke-width:1;fill:none"/><line x1="54.0" y1="202.0" x2="54.0" y2="207.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="54.0" y="223.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">8</tspan></text><line x1="153.0" y1="202.0" x2="153.0" y2="207.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="153.0" y="223.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">9</tspan></text><line x1="252.0" y1="202.0" x2="252.0" y2="207.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="252.0" y="223.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">10</tspan></text><line x1="351.0" y1="202.0" x2="351.0" y2="207.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="351.0" y="223.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">11</tspan></text><line x1="450.0" y1="202.0" x2="450.0" y2="207.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="450.0" y="223.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10<tspan font-size="10.1" dy="-7">12</tspan></text><path d="M54.0 147.8 L56.5 145.6 L59.0 143.3 L61.4 141.1 L63.9 138.8 L66.4 136.6 L68.9 134.3 L71.3 132.0 L73.8 129.8 L76.3 127.5 L78.8 125.3 L81.2 123.1 L83.7 120.9 L86.2 118.7 L88.6 116.5 L91.1 114.3 L93.6 112.2 L96.1 110.1 L98.5 108.0 L101.0 105.9 L103.5 103.9 L106.0 101.8 L108.5 99.8 L110.9 97.9 L113.4 96.0 L115.9 94.1 L118.4 92.2 L120.8 90.4 L123.3 88.6 L125.8 86.8 L128.2 85.0 L130.7 83.3 L133.2 81.7 L135.7 80.0 L138.1 78.4 L140.6 76.9 L143.1 75.3 L145.6 73.8 L148.0 72.4 L150.5 70.9 L153.0 69.5 L155.5 68.2 L158.0 66.8 L160.4 65.5 L162.9 64.2 L165.4 63.0 L167.9 61.8 L170.3 60.6 L172.8 59.5 L175.3 58.3 L177.8 57.2 L180.2 56.2 L182.7 55.1 L185.2 54.1 L187.6 53.2 L190.1 52.2 L192.6 51.3 L195.1 50.4 L197.5 49.5 L200.0 48.7 L202.5 47.8 L205.0 47.0 L207.5 46.2 L209.9 45.5 L212.4 44.8 L214.9 44.0 L217.4 43.3 L219.8 42.7 L222.3 42.0 L224.8 41.4 L227.2 40.8 L229.7 40.2 L232.2 39.6 L234.7 39.0 L237.1 38.5 L239.6 38.0 L242.1 37.5 L244.6 37.0 L247.0 36.5 L249.5 36.0 L252.0 35.6 L254.5 35.1 L257.0 34.7 L259.4 34.3 L261.9 33.9 L264.4 33.5 L266.9 33.1 L269.3 32.8 L271.8 32.4 L274.3 32.1 L276.8 31.7 L279.2 31.4 L281.7 31.1 L284.2 30.8 L286.6 30.5 L289.1 30.3 L291.6 30.0 L294.1 29.7 L296.5 29.5 L299.0 29.2 L301.5 29.0 L304.0 28.8 L306.5 28.5 L308.9 28.3 L311.4 28.1 L313.9 27.9 L316.4 27.7 L318.8 27.5 L321.3 27.3 L323.8 27.2 L326.2 27.0 L328.7 26.8 L331.2 26.7 L333.7 26.5 L336.1 26.4 L338.6 26.2 L341.1 26.1 L343.6 25.9 L346.0 25.8 L348.5 25.7 L351.0 25.6 L353.5 25.4 L356.0 25.3 L358.4 25.2 L360.9 25.1 L363.4 25.0 L365.9 24.9 L368.3 24.8 L370.8 24.7 L373.3 24.6 L375.8 24.5 L378.2 24.5 L380.7 24.4 L383.2 24.3 L385.6 24.2 L388.1 24.1 L390.6 24.1 L393.1 24.0 L395.5 23.9 L398.0 23.9 L400.5 23.8 L403.0 23.7 L405.5 23.7 L407.9 23.6 L410.4 23.6 L412.9 23.5 L415.4 23.5 L417.8 23.4 L420.3 23.4 L422.8 23.3 L425.2 23.3 L427.7 23.2 L430.2 23.2 L432.7 23.2 L435.1 23.1 L437.6 23.1 L440.1 23.1 L442.6 23.0 L445.0 23.0 L447.5 22.9 L450.0 22.9" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><path d="M54.0 201.6 L56.5 201.5 L59.0 201.3 L61.4 201.2 L63.9 201.0 L66.4 200.9 L68.9 200.6 L71.3 200.4 L73.8 200.1 L76.3 199.8 L78.8 199.5 L81.2 199.1 L83.7 198.7 L86.2 198.2 L88.6 197.6 L91.1 197.1 L93.6 196.4 L96.1 195.7 L98.5 195.0 L101.0 194.2 L103.5 193.3 L106.0 192.4 L108.5 191.4 L110.9 190.3 L113.4 189.2 L115.9 188.0 L118.4 186.8 L120.8 185.5 L123.3 184.1 L125.8 182.7 L128.2 181.2 L130.7 179.6 L133.2 178.0 L135.7 176.3 L138.1 174.6 L140.6 172.8 L143.1 170.9 L145.6 169.0 L148.0 167.1 L150.5 165.1 L153.0 163.1 L155.5 161.1 L158.0 159.0 L160.4 156.9 L162.9 154.7 L165.4 152.6 L167.9 150.4 L170.3 148.2 L172.8 145.9 L175.3 143.7 L177.8 141.5 L180.2 139.2 L182.7 136.9 L185.2 134.7 L187.6 132.4 L190.1 130.2 L192.6 127.9 L195.1 125.7 L197.5 123.5 L200.0 121.2 L202.5 119.0 L205.0 116.9 L207.5 114.7 L209.9 112.5 L212.4 110.4 L214.9 108.3 L217.4 106.2 L219.8 104.2 L222.3 102.2 L224.8 100.2 L227.2 98.2 L229.7 96.3 L232.2 94.4 L234.7 92.5 L237.1 90.7 L239.6 88.9 L242.1 87.1 L244.6 85.3 L247.0 83.6 L249.5 82.0 L252.0 80.3 L254.5 78.7 L257.0 77.1 L259.4 75.6 L261.9 74.1 L264.4 72.6 L266.9 71.2 L269.3 69.8 L271.8 68.4 L274.3 67.0 L276.8 65.7 L279.2 64.5 L281.7 63.2 L284.2 62.0 L286.6 60.8 L289.1 59.6 L291.6 58.5 L294.1 57.4 L296.5 56.4 L299.0 55.3 L301.5 54.3 L304.0 53.3 L306.5 52.4 L308.9 51.4 L311.4 50.5 L313.9 49.7 L316.4 48.8 L318.8 48.0 L321.3 47.2 L323.8 46.4 L326.2 45.6 L328.7 44.9 L331.2 44.2 L333.7 43.5 L336.1 42.8 L338.6 42.1 L341.1 41.5 L343.6 40.9 L346.0 40.3 L348.5 39.7 L351.0 39.1 L353.5 38.6 L356.0 38.1 L358.4 37.5 L360.9 37.0 L363.4 36.6 L365.9 36.1 L368.3 35.6 L370.8 35.2 L373.3 34.8 L375.8 34.4 L378.2 34.0 L380.7 33.6 L383.2 33.2 L385.6 32.8 L388.1 32.5 L390.6 32.1 L393.1 31.8 L395.5 31.5 L398.0 31.2 L400.5 30.9 L403.0 30.6 L405.5 30.3 L407.9 30.0 L410.4 29.8 L412.9 29.5 L415.4 29.3 L417.8 29.0 L420.3 28.8 L422.8 28.6 L425.2 28.4 L427.7 28.1 L430.2 27.9 L432.7 27.7 L435.1 27.6 L437.6 27.4 L440.1 27.2 L442.6 27.0 L445.0 26.9 L447.5 26.7 L450.0 26.5" style="stroke:var(--warn);stroke-width:3;fill:none"/><text x="145.0" y="63.5" font-size="14" text-anchor="end" style="fill:var(--accent)">每个 token 对</text><text x="210.2" y="137.1" font-size="14" text-anchor="start" style="fill:var(--warn)">5 个 token 全对</text><text x="252.0" y="240.0" font-size="14" text-anchor="middle" style="fill:var(--muted)"><tspan font-style="italic">N</tspan>（对数刻度，示意）</text>
</svg>
<figcaption>图 7　同一组模型、同一批输出（示意数字）。蓝线：每个答案 token 猜对的概率，随规模平滑上升。橙线：5 个 token 全对才算对，即 <i>p</i><sup>5</sup>；小模型时几乎是 0，到某个规模附近才「突然」升起来。</figcaption>
</figure>

模型本身每一步都在平稳变好，只是 $p^5$ 这种「乘起来」的打分，把前面的进步压在 0 附近，到后面才一起显出来。

他们用三类证据支持这个看法：

1. 在 BIG-Bench 里被报告为涌现的任务中，超过 92% 用的是两种打分之一：选择题对错（Multiple Choice Grade）或完全匹配（Exact String Match）。这两种打分都是不连续或非线性的。
2. 用 InstructGPT/GPT-3 系列（350M 到 175B）做两位数乘法、四位数加法，用准确率看像涌现；换成 token 编辑距离（错了几个 token，随错误率线性变化）看，同一批输出是平稳上升的。
3. 反过来，选一个本来平稳的视觉任务，故意用非线性的打分，也能「造」出涌现曲线。

### 两边都对了一部分

Schaeffer 等人说明了：**很多看上去的突变，换一种连续的度量就消失了**，所以「能力突然出现、无法预测」的说法要打折扣。

但问题没有完全解决：

- 用户关心的常常就是「完全对」：算术题差一位就是错，代码差一个字符就跑不起来。用连续指标看是平稳的，不等于用户体验也是平稳的。Wei 等人也写过，同样的任务上交叉熵损失在小模型阶段就在下降，只是被准确率这样的指标盖住了。
- Du 等人（2024）换了一个角度：不按参数量，按**预训练损失**排模型。他们发现有些任务即使用连续指标打分，也要等预训练损失降到某个阈值以下才离开随机水平；损失相同的模型，不论参数和数据怎么配，下游表现都差不多。

比较稳妥的说法是：**预训练损失随规模平稳下降，这一点是可预测的；某些下游能力在损失降到一定程度后才变得可用，用什么指标去看，会大大影响它显得有多「突然」。**

## 用公开数字核算一遍

最后把几个公开了数字的模型放在一起，用 $6ND$ 算一遍，和官方给的数对照。「有效利用率」是用 $6ND$ 除以「卡时 × 3600 × 单卡峰值」反推出来的平均值（V100 的 FP16 峰值按 125 TFLOPS，H100 的 BF16 按 989.5 TFLOPS）。

| 模型 | $N$ | $D$ | 每参数 token | $6ND$ | 官方报告的 $C$ | 训练卡时 | 有效利用率 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-3 | 175B | 300B | 1.7 | $3.15 \times 10^{23}$ | $3.14 \times 10^{23}$ | 3.55M V100 | 20% |
| Gopher | 280B | 300B | 1.1 | $5.04 \times 10^{23}$ | $5.76 \times 10^{23}$ | 未公开（TPU v3） | — |
| Chinchilla | 70B | 1.4T | 20 | $5.88 \times 10^{23}$ | $5.76 \times 10^{23}$ | 未公开（TPU v3/v4） | — |
| Llama-3-8B | 8.03B | 15T | 1,868 | $7.23 \times 10^{23}$ | — | 1.30M H100 | 16% |
| Llama-3-70B | 70.6B | 15T | 212 | $6.35 \times 10^{24}$ | — | 6.40M H100 | 28% |
| Llama-3.1-405B | 405B | 15.6T | 39 | $3.79 \times 10^{25}$ | $3.80 \times 10^{25}$ | 30.84M H100 | 35% |

逐行看：

- **GPT-3**：$6ND$ 和论文给的 $3.14 \times 10^{23}$ 几乎一样。论文没给卡时；Patterson 等人（2021）的表里写的是 10,000 张 V100 训了 14.8 天，乘出来是 3,552,000 卡时（这是我们乘的）。
- **Gopher 与 Chinchilla**：Chinchilla 论文说两者用了同样的算力 $5.76 \times 10^{23}$。Chinchilla 的 $6ND$ 只差 2%。Gopher 的 $6ND$ 少了约 12%，因为论文的算力是按模型结构逐项数出来的（附录里把嵌入、注意力等都算进去），不是用 $6ND$ 估的。两者都在 TPU 上训练，卡时未公开。
- **Llama-3-8B / 70B**：官方模型卡只说「超过 15 T token」和卡时（H100-80GB），没有单独给 $C$。70B 的有效利用率比 8B 高：大模型每张卡上的矩阵更大，通信占比更小。
- **Llama-3.1-405B**：技术报告给的 $3.8 \times 10^{25}$ 和 $6ND$ 一致，用 15.6 T token；卡时 3084 万取自 Llama 3.1 模型卡。反推的 35% 接近报告里的 MFU 38%–43%。

<figure class="fig">
<svg viewBox="0 0 480 290" role="img" aria-label="公开模型的参数量与训练 token 数">
<line x1="60.0" y1="242.0" x2="450.0" y2="242.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="60.0" y1="22.0" x2="60.0" y2="242.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><line x1="111.0" y1="242.0" x2="111.0" y2="247.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="111.0" y="263.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10B</text><line x1="280.5" y1="242.0" x2="280.5" y2="247.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="280.5" y="263.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">100B</text><line x1="450.0" y1="242.0" x2="450.0" y2="247.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="450.0" y="263.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1T</text><line x1="55.0" y1="242.0" x2="60.0" y2="242.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="52.0" y="247.0" font-size="14" text-anchor="end" style="fill:var(--muted)">100B</text><line x1="55.0" y1="153.2" x2="60.0" y2="153.2" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="52.0" y="158.2" font-size="14" text-anchor="end" style="fill:var(--muted)">1T</text><line x1="55.0" y1="64.4" x2="60.0" y2="64.4" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="52.0" y="69.4" font-size="14" text-anchor="end" style="fill:var(--muted)">10T</text><line x1="60.0" y1="242.0" x2="450.0" y2="37.6" style="stroke:var(--ok);stroke-width:1.5;stroke-dasharray:5 4;fill:none"/><line x1="280.5" y1="242.0" x2="450.0" y2="153.2" style="stroke:var(--muted);stroke-width:1.5;stroke-dasharray:5 4;fill:none"/><text x="124.4" y="226.2" font-size="13" text-anchor="start" style="fill:var(--ok)">20 个/参数</text><text x="406.4" y="164.9" font-size="13" text-anchor="end" style="fill:var(--muted)">1 个/参数</text><circle cx="321.7" cy="199.6" r="5.5" style="fill:var(--accent)"/><text x="313.7" y="221.6" font-size="13" text-anchor="end" style="fill:var(--accent)">GPT-3 · 1.7</text><circle cx="356.3" cy="199.6" r="5.5" style="fill:var(--accent)"/><text x="364.3" y="221.6" font-size="13" text-anchor="start" style="fill:var(--accent)">Gopher · 1.1</text><circle cx="254.3" cy="140.2" r="5.5" style="fill:var(--ok)"/><text x="262.3" y="156.2" font-size="13" text-anchor="start" style="fill:var(--ok)">Chinchilla · 20</text><circle cx="94.9" cy="48.7" r="5.5" style="fill:var(--warn)"/><text x="102.9" y="66.7" font-size="13" text-anchor="start" style="fill:var(--warn)">Llama-3-8B · 1,868</text><circle cx="254.9" cy="48.7" r="5.5" style="fill:var(--warn)"/><text x="262.9" y="66.7" font-size="13" text-anchor="start" style="fill:var(--warn)">Llama-3-70B · 212</text><circle cx="383.5" cy="47.2" r="5.5" style="fill:var(--warn)"/><text x="375.5" y="35.2" font-size="13" text-anchor="end" style="fill:var(--warn)">Llama-3.1-405B · 39</text><text x="255.0" y="282.0" font-size="14" text-anchor="middle" style="fill:var(--muted)"><tspan font-style="italic">N</tspan>（参数量）</text><text x="12.0" y="14.0" font-size="14" text-anchor="start" style="fill:var(--muted)"><tspan font-style="italic">D</tspan>（训练 token）</text>
</svg>
<figcaption>图 8　六个公开模型，横轴参数量、纵轴训练 token 数，两个轴都是对数。点旁的数字是每个参数分到的 token。绿虚线是 Chinchilla 的「每参数 20 个」：GPT-3、Gopher 在它下面很远，Llama 3 全在它上面。</figcaption>
</figure>

从图上能看出这几年的变化：2020 年的 GPT-3 和 2021 年的 Gopher 每个参数只读 1–2 个 token，远在 Chinchilla 线下面；2022 年 Chinchilla 回到 20；2024 年的 Llama 3 全部在这条线上面，8B 更是高出近两个数量级。Llama 3 技术报告里，Meta 自己也拟合了一条规模定律，算出 $3.8 \times 10^{25}$ FLOPs 的最优是 402B 参数、16.55 T token，于是旗舰模型选了 405B、15.6 T，约每参数 39 个 token；而 8B 和 70B 这两个要大量部署的模型，则故意训得远超最优。

## 实验里讲了什么

1. **6ND 算力计算器**：拖参数量和训练 token，选显卡和利用率，看总运算、卡时、用多少张卡要训几天；可以直接选 GPT-3、Chinchilla、Llama 3 的配置，和官方卡时对照。
2. **对数坐标下的幂律**：拖指数 $\alpha$，看普通坐标下的弯曲线怎样在对数坐标下变成直线、斜率就是 $-\alpha$，以及参数每乘 10 损失降多少。
3. **给定算力，拖 $N$**：U 形曲线、两项代价、最优的 $N$ 和 $D$、每参数 token 数；改算力看谷底怎么移动，在 Besiroglu 重新拟合和原论文两组系数之间切换。
4. **把推理算进去**：拖一生要生成的 token 数，看训练 + 推理总运算最少的模型怎样变小、每参数 token 数怎样变大。
5. **涌现与度量**：同一组每 token 准确率，分别用「全对」、平均 token 准确率、编辑距离打分；拖答案长度，看「突变」怎么出现和消失。
6. **公开模型散点图**：六个模型的 $N$、$D$，每个点标出每参数 token 数；点一个点看它的 $6ND$、官方算力、卡时和有效利用率。

## 和前后两讲的关系

上一讲预训练讲了模型怎样在海量文本上学会预测下一个 token；这一讲算的是这件事的账：要做多少次运算、要多少卡时、参数和数据怎么配才划算。反向传播那一讲讲的两件事（传梯度给上一层、算参数自己的梯度），在这里就是 $6N$ 里的两个 $2N$。下一讲 LoRA 讲另一笔账：预训练要几十万到几千万卡时，而微调只需要改很少的参数，代价可以小几个数量级。

## 延伸阅读

- Jared Kaplan et al., *Scaling Laws for Neural Language Models* (2020)，幂律与 $C \approx 6N$ 每 token 的出处
- Jordan Hoffmann et al., *Training Compute-Optimal Large Language Models* (2022)，Chinchilla
- Tamay Besiroglu et al., *Chinchilla Scaling: A replication attempt* (2024)，本讲用的拟合系数
- Nikhil Sardana, Jonathan Frankle, *Beyond Chinchilla-Optimal: Accounting for Inference in Language Model Scaling Laws* (2023)
- Jason Wei et al., *Emergent Abilities of Large Language Models* (TMLR 2022)
- Rylan Schaeffer, Brando Miranda, Sanmi Koyejo, *Are Emergent Abilities of Large Language Models a Mirage?* (NeurIPS 2023)
- Zhengxiao Du et al., *Understanding Emergent Abilities of Language Models from the Loss Perspective* (NeurIPS 2024)
- Llama Team, *The Llama 3 Herd of Models* (2024)；Meta Llama 3 / Llama 3.1 模型卡
- David Patterson et al., *Carbon Emissions and Large Neural Network Training* (2021)，GPT-3 的训练硬件与天数
