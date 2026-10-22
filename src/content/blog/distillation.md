---
title: "蒸馏：小模型怎么向大模型学"
description: "一张猫的图片，硬标签只说「是猫」，老师的概率还说「有点像狗，一点也不像汽车」。用一组能手算的数字，一步步推出温度、KL 散度损失和为什么要乘 T²；在浏览器里真的训练一个老师和一批学生；再看序列级蒸馏和 DeepSeek-R1 怎么把推理能力蒸馏进 1.5B 到 70B 的小模型，以及蒸馏学不到什么。"
pubDate: 2026-10-22
tags: ["蒸馏", "软标签", "KL 散度", "温度", "DeepSeek-R1"]
lab: /labs/distillation/
series: ai-mastery
order: 44
---

<!-- 本文由 labs-src/distillation/toy.py 从 article.src.md 生成，图和数字都由脚本算出（训练结果来自 run_lab.mjs 跑实验页里的同一段代码）。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

蒸馏（distillation）就是让一个小模型（学生）去模仿一个大模型（老师）的输出，而不只是模仿标准答案。老师的输出是一个概率分布，里面除了「哪个对」，还藏着「错的那些里，哪些错得不离谱」；把它除以一个温度 $T$ 再做 softmax，这些小概率就被放大到学生学得到的程度。损失用老师和学生分布之间的 KL 散度，再乘 $T^2$ 补回温度带来的梯度缩小。到了大模型，最常见的做法更简单：让老师写出大量回答，学生直接拿来做 SFT。DeepSeek-R1 就是这样把长推理的能力，交给了 1.5B 到 70B 的六个小模型。

## 从一个问题开始：大模型太贵，小模型太笨

上一讲推理模型讲到，一个大模型多想一会儿，答案会更好；可它每个 token 都要过一遍几百 B 的参数，又慢又贵。小模型便宜，但从头训出来的小模型往往不够聪明。

一个自然的想法：既然大模型已经训好了，能不能让小模型**向大模型学**，而不是从零学？这就是蒸馏。被模仿的大模型叫**老师**（teacher），模仿它的小模型叫**学生**（student）。

问题是：老师能教给学生什么，是训练数据里本来没有的？要回答这个问题，先回到最简单的情形：分类。

## 第一步：硬标签只说对错

假设一个图片分类模型要从 4 个类别里选：猫、狗、狐狸、汽车。给它一张猫的照片。

训练数据里，这张照片的标签写的是「猫」。写成向量，就是在「猫」那一格放 1，其余放 0：

$$
y = (1,\ 0,\ 0,\ 0)
$$

这种只有一格是 1 的标签叫**硬标签**（hard label），也叫 one-hot。它只告诉模型一件事：这是猫。至于狗、狐狸、汽车，它们一律是 0，一样地「不对」。

老师是一个已经训好的大模型。它看这张照片，给 4 个类别各打一个分数，叫 logit（softmax 之前的分数，单位就是一个数，可正可负）。我们的例子里，老师的 logits 是：

$$
v = (4,\ 1,\ 0,\ -5)
$$

依次对应猫、狗、狐狸、汽车。这组数字会一直用到最后。（4 个数的平均正好是 $0$，第六步会用到这一点。）

把 logits 变成概率用 softmax（向量与 softmax 那一讲讲过）：每个数取指数，再除以总和。先算 4 个指数：

$$
e^{4} = 54.598,\quad e^{1} = 2.718,\quad e^{0} = 1.000,\quad e^{-5} = 0.00674
$$

加起来：

$$
54.598 + 2.718 + 1.000 + 0.00674 = 58.323
$$

每个除以总和，就是老师给的概率：

$$
p = (0.936,\ 0.047,\ 0.017,\ 0.00012)
$$

<figure class="fig">
<svg viewBox="0 0 480 238" role="img" aria-label="硬标签与老师在温度 1 下的概率">
<rect x="20.0" y="12.0" width="12.0" height="12.0" rx="3" style="fill:var(--muted)"/><text x="38.0" y="22.0" font-size="14" text-anchor="start" style="fill:var(--muted)">硬标签</text><rect x="95.0" y="12.0" width="12.0" height="12.0" rx="3" style="fill:var(--accent)"/><text x="113.0" y="22.0" font-size="14" text-anchor="start" style="fill:var(--muted)">老师的概率（T = 1）</text><line x1="20.0" y1="200.0" x2="460.0" y2="200.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><rect x="38.0" y="62.0" width="34.0" height="138.0" rx="3" style="fill:var(--muted)"/><rect x="78.0" y="70.8" width="34.0" height="129.2" rx="3" style="fill:var(--accent)"/><text x="95.0" y="64.8" font-size="14" text-anchor="middle" style="fill:var(--accent)">93.6%</text><text x="55.0" y="56.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><text x="75.0" y="224.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">猫</text><rect x="148.0" y="200.0" width="34.0" height="0.0" rx="3" style="fill:var(--muted)"/><rect x="188.0" y="193.6" width="34.0" height="6.4" rx="3" style="fill:var(--accent)"/><text x="205.0" y="187.6" font-size="14" text-anchor="middle" style="fill:var(--accent)">4.7%</text><text x="185.0" y="224.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">狗</text><rect x="258.0" y="200.0" width="34.0" height="0.0" rx="3" style="fill:var(--muted)"/><rect x="298.0" y="197.6" width="34.0" height="2.4" rx="3" style="fill:var(--accent)"/><text x="315.0" y="191.6" font-size="14" text-anchor="middle" style="fill:var(--accent)">1.7%</text><text x="295.0" y="224.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">狐狸</text><rect x="368.0" y="200.0" width="34.0" height="0.0" rx="3" style="fill:var(--muted)"/><rect x="408.0" y="200.0" width="34.0" height="0.0" rx="3" style="fill:var(--accent)"/><text x="425.0" y="194.0" font-size="14" text-anchor="middle" style="fill:var(--accent)">0.01%</text><text x="405.0" y="224.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">汽车</text>
</svg>
<figcaption>图 1　同一张猫的图片。灰色是硬标签：猫 1，其余全是 0。蓝色是老师的概率：猫 93.6%，狗 4.7%，狐狸 1.7%，汽车 0.012%（在柱子底部，几乎看不见）。</figcaption>
</figure>

老师和硬标签都认为这是猫。差别在剩下那 3 个类别上。

## 第二步：老师的概率里藏着「错得不离谱」

看老师给错误类别的概率：狗 4.7%，狐狸 1.7%，汽车 0.012%。都很小，但它们之间差得很多。算狗和汽车的比值：两个概率的分母都是总和 $58.323$，相除时约掉，只剩两个指数相除：

$$
\frac{p_{\text{狗}}}{p_{\text{汽车}}} = \frac{e^{1}}{e^{-5}} = \frac{2.718}{0.00674} \approx 403
$$

也就是说，老师觉得这张图「被看成狗」的可能性，是「被看成汽车」的约 403 倍。这正是它从大量图片里学到的知识：猫和狗都是毛茸茸的四条腿动物，猫和汽车毫不相干。

硬标签里没有这个信息：狗和汽车都是 0。Hinton 等人 2015 年提出蒸馏的论文里举的例子是：一张宝马车的图片，被误认成垃圾车的概率很小，但仍比被误认成胡萝卜大很多倍。这些「错的概率之间的比例」告诉学生**类别之间谁和谁像**。他们把老师的这种输出叫**软标签**（soft target）。

还有一个推论：同一张图，硬标签只说了一件事（是哪一类），软标签给的是 4 个数之间的全部比例。每个训练样本能教给学生的东西更多，所以学生可以用更少的数据学。第七步会在浏览器里真的验证这一点。

可是直接用 $T = 1$ 的软标签有一个麻烦：狗只有 4.7%，汽车只有 0.012%，这些数太小了。下一步会看到，损失里每一项是「目标概率 × 某个数」，目标概率这么小，这几项几乎不影响损失，学生也就几乎学不到它们。要先把这些小概率放大。

## 第三步：温度把小概率放大

办法是在 softmax 之前，把每个 logit 除以同一个数 $T$，叫**温度**（temperature）：

$$
p_i = \frac{e^{v_i/T}}{\sum_j e^{v_j/T}}
$$

$T = 1$ 就是普通的 softmax。（温度在向量与 softmax 那一讲出现过，这里是同一个东西。）

用 $T = 4$ 手算一遍。先把每个 logit 除以 4：

$$
\frac{v}{4} = \left(\frac{4}{4},\ \frac{1}{4},\ \frac{0}{4},\ \frac{-5}{4}\right) = (1,\ 0.25,\ 0,\ -1.25)
$$

取指数：

$$
e^{1} = 2.718,\quad e^{0.25} = 1.284,\quad e^{0} = 1.000,\quad e^{-1.25} = 0.287
$$

总和是 $5.289$，每个除以总和：

$$
p^{(4)} = (0.514,\ 0.243,\ 0.189,\ 0.054)
$$

上标 $(4)$ 表示这是温度 4 下的分布。猫从 93.6% 降到 51.4%，狗从 4.7% 升到 24.3%，汽车从 0.012% 升到 5.4%。

<figure class="fig">
<svg viewBox="0 0 480 336" role="img" aria-label="老师在温度 1、2、4、10 下的分布">
<text x="14.0" y="26.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">T = 1</text><line x1="10.0" y1="134.0" x2="230.0" y2="134.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><rect x="22.5" y="46.0" width="30.0" height="88.0" rx="3" style="fill:var(--accent)"/><text x="37.5" y="41.0" font-size="13" text-anchor="middle" style="fill:var(--accent)">94</text><text x="37.5" y="152.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">猫</text><rect x="77.5" y="129.6" width="30.0" height="4.4" rx="3" style="fill:var(--accent)"/><text x="92.5" y="124.6" font-size="13" text-anchor="middle" style="fill:var(--accent)">5</text><text x="92.5" y="152.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">狗</text><rect x="132.5" y="132.4" width="30.0" height="1.6" rx="3" style="fill:var(--accent)"/><text x="147.5" y="127.4" font-size="13" text-anchor="middle" style="fill:var(--accent)">2</text><text x="147.5" y="152.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">狐狸</text><rect x="187.5" y="134.0" width="30.0" height="0.0" rx="3" style="fill:var(--accent)"/><text x="202.5" y="129.0" font-size="13" text-anchor="middle" style="fill:var(--accent)">0.01</text><text x="202.5" y="152.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">汽车</text><text x="254.0" y="26.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">T = 2</text><line x1="250.0" y1="134.0" x2="470.0" y2="134.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><rect x="262.5" y="65.4" width="30.0" height="68.6" rx="3" style="fill:var(--accent)"/><text x="277.5" y="60.4" font-size="13" text-anchor="middle" style="fill:var(--accent)">73</text><text x="277.5" y="152.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">猫</text><rect x="317.5" y="118.7" width="30.0" height="15.3" rx="3" style="fill:var(--accent)"/><text x="332.5" y="113.7" font-size="13" text-anchor="middle" style="fill:var(--accent)">16</text><text x="332.5" y="152.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">狗</text><rect x="372.5" y="124.7" width="30.0" height="9.3" rx="3" style="fill:var(--accent)"/><text x="387.5" y="119.7" font-size="13" text-anchor="middle" style="fill:var(--accent)">10</text><text x="387.5" y="152.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">狐狸</text><rect x="427.5" y="133.2" width="30.0" height="0.8" rx="3" style="fill:var(--accent)"/><text x="442.5" y="128.2" font-size="13" text-anchor="middle" style="fill:var(--accent)">1</text><text x="442.5" y="152.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">汽车</text><text x="14.0" y="192.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">T = 4</text><line x1="10.0" y1="300.0" x2="230.0" y2="300.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><rect x="22.5" y="251.7" width="30.0" height="48.3" rx="3" style="fill:var(--accent)"/><text x="37.5" y="246.7" font-size="13" text-anchor="middle" style="fill:var(--accent)">51</text><text x="37.5" y="318.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">猫</text><rect x="77.5" y="277.2" width="30.0" height="22.8" rx="3" style="fill:var(--accent)"/><text x="92.5" y="272.2" font-size="13" text-anchor="middle" style="fill:var(--accent)">24</text><text x="92.5" y="318.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">狗</text><rect x="132.5" y="282.2" width="30.0" height="17.8" rx="3" style="fill:var(--accent)"/><text x="147.5" y="277.2" font-size="13" text-anchor="middle" style="fill:var(--accent)">19</text><text x="147.5" y="318.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">狐狸</text><rect x="187.5" y="294.9" width="30.0" height="5.1" rx="3" style="fill:var(--accent)"/><text x="202.5" y="289.9" font-size="13" text-anchor="middle" style="fill:var(--accent)">5</text><text x="202.5" y="318.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">汽车</text><text x="254.0" y="192.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">T = 10</text><line x1="250.0" y1="300.0" x2="470.0" y2="300.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><rect x="262.5" y="266.6" width="30.0" height="33.4" rx="3" style="fill:var(--accent)"/><text x="277.5" y="261.6" font-size="13" text-anchor="middle" style="fill:var(--accent)">35</text><text x="277.5" y="318.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">猫</text><rect x="317.5" y="275.3" width="30.0" height="24.7" rx="3" style="fill:var(--accent)"/><text x="332.5" y="270.3" font-size="13" text-anchor="middle" style="fill:var(--accent)">26</text><text x="332.5" y="318.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">狗</text><rect x="372.5" y="277.6" width="30.0" height="22.4" rx="3" style="fill:var(--accent)"/><text x="387.5" y="272.6" font-size="13" text-anchor="middle" style="fill:var(--accent)">24</text><text x="387.5" y="318.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">狐狸</text><rect x="427.5" y="286.4" width="30.0" height="13.6" rx="3" style="fill:var(--accent)"/><text x="442.5" y="281.4" font-size="13" text-anchor="middle" style="fill:var(--accent)">14</text><text x="442.5" y="318.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">汽车</text>
</svg>
<figcaption>图 2　同一组 logits，除以不同的温度再做 softmax（柱顶数字是百分比）。T 越大，分布越平：猫的份额让出来，狗、狐狸、汽车一个个露出来，但排序始终不变。</figcaption>
</figure>

为什么除以 $T$ 会让分布变平？看两个类别概率的比值。分母相同，约掉之后只剩分子：

$$
\frac{p_{\text{狗}}}{p_{\text{汽车}}} = \frac{e^{v_{\text{狗}}/T}}{e^{v_{\text{汽车}}/T}} = e^{(v_{\text{狗}} - v_{\text{汽车}})/T} = e^{(1-(-5))/T} = e^{6/T}
$$

$T = 1$ 时是 $e^{6} \approx 403$；$T = 4$ 时是 $e^{1.5} \approx 4.48$。logit 的差被 $T$ 除小了，比值就从几百倍缩到几倍。但只要 $T > 0$，差的正负号不变，**排序不变**：老师仍然认为猫 > 狗 > 狐狸 > 汽车，只是把这个排序说得更「大声」，让学生听得见。

<details class="pause"><summary>停一下：T 一直加大，比如 T = 1000，分布会变成什么样？还有用吗？</summary>

$T = 1000$ 时，每个 $v_i/T$ 都接近 0，每个 $e^{v_i/T}$ 都接近 1，4 个概率都接近 $1/4$。排序在数学上还在，但差别小到几乎为 0，学生学到的只剩「4 个类别差不多」，连「这是猫」都快看不出来了。所以 $T$ 不是越大越好。Hinton 等人在 MNIST 上用的是 $T = 20$，实际中常见 1 到 20 之间，要按任务试。

</details>

## 第四步：软标签的损失：交叉熵与 KL 散度

现在学生要去对齐老师的分布。学生也是一个模型，对同一张图给出自己的 logits：

$$
z = (2,\ 0,\ 1,\ -3)
$$

（同样平均为 0。）注意学生把狐狸（1）排在了狗（0）前面，和老师的看法不同。

学生也在**同一个温度** $T = 4$ 下做 softmax。$z/4 = (0.5,\ 0,\ 0.25,\ -0.75)$，取指数是 $1.649,\ 1.000,\ 1.284,\ 0.472$，总和 $4.405$，所以：

$$
q^{(4)} = (0.374,\ 0.227,\ 0.291,\ 0.107)
$$

<figure class="fig">
<svg viewBox="0 0 480 230" role="img" aria-label="温度 4 下老师与学生的分布">
<rect x="20.0" y="12.0" width="12.0" height="12.0" rx="3" style="fill:var(--accent)"/><text x="38.0" y="22.0" font-size="14" text-anchor="start" style="fill:var(--muted)">老师 p（T = 4）</text><rect x="215.0" y="12.0" width="12.0" height="12.0" rx="3" style="fill:var(--warn)"/><text x="233.0" y="22.0" font-size="14" text-anchor="start" style="fill:var(--muted)">学生 q（T = 4）</text><line x1="20.0" y1="196.0" x2="460.0" y2="196.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><rect x="41.0" y="71.0" width="32.0" height="125.0" rx="3" style="fill:var(--accent)"/><rect x="77.0" y="105.0" width="32.0" height="91.0" rx="3" style="fill:var(--warn)"/><text x="57.0" y="65.0" font-size="13" text-anchor="middle" style="fill:var(--accent)">51.4</text><text x="93.0" y="99.0" font-size="13" text-anchor="middle" style="fill:var(--warn)">37.4</text><text x="75.0" y="220.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">猫</text><rect x="151.0" y="137.0" width="32.0" height="59.0" rx="3" style="fill:var(--accent)"/><rect x="187.0" y="140.8" width="32.0" height="55.2" rx="3" style="fill:var(--warn)"/><text x="167.0" y="131.0" font-size="13" text-anchor="middle" style="fill:var(--accent)">24.3</text><text x="203.0" y="134.8" font-size="13" text-anchor="middle" style="fill:var(--warn)">22.7</text><text x="185.0" y="220.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">狗</text><rect x="261.0" y="150.0" width="32.0" height="46.0" rx="3" style="fill:var(--accent)"/><rect x="297.0" y="125.1" width="32.0" height="70.9" rx="3" style="fill:var(--warn)"/><text x="277.0" y="144.0" font-size="13" text-anchor="middle" style="fill:var(--accent)">18.9</text><text x="313.0" y="119.1" font-size="13" text-anchor="middle" style="fill:var(--warn)">29.1</text><text x="295.0" y="220.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">狐狸</text><rect x="371.0" y="182.8" width="32.0" height="13.2" rx="3" style="fill:var(--accent)"/><rect x="407.0" y="169.9" width="32.0" height="26.1" rx="3" style="fill:var(--warn)"/><text x="387.0" y="176.8" font-size="13" text-anchor="middle" style="fill:var(--accent)">5.4</text><text x="423.0" y="163.9" font-size="13" text-anchor="middle" style="fill:var(--warn)">10.7</text><text x="405.0" y="220.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">汽车</text>
</svg>
<figcaption>图 3　温度都取 4（柱顶数字是百分比）。学生把狐狸排在狗前面，汽车也给多了；老师的分布里，狗比狐狸更像猫。软标签的损失就是要量出这两组柱子差多少。</figcaption>
</figure>

用什么数来量「学生的分布 $q$ 离老师的分布 $p$ 有多远」？先想交叉熵。预训练那一讲里，交叉熵是「正确 token 的概率取负对数」：$-\ln q_{\text{正确}}$。把它写成对所有类别求和的形式，硬标签 $y$ 只有正确那一格是 1：

$$
\mathrm{CE}(y, q) = -\sum_i y_i \ln q_i = -\ln q_{\text{正确}}
$$

把 $y$ 换成老师的软分布 $p$，就是软标签的交叉熵：每个类别都参与，权重是老师给它的概率：

$$
H(p, q) = -\sum_i p_i \ln q_i
$$

逐项算（$T = 4$）：

| 类别 | $p_i$ | $\ln q_i$ | $-p_i \ln q_i$ |
| --- | --- | --- | --- |
| 猫 | $0.514$ | $-0.983$ | $0.505$ |
| 狗 | $0.243$ | $-1.483$ | $0.360$ |
| 狐狸 | $0.189$ | $-1.233$ | $0.233$ |
| 汽车 | $0.054$ | $-2.233$ | $0.121$ |

加起来 $H(p, q) = 1.219$。这里能看到第二步说的问题：每一行都是「$p_i$ × 某个数」。如果用 $T = 1$，汽车的 $p_i$ 只有 $0.00012$，那一行几乎是 0，汽车对损失的影响就没了。

还有一点不方便：学生就算和老师一模一样（$q = p$），$H(p, q)$ 也不是 0。把 $q = p$ 代进去，得到的是 $-\sum_i p_i \ln p_i$，这叫老师分布的**熵** $H(p)$，衡量老师自己有多不确定。在我们的例子里：

$$
H(p) = -\sum_i p_i \ln p_i = 1.159
$$

把这个「学到完美也去不掉的部分」减掉，剩下的就是 **KL 散度**（Kullback–Leibler divergence）：

$$
\mathrm{KL}(p \,\|\, q) = H(p, q) - H(p) = 1.219 - 1.159 = 0.060
$$

把两个求和合成一个，就是常见的写法（$-\sum p_i \ln q_i + \sum p_i \ln p_i$，两项合并，对数相减变成除法）：

$$
\mathrm{KL}(p \,\|\, q) = \sum_i p_i \ln \frac{p_i}{q_i}
$$

它有两个好性质：$q = p$ 时正好是 0；$q$ 离 $p$ 越远越大。

对学生来说，交叉熵和 KL 只差一个 $H(p)$，而 $H(p)$ 只由老师决定、和学生的参数无关，**两者对学生参数的梯度完全一样**。所以论文里写交叉熵、代码里写 KL，训练效果相同；用 KL 只是为了让损失的最低点是 0，好读。

## 第五步：梯度 $(q - p)/T$

学生的参数要往哪边调？和后训练那一讲推 $p - y$ 的步骤一样，先求损失对每个 logit $z_k$ 的导数。这里每一步只做一件事。

学生在温度 $T$ 下的概率是：

$$
q_i = \frac{e^{z_i/T}}{\sum_j e^{z_j/T}}
$$

取对数，除法变减法：

$$
\ln q_i = \frac{z_i}{T} - \ln \sum_j e^{z_j/T}
$$

代进 $H(p, q) = -\sum_i p_i \ln q_i$，展开成两项：

$$
H(p, q) = -\sum_i p_i \frac{z_i}{T} + \sum_i p_i \ln \sum_j e^{z_j/T}
$$

第二项里，$\ln \sum_j e^{z_j/T}$ 和 $i$ 无关，可以提到 $\sum_i$ 外面；剩下的 $\sum_i p_i = 1$（概率加起来是 1）：

$$
H(p, q) = -\frac{1}{T}\sum_i p_i z_i + \ln \sum_j e^{z_j/T}
$$

对某一个 $z_k$ 求导，两项分别看。第一项里只有 $i = k$ 那一个含 $z_k$，导数是 $-p_k/T$。第二项是 $\ln(\cdot)$ 套着一个和：外层 $\ln$ 的导数是 $1/\sum_j e^{z_j/T}$；里面只有 $e^{z_k/T}$ 含 $z_k$，它的导数是 $e^{z_k/T} \cdot \frac{1}{T}$（链式法则，指数里的 $z_k/T$ 对 $z_k$ 求导得 $1/T$）。乘起来：

$$
\frac{1}{\sum_j e^{z_j/T}} \cdot e^{z_k/T} \cdot \frac{1}{T} = \frac{q_k}{T}
$$

两项合起来：

$$
\frac{\partial\, H(p, q)}{\partial z_k} = \frac{q_k - p_k}{T}
$$

上一步说过 KL 和 $H(p, q)$ 的梯度相同，所以这也是 KL 的梯度。它和后训练那一讲的 $p - y$ 是同一个形状：**学生的概率减去目标的概率**，只是多了一个 $1/T$。$T = 1$ 且目标是硬标签时，它就退回成 $q - y$。

代入 $T = 4$ 的数字：

| 类别 | $q^{(4)}_k$ | $p^{(4)}_k$ | $q_k - p_k$ | 梯度 $(q_k - p_k)/4$ |
| --- | --- | --- | --- | --- |
| 猫 | $0.374$ | $0.514$ | $-0.140$ | $-0.0349$ |
| 狗 | $0.227$ | $0.243$ | $-0.016$ | $-0.0039$ |
| 狐狸 | $0.291$ | $0.189$ | $0.102$ | $0.0256$ |
| 汽车 | $0.107$ | $0.054$ | $0.053$ | $0.0133$ |

梯度下降是**减去**梯度：梯度为负的 logit 会升，为正的会降。所以软标签要学生：猫升、**狗升**、狐狸降、汽车降。

拿硬标签对比。硬标签在 $T = 1$ 下算，学生的 $q^{(1)}$：$e^{z} = (7.389,\ 1.000,\ 2.718,\ 0.050)$，总和 $11.157$，$q^{(1)} = (0.662,\ 0.090,\ 0.244,\ 0.004)$。梯度是 $q^{(1)} - y$：

$$
q^{(1)} - y = (-0.338,\ 0.090,\ 0.244,\ 0.004)
$$

只有猫是负的；狗、狐狸、汽车都是正的，三个一起往下压，学生原来给谁的概率大，谁就被压得多。硬标签永远不会告诉学生「狗应该比狐狸高」。

<figure class="fig">
<svg viewBox="0 0 480 234" role="img" aria-label="硬标签与软标签对每个 logit 的梯度">
<text x="120.0" y="22.0" font-size="15" text-anchor="middle" font-weight="600" style="fill:var(--fg)">硬标签的梯度</text><text x="120.0" y="42.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">刻度 ×1</text><line x1="14.0" y1="120.0" x2="226.0" y2="120.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><rect x="30.0" y="120.0" width="28.0" height="67.5" rx="3" style="fill:var(--muted)"/><text x="44.0" y="203.5" font-size="12" text-anchor="middle" style="fill:var(--muted)">−0.338</text><text x="44.0" y="222.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">猫</text><rect x="82.0" y="102.1" width="28.0" height="17.9" rx="3" style="fill:var(--muted)"/><text x="96.0" y="96.1" font-size="12" text-anchor="middle" style="fill:var(--muted)">+0.090</text><text x="96.0" y="222.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">狗</text><rect x="134.0" y="71.3" width="28.0" height="48.7" rx="3" style="fill:var(--muted)"/><text x="148.0" y="65.3" font-size="12" text-anchor="middle" style="fill:var(--muted)">+0.244</text><text x="148.0" y="222.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">狐狸</text><rect x="186.0" y="119.1" width="28.0" height="0.9" rx="3" style="fill:var(--muted)"/><text x="200.0" y="113.1" font-size="12" text-anchor="middle" style="fill:var(--muted)">+0.004</text><text x="200.0" y="222.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">汽车</text><text x="360.0" y="22.0" font-size="15" text-anchor="middle" font-weight="600" style="fill:var(--fg)">软标签的梯度（T = 4）</text><text x="360.0" y="42.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">刻度 ×10</text><line x1="254.0" y1="120.0" x2="466.0" y2="120.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><rect x="270.0" y="120.0" width="28.0" height="69.8" rx="3" style="fill:var(--accent)"/><text x="284.0" y="205.8" font-size="12" text-anchor="middle" style="fill:var(--accent)">−0.035</text><text x="284.0" y="222.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">猫</text><rect x="322.0" y="120.0" width="28.0" height="7.9" rx="3" style="fill:var(--accent)"/><text x="336.0" y="143.9" font-size="12" text-anchor="middle" style="fill:var(--accent)">−0.004</text><text x="336.0" y="222.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">狗</text><rect x="374.0" y="68.8" width="28.0" height="51.2" rx="3" style="fill:var(--accent)"/><text x="388.0" y="62.8" font-size="12" text-anchor="middle" style="fill:var(--accent)">+0.026</text><text x="388.0" y="222.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">狐狸</text><rect x="426.0" y="93.5" width="28.0" height="26.5" rx="3" style="fill:var(--accent)"/><text x="440.0" y="87.5" font-size="12" text-anchor="middle" style="fill:var(--accent)">+0.013</text><text x="440.0" y="222.0" font-size="15" text-anchor="middle" style="fill:var(--fg)">汽车</text><line x1="240.0" y1="30.0" x2="240.0" y2="210.0" style="stroke:var(--line);stroke-width:1;stroke-dasharray:3 4;fill:none"/>
</svg>
<figcaption>图 4　柱子朝上 = 梯度为正 = 这个 logit 要降；朝下 = 要升。看「狗」：硬标签要把它压下去，软标签要把它抬起来。右边的刻度放大了 10 倍：软标签的梯度小得多，第六步专门讲这件事。</figcaption>
</figure>

<details class="pause"><summary>停一下：如果学生已经和老师在 T = 4 下完全一样，软标签的梯度是多少？硬标签的呢？</summary>

软标签的梯度是 $(q_k - p_k)/T$，$q = p$ 时每一项都是 0：老师能教的已经全教完了。硬标签的梯度是 $q^{(1)} - y$，只要学生给猫的概率不是 100%，它就不是 0：学生和老师一样时，$q^{(1)}_{\text{猫}} = 0.936$，猫的梯度是 $0.936 - 1$，仍然负，硬标签会继续要求学生「更确定一点是猫」，甚至超过老师的确定程度。实验 02 选「和老师一样」可以看到这两项。

</details>

## 第六步：为什么要乘 $T^2$

图 4 右边的刻度放大了 10 倍才看得清：软标签的梯度长度是 $0.0455$，硬标签是 $0.4260$。差这么多，一个原因是梯度里那个 $1/T$；另一个原因藏在 $q_k - p_k$ 里，它也随 $T$ 变小。下面把这两个原因合在一起算出来。

**先做一个不影响结果的准备**：给所有 logit 加同一个数 $c$，softmax 不变。因为 $e^{(v_i + c)/T} = e^{v_i/T} \cdot e^{c/T}$，分子分母都多乘一个 $e^{c/T}$，约掉了。所以总可以假设 logits 的平均是 0，也就是 $\sum_i v_i = 0$、$\sum_i z_i = 0$。我们的例子本来就是这样：$4 + 1 + 0 - 5 = 0$，$2 + 0 + 1 - 3 = 0$。

**第 1 步：$T$ 很大时，指数可以用直线近似。** $x$ 接近 0 时，$e^{x} \approx 1 + x$（例如 $e^{0.1} = 1.105$，$1 + 0.1 = 1.1$）。$T$ 很大时 $v_i/T$ 接近 0，所以：

$$
e^{v_i/T} \approx 1 + \frac{v_i}{T}
$$

**第 2 步：代进 softmax 的分母。** 分母是 $N$ 个这样的项相加（$N$ 是类别数，这里 $N = 4$）：

$$
\sum_j e^{v_j/T} \approx \sum_j \left(1 + \frac{v_j}{T}\right) = N + \frac{1}{T}\sum_j v_j = N
$$

最后一步用了平均为 0：$\sum_j v_j = 0$。

**第 3 步：老师的概率近似为**

$$
p_i \approx \frac{1 + v_i/T}{N}
$$

学生同理：

$$
q_i \approx \frac{1 + z_i/T}{N}
$$

**第 4 步：两者相减，$1/N$ 那部分抵消：**

$$
q_i - p_i \approx \frac{1 + z_i/T}{N} - \frac{1 + v_i/T}{N} = \frac{z_i - v_i}{N\,T}
$$

**第 5 步：再除以梯度里本来的 $T$：**

$$
\frac{q_i - p_i}{T} \approx \frac{z_i - v_i}{N\,T^2}
$$

结论：$T$ 很大时，软标签的梯度**按 $1/T^2$ 缩小**。一个 $1/T$ 来自 $q - p$ 本身（分布被拉平，学生和老师的差距也被拉平），另一个 $1/T$ 来自求导时指数里的 $z/T$。

用 $T = 16$ 验算一下。近似式给出 $(z - v)/(4 \times 256)$：

$$
\frac{(2 - 4,\ 0 - 1,\ 1 - 0,\ -3 + 5)}{1024} = (-0.00195,\ -0.00098,\ 0.00098,\ 0.00195)
$$

真实的 $(q - p)/16$ 是 $(-0.00208,\ -0.00078,\ 0.00120,\ 0.00166)$，已经很接近。

把不同温度下软标签梯度的长度列出来，再乘上 $T^2$：

| $T$ | 梯度长度 | 乘 $T^2$ 之后 |
| --- | --- | --- |
| 1 | $0.3580$ | $0.358$ |
| 2 | $0.1575$ | $0.630$ |
| 4 | $0.0455$ | $0.727$ |
| 8 | $0.0119$ | $0.758$ |
| 16 | $0.00303$ | $0.775$ |
| 32 | $0.00076$ | $0.783$ |

中间一列从 $T = 4$ 到 $T = 16$ 缩小了 15.0 倍（$1/T^2$ 预言的是 16 倍）；右边一列基本走平，并趋向近似式给出的极限 $|z - v|/N = \sqrt{4 + 1 + 1 + 4}\,/\,4 = 0.791$。

<figure class="fig">
<svg viewBox="0 0 480 258" role="img" aria-label="软标签梯度长度随温度变化，乘与不乘 T 平方">
<line x1="70.0" y1="210.0" x2="450.0" y2="210.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="70.0" y1="210.0" x2="70.0" y2="22.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="70.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><text x="146.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2</text><text x="222.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">4</text><text x="298.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">8</text><text x="374.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">16</text><text x="450.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">32</text><text x="450.0" y="250.0" font-size="14" text-anchor="end" style="fill:var(--muted)">温度 T</text><line x1="66.0" y1="195.5" x2="70.0" y2="195.5" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="200.5" font-size="13" text-anchor="end" style="fill:var(--muted)">0.001</text><line x1="66.0" y1="142.1" x2="70.0" y2="142.1" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="147.1" font-size="13" text-anchor="end" style="fill:var(--muted)">0.01</text><line x1="66.0" y1="88.6" x2="70.0" y2="88.6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="93.6" font-size="13" text-anchor="end" style="fill:var(--muted)">0.1</text><line x1="66.0" y1="35.2" x2="70.0" y2="35.2" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="40.2" font-size="13" text-anchor="end" style="fill:var(--muted)">1</text><text x="76.0" y="18.0" font-size="14" text-anchor="start" style="fill:var(--muted)">软标签梯度的长度</text><path d="M70.0 59.1 L73.2 59.5 L76.3 60.0 L79.5 60.5 L82.7 61.1 L85.8 61.7 L89.0 62.3 L92.2 63.0 L95.3 63.7 L98.5 64.4 L101.7 65.1 L104.8 65.9 L108.0 66.7 L111.2 67.5 L114.3 68.4 L117.5 69.2 L120.7 70.1 L123.8 71.1 L127.0 72.0 L130.2 73.0 L133.3 74.0 L136.5 75.0 L139.7 76.0 L142.8 77.0 L146.0 78.1 L149.2 79.2 L152.3 80.3 L155.5 81.4 L158.7 82.5 L161.8 83.7 L165.0 84.8 L168.2 86.0 L171.3 87.1 L174.5 88.3 L177.7 89.5 L180.8 90.7 L184.0 91.9 L187.2 93.1 L190.3 94.4 L193.5 95.6 L196.7 96.8 L199.8 98.1 L203.0 99.3 L206.2 100.6 L209.3 101.9 L212.5 103.1 L215.7 104.4 L218.8 105.7 L222.0 106.9 L225.2 108.2 L228.3 109.5 L231.5 110.8 L234.7 112.1 L237.8 113.4 L241.0 114.6 L244.2 115.9 L247.3 117.2 L250.5 118.5 L253.7 119.8 L256.8 121.1 L260.0 122.4 L263.2 123.7 L266.3 125.0 L269.5 126.3 L272.7 127.7 L275.8 129.0 L279.0 130.3 L282.2 131.6 L285.3 132.9 L288.5 134.2 L291.7 135.5 L294.8 136.8 L298.0 138.1 L301.2 139.4 L304.3 140.8 L307.5 142.1 L310.7 143.4 L313.8 144.7 L317.0 146.0 L320.2 147.3 L323.3 148.7 L326.5 150.0 L329.7 151.3 L332.8 152.6 L336.0 153.9 L339.2 155.2 L342.3 156.6 L345.5 157.9 L348.7 159.2 L351.8 160.5 L355.0 161.9 L358.2 163.2 L361.3 164.5 L364.5 165.8 L367.7 167.2 L370.8 168.5 L374.0 169.8 L377.2 171.1 L380.3 172.5 L383.5 173.8 L386.7 175.1 L389.8 176.4 L393.0 177.8 L396.2 179.1 L399.3 180.4 L402.5 181.8 L405.7 183.1 L408.8 184.4 L412.0 185.7 L415.2 187.1 L418.3 188.4 L421.5 189.7 L424.7 191.1 L427.8 192.4 L431.0 193.7 L434.2 195.1 L437.3 196.4 L440.5 197.7 L443.7 199.1 L446.8 200.4 L450.0 201.7" style="stroke:var(--muted);stroke-width:2.2;stroke-dasharray:6 4;fill:none"/><path d="M70.0 59.1 L73.2 58.2 L76.3 57.3 L79.5 56.5 L82.7 55.7 L85.8 55.0 L89.0 54.3 L92.2 53.6 L95.3 52.9 L98.5 52.3 L101.7 51.7 L104.8 51.1 L108.0 50.6 L111.2 50.1 L114.3 49.6 L117.5 49.1 L120.7 48.7 L123.8 48.3 L127.0 47.9 L130.2 47.5 L133.3 47.2 L136.5 46.8 L139.7 46.5 L142.8 46.2 L146.0 45.9 L149.2 45.7 L152.3 45.4 L155.5 45.2 L158.7 45.0 L161.8 44.8 L165.0 44.6 L168.2 44.4 L171.3 44.2 L174.5 44.1 L177.7 43.9 L180.8 43.8 L184.0 43.7 L187.2 43.6 L190.3 43.4 L193.5 43.3 L196.7 43.2 L199.8 43.1 L203.0 43.0 L206.2 43.0 L209.3 42.9 L212.5 42.8 L215.7 42.7 L218.8 42.7 L222.0 42.6 L225.2 42.5 L228.3 42.5 L231.5 42.4 L234.7 42.4 L237.8 42.3 L241.0 42.3 L244.2 42.2 L247.3 42.2 L250.5 42.1 L253.7 42.1 L256.8 42.1 L260.0 42.0 L263.2 42.0 L266.3 41.9 L269.5 41.9 L272.7 41.9 L275.8 41.8 L279.0 41.8 L282.2 41.8 L285.3 41.8 L288.5 41.7 L291.7 41.7 L294.8 41.7 L298.0 41.6 L301.2 41.6 L304.3 41.6 L307.5 41.6 L310.7 41.5 L313.8 41.5 L317.0 41.5 L320.2 41.5 L323.3 41.4 L326.5 41.4 L329.7 41.4 L332.8 41.4 L336.0 41.4 L339.2 41.3 L342.3 41.3 L345.5 41.3 L348.7 41.3 L351.8 41.3 L355.0 41.2 L358.2 41.2 L361.3 41.2 L364.5 41.2 L367.7 41.2 L370.8 41.2 L374.0 41.1 L377.2 41.1 L380.3 41.1 L383.5 41.1 L386.7 41.1 L389.8 41.1 L393.0 41.1 L396.2 41.1 L399.3 41.0 L402.5 41.0 L405.7 41.0 L408.8 41.0 L412.0 41.0 L415.2 41.0 L418.3 41.0 L421.5 41.0 L424.7 41.0 L427.8 41.0 L431.0 41.0 L434.2 40.9 L437.3 40.9 L440.5 40.9 L443.7 40.9 L446.8 40.9 L450.0 40.9" style="stroke:var(--accent);stroke-width:2.8;fill:none"/><line x1="70.0" y1="40.7" x2="450.0" y2="40.7" style="stroke:var(--ok);stroke-width:1.2;stroke-dasharray:2 4;fill:none"/><text x="450.0" y="32.7" font-size="13" text-anchor="end" style="fill:var(--ok)">|z − v| / N = 0.791</text><circle cx="70.0" cy="59.1" r="4" style="fill:var(--muted)"/><circle cx="70.0" cy="59.1" r="4" style="fill:var(--accent)"/><circle cx="222.0" cy="106.9" r="4" style="fill:var(--muted)"/><circle cx="222.0" cy="42.6" r="4" style="fill:var(--accent)"/><circle cx="374.0" cy="169.8" r="4" style="fill:var(--muted)"/><circle cx="374.0" cy="41.1" r="4" style="fill:var(--accent)"/><text x="94.5" y="163.3" font-size="14" text-anchor="start" style="fill:var(--muted)">不乘：按 1/T² 变小</text><text x="156.5" y="67.1" font-size="14" text-anchor="start" style="fill:var(--accent)">乘 T²：走平</text>
</svg>
<figcaption>图 5　两个坐标轴都是对数刻度。灰色虚线是软标签梯度本来的长度：T 从 1 到 32，从 0.358 掉到 0.00076。蓝线乘上 T² 之后几乎是平的，并且趋向绿色虚线 0.791（第六步推出来的极限）。</figcaption>
</figure>

**为什么要它走平？** 因为实际训练时，软标签的损失通常和硬标签的交叉熵一起用，按权重 $\alpha$ 加起来：

$$
L = \alpha\,\mathrm{CE}\big(y,\ q^{(1)}\big) + (1-\alpha)\,T^2\,\mathrm{KL}\big(p^{(T)}\,\big\|\,q^{(T)}\big)
$$

硬标签那一项在 $T = 1$ 下算，它的梯度和 $T$ 无关。如果软标签那一项不乘 $T^2$，换一个温度，两项的相对分量就跟着变：取 $\alpha = 0.5$、$T = 4$，不乘时软项梯度只有硬项的 $0.107$ 倍，几乎被淹没；乘上 $T^2 = 16$ 后是 $1.707$ 倍。乘了 $T^2$，调温度时就不用重新调 $\alpha$。Hinton 等人的原话是：软标签产生的梯度大小按 $1/T^2$ 缩放，所以同时用软硬两种标签时，乘以 $T^2$ 很重要。

如果只用软标签（$\alpha = 0$），乘不乘 $T^2$ 只相当于把学习率放大 $T^2$ 倍；Adam 这类按梯度大小自动缩放步长的优化器，对整体放大一个常数基本不敏感。

<details class="pause"><summary>停一下：如果 4 个类别换成 10 个类别，T 很大时软标签的梯度会怎样变？</summary>

近似式是 $(z_i - v_i)/(N T^2)$，$N$ 在分母上。类别从 4 变成 10，在 logit 差距相同的情况下梯度再小 2.5 倍。这和 $T$ 无关，所以乘 $T^2$ 补不回来；它是固定的比例，可以并进学习率或 $\alpha$ 里。真实的大模型，「类别」是整个词表（例如 128,256 个 token），所以词元级蒸馏的损失通常直接按 KL 的数值调权重，而不是靠公式去补。

</details>

## 第七步：在浏览器里真训一次

前面的推导说软标签信息更多。到底有没有用，最好真训一次看看。实验 03 在页面里训练（下面的数字是用页面里同一段代码在 node 里跑出来的，和浏览器里逐字一致）：

- **数据**：平面上三条旋臂，三类，每个点带一点噪声。
- **老师**：单隐层 MLP（MLP 那一讲的结构），32 个隐藏单元，600 个带标签的点，Adam 训练 300 步。在另外 1500 个点上验证，错误率 1.1%。
- **学生**：同样结构，16 个隐藏单元，**只拿到 60 个点**。两个学生从同一组初始参数出发、各训练 300 步：一个用这 60 个点的真实类别（硬标签，交叉熵），一个用老师在 $T = 4$ 下对这 60 个点的概率（软标签，$T^2\,\mathrm{KL}$）。

结果：硬标签学生错 3.9%，软标签学生错 1.2%，接近老师的 1.1%。

<figure class="fig">
<svg viewBox="0 0 480 194" role="img" aria-label="老师、硬标签学生、软标签学生在平面上的分界">
<path d="M8.00 4.00h90.44v4.41h-90.44zM8.00 8.11h90.44v4.41h-90.44zM8.00 12.22h90.44v4.41h-90.44zM8.00 16.33h90.44v4.41h-90.44zM8.00 20.44h94.56v4.41h-94.56zM8.00 24.56h94.56v4.41h-94.56zM8.00 28.67h94.56v4.41h-94.56zM8.00 32.78h94.56v4.41h-94.56zM8.00 36.89h94.56v4.41h-94.56zM8.00 41.00h98.67v4.41h-98.67zM8.00 45.11h98.67v4.41h-98.67zM8.00 49.22h98.67v4.41h-98.67zM8.00 53.33h53.44v4.41h-53.44zM77.89 53.33h32.89v4.41h-32.89zM8.00 57.44h49.33v4.41h-49.33zM82.00 57.44h28.78v4.41h-28.78zM8.00 61.56h41.11v4.41h-41.11zM86.11 61.56h24.67v4.41h-24.67zM8.00 65.67h37.00v4.41h-37.00zM86.11 65.67h24.67v4.41h-24.67zM8.00 69.78h37.00v4.41h-37.00zM86.11 69.78h24.67v4.41h-24.67zM8.00 73.89h32.89v4.41h-32.89zM86.11 73.89h24.67v4.41h-24.67zM8.00 78.00h28.78v4.41h-28.78zM86.11 78.00h20.56v4.41h-20.56zM8.00 82.11h24.67v4.41h-24.67zM90.22 82.11h12.33v4.41h-12.33zM8.00 86.22h16.44v4.41h-16.44zM8.00 90.33h12.33v4.41h-12.33z" style="fill:var(--accent);fill-opacity:0.28"/><path d="M61.44 53.33h16.44v4.41h-16.44zM57.33 57.44h24.67v4.41h-24.67zM49.11 61.56h37.00v4.41h-37.00zM45.00 65.67h41.11v4.41h-41.11zM45.00 69.78h41.11v4.41h-41.11zM40.89 73.89h45.22v4.41h-45.22zM36.78 78.00h45.22v4.41h-45.22zM32.67 82.11h37.00v4.41h-37.00zM24.44 86.22h41.11v4.41h-41.11zM20.33 90.33h41.11v4.41h-41.11zM8.00 94.44h53.44v4.41h-53.44zM8.00 98.56h57.56v4.41h-57.56zM8.00 102.67h61.67v4.41h-61.67zM8.00 106.78h65.78v4.41h-65.78zM8.00 110.89h74.00v4.41h-74.00zM8.00 115.00h86.33v4.41h-86.33zM8.00 119.11h102.78v4.41h-102.78zM8.00 123.22h111.00v4.41h-111.00zM8.00 127.33h119.22v4.41h-119.22zM8.00 131.44h123.33v4.41h-123.33zM8.00 135.56h131.56v4.41h-131.56zM8.00 139.67h135.67v4.41h-135.67zM8.00 143.78h143.89v4.41h-143.89zM8.00 147.89h148.00v4.41h-148.00z" style="fill:var(--warn);fill-opacity:0.28"/><path d="M98.44 4.00h57.56v4.41h-57.56zM98.44 8.11h57.56v4.41h-57.56zM98.44 12.22h57.56v4.41h-57.56zM98.44 16.33h57.56v4.41h-57.56zM102.56 20.44h53.44v4.41h-53.44zM102.56 24.56h53.44v4.41h-53.44zM102.56 28.67h53.44v4.41h-53.44zM102.56 32.78h53.44v4.41h-53.44zM102.56 36.89h53.44v4.41h-53.44zM106.67 41.00h49.33v4.41h-49.33zM106.67 45.11h49.33v4.41h-49.33zM106.67 49.22h49.33v4.41h-49.33zM110.78 53.33h45.22v4.41h-45.22zM110.78 57.44h45.22v4.41h-45.22zM110.78 61.56h45.22v4.41h-45.22zM110.78 65.67h45.22v4.41h-45.22zM110.78 69.78h45.22v4.41h-45.22zM110.78 73.89h45.22v4.41h-45.22zM82.00 78.00h4.11v4.41h-4.11zM106.67 78.00h49.33v4.41h-49.33zM69.67 82.11h20.56v4.41h-20.56zM102.56 82.11h53.44v4.41h-53.44zM65.56 86.22h90.44v4.41h-90.44zM61.44 90.33h94.56v4.41h-94.56zM61.44 94.44h94.56v4.41h-94.56zM65.56 98.56h90.44v4.41h-90.44zM69.67 102.67h86.33v4.41h-86.33zM73.78 106.78h82.22v4.41h-82.22zM82.00 110.89h74.00v4.41h-74.00zM94.33 115.00h61.67v4.41h-61.67zM110.78 119.11h45.22v4.41h-45.22zM119.00 123.22h37.00v4.41h-37.00zM127.22 127.33h28.78v4.41h-28.78zM131.33 131.44h24.67v4.41h-24.67zM139.56 135.56h16.44v4.41h-16.44zM143.67 139.67h12.33v4.41h-12.33zM151.89 143.78h4.11v4.41h-4.11z" style="fill:var(--ok);fill-opacity:0.28"/><text x="82.0" y="172.0" font-size="14" text-anchor="middle" style="fill:var(--fg)">老师（32 单元）</text><text x="82.0" y="190.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">错 1.1%</text><path d="M166.00 4.00h82.22v4.41h-82.22zM166.00 8.11h82.22v4.41h-82.22zM166.00 12.22h86.33v4.41h-86.33zM166.00 16.33h86.33v4.41h-86.33zM166.00 20.44h86.33v4.41h-86.33zM166.00 24.56h86.33v4.41h-86.33zM166.00 28.67h90.44v4.41h-90.44zM166.00 32.78h90.44v4.41h-90.44zM166.00 36.89h94.56v4.41h-94.56zM166.00 41.00h94.56v4.41h-94.56zM166.00 45.11h98.67v4.41h-98.67zM166.00 49.22h98.67v4.41h-98.67zM166.00 53.33h53.44v4.41h-53.44zM227.67 53.33h37.00v4.41h-37.00zM166.00 57.44h49.33v4.41h-49.33zM235.89 57.44h32.89v4.41h-32.89zM166.00 61.56h45.22v4.41h-45.22zM240.00 61.56h28.78v4.41h-28.78zM166.00 65.67h41.11v4.41h-41.11zM240.00 65.67h28.78v4.41h-28.78zM166.00 69.78h32.89v4.41h-32.89zM244.11 69.78h28.78v4.41h-28.78zM166.00 73.89h24.67v4.41h-24.67zM244.11 73.89h24.67v4.41h-24.67z" style="fill:var(--accent);fill-opacity:0.28"/><path d="M219.44 53.33h8.22v4.41h-8.22zM215.33 57.44h20.56v4.41h-20.56zM211.22 61.56h28.78v4.41h-28.78zM207.11 65.67h32.89v4.41h-32.89zM198.89 69.78h45.22v4.41h-45.22zM190.67 73.89h53.44v4.41h-53.44zM166.00 78.00h69.89v4.41h-69.89zM166.00 82.11h61.67v4.41h-61.67zM166.00 86.22h57.56v4.41h-57.56zM166.00 90.33h53.44v4.41h-53.44zM166.00 94.44h53.44v4.41h-53.44zM166.00 98.56h57.56v4.41h-57.56zM166.00 102.67h61.67v4.41h-61.67zM166.00 106.78h69.89v4.41h-69.89zM166.00 110.89h78.11v4.41h-78.11zM166.00 115.00h86.33v4.41h-86.33zM166.00 119.11h94.56v4.41h-94.56zM166.00 123.22h98.67v4.41h-98.67zM166.00 127.33h106.89v4.41h-106.89zM166.00 131.44h115.11v4.41h-115.11zM166.00 135.56h123.33v4.41h-123.33zM166.00 139.67h127.44v4.41h-127.44zM166.00 143.78h131.56v4.41h-131.56zM166.00 147.89h139.78v4.41h-139.78z" style="fill:var(--warn);fill-opacity:0.28"/><path d="M248.22 4.00h65.78v4.41h-65.78zM248.22 8.11h65.78v4.41h-65.78zM252.33 12.22h61.67v4.41h-61.67zM252.33 16.33h61.67v4.41h-61.67zM252.33 20.44h61.67v4.41h-61.67zM252.33 24.56h61.67v4.41h-61.67zM256.44 28.67h57.56v4.41h-57.56zM256.44 32.78h57.56v4.41h-57.56zM260.56 36.89h53.44v4.41h-53.44zM260.56 41.00h53.44v4.41h-53.44zM264.67 45.11h49.33v4.41h-49.33zM264.67 49.22h49.33v4.41h-49.33zM264.67 53.33h49.33v4.41h-49.33zM268.78 57.44h45.22v4.41h-45.22zM268.78 61.56h45.22v4.41h-45.22zM268.78 65.67h45.22v4.41h-45.22zM272.89 69.78h41.11v4.41h-41.11zM268.78 73.89h45.22v4.41h-45.22zM235.89 78.00h78.11v4.41h-78.11zM227.67 82.11h86.33v4.41h-86.33zM223.56 86.22h90.44v4.41h-90.44zM219.44 90.33h94.56v4.41h-94.56zM219.44 94.44h94.56v4.41h-94.56zM223.56 98.56h90.44v4.41h-90.44zM227.67 102.67h86.33v4.41h-86.33zM235.89 106.78h78.11v4.41h-78.11zM244.11 110.89h69.89v4.41h-69.89zM252.33 115.00h61.67v4.41h-61.67zM260.56 119.11h53.44v4.41h-53.44zM264.67 123.22h49.33v4.41h-49.33zM272.89 127.33h41.11v4.41h-41.11zM281.11 131.44h32.89v4.41h-32.89zM289.33 135.56h24.67v4.41h-24.67zM293.44 139.67h20.56v4.41h-20.56zM297.56 143.78h16.44v4.41h-16.44zM305.78 147.89h8.22v4.41h-8.22z" style="fill:var(--ok);fill-opacity:0.28"/><circle cx="197.5" cy="41.4" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="242.4" cy="126.8" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="276.8" cy="39.9" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="188.8" cy="57.0" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="227.3" cy="114.8" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="230.1" cy="88.6" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="187.6" cy="65.9" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="207.6" cy="71.9" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="280.0" cy="39.5" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="230.4" cy="41.5" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="247.6" cy="130.0" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="282.1" cy="55.4" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="242.3" cy="50.5" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="210.6" cy="93.9" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="241.8" cy="94.8" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="189.8" cy="60.4" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="261.6" cy="132.7" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="265.1" cy="28.3" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="252.7" cy="56.9" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="200.1" cy="99.6" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="279.1" cy="69.5" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="258.1" cy="52.8" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="219.4" cy="121.6" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="265.7" cy="102.3" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="250.4" cy="71.5" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="199.5" cy="87.5" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="281.3" cy="74.2" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="243.8" cy="46.1" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="209.6" cy="101.0" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="233.6" cy="91.7" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="184.6" cy="46.5" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="229.2" cy="129.7" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="248.0" cy="104.3" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="225.0" cy="44.4" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="227.1" cy="126.3" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="279.9" cy="90.1" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="252.2" cy="58.7" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="222.6" cy="67.1" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="233.6" cy="87.6" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="179.8" cy="65.8" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="215.6" cy="109.3" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="242.0" cy="93.1" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="202.6" cy="62.9" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="212.8" cy="79.8" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="282.7" cy="70.2" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="244.4" cy="54.2" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="214.7" cy="82.2" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="234.2" cy="88.2" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="251.5" cy="58.4" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="233.0" cy="67.0" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="252.3" cy="106.1" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="178.8" cy="68.2" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="236.9" cy="123.7" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="281.4" cy="95.0" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="261.9" cy="67.3" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="235.9" cy="77.7" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="280.2" cy="53.5" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="260.6" cy="64.8" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="231.0" cy="70.8" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="260.5" cy="21.1" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><text x="240.0" y="172.0" font-size="14" text-anchor="middle" style="fill:var(--fg)">硬标签学生</text><text x="240.0" y="190.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">错 3.9%</text><path d="M324.00 4.00h90.44v4.41h-90.44zM324.00 8.11h90.44v4.41h-90.44zM324.00 12.22h90.44v4.41h-90.44zM324.00 16.33h90.44v4.41h-90.44zM324.00 20.44h90.44v4.41h-90.44zM324.00 24.56h94.56v4.41h-94.56zM324.00 28.67h94.56v4.41h-94.56zM324.00 32.78h94.56v4.41h-94.56zM324.00 36.89h98.67v4.41h-98.67zM324.00 41.00h98.67v4.41h-98.67zM324.00 45.11h98.67v4.41h-98.67zM324.00 49.22h102.78v4.41h-102.78zM324.00 53.33h57.56v4.41h-57.56zM393.89 53.33h32.89v4.41h-32.89zM324.00 57.44h49.33v4.41h-49.33zM398.00 57.44h28.78v4.41h-28.78zM324.00 61.56h45.22v4.41h-45.22zM398.00 61.56h32.89v4.41h-32.89zM324.00 65.67h41.11v4.41h-41.11zM398.00 65.67h32.89v4.41h-32.89zM324.00 69.78h32.89v4.41h-32.89zM398.00 69.78h32.89v4.41h-32.89zM324.00 73.89h28.78v4.41h-28.78zM402.11 73.89h24.67v4.41h-24.67zM324.00 78.00h24.67v4.41h-24.67zM402.11 78.00h20.56v4.41h-20.56zM324.00 82.11h16.44v4.41h-16.44zM324.00 86.22h4.11v4.41h-4.11z" style="fill:var(--accent);fill-opacity:0.28"/><path d="M381.56 53.33h12.33v4.41h-12.33zM373.33 57.44h24.67v4.41h-24.67zM369.22 61.56h28.78v4.41h-28.78zM365.11 65.67h32.89v4.41h-32.89zM356.89 69.78h41.11v4.41h-41.11zM352.78 73.89h49.33v4.41h-49.33zM348.67 78.00h49.33v4.41h-49.33zM340.44 82.11h45.22v4.41h-45.22zM328.11 86.22h53.44v4.41h-53.44zM324.00 90.33h53.44v4.41h-53.44zM324.00 94.44h53.44v4.41h-53.44zM324.00 98.56h57.56v4.41h-57.56zM324.00 102.67h61.67v4.41h-61.67zM324.00 106.78h65.78v4.41h-65.78zM324.00 110.89h74.00v4.41h-74.00zM324.00 115.00h86.33v4.41h-86.33zM324.00 119.11h98.67v4.41h-98.67zM324.00 123.22h106.89v4.41h-106.89zM324.00 127.33h115.11v4.41h-115.11zM324.00 131.44h123.33v4.41h-123.33zM324.00 135.56h127.44v4.41h-127.44zM324.00 139.67h131.56v4.41h-131.56zM324.00 143.78h135.67v4.41h-135.67zM324.00 147.89h139.78v4.41h-139.78z" style="fill:var(--warn);fill-opacity:0.28"/><path d="M414.44 4.00h57.56v4.41h-57.56zM414.44 8.11h57.56v4.41h-57.56zM414.44 12.22h57.56v4.41h-57.56zM414.44 16.33h57.56v4.41h-57.56zM414.44 20.44h57.56v4.41h-57.56zM418.56 24.56h53.44v4.41h-53.44zM418.56 28.67h53.44v4.41h-53.44zM418.56 32.78h53.44v4.41h-53.44zM422.67 36.89h49.33v4.41h-49.33zM422.67 41.00h49.33v4.41h-49.33zM422.67 45.11h49.33v4.41h-49.33zM426.78 49.22h45.22v4.41h-45.22zM426.78 53.33h45.22v4.41h-45.22zM426.78 57.44h45.22v4.41h-45.22zM430.89 61.56h41.11v4.41h-41.11zM430.89 65.67h41.11v4.41h-41.11zM430.89 69.78h41.11v4.41h-41.11zM426.78 73.89h45.22v4.41h-45.22zM398.00 78.00h4.11v4.41h-4.11zM422.67 78.00h49.33v4.41h-49.33zM385.67 82.11h86.33v4.41h-86.33zM381.56 86.22h90.44v4.41h-90.44zM377.44 90.33h94.56v4.41h-94.56zM377.44 94.44h94.56v4.41h-94.56zM381.56 98.56h90.44v4.41h-90.44zM385.67 102.67h86.33v4.41h-86.33zM389.78 106.78h82.22v4.41h-82.22zM398.00 110.89h74.00v4.41h-74.00zM410.33 115.00h61.67v4.41h-61.67zM422.67 119.11h49.33v4.41h-49.33zM430.89 123.22h41.11v4.41h-41.11zM439.11 127.33h32.89v4.41h-32.89zM447.33 131.44h24.67v4.41h-24.67zM451.44 135.56h20.56v4.41h-20.56zM455.56 139.67h16.44v4.41h-16.44zM459.67 143.78h12.33v4.41h-12.33zM463.78 147.89h8.22v4.41h-8.22z" style="fill:var(--ok);fill-opacity:0.28"/><circle cx="355.5" cy="41.4" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="400.4" cy="126.8" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="434.8" cy="39.9" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="346.8" cy="57.0" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="385.3" cy="114.8" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="388.1" cy="88.6" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="345.6" cy="65.9" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="365.6" cy="71.9" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="438.0" cy="39.5" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="388.4" cy="41.5" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="405.6" cy="130.0" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="440.1" cy="55.4" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="400.3" cy="50.5" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="368.6" cy="93.9" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="399.8" cy="94.8" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="347.8" cy="60.4" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="419.6" cy="132.7" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="423.1" cy="28.3" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="410.7" cy="56.9" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="358.1" cy="99.6" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="437.1" cy="69.5" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="416.1" cy="52.8" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="377.4" cy="121.6" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="423.7" cy="102.3" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="408.4" cy="71.5" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="357.5" cy="87.5" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="439.3" cy="74.2" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="401.8" cy="46.1" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="367.6" cy="101.0" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="391.6" cy="91.7" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="342.6" cy="46.5" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="387.2" cy="129.7" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="406.0" cy="104.3" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="383.0" cy="44.4" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="385.1" cy="126.3" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="437.9" cy="90.1" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="410.2" cy="58.7" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="380.6" cy="67.1" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="391.6" cy="87.6" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="337.8" cy="65.8" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="373.6" cy="109.3" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="400.0" cy="93.1" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="360.6" cy="62.9" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="370.8" cy="79.8" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="440.7" cy="70.2" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="402.4" cy="54.2" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="372.7" cy="82.2" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="392.2" cy="88.2" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="409.5" cy="58.4" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="391.0" cy="67.0" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="410.3" cy="106.1" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="336.8" cy="68.2" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="394.9" cy="123.7" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="439.4" cy="95.0" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="419.9" cy="67.3" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="393.9" cy="77.7" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="438.2" cy="53.5" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><circle cx="418.6" cy="64.8" r="2.6" style="fill:var(--accent);stroke:var(--bg);stroke-width:0.8"/><circle cx="389.0" cy="70.8" r="2.6" style="fill:var(--warn);stroke:var(--bg);stroke-width:0.8"/><circle cx="418.5" cy="21.1" r="2.6" style="fill:var(--ok);stroke:var(--bg);stroke-width:0.8"/><text x="398.0" y="172.0" font-size="14" text-anchor="middle" style="fill:var(--fg)">软标签学生（T = 4）</text><text x="398.0" y="190.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">错 1.2%</text>
</svg>
<figcaption>图 6　三种颜色是三类，背景色是模型把每个位置判成哪一类，圆点是学生拿到的 60 个点。两个学生都是 16 个隐藏单元、同一组初始参数、同样训练 300 步，只有目标不同。软标签学生的分界更贴近老师。</figcaption>
</figure>

为什么差这么多？60 个点很稀，两条旋臂之间大片地方没有点。硬标签只告诉学生「这个点是蓝色」，至于这个点离橙色那条臂有多近，学生不知道，它就在空白处随手画分界。软标签在每个点上都多说了一句，比如「这个点九成是蓝色，但有一点像橙色」，相当于告诉学生分界大概在哪个方向、离这里多远。同样 60 个点，学到的东西更多。

换其他设置（实验 03 都可以点）：只给 30 个点时，硬标签 5.0%、软标签 1.6%；给 120 个点时，1.8% 对 1.3%，点越多，硬标签自己也能学好，软标签的优势就越小。温度也有讲究：60 个点、$T = 1$ 时软标签学生错 3.9%，和硬标签几乎一样（$T = 1$ 的老师分布本身就接近硬标签）；$T = 2$ 是 2.1%，$T = 4$ 是 1.2%，$T = 8$ 又回到 2.2%。

**学生的容量**。把学生的隐藏层宽度从 1 一路加到 32（实验 04）：

<figure class="fig">
<svg viewBox="0 0 480 250" role="img" aria-label="验证错误率随学生隐藏层宽度的变化">
<line x1="64.0" y1="200.0" x2="460.0" y2="200.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="64.0" y1="200.0" x2="64.0" y2="22.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="64.0" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><text x="120.6" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2</text><text x="177.1" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">3</text><text x="233.7" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">4</text><text x="290.3" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">6</text><text x="346.9" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">8</text><text x="403.4" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">16</text><text x="460.0" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">32</text><text x="460.0" y="240.0" font-size="14" text-anchor="end" style="fill:var(--muted)">学生的隐藏层宽度</text><line x1="60.0" y1="176.8" x2="64.0" y2="176.8" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="56.0" y="181.8" font-size="13" text-anchor="end" style="fill:var(--muted)">1%</text><line x1="60.0" y1="148.1" x2="64.0" y2="148.1" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="56.0" y="153.1" font-size="13" text-anchor="end" style="fill:var(--muted)">5%</text><line x1="60.0" y1="96.3" x2="64.0" y2="96.3" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="56.0" y="101.3" font-size="13" text-anchor="end" style="fill:var(--muted)">20%</text><line x1="60.0" y1="36.0" x2="64.0" y2="36.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="56.0" y="41.0" font-size="13" text-anchor="end" style="fill:var(--muted)">50%</text><text x="70.0" y="16.0" font-size="14" text-anchor="start" style="fill:var(--muted)">验证错误率</text><line x1="64.0" y1="176.0" x2="460.0" y2="176.0" style="stroke:var(--fg);stroke-width:1.2;stroke-dasharray:5 4;fill:none"/><text x="70.0" y="194.0" font-size="13" text-anchor="start" style="fill:var(--fg)">老师 1.1%</text><path d="M64.0 34.2 L120.6 99.6 L177.1 115.1 L233.7 125.0 L290.3 157.2 L346.9 164.6 L403.4 154.4 L460.0 163.1" style="stroke:var(--warn);stroke-width:2.4;fill:none"/><circle cx="64.0" cy="34.2" r="3.5" style="fill:var(--warn)"/><circle cx="120.6" cy="99.6" r="3.5" style="fill:var(--warn)"/><circle cx="177.1" cy="115.1" r="3.5" style="fill:var(--warn)"/><circle cx="233.7" cy="125.0" r="3.5" style="fill:var(--warn)"/><circle cx="290.3" cy="157.2" r="3.5" style="fill:var(--warn)"/><circle cx="346.9" cy="164.6" r="3.5" style="fill:var(--warn)"/><circle cx="403.4" cy="154.4" r="3.5" style="fill:var(--warn)"/><circle cx="460.0" cy="163.1" r="3.5" style="fill:var(--warn)"/><path d="M64.0 41.9 L120.6 75.4 L177.1 103.6 L233.7 122.4 L290.3 164.6 L346.9 168.9 L403.4 174.6 L460.0 174.6" style="stroke:var(--ok);stroke-width:2.4;fill:none"/><circle cx="64.0" cy="41.9" r="3.5" style="fill:var(--ok)"/><circle cx="120.6" cy="75.4" r="3.5" style="fill:var(--ok)"/><circle cx="177.1" cy="103.6" r="3.5" style="fill:var(--ok)"/><circle cx="233.7" cy="122.4" r="3.5" style="fill:var(--ok)"/><circle cx="290.3" cy="164.6" r="3.5" style="fill:var(--ok)"/><circle cx="346.9" cy="168.9" r="3.5" style="fill:var(--ok)"/><circle cx="403.4" cy="174.6" r="3.5" style="fill:var(--ok)"/><circle cx="460.0" cy="174.6" r="3.5" style="fill:var(--ok)"/><rect x="214.0" y="26.0" width="12.0" height="12.0" rx="3" style="fill:var(--warn)"/><text x="232.0" y="36.0" font-size="14" text-anchor="start" style="fill:var(--muted)">硬标签学生</text><rect x="319.0" y="26.0" width="12.0" height="12.0" rx="3" style="fill:var(--ok)"/><text x="337.0" y="36.0" font-size="14" text-anchor="start" style="fill:var(--muted)">软标签学生</text>
</svg>
<figcaption>图 7　同样 60 个点、T = 4，每个宽度各训练一个硬标签学生和一个软标签学生（纵轴按平方根刻度，小错误率看得清）。宽度 2 到 4，软标签不比硬标签好；宽度 6 起软标签学生一直更好，16 以后贴近老师。</figcaption>
</figure>

- 宽度 1：一个隐藏单元只能把平面切一刀，两种学生都错一半左右（硬标签 51.1%，软标签 46.5%）。
- 宽度 2 到 4：学生画不出三条旋臂。这时软标签反而不比硬标签好（宽度 2 时 28.9% 对 18.7%）：老师的分布是一个弯弯曲曲的形状，学生装不下，硬去拟合它，不如只学「是哪一类」。
- 宽度 6 起，软标签学生一直更好；16 和 32 时都是 1.2%，贴近老师。

蒸馏不是魔法：**学生得有足够的容量去装老师给的东西**。

## 序列级蒸馏：直接拿老师写的文本做 SFT

到了大语言模型，「分类」变成了「预测下一个 token」：每个位置有一个分布，类别就是整个词表。上面的方法可以原样搬过来，有两种做法。

**词元级蒸馏**（token-level）：在每个位置，让学生的下一个 token 分布去对齐老师的分布，损失是每个位置的 KL 加起来，梯度就是第五步的 $q - p$。这需要老师在每个位置**整个词表**上的概率（Llama 3 的词表是 128,256 个 token，每个位置就是十几万个数），还要求老师和学生用同一个分词器，否则两边的「类别」对不上。Google 的 Gemma 2 就是这样训练 2B 和 9B 两个小模型的：在预训练阶段用一个更大的模型当老师，按老师给每个 token 的概率训练，而不是按「下一个 token 是什么」训练；9B 用了 8 T token，2B 用了 2 T token。论文的对照实验里，同样训练 500 B token 的 2B 模型，从头训练三项基准平均 60.3，从 7B 老师蒸馏 67.7（2026-10-22 核对 Gemma 2 技术报告）。

**序列级蒸馏**（sequence-level）：更省事。让老师对大量提示写出完整回答，把这些回答当成示范，学生做普通的 SFT，和后训练那一讲第二步一模一样：每个位置的目标是 one-hot，梯度是 $q - y$，只不过这个 $y$ 是老师写出来的 token。这个名字来自 Kim 和 Rush 2016 年的机器翻译论文：他们让学生直接学老师用束搜索译出的整句话，最好的学生比老师快 10 倍、效果损失很小，用贪心解码时比不蒸馏的同尺寸模型高 4.2 BLEU。

<figure class="fig">
<svg viewBox="0 0 480 258" role="img" aria-label="词元级蒸馏与序列级蒸馏的对比">
<text x="10.0" y="22.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--fg)">词元级：每个位置对齐老师的整个分布</text><rect x="14" y="36" width="42" height="30" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="35.0" y="57.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">17</text><rect x="64" y="36" width="42" height="30" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="85.0" y="57.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">×</text><rect x="114" y="36" width="42" height="30" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="135.0" y="57.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">3</text><rect x="164" y="36" width="42" height="30" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="185.0" y="57.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">=</text><rect x="214" y="36" width="42" height="30" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="235.0" y="57.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">51</text><line x1="272.0" y1="51.0" x2="291.0" y2="51.0" style="stroke:var(--muted);stroke-width:1.5;fill:none"/><path d="M300.0 51.0 L291.9 54.9 L291.9 47.1 z" style="fill:var(--muted)"/><rect x="310.0" y="37.5" width="14.0" height="38.5" rx="3" style="fill:var(--accent)"/><rect x="326.0" y="51.5" width="14.0" height="24.5" rx="3" style="fill:var(--warn)"/><rect x="348.0" y="62.0" width="14.0" height="14.0" rx="3" style="fill:var(--accent)"/><rect x="364.0" y="55.0" width="14.0" height="21.0" rx="3" style="fill:var(--warn)"/><rect x="386.0" y="65.5" width="14.0" height="10.5" rx="3" style="fill:var(--accent)"/><rect x="402.0" y="62.0" width="14.0" height="14.0" rx="3" style="fill:var(--warn)"/><rect x="424.0" y="69.0" width="14.0" height="7.0" rx="3" style="fill:var(--accent)"/><rect x="440.0" y="65.5" width="14.0" height="10.5" rx="3" style="fill:var(--warn)"/><text x="310.0" y="96.0" font-size="13" text-anchor="start" style="fill:var(--muted)">老师 p 与学生 q（示意）</text><text x="10.0" y="128.0" font-size="13" text-anchor="start" style="fill:var(--muted)">要老师在每个位置的全部概率（同一个分词器）。损失 KL(p ‖ q)，梯度 q − p。</text><text x="10.0" y="168.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--fg)">序列级：老师先写出整段回答，学生照着做 SFT</text><rect x="14" y="182" width="84" height="34" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="56.0" y="205.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">老师</text><line x1="102.0" y1="199.0" x2="127.0" y2="199.0" style="stroke:var(--muted);stroke-width:1.5;fill:none"/><path d="M136.0 199.0 L127.9 202.9 L127.9 195.1 z" style="fill:var(--muted)"/><rect x="142" y="182" width="50" height="34" rx="6" style="stroke:var(--accent);stroke-width:1.5;fill:none"/><text x="167.0" y="205.0" font-size="14" text-anchor="middle" style="fill:var(--accent)">51</text><rect x="198" y="182" width="50" height="34" rx="6" style="stroke:var(--accent);stroke-width:1.5;fill:none"/><text x="223.0" y="205.0" font-size="14" text-anchor="middle" style="fill:var(--accent)">。</text><rect x="254" y="182" width="50" height="34" rx="6" style="stroke:var(--accent);stroke-width:1.5;fill:none"/><text x="279.0" y="205.0" font-size="14" text-anchor="middle" style="fill:var(--accent)">&lt;end&gt;</text><line x1="316.0" y1="199.0" x2="341.0" y2="199.0" style="stroke:var(--muted);stroke-width:1.5;fill:none"/><path d="M350.0 199.0 L341.9 202.9 L341.9 195.1 z" style="fill:var(--muted)"/><rect x="356" y="182" width="110" height="34" rx="6" style="stroke:var(--warn);stroke-width:2;fill:none"/><text x="411.0" y="205.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">学生 SFT</text><text x="10.0" y="244.0" font-size="13" text-anchor="start" style="fill:var(--muted)">只要老师输出的文字。每个位置的目标是 one-hot，梯度 q − y。</text>
</svg>
<figcaption>图 8　上：词元级蒸馏，学生在每个位置对齐老师的整个下一个 token 分布（示意）。下：序列级蒸馏，老师写出的文字当作示范，学生做普通的 SFT，和后训练那一讲第二步一模一样。</figcaption>
</figure>

两种做法的取舍：

| | 词元级 | 序列级 |
| --- | --- | --- |
| 要老师给什么 | 每个位置整个词表的概率 | 只要老师输出的文字 |
| 分词器 | 必须和老师一样 | 无所谓 |
| 每个 token 的信息 | 整个分布（软标签） | 一个 token（硬标签） |
| 能不能通过 API 做 | 一般不能（API 最多给前几个 token 的概率） | 能 |

序列级蒸馏丢掉了软标签的信息，为什么还好用？因为老师写的文字本身就比人写的数据「好学」：风格统一、步骤完整、格式一致，正好是老师那个分布里最可能的样子。学生学的不是「人可能怎么写」，而是「老师最可能怎么写」，目标集中，小模型更容易装下。这也是为什么后训练里「用模型自己生成、再筛选出来的数据」越来越多：从某种意义上说，那就是在做序列级蒸馏。

## 推理能力的蒸馏：DeepSeek-R1

上一讲推理模型讲了 DeepSeek-R1 怎么用强化学习学会长推理。同一篇论文（DeepSeek-AI，arXiv 2501.12948，2025 年 1 月）还做了一件事：把 R1 的推理能力蒸馏进小模型。做法就是序列级蒸馏，下面的数字 2026-10-22 对照论文 v1 与官方模型卡核实：

- **数据**：用 R1 整理出约 80 万条样本，其中约 60 万条是推理数据（用 R1 训练中强化学习阶段的模型生成长推理，只保留答案正确、读得懂的），约 20 万条是写作、问答等非推理数据。这正是后训练那一讲图 7 里 R1 第二次 SFT 用的那批数据。
- **学生**：6 个开源底座：Qwen2.5-Math-1.5B、Qwen2.5-Math-7B、Qwen2.5-14B、Qwen2.5-32B、Llama-3.1-8B、Llama-3.3-70B-Instruct。
- **训练**：只做 SFT，**不做强化学习**。论文说加上强化学习还能显著提升，但这一步留给社区。

AIME 2024 每题答一次的正确率（pass@1，%）：

<figure class="fig">
<svg viewBox="0 0 480 314" role="img" aria-label="DeepSeek-R1 蒸馏模型在 AIME 2024 上的 pass@1">
<text x="140.0" y="27.0" font-size="14" text-anchor="end" style="fill:var(--muted)">GPT-4o-0513</text><rect x="150.0" y="14.0" width="25.1" height="18.0" rx="3" style="fill:var(--line)"/><text x="181.1" y="28.0" font-size="14" text-anchor="start" style="fill:var(--muted)">9.3</text><text x="140.0" y="57.0" font-size="14" text-anchor="end" style="fill:var(--muted)">Claude-3.5-Sonnet</text><rect x="150.0" y="44.0" width="43.2" height="18.0" rx="3" style="fill:var(--line)"/><text x="199.2" y="58.0" font-size="14" text-anchor="start" style="fill:var(--muted)">16.0</text><text x="140.0" y="87.0" font-size="14" text-anchor="end" style="fill:var(--fg)">蒸馏 Qwen-1.5B</text><rect x="150.0" y="74.0" width="78.0" height="18.0" rx="3" style="fill:var(--accent)"/><text x="234.0" y="88.0" font-size="14" text-anchor="start" style="fill:var(--accent)">28.9</text><text x="140.0" y="117.0" font-size="14" text-anchor="end" style="fill:var(--fg)">蒸馏 Llama-8B</text><rect x="150.0" y="104.0" width="136.1" height="18.0" rx="3" style="fill:var(--accent)"/><text x="292.1" y="118.0" font-size="14" text-anchor="start" style="fill:var(--accent)">50.4</text><text x="140.0" y="147.0" font-size="14" text-anchor="end" style="fill:var(--fg)">蒸馏 Qwen-7B</text><rect x="150.0" y="134.0" width="149.8" height="18.0" rx="3" style="fill:var(--accent)"/><text x="305.9" y="148.0" font-size="14" text-anchor="start" style="fill:var(--accent)">55.5</text><text x="140.0" y="177.0" font-size="14" text-anchor="end" style="fill:var(--fg)">蒸馏 Qwen-14B</text><rect x="150.0" y="164.0" width="188.2" height="18.0" rx="3" style="fill:var(--accent)"/><text x="344.2" y="178.0" font-size="14" text-anchor="start" style="fill:var(--accent)">69.7</text><text x="140.0" y="207.0" font-size="14" text-anchor="end" style="fill:var(--fg)">蒸馏 Llama-70B</text><rect x="150.0" y="194.0" width="189.0" height="18.0" rx="3" style="fill:var(--accent)"/><text x="345.0" y="208.0" font-size="14" text-anchor="start" style="fill:var(--accent)">70.0</text><text x="140.0" y="237.0" font-size="14" text-anchor="end" style="fill:var(--fg)">蒸馏 Qwen-32B</text><rect x="150.0" y="224.0" width="196.0" height="18.0" rx="3" style="fill:var(--accent)"/><text x="352.0" y="238.0" font-size="14" text-anchor="start" style="fill:var(--accent)">72.6</text><text x="140.0" y="267.0" font-size="14" text-anchor="end" style="fill:var(--fg)">Qwen-32B 纯 RL</text><rect x="150.0" y="254.0" width="126.9" height="18.0" rx="3" style="fill:var(--warn)"/><text x="282.9" y="268.0" font-size="14" text-anchor="start" style="fill:var(--warn)">47.0</text><text x="140.0" y="297.0" font-size="14" text-anchor="end" style="fill:var(--fg)">R1（老师）</text><rect x="150.0" y="284.0" width="215.5" height="18.0" rx="3" style="fill:var(--ok)"/><text x="371.5" y="298.0" font-size="14" text-anchor="start" style="fill:var(--ok)">79.8</text>
</svg>
<figcaption>图 9　AIME 2024 每题答一次的正确率（%）。蓝色是 6 个蒸馏学生，橙色是同一个 Qwen2.5-32B 底座不蒸馏、直接做大规模强化学习，绿色是老师 R1，灰色是两个对照模型。数字来自 DeepSeek-R1 论文表 4、5、6（2026-10-22 核实）。</figcaption>
</figure>

几个要看的地方：

1. **小模型也学会了长推理**。1.5B 的学生 AIME 28.9，高过 GPT-4o 的 9.3 和 Claude-3.5-Sonnet 的 16.0；32B 的学生 72.6，超过 o1-mini 的 63.6。数学题 MATH-500 上，7B 学生 92.8，32B 学生 94.3。
2. **蒸馏打败了直接强化学习**。论文的对照实验：同一个 Qwen2.5-32B 底座，不蒸馏，直接照 R1-Zero 的办法做大规模强化学习，AIME 只到 47.0；用 R1 的数据蒸馏，72.6。论文的结论是：把更强的模型蒸馏进小模型效果很好；小模型靠自己做大规模强化学习，需要巨大的算力，而且可能还达不到蒸馏的效果。
3. **学生没有超过老师**。R1 自己是 79.8，6 个学生都比它低。
4. **知识类的题，小模型装不下**。研究生水平的科学选择题 GPQA Diamond 上，1.5B 学生只有 33.8，低于 GPT-4o 的 49.9；70B 学生 65.2，接近老师 R1 的 71.5。推理的「写法」可以学过去，事实知识要靠参数去存。

<details class="pause"><summary>停一下：R1 的蒸馏用的是软标签还是硬标签？为什么这样选？</summary>

是硬标签：每条样本是 R1 写出来的一段文字，学生在每个位置学的是「下一个 token 是这个」，也就是序列级蒸馏。原因至少有两个：6 个学生里有 Qwen 也有 Llama，分词器和 R1 都不一样，词元级蒸馏的「类别」对不上；而且长推理动辄几千上万个 token，每个位置存十几万个概率，数据量太大。序列级蒸馏只要文字，换多少种学生都能用同一批数据。

</details>

## 蒸馏的边界

蒸馏很划算，但它有几条绕不过去的限制。

**学生学不到老师没表现出来的东西。** 学生能看到的只有老师在迁移数据（用来生成软标签或回答的那批输入）上的输出。老师在哪类输入上从没被问过，学生在那里就没有任何信号。老师在某道题上犯了错，学生也会把这个错学过去：蒸馏复制的是老师的行为，不是老师背后的「真相」。

反过来，只要老师表现出来了，哪怕方式很间接，学生也能学到。Hinton 等人做过一个实验：迁移数据里完全去掉数字 3，学生一张 3 都没见过；但老师在别的数字上给「像 3」的那点小概率，已经透露了 3 长什么样。只调整一下「3」这一类的偏置，学生就能认对测试集里 98.6% 的 3。这一点也正好说明前提：老师得在输出里把它**表现出来**。

**学生的上限是老师。** 第七步的学生最好也只是贴近老师，R1 的 6 个学生都低于 R1。论文的另一句结论也在说这件事：蒸馏又省又有效，但要再往前推进智能的边界，可能还是需要更强的底座和更大规模的强化学习。蒸馏能把已有的能力变便宜，不能创造新能力。

**学生得装得下。** 第七步的宽度 2 到 4、R1 学生在 GPQA 上的表现，都是同一回事：容量不够，老师给得再好也装不进去。

**许可协议。** 用别人的模型当老师之前要看协议：例如 OpenAI 的使用条款禁止「用输出开发与 OpenAI 竞争的模型」，而 DeepSeek-R1 用 MIT 协议、明确允许用来蒸馏，同时学生还要遵守自己底座的协议（R1 的 Llama 学生仍受 Llama 协议约束）（2026-10-22 核实）。

## 实验里讲了什么

1. **温度**：拖动 $T$，看老师的软分布怎么变平，狗与汽车的概率比 $e^{6/T}$ 怎么缩小，熵怎么升高。
2. **KL 损失与交叉熵计算器**：选不同的学生、拖 $T$ 和 $\alpha$、开关「乘 $T^2$」，看两项损失和它们给每个 logit 的梯度；下面的曲线是软标签梯度长度随 $T$ 的变化，乘与不乘 $T^2$。
3. **真实训练**：浏览器里训练一个老师 MLP 和两个学生 MLP，一个用硬标签、一个用软标签，比较验证错误率和分界；可以改学生拿到的点数和温度。
4. **学生容量**：学生隐藏层宽度从 1 到 32，各训练一对学生，看错误率曲线和每个宽度下的分界。
5. **DeepSeek-R1 蒸馏成绩**：6 个蒸馏学生、纯 RL 对照、老师 R1 和三个对照模型在五个指标上的分数。

## 和前后两讲的关系

后训练那一讲讲了 SFT：照着示范学，梯度是 $p - y$。这一讲把示范换成了老师：软标签把 $y$ 换成老师的分布，梯度变成 $(q - p)/T$；序列级蒸馏则干脆就是拿老师写的文字做 SFT。上一讲推理模型讲了 R1 怎么用强化学习学会长推理，这一讲看到它怎么把这个能力交给小模型。下一讲讲模型评测：蒸馏出来的小模型分数很好看，但「AIME 72.6」测的是什么、误差有多大、题目有没有漏进训练数据，都得用评测那一讲的工具去问。

## 延伸阅读

- Geoffrey Hinton, Oriol Vinyals, Jeff Dean, *Distilling the Knowledge in a Neural Network* (2015)，温度、软标签、$T^2$ 与 MNIST 去掉数字 3 的实验
- Yoon Kim, Alexander M. Rush, *Sequence-Level Knowledge Distillation* (2016)，序列级蒸馏
- Gemma Team, *Gemma 2: Improving Open Language Models at a Practical Size* (2024)，第 3.2 节：预训练阶段的词元级蒸馏
- DeepSeek-AI, *DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning* (2025)，第 2.4 节与第 4.1 节：蒸馏与强化学习的对比
