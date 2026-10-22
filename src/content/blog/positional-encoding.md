---
title: "位置编码与 RoPE：注意力怎么知道谁在前谁在后"
description: "注意力本身看不出词序：把前面的词打乱，算出来的结果一模一样。沿用注意力一讲的四个 token，一步步算过三种补救办法：给每个位置发一个向量、正弦位置编码、把 q 和 k 按位置旋转的 RoPE，推出旋转后的点积只取决于相对距离；最后讲训练长度之外为什么会崩，以及 Llama 3 的 rope_theta 和 rope_scaling。"
pubDate: 2026-10-22
tags: ["Transformer", "位置编码", "RoPE", "长上下文"]
lab: /labs/positional-encoding/
series: ai-mastery
order: 6
---

<!-- 本文由 labs-src/positional-encoding/toy.py 从 article.src.md 生成，图和数字都由脚本算出。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

注意力只比较「谁和谁的内容相关」，词排在第几个，它一点也不知道，所以「我欠你钱」和「你欠我钱」在它眼里差不多。补救的办法是把位置信息塞进去。现在大多数大模型用的是 RoPE：把每个词的 $q$ 和 $k$ 按它所在的位置转一个角度。两个向量都转过之后再做点积，结果只取决于两个词**相隔多远**，不取决于它们各自在第几个位置。

下面沿用注意力一讲的那组小数字，一步一步算出来。

## 第一步：打乱词序，注意力算出来的结果一模一样

先回顾注意力一讲的小例子。句子只有 4 个 token：粮油、店、买了、小米。每个 token 有一个 2 维向量 $x$，用三个矩阵算出查询、键、值：

$$
q = W_Q\,x \qquad k = W_K\,x \qquad v = W_V\,x
$$

$$
W_Q = \begin{pmatrix} 1 & 1 \\ 0 & -1.2 \end{pmatrix}
$$

$$
W_K = \begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}
$$

$$
W_V = \begin{pmatrix} 1 & 0 \\ 0 & 2 \end{pmatrix}
$$

「小米」的查询是 $q = (1.0,\ -0.6)$。它和每个词的 $k$ 做点积得到分数 $s$，除以 $\sqrt{2}$ 再做 softmax 得到份额，最后按份额把各个 $v$ 加起来，加回自己身上，得到 $x' \approx (0.74,\ 1.66)$。

我们从第 0 个开始给位置编号。原来的句子：

| 位置 | token | 分数 $s$ | 份额 |
| --- | --- | --- | --- |
| 0 | 粮油 | 1.600 | 40.8% |
| 1 | 店 | 0.480 | 18.5% |
| 2 | 买了 | 0.080 | 13.9% |
| 3 | 小米 | 1.000 | 26.7% |

现在把前三个词打乱，变成「店 买了 粮油 小米」。这句话已经不通了，可我们照样算一遍。

先看「粮油」的分数。它的 $k$ 只由它自己的 $x$ 算出来：$k = W_K\,x_{\text{粮油}} = (1,\ -1)$。$x_{\text{粮油}}$ 是查表查出来的，只看 token 本身，不看它排第几。所以「粮油」挪到第 2 个位置之后，$k$ 还是 $(1,\ -1)$。「小米」的 $q$ 也没变。点积 $q \cdot k = 1.0 \times 1 + (-0.6) \times (-1) = 1.6$，和原来一样。

另外三个词同理，每个分数都跟着词走，只是换了一行：

| 位置 | token | 分数 $s$ | 份额 |
| --- | --- | --- | --- |
| 0 | 店 | 0.480 | 18.5% |
| 1 | 买了 | 0.080 | 13.9% |
| 2 | 粮油 | 1.600 | 40.8% |
| 3 | 小米 | 1.000 | 26.7% |

最后一步是把 $w \times v$ 加起来。加法不管先加谁、后加谁，结果都一样（$a + b = b + a$），所以 $x'$ 也一模一样：

<figure class="fig">
<svg viewBox="0 0 480 220" role="img" aria-label="两种词序下小米分给每个词的份额">
<text x="20.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">粮油 店 买了 小米</text><text x="260.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">店 买了 粮油 小米</text><text x="72.0" y="55.0" font-size="15" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="80" y="38" width="89.8" height="22" rx="4" style="fill:var(--warn)"/><text x="175.8" y="55.0" font-size="15" text-anchor="start" style="fill:var(--warn)">40.8%</text><text x="72.0" y="93.0" font-size="15" text-anchor="end" style="fill:var(--fg)">店</text><rect x="80" y="76" width="40.7" height="22" rx="4" style="fill:var(--line)"/><text x="126.7" y="93.0" font-size="15" text-anchor="start" style="fill:var(--muted)">18.5%</text><text x="72.0" y="131.0" font-size="15" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="80" y="114" width="30.7" height="22" rx="4" style="fill:var(--line)"/><text x="116.7" y="131.0" font-size="15" text-anchor="start" style="fill:var(--muted)">13.9%</text><text x="72.0" y="169.0" font-size="15" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="80" y="152" width="58.8" height="22" rx="4" style="fill:var(--line)"/><text x="144.8" y="169.0" font-size="15" text-anchor="start" style="fill:var(--muted)">26.7%</text><text x="20.0" y="208.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--accent)">x′ = (0.74, 1.66)</text><text x="312.0" y="55.0" font-size="15" text-anchor="end" style="fill:var(--fg)">店</text><rect x="320" y="38" width="40.7" height="22" rx="4" style="fill:var(--line)"/><text x="366.7" y="55.0" font-size="15" text-anchor="start" style="fill:var(--muted)">18.5%</text><text x="312.0" y="93.0" font-size="15" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="320" y="76" width="30.7" height="22" rx="4" style="fill:var(--line)"/><text x="356.7" y="93.0" font-size="15" text-anchor="start" style="fill:var(--muted)">13.9%</text><text x="312.0" y="131.0" font-size="15" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="320" y="114" width="89.8" height="22" rx="4" style="fill:var(--warn)"/><text x="415.8" y="131.0" font-size="15" text-anchor="start" style="fill:var(--warn)">40.8%</text><text x="312.0" y="169.0" font-size="15" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="320" y="152" width="58.8" height="22" rx="4" style="fill:var(--line)"/><text x="384.8" y="169.0" font-size="15" text-anchor="start" style="fill:var(--muted)">26.7%</text><text x="260.0" y="208.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--accent)">x′ = (0.74, 1.66)</text>
</svg>
<figcaption>图 1　左右两句只是前三个词的顺序不同。「小米」分给每个词的份额一模一样，只是换了行；加出来的 x′ 也一样。</figcaption>
</figure>

这就是问题所在：**注意力本身不知道词序。**「小米」只知道前面有粮油、店、买了，不知道它们是什么顺序。换成真正有意义的句子也一样：「我欠你钱」和「你欠我钱」，最后一个词都是「钱」，前面也是同样三个词，「钱」算出来的结果完全一样，模型分不清谁欠谁。

<details class="pause"><summary>停一下：生成文字的模型会遮住后面的词（每个词只能看前面），这本身算不算一点位置信息？</summary>

算一点，但很弱。第 0 个词只能看到 1 个词（它自己），第 1 个词能看到 2 个，第 100 个词能看到 101 个。看到的词越多，每个词分到的份额一般越小，模型可以从这种「被摊薄」的程度里间接猜出自己大概在第几个。有研究发现，完全不加位置编码的模型（常叫 NoPE）也能训练出来。可它只能猜出「我自己在第几个」，仍然说不清「前面三个词谁先谁后」。所以大多数模型都会把位置信息明确地加进去。

</details>

## 第二步：最朴素的办法：给每个位置发一个向量

既然 $x$ 只看 token 不看位置，那就再准备一张表：第 0 个位置一个向量，第 1 个位置一个向量……记作 $p_0, p_1, p_2, \dots$。每个 token 的向量先加上它所在位置的向量，再去算 $q$、$k$、$v$：

$$
h = x + p_{\text{位置}}
$$

$p$ 和 $x$ 一样，一开始是随机数，训练中慢慢调好，所以叫**可学习的绝对位置编码**。GPT-2 用的就是这种。

我们给 4 个位置配上这样的 $p$（假装是训练好的，取得小一些，免得盖掉词本身的意思）：

| 位置 | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| $p$ | $(0.1,\ 0.2)$ | $(0.2,\ -0.1)$ | $(-0.1,\ -0.2)$ | $(-0.2,\ 0.1)$ |

算一个例子：原句里「粮油」在位置 0，「小米」在位置 3。

「粮油」：$h = (0,\ 1) + (0.1,\ 0.2) = (0.1,\ 1.2)$，$k = W_K\,h = (0.1 + 1.2,\ \ 0.1 - 1.2) = (1.3,\ -1.1)$。

「小米」：$h = (0.5,\ 0.5) + (-0.2,\ 0.1) = (0.3,\ 0.6)$，$q = W_Q\,h = (0.3 + 0.6,\ \ 0 - 1.2 \times 0.6) = (0.9,\ -0.72)$。

分数：$q \cdot k = 0.9 \times 1.3 + (-0.72) \times (-1.1) = 1.17 + 0.792 = 1.962$。

四个词都这样算：

| 位置 | token | $x + p$ | 分数 $s$ | 份额 |
| --- | --- | --- | --- | --- |
| 0 | 粮油 | $(0.10,\ 1.20)$ | 1.962 | 49.5% |
| 1 | 店 | $(0.60,\ 0.10)$ | 0.270 | 15.0% |
| 2 | 买了 | $(0.10,\ −0.20)$ | −0.306 | 10.0% |
| 3 | 小米 | $(0.30,\ 0.60)$ | 1.026 | 25.5% |

打乱之后，「粮油」到了位置 2，加的是 $p_2$，$h$ 变成 $(0,\ 1) + (-0.1,\ -0.2) = (-0.1,\ 0.8)$，分数也变了：

| 位置 | token | $x + p$ | 分数 $s$ | 份额 |
| --- | --- | --- | --- | --- |
| 0 | 店 | $(0.50,\ 0.40)$ | 0.738 | 23.5% |
| 1 | 买了 | $(0.40,\ −0.10)$ | −0.090 | 13.1% |
| 2 | 粮油 | $(−0.10,\ 0.80)$ | 1.278 | 34.5% |
| 3 | 小米 | $(0.30,\ 0.60)$ | 1.026 | 28.9% |

<figure class="fig">
<svg viewBox="0 0 480 220" role="img" aria-label="加了位置向量后两种词序下小米的份额">
<text x="20.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">粮油 店 买了 小米（加 p）</text><text x="260.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">店 买了 粮油 小米（加 p）</text><text x="72.0" y="55.0" font-size="15" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="80" y="38" width="108.9" height="22" rx="4" style="fill:var(--warn)"/><text x="194.9" y="55.0" font-size="15" text-anchor="start" style="fill:var(--warn)">49.5%</text><text x="72.0" y="93.0" font-size="15" text-anchor="end" style="fill:var(--fg)">店</text><rect x="80" y="76" width="32.9" height="22" rx="4" style="fill:var(--line)"/><text x="118.9" y="93.0" font-size="15" text-anchor="start" style="fill:var(--muted)">15.0%</text><text x="72.0" y="131.0" font-size="15" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="80" y="114" width="21.9" height="22" rx="4" style="fill:var(--line)"/><text x="107.9" y="131.0" font-size="15" text-anchor="start" style="fill:var(--muted)">10.0%</text><text x="72.0" y="169.0" font-size="15" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="80" y="152" width="56.2" height="22" rx="4" style="fill:var(--line)"/><text x="142.2" y="169.0" font-size="15" text-anchor="start" style="fill:var(--muted)">25.5%</text><text x="20.0" y="208.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--accent)">x′ = (0.53, 2.09)</text><text x="312.0" y="55.0" font-size="15" text-anchor="end" style="fill:var(--fg)">店</text><rect x="320" y="38" width="51.8" height="22" rx="4" style="fill:var(--line)"/><text x="377.8" y="55.0" font-size="15" text-anchor="start" style="fill:var(--muted)">23.5%</text><text x="312.0" y="93.0" font-size="15" text-anchor="end" style="fill:var(--fg)">买了</text><rect x="320" y="76" width="28.8" height="22" rx="4" style="fill:var(--line)"/><text x="354.8" y="93.0" font-size="15" text-anchor="start" style="fill:var(--muted)">13.1%</text><text x="312.0" y="131.0" font-size="15" text-anchor="end" style="fill:var(--fg)">粮油</text><rect x="320" y="114" width="75.9" height="22" rx="4" style="fill:var(--warn)"/><text x="401.9" y="131.0" font-size="15" text-anchor="start" style="fill:var(--warn)">34.5%</text><text x="312.0" y="169.0" font-size="15" text-anchor="end" style="fill:var(--fg)">小米</text><rect x="320" y="152" width="63.5" height="22" rx="4" style="fill:var(--line)"/><text x="389.5" y="169.0" font-size="15" text-anchor="start" style="fill:var(--muted)">28.9%</text><text x="260.0" y="208.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--accent)">x′ = (0.52, 1.66)</text>
</svg>
<figcaption>图 2　加上位置向量之后，同样两句话，「小米」分出去的份额不同了，x′ 也不同了。</figcaption>
</figure>

现在两种词序算出来不一样了：$x'$ 从 $(0.53,\ 2.09)$ 变成 $(0.52,\ 1.66)$。模型终于能分辨顺序。

这个办法简单，GPT-2、BERT 都用它，但有三个毛病。

**(1) 表有多长，就只能读多长。** GPT-2 的位置表有 1024 行，每行 768 个数。第 1025 个 token 在表里没有对应的行，模型根本没法处理。

**(2) 每个位置各学各的。** 训练数据里短文本多、长文本少，排在第 1000 个附近的位置很少被用到，那几行向量就训练得不好。

**(3) 它记的是「第几个」，而语言里更要紧的是「隔几个」。** 同样是「粮油」紧挨在「小米」前面，放在不同的地方，分数就不同。「粮油」在 0、「小米」在 1 时，分数是 1.958；整体往后挪两格，「粮油」在 2、「小米」在 3，分数是 1.278。「前一个词」这种关系，模型要在每一个位置上分别重新学一遍。

<details class="pause"><summary>停一下：用第 1 条说，GPT-2 的位置表一共有多少个参数？</summary>

1024 行，每行 768 个数：$1024 \times 768 = 786{,}432$ 个参数，约 79 万。和 GPT-2 small 的 1.24 亿个参数比，不到 1%。参数不多，毛病在第 1 条和第 3 条：表外的位置没法用，相同的距离在不同位置要分别学。

</details>

## 第三步：正弦位置编码：一组转速不同的指针

2017 年提出 Transformer 的论文（Vaswani 等）没用可学习的表，而是用公式直接算出每个位置的向量：

$$
\begin{aligned}
\operatorname{PE}(\text{pos},\ 2i) &= \sin\!\left(\frac{\text{pos}}{10000^{2i/d}}\right) \\[4pt]
\operatorname{PE}(\text{pos},\ 2i+1) &= \cos\!\left(\frac{\text{pos}}{10000^{2i/d}}\right)
\end{aligned}
$$

这里 $\text{pos}$ 是位置编号，$d$ 是向量的长度，$i = 0, 1, \dots, d/2 - 1$。第 $2i$ 个数用 $\sin$，紧挨着的第 $2i+1$ 个数用 $\cos$，括号里是同一个值。所以这些数**两个一对**：第 $i$ 对是同一个角度的 $\sin$ 和 $\cos$。

把分母写成一个数会更清楚。记

$$
\omega_i = 10000^{-2i/d}
$$

第 $i$ 对就是 $\big(\sin(\omega_i\,\text{pos}),\ \cos(\omega_i\,\text{pos})\big)$。$\omega_i$ 是第 $i$ 对的**转速**：位置每往后一个，角度增加 $\omega_i$（单位是弧度 rad，$1\ \text{rad} \approx 57.3°$）。

先拿 $d = 4$ 算一遍。只有 2 对：

- 第 0 对：$\omega_0 = 10000^{0} = 1$。
- 第 1 对：$\omega_1 = 10000^{-2/4} = 10000^{-1/2} = \dfrac{1}{\sqrt{10000}} = \dfrac{1}{100} = 0.01$。

位置 0 到 3 的编码：

| 位置 | 第 1 对：$\sin(\text{pos})$ | $\cos(\text{pos})$ | 第 2 对：$\sin(0.01\,\text{pos})$ | $\cos(0.01\,\text{pos})$ |
| --- | --- | --- | --- | --- |
| 0 | 0.000 | 1.000 | 0.000 | 1.000 |
| 1 | 0.841 | 0.540 | 0.010 | 1.000 |
| 2 | 0.909 | −0.416 | 0.020 | 1.000 |
| 3 | 0.141 | −0.990 | 0.030 | 1.000 |

$\sin$ 和 $\cos$ 是同一个角度的一对，所以每一对都可以画成**单位圆上的一个点**（横坐标取 $\cos$，纵坐标取 $\sin$），角度就是 $\omega_i\,\text{pos}$：

<figure class="fig">
<svg viewBox="0 0 480 230" role="img" aria-label="两对数画成圆上的点">
<circle cx="120" cy="100" r="70" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="120.0" y="196.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">第 1 对：每个位置转 1 rad ≈ 57.3°</text><circle cx="190.0" cy="100.0" r="5" style="fill:var(--muted)"/><text x="206.0" y="105.0" font-size="14" text-anchor="middle" style="fill:var(--fg)">0</text><circle cx="157.8" cy="41.1" r="5" style="fill:var(--accent)"/><text x="166.5" y="32.6" font-size="14" text-anchor="middle" style="fill:var(--fg)">1</text><circle cx="90.9" cy="36.3" r="5" style="fill:var(--accent)"/><text x="84.2" y="26.8" font-size="14" text-anchor="middle" style="fill:var(--fg)">2</text><circle cx="50.7" cy="90.1" r="5" style="fill:var(--accent)"/><text x="34.9" y="92.9" font-size="14" text-anchor="middle" style="fill:var(--fg)">3</text><line x1="120.0" y1="100.0" x2="67.1" y2="92.5" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><path d="M56.2 90.9 L66.8 87.9 L65.6 96.8 z" style="fill:var(--accent)"/><circle cx="360" cy="100" r="70" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="360.0" y="196.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">第 2 对：每个位置转 0.573°</text><circle cx="430.0" cy="100.0" r="5" style="fill:var(--muted)"/><circle cx="430.0" cy="99.3" r="5" style="fill:var(--accent)"/><circle cx="430.0" cy="98.6" r="5" style="fill:var(--accent)"/><circle cx="430.0" cy="97.9" r="5" style="fill:var(--accent)"/><text x="440.0" y="86.0" font-size="13" text-anchor="start" style="fill:var(--fg)">0–3 挤在一起</text><line x1="360.0" y1="100.0" x2="413.4" y2="98.4" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><path d="M424.4 98.1 L414.5 102.9 L414.2 93.9 z" style="fill:var(--accent)"/>
</svg>
<figcaption>图 4　每一对 (sin, cos) 都是圆上的一个点（以 cos 为横坐标、sin 为纵坐标）。位置 0、1、2、3 依次往逆时针转。左边转得快，右边几乎不动；箭头指着位置 3。</figcaption>
</figure>

就像钟表上的指针：第 0 对是秒针，每个位置转 57.3°，相邻两个位置差别很大，可 6.28 个位置就绕回一圈，位置 0 和位置 6 的指针只差 $360° - 6 \times 57.3° \approx 16°$，几乎重合；第 1 对是分针，转得很慢，相邻位置几乎分不开，可要 628 个位置才绕一圈。几根转速不同的指针合起来，近处和远处的位置都能分清。

真实模型的 $d$ 有几百上千，转速从 $\omega_0 = 1$ 一路降到接近 $10000^{-1} = 0.0001$。把 $d = 32$、位置 0 到 35 的编码画成一张图：

<figure class="fig">
<svg viewBox="0 0 480 342" role="img" aria-label="正弦位置编码热力图">
<text x="46.0" y="20.0" font-size="14" text-anchor="start" style="fill:var(--muted)">维度 →</text><text x="38.0" y="40.0" font-size="14" text-anchor="end" style="fill:var(--muted)">位置</text><text x="38.0" y="58.0" font-size="14" text-anchor="end" style="fill:var(--muted)">↓</text><g style="fill:var(--accent)"><rect x="58" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="83" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="108" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="133" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="158" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="182" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="207" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="232" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="257" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="282" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="306" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="30" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="38" width="11" height="7" fill-opacity="0.84"/><rect x="58" y="38" width="11" height="7" fill-opacity="0.54"/><rect x="71" y="38" width="11" height="7" fill-opacity="0.53"/><rect x="83" y="38" width="11" height="7" fill-opacity="0.85"/><rect x="96" y="38" width="11" height="7" fill-opacity="0.31"/><rect x="108" y="38" width="11" height="7" fill-opacity="0.95"/><rect x="120" y="38" width="11" height="7" fill-opacity="0.18"/><rect x="133" y="38" width="11" height="7" fill-opacity="0.98"/><rect x="145" y="38" width="11" height="7" fill-opacity="0.10"/><rect x="158" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="170" y="38" width="11" height="7" fill-opacity="0.06"/><rect x="182" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="195" y="38" width="11" height="7" fill-opacity="0.03"/><rect x="207" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="232" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="257" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="282" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="306" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="38" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="46" width="11" height="7" fill-opacity="0.91"/><rect x="71" y="46" width="11" height="7" fill-opacity="0.90"/><rect x="83" y="46" width="11" height="7" fill-opacity="0.43"/><rect x="96" y="46" width="11" height="7" fill-opacity="0.59"/><rect x="108" y="46" width="11" height="7" fill-opacity="0.81"/><rect x="120" y="46" width="11" height="7" fill-opacity="0.35"/><rect x="133" y="46" width="11" height="7" fill-opacity="0.94"/><rect x="145" y="46" width="11" height="7" fill-opacity="0.20"/><rect x="158" y="46" width="11" height="7" fill-opacity="0.98"/><rect x="170" y="46" width="11" height="7" fill-opacity="0.11"/><rect x="182" y="46" width="11" height="7" fill-opacity="0.99"/><rect x="195" y="46" width="11" height="7" fill-opacity="0.06"/><rect x="207" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="220" y="46" width="11" height="7" fill-opacity="0.04"/><rect x="232" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="257" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="282" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="306" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="46" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="54" width="11" height="7" fill-opacity="0.14"/><rect x="71" y="54" width="11" height="7" fill-opacity="0.99"/><rect x="96" y="54" width="11" height="7" fill-opacity="0.81"/><rect x="108" y="54" width="11" height="7" fill-opacity="0.58"/><rect x="120" y="54" width="11" height="7" fill-opacity="0.51"/><rect x="133" y="54" width="11" height="7" fill-opacity="0.86"/><rect x="145" y="54" width="11" height="7" fill-opacity="0.30"/><rect x="158" y="54" width="11" height="7" fill-opacity="0.96"/><rect x="170" y="54" width="11" height="7" fill-opacity="0.17"/><rect x="182" y="54" width="11" height="7" fill-opacity="0.99"/><rect x="195" y="54" width="11" height="7" fill-opacity="0.09"/><rect x="207" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="220" y="54" width="11" height="7" fill-opacity="0.05"/><rect x="232" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="244" y="54" width="11" height="7" fill-opacity="0.03"/><rect x="257" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="282" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="306" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="54" width="11" height="7" fill-opacity="1.00"/><rect x="71" y="62" width="11" height="7" fill-opacity="0.78"/><rect x="96" y="62" width="11" height="7" fill-opacity="0.95"/><rect x="108" y="62" width="11" height="7" fill-opacity="0.30"/><rect x="120" y="62" width="11" height="7" fill-opacity="0.65"/><rect x="133" y="62" width="11" height="7" fill-opacity="0.76"/><rect x="145" y="62" width="11" height="7" fill-opacity="0.39"/><rect x="158" y="62" width="11" height="7" fill-opacity="0.92"/><rect x="170" y="62" width="11" height="7" fill-opacity="0.22"/><rect x="182" y="62" width="11" height="7" fill-opacity="0.97"/><rect x="195" y="62" width="11" height="7" fill-opacity="0.13"/><rect x="207" y="62" width="11" height="7" fill-opacity="0.99"/><rect x="220" y="62" width="11" height="7" fill-opacity="0.07"/><rect x="232" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="244" y="62" width="11" height="7" fill-opacity="0.04"/><rect x="257" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="269" y="62" width="11" height="7" fill-opacity="0.02"/><rect x="282" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="306" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="62" width="11" height="7" fill-opacity="1.00"/><rect x="58" y="70" width="11" height="7" fill-opacity="0.28"/><rect x="71" y="70" width="11" height="7" fill-opacity="0.32"/><rect x="96" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="120" y="70" width="11" height="7" fill-opacity="0.78"/><rect x="133" y="70" width="11" height="7" fill-opacity="0.63"/><rect x="145" y="70" width="11" height="7" fill-opacity="0.48"/><rect x="158" y="70" width="11" height="7" fill-opacity="0.88"/><rect x="170" y="70" width="11" height="7" fill-opacity="0.28"/><rect x="182" y="70" width="11" height="7" fill-opacity="0.96"/><rect x="195" y="70" width="11" height="7" fill-opacity="0.16"/><rect x="207" y="70" width="11" height="7" fill-opacity="0.99"/><rect x="220" y="70" width="11" height="7" fill-opacity="0.09"/><rect x="232" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="244" y="70" width="11" height="7" fill-opacity="0.05"/><rect x="257" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="269" y="70" width="11" height="7" fill-opacity="0.03"/><rect x="282" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="306" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="70" width="11" height="7" fill-opacity="1.00"/><rect x="58" y="78" width="11" height="7" fill-opacity="0.96"/><rect x="96" y="78" width="11" height="7" fill-opacity="0.95"/><rect x="120" y="78" width="11" height="7" fill-opacity="0.88"/><rect x="133" y="78" width="11" height="7" fill-opacity="0.48"/><rect x="145" y="78" width="11" height="7" fill-opacity="0.56"/><rect x="158" y="78" width="11" height="7" fill-opacity="0.83"/><rect x="170" y="78" width="11" height="7" fill-opacity="0.33"/><rect x="182" y="78" width="11" height="7" fill-opacity="0.94"/><rect x="195" y="78" width="11" height="7" fill-opacity="0.19"/><rect x="207" y="78" width="11" height="7" fill-opacity="0.98"/><rect x="220" y="78" width="11" height="7" fill-opacity="0.11"/><rect x="232" y="78" width="11" height="7" fill-opacity="0.99"/><rect x="244" y="78" width="11" height="7" fill-opacity="0.06"/><rect x="257" y="78" width="11" height="7" fill-opacity="1.00"/><rect x="269" y="78" width="11" height="7" fill-opacity="0.03"/><rect x="282" y="78" width="11" height="7" fill-opacity="1.00"/><rect x="306" y="78" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="78" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="78" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="78" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="78" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="78" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="86" width="11" height="7" fill-opacity="0.66"/><rect x="58" y="86" width="11" height="7" fill-opacity="0.75"/><rect x="96" y="86" width="11" height="7" fill-opacity="0.80"/><rect x="120" y="86" width="11" height="7" fill-opacity="0.95"/><rect x="133" y="86" width="11" height="7" fill-opacity="0.32"/><rect x="145" y="86" width="11" height="7" fill-opacity="0.64"/><rect x="158" y="86" width="11" height="7" fill-opacity="0.76"/><rect x="170" y="86" width="11" height="7" fill-opacity="0.38"/><rect x="182" y="86" width="11" height="7" fill-opacity="0.92"/><rect x="195" y="86" width="11" height="7" fill-opacity="0.22"/><rect x="207" y="86" width="11" height="7" fill-opacity="0.98"/><rect x="220" y="86" width="11" height="7" fill-opacity="0.12"/><rect x="232" y="86" width="11" height="7" fill-opacity="0.99"/><rect x="244" y="86" width="11" height="7" fill-opacity="0.07"/><rect x="257" y="86" width="11" height="7" fill-opacity="1.00"/><rect x="269" y="86" width="11" height="7" fill-opacity="0.04"/><rect x="282" y="86" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="86" width="11" height="7" fill-opacity="0.02"/><rect x="306" y="86" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="86" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="86" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="86" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="86" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="86" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="94" width="11" height="7" fill-opacity="0.99"/><rect x="96" y="94" width="11" height="7" fill-opacity="0.57"/><rect x="120" y="94" width="11" height="7" fill-opacity="0.99"/><rect x="133" y="94" width="11" height="7" fill-opacity="0.15"/><rect x="145" y="94" width="11" height="7" fill-opacity="0.72"/><rect x="158" y="94" width="11" height="7" fill-opacity="0.70"/><rect x="170" y="94" width="11" height="7" fill-opacity="0.43"/><rect x="182" y="94" width="11" height="7" fill-opacity="0.90"/><rect x="195" y="94" width="11" height="7" fill-opacity="0.25"/><rect x="207" y="94" width="11" height="7" fill-opacity="0.97"/><rect x="220" y="94" width="11" height="7" fill-opacity="0.14"/><rect x="232" y="94" width="11" height="7" fill-opacity="0.99"/><rect x="244" y="94" width="11" height="7" fill-opacity="0.08"/><rect x="257" y="94" width="11" height="7" fill-opacity="1.00"/><rect x="269" y="94" width="11" height="7" fill-opacity="0.04"/><rect x="282" y="94" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="94" width="11" height="7" fill-opacity="0.03"/><rect x="306" y="94" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="94" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="94" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="94" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="94" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="94" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="102" width="11" height="7" fill-opacity="0.41"/><rect x="83" y="102" width="11" height="7" fill-opacity="0.34"/><rect x="96" y="102" width="11" height="7" fill-opacity="0.29"/><rect x="120" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="145" y="102" width="11" height="7" fill-opacity="0.78"/><rect x="158" y="102" width="11" height="7" fill-opacity="0.62"/><rect x="170" y="102" width="11" height="7" fill-opacity="0.48"/><rect x="182" y="102" width="11" height="7" fill-opacity="0.87"/><rect x="195" y="102" width="11" height="7" fill-opacity="0.28"/><rect x="207" y="102" width="11" height="7" fill-opacity="0.96"/><rect x="220" y="102" width="11" height="7" fill-opacity="0.16"/><rect x="232" y="102" width="11" height="7" fill-opacity="0.99"/><rect x="244" y="102" width="11" height="7" fill-opacity="0.09"/><rect x="257" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="269" y="102" width="11" height="7" fill-opacity="0.05"/><rect x="282" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="102" width="11" height="7" fill-opacity="0.03"/><rect x="306" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="102" width="11" height="7" fill-opacity="1.00"/><rect x="83" y="110" width="11" height="7" fill-opacity="0.79"/><rect x="120" y="110" width="11" height="7" fill-opacity="0.98"/><rect x="145" y="110" width="11" height="7" fill-opacity="0.84"/><rect x="158" y="110" width="11" height="7" fill-opacity="0.54"/><rect x="170" y="110" width="11" height="7" fill-opacity="0.53"/><rect x="182" y="110" width="11" height="7" fill-opacity="0.85"/><rect x="195" y="110" width="11" height="7" fill-opacity="0.31"/><rect x="207" y="110" width="11" height="7" fill-opacity="0.95"/><rect x="220" y="110" width="11" height="7" fill-opacity="0.18"/><rect x="232" y="110" width="11" height="7" fill-opacity="0.98"/><rect x="244" y="110" width="11" height="7" fill-opacity="0.10"/><rect x="257" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="269" y="110" width="11" height="7" fill-opacity="0.06"/><rect x="282" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="110" width="11" height="7" fill-opacity="0.03"/><rect x="306" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="83" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="120" y="118" width="11" height="7" fill-opacity="0.93"/><rect x="145" y="118" width="11" height="7" fill-opacity="0.89"/><rect x="158" y="118" width="11" height="7" fill-opacity="0.45"/><rect x="170" y="118" width="11" height="7" fill-opacity="0.58"/><rect x="182" y="118" width="11" height="7" fill-opacity="0.81"/><rect x="195" y="118" width="11" height="7" fill-opacity="0.34"/><rect x="207" y="118" width="11" height="7" fill-opacity="0.94"/><rect x="220" y="118" width="11" height="7" fill-opacity="0.19"/><rect x="232" y="118" width="11" height="7" fill-opacity="0.98"/><rect x="244" y="118" width="11" height="7" fill-opacity="0.11"/><rect x="257" y="118" width="11" height="7" fill-opacity="0.99"/><rect x="269" y="118" width="11" height="7" fill-opacity="0.06"/><rect x="282" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="118" width="11" height="7" fill-opacity="0.03"/><rect x="306" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="331" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="58" y="126" width="11" height="7" fill-opacity="0.84"/><rect x="71" y="126" width="11" height="7" fill-opacity="0.45"/><rect x="83" y="126" width="11" height="7" fill-opacity="0.89"/><rect x="120" y="126" width="11" height="7" fill-opacity="0.85"/><rect x="145" y="126" width="11" height="7" fill-opacity="0.93"/><rect x="158" y="126" width="11" height="7" fill-opacity="0.36"/><rect x="170" y="126" width="11" height="7" fill-opacity="0.62"/><rect x="182" y="126" width="11" height="7" fill-opacity="0.78"/><rect x="195" y="126" width="11" height="7" fill-opacity="0.37"/><rect x="207" y="126" width="11" height="7" fill-opacity="0.93"/><rect x="220" y="126" width="11" height="7" fill-opacity="0.21"/><rect x="232" y="126" width="11" height="7" fill-opacity="0.98"/><rect x="244" y="126" width="11" height="7" fill-opacity="0.12"/><rect x="257" y="126" width="11" height="7" fill-opacity="0.99"/><rect x="269" y="126" width="11" height="7" fill-opacity="0.07"/><rect x="282" y="126" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="126" width="11" height="7" fill-opacity="0.04"/><rect x="306" y="126" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="126" width="11" height="7" fill-opacity="0.02"/><rect x="331" y="126" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="126" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="126" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="126" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="126" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="134" width="11" height="7" fill-opacity="0.42"/><rect x="58" y="134" width="11" height="7" fill-opacity="0.91"/><rect x="71" y="134" width="11" height="7" fill-opacity="0.86"/><rect x="83" y="134" width="11" height="7" fill-opacity="0.52"/><rect x="120" y="134" width="11" height="7" fill-opacity="0.74"/><rect x="145" y="134" width="11" height="7" fill-opacity="0.96"/><rect x="158" y="134" width="11" height="7" fill-opacity="0.27"/><rect x="170" y="134" width="11" height="7" fill-opacity="0.67"/><rect x="182" y="134" width="11" height="7" fill-opacity="0.74"/><rect x="195" y="134" width="11" height="7" fill-opacity="0.40"/><rect x="207" y="134" width="11" height="7" fill-opacity="0.92"/><rect x="220" y="134" width="11" height="7" fill-opacity="0.23"/><rect x="232" y="134" width="11" height="7" fill-opacity="0.97"/><rect x="244" y="134" width="11" height="7" fill-opacity="0.13"/><rect x="257" y="134" width="11" height="7" fill-opacity="0.99"/><rect x="269" y="134" width="11" height="7" fill-opacity="0.07"/><rect x="282" y="134" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="134" width="11" height="7" fill-opacity="0.04"/><rect x="306" y="134" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="134" width="11" height="7" fill-opacity="0.02"/><rect x="331" y="134" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="134" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="134" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="134" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="134" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="142" width="11" height="7" fill-opacity="0.99"/><rect x="58" y="142" width="11" height="7" fill-opacity="0.14"/><rect x="71" y="142" width="11" height="7" fill-opacity="1.00"/><rect x="120" y="142" width="11" height="7" fill-opacity="0.61"/><rect x="145" y="142" width="11" height="7" fill-opacity="0.99"/><rect x="158" y="142" width="11" height="7" fill-opacity="0.17"/><rect x="170" y="142" width="11" height="7" fill-opacity="0.71"/><rect x="182" y="142" width="11" height="7" fill-opacity="0.71"/><rect x="195" y="142" width="11" height="7" fill-opacity="0.43"/><rect x="207" y="142" width="11" height="7" fill-opacity="0.90"/><rect x="220" y="142" width="11" height="7" fill-opacity="0.25"/><rect x="232" y="142" width="11" height="7" fill-opacity="0.97"/><rect x="244" y="142" width="11" height="7" fill-opacity="0.14"/><rect x="257" y="142" width="11" height="7" fill-opacity="0.99"/><rect x="269" y="142" width="11" height="7" fill-opacity="0.08"/><rect x="282" y="142" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="142" width="11" height="7" fill-opacity="0.04"/><rect x="306" y="142" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="142" width="11" height="7" fill-opacity="0.02"/><rect x="331" y="142" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="142" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="142" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="142" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="142" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="150" width="11" height="7" fill-opacity="0.65"/><rect x="71" y="150" width="11" height="7" fill-opacity="0.84"/><rect x="108" y="150" width="11" height="7" fill-opacity="0.03"/><rect x="120" y="150" width="11" height="7" fill-opacity="0.46"/><rect x="145" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="158" y="150" width="11" height="7" fill-opacity="0.07"/><rect x="170" y="150" width="11" height="7" fill-opacity="0.75"/><rect x="182" y="150" width="11" height="7" fill-opacity="0.66"/><rect x="195" y="150" width="11" height="7" fill-opacity="0.46"/><rect x="207" y="150" width="11" height="7" fill-opacity="0.89"/><rect x="220" y="150" width="11" height="7" fill-opacity="0.26"/><rect x="232" y="150" width="11" height="7" fill-opacity="0.96"/><rect x="244" y="150" width="11" height="7" fill-opacity="0.15"/><rect x="257" y="150" width="11" height="7" fill-opacity="0.99"/><rect x="269" y="150" width="11" height="7" fill-opacity="0.08"/><rect x="282" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="150" width="11" height="7" fill-opacity="0.05"/><rect x="306" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="150" width="11" height="7" fill-opacity="0.03"/><rect x="331" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="71" y="158" width="11" height="7" fill-opacity="0.41"/><rect x="108" y="158" width="11" height="7" fill-opacity="0.34"/><rect x="120" y="158" width="11" height="7" fill-opacity="0.29"/><rect x="145" y="158" width="11" height="7" fill-opacity="1.00"/><rect x="170" y="158" width="11" height="7" fill-opacity="0.78"/><rect x="182" y="158" width="11" height="7" fill-opacity="0.62"/><rect x="195" y="158" width="11" height="7" fill-opacity="0.48"/><rect x="207" y="158" width="11" height="7" fill-opacity="0.87"/><rect x="220" y="158" width="11" height="7" fill-opacity="0.28"/><rect x="232" y="158" width="11" height="7" fill-opacity="0.96"/><rect x="244" y="158" width="11" height="7" fill-opacity="0.16"/><rect x="257" y="158" width="11" height="7" fill-opacity="0.99"/><rect x="269" y="158" width="11" height="7" fill-opacity="0.09"/><rect x="282" y="158" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="158" width="11" height="7" fill-opacity="0.05"/><rect x="306" y="158" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="158" width="11" height="7" fill-opacity="0.03"/><rect x="331" y="158" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="158" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="158" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="158" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="158" width="11" height="7" fill-opacity="1.00"/><rect x="108" y="166" width="11" height="7" fill-opacity="0.62"/><rect x="120" y="166" width="11" height="7" fill-opacity="0.12"/><rect x="145" y="166" width="11" height="7" fill-opacity="0.99"/><rect x="170" y="166" width="11" height="7" fill-opacity="0.82"/><rect x="182" y="166" width="11" height="7" fill-opacity="0.58"/><rect x="195" y="166" width="11" height="7" fill-opacity="0.51"/><rect x="207" y="166" width="11" height="7" fill-opacity="0.86"/><rect x="220" y="166" width="11" height="7" fill-opacity="0.30"/><rect x="232" y="166" width="11" height="7" fill-opacity="0.95"/><rect x="244" y="166" width="11" height="7" fill-opacity="0.17"/><rect x="257" y="166" width="11" height="7" fill-opacity="0.99"/><rect x="269" y="166" width="11" height="7" fill-opacity="0.10"/><rect x="282" y="166" width="11" height="7" fill-opacity="1.00"/><rect x="294" y="166" width="11" height="7" fill-opacity="0.05"/><rect x="306" y="166" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="166" width="11" height="7" fill-opacity="0.03"/><rect x="331" y="166" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="166" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="166" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="166" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="166" width="11" height="7" fill-opacity="1.00"/><rect x="58" y="174" width="11" height="7" fill-opacity="0.66"/><rect x="108" y="174" width="11" height="7" fill-opacity="0.83"/><rect x="145" y="174" width="11" height="7" fill-opacity="0.97"/><rect x="170" y="174" width="11" height="7" fill-opacity="0.85"/><rect x="182" y="174" width="11" height="7" fill-opacity="0.53"/><rect x="195" y="174" width="11" height="7" fill-opacity="0.54"/><rect x="207" y="174" width="11" height="7" fill-opacity="0.84"/><rect x="220" y="174" width="11" height="7" fill-opacity="0.31"/><rect x="232" y="174" width="11" height="7" fill-opacity="0.95"/><rect x="244" y="174" width="11" height="7" fill-opacity="0.18"/><rect x="257" y="174" width="11" height="7" fill-opacity="0.98"/><rect x="269" y="174" width="11" height="7" fill-opacity="0.10"/><rect x="282" y="174" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="174" width="11" height="7" fill-opacity="0.06"/><rect x="306" y="174" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="174" width="11" height="7" fill-opacity="0.03"/><rect x="331" y="174" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="174" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="174" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="174" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="174" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="182" width="11" height="7" fill-opacity="0.15"/><rect x="58" y="182" width="11" height="7" fill-opacity="0.99"/><rect x="108" y="182" width="11" height="7" fill-opacity="0.96"/><rect x="145" y="182" width="11" height="7" fill-opacity="0.95"/><rect x="170" y="182" width="11" height="7" fill-opacity="0.88"/><rect x="182" y="182" width="11" height="7" fill-opacity="0.48"/><rect x="195" y="182" width="11" height="7" fill-opacity="0.57"/><rect x="207" y="182" width="11" height="7" fill-opacity="0.82"/><rect x="220" y="182" width="11" height="7" fill-opacity="0.33"/><rect x="232" y="182" width="11" height="7" fill-opacity="0.94"/><rect x="244" y="182" width="11" height="7" fill-opacity="0.19"/><rect x="257" y="182" width="11" height="7" fill-opacity="0.98"/><rect x="269" y="182" width="11" height="7" fill-opacity="0.11"/><rect x="282" y="182" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="182" width="11" height="7" fill-opacity="0.06"/><rect x="306" y="182" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="182" width="11" height="7" fill-opacity="0.03"/><rect x="331" y="182" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="182" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="182" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="182" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="182" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="190" width="11" height="7" fill-opacity="0.91"/><rect x="58" y="190" width="11" height="7" fill-opacity="0.41"/><rect x="83" y="190" width="11" height="7" fill-opacity="0.25"/><rect x="96" y="190" width="11" height="7" fill-opacity="0.04"/><rect x="108" y="190" width="11" height="7" fill-opacity="1.00"/><rect x="145" y="190" width="11" height="7" fill-opacity="0.91"/><rect x="170" y="190" width="11" height="7" fill-opacity="0.90"/><rect x="182" y="190" width="11" height="7" fill-opacity="0.43"/><rect x="195" y="190" width="11" height="7" fill-opacity="0.59"/><rect x="207" y="190" width="11" height="7" fill-opacity="0.81"/><rect x="220" y="190" width="11" height="7" fill-opacity="0.35"/><rect x="232" y="190" width="11" height="7" fill-opacity="0.94"/><rect x="244" y="190" width="11" height="7" fill-opacity="0.20"/><rect x="257" y="190" width="11" height="7" fill-opacity="0.98"/><rect x="269" y="190" width="11" height="7" fill-opacity="0.11"/><rect x="282" y="190" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="190" width="11" height="7" fill-opacity="0.06"/><rect x="306" y="190" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="190" width="11" height="7" fill-opacity="0.04"/><rect x="331" y="190" width="11" height="7" fill-opacity="1.00"/><rect x="356" y="190" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="190" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="190" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="190" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="198" width="11" height="7" fill-opacity="0.84"/><rect x="83" y="198" width="11" height="7" fill-opacity="0.73"/><rect x="96" y="198" width="11" height="7" fill-opacity="0.35"/><rect x="108" y="198" width="11" height="7" fill-opacity="0.94"/><rect x="145" y="198" width="11" height="7" fill-opacity="0.86"/><rect x="170" y="198" width="11" height="7" fill-opacity="0.92"/><rect x="182" y="198" width="11" height="7" fill-opacity="0.38"/><rect x="195" y="198" width="11" height="7" fill-opacity="0.62"/><rect x="207" y="198" width="11" height="7" fill-opacity="0.79"/><rect x="220" y="198" width="11" height="7" fill-opacity="0.36"/><rect x="232" y="198" width="11" height="7" fill-opacity="0.93"/><rect x="244" y="198" width="11" height="7" fill-opacity="0.21"/><rect x="257" y="198" width="11" height="7" fill-opacity="0.98"/><rect x="269" y="198" width="11" height="7" fill-opacity="0.12"/><rect x="282" y="198" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="198" width="11" height="7" fill-opacity="0.07"/><rect x="306" y="198" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="198" width="11" height="7" fill-opacity="0.04"/><rect x="331" y="198" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="198" width="11" height="7" fill-opacity="0.02"/><rect x="356" y="198" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="198" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="198" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="198" width="11" height="7" fill-opacity="1.00"/><rect x="83" y="206" width="11" height="7" fill-opacity="0.98"/><rect x="96" y="206" width="11" height="7" fill-opacity="0.62"/><rect x="108" y="206" width="11" height="7" fill-opacity="0.78"/><rect x="145" y="206" width="11" height="7" fill-opacity="0.81"/><rect x="170" y="206" width="11" height="7" fill-opacity="0.94"/><rect x="182" y="206" width="11" height="7" fill-opacity="0.33"/><rect x="195" y="206" width="11" height="7" fill-opacity="0.64"/><rect x="207" y="206" width="11" height="7" fill-opacity="0.77"/><rect x="220" y="206" width="11" height="7" fill-opacity="0.38"/><rect x="232" y="206" width="11" height="7" fill-opacity="0.92"/><rect x="244" y="206" width="11" height="7" fill-opacity="0.22"/><rect x="257" y="206" width="11" height="7" fill-opacity="0.98"/><rect x="269" y="206" width="11" height="7" fill-opacity="0.12"/><rect x="282" y="206" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="206" width="11" height="7" fill-opacity="0.07"/><rect x="306" y="206" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="206" width="11" height="7" fill-opacity="0.04"/><rect x="331" y="206" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="206" width="11" height="7" fill-opacity="0.02"/><rect x="356" y="206" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="206" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="206" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="206" width="11" height="7" fill-opacity="1.00"/><rect x="71" y="214" width="11" height="7" fill-opacity="0.36"/><rect x="83" y="214" width="11" height="7" fill-opacity="0.93"/><rect x="96" y="214" width="11" height="7" fill-opacity="0.84"/><rect x="108" y="214" width="11" height="7" fill-opacity="0.55"/><rect x="145" y="214" width="11" height="7" fill-opacity="0.75"/><rect x="170" y="214" width="11" height="7" fill-opacity="0.96"/><rect x="182" y="214" width="11" height="7" fill-opacity="0.27"/><rect x="195" y="214" width="11" height="7" fill-opacity="0.66"/><rect x="207" y="214" width="11" height="7" fill-opacity="0.75"/><rect x="220" y="214" width="11" height="7" fill-opacity="0.40"/><rect x="232" y="214" width="11" height="7" fill-opacity="0.92"/><rect x="244" y="214" width="11" height="7" fill-opacity="0.23"/><rect x="257" y="214" width="11" height="7" fill-opacity="0.97"/><rect x="269" y="214" width="11" height="7" fill-opacity="0.13"/><rect x="282" y="214" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="214" width="11" height="7" fill-opacity="0.07"/><rect x="306" y="214" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="214" width="11" height="7" fill-opacity="0.04"/><rect x="331" y="214" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="214" width="11" height="7" fill-opacity="0.02"/><rect x="356" y="214" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="214" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="214" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="214" width="11" height="7" fill-opacity="1.00"/><rect x="58" y="222" width="11" height="7" fill-opacity="0.42"/><rect x="71" y="222" width="11" height="7" fill-opacity="0.80"/><rect x="83" y="222" width="11" height="7" fill-opacity="0.60"/><rect x="96" y="222" width="11" height="7" fill-opacity="0.97"/><rect x="108" y="222" width="11" height="7" fill-opacity="0.26"/><rect x="145" y="222" width="11" height="7" fill-opacity="0.68"/><rect x="170" y="222" width="11" height="7" fill-opacity="0.98"/><rect x="182" y="222" width="11" height="7" fill-opacity="0.22"/><rect x="195" y="222" width="11" height="7" fill-opacity="0.69"/><rect x="207" y="222" width="11" height="7" fill-opacity="0.73"/><rect x="220" y="222" width="11" height="7" fill-opacity="0.41"/><rect x="232" y="222" width="11" height="7" fill-opacity="0.91"/><rect x="244" y="222" width="11" height="7" fill-opacity="0.24"/><rect x="257" y="222" width="11" height="7" fill-opacity="0.97"/><rect x="269" y="222" width="11" height="7" fill-opacity="0.13"/><rect x="282" y="222" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="222" width="11" height="7" fill-opacity="0.08"/><rect x="306" y="222" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="222" width="11" height="7" fill-opacity="0.04"/><rect x="331" y="222" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="222" width="11" height="7" fill-opacity="0.02"/><rect x="356" y="222" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="222" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="222" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="222" width="11" height="7" fill-opacity="1.00"/><rect x="58" y="230" width="11" height="7" fill-opacity="0.99"/><rect x="71" y="230" width="11" height="7" fill-opacity="1.00"/><rect x="83" y="230" width="11" height="7" fill-opacity="0.08"/><rect x="96" y="230" width="11" height="7" fill-opacity="1.00"/><rect x="145" y="230" width="11" height="7" fill-opacity="0.60"/><rect x="170" y="230" width="11" height="7" fill-opacity="0.99"/><rect x="182" y="230" width="11" height="7" fill-opacity="0.16"/><rect x="195" y="230" width="11" height="7" fill-opacity="0.71"/><rect x="207" y="230" width="11" height="7" fill-opacity="0.70"/><rect x="220" y="230" width="11" height="7" fill-opacity="0.43"/><rect x="232" y="230" width="11" height="7" fill-opacity="0.90"/><rect x="244" y="230" width="11" height="7" fill-opacity="0.25"/><rect x="257" y="230" width="11" height="7" fill-opacity="0.97"/><rect x="269" y="230" width="11" height="7" fill-opacity="0.14"/><rect x="282" y="230" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="230" width="11" height="7" fill-opacity="0.08"/><rect x="306" y="230" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="230" width="11" height="7" fill-opacity="0.04"/><rect x="331" y="230" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="230" width="11" height="7" fill-opacity="0.02"/><rect x="356" y="230" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="230" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="230" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="230" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="238" width="11" height="7" fill-opacity="0.76"/><rect x="58" y="238" width="11" height="7" fill-opacity="0.65"/><rect x="71" y="238" width="11" height="7" fill-opacity="0.89"/><rect x="96" y="238" width="11" height="7" fill-opacity="0.93"/><rect x="145" y="238" width="11" height="7" fill-opacity="0.52"/><rect x="170" y="238" width="11" height="7" fill-opacity="0.99"/><rect x="182" y="238" width="11" height="7" fill-opacity="0.11"/><rect x="195" y="238" width="11" height="7" fill-opacity="0.73"/><rect x="207" y="238" width="11" height="7" fill-opacity="0.68"/><rect x="220" y="238" width="11" height="7" fill-opacity="0.45"/><rect x="232" y="238" width="11" height="7" fill-opacity="0.90"/><rect x="244" y="238" width="11" height="7" fill-opacity="0.26"/><rect x="257" y="238" width="11" height="7" fill-opacity="0.97"/><rect x="269" y="238" width="11" height="7" fill-opacity="0.15"/><rect x="282" y="238" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="238" width="11" height="7" fill-opacity="0.08"/><rect x="306" y="238" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="238" width="11" height="7" fill-opacity="0.05"/><rect x="331" y="238" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="238" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="238" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="238" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="238" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="238" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="246" width="11" height="7" fill-opacity="0.96"/><rect x="71" y="246" width="11" height="7" fill-opacity="0.50"/><rect x="96" y="246" width="11" height="7" fill-opacity="0.77"/><rect x="133" y="246" width="11" height="7" fill-opacity="0.09"/><rect x="145" y="246" width="11" height="7" fill-opacity="0.43"/><rect x="170" y="246" width="11" height="7" fill-opacity="1.00"/><rect x="182" y="246" width="11" height="7" fill-opacity="0.05"/><rect x="195" y="246" width="11" height="7" fill-opacity="0.75"/><rect x="207" y="246" width="11" height="7" fill-opacity="0.66"/><rect x="220" y="246" width="11" height="7" fill-opacity="0.46"/><rect x="232" y="246" width="11" height="7" fill-opacity="0.89"/><rect x="244" y="246" width="11" height="7" fill-opacity="0.27"/><rect x="257" y="246" width="11" height="7" fill-opacity="0.96"/><rect x="269" y="246" width="11" height="7" fill-opacity="0.15"/><rect x="282" y="246" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="246" width="11" height="7" fill-opacity="0.09"/><rect x="306" y="246" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="246" width="11" height="7" fill-opacity="0.05"/><rect x="331" y="246" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="246" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="246" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="246" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="246" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="246" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="254" width="11" height="7" fill-opacity="0.27"/><rect x="96" y="254" width="11" height="7" fill-opacity="0.54"/><rect x="133" y="254" width="11" height="7" fill-opacity="0.26"/><rect x="145" y="254" width="11" height="7" fill-opacity="0.33"/><rect x="170" y="254" width="11" height="7" fill-opacity="1.00"/><rect x="195" y="254" width="11" height="7" fill-opacity="0.77"/><rect x="207" y="254" width="11" height="7" fill-opacity="0.63"/><rect x="220" y="254" width="11" height="7" fill-opacity="0.48"/><rect x="232" y="254" width="11" height="7" fill-opacity="0.88"/><rect x="244" y="254" width="11" height="7" fill-opacity="0.28"/><rect x="257" y="254" width="11" height="7" fill-opacity="0.96"/><rect x="269" y="254" width="11" height="7" fill-opacity="0.16"/><rect x="282" y="254" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="254" width="11" height="7" fill-opacity="0.09"/><rect x="306" y="254" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="254" width="11" height="7" fill-opacity="0.05"/><rect x="331" y="254" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="254" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="254" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="254" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="254" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="254" width="11" height="7" fill-opacity="1.00"/><rect x="96" y="262" width="11" height="7" fill-opacity="0.25"/><rect x="133" y="262" width="11" height="7" fill-opacity="0.43"/><rect x="145" y="262" width="11" height="7" fill-opacity="0.24"/><rect x="170" y="262" width="11" height="7" fill-opacity="1.00"/><rect x="195" y="262" width="11" height="7" fill-opacity="0.79"/><rect x="207" y="262" width="11" height="7" fill-opacity="0.61"/><rect x="220" y="262" width="11" height="7" fill-opacity="0.49"/><rect x="232" y="262" width="11" height="7" fill-opacity="0.87"/><rect x="244" y="262" width="11" height="7" fill-opacity="0.29"/><rect x="257" y="262" width="11" height="7" fill-opacity="0.96"/><rect x="269" y="262" width="11" height="7" fill-opacity="0.16"/><rect x="282" y="262" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="262" width="11" height="7" fill-opacity="0.09"/><rect x="306" y="262" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="262" width="11" height="7" fill-opacity="0.05"/><rect x="331" y="262" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="262" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="262" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="262" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="262" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="262" width="11" height="7" fill-opacity="1.00"/><rect x="58" y="270" width="11" height="7" fill-opacity="0.15"/><rect x="133" y="270" width="11" height="7" fill-opacity="0.58"/><rect x="145" y="270" width="11" height="7" fill-opacity="0.14"/><rect x="170" y="270" width="11" height="7" fill-opacity="0.99"/><rect x="195" y="270" width="11" height="7" fill-opacity="0.81"/><rect x="207" y="270" width="11" height="7" fill-opacity="0.58"/><rect x="220" y="270" width="11" height="7" fill-opacity="0.51"/><rect x="232" y="270" width="11" height="7" fill-opacity="0.86"/><rect x="244" y="270" width="11" height="7" fill-opacity="0.30"/><rect x="257" y="270" width="11" height="7" fill-opacity="0.96"/><rect x="269" y="270" width="11" height="7" fill-opacity="0.17"/><rect x="282" y="270" width="11" height="7" fill-opacity="0.99"/><rect x="294" y="270" width="11" height="7" fill-opacity="0.09"/><rect x="306" y="270" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="270" width="11" height="7" fill-opacity="0.05"/><rect x="331" y="270" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="270" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="270" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="270" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="270" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="270" width="11" height="7" fill-opacity="1.00"/><rect x="58" y="278" width="11" height="7" fill-opacity="0.91"/><rect x="83" y="278" width="11" height="7" fill-opacity="0.15"/><rect x="133" y="278" width="11" height="7" fill-opacity="0.72"/><rect x="145" y="278" width="11" height="7" fill-opacity="0.04"/><rect x="170" y="278" width="11" height="7" fill-opacity="0.99"/><rect x="195" y="278" width="11" height="7" fill-opacity="0.83"/><rect x="207" y="278" width="11" height="7" fill-opacity="0.56"/><rect x="220" y="278" width="11" height="7" fill-opacity="0.52"/><rect x="232" y="278" width="11" height="7" fill-opacity="0.85"/><rect x="244" y="278" width="11" height="7" fill-opacity="0.31"/><rect x="257" y="278" width="11" height="7" fill-opacity="0.95"/><rect x="269" y="278" width="11" height="7" fill-opacity="0.17"/><rect x="282" y="278" width="11" height="7" fill-opacity="0.98"/><rect x="294" y="278" width="11" height="7" fill-opacity="0.10"/><rect x="306" y="278" width="11" height="7" fill-opacity="1.00"/><rect x="319" y="278" width="11" height="7" fill-opacity="0.06"/><rect x="331" y="278" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="278" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="278" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="278" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="278" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="278" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="286" width="11" height="7" fill-opacity="0.55"/><rect x="58" y="286" width="11" height="7" fill-opacity="0.83"/><rect x="83" y="286" width="11" height="7" fill-opacity="0.66"/><rect x="133" y="286" width="11" height="7" fill-opacity="0.83"/><rect x="170" y="286" width="11" height="7" fill-opacity="0.97"/><rect x="195" y="286" width="11" height="7" fill-opacity="0.85"/><rect x="207" y="286" width="11" height="7" fill-opacity="0.53"/><rect x="220" y="286" width="11" height="7" fill-opacity="0.54"/><rect x="232" y="286" width="11" height="7" fill-opacity="0.84"/><rect x="244" y="286" width="11" height="7" fill-opacity="0.31"/><rect x="257" y="286" width="11" height="7" fill-opacity="0.95"/><rect x="269" y="286" width="11" height="7" fill-opacity="0.18"/><rect x="282" y="286" width="11" height="7" fill-opacity="0.98"/><rect x="294" y="286" width="11" height="7" fill-opacity="0.10"/><rect x="306" y="286" width="11" height="7" fill-opacity="0.99"/><rect x="319" y="286" width="11" height="7" fill-opacity="0.06"/><rect x="331" y="286" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="286" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="286" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="286" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="286" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="286" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="294" width="11" height="7" fill-opacity="1.00"/><rect x="83" y="294" width="11" height="7" fill-opacity="0.96"/><rect x="133" y="294" width="11" height="7" fill-opacity="0.92"/><rect x="170" y="294" width="11" height="7" fill-opacity="0.96"/><rect x="195" y="294" width="11" height="7" fill-opacity="0.86"/><rect x="207" y="294" width="11" height="7" fill-opacity="0.50"/><rect x="220" y="294" width="11" height="7" fill-opacity="0.55"/><rect x="232" y="294" width="11" height="7" fill-opacity="0.83"/><rect x="244" y="294" width="11" height="7" fill-opacity="0.32"/><rect x="257" y="294" width="11" height="7" fill-opacity="0.95"/><rect x="269" y="294" width="11" height="7" fill-opacity="0.18"/><rect x="282" y="294" width="11" height="7" fill-opacity="0.98"/><rect x="294" y="294" width="11" height="7" fill-opacity="0.10"/><rect x="306" y="294" width="11" height="7" fill-opacity="0.99"/><rect x="319" y="294" width="11" height="7" fill-opacity="0.06"/><rect x="331" y="294" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="294" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="294" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="294" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="294" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="294" width="11" height="7" fill-opacity="1.00"/><rect x="46" y="302" width="11" height="7" fill-opacity="0.53"/><rect x="71" y="302" width="11" height="7" fill-opacity="0.27"/><rect x="83" y="302" width="11" height="7" fill-opacity="0.96"/><rect x="133" y="302" width="11" height="7" fill-opacity="0.97"/><rect x="170" y="302" width="11" height="7" fill-opacity="0.94"/><rect x="195" y="302" width="11" height="7" fill-opacity="0.88"/><rect x="207" y="302" width="11" height="7" fill-opacity="0.48"/><rect x="220" y="302" width="11" height="7" fill-opacity="0.57"/><rect x="232" y="302" width="11" height="7" fill-opacity="0.82"/><rect x="244" y="302" width="11" height="7" fill-opacity="0.33"/><rect x="257" y="302" width="11" height="7" fill-opacity="0.94"/><rect x="269" y="302" width="11" height="7" fill-opacity="0.19"/><rect x="282" y="302" width="11" height="7" fill-opacity="0.98"/><rect x="294" y="302" width="11" height="7" fill-opacity="0.11"/><rect x="306" y="302" width="11" height="7" fill-opacity="0.99"/><rect x="319" y="302" width="11" height="7" fill-opacity="0.06"/><rect x="331" y="302" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="302" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="302" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="302" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="302" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="302" width="11" height="7" fill-opacity="1.00"/><rect x="71" y="310" width="11" height="7" fill-opacity="0.74"/><rect x="83" y="310" width="11" height="7" fill-opacity="0.67"/><rect x="108" y="310" width="11" height="7" fill-opacity="0.07"/><rect x="133" y="310" width="11" height="7" fill-opacity="1.00"/><rect x="170" y="310" width="11" height="7" fill-opacity="0.92"/><rect x="195" y="310" width="11" height="7" fill-opacity="0.89"/><rect x="207" y="310" width="11" height="7" fill-opacity="0.45"/><rect x="220" y="310" width="11" height="7" fill-opacity="0.58"/><rect x="232" y="310" width="11" height="7" fill-opacity="0.81"/><rect x="244" y="310" width="11" height="7" fill-opacity="0.34"/><rect x="257" y="310" width="11" height="7" fill-opacity="0.94"/><rect x="269" y="310" width="11" height="7" fill-opacity="0.20"/><rect x="282" y="310" width="11" height="7" fill-opacity="0.98"/><rect x="294" y="310" width="11" height="7" fill-opacity="0.11"/><rect x="306" y="310" width="11" height="7" fill-opacity="0.99"/><rect x="319" y="310" width="11" height="7" fill-opacity="0.06"/><rect x="331" y="310" width="11" height="7" fill-opacity="1.00"/><rect x="344" y="310" width="11" height="7" fill-opacity="0.03"/><rect x="356" y="310" width="11" height="7" fill-opacity="1.00"/><rect x="381" y="310" width="11" height="7" fill-opacity="1.00"/><rect x="406" y="310" width="11" height="7" fill-opacity="1.00"/><rect x="430" y="310" width="11" height="7" fill-opacity="1.00"/></g><g style="fill:var(--warn)"><rect x="58" y="46" width="11" height="7" fill-opacity="0.42"/><rect x="58" y="54" width="11" height="7" fill-opacity="0.99"/><rect x="83" y="54" width="11" height="7" fill-opacity="0.12"/><rect x="46" y="62" width="11" height="7" fill-opacity="0.76"/><rect x="58" y="62" width="11" height="7" fill-opacity="0.65"/><rect x="83" y="62" width="11" height="7" fill-opacity="0.63"/><rect x="46" y="70" width="11" height="7" fill-opacity="0.96"/><rect x="83" y="70" width="11" height="7" fill-opacity="0.95"/><rect x="46" y="78" width="11" height="7" fill-opacity="0.28"/><rect x="71" y="78" width="11" height="7" fill-opacity="0.23"/><rect x="83" y="78" width="11" height="7" fill-opacity="0.97"/><rect x="108" y="78" width="11" height="7" fill-opacity="0.32"/><rect x="71" y="86" width="11" height="7" fill-opacity="0.71"/><rect x="83" y="86" width="11" height="7" fill-opacity="0.70"/><rect x="108" y="86" width="11" height="7" fill-opacity="0.60"/><rect x="58" y="94" width="11" height="7" fill-opacity="0.15"/><rect x="71" y="94" width="11" height="7" fill-opacity="0.98"/><rect x="83" y="94" width="11" height="7" fill-opacity="0.21"/><rect x="108" y="94" width="11" height="7" fill-opacity="0.82"/><rect x="58" y="102" width="11" height="7" fill-opacity="0.91"/><rect x="71" y="102" width="11" height="7" fill-opacity="0.94"/><rect x="108" y="102" width="11" height="7" fill-opacity="0.96"/><rect x="133" y="102" width="11" height="7" fill-opacity="0.03"/><rect x="46" y="110" width="11" height="7" fill-opacity="0.54"/><rect x="58" y="110" width="11" height="7" fill-opacity="0.84"/><rect x="71" y="110" width="11" height="7" fill-opacity="0.61"/><rect x="96" y="110" width="11" height="7" fill-opacity="0.02"/><rect x="108" y="110" width="11" height="7" fill-opacity="1.00"/><rect x="133" y="110" width="11" height="7" fill-opacity="0.21"/><rect x="46" y="118" width="11" height="7" fill-opacity="1.00"/><rect x="71" y="118" width="11" height="7" fill-opacity="0.10"/><rect x="96" y="118" width="11" height="7" fill-opacity="0.33"/><rect x="108" y="118" width="11" height="7" fill-opacity="0.94"/><rect x="133" y="118" width="11" height="7" fill-opacity="0.38"/><rect x="46" y="126" width="11" height="7" fill-opacity="0.54"/><rect x="96" y="126" width="11" height="7" fill-opacity="0.61"/><rect x="108" y="126" width="11" height="7" fill-opacity="0.79"/><rect x="133" y="126" width="11" height="7" fill-opacity="0.53"/><rect x="96" y="134" width="11" height="7" fill-opacity="0.82"/><rect x="108" y="134" width="11" height="7" fill-opacity="0.57"/><rect x="133" y="134" width="11" height="7" fill-opacity="0.68"/><rect x="96" y="142" width="11" height="7" fill-opacity="0.96"/><rect x="108" y="142" width="11" height="7" fill-opacity="0.28"/><rect x="133" y="142" width="11" height="7" fill-opacity="0.79"/><rect x="58" y="150" width="11" height="7" fill-opacity="0.76"/><rect x="83" y="150" width="11" height="7" fill-opacity="0.55"/><rect x="96" y="150" width="11" height="7" fill-opacity="1.00"/><rect x="133" y="150" width="11" height="7" fill-opacity="0.89"/><rect x="46" y="158" width="11" height="7" fill-opacity="0.29"/><rect x="58" y="158" width="11" height="7" fill-opacity="0.96"/><rect x="83" y="158" width="11" height="7" fill-opacity="0.91"/><rect x="96" y="158" width="11" height="7" fill-opacity="0.94"/><rect x="133" y="158" width="11" height="7" fill-opacity="0.96"/><rect x="158" y="158" width="11" height="7" fill-opacity="0.03"/><rect x="46" y="166" width="11" height="7" fill-opacity="0.96"/><rect x="58" y="166" width="11" height="7" fill-opacity="0.28"/><rect x="71" y="166" width="11" height="7" fill-opacity="0.13"/><rect x="83" y="166" width="11" height="7" fill-opacity="0.99"/><rect x="96" y="166" width="11" height="7" fill-opacity="0.79"/><rect x="133" y="166" width="11" height="7" fill-opacity="0.99"/><rect x="158" y="166" width="11" height="7" fill-opacity="0.13"/><rect x="46" y="174" width="11" height="7" fill-opacity="0.75"/><rect x="71" y="174" width="11" height="7" fill-opacity="0.64"/><rect x="83" y="174" width="11" height="7" fill-opacity="0.77"/><rect x="96" y="174" width="11" height="7" fill-opacity="0.56"/><rect x="120" y="174" width="11" height="7" fill-opacity="0.06"/><rect x="133" y="174" width="11" height="7" fill-opacity="1.00"/><rect x="158" y="174" width="11" height="7" fill-opacity="0.23"/><rect x="71" y="182" width="11" height="7" fill-opacity="0.95"/><rect x="83" y="182" width="11" height="7" fill-opacity="0.31"/><rect x="96" y="182" width="11" height="7" fill-opacity="0.27"/><rect x="120" y="182" width="11" height="7" fill-opacity="0.23"/><rect x="133" y="182" width="11" height="7" fill-opacity="0.97"/><rect x="158" y="182" width="11" height="7" fill-opacity="0.32"/><rect x="71" y="190" width="11" height="7" fill-opacity="0.97"/><rect x="120" y="190" width="11" height="7" fill-opacity="0.40"/><rect x="133" y="190" width="11" height="7" fill-opacity="0.92"/><rect x="158" y="190" width="11" height="7" fill-opacity="0.42"/><rect x="58" y="198" width="11" height="7" fill-opacity="0.55"/><rect x="71" y="198" width="11" height="7" fill-opacity="0.69"/><rect x="120" y="198" width="11" height="7" fill-opacity="0.56"/><rect x="133" y="198" width="11" height="7" fill-opacity="0.83"/><rect x="158" y="198" width="11" height="7" fill-opacity="0.50"/><rect x="58" y="206" width="11" height="7" fill-opacity="1.00"/><rect x="71" y="206" width="11" height="7" fill-opacity="0.19"/><rect x="120" y="206" width="11" height="7" fill-opacity="0.70"/><rect x="133" y="206" width="11" height="7" fill-opacity="0.72"/><rect x="158" y="206" width="11" height="7" fill-opacity="0.59"/><rect x="46" y="214" width="11" height="7" fill-opacity="0.85"/><rect x="58" y="214" width="11" height="7" fill-opacity="0.53"/><rect x="120" y="214" width="11" height="7" fill-opacity="0.81"/><rect x="133" y="214" width="11" height="7" fill-opacity="0.58"/><rect x="158" y="214" width="11" height="7" fill-opacity="0.67"/><rect x="46" y="222" width="11" height="7" fill-opacity="0.91"/><rect x="120" y="222" width="11" height="7" fill-opacity="0.90"/><rect x="133" y="222" width="11" height="7" fill-opacity="0.43"/><rect x="158" y="222" width="11" height="7" fill-opacity="0.74"/><rect x="46" y="230" width="11" height="7" fill-opacity="0.13"/><rect x="108" y="230" width="11" height="7" fill-opacity="0.05"/><rect x="120" y="230" width="11" height="7" fill-opacity="0.96"/><rect x="133" y="230" width="11" height="7" fill-opacity="0.26"/><rect x="158" y="230" width="11" height="7" fill-opacity="0.80"/><rect x="83" y="238" width="11" height="7" fill-opacity="0.47"/><rect x="108" y="238" width="11" height="7" fill-opacity="0.36"/><rect x="120" y="238" width="11" height="7" fill-opacity="1.00"/><rect x="133" y="238" width="11" height="7" fill-opacity="0.09"/><rect x="158" y="238" width="11" height="7" fill-opacity="0.86"/><rect x="58" y="246" width="11" height="7" fill-opacity="0.29"/><rect x="83" y="246" width="11" height="7" fill-opacity="0.87"/><rect x="108" y="246" width="11" height="7" fill-opacity="0.63"/><rect x="120" y="246" width="11" height="7" fill-opacity="1.00"/><rect x="158" y="246" width="11" height="7" fill-opacity="0.90"/><rect x="58" y="254" width="11" height="7" fill-opacity="0.96"/><rect x="71" y="254" width="11" height="7" fill-opacity="0.04"/><rect x="83" y="254" width="11" height="7" fill-opacity="1.00"/><rect x="108" y="254" width="11" height="7" fill-opacity="0.84"/><rect x="120" y="254" width="11" height="7" fill-opacity="0.96"/><rect x="158" y="254" width="11" height="7" fill-opacity="0.94"/><rect x="46" y="262" width="11" height="7" fill-opacity="0.66"/><rect x="58" y="262" width="11" height="7" fill-opacity="0.75"/><rect x="71" y="262" width="11" height="7" fill-opacity="0.56"/><rect x="83" y="262" width="11" height="7" fill-opacity="0.83"/><rect x="108" y="262" width="11" height="7" fill-opacity="0.97"/><rect x="120" y="262" width="11" height="7" fill-opacity="0.90"/><rect x="158" y="262" width="11" height="7" fill-opacity="0.97"/><rect x="182" y="262" width="11" height="7" fill-opacity="0.06"/><rect x="46" y="270" width="11" height="7" fill-opacity="0.99"/><rect x="71" y="270" width="11" height="7" fill-opacity="0.92"/><rect x="83" y="270" width="11" height="7" fill-opacity="0.40"/><rect x="96" y="270" width="11" height="7" fill-opacity="0.06"/><rect x="108" y="270" width="11" height="7" fill-opacity="1.00"/><rect x="120" y="270" width="11" height="7" fill-opacity="0.81"/><rect x="158" y="270" width="11" height="7" fill-opacity="0.99"/><rect x="182" y="270" width="11" height="7" fill-opacity="0.12"/><rect x="46" y="278" width="11" height="7" fill-opacity="0.40"/><rect x="71" y="278" width="11" height="7" fill-opacity="0.99"/><rect x="96" y="278" width="11" height="7" fill-opacity="0.37"/><rect x="108" y="278" width="11" height="7" fill-opacity="0.93"/><rect x="120" y="278" width="11" height="7" fill-opacity="0.70"/><rect x="158" y="278" width="11" height="7" fill-opacity="1.00"/><rect x="182" y="278" width="11" height="7" fill-opacity="0.17"/><rect x="71" y="286" width="11" height="7" fill-opacity="0.75"/><rect x="96" y="286" width="11" height="7" fill-opacity="0.64"/><rect x="108" y="286" width="11" height="7" fill-opacity="0.77"/><rect x="120" y="286" width="11" height="7" fill-opacity="0.56"/><rect x="145" y="286" width="11" height="7" fill-opacity="0.06"/><rect x="158" y="286" width="11" height="7" fill-opacity="1.00"/><rect x="182" y="286" width="11" height="7" fill-opacity="0.23"/><rect x="71" y="294" width="11" height="7" fill-opacity="0.29"/><rect x="96" y="294" width="11" height="7" fill-opacity="0.85"/><rect x="108" y="294" width="11" height="7" fill-opacity="0.53"/><rect x="120" y="294" width="11" height="7" fill-opacity="0.40"/><rect x="145" y="294" width="11" height="7" fill-opacity="0.16"/><rect x="158" y="294" width="11" height="7" fill-opacity="0.99"/><rect x="182" y="294" width="11" height="7" fill-opacity="0.28"/><rect x="58" y="302" width="11" height="7" fill-opacity="0.85"/><rect x="96" y="302" width="11" height="7" fill-opacity="0.97"/><rect x="108" y="302" width="11" height="7" fill-opacity="0.24"/><rect x="120" y="302" width="11" height="7" fill-opacity="0.23"/><rect x="145" y="302" width="11" height="7" fill-opacity="0.26"/><rect x="158" y="302" width="11" height="7" fill-opacity="0.97"/><rect x="182" y="302" width="11" height="7" fill-opacity="0.33"/><rect x="46" y="310" width="11" height="7" fill-opacity="0.43"/><rect x="58" y="310" width="11" height="7" fill-opacity="0.90"/><rect x="96" y="310" width="11" height="7" fill-opacity="1.00"/><rect x="120" y="310" width="11" height="7" fill-opacity="0.06"/><rect x="145" y="310" width="11" height="7" fill-opacity="0.35"/><rect x="158" y="310" width="11" height="7" fill-opacity="0.94"/><rect x="182" y="310" width="11" height="7" fill-opacity="0.39"/></g><text x="38.0" y="37.0" font-size="12" text-anchor="end" style="fill:var(--muted)">0</text><text x="38.0" y="117.0" font-size="12" text-anchor="end" style="fill:var(--muted)">10</text><text x="38.0" y="197.0" font-size="12" text-anchor="end" style="fill:var(--muted)">20</text><text x="38.0" y="277.0" font-size="12" text-anchor="end" style="fill:var(--muted)">30</text><text x="51.5" y="334.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">0</text><text x="150.7" y="334.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">8</text><text x="249.9" y="334.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">16</text><text x="349.1" y="334.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">24</text><text x="435.9" y="334.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">31</text>
</svg>
<figcaption>图 3　每一行是一个位置的编码（d = 32），每一列是一维。蓝色是正数，橙色是负数，越深绝对值越大。左边几列变得很快，越往右变得越慢。</figcaption>
</figure>

这套公式还有一个好性质：**往后挪 $k$ 个位置，每一对都只是转了一个固定的角度。** 一步步看第 $i$ 对。记 $a = \omega_i\,\text{pos}$、$b = \omega_i\,k$。往后挪 $k$ 个位置，角度变成 $a + b$。用两角和公式展开：

$$
\sin(a + b) = \sin a \cos b + \cos a \sin b
$$

$$
\cos(a + b) = \cos a \cos b - \sin a \sin b
$$

右边只用到原来的 $\sin a$、$\cos a$，再乘上只和 $b$ 有关的 $\cos b$、$\sin b$。写成矩阵：

$$
\begin{pmatrix} \sin(a+b) \\ \cos(a+b) \end{pmatrix} = M \begin{pmatrix} \sin a \\ \cos a \end{pmatrix}
$$

$$
M = \begin{pmatrix} \cos b & \sin b \\ -\sin b & \cos b \end{pmatrix}
$$

矩阵 $M$只取决于挪了几格 $k$（通过 $b = \omega_i k$），和原来在哪个位置无关。用表里的数验算：第 0 对从位置 1 挪到位置 3，$k = 2$，$b = 2$，$\cos 2 = -0.416$，$\sin 2 = 0.909$：

$$
\begin{aligned}
\sin 3 &= 0.841 \times (-0.416) \\
&\quad + 0.540 \times 0.909 \\
&= -0.350 + 0.491 = 0.141 \\[6pt]
\cos 3 &= 0.540 \times (-0.416) \\
&\quad - 0.841 \times 0.909 \\
&= -0.225 - 0.765 = -0.990
\end{aligned}
$$

和表里位置 3 的 $0.141$、$-0.990$ 一致。论文作者希望模型能借这个性质学会「相隔几个位置」。

可正弦编码是**加**在 $x$ 上的，和第二步一样：$h = x + \operatorname{PE}$。加完之后再乘 $W_Q$、$W_K$，点积会展开成四项：

$$
\begin{aligned}
q \cdot k = {} & \underbrace{(W_Q x_m)\cdot(W_K x_n)}_{\text{内容对内容}} \\
+ {} & \underbrace{(W_Q x_m)\cdot(W_K p_n)}_{\text{内容对位置}} \\
+ {} & \underbrace{(W_Q p_m)\cdot(W_K x_n)}_{\text{位置对内容}} \\
+ {} & \underbrace{(W_Q p_m)\cdot(W_K p_n)}_{\text{位置对位置}}
\end{aligned}
$$

这里 $m$ 是「小米」的位置，$n$ 是被看的词的位置，$p$ 是正弦编码。「挪 $k$ 格就是转一个角度」这个好性质只属于 $p$ 本身；乘上 $W_Q$、$W_K$ 之后，圆被拉扁、拉斜，后三项都不再只取决于 $m - n$。用我们的 2 维例子算一下：取一对、每个位置转 10° 的正弦编码，「小米」在 3、「粮油」在 0 时分数是 8.011；两个都往后挪 10 格（13 和 10），分数变成 2.062。（数字这么大，是因为这里位置向量的长度是 1，比内容向量还长。）相隔都是 3，分数却差了好几倍。

此外，ALiBi 论文（Press 等，2021）实测发现，用正弦编码训练的模型，输入只比训练时长一点，效果就明显变差。

<details class="pause"><summary>停一下：为什么每一对要同时用 sin 和 cos？只用 sin 行不行？</summary>

只用 $\sin$ 会有两个问题。第一，不同角度的 $\sin$ 可能相等：$\sin(1) = \sin(\pi - 1) = 0.841$，位置 1 和位置 $\pi - 1 \approx 2.14$ 分不开。加上 $\cos$ 之后，$\cos(1) = 0.540$、$\cos(\pi - 1) = -0.540$，一对数就能唯一确定一个角度。第二，上面「挪 $k$ 格」的公式里，新的 $\sin$ 既要用到旧的 $\sin$ 也要用到旧的 $\cos$；只有 $\sin$，就没法用一个固定的矩阵算出挪动之后的值。

</details>

## 第四步：RoPE：不加，直接转

上一步的启发是：位置往后挪，就是转一个角度。2021 年，苏剑林等人在 RoFormer 论文里提出：既然如此，干脆**不往 $x$ 上加东西**，而是把 $q$ 和 $k$ 本身按位置转一个角度。这就是**旋转位置编码**（Rotary Position Embedding，RoPE）。先看「转」怎么算。

### 4.1　把一个点转一个角度

平面上一个点 $(a,\ b)$，离原点的距离是 $r = \sqrt{a^2 + b^2}$，和横轴的夹角记作 $\varphi$。它可以写成：

$$
a = r\cos\varphi \qquad b = r\sin\varphi
$$

绕原点逆时针转 $\alpha$，距离 $r$ 不变，角度变成 $\varphi + \alpha$。新的点是：

$$
a' = r\cos(\varphi + \alpha) \qquad b' = r\sin(\varphi + \alpha)
$$

用两角和公式展开第一个：

$$
\begin{aligned}
a' &= r\cos\varphi\cos\alpha - r\sin\varphi\sin\alpha \\
&= a\cos\alpha - b\sin\alpha
\end{aligned}
$$

第二步把 $r\cos\varphi$ 换成 $a$、$r\sin\varphi$ 换成 $b$。第二个同样展开：

$$
\begin{aligned}
b' &= r\sin\varphi\cos\alpha + r\cos\varphi\sin\alpha \\
&= b\cos\alpha + a\sin\alpha
\end{aligned}
$$

写成矩阵，就是**旋转矩阵** $R(\alpha)$：

$$
\begin{pmatrix} a' \\ b' \end{pmatrix} = \underbrace{\begin{pmatrix} \cos\alpha & -\sin\alpha \\ \sin\alpha & \cos\alpha \end{pmatrix}}_{R(\alpha)} \begin{pmatrix} a \\ b \end{pmatrix}
$$

拿「小米」的 $q = (1.0,\ -0.6)$ 转 $30°$ 试试。$\cos 30° = 0.866$，$\sin 30° = 0.5$：

$$
\begin{aligned}
a' &= 1.0 \times 0.866 - (-0.6) \times 0.5 \\
&= 0.866 + 0.3 = 1.166 \\[6pt]
b' &= 1.0 \times 0.5 + (-0.6) \times 0.866 \\
&= 0.5 - 0.520 = -0.020
\end{aligned}
$$

转完是 $(1.166,\ −0.020)$。验算长度：原来 $\sqrt{1.0^2 + 0.6^2} = \sqrt{1.36} = 1.166$，转完 $\sqrt{1.166^2 + 0.020^2} \approx 1.166$，没变。

<figure class="fig">
<svg viewBox="0 0 480 280" role="img" aria-label="把 q 绕原点转 30 度">
<line x1="15" y1="140" x2="285" y2="140" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="150" y1="5" x2="150" y2="275" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="150.0" y1="140.0" x2="260.6" y2="206.3" style="stroke:var(--muted);stroke-width:3;fill:none"/><path d="M270.0 212.0 L259.1 210.7 L263.7 203.0 z" style="fill:var(--muted)"/><line x1="150.0" y1="140.0" x2="278.9" y2="142.2" style="stroke:var(--warn);stroke-width:3.5;fill:none"/><path d="M289.9 142.4 L279.8 146.7 L280.0 137.7 z" style="fill:var(--warn)"/><path d="M194.6 166.8 A52 52 0 0 0 202.0 140.9" style="stroke:var(--warn);stroke-width:1.6;fill:none"/><text x="276.0" y="232.0" font-size="15" text-anchor="start" style="fill:var(--muted)">q (1.00, −0.60)</text><text x="295.9" y="134.4" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--warn)">转 30° 后 (1.17, −0.02)</text><text x="208.0" y="154.0" font-size="14" text-anchor="start" style="fill:var(--warn)">30°</text>
</svg>
<figcaption>图 5　灰色是「小米」原来的 q，橙色是把它绕原点逆时针转 30° 之后。长度不变，只是方向变了。</figcaption>
</figure>

### 4.2　两个向量一起转，点积不变

注意力一讲说过，点积可以写成长度乘长度乘夹角的余弦：

$$
q \cdot k = \lVert q \rVert\,\lVert k \rVert \cos(\varphi_q - \varphi_k)
$$

$\varphi_q$、$\varphi_k$ 是两个向量各自和横轴的夹角，$\varphi_q - \varphi_k$ 就是它们之间的夹角。

代入例子。$q = (1.0,\ -0.6)$，角度 $\varphi_q = \arctan(-0.6 / 1.0) = −30.96°$，长度 $1.166$。「粮油」的 $k = (1,\ -1)$，角度 $\varphi_k = \arctan(-1 / 1) = −45.00°$，长度 $\sqrt{2} = 1.414$。夹角是 $−30.96° - (−45.00°) = 14.04°$，于是：

$$
\begin{aligned}
q \cdot k &= 1.166 \times 1.414 \times \cos 14.04° \\
&= 1.649 \times 0.970 = 1.600
\end{aligned}
$$

和注意力一讲直接算的 1.6 一致。

现在把 $q$ 和 $k$ **都**转 $30°$。长度不变；两个角度各加 $30°$，相减时 $30°$ 正好消掉，夹角还是 $14.04°$。所以点积不变。直接算一遍：$k$ 转 $30°$ 是 $(1 \times 0.866 + 0.5,\ \ 0.5 - 0.866) = (1.366,\ −0.366)$，和转过的 $q = (1.166,\ −0.020)$ 做点积：

$$
\begin{aligned}
& 1.166 \times 1.366 + (-0.020) \times (-0.366) \\
&= 1.593 + 0.007 = 1.600
\end{aligned}
$$

<figure class="fig">
<svg viewBox="0 0 480 275" role="img" aria-label="两个向量一起转同样的角度，点积不变">
<line x1="20" y1="115" x2="220" y2="115" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="120" y1="15" x2="120" y2="215" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="120.0" y1="115.0" x2="180.2" y2="175.2" style="stroke:var(--accent);stroke-width:3;fill:none"/><path d="M188.0 183.0 L177.7 179.1 L184.1 172.7 z" style="fill:var(--accent)"/><line x1="120.0" y1="115.0" x2="178.6" y2="150.1" style="stroke:var(--warn);stroke-width:3;fill:none"/><path d="M188.0 155.8 L177.1 154.5 L181.7 146.8 z" style="fill:var(--warn)"/><path d="M144.0 139.0 A34 34 0 0 0 149.2 132.5" style="stroke:var(--fg);stroke-width:1.4;fill:none"/><text x="120.0" y="239.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">原来</text><text x="120.0" y="261.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">夹角 14.04°</text><line x1="260" y1="115" x2="460" y2="115" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="360" y1="15" x2="360" y2="215" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="360.0" y1="115.0" x2="442.3" y2="137.0" style="stroke:var(--accent);stroke-width:3;fill:none"/><path d="M452.9 139.9 L442.0 141.6 L444.3 133.0 z" style="fill:var(--accent)"/><line x1="360.0" y1="115.0" x2="428.3" y2="116.1" style="stroke:var(--warn);stroke-width:3;fill:none"/><path d="M439.3 116.3 L429.2 120.6 L429.3 111.7 z" style="fill:var(--warn)"/><path d="M392.8 123.8 A34 34 0 0 0 394.0 115.6" style="stroke:var(--fg);stroke-width:1.4;fill:none"/><text x="360.0" y="239.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">两个都转 30°</text><text x="360.0" y="261.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">夹角 14.04°</text><text x="120.0" y="22.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">点积 1.600</text><text x="360.0" y="22.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">点积 1.600</text>
</svg>
<figcaption>图 6　橙色是 q，蓝色是「粮油」的 k。两个一起转 30°，它们之间的夹角还是 14.04°，点积还是 1.6。</figcaption>
</figure>

### 4.3　按位置转：分数只看相对距离

RoPE 的规则是：**位置 $m$ 上的向量转 $m\theta$**。$\theta$ 是一个固定的角度，我们的例子取 $\theta = 10°$。

- 「小米」在位置 $m$，它的 $q$ 转 $m\theta$，角度变成 $\varphi_q + m\theta$。
- 被看的词在位置 $n$，它的 $k$ 转 $n\theta$，角度变成 $\varphi_k + n\theta$。

两者的夹角：

$$
\begin{aligned}
& (\varphi_q + m\theta) - (\varphi_k + n\theta) \\
&= (\varphi_q - \varphi_k) + (m - n)\,\theta
\end{aligned}
$$

括号里的 $m\theta$ 和 $n\theta$ 只剩下差 $(m - n)\theta$。长度又都不变，所以：

$$
\begin{aligned}
q_m \cdot k_n &= \lVert q \rVert\,\lVert k \rVert \\
&\times \cos\big(\varphi_q - \varphi_k + (m - n)\,\theta\big)
\end{aligned}
$$

右边只有 $m - n$，没有单独的 $m$ 或 $n$。**旋转之后的点积只取决于相对距离 $m - n$**。这就是 RoPE 的核心。

用数字验算。「小米」在 3、「粮油」在 0：$q$ 转 $30°$，$k$ 不转，夹角 $14.04° + 30° = 44.04°$，分数 $1.649 \times \cos 44.04° = 1.649 \times 0.719 = 1.186$。

两个都往后挪 10 格，「小米」在 13、「粮油」在 10：$q$ 转 $130°$，$k$ 转 $100°$，夹角 $14.04° + 130° - 100° = 44.04°$，分数还是 $1.186$。

<figure class="fig">
<svg viewBox="0 0 480 275" role="img" aria-label="相对距离相同，分数相同">
<line x1="20" y1="115" x2="220" y2="115" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="120" y1="15" x2="120" y2="215" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="120.0" y1="115.0" x2="180.2" y2="175.2" style="stroke:var(--accent);stroke-width:3;fill:none"/><path d="M188.0 183.0 L177.7 179.1 L184.1 172.7 z" style="fill:var(--accent)"/><line x1="120.0" y1="115.0" x2="188.3" y2="116.1" style="stroke:var(--warn);stroke-width:3;fill:none"/><path d="M199.3 116.3 L189.2 120.6 L189.3 111.7 z" style="fill:var(--warn)"/><path d="M144.0 139.0 A34 34 0 0 0 154.0 115.6" style="stroke:var(--fg);stroke-width:1.4;fill:none"/><text x="120.0" y="239.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">q 在位置 3，k 在位置 0</text><text x="120.0" y="261.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">夹角 44.04°</text><line x1="260" y1="115" x2="460" y2="115" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="360" y1="15" x2="360" y2="215" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="360.0" y1="115.0" x2="408.8" y2="45.2" style="stroke:var(--accent);stroke-width:3;fill:none"/><path d="M415.2 36.2 L413.1 47.0 L405.7 41.9 z" style="fill:var(--accent)"/><line x1="360.0" y1="115.0" x2="349.3" y2="47.5" style="stroke:var(--warn);stroke-width:3;fill:none"/><path d="M347.5 36.7 L353.6 45.9 L344.7 47.3 z" style="fill:var(--warn)"/><path d="M379.5 87.1 A34 34 0 0 0 354.7 81.4" style="stroke:var(--fg);stroke-width:1.4;fill:none"/><text x="360.0" y="239.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">q 在位置 13，k 在位置 10</text><text x="360.0" y="261.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">夹角 44.04°</text><text x="120.0" y="22.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">分数 1.186</text><text x="360.0" y="22.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">分数 1.186</text>
</svg>
<figcaption>图 7　左边 q 转 30°、k 不转；右边 q 转 130°、k 转 100°。两边都差 30°，夹角一样，分数一样。</figcaption>
</figure>

同样的结论也可以用矩阵推一遍，不用画角度。转过之后的点积是 $(R(m\theta)\,q) \cdot (R(n\theta)\,k)$。点积可以写成「前一个转置，乘后一个」：

$$
\begin{aligned}
& (R(m\theta)\,q)^{\top} (R(n\theta)\,k) \\
&= q^{\top}\, R(m\theta)^{\top}\, R(n\theta)\, k
\end{aligned}
$$

这里用了 $(AB)^{\top} = B^{\top}A^{\top}$。旋转矩阵转置之后，右上和左下的 $\sin$ 交换了正负号，正好是往回转：

$$
R(\alpha)^{\top} = \begin{pmatrix} \cos\alpha & \sin\alpha \\ -\sin\alpha & \cos\alpha \end{pmatrix} = R(-\alpha)
$$

先往回转 $m\theta$、再往前转 $n\theta$，合起来就是转 $(n - m)\theta$：$R(-m\theta)\,R(n\theta) = R\big((n - m)\theta\big)$。于是：

$$
q_m \cdot k_n = q^{\top}\, R\big((n - m)\,\theta\big)\, k
$$

中间的矩阵只取决于 $n - m$。两种推法结论相同。

<details class="pause"><summary>停一下：如果反过来，<i>q</i> 在位置 0、<i>k</i> 在位置 3，分数还是 1.186 吗？</summary>

不是。这时 $m - n = -3$，夹角是 $14.04° - 30° = -15.96°$，分数 $1.649 \times \cos(-15.96°) = 1.649 \times 0.961 = 1.586$。RoPE 不只知道相隔几个，还知道谁在前、谁在后。（生成文字时 $q$ 只看前面的词，$m - n$ 总是大于等于 0。）

</details>

### 4.4　四个 token 一起算

把 RoPE 用到整句话上。每个词的 $k$ 按自己的位置转，「小米」的 $q$ 转 $3 \times 10° = 30°$。每个分数只看「小米」和它相隔几格：「粮油」隔 3 格，夹角 $44.04°$，分数 1.186；「小米」对自己隔 0 格，不转，分数还是 1.000。

| 位置 | token | 分数 $s$ | 份额 |
| --- | --- | --- | --- |
| 0 | 粮油 | 1.186 | 33.0% |
| 1 | 店 | 0.643 | 22.5% |
| 2 | 买了 | 0.134 | 15.7% |
| 3 | 小米 | 1.000 | 28.9% |

打乱成「店 买了 粮油 小米」后，「粮油」只隔 1 格，夹角 $14.04° + 10° = 24.04°$，分数 $1.649 \times 0.913 = 1.506$：

| 位置 | token | 分数 $s$ | 份额 |
| --- | --- | --- | --- |
| 0 | 店 | 0.696 | 21.2% |
| 1 | 买了 | 0.185 | 14.8% |
| 2 | 粮油 | 1.506 | 37.7% |
| 3 | 小米 | 1.000 | 26.3% |

两种词序的 $x'$ 分别是 $(0.77,\ 1.54)$ 和 $(0.75,\ 1.60)$，不一样了。

三点要注意：

- **只转 $q$ 和 $k$，不转 $v$。** 位置只影响「看谁、看多少」，不改变从每个词那里拿走的内容。
- **每一层的注意力都转一次**，用的都是这个 token 在整句里的编号。不像前两种办法只在最开始加一次。
- **$x$ 本身不被改动**，没有「内容对位置」那种混在一起的项。

## 第五步：一个转速不够，要很多个

只有一个转速有个毛病：转满 360° 就回到原样。$\theta = 10°$ 时，每 36 个位置转一整圈：

| 位置差 $m - n$ | 夹角 $14.04° + 10° \times (m-n)$ | 分数 $1.649 \cos(\cdot)$ |
| --- | --- | --- |
| 0 | 14.04° | 1.600 |
| 1 | 24.04° | 1.506 |
| 2 | 34.04° | 1.367 |
| 3 | 44.04° | 1.186 |
| 8 | 94.04° | −0.116 |
| 18 | 194.04° | −1.600 |
| 36 | 374.04° | 1.600 |
| 39 | 404.04° | 1.186 |

<figure class="fig">
<svg viewBox="0 0 480 250" role="img" aria-label="只有一个频率时分数随位置差周期变化">
<line x1="50" y1="115.0" x2="450" y2="115.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="50" y1="200" x2="50" y2="30" style="stroke:var(--line);stroke-width:1.2;fill:none"/><polyline points="50.0,39.4 51.7,40.5 53.3,41.8 55.0,43.3 56.7,45.0 58.3,46.9 60.0,49.0 61.7,51.2 63.3,53.7 65.0,56.3 66.7,59.0 68.3,61.9 70.0,65.0 71.7,68.2 73.3,71.5 75.0,74.9 76.7,78.5 78.3,82.1 80.0,85.9 81.7,89.7 83.3,93.6 85.0,97.5 86.7,101.5 88.3,105.6 90.0,109.6 91.7,113.7 93.3,117.8 95.0,121.8 96.7,125.9 98.3,129.9 100.0,133.9 101.7,137.8 103.3,141.7 105.0,145.5 106.7,149.2 108.3,152.8 110.0,156.3 111.7,159.7 113.3,163.0 115.0,166.1 116.7,169.1 118.3,172.0 120.0,174.7 121.7,177.2 123.3,179.6 125.0,181.8 126.7,183.8 128.3,185.6 130.0,187.2 131.7,188.7 133.3,189.9 135.0,190.9 136.7,191.7 138.3,192.3 140.0,192.7 141.7,192.9 143.3,192.8 145.0,192.6 146.7,192.1 148.3,191.4 150.0,190.6 151.7,189.5 153.3,188.2 155.0,186.7 156.7,185.0 158.3,183.1 160.0,181.0 161.7,178.8 163.3,176.3 165.0,173.7 166.7,171.0 168.3,168.1 170.0,165.0 171.7,161.8 173.3,158.5 175.0,155.1 176.7,151.5 178.3,147.9 180.0,144.1 181.7,140.3 183.3,136.4 185.0,132.5 186.7,128.5 188.3,124.4 190.0,120.4 191.7,116.3 193.3,112.2 195.0,108.2 196.7,104.1 198.3,100.1 200.0,96.1 201.7,92.2 203.3,88.3 205.0,84.5 206.7,80.8 208.3,77.2 210.0,73.7 211.7,70.3 213.3,67.0 215.0,63.9 216.7,60.9 218.3,58.0 220.0,55.3 221.7,52.8 223.3,50.4 225.0,48.2 226.7,46.2 228.3,44.4 230.0,42.8 231.7,41.3 233.3,40.1 235.0,39.1 236.7,38.3 238.3,37.7 240.0,37.3 241.7,37.1 243.3,37.2 245.0,37.4 246.7,37.9 248.3,38.6 250.0,39.4 251.7,40.5 253.3,41.8 255.0,43.3 256.7,45.0 258.3,46.9 260.0,49.0 261.7,51.2 263.3,53.7 265.0,56.3 266.7,59.0 268.3,61.9 270.0,65.0 271.7,68.2 273.3,71.5 275.0,74.9 276.7,78.5 278.3,82.1 280.0,85.9 281.7,89.7 283.3,93.6 285.0,97.5 286.7,101.5 288.3,105.6 290.0,109.6 291.7,113.7 293.3,117.8 295.0,121.8 296.7,125.9 298.3,129.9 300.0,133.9 301.7,137.8 303.3,141.7 305.0,145.5 306.7,149.2 308.3,152.8 310.0,156.3 311.7,159.7 313.3,163.0 315.0,166.1 316.7,169.1 318.3,172.0 320.0,174.7 321.7,177.2 323.3,179.6 325.0,181.8 326.7,183.8 328.3,185.6 330.0,187.2 331.7,188.7 333.3,189.9 335.0,190.9 336.7,191.7 338.3,192.3 340.0,192.7 341.7,192.9 343.3,192.8 345.0,192.6 346.7,192.1 348.3,191.4 350.0,190.6 351.7,189.5 353.3,188.2 355.0,186.7 356.7,185.0 358.3,183.1 360.0,181.0 361.7,178.8 363.3,176.3 365.0,173.7 366.7,171.0 368.3,168.1 370.0,165.0 371.7,161.8 373.3,158.5 375.0,155.1 376.7,151.5 378.3,147.9 380.0,144.1 381.7,140.3 383.3,136.4 385.0,132.5 386.7,128.5 388.3,124.4 390.0,120.4 391.7,116.3 393.3,112.2 395.0,108.2 396.7,104.1 398.3,100.1 400.0,96.1 401.7,92.2 403.3,88.3 405.0,84.5 406.7,80.8 408.3,77.2 410.0,73.7 411.7,70.3 413.3,67.0 415.0,63.9 416.7,60.9 418.3,58.0 420.0,55.3 421.7,52.8 423.3,50.4 425.0,48.2 426.7,46.2 428.3,44.4 430.0,42.8 431.7,41.3 433.3,40.1 435.0,39.1 436.7,38.3 438.3,37.7 440.0,37.3 441.7,37.1 443.3,37.2 445.0,37.4 446.7,37.9 448.3,38.6 450.0,39.4" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><circle cx="66.7" cy="59.0" r="6" style="fill:var(--warn)"/><text x="66.7" y="47.0" font-size="15" text-anchor="middle" font-weight="600" style="fill:var(--warn)">3</text><circle cx="266.7" cy="59.0" r="6" style="fill:var(--warn)"/><text x="266.7" y="47.0" font-size="15" text-anchor="middle" font-weight="600" style="fill:var(--warn)">39</text><text x="50.0" y="220.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">0</text><text x="150.0" y="220.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">18</text><text x="250.0" y="220.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">36</text><text x="350.0" y="220.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">54</text><text x="450.0" y="220.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">72</text><text x="450.0" y="240.0" font-size="14" text-anchor="end" style="fill:var(--muted)">位置差 m − n</text><text x="42.0" y="120.0" font-size="13" text-anchor="end" style="fill:var(--muted)">0</text><text x="58.0" y="24.0" font-size="14" text-anchor="start" style="fill:var(--muted)">分数</text>
</svg>
<figcaption>图 8　只有一对、每个位置转 10° 时，分数随位置差变化。转满 360° 就回到原样：位置差 3 和 39 的分数完全一样。</figcaption>
</figure>

位置差 3 和 39 的分数都是 1.186，模型分不清「隔 3 个」和「隔 39 个」。

解决办法和正弦编码一样：多放几根转速不同的指针。真实的 $q$、$k$ 有 $d$ 个数（Llama 3 每个头 $d = 128$），**两个一对**，分成 $d/2 = 64$ 对。每一对是一个 2 维平面，按同样的规则旋转，只是转速各不相同：

$$
\theta_i = b^{-2i/d}, \qquad i = 0, 1, \dots, \tfrac{d}{2} - 1
$$

$b$ 叫**底数**（配置文件里的 `rope_theta`），原论文取 10000，和正弦编码的 $\omega_i$ 是同一个公式。第 $i$ 对在位置 $m$ 上转 $m\theta_i$：

$$
\begin{pmatrix} q'_{2i} \\ q'_{2i+1} \end{pmatrix} = R(m\theta_i) \begin{pmatrix} q_{2i} \\ q_{2i+1} \end{pmatrix}
$$

$R$ 就是 4.1 节的旋转矩阵。$k$ 也一样。点积是各对的点积加起来，每一对都满足第四步的结论，所以总分数还是只取决于 $m - n$：

$$
\begin{aligned}
q_m \cdot k_n = \sum_{i=0}^{d/2 - 1} & \lVert q^{(i)} \rVert\,\lVert k^{(i)} \rVert \\
\times & \cos\big(\varphi^{(i)} + (m - n)\,\theta_i\big)
\end{aligned}
$$

$q^{(i)}$、$k^{(i)}$ 是第 $i$ 对的两个数，$\varphi^{(i)}$ 是这一对在旋转之前的夹角。

先用两对验算。给 $q$、$k$ 各再加一对数，为了简单，第二对和第一对取同样的数，只是转速改成每个位置 $1°$。位置差 3：第一对 1.186，第二对夹角 $14.04° + 3° = 17.04°$，分数 1.577，合计 2.763。位置差 39：第一对仍是 1.186，第二对夹角 $53.04°$，分数 0.992，合计 $\approx$ 2.177。慢的那一对把两者分开了。

$d = 128$、$b = 10000$ 时，64 对的转速：

| 第几对 $i$ | $\theta_i$（rad / 位置） | 每个位置转 | 转一圈要多少个位置 |
| --- | --- | --- | --- |
| 0 | 1 | 57.3° | 6.3 |
| 1 | 0.866 | 49.6° | 7.3 |
| 16 | 0.1 | 5.73° | 62.8 |
| 32 | 0.01 | 0.573° | 628 |
| 48 | 0.001 | 0.0573° | 6,283 |
| 63 | 0.000115 | 0.00662° | 54,410 |

第 0 对每个位置转 57.3°，6.3 个位置一圈；第 63 对每个位置只转 0.0066°，要 54,410 个位置才转一圈。

<figure class="fig">
<svg viewBox="0 0 480 290" role="img" aria-label="频率越多，分数越不会周期性地回到原样">
<line x1="50" y1="120.0" x2="450" y2="120.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><line x1="50" y1="210" x2="50" y2="30" style="stroke:var(--line);stroke-width:1.2;fill:none"/><polyline points="50.0,30.0 51.3,30.2 52.7,30.9 54.0,32.0 55.3,33.5 56.7,35.4 58.0,37.8 59.3,40.5 60.7,43.7 62.0,47.2 63.3,51.1 64.7,55.3 66.0,59.8 67.3,64.6 68.7,69.7 70.0,75.0 71.3,80.5 72.7,86.3 74.0,92.2 75.3,98.2 76.7,104.4 78.0,110.6 79.3,116.9 80.7,123.1 82.0,129.4 83.3,135.6 84.7,141.8 86.0,147.8 87.3,153.7 88.7,159.5 90.0,165.0 91.3,170.3 92.7,175.4 94.0,180.2 95.3,184.7 96.7,188.9 98.0,192.8 99.3,196.3 100.7,199.5 102.0,202.2 103.3,204.6 104.7,206.5 106.0,208.0 107.3,209.1 108.7,209.8 110.0,210.0 111.3,209.8 112.7,209.1 114.0,208.0 115.3,206.5 116.7,204.6 118.0,202.2 119.3,199.5 120.7,196.3 122.0,192.8 123.3,188.9 124.7,184.7 126.0,180.2 127.3,175.4 128.7,170.3 130.0,165.0 131.3,159.5 132.7,153.7 134.0,147.8 135.3,141.8 136.7,135.6 138.0,129.4 139.3,123.1 140.7,116.9 142.0,110.6 143.3,104.4 144.7,98.2 146.0,92.2 147.3,86.3 148.7,80.5 150.0,75.0 151.3,69.7 152.7,64.6 154.0,59.8 155.3,55.3 156.7,51.1 158.0,47.2 159.3,43.7 160.7,40.5 162.0,37.8 163.3,35.4 164.7,33.5 166.0,32.0 167.3,30.9 168.7,30.2 170.0,30.0 171.3,30.2 172.7,30.9 174.0,32.0 175.3,33.5 176.7,35.4 178.0,37.8 179.3,40.5 180.7,43.7 182.0,47.2 183.3,51.1 184.7,55.3 186.0,59.8 187.3,64.6 188.7,69.7 190.0,75.0 191.3,80.5 192.7,86.3 194.0,92.2 195.3,98.2 196.7,104.4 198.0,110.6 199.3,116.9 200.7,123.1 202.0,129.4 203.3,135.6 204.7,141.8 206.0,147.8 207.3,153.7 208.7,159.5 210.0,165.0 211.3,170.3 212.7,175.4 214.0,180.2 215.3,184.7 216.7,188.9 218.0,192.8 219.3,196.3 220.7,199.5 222.0,202.2 223.3,204.6 224.7,206.5 226.0,208.0 227.3,209.1 228.7,209.8 230.0,210.0 231.3,209.8 232.7,209.1 234.0,208.0 235.3,206.5 236.7,204.6 238.0,202.2 239.3,199.5 240.7,196.3 242.0,192.8 243.3,188.9 244.7,184.7 246.0,180.2 247.3,175.4 248.7,170.3 250.0,165.0 251.3,159.5 252.7,153.7 254.0,147.8 255.3,141.8 256.7,135.6 258.0,129.4 259.3,123.1 260.7,116.9 262.0,110.6 263.3,104.4 264.7,98.2 266.0,92.2 267.3,86.3 268.7,80.5 270.0,75.0 271.3,69.7 272.7,64.6 274.0,59.8 275.3,55.3 276.7,51.1 278.0,47.2 279.3,43.7 280.7,40.5 282.0,37.8 283.3,35.4 284.7,33.5 286.0,32.0 287.3,30.9 288.7,30.2 290.0,30.0 291.3,30.2 292.7,30.9 294.0,32.0 295.3,33.5 296.7,35.4 298.0,37.8 299.3,40.5 300.7,43.7 302.0,47.2 303.3,51.1 304.7,55.3 306.0,59.8 307.3,64.6 308.7,69.7 310.0,75.0 311.3,80.5 312.7,86.3 314.0,92.2 315.3,98.2 316.7,104.4 318.0,110.6 319.3,116.9 320.7,123.1 322.0,129.4 323.3,135.6 324.7,141.8 326.0,147.8 327.3,153.7 328.7,159.5 330.0,165.0 331.3,170.3 332.7,175.4 334.0,180.2 335.3,184.7 336.7,188.9 338.0,192.8 339.3,196.3 340.7,199.5 342.0,202.2 343.3,204.6 344.7,206.5 346.0,208.0 347.3,209.1 348.7,209.8 350.0,210.0 351.3,209.8 352.7,209.1 354.0,208.0 355.3,206.5 356.7,204.6 358.0,202.2 359.3,199.5 360.7,196.3 362.0,192.8 363.3,188.9 364.7,184.7 366.0,180.2 367.3,175.4 368.7,170.3 370.0,165.0 371.3,159.5 372.7,153.7 374.0,147.8 375.3,141.8 376.7,135.6 378.0,129.4 379.3,123.1 380.7,116.9 382.0,110.6 383.3,104.4 384.7,98.2 386.0,92.2 387.3,86.3 388.7,80.5 390.0,75.0 391.3,69.7 392.7,64.6 394.0,59.8 395.3,55.3 396.7,51.1 398.0,47.2 399.3,43.7 400.7,40.5 402.0,37.8 403.3,35.4 404.7,33.5 406.0,32.0 407.3,30.9 408.7,30.2 410.0,30.0 411.3,30.2 412.7,30.9 414.0,32.0 415.3,33.5 416.7,35.4 418.0,37.8 419.3,40.5 420.7,43.7 422.0,47.2 423.3,51.1 424.7,55.3 426.0,59.8 427.3,64.6 428.7,69.7 430.0,75.0 431.3,80.5 432.7,86.3 434.0,92.2 435.3,98.2 436.7,104.4 438.0,110.6 439.3,116.9 440.7,123.1 442.0,129.4 443.3,135.6 444.7,141.8 446.0,147.8 447.3,153.7 448.7,159.5 450.0,165.0" style="stroke:var(--line);stroke-width:2;fill:none"/><polyline points="50.0,30.0 51.3,30.1 52.7,30.4 54.0,31.0 55.3,31.8 56.7,32.7 58.0,33.9 59.3,35.3 60.7,36.9 62.0,38.7 63.3,40.6 64.7,42.8 66.0,45.0 67.3,47.5 68.7,50.1 70.0,52.7 71.3,55.6 72.7,58.5 74.0,61.4 75.3,64.5 76.7,67.6 78.0,70.8 79.3,74.0 80.7,77.1 82.0,80.3 83.3,83.5 84.7,86.6 86.0,89.7 87.3,92.7 88.7,95.6 90.0,98.5 91.3,101.2 92.7,103.8 94.0,106.3 95.3,108.6 96.7,110.8 98.0,112.8 99.3,114.7 100.7,116.3 102.0,117.8 103.3,119.0 104.7,120.1 106.0,120.9 107.3,121.6 108.7,122.0 110.0,122.2 111.3,122.2 112.7,122.0 114.0,121.5 115.3,120.9 116.7,120.0 118.0,118.9 119.3,117.7 120.7,116.2 122.0,114.6 123.3,112.7 124.7,110.8 126.0,108.6 127.3,106.3 128.7,103.9 130.0,101.4 131.3,98.7 132.7,96.0 134.0,93.2 135.3,90.3 136.7,87.4 138.0,84.4 139.3,81.4 140.7,78.4 142.0,75.4 143.3,72.5 144.7,69.5 146.0,66.7 147.3,63.9 148.7,61.1 150.0,58.5 151.3,56.0 152.7,53.6 154.0,51.4 155.3,49.3 156.7,47.4 158.0,45.6 159.3,44.0 160.7,42.6 162.0,41.4 163.3,40.4 164.7,39.6 166.0,39.0 167.3,38.7 168.7,38.5 170.0,38.6 171.3,38.9 172.7,39.4 174.0,40.1 175.3,41.1 176.7,42.3 178.0,43.6 179.3,45.2 180.7,47.0 182.0,48.9 183.3,51.1 184.7,53.4 186.0,55.8 187.3,58.4 188.7,61.2 190.0,64.1 191.3,67.0 192.7,70.1 194.0,73.3 195.3,76.5 196.7,79.8 198.0,83.1 199.3,86.5 200.7,89.9 202.0,93.2 203.3,96.6 204.7,99.9 206.0,103.1 207.3,106.3 208.7,109.4 210.0,112.4 211.3,115.3 212.7,118.1 214.0,120.7 215.3,123.2 216.7,125.5 218.0,127.7 219.3,129.7 220.7,131.5 222.0,133.2 223.3,134.6 224.7,135.8 226.0,136.8 227.3,137.6 228.7,138.2 230.0,138.5 231.3,138.7 232.7,138.6 234.0,138.3 235.3,137.8 236.7,137.1 238.0,136.2 239.3,135.1 240.7,133.8 242.0,132.3 243.3,130.6 244.7,128.8 246.0,126.8 247.3,124.7 248.7,122.4 250.0,120.0 251.3,117.5 252.7,114.9 254.0,112.2 255.3,109.5 256.7,106.7 258.0,103.9 259.3,101.0 260.7,98.1 262.0,95.3 263.3,92.5 264.7,89.7 266.0,86.9 267.3,84.3 268.7,81.7 270.0,79.2 271.3,76.8 272.7,74.6 274.0,72.5 275.3,70.5 276.7,68.7 278.0,67.0 279.3,65.6 280.7,64.3 282.0,63.2 283.3,62.3 284.7,61.6 286.0,61.2 287.3,60.9 288.7,60.9 290.0,61.1 291.3,61.5 292.7,62.1 294.0,63.0 295.3,64.0 296.7,65.3 298.0,66.8 299.3,68.5 300.7,70.3 302.0,72.4 303.3,74.6 304.7,77.0 306.0,79.6 307.3,82.3 308.7,85.2 310.0,88.1 311.3,91.2 312.7,94.4 314.0,97.7 315.3,101.0 316.7,104.4 318.0,107.8 319.3,111.2 320.7,114.7 322.0,118.1 323.3,121.6 324.7,124.9 326.0,128.3 327.3,131.5 328.7,134.7 330.0,137.8 331.3,140.8 332.7,143.6 334.0,146.3 335.3,148.9 336.7,151.3 338.0,153.6 339.3,155.7 340.7,157.5 342.0,159.2 343.3,160.7 344.7,162.0 346.0,163.1 347.3,163.9 348.7,164.6 350.0,165.0 351.3,165.2 352.7,165.2 354.0,165.0 355.3,164.5 356.7,163.9 358.0,163.0 359.3,161.9 360.7,160.7 362.0,159.2 363.3,157.6 364.7,155.8 366.0,153.9 367.3,151.8 368.7,149.6 370.0,147.2 371.3,144.7 372.7,142.2 374.0,139.5 375.3,136.8 376.7,134.1 378.0,131.3 379.3,128.5 380.7,125.6 382.0,122.8 383.3,120.0 384.7,117.2 386.0,114.5 387.3,111.9 388.7,109.3 390.0,106.9 391.3,104.5 392.7,102.3 394.0,100.2 395.3,98.2 396.7,96.4 398.0,94.8 399.3,93.3 400.7,92.1 402.0,91.0 403.3,90.1 404.7,89.4 406.0,89.0 407.3,88.7 408.7,88.7 410.0,88.9 411.3,89.3 412.7,89.9 414.0,90.8 415.3,91.8 416.7,93.1 418.0,94.6 419.3,96.2 420.7,98.1 422.0,100.2 423.3,102.4 424.7,104.8 426.0,107.3 427.3,110.0 428.7,112.9 430.0,115.8 431.3,118.9 432.7,122.0 434.0,125.3 435.3,128.6 436.7,131.9 438.0,135.3 439.3,138.7 440.7,142.1 442.0,145.6 443.3,148.9 444.7,152.3 446.0,155.6 447.3,158.8 448.7,162.0 450.0,165.0" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><polyline points="50.0,30.0 51.3,30.4 52.7,31.7 54.0,33.8 55.3,36.4 56.7,39.3 58.0,42.3 59.3,45.3 60.7,47.9 62.0,50.0 63.3,51.7 64.7,52.8 66.0,53.5 67.3,53.8 68.7,53.8 70.0,53.8 71.3,53.8 72.7,54.0 74.0,54.4 75.3,54.9 76.7,55.7 78.0,56.6 79.3,57.5 80.7,58.4 82.0,59.2 83.3,59.8 84.7,60.2 86.0,60.4 87.3,60.5 88.7,60.4 90.0,60.4 91.3,60.4 92.7,60.5 94.0,60.7 95.3,61.1 96.7,61.6 98.0,62.2 99.3,62.8 100.7,63.3 102.0,63.8 103.3,64.2 104.7,64.4 106.0,64.5 107.3,64.4 108.7,64.4 110.0,64.3 111.3,64.3 112.7,64.3 114.0,64.5 115.3,64.8 116.7,65.2 118.0,65.7 119.3,66.2 120.7,66.7 122.0,67.0 123.3,67.3 124.7,67.4 126.0,67.4 127.3,67.3 128.7,67.1 130.0,67.0 131.3,66.9 132.7,67.0 134.0,67.2 135.3,67.5 136.7,67.9 138.0,68.3 139.3,68.8 140.7,69.2 142.0,69.5 143.3,69.7 144.7,69.8 146.0,69.7 147.3,69.5 148.7,69.2 150.0,69.0 151.3,68.9 152.7,68.9 154.0,69.1 155.3,69.4 156.7,69.8 158.0,70.4 159.3,70.9 160.7,71.4 162.0,71.7 163.3,71.9 164.7,71.9 166.0,71.7 167.3,71.4 168.7,71.0 170.0,70.6 171.3,70.3 172.7,70.2 174.0,70.3 175.3,70.6 176.7,71.1 178.0,71.8 179.3,72.5 180.7,73.2 182.0,73.8 183.3,74.2 184.7,74.3 186.0,74.1 187.3,73.7 188.7,73.0 190.0,72.3 191.3,71.6 192.7,71.1 194.0,70.8 195.3,70.9 196.7,71.3 198.0,72.0 199.3,72.9 200.7,74.0 202.0,75.1 203.3,76.1 204.7,76.7 206.0,77.0 207.3,76.9 208.7,76.3 210.0,75.4 211.3,74.3 212.7,73.1 214.0,72.1 215.3,71.3 216.7,70.8 218.0,70.9 219.3,71.4 220.7,72.4 222.0,73.7 223.3,75.2 224.7,76.7 226.0,78.0 227.3,79.0 228.7,79.5 230.0,79.6 231.3,79.1 232.7,78.2 234.0,77.0 235.3,75.6 236.7,74.2 238.0,73.0 239.3,72.1 240.7,71.7 242.0,71.6 243.3,72.1 244.7,72.9 246.0,74.0 247.3,75.3 248.7,76.6 250.0,77.8 251.3,78.8 252.7,79.6 254.0,80.0 255.3,80.2 256.7,80.0 258.0,79.7 259.3,79.1 260.7,78.5 262.0,77.8 263.3,77.1 264.7,76.4 266.0,75.8 267.3,75.3 268.7,74.8 270.0,74.5 271.3,74.3 272.7,74.2 274.0,74.3 275.3,74.6 276.7,75.0 278.0,75.7 279.3,76.6 280.7,77.6 282.0,78.7 283.3,79.8 284.7,80.8 286.0,81.7 287.3,82.3 288.7,82.6 290.0,82.5 291.3,82.1 292.7,81.4 294.0,80.4 295.3,79.3 296.7,78.1 298.0,77.0 299.3,76.1 300.7,75.4 302.0,75.0 303.3,74.9 304.7,75.0 306.0,75.4 307.3,75.9 308.7,76.5 310.0,77.1 311.3,77.7 312.7,78.2 314.0,78.6 315.3,79.0 316.7,79.3 318.0,79.7 319.3,80.2 320.7,80.8 322.0,81.4 323.3,82.1 324.7,82.8 326.0,83.4 327.3,83.8 328.7,84.0 330.0,83.8 331.3,83.4 332.7,82.6 334.0,81.5 335.3,80.2 336.7,78.8 338.0,77.4 339.3,76.3 340.7,75.5 342.0,75.0 343.3,74.9 344.7,75.3 346.0,76.0 347.3,76.9 348.7,78.0 350.0,79.1 351.3,80.0 352.7,80.7 354.0,81.2 355.3,81.4 356.7,81.3 358.0,81.2 359.3,80.9 360.7,80.8 362.0,80.8 363.3,81.1 364.7,81.7 366.0,82.5 367.3,83.4 368.7,84.5 370.0,85.4 371.3,86.1 372.7,86.5 374.0,86.5 375.3,85.9 376.7,85.0 378.0,83.6 379.3,81.9 380.7,80.2 382.0,78.5 383.3,77.0 384.7,76.0 386.0,75.4 387.3,75.3 388.7,75.7 390.0,76.5 391.3,77.6 392.7,78.8 394.0,80.0 395.3,81.1 396.7,82.0 398.0,82.5 399.3,82.7 400.7,82.6 402.0,82.2 403.3,81.8 404.7,81.4 406.0,81.1 407.3,81.0 408.7,81.2 410.0,81.7 411.3,82.4 412.7,83.4 414.0,84.4 415.3,85.4 416.7,86.4 418.0,87.1 419.3,87.6 420.7,87.8 422.0,87.7 423.3,87.3 424.7,86.7 426.0,85.8 427.3,84.9 428.7,83.9 430.0,82.8 431.3,81.8 432.7,80.9 434.0,80.0 435.3,79.3 436.7,78.6 438.0,78.2 439.3,77.9 440.7,77.7 442.0,77.8 443.3,78.1 444.7,78.6 446.0,79.3 447.3,80.1 448.7,81.1 450.0,82.1" style="stroke:var(--warn);stroke-width:2.6;fill:none"/><text x="50.0" y="230.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">0</text><text x="150.0" y="230.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">30</text><text x="250.0" y="230.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">60</text><text x="350.0" y="230.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">90</text><text x="450.0" y="230.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">120</text><text x="450.0" y="250.0" font-size="14" text-anchor="end" style="fill:var(--muted)">位置差 m − n</text><text x="42.0" y="35.0" font-size="13" text-anchor="end" style="fill:var(--muted)">1</text><text x="42.0" y="125.0" font-size="13" text-anchor="end" style="fill:var(--muted)">0</text><text x="42.0" y="215.0" font-size="13" text-anchor="end" style="fill:var(--muted)">−1</text><rect x="50" y="262" width="18" height="4" rx="2" style="fill:var(--line)"/><text x="74.0" y="269.0" font-size="14" text-anchor="start" style="fill:var(--muted)">1 对（10°）</text><rect x="180" y="262" width="18" height="4" rx="2" style="fill:var(--accent)"/><text x="204.0" y="269.0" font-size="14" text-anchor="start" style="fill:var(--accent)">2 对（10°、1°）</text><rect x="330" y="262" width="18" height="4" rx="2" style="fill:var(--warn)"/><text x="354.0" y="269.0" font-size="14" text-anchor="start" style="fill:var(--warn)">64 对（真实）</text>
</svg>
<figcaption>图 9　q 和 k 每一对都同向时，分数（除以对数）随位置差的变化。灰线每 36 个位置回到 1；蓝线要很久才回来；橙线是底数 10000、128 维的 64 对，离得越远越低，不再回到 1。</figcaption>
</figure>

图 9 里还能看到一个趋势：$q$、$k$ 方向一致时，离得越远，分数总体越低。快的对很快就转乱了，各对的余弦有正有负、互相抵消，只剩慢的对还在贡献。RoFormer 论文把这叫作远程衰减：距离远的词默认分数低一些。（真实的 $q$、$k$ 每对的方向由训练决定，不一定都同向，模型也可以利用快的对专门找「前一个词」。）

<details class="pause"><summary>停一下：如果 64 对的转速全都设成一样，会怎样？</summary>

每一对都是同一个周期，总分数里每一项都以同样的周期重复，整个分数和只有一对时一样，每隔一圈就回到原样。取 $\theta = 1$ rad 时，转一圈要 $2\pi \approx 6.28$ 个位置，模型基本分不清离得稍远的词。转速必须拉开，从很快到很慢都有。

</details>

## 第六步：超出训练长度为什么会崩，怎么扩

### 6.1　没见过的角度

模型训练时，输入最长有 $L$ 个 token（训练长度）。在这个长度里，$q$ 和 $k$ 的位置差最多是 $L - 1$，第 $i$ 对见过的夹角变化最多是 $(L - 1)\,\theta_i$。

- **快的对**：转一圈只要几个、几十个位置，$L$ 个位置里转了很多圈，每个角度都见过很多次。
- **慢的对**：转一圈要的位置比 $L$ 还多，训练时只走过圆上的一段弧，剩下的角度从没见过。

输入一旦超过 $L$，慢的对会转到没见过的角度，这几对算出来的分数是模型从没学过怎么读的，注意力就乱了，输出开始胡言乱语。这是目前比较公认的解释（见下面 YaRN 论文）。

用 Llama 3 的数算：$b = 500{,}000$、$d = 128$、训练长度 $L = 8192$。第 $i$ 对转一圈要 $2\pi / \theta_i$ 个位置，8192 个位置里转了 $8192 \div (2\pi/\theta_i)$ 圈。第 0 对转了约 1,304 圈，第 63 对只转了 0.0032 圈。64 对里有 **29 对**连一圈都没转完：

<figure class="fig">
<svg viewBox="0 0 480 250" role="img" aria-label="训练长度内每一对转过的圈数">
<text x="48.0" y="215.0" font-size="12" text-anchor="end" style="fill:var(--muted)">10<tspan dy="-5" font-size="9">−3</tspan></text><text x="48.0" y="189.3" font-size="12" text-anchor="end" style="fill:var(--muted)">10<tspan dy="-5" font-size="9">−2</tspan></text><text x="48.0" y="163.6" font-size="12" text-anchor="end" style="fill:var(--muted)">10<tspan dy="-5" font-size="9">−1</tspan></text><text x="48.0" y="137.9" font-size="12" text-anchor="end" style="fill:var(--muted)">1</text><text x="48.0" y="112.1" font-size="12" text-anchor="end" style="fill:var(--muted)">10</text><text x="48.0" y="86.4" font-size="12" text-anchor="end" style="fill:var(--muted)">10<tspan dy="-5" font-size="9">2</tspan></text><text x="48.0" y="60.7" font-size="12" text-anchor="end" style="fill:var(--muted)">10<tspan dy="-5" font-size="9">3</tspan></text><text x="48.0" y="35.0" font-size="12" text-anchor="end" style="fill:var(--muted)">10<tspan dy="-5" font-size="9">4</tspan></text><line x1="56" y1="132.9" x2="456" y2="132.9" style="stroke:var(--fg);stroke-width:1.2;stroke-dasharray:4 4;fill:none"/><text x="456.0" y="126.9" font-size="13" text-anchor="end" style="fill:var(--fg)">一圈</text><rect x="56.6" y="52.8" width="5.0" height="157.2" style="fill:var(--accent)"/><rect x="62.9" y="55.0" width="5.0" height="155.0" style="fill:var(--accent)"/><rect x="69.1" y="57.3" width="5.0" height="152.7" style="fill:var(--accent)"/><rect x="75.3" y="59.6" width="5.0" height="150.4" style="fill:var(--accent)"/><rect x="81.6" y="61.9" width="5.0" height="148.1" style="fill:var(--accent)"/><rect x="87.8" y="64.2" width="5.0" height="145.8" style="fill:var(--accent)"/><rect x="94.1" y="66.5" width="5.0" height="143.5" style="fill:var(--accent)"/><rect x="100.3" y="68.8" width="5.0" height="141.2" style="fill:var(--accent)"/><rect x="106.6" y="71.1" width="5.0" height="138.9" style="fill:var(--accent)"/><rect x="112.8" y="73.4" width="5.0" height="136.6" style="fill:var(--accent)"/><rect x="119.1" y="75.6" width="5.0" height="134.4" style="fill:var(--accent)"/><rect x="125.3" y="77.9" width="5.0" height="132.1" style="fill:var(--accent)"/><rect x="131.6" y="80.2" width="5.0" height="129.8" style="fill:var(--accent)"/><rect x="137.8" y="82.5" width="5.0" height="127.5" style="fill:var(--accent)"/><rect x="144.1" y="84.8" width="5.0" height="125.2" style="fill:var(--accent)"/><rect x="150.3" y="87.1" width="5.0" height="122.9" style="fill:var(--accent)"/><rect x="156.6" y="89.4" width="5.0" height="120.6" style="fill:var(--accent)"/><rect x="162.8" y="91.7" width="5.0" height="118.3" style="fill:var(--accent)"/><rect x="169.1" y="94.0" width="5.0" height="116.0" style="fill:var(--accent)"/><rect x="175.3" y="96.3" width="5.0" height="113.7" style="fill:var(--accent)"/><rect x="181.6" y="98.5" width="5.0" height="111.5" style="fill:var(--accent)"/><rect x="187.8" y="100.8" width="5.0" height="109.2" style="fill:var(--accent)"/><rect x="194.1" y="103.1" width="5.0" height="106.9" style="fill:var(--accent)"/><rect x="200.3" y="105.4" width="5.0" height="104.6" style="fill:var(--accent)"/><rect x="206.6" y="107.7" width="5.0" height="102.3" style="fill:var(--accent)"/><rect x="212.8" y="110.0" width="5.0" height="100.0" style="fill:var(--accent)"/><rect x="219.1" y="112.3" width="5.0" height="97.7" style="fill:var(--accent)"/><rect x="225.3" y="114.6" width="5.0" height="95.4" style="fill:var(--accent)"/><rect x="231.6" y="116.9" width="5.0" height="93.1" style="fill:var(--accent)"/><rect x="237.8" y="119.2" width="5.0" height="90.8" style="fill:var(--accent)"/><rect x="244.1" y="121.4" width="5.0" height="88.6" style="fill:var(--accent)"/><rect x="250.3" y="123.7" width="5.0" height="86.3" style="fill:var(--accent)"/><rect x="256.6" y="126.0" width="5.0" height="84.0" style="fill:var(--accent)"/><rect x="262.9" y="128.3" width="5.0" height="81.7" style="fill:var(--accent)"/><rect x="269.1" y="130.6" width="5.0" height="79.4" style="fill:var(--accent)"/><rect x="275.4" y="132.9" width="5.0" height="77.1" style="fill:var(--warn)"/><rect x="281.6" y="135.2" width="5.0" height="74.8" style="fill:var(--warn)"/><rect x="287.9" y="137.5" width="5.0" height="72.5" style="fill:var(--warn)"/><rect x="294.1" y="139.8" width="5.0" height="70.2" style="fill:var(--warn)"/><rect x="300.4" y="142.1" width="5.0" height="67.9" style="fill:var(--warn)"/><rect x="306.6" y="144.3" width="5.0" height="65.7" style="fill:var(--warn)"/><rect x="312.9" y="146.6" width="5.0" height="63.4" style="fill:var(--warn)"/><rect x="319.1" y="148.9" width="5.0" height="61.1" style="fill:var(--warn)"/><rect x="325.4" y="151.2" width="5.0" height="58.8" style="fill:var(--warn)"/><rect x="331.6" y="153.5" width="5.0" height="56.5" style="fill:var(--warn)"/><rect x="337.9" y="155.8" width="5.0" height="54.2" style="fill:var(--warn)"/><rect x="344.1" y="158.1" width="5.0" height="51.9" style="fill:var(--warn)"/><rect x="350.4" y="160.4" width="5.0" height="49.6" style="fill:var(--warn)"/><rect x="356.6" y="162.7" width="5.0" height="47.3" style="fill:var(--warn)"/><rect x="362.9" y="165.0" width="5.0" height="45.0" style="fill:var(--warn)"/><rect x="369.1" y="167.2" width="5.0" height="42.8" style="fill:var(--warn)"/><rect x="375.4" y="169.5" width="5.0" height="40.5" style="fill:var(--warn)"/><rect x="381.6" y="171.8" width="5.0" height="38.2" style="fill:var(--warn)"/><rect x="387.9" y="174.1" width="5.0" height="35.9" style="fill:var(--warn)"/><rect x="394.1" y="176.4" width="5.0" height="33.6" style="fill:var(--warn)"/><rect x="400.4" y="178.7" width="5.0" height="31.3" style="fill:var(--warn)"/><rect x="406.6" y="181.0" width="5.0" height="29.0" style="fill:var(--warn)"/><rect x="412.9" y="183.3" width="5.0" height="26.7" style="fill:var(--warn)"/><rect x="419.1" y="185.6" width="5.0" height="24.4" style="fill:var(--warn)"/><rect x="425.4" y="187.8" width="5.0" height="22.2" style="fill:var(--warn)"/><rect x="431.6" y="190.1" width="5.0" height="19.9" style="fill:var(--warn)"/><rect x="437.9" y="192.4" width="5.0" height="17.6" style="fill:var(--warn)"/><rect x="444.1" y="194.7" width="5.0" height="15.3" style="fill:var(--warn)"/><rect x="450.4" y="197.0" width="5.0" height="13.0" style="fill:var(--warn)"/><text x="59.1" y="228.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">0</text><text x="159.1" y="228.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">16</text><text x="259.1" y="228.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">32</text><text x="359.1" y="228.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">48</text><text x="452.9" y="228.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">63</text><text x="456.0" y="248.0" font-size="14" text-anchor="end" style="fill:var(--muted)">第几对 i</text><text x="60.0" y="16.0" font-size="14" text-anchor="start" style="fill:var(--muted)">训练长度 8192 内转过的圈数（对数刻度）</text>
</svg>
<figcaption>图 10　底数 50 万、128 维（Llama 3）时，64 对在 8192 个位置内各转了几圈。蓝色的转满了不止一圈，所有角度都见过；橙色的 29 对连一圈都没转完。</figcaption>
</figure>

下面三种办法都是想让模型在比 $L$ 更长的输入上，仍然只遇到见过的角度。记目标长度是训练长度的 $s$ 倍，例子里取 $s = 4$（8192 扩到 32768）。

### 6.2　位置插值：把位置编号除以 $s$

Chen 等人（2023，Meta）的**位置插值**（Position Interpolation，PI）：位置 $m$ 不再转 $m\theta_i$，而是转 $\dfrac{m}{s}\theta_i$。

$s = 4$ 时，位置差 32768 转的角度和原来位置差 8192 一样，所有角度都回到训练时见过的范围。代价是相邻两个 token 的角度差也缩小到 $1/4$：第 0 对原来相邻差 57.3°，现在只差 14.3°，挨着的词更难分清。所以插值之后要再训练一小会儿。论文用这个办法把 LLaMA 7B 到 65B 的窗口扩到 32768，只训练了不到 1000 步。

### 6.3　NTK-aware：改底数，快的不动、慢的放慢

2023 年网友 bloc97 在 Reddit 的 r/LocalLLaMA 上提出 **NTK-aware** 插值：不改位置编号，而是把底数 $b$ 调大，

$$
b' = b \cdot s^{\,d/(d-2)}
$$

为什么是这个指数？看两头。第 0 对：$\theta_0 = b'^{\,0} = 1$，不管 $b$ 怎么改都不变，最快的指针原样保留。最后一对 $i = d/2 - 1$，指数是 $-2i/d = -(d-2)/d$：

$$
\begin{aligned}
\theta'_{\text{末}} &= \big(b \cdot s^{d/(d-2)}\big)^{-(d-2)/d} \\
&= b^{-(d-2)/d} \cdot s^{-1} = \frac{\theta_{\text{末}}}{s}
\end{aligned}
$$

最慢的一对正好放慢 $s$ 倍，回到见过的范围。中间的对放慢得不到 $s$ 倍：第 $i$ 对的转速变成

$$
\begin{aligned}
\theta'_i = b'^{-2i/d} &= b^{-2i/d} \cdot s^{-2i/(d-2)} \\
&= \frac{\theta_i}{s^{\,2i/(d-2)}}
\end{aligned}
$$

也就是放慢 $s^{2i/(d-2)}$ 倍。所以训练时没转满一圈的那些对，测试时仍会转出一点没见过的角度，只是比直接用少得多。用 Llama 3 的数（$s = 4$）：直接用时，那 29 对都转到训练时的 4 倍远；改底数之后，其中最快的第 35 对放慢 $4^{70/126} \approx 2.16$ 倍，只转到训练时的 $4 / 2.16 \approx 1.85$ 倍，越往后越接近 1 倍，最后一对正好 1 倍。

代入 $b = 500{,}000$、$d = 128$、$s = 4$：$b' = 500{,}000 \times 4^{128/126} \approx$ 2,044,497。这种办法改动小，不训练也能用上一些，但正因为中间那些对还会稍微超出，扩得太多就不行了。

### 6.4　YaRN：分段处理，再调一下温度

Peng 等人（2023）的 **YaRN** 把两者结合，按每一对在训练长度里转了几圈（记作 $r_i = L \cdot \theta_i / 2\pi$）分三段：

- $r_i < 1$（没转满一圈）：放慢 $s$ 倍，和位置插值一样。
- $r_i > 32$（转了很多圈）：完全不动，保住相邻词的分辨率。
- 中间：两者线性过渡。

（1 和 32 是论文对 Llama 系列实验出来的值。）Llama 3 的数代入，64 对里 29 对放慢、19 对不动、16 对过渡：

<figure class="fig">
<svg viewBox="0 0 480 280" role="img" aria-label="三种扩展办法下每一对转速的倍数">
<line x1="56" y1="40.0" x2="456" y2="40.0" style="stroke:var(--line);stroke-width:1;fill:none"/><text x="48.0" y="45.0" font-size="13" text-anchor="end" style="fill:var(--muted)">1</text><line x1="56" y1="140.0" x2="456" y2="140.0" style="stroke:var(--line);stroke-width:1;fill:none"/><text x="48.0" y="145.0" font-size="13" text-anchor="end" style="fill:var(--muted)">1/2</text><line x1="56" y1="190.0" x2="456" y2="190.0" style="stroke:var(--line);stroke-width:1;fill:none"/><text x="48.0" y="195.0" font-size="13" text-anchor="end" style="fill:var(--muted)">1/4</text><polyline points="59.1,190.0 65.4,190.0 71.6,190.0 77.9,190.0 84.1,190.0 90.4,190.0 96.6,190.0 102.9,190.0 109.1,190.0 115.4,190.0 121.6,190.0 127.9,190.0 134.1,190.0 140.4,190.0 146.6,190.0 152.9,190.0 159.1,190.0 165.4,190.0 171.6,190.0 177.9,190.0 184.1,190.0 190.4,190.0 196.6,190.0 202.9,190.0 209.1,190.0 215.4,190.0 221.6,190.0 227.9,190.0 234.1,190.0 240.4,190.0 246.6,190.0 252.9,190.0 259.1,190.0 265.4,190.0 271.6,190.0 277.9,190.0 284.1,190.0 290.4,190.0 296.6,190.0 302.9,190.0 309.1,190.0 315.4,190.0 321.6,190.0 327.9,190.0 334.1,190.0 340.4,190.0 346.6,190.0 352.9,190.0 359.1,190.0 365.4,190.0 371.6,190.0 377.9,190.0 384.1,190.0 390.4,190.0 396.6,190.0 402.9,190.0 409.1,190.0 415.4,190.0 421.6,190.0 427.9,190.0 434.1,190.0 440.4,190.0 446.6,190.0 452.9,190.0" style="stroke:var(--muted);stroke-width:2.4;stroke-dasharray:6 4;fill:none"/><polyline points="59.1,40.0 65.4,44.4 71.6,48.6 77.9,52.8 84.1,56.9 90.4,60.8 96.6,64.7 102.9,68.6 109.1,72.3 115.4,75.9 121.6,79.5 127.9,83.0 134.1,86.4 140.4,89.8 146.6,93.0 152.9,96.2 159.1,99.4 165.4,102.4 171.6,105.4 177.9,108.3 184.1,111.2 190.4,114.0 196.6,116.8 202.9,119.4 209.1,122.1 215.4,124.6 221.6,127.1 227.9,129.6 234.1,132.0 240.4,134.3 246.6,136.6 252.9,138.9 259.1,141.1 265.4,143.2 271.6,145.4 277.9,147.4 284.1,149.4 290.4,151.4 296.6,153.3 302.9,155.2 309.1,157.1 315.4,158.9 321.6,160.6 327.9,162.4 334.1,164.0 340.4,165.7 346.6,167.3 352.9,168.9 359.1,170.4 365.4,172.0 371.6,173.4 377.9,174.9 384.1,176.3 390.4,177.7 396.6,179.0 402.9,180.4 409.1,181.7 415.4,182.9 421.6,184.2 427.9,185.4 434.1,186.6 440.4,187.8 446.6,188.9 452.9,190.0" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><polyline points="59.1,40.0 65.4,40.0 71.6,40.0 77.9,40.0 84.1,40.0 90.4,40.0 96.6,40.0 102.9,40.0 109.1,40.0 115.4,40.0 121.6,40.0 127.9,40.0 134.1,40.0 140.4,40.0 146.6,40.0 152.9,40.0 159.1,40.0 165.4,40.0 171.6,40.0 177.9,66.6 184.1,90.4 190.4,109.7 196.6,125.5 202.9,138.4 209.1,148.8 215.4,157.4 221.6,164.3 227.9,170.0 234.1,174.6 240.4,178.3 246.6,181.4 252.9,183.9 259.1,185.9 265.4,187.6 271.6,188.9 277.9,190.0 284.1,190.0 290.4,190.0 296.6,190.0 302.9,190.0 309.1,190.0 315.4,190.0 321.6,190.0 327.9,190.0 334.1,190.0 340.4,190.0 346.6,190.0 352.9,190.0 359.1,190.0 365.4,190.0 371.6,190.0 377.9,190.0 384.1,190.0 390.4,190.0 396.6,190.0 402.9,190.0 409.1,190.0 415.4,190.0 421.6,190.0 427.9,190.0 434.1,190.0 440.4,190.0 446.6,190.0 452.9,190.0" style="stroke:var(--warn);stroke-width:2.8;fill:none"/><text x="59.1" y="218.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">0</text><text x="159.1" y="218.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">16</text><text x="259.1" y="218.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">32</text><text x="359.1" y="218.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">48</text><text x="452.9" y="218.0" font-size="12" text-anchor="middle" style="fill:var(--muted)">63</text><text x="456.0" y="238.0" font-size="14" text-anchor="end" style="fill:var(--muted)">第几对 i</text><rect x="56" y="250" width="18" height="4" rx="2" style="fill:var(--muted)"/><text x="80.0" y="257.0" font-size="14" text-anchor="start" style="fill:var(--muted)">位置插值</text><rect x="176" y="250" width="18" height="4" rx="2" style="fill:var(--accent)"/><text x="200.0" y="257.0" font-size="14" text-anchor="start" style="fill:var(--accent)">NTK-aware</text><rect x="306" y="250" width="18" height="4" rx="2" style="fill:var(--warn)"/><text x="330.0" y="257.0" font-size="14" text-anchor="start" style="fill:var(--warn)">YaRN（分段）</text>
</svg>
<figcaption>图 11　把 8192 扩到 4 倍（s = 4，底数 50 万）时，每一对的转速变成原来的几倍。位置插值全部放慢 4 倍；NTK-aware 快的几乎不变、慢的放慢 4 倍；YaRN 快的完全不动、慢的放慢 4 倍、中间平滑过渡。</figcaption>
</figure>

YaRN 还给分数乘一个略大于 1 的系数：窗口变长后，每个词要分给更多的词，份额被摊薄、变得平均，乘一个系数把它拉回来。论文的经验公式是

$$
\sqrt{1/t} = 0.1 \ln s + 1
$$

$s = 4$ 时 $\sqrt{1/t} = 0.1 \times 1.386 + 1 = 1.139$，$q$ 和 $k$ 各乘这个数，分数就乘了 $1.139^2 = 1.296$。论文用 YaRN 把 Llama 2 7B、13B 扩到 128K，先训练 400 步（$s = 16$），再加 200 步到 $s = 32$。

<details class="pause"><summary>停一下：位置插值 s = 4 时，第 0 对上相邻两个 token 的角度差是多少？YaRN 呢？</summary>

位置插值：$57.3° / 4 = 14.3°$。YaRN：第 0 对在 8192 个位置里转了约 1304 圈，远大于 32，完全不动，仍是 57.3°。这就是 YaRN 比单纯插值好的地方：快的指针不受影响，相邻的词照样分得清。

</details>

## 回到真实模型：Llama 3

以 Meta 公开的配置文件为准：

| | Llama 3 8B | Llama 3.1 8B |
| --- | --- | --- |
| 每个头的维度 | 128（64 对） | 128（64 对） |
| `rope_theta`（底数 $b$） | 500,000 | 500,000 |
| `max_position_embeddings` | 8,192 | 131,072 |
| `rope_scaling` | 无 | `rope_type: llama3`，`factor: 8`，`low_freq_factor: 1`，`high_freq_factor: 4`，`original_max_position_embeddings: 8192` |

几点说明：

- **底数从 10000 调到 50 万。** Llama 2 用的是原论文的 10000。Llama 3 论文写道，把底数调大到 500,000 是为了更好地支持长上下文。底数越大，最慢的指针越慢：$b = 500{,}000$ 时第 63 对每个位置只转 $2.46 × 10^{-6}$ rad，要 2,559,196 个位置才转一圈，远处的位置差也能对应到互不相同的角度。
- **Llama 3.1 的 `rope_scaling` 就是 YaRN 那种分段思路。** 转一圈要的位置少于 $8192 / 4 = 2048$ 的对（快的）不动，共 29 对；多于 $8192 / 1 = 8192$ 的对（慢的）放慢 8 倍，共 29 对；中间 6 对平滑过渡。`low_freq_factor`、`high_freq_factor` 就是这两条分界线。再加上 Llama 3 论文里分 6 个阶段、约 800B token 的长上下文训练，窗口从 8K 扩到 128K。
- **每个头用同样的 64 个转速**，32 个查询头和 8 个 KV 头都按同样的角度转。
- **「一对」不一定是挨着的两个数。** RoFormer 原文把第 $2i$、$2i+1$ 个数配成一对；Hugging Face 的 Llama 实现把第 $i$ 个和第 $i + 64$ 个配成一对。只是排列不同，转法一样，但两种写法的权重不能混用。
- **KV Cache 里存的是转过的 $k$。** 一个 token 的位置定下来就不会变，它的 $k$ 转一次存起来，后面每一步直接用。

## 实验里讲了什么

1. **打乱词序。** 拖动前三个词的顺序，分别在不加位置、加位置向量、RoPE 三种情况下，看「小米」的分数、份额和 $x'$ 变不变。
2. **正弦位置编码。** 改维度和底数，看热力图；选一个位置，看各对指针的角度；任意两个位置的编码有多像。
3. **RoPE 旋转盘。** 拖「小米」和「粮油」的位置，看 $q$、$k$ 怎么转，分数怎么跟着位置差走；两个一起挪，分数不变。
4. **多频率叠加。** 改对数和底数，看分数随位置差的曲线怎么从周期变成不再回头。
5. **超出训练长度。** 选训练长度、测试长度和扩展办法（直接用、位置插值、NTK-aware、YaRN、Llama 3），看哪些对转到了训练时没见过的角度，相邻词的角度差还剩多少。

## 和前后两讲的关系

上一讲拆开了一个注意力头：$q$ 找 $k$、按份额读 $v$。这一讲补上它缺的东西：词序。RoPE 就是在算 $q \cdot k$ 之前，把 $q$ 和 $k$ 按位置转一下。下一讲把一个头扩成几十个头，讲为什么要切成多头，又为什么让几个查询头共用一组 $k$、$v$（GQA）；每个头都按这一讲的办法旋转。之后的 KV Cache 一讲里存下来的，就是转过之后的 $k$。

## 延伸阅读

- Vaswani et al., *Attention Is All You Need* (2017)，正弦位置编码
- Su et al., *RoFormer: Enhanced Transformer with Rotary Position Embedding* (2021)，RoPE
- Press, Smith, Lewis, *Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation* (2021)，ALiBi
- Chen et al., *Extending Context Window of Large Language Models via Positional Interpolation* (2023)
- Peng et al., *YaRN: Efficient Context Window Extension of Large Language Models* (2023)
- Kazemnejad et al., *The Impact of Positional Encoding on Length Generalization in Transformers* (2023)，NoPE
- Meta, *The Llama 3 Herd of Models* (2024)
