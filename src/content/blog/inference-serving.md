---
title: "推理服务：一张卡怎么同时伺候几百个用户"
description: "一张 H100 跑 Llama-3-8B，只服务一个人时 99% 以上的算力在等数据。用同一组数字一步步算：为什么 decode 受带宽限制、batch 为什么几乎白送、KV cache 为什么又把它吃回去；再看连续批处理、PagedAttention、prefix caching、投机解码，以及吞吐和延迟怎么取舍。"
pubDate: 2026-10-22
tags: ["LLM 推理", "推理服务", "连续批处理", "PagedAttention", "投机解码", "vLLM"]
lab: /labs/inference-serving/
series: ai-mastery
order: 13
---

<!-- 本文由 labs-src/inference-serving/toy.py 从 article.src.md 生成，图和数字都由脚本算出。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

生成阶段（decode）每出一个 token，都要把模型的全部权重从显存读一遍，而每个权重只做一次乘加，所以一个人用的时候，GPU 绝大部分时间在等数据。推理服务的核心办法是**让很多人共用这一次读取**：把几百个请求拼成一批（batch），读一遍权重，几百个人各出一个 token。剩下的工作都是围绕这件事展开的：请求有长有短，要随时补位（连续批处理）；每个人的 KV cache 要存，要存得不浪费（PagedAttention），相同的开头只存一份（prefix caching）；一个人用时算力闲着，就让小模型先猜几个 token、大模型一次验证（投机解码）。最后，batch 越大总量越多、每个人越慢，要在吞吐和延迟之间选一个点。

## 第一步：只有一个用户时，GPU 在干什么

整讲用同一个例子：**一张 H100 SXM 显卡，跑 Llama-3-8B，权重用 BF16 存。**

H100 SXM 的三个数（NVIDIA 规格表，2026-10 核实）：

- 显存 80 GB；
- 显存带宽 3.35 TB/s，即每秒能从显存读 3.35 万亿字节；
- BF16 稠密算力 989.4 TFLOPS，即每秒能做 989.4 万亿次浮点运算（一次乘法或一次加法算一次）。

Llama-3-8B 有 8,030,261,248 个参数。BF16 每个参数占 2 字节，权重一共：

$$
8{,}030{,}261{,}248 \times 2\ \text{B} = 16.06\ \text{GB}
$$

硬件那一讲和量化那一讲都说过：decode 每出一个 token，要把全部权重从显存搬进计算单元一遍。先只算这一项（KV cache 第三步再加），搬一遍要：

$$
\frac{16.06\ \text{GB}}{3.35\ \text{TB/s}} = \frac{16.06 \times 10^{9}}{3.35 \times 10^{12}}\ \text{s} = 4.79\ \text{ms}
$$

搬进来之后要算多少？每个参数和输入相乘一次、再加到结果里一次，是 2 次运算，所以一个 token 要：

$$
2 \times 8{,}030{,}261{,}248 = 16.06 \times 10^{9}\ \text{次运算}
$$

H100 算完它要：

$$
\frac{16.06 \times 10^{9}}{989.4 \times 10^{12}}\ \text{s} = 0.0162\ \text{ms}
$$

<figure class="fig">
<svg viewBox="0 0 480 190" role="img" aria-label="batch 为 1 时读权重与计算各花多少时间">
<text x="20.0" y="28.0" font-size="16" text-anchor="start" style="fill:var(--muted)">生成 1 个 token（batch 1）</text><text x="120.0" y="74.0" font-size="16" text-anchor="end" style="fill:var(--fg)">读权重</text><rect x="130.0" y="56.0" width="250.0" height="26.0" rx="3" style="fill:var(--accent)"/><text x="388.0" y="75.0" font-size="16" text-anchor="start" style="fill:var(--accent)">4.79 ms</text><text x="120.0" y="124.0" font-size="16" text-anchor="end" style="fill:var(--fg)">计算</text><rect x="130.0" y="106.0" width="1.5" height="26.0" rx="3" style="fill:var(--warn)"/><text x="140.0" y="125.0" font-size="16" text-anchor="start" style="fill:var(--warn)">0.0162 ms</text><text x="20.0" y="172.0" font-size="16" text-anchor="start" style="fill:var(--muted)">计算单元有 99.66% 的时间在等数据</text>
</svg>
<figcaption>图 1　Llama-3-8B 在 H100 上生成 1 个 token：把 16.06 GB 权重从显存读一遍要 4.79 ms，真正的乘加只要 0.0162 ms，橙条细到几乎看不见。</figcaption>
</figure>

搬数据 4.79 ms，计算 0.0162 ms，差了 295 倍。计算单元只在 $1/295$（约 0.34%） 的时间里干活，其余时间在等数据。这时速度完全由带宽决定：一秒最多出 $1 / 4.79\ \text{ms} \approx 209$ 个 token。这就是「decode 受带宽限制」的意思。

<details class="pause"><summary>停一下：按量化那一讲，把权重换成 INT4（按组 128，每个权重约 4.125 位），一个人用时每秒最多出几个 token？算力利用率变高还是变低？</summary>

权重变成 $8{,}030{,}261{,}248 \times 4.125 / 8 = 4.14\ \text{GB}$，读一遍要 $4.14 / 3.35\ \text{TB/s} = 1.24\ \text{ms}$，每秒最多 809 个 token，快了将近 4 倍。要算的运算次数没变（反量化还要多算一点），时间却短了，所以算力利用率变高了，但仍然只有 1% 左右，GPU 照样大部分时间在等。

</details>

## 第二步：一份权重，很多人共用

现在有 64 个用户同时在等回答。最笨的做法是一个一个来：每人 4.79 ms，轮一圈要 $64 \times 4.79\ \text{ms} \approx 306.8\ \text{ms}$。

注意一件事：64 个人用的是**同一份权重**。把 64 个人这一步的输入拼成一个 64 行的矩阵，权重读进来一次，和 64 行分别相乘，64 个人各得到一个 token。这叫**批处理**（batching），64 是 **batch 大小** $B$。

这一步要读的字节没变，还是 16.06 GB，搬运时间还是 4.79 ms。运算次数变成 64 倍：

$$
64 \times 16.06 \times 10^{9} = 1.03 \times 10^{12}\ \text{次}, \qquad \frac{1.03 \times 10^{12}}{989.4 \times 10^{12}}\ \text{s} = 1.04\ \text{ms}
$$

1.04 ms 仍然比 4.79 ms 短，计算可以和搬运同时进行，所以这一步还是 4.79 ms，但出了 64 个 token。整张卡每秒出 $64 / 4.79\ \text{ms} \approx 13,350$ 个 token，是一个人时的 64 倍，几乎白送。

能一直白送下去吗？用一个数来判断：**算术强度**，即每从显存读 1 字节，做多少次运算（单位 FLOP/B）。

- batch $B$ 时，运算 $= B \times 2 \times 8{,}030{,}261{,}248$，读的字节 $= 2 \times 8{,}030{,}261{,}248$，两者相除，算术强度正好是 $B$。
- H100 自己也有一个比值：算力除以带宽，$989.4 \times 10^{12} / 3.35 \times 10^{12} \approx 295$ FLOP/B。意思是每读 1 字节，它有能力做 295 次运算。

算术强度低于 295，数据跟不上，速度由带宽决定，强度每翻一倍，每秒完成的运算也翻一倍；高于 295，算力用满，再加大 batch 也不会更快。把这两段画在一起，就是**屋顶线**（roofline）：

$$
\text{可达到的算力} = \min\left(\text{峰值算力},\ \text{算术强度} \times \text{带宽}\right)
$$

<figure class="fig">
<svg viewBox="0 0 480 320" role="img" aria-label="屋顶线：算术强度与可达到的算力">
<line x1="70.0" y1="260.0" x2="450.0" y2="260.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="70.0" y1="260.0" x2="70.0" y2="40.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="101.7" y1="260.0" x2="101.7" y2="265.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="101.7" y="282.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><line x1="207.2" y1="260.0" x2="207.2" y2="265.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="207.2" y="282.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10</text><line x1="312.8" y1="260.0" x2="312.8" y2="265.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="312.8" y="282.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">100</text><line x1="418.3" y1="260.0" x2="418.3" y2="265.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="418.3" y="282.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1,000</text><line x1="65.0" y1="260.0" x2="70.0" y2="260.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="265.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1</text><line x1="65.0" y1="193.3" x2="70.0" y2="193.3" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="198.3" font-size="14" text-anchor="end" style="fill:var(--muted)">10</text><line x1="65.0" y1="126.7" x2="70.0" y2="126.7" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="131.7" font-size="14" text-anchor="end" style="fill:var(--muted)">100</text><line x1="65.0" y1="60.0" x2="70.0" y2="60.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="62.0" y="65.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1000</text><text x="450.0" y="304.0" font-size="15" text-anchor="end" style="fill:var(--muted)">算术强度（FLOP/B）</text><text x="62.0" y="30.0" font-size="15" text-anchor="start" style="fill:var(--muted)">TFLOPS</text><polyline points="70.0,245.0 71.9,243.8 73.8,242.6 75.7,241.4 77.6,240.2 79.5,239.0 81.4,237.8 83.3,236.6 85.2,235.4 87.1,234.2 89.0,233.0 90.9,231.8 92.8,230.6 94.7,229.4 96.6,228.2 98.5,227.0 100.4,225.8 102.3,224.6 104.2,223.4 106.1,222.2 108.0,221.0 109.9,219.8 111.8,218.6 113.7,217.4 115.6,216.2 117.5,215.0 119.4,213.8 121.3,212.6 123.2,211.4 125.1,210.2 127.0,209.0 128.9,207.8 130.8,206.6 132.7,205.4 134.6,204.2 136.5,203.0 138.4,201.8 140.3,200.6 142.2,199.4 144.1,198.2 146.0,197.0 147.9,195.8 149.8,194.6 151.7,193.4 153.6,192.2 155.5,191.0 157.4,189.8 159.3,188.6 161.2,187.4 163.1,186.2 165.0,185.0 166.9,183.8 168.8,182.6 170.7,181.4 172.6,180.2 174.5,179.0 176.4,177.8 178.3,176.6 180.2,175.4 182.1,174.2 184.0,173.0 185.9,171.8 187.8,170.6 189.7,169.4 191.6,168.2 193.5,167.0 195.4,165.8 197.3,164.6 199.2,163.4 201.1,162.2 203.0,161.0 204.9,159.8 206.8,158.6 208.7,157.4 210.6,156.2 212.5,155.0 214.4,153.8 216.3,152.6 218.2,151.4 220.1,150.2 222.0,149.0 223.9,147.8 225.8,146.6 227.7,145.4 229.6,144.2 231.5,143.0 233.4,141.8 235.3,140.6 237.2,139.4 239.1,138.2 241.0,137.0 242.9,135.8 244.8,134.6 246.7,133.4 248.6,132.2 250.5,131.0 252.4,129.8 254.3,128.6 256.2,127.4 258.1,126.2 260.0,125.0 261.9,123.8 263.8,122.6 265.7,121.4 267.6,120.2 269.5,119.0 271.4,117.8 273.3,116.6 275.2,115.4 277.1,114.2 279.0,113.0 280.9,111.8 282.8,110.6 284.7,109.4 286.6,108.2 288.5,107.0 290.4,105.8 292.3,104.6 294.2,103.4 296.1,102.2 298.0,101.0 299.9,99.8 301.8,98.6 303.7,97.4 305.6,96.2 307.5,95.0 309.4,93.8 311.3,92.6 313.2,91.4 315.1,90.2 317.0,89.0 318.9,87.8 320.8,86.6 322.7,85.4 324.6,84.2 326.5,83.0 328.4,81.8 330.3,80.6 332.2,79.4 334.1,78.2 336.0,77.0 337.9,75.8 339.8,74.6 341.7,73.4 343.6,72.2 345.5,71.0 347.4,69.8 349.3,68.6 351.2,67.4 353.1,66.2 355.0,65.0 356.9,63.8 358.8,62.6 360.7,61.4 362.6,60.3 364.5,60.3 366.4,60.3 368.3,60.3 370.2,60.3 372.1,60.3 374.0,60.3 375.9,60.3 377.8,60.3 379.7,60.3 381.6,60.3 383.5,60.3 385.4,60.3 387.3,60.3 389.2,60.3 391.1,60.3 393.0,60.3 394.9,60.3 396.8,60.3 398.7,60.3 400.6,60.3 402.5,60.3 404.4,60.3 406.3,60.3 408.2,60.3 410.1,60.3 412.0,60.3 413.9,60.3 415.8,60.3 417.7,60.3 419.6,60.3 421.5,60.3 423.4,60.3 425.3,60.3 427.2,60.3 429.1,60.3 431.0,60.3 432.9,60.3 434.8,60.3 436.7,60.3 438.6,60.3 440.5,60.3 442.4,60.3 444.3,60.3 446.2,60.3 448.1,60.3 450.0,60.3" style="stroke:var(--fg);stroke-width:2.5;fill:none"/><text x="368.4" y="52.3" font-size="15" text-anchor="start" style="fill:var(--fg)">拐点 295</text><text x="183.8" y="207.1" font-size="15" text-anchor="start" style="fill:var(--muted)">带宽限制</text><circle cx="101.7" cy="225.0" r="5.5" style="fill:var(--accent)"/><text x="109.7" y="243.0" font-size="15" text-anchor="start" style="fill:var(--accent)">B = 1</text><circle cx="228.8" cy="144.7" r="5.5" style="fill:var(--accent)"/><text x="236.8" y="162.7" font-size="15" text-anchor="start" style="fill:var(--accent)">B = 16</text><circle cx="292.3" cy="104.6" r="5.5" style="fill:var(--accent)"/><text x="300.3" y="122.6" font-size="15" text-anchor="start" style="fill:var(--accent)">B = 64</text>
</svg>
<figcaption>图 2　H100 的屋顶线（两轴都是对数刻度）。拐点左边，速度由带宽决定，越往右越快；拐点 295 右边，算力用满，再往右也不会更快。蓝点是只算权重时 batch 1、16、64 的位置。</figcaption>
</figure>

只看权重的话，batch 一直加到 295 左右都是白送。可我们漏算了一样东西。

## 第三步：把 KV cache 算进来

KV Cache 那一讲讲过：每个 token 在每一层都存一份 K 和一份 V，生成下一个 token 时，前面所有 token 的 K、V 都要读一遍。Llama-3-8B 每个 token 的 KV cache 是：

$$
\underbrace{2}_{K \text{ 和 } V} \times \underbrace{32}_{\text{层}} \times \underbrace{8}_{\text{KV 头}} \times \underbrace{128}_{\text{头维度}} \times \underbrace{2\ \text{B}}_{\text{BF16}} = 131,072\ \text{B}
$$

（8 个 KV 头而不是 32 个，是多头那一讲的 GQA 省下来的。）

假设每个用户的对话已经有 1000 个 token，一个人的 KV cache 就是：

$$
1000 \times 131,072\ \text{B} = 131.1\ \text{MB}
$$

关键在于：权重是大家共用的，**KV cache 是每人一份**。batch 里有 $B$ 个人，这一步就要读 $B$ 份。于是一步要读的字节变成：

$$
\text{读的字节} = 16.06\ \text{GB} + B \times 0.1311\ \text{GB}
$$

代入 $B = 64$：

$$
16.06 + 64 \times 0.1311 = 16.06 + 8.39 = 24.45\ \text{GB}
$$

$$
\frac{24.45\ \text{GB}}{3.35\ \text{TB/s}} = 7.30\ \text{ms}
$$

<figure class="fig">
<svg viewBox="0 0 480 158" role="img" aria-label="batch 64 时一步要读的权重与 KV cache">
<text x="20.0" y="28.0" font-size="16" text-anchor="start" style="fill:var(--muted)">batch 64，每人上下文 1000 个 token：一步要读的字节</text><rect x="20.0" y="50.0" width="289.0" height="34.0" rx="3" style="fill:var(--accent)"/><text x="164.5" y="73.0" font-size="15" text-anchor="middle" style="fill:var(--bg)">权重 16.06 GB</text><rect x="309.0" y="50.0" width="151.0" height="34.0" rx="3" style="fill:var(--warn)"/><line x1="327.9" y1="50.0" x2="327.9" y2="84.0" style="stroke:var(--bg);stroke-width:1.2;fill:none"/><line x1="346.8" y1="50.0" x2="346.8" y2="84.0" style="stroke:var(--bg);stroke-width:1.2;fill:none"/><line x1="365.6" y1="50.0" x2="365.6" y2="84.0" style="stroke:var(--bg);stroke-width:1.2;fill:none"/><line x1="384.5" y1="50.0" x2="384.5" y2="84.0" style="stroke:var(--bg);stroke-width:1.2;fill:none"/><line x1="403.4" y1="50.0" x2="403.4" y2="84.0" style="stroke:var(--bg);stroke-width:1.2;fill:none"/><line x1="422.3" y1="50.0" x2="422.3" y2="84.0" style="stroke:var(--bg);stroke-width:1.2;fill:none"/><line x1="441.1" y1="50.0" x2="441.1" y2="84.0" style="stroke:var(--bg);stroke-width:1.2;fill:none"/><text x="384.5" y="108.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">64 份 KV cache，共 8.39 GB</text><text x="20.0" y="140.0" font-size="16" text-anchor="start" style="fill:var(--fg)">合计 24.45 GB ÷ 3.35 TB/s = 7.30 ms</text>
</svg>
<figcaption>图 3　蓝色的权重 64 个人共用，读一遍就够；橙色的 KV cache 每人一份，有几个人就要读几份。</figcaption>
</figure>

运算也多了一点：注意力要拿当前位置的 $q$ 和前面 1000 个 $k$ 做点积、再按份额加权 1000 个 $v$，每个 token 多出约 $0.52 \times 10^{9}$ 次运算，合计每人 $16.58 \times 10^{9}$ 次。64 人共 1.07 ms，仍小于 7.30 ms，所以这一步是 7.30 ms，出 64 个 token：

- 整张卡每秒：$64 / 7.30\ \text{ms} \approx 8,769$ 个 token；
- 每个用户每秒：$1 / 7.30\ \text{ms} \approx 137.0$ 个 token。

换几个 batch 大小，同样算：

| batch $B$ | 一步读的字节 | 一步的时间 | 计算占用 | 整卡 token/s | 每个用户 token/s |
| --- | --- | --- | --- | --- | --- |
| 1 | 16.19 GB | 4.83 ms | 0.3% | 207 | 206.9 |
| 8 | 17.11 GB | 5.11 ms | 2.6% | 1,566 | 195.8 |
| 64 | 24.45 GB | 7.30 ms | 14.7% | 8,769 | 137.0 |
| 256 | 49.61 GB | 14.81 ms | 29.0% | 17,285 | 67.5 |
| 487 | 79.89 GB | 23.85 ms | 34.2% | 20,421 | 41.9 |

最后一行的 487 是显存的上限：80 GB 减去权重 16.06 GB 还剩 63.94 GB，每人 0.1311 GB，最多放 $\lfloor 63.94 / 0.1311 \rfloor = 487$ 个人（这里没扣激活值等运行开销，实际要再少一些）。这张卡在这个设定下，最多同时伺候 487 个用户。

<figure class="fig">
<svg viewBox="0 0 480 300" role="img" aria-label="总吞吐与每个用户的速度随 batch 的变化">
<line x1="70.0" y1="250.0" x2="430.0" y2="250.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="70.0" y1="250.0" x2="70.0" y2="50.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="430.0" y1="250.0" x2="430.0" y2="50.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="70.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0</text><text x="142.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">100</text><text x="214.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">200</text><text x="286.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">300</text><text x="358.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">400</text><text x="430.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">500</text><text x="64.0" y="255.0" font-size="14" text-anchor="end" style="fill:var(--accent)">0</text><text x="64.0" y="164.1" font-size="14" text-anchor="end" style="fill:var(--accent)">10k</text><text x="64.0" y="73.2" font-size="14" text-anchor="end" style="fill:var(--accent)">20k</text><text x="436.0" y="255.0" font-size="14" text-anchor="start" style="fill:var(--warn)">0</text><text x="436.0" y="164.1" font-size="14" text-anchor="start" style="fill:var(--warn)">100</text><text x="436.0" y="73.2" font-size="14" text-anchor="start" style="fill:var(--warn)">200</text><text x="250.0" y="290.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">batch（同时服务的用户数）</text><polyline points="70.7,248.1 71.4,246.3 72.2,244.4 72.9,242.7 73.6,240.9 74.3,239.2 75.0,237.4 75.8,235.8 76.5,234.1 77.2,232.5 77.9,230.9 78.6,229.3 79.4,227.7 80.1,226.2 80.8,224.7 81.5,223.2 82.2,221.7 83.0,220.2 83.7,218.8 84.4,217.4 85.1,216.0 85.8,214.6 86.6,213.3 87.3,211.9 88.0,210.6 88.7,209.3 89.4,208.0 90.2,206.8 90.9,205.5 91.6,204.3 92.3,203.1 93.0,201.9 93.8,200.7 94.5,199.5 95.2,198.4 95.9,197.2 96.6,196.1 97.4,195.0 98.1,193.9 98.8,192.8 99.5,191.7 100.2,190.7 101.0,189.6 101.7,188.6 102.4,187.6 103.1,186.6 103.8,185.6 104.6,184.6 105.3,183.6 106.0,182.7 106.7,181.7 107.4,180.8 108.2,179.8 108.9,178.9 109.6,178.0 110.3,177.1 111.0,176.2 111.8,175.4 112.5,174.5 113.2,173.6 113.9,172.8 114.6,171.9 115.4,171.1 116.1,170.3 116.8,169.5 117.5,168.7 118.2,167.9 119.0,167.1 119.7,166.3 120.4,165.5 121.1,164.8 121.8,164.0 122.6,163.3 123.3,162.5 124.0,161.8 124.7,161.1 125.4,160.3 126.2,159.6 126.9,158.9 127.6,158.2 128.3,157.5 129.0,156.8 129.8,156.2 130.5,155.5 131.2,154.8 131.9,154.2 132.6,153.5 133.4,152.9 134.1,152.2 134.8,151.6 135.5,151.0 136.2,150.4 137.0,149.7 137.7,149.1 138.4,148.5 139.1,147.9 139.8,147.3 140.6,146.7 141.3,146.2 142.0,145.6 142.7,145.0 143.4,144.4 144.2,143.9 144.9,143.3 145.6,142.8 146.3,142.2 147.0,141.7 147.8,141.1 148.5,140.6 149.2,140.1 149.9,139.6 150.6,139.0 151.4,138.5 152.1,138.0 152.8,137.5 153.5,137.0 154.2,136.5 155.0,136.0 155.7,135.5 156.4,135.0 157.1,134.6 157.8,134.1 158.6,133.6 159.3,133.1 160.0,132.7 160.7,132.2 161.4,131.7 162.2,131.3 162.9,130.8 163.6,130.4 164.3,129.9 165.0,129.5 165.8,129.1 166.5,128.6 167.2,128.2 167.9,127.8 168.6,127.3 169.4,126.9 170.1,126.5 170.8,126.1 171.5,125.7 172.2,125.3 173.0,124.9 173.7,124.5 174.4,124.1 175.1,123.7 175.8,123.3 176.6,122.9 177.3,122.5 178.0,122.1 178.7,121.7 179.4,121.4 180.2,121.0 180.9,120.6 181.6,120.2 182.3,119.9 183.0,119.5 183.8,119.1 184.5,118.8 185.2,118.4 185.9,118.1 186.6,117.7 187.4,117.4 188.1,117.0 188.8,116.7 189.5,116.3 190.2,116.0 191.0,115.6 191.7,115.3 192.4,115.0 193.1,114.6 193.8,114.3 194.6,114.0 195.3,113.7 196.0,113.3 196.7,113.0 197.4,112.7 198.2,112.4 198.9,112.1 199.6,111.8 200.3,111.4 201.0,111.1 201.8,110.8 202.5,110.5 203.2,110.2 203.9,109.9 204.6,109.6 205.4,109.3 206.1,109.0 206.8,108.7 207.5,108.5 208.2,108.2 209.0,107.9 209.7,107.6 210.4,107.3 211.1,107.0 211.8,106.8 212.6,106.5 213.3,106.2 214.0,105.9 214.7,105.6 215.4,105.4 216.2,105.1 216.9,104.8 217.6,104.6 218.3,104.3 219.0,104.0 219.8,103.8 220.5,103.5 221.2,103.3 221.9,103.0 222.6,102.8 223.4,102.5 224.1,102.2 224.8,102.0 225.5,101.7 226.2,101.5 227.0,101.3 227.7,101.0 228.4,100.8 229.1,100.5 229.8,100.3 230.6,100.0 231.3,99.8 232.0,99.6 232.7,99.3 233.4,99.1 234.2,98.9 234.9,98.6 235.6,98.4 236.3,98.2 237.0,98.0 237.8,97.7 238.5,97.5 239.2,97.3 239.9,97.1 240.6,96.8 241.4,96.6 242.1,96.4 242.8,96.2 243.5,96.0 244.2,95.8 245.0,95.5 245.7,95.3 246.4,95.1 247.1,94.9 247.8,94.7 248.6,94.5 249.3,94.3 250.0,94.1 250.7,93.9 251.4,93.7 252.2,93.5 252.9,93.3 253.6,93.1 254.3,92.9 255.0,92.7 255.8,92.5 256.5,92.3 257.2,92.1 257.9,91.9 258.6,91.7 259.4,91.5 260.1,91.3 260.8,91.1 261.5,90.9 262.2,90.7 263.0,90.6 263.7,90.4 264.4,90.2 265.1,90.0 265.8,89.8 266.6,89.6 267.3,89.4 268.0,89.3 268.7,89.1 269.4,88.9 270.2,88.7 270.9,88.6 271.6,88.4 272.3,88.2 273.0,88.0 273.8,87.9 274.5,87.7 275.2,87.5 275.9,87.3 276.6,87.2 277.4,87.0 278.1,86.8 278.8,86.7 279.5,86.5 280.2,86.3 281.0,86.2 281.7,86.0 282.4,85.8 283.1,85.7 283.8,85.5 284.6,85.4 285.3,85.2 286.0,85.0 286.7,84.9 287.4,84.7 288.2,84.6 288.9,84.4 289.6,84.2 290.3,84.1 291.0,83.9 291.8,83.8 292.5,83.6 293.2,83.5 293.9,83.3 294.6,83.2 295.4,83.0 296.1,82.9 296.8,82.7 297.5,82.6 298.2,82.4 299.0,82.3 299.7,82.1 300.4,82.0 301.1,81.8 301.8,81.7 302.6,81.6 303.3,81.4 304.0,81.3 304.7,81.1 305.4,81.0 306.2,80.8 306.9,80.7 307.6,80.6 308.3,80.4 309.0,80.3 309.8,80.1 310.5,80.0 311.2,79.9 311.9,79.7 312.6,79.6 313.4,79.5 314.1,79.3 314.8,79.2 315.5,79.1 316.2,78.9 317.0,78.8 317.7,78.7 318.4,78.5 319.1,78.4 319.8,78.3 320.6,78.2 321.3,78.0 322.0,77.9 322.7,77.8 323.4,77.6 324.2,77.5 324.9,77.4 325.6,77.3 326.3,77.1 327.0,77.0 327.8,76.9 328.5,76.8 329.2,76.7 329.9,76.5 330.6,76.4 331.4,76.3 332.1,76.2 332.8,76.0 333.5,75.9 334.2,75.8 335.0,75.7 335.7,75.6 336.4,75.5 337.1,75.3 337.8,75.2 338.6,75.1 339.3,75.0 340.0,74.9 340.7,74.8 341.4,74.6 342.2,74.5 342.9,74.4 343.6,74.3 344.3,74.2 345.0,74.1 345.8,74.0 346.5,73.9 347.2,73.7 347.9,73.6 348.6,73.5 349.4,73.4 350.1,73.3 350.8,73.2 351.5,73.1 352.2,73.0 353.0,72.9 353.7,72.8 354.4,72.7 355.1,72.6 355.8,72.5 356.6,72.3 357.3,72.2 358.0,72.1 358.7,72.0 359.4,71.9 360.2,71.8 360.9,71.7 361.6,71.6 362.3,71.5 363.0,71.4 363.8,71.3 364.5,71.2 365.2,71.1 365.9,71.0 366.6,70.9 367.4,70.8 368.1,70.7 368.8,70.6 369.5,70.5 370.2,70.4 371.0,70.3 371.7,70.2 372.4,70.1 373.1,70.0 373.8,69.9 374.6,69.8 375.3,69.7 376.0,69.6 376.7,69.6 377.4,69.5 378.2,69.4 378.9,69.3 379.6,69.2 380.3,69.1 381.0,69.0 381.8,68.9 382.5,68.8 383.2,68.7 383.9,68.6 384.6,68.5 385.4,68.4 386.1,68.4 386.8,68.3 387.5,68.2 388.2,68.1 389.0,68.0 389.7,67.9 390.4,67.8 391.1,67.7 391.8,67.6 392.6,67.6 393.3,67.5 394.0,67.4 394.7,67.3 395.4,67.2 396.2,67.1 396.9,67.0 397.6,66.9 398.3,66.9 399.0,66.8 399.8,66.7 400.5,66.6 401.2,66.5 401.9,66.4 402.6,66.4 403.4,66.3 404.1,66.2 404.8,66.1 405.5,66.0 406.2,65.9 407.0,65.9 407.7,65.8 408.4,65.7 409.1,65.6 409.8,65.5 410.6,65.5 411.3,65.4 412.0,65.3 412.7,65.2 413.4,65.1 414.2,65.1 414.9,65.0 415.6,64.9 416.3,64.8 417.0,64.7 417.8,64.7 418.5,64.6 419.2,64.5 419.9,64.4 420.6,64.4" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><polyline points="70.7,61.9 71.4,63.4 72.2,64.9 72.9,66.4 73.6,67.8 74.3,69.2 75.0,70.6 75.8,72.0 76.5,73.4 77.2,74.7 77.9,76.0 78.6,77.3 79.4,78.6 80.1,79.8 80.8,81.1 81.5,82.3 82.2,83.5 83.0,84.7 83.7,85.8 84.4,87.0 85.1,88.1 85.8,89.2 86.6,90.3 87.3,91.4 88.0,92.5 88.7,93.6 89.4,94.6 90.2,95.6 90.9,96.7 91.6,97.7 92.3,98.7 93.0,99.6 93.8,100.6 94.5,101.6 95.2,102.5 95.9,103.4 96.6,104.4 97.4,105.3 98.1,106.2 98.8,107.0 99.5,107.9 100.2,108.8 101.0,109.6 101.7,110.5 102.4,111.3 103.1,112.1 103.8,112.9 104.6,113.8 105.3,114.5 106.0,115.3 106.7,116.1 107.4,116.9 108.2,117.6 108.9,118.4 109.6,119.1 110.3,119.9 111.0,120.6 111.8,121.3 112.5,122.0 113.2,122.7 113.9,123.4 114.6,124.1 115.4,124.8 116.1,125.4 116.8,126.1 117.5,126.8 118.2,127.4 119.0,128.1 119.7,128.7 120.4,129.3 121.1,129.9 121.8,130.6 122.6,131.2 123.3,131.8 124.0,132.4 124.7,133.0 125.4,133.6 126.2,134.1 126.9,134.7 127.6,135.3 128.3,135.8 129.0,136.4 129.8,137.0 130.5,137.5 131.2,138.0 131.9,138.6 132.6,139.1 133.4,139.6 134.1,140.2 134.8,140.7 135.5,141.2 136.2,141.7 137.0,142.2 137.7,142.7 138.4,143.2 139.1,143.7 139.8,144.2 140.6,144.6 141.3,145.1 142.0,145.6 142.7,146.1 143.4,146.5 144.2,147.0 144.9,147.4 145.6,147.9 146.3,148.3 147.0,148.8 147.8,149.2 148.5,149.6 149.2,150.1 149.9,150.5 150.6,150.9 151.4,151.4 152.1,151.8 152.8,152.2 153.5,152.6 154.2,153.0 155.0,153.4 155.7,153.8 156.4,154.2 157.1,154.6 157.8,155.0 158.6,155.4 159.3,155.8 160.0,156.1 160.7,156.5 161.4,156.9 162.2,157.3 162.9,157.6 163.6,158.0 164.3,158.4 165.0,158.7 165.8,159.1 166.5,159.4 167.2,159.8 167.9,160.1 168.6,160.5 169.4,160.8 170.1,161.2 170.8,161.5 171.5,161.8 172.2,162.2 173.0,162.5 173.7,162.8 174.4,163.2 175.1,163.5 175.8,163.8 176.6,164.1 177.3,164.4 178.0,164.7 178.7,165.1 179.4,165.4 180.2,165.7 180.9,166.0 181.6,166.3 182.3,166.6 183.0,166.9 183.8,167.2 184.5,167.5 185.2,167.8 185.9,168.1 186.6,168.3 187.4,168.6 188.1,168.9 188.8,169.2 189.5,169.5 190.2,169.7 191.0,170.0 191.7,170.3 192.4,170.6 193.1,170.8 193.8,171.1 194.6,171.4 195.3,171.6 196.0,171.9 196.7,172.2 197.4,172.4 198.2,172.7 198.9,172.9 199.6,173.2 200.3,173.5 201.0,173.7 201.8,174.0 202.5,174.2 203.2,174.4 203.9,174.7 204.6,174.9 205.4,175.2 206.1,175.4 206.8,175.7 207.5,175.9 208.2,176.1 209.0,176.4 209.7,176.6 210.4,176.8 211.1,177.1 211.8,177.3 212.6,177.5 213.3,177.7 214.0,178.0 214.7,178.2 215.4,178.4 216.2,178.6 216.9,178.8 217.6,179.1 218.3,179.3 219.0,179.5 219.8,179.7 220.5,179.9 221.2,180.1 221.9,180.3 222.6,180.5 223.4,180.8 224.1,181.0 224.8,181.2 225.5,181.4 226.2,181.6 227.0,181.8 227.7,182.0 228.4,182.2 229.1,182.4 229.8,182.6 230.6,182.8 231.3,183.0 232.0,183.1 232.7,183.3 233.4,183.5 234.2,183.7 234.9,183.9 235.6,184.1 236.3,184.3 237.0,184.5 237.8,184.6 238.5,184.8 239.2,185.0 239.9,185.2 240.6,185.4 241.4,185.6 242.1,185.7 242.8,185.9 243.5,186.1 244.2,186.3 245.0,186.4 245.7,186.6 246.4,186.8 247.1,187.0 247.8,187.1 248.6,187.3 249.3,187.5 250.0,187.6 250.7,187.8 251.4,188.0 252.2,188.1 252.9,188.3 253.6,188.5 254.3,188.6 255.0,188.8 255.8,188.9 256.5,189.1 257.2,189.3 257.9,189.4 258.6,189.6 259.4,189.7 260.1,189.9 260.8,190.0 261.5,190.2 262.2,190.4 263.0,190.5 263.7,190.7 264.4,190.8 265.1,191.0 265.8,191.1 266.6,191.3 267.3,191.4 268.0,191.6 268.7,191.7 269.4,191.8 270.2,192.0 270.9,192.1 271.6,192.3 272.3,192.4 273.0,192.6 273.8,192.7 274.5,192.8 275.2,193.0 275.9,193.1 276.6,193.3 277.4,193.4 278.1,193.5 278.8,193.7 279.5,193.8 280.2,193.9 281.0,194.1 281.7,194.2 282.4,194.4 283.1,194.5 283.8,194.6 284.6,194.7 285.3,194.9 286.0,195.0 286.7,195.1 287.4,195.3 288.2,195.4 288.9,195.5 289.6,195.7 290.3,195.8 291.0,195.9 291.8,196.0 292.5,196.2 293.2,196.3 293.9,196.4 294.6,196.5 295.4,196.7 296.1,196.8 296.8,196.9 297.5,197.0 298.2,197.1 299.0,197.3 299.7,197.4 300.4,197.5 301.1,197.6 301.8,197.7 302.6,197.8 303.3,198.0 304.0,198.1 304.7,198.2 305.4,198.3 306.2,198.4 306.9,198.5 307.6,198.7 308.3,198.8 309.0,198.9 309.8,199.0 310.5,199.1 311.2,199.2 311.9,199.3 312.6,199.4 313.4,199.5 314.1,199.7 314.8,199.8 315.5,199.9 316.2,200.0 317.0,200.1 317.7,200.2 318.4,200.3 319.1,200.4 319.8,200.5 320.6,200.6 321.3,200.7 322.0,200.8 322.7,200.9 323.4,201.0 324.2,201.1 324.9,201.2 325.6,201.3 326.3,201.4 327.0,201.5 327.8,201.6 328.5,201.7 329.2,201.8 329.9,201.9 330.6,202.0 331.4,202.1 332.1,202.2 332.8,202.3 333.5,202.4 334.2,202.5 335.0,202.6 335.7,202.7 336.4,202.8 337.1,202.9 337.8,203.0 338.6,203.1 339.3,203.2 340.0,203.3 340.7,203.4 341.4,203.5 342.2,203.6 342.9,203.7 343.6,203.8 344.3,203.9 345.0,203.9 345.8,204.0 346.5,204.1 347.2,204.2 347.9,204.3 348.6,204.4 349.4,204.5 350.1,204.6 350.8,204.7 351.5,204.8 352.2,204.8 353.0,204.9 353.7,205.0 354.4,205.1 355.1,205.2 355.8,205.3 356.6,205.4 357.3,205.4 358.0,205.5 358.7,205.6 359.4,205.7 360.2,205.8 360.9,205.9 361.6,206.0 362.3,206.0 363.0,206.1 363.8,206.2 364.5,206.3 365.2,206.4 365.9,206.5 366.6,206.5 367.4,206.6 368.1,206.7 368.8,206.8 369.5,206.9 370.2,206.9 371.0,207.0 371.7,207.1 372.4,207.2 373.1,207.3 373.8,207.3 374.6,207.4 375.3,207.5 376.0,207.6 376.7,207.6 377.4,207.7 378.2,207.8 378.9,207.9 379.6,207.9 380.3,208.0 381.0,208.1 381.8,208.2 382.5,208.3 383.2,208.3 383.9,208.4 384.6,208.5 385.4,208.5 386.1,208.6 386.8,208.7 387.5,208.8 388.2,208.8 389.0,208.9 389.7,209.0 390.4,209.1 391.1,209.1 391.8,209.2 392.6,209.3 393.3,209.3 394.0,209.4 394.7,209.5 395.4,209.6 396.2,209.6 396.9,209.7 397.6,209.8 398.3,209.8 399.0,209.9 399.8,210.0 400.5,210.0 401.2,210.1 401.9,210.2 402.6,210.3 403.4,210.3 404.1,210.4 404.8,210.5 405.5,210.5 406.2,210.6 407.0,210.7 407.7,210.7 408.4,210.8 409.1,210.9 409.8,210.9 410.6,211.0 411.3,211.0 412.0,211.1 412.7,211.2 413.4,211.2 414.2,211.3 414.9,211.4 415.6,211.4 416.3,211.5 417.0,211.6 417.8,211.6 418.5,211.7 419.2,211.8 419.9,211.8 420.6,211.9" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><line x1="420.6" y1="250.0" x2="420.6" y2="50.0" style="stroke:var(--muted);stroke-width:1.5;stroke-dasharray:5 4;fill:none"/><text x="414.6" y="240.0" font-size="14" text-anchor="end" style="fill:var(--muted)">显存满 487</text><text x="192.4" y="101.0" font-size="15" text-anchor="end" style="fill:var(--accent)">整卡 token/s</text><text x="257.2" y="215.3" font-size="15" text-anchor="start" style="fill:var(--warn)">每个用户 token/s</text>
</svg>
<figcaption>图 4　蓝线（左轴）是整张卡每秒出的 token 数，橙线（右轴）是每个用户每秒拿到的 token 数。batch 越大，总量越多，每个人越慢。</figcaption>
</figure>

表里还有一件事：**计算占用始终没到 100%**。batch 越大，算术强度越接近一个上限：多一个人，多读 131.1 MB，多算 $16.58 \times 10^{9}$ 次，比值是 $16.58 \times 10^{9} / (131.1 \times 10^{6}) \approx 127$ FLOP/B，比拐点 295 低。所以上下文有 1000 个 token 时，不管 batch 多大，decode 都是带宽说了算，而越来越多的带宽花在了读 KV cache 上。这就是 GQA、MLA 和 KV cache 量化值钱的地方：KV cache 小一半，同样的带宽就能多伺候将近一倍的人。

<details class="pause"><summary>停一下：如果每个用户的上下文从 1000 个 token 变成 4000 个，最多能同时服务几个人？</summary>

每人的 KV cache 变成 $4000 \times 131,072\ \text{B} = 524.3\ \text{MB}$。剩余显存还是 63.94 GB，$\lfloor 63.94 / 0.5243 \rfloor = 121$ 个人，只有原来的四分之一左右。上下文越长，能同时伺候的人越少。

</details>

## 第四步：静态批处理：一批走完，下一批才进来

道理清楚了：batch 越大越划算。可真实的请求不是整整齐齐一起来、一起走的，每个回答长短不一。

把规模缩小到能数格子：只有 4 个**槽**（batch 最多 4 个人），排队的有 8 个请求 A–H，各自要生成的 token 数是：

| 请求 | A | B | C | D | E | F | G | H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 要生成的 token | 7 | 2 | 3 | 8 | 2 | 6 | 4 | 3 |

每一步，每个占着槽的请求出 1 个 token（为了好数，先不算读入问题的 prefill）。

最直接的做法是**静态批处理**：A、B、C、D 组成一批，一起开始；这一批里最长的 D 要 8 步，所以要等 8 步全部结束，才换下一批 E、F、G、H，这一批最长的 F 要 6 步。

<figure class="fig">
<svg viewBox="0 0 480 230" role="img" aria-label="静态批处理的时间线">
<text x="20.0" y="26.0" font-size="16" text-anchor="start" style="fill:var(--muted)">静态批处理：一批全部结束，下一批才进来</text><text x="52.0" y="66.0" font-size="14" text-anchor="end" style="fill:var(--muted)">槽 1</text><rect x="63.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="91.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="119.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="147.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="175.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="203.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="231.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="259.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="287.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="315.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="343.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="371.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="399.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="427.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><text x="52.0" y="100.0" font-size="14" text-anchor="end" style="fill:var(--muted)">槽 2</text><rect x="63.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="91.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="119.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="147.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="175.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="203.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="231.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="259.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="287.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="315.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="343.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="371.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="399.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="427.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><text x="52.0" y="134.0" font-size="14" text-anchor="end" style="fill:var(--muted)">槽 3</text><rect x="63.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="91.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="119.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="147.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="175.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="203.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="231.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="259.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="287.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="315.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="343.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="371.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="399.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="427.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><text x="52.0" y="168.0" font-size="14" text-anchor="end" style="fill:var(--muted)">槽 4</text><rect x="63.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="91.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="119.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="147.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="175.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="203.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="231.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="259.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="287.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="315.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="343.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="371.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="399.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="427.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="63.0" y="47.0" width="194.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="71.0" y="66.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">A</text><rect x="63.0" y="81.0" width="54.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="71.0" y="100.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">B</text><rect x="63.0" y="115.0" width="82.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="71.0" y="134.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">C</text><rect x="63.0" y="149.0" width="222.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="71.0" y="168.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">D</text><rect x="287.0" y="47.0" width="54.0" height="28.0" rx="4" style="fill:var(--ok)"/><text x="295.0" y="66.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">E</text><rect x="287.0" y="81.0" width="166.0" height="28.0" rx="4" style="fill:var(--ok)"/><text x="295.0" y="100.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">F</text><rect x="287.0" y="115.0" width="110.0" height="28.0" rx="4" style="fill:var(--ok)"/><text x="295.0" y="134.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">G</text><rect x="287.0" y="149.0" width="82.0" height="28.0" rx="4" style="fill:var(--ok)"/><text x="295.0" y="168.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">H</text><text x="104.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">2</text><text x="160.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">4</text><text x="216.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">6</text><text x="272.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">8</text><text x="328.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">10</text><text x="384.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">12</text><text x="440.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">14</text><line x1="454.0" y1="40.0" x2="454.0" y2="182.0" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><text x="458.0" y="218.0" font-size="15" text-anchor="end" style="fill:var(--warn)">第 14 步全部完成</text>
</svg>
<figcaption>图 5　横轴是 decode 的步数，每一步每个槽出 1 个 token。蓝色是第一批 A–D，绿色是第二批 E–H。空着的格子就是槽在白等：B 第 2 步就说完了，它的槽要空等到第 8 步。</figcaption>
</figure>

一共 $8 + 6 = 14$ 步。4 个槽 × 14 步 = 56 个格子，真正出 token 的只有 $7 + 2 + 3 + 8 + 2 + 6 + 4 + 3 = 35$ 个，利用率 $35 / 56$ = 62.5%。B 在第 2 步就说完了，它的槽空等 6 步；E 只要 2 个 token，却要排到第 9 步才开始，第 10 步才拿到完整回答。

## 第五步：连续批处理：谁说完了，下一步就补人

换个规矩：**每一步结束时检查一遍**，谁说完了，就把它的槽交给队首的下一个请求，下一步新请求就开始生成。这叫**连续批处理**（continuous batching），最早由 Orca（Yu 等，OSDI 2022）以「按迭代调度」的名字提出：调度的单位是一步，而不是一整个请求。

照这个规矩一步步排：

- 第 1–2 步：A、B、C、D 在跑。B 第 2 步说完。
- 第 3 步：E 补进 B 的槽。C 第 3 步说完。
- 第 4 步：F 补进 C 的槽。E 第 4 步说完（它从第 3 步开始，2 个 token）。
- 第 5 步：G 补进 E 的槽。A 第 7 步说完。
- 第 8 步：H 补进 A 的槽。D、G 第 8 步说完，F 第 9 步说完，H 第 10 步说完。

<figure class="fig">
<svg viewBox="0 0 480 230" role="img" aria-label="连续批处理的时间线">
<text x="20.0" y="26.0" font-size="16" text-anchor="start" style="fill:var(--muted)">连续批处理：谁说完了，下一步就有人补进来</text><text x="52.0" y="66.0" font-size="14" text-anchor="end" style="fill:var(--muted)">槽 1</text><rect x="63.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="91.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="119.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="147.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="175.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="203.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="231.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="259.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="287.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="315.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="343.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="371.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="399.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="427.0" y="47.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><text x="52.0" y="100.0" font-size="14" text-anchor="end" style="fill:var(--muted)">槽 2</text><rect x="63.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="91.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="119.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="147.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="175.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="203.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="231.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="259.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="287.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="315.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="343.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="371.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="399.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="427.0" y="81.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><text x="52.0" y="134.0" font-size="14" text-anchor="end" style="fill:var(--muted)">槽 3</text><rect x="63.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="91.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="119.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="147.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="175.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="203.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="231.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="259.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="287.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="315.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="343.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="371.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="399.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="427.0" y="115.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><text x="52.0" y="168.0" font-size="14" text-anchor="end" style="fill:var(--muted)">槽 4</text><rect x="63.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="91.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="119.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="147.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="175.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="203.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="231.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="259.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="287.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="315.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="343.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="371.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="399.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="427.0" y="149.0" width="26.0" height="28.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1"/><rect x="63.0" y="47.0" width="194.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="71.0" y="66.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">A</text><rect x="63.0" y="81.0" width="54.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="71.0" y="100.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">B</text><rect x="63.0" y="115.0" width="82.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="71.0" y="134.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">C</text><rect x="63.0" y="149.0" width="222.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="71.0" y="168.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">D</text><rect x="119.0" y="81.0" width="54.0" height="28.0" rx="4" style="fill:var(--ok)"/><text x="127.0" y="100.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">E</text><rect x="147.0" y="115.0" width="166.0" height="28.0" rx="4" style="fill:var(--ok)"/><text x="155.0" y="134.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">F</text><rect x="175.0" y="81.0" width="110.0" height="28.0" rx="4" style="fill:var(--ok)"/><text x="183.0" y="100.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">G</text><rect x="259.0" y="47.0" width="82.0" height="28.0" rx="4" style="fill:var(--ok)"/><text x="267.0" y="66.0" font-size="15" text-anchor="start" font-weight="600" style="fill:var(--bg)">H</text><text x="104.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">2</text><text x="160.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">4</text><text x="216.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">6</text><text x="272.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">8</text><text x="328.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">10</text><text x="384.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">12</text><text x="440.0" y="198.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">14</text><line x1="342.0" y1="40.0" x2="342.0" y2="182.0" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><text x="346.0" y="218.0" font-size="15" text-anchor="start" style="fill:var(--warn)">第 10 步全部完成</text>
</svg>
<figcaption>图 6　同样 8 个请求、同样 4 个槽。B 第 2 步说完，第 3 步 E 就补进它的槽；空格子只剩最后收尾的几格。</figcaption>
</figure>

同样 8 个请求，10 步全部完成，利用率 $35 / 40$ = 87.5%。每个请求完成的平均步数也从 8.375 降到 6.375：E 第 4 步就拿到了回答，而不是第 10 步。

真实的服务里还要处理新请求的 prefill：一个刚进来的请求要先把整段问题读一遍，算出它的 KV cache。prefill 一次处理几百上千个 token，一份权重乘很多行，算术强度高，是算力说了算；如果整段一口气做完，同一步里正在 decode 的人都要等它。常见的做法是**分块 prefill**（chunked prefill）：把长问题切成几块，每一步只带一块，和大家的 decode 拼在一起算。

## 第六步：KV cache 放在哪：按最大长度预留

连续批处理让 batch 一直满着，batch 能多大，取决于显存里放得下多少份 KV cache。第三步算的是理想情况，每份正好占自己那么多。实际做到这一点并不容易。

问题出在：一个请求开始时，**不知道它最后会生成多少个 token**。早期的做法是按允许的最大长度，给每个请求预留一整段连续的显存，这样它怎么写都不会越界。

用最小的例子数格子：显存一共 36 格，每格放 1 个 token 的 K、V；每个请求最长 12 个 token。此刻有三个请求，已经写了 5、9、3 个 token。

- 按最大长度预留：每个请求占 12 格，三个占满 36 格，实际只写了 $5 + 9 + 3 = 17$ 格，其余 $36 - 17 = 19$ 格被占着没用，浪费 $19 / 36$ = 52.8%。新请求一个也进不来。

这还只是一种浪费（预留了没用上）。另外，请求结束后释放的一段段空间大小不一，新请求要的连续长度可能哪一段都放不下，这叫**外部碎片**。PagedAttention 论文（Kwon 等，SOSP 2023）实测了当时的系统：KV cache 区域里，真正存着 token 状态的只有 20.4%–38.2%。

## 第七步：PagedAttention：按页分配，用到才给

操作系统早就遇到过同样的问题，办法是**分页**：内存切成固定大小的页，程序看到的是连续的地址，实际可以散落在任何物理页上，由一张页表记录对应关系，用到一页才分配一页。

PagedAttention 把这一套搬到 KV cache 上：

1. 显存切成固定大小的**块**，每块放固定个数 token 的 K、V。我们的例子里每块 4 格。
2. 每个请求有一张**块表**，记着它的第 0、1、2…… 个逻辑块分别放在第几号物理块。
3. 请求写满一块，才再分配一块；请求结束，块还回空闲池。
4. 注意力算子按块表去各个物理块里取 K、V，不要求它们挨在一起。

同样三个请求：5 个 token 要 $\lceil 5/4 \rceil = 2$ 块，9 个要 3 块，3 个要 1 块，一共 6 块 = 24 格。占着没用的只有每个请求最后一块里的空格：$24 - 17 = 7$ 格，浪费 $7 / 24$ = 29.2%。更要紧的是还空出 3 块，可以再接新请求。

<figure class="fig">
<svg viewBox="0 0 480 200" role="img" aria-label="预留整段空间与分页分配 KV cache 的对比">
<text x="20.0" y="28.0" font-size="15" text-anchor="start" style="fill:var(--muted)">按最大长度预留（每个请求先占 12 格）</text><rect x="20.0" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="31.6" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="43.2" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="54.8" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="66.4" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="78.0" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="89.6" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="101.2" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="112.8" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="124.4" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="136.0" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="147.6" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><text x="89.6" y="82.0" font-size="14" text-anchor="middle" style="fill:var(--accent)">A：用 5，占 12</text><rect x="159.2" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="170.8" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="182.4" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="194.0" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="205.6" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="217.2" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="228.8" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="240.4" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="252.0" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="263.6" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="275.2" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="286.8" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><text x="228.8" y="82.0" font-size="14" text-anchor="middle" style="fill:var(--warn)">B：用 9，占 12</text><rect x="298.4" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--ok)"/><rect x="310.0" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--ok)"/><rect x="321.6" y="36.0" width="10.1" height="26.0" rx="2" style="fill:var(--ok)"/><rect x="333.2" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="344.8" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="356.4" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="368.0" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="379.6" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="391.2" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="402.8" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="414.4" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="426.0" y="36.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><text x="368.0" y="82.0" font-size="14" text-anchor="middle" style="fill:var(--ok)">C：用 3，占 12</text><text x="20.0" y="132.0" font-size="15" text-anchor="start" style="fill:var(--muted)">分页（每块 4 格，用到才给）</text><rect x="20.0" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="31.6" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="43.2" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="54.8" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="70.4" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="82.0" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="93.6" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="105.2" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="120.8" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="132.4" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="144.0" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="155.6" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="171.2" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="182.8" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="194.4" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="206.0" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="221.6" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="233.2" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="244.8" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="256.4" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="272.0" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--ok)"/><rect x="283.6" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--ok)"/><rect x="295.2" y="140.0" width="10.1" height="26.0" rx="2" style="fill:var(--ok)"/><rect x="306.8" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="322.4" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="334.0" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="345.6" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="357.2" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="372.8" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="384.4" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="396.0" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="407.6" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="423.2" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="434.8" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="446.4" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="458.0" y="140.0" width="10.1" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><text x="171.2" y="186.0" font-size="14" text-anchor="middle" style="fill:var(--fg)">用了 6 块</text><text x="398.0" y="186.0" font-size="14" text-anchor="middle" style="fill:var(--ok)">空出 3 块给新请求</text>
</svg>
<figcaption>图 7　一共 36 格显存，每格存 1 个 token 的 K、V。上：三个请求各占 12 格，实际只用了 17 格，空框是被占着又没用上的。下：分页以后同样三个请求只占 24 格，空框只出现在每个请求的最后一块里。</figcaption>
</figure>

<figure class="fig">
<svg viewBox="0 0 480 200" role="img" aria-label="块表把逻辑块映射到显存里不连续的物理块">
<text x="20.0" y="26.0" font-size="16" text-anchor="start" style="fill:var(--muted)">请求 B 的块表</text><text x="20.0" y="69.0" font-size="15" text-anchor="start" style="fill:var(--fg)">逻辑块 0</text><rect x="100.0" y="50.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="112.4" y="50.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="124.8" y="50.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="137.2" y="50.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><text x="159.6" y="69.0" font-size="14" text-anchor="start" style="fill:var(--muted)">token 1–4</text><text x="268.0" y="69.0" font-size="16" text-anchor="start" style="fill:var(--muted)">→</text><rect x="288.0" y="48.0" width="64.0" height="30.0" rx="4" style="fill:none;stroke:var(--line);stroke-width:1.2"/><text x="320.0" y="69.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">5</text><text x="20.0" y="113.0" font-size="15" text-anchor="start" style="fill:var(--fg)">逻辑块 1</text><rect x="100.0" y="94.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="112.4" y="94.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="124.8" y="94.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="137.2" y="94.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><text x="159.6" y="113.0" font-size="14" text-anchor="start" style="fill:var(--muted)">token 5–8</text><text x="268.0" y="113.0" font-size="16" text-anchor="start" style="fill:var(--muted)">→</text><rect x="288.0" y="92.0" width="64.0" height="30.0" rx="4" style="fill:none;stroke:var(--line);stroke-width:1.2"/><text x="320.0" y="113.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">1</text><text x="20.0" y="157.0" font-size="15" text-anchor="start" style="fill:var(--fg)">逻辑块 2</text><rect x="100.0" y="138.0" width="10.9" height="26.0" rx="2" style="fill:var(--warn)"/><rect x="112.4" y="138.0" width="10.9" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="124.8" y="138.0" width="10.9" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="137.2" y="138.0" width="10.9" height="26.0" rx="2" style="fill:none;stroke:var(--line);stroke-width:1.2"/><text x="159.6" y="157.0" font-size="14" text-anchor="start" style="fill:var(--muted)">token 9</text><text x="268.0" y="157.0" font-size="16" text-anchor="start" style="fill:var(--muted)">→</text><rect x="288.0" y="136.0" width="64.0" height="30.0" rx="4" style="fill:none;stroke:var(--line);stroke-width:1.2"/><text x="320.0" y="157.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">7</text><text x="380.0" y="26.0" font-size="16" text-anchor="start" style="fill:var(--muted)">显存</text><rect x="390.0" y="36.0" width="70.0" height="14.0" rx="2" style="fill:var(--line);fill-opacity:0.6"/><text x="384.0" y="48.0" font-size="12" text-anchor="end" style="fill:var(--muted)">0</text><rect x="390.0" y="53.0" width="70.0" height="14.0" rx="2" style="fill:var(--warn);fill-opacity:1"/><text x="384.0" y="65.0" font-size="12" text-anchor="end" style="fill:var(--muted)">1</text><rect x="390.0" y="70.0" width="70.0" height="14.0" rx="2" style="fill:var(--line);fill-opacity:0.6"/><text x="384.0" y="82.0" font-size="12" text-anchor="end" style="fill:var(--muted)">2</text><rect x="390.0" y="87.0" width="70.0" height="14.0" rx="2" style="fill:var(--line);fill-opacity:0.6"/><text x="384.0" y="99.0" font-size="12" text-anchor="end" style="fill:var(--muted)">3</text><rect x="390.0" y="104.0" width="70.0" height="14.0" rx="2" style="fill:var(--line);fill-opacity:0.6"/><text x="384.0" y="116.0" font-size="12" text-anchor="end" style="fill:var(--muted)">4</text><rect x="390.0" y="121.0" width="70.0" height="14.0" rx="2" style="fill:var(--warn);fill-opacity:1"/><text x="384.0" y="133.0" font-size="12" text-anchor="end" style="fill:var(--muted)">5</text><rect x="390.0" y="138.0" width="70.0" height="14.0" rx="2" style="fill:var(--line);fill-opacity:0.6"/><text x="384.0" y="150.0" font-size="12" text-anchor="end" style="fill:var(--muted)">6</text><rect x="390.0" y="155.0" width="70.0" height="14.0" rx="2" style="fill:var(--warn);fill-opacity:1"/><text x="384.0" y="167.0" font-size="12" text-anchor="end" style="fill:var(--muted)">7</text><rect x="390.0" y="172.0" width="70.0" height="14.0" rx="2" style="fill:var(--line);fill-opacity:0.6"/><text x="384.0" y="184.0" font-size="12" text-anchor="end" style="fill:var(--muted)">8</text>
</svg>
<figcaption>图 8　请求 B 有 9 个 token，分成 3 个逻辑块；块表记着每个逻辑块放在显存的第几号物理块（5、1、7），三块不需要挨在一起。最后一块只用了 1 格。</figcaption>
</figure>

浪费有上限：每个请求只有最后一块可能没写满，最多空「块大小 − 1」格。真实的块是 16 个 token（vLLM 默认值，2026-10 核实），Llama-3-8B 一块是 $16 \times 131,072\ \text{B} = 2\ \text{MiB}$。平均每个请求空 $(16-1)/2 = 7.5$ 格，对一个 1000 个 token 的请求是 0.75%。外部碎片也没有了：所有块一样大，任何一个空块都能给任何请求用。

论文报告，这样做让 vLLM 在延迟相同的情况下，吞吐比 FasterTransformer、Orca 高 2–4 倍，序列越长、模型越大，提升越明显。省下的显存变成了更大的 batch，而第三步已经算过，batch 越大吞吐越高。

块表还带来一个额外的好处：两个请求的块表可以指向同一个物理块。这就是下一步的基础。

## 第八步：prefix caching：相同的开头只算一次、只存一份

很多请求的开头一模一样：同一个应用的系统提示、同一份长文档、多轮对话里之前的每一轮。设我们例子里每个用户的 1000 个 token 中，前 800 个是所有人共用的系统提示，后 200 个是各自的问题。

前 800 个 token 一样，它们的 K、V 也一样吗？一样。第 $i$ 个位置的 K、V 只取决于第 1 到第 $i$ 个 token（模型只往前看，位置编码也只看位置号），开头完全相同，算出来就完全相同。

所以只要认出「这一块和以前某一块一样」，就能直接复用。办法是给每个**写满的块**算一个哈希：

$$
h_j = \operatorname{hash}\left(h_{j-1},\ \text{第 } j \text{ 块的 } 16 \text{ 个 token}\right)
$$

把前一块的哈希也算进去，是因为同样 16 个 token，前面的内容不同，K、V 就不同；带上 $h_{j-1}$，哈希相同就意味着从开头到这一块全部相同。800 个 token 正好是 $800 / 16 = 50$ 块。新请求进来，从第一块开始逐块算哈希、查表，前 50 块都能查到，就让它的块表直接指向已有的物理块，从第 51 块开始才自己算。

<figure class="fig">
<svg viewBox="0 0 480 196" role="img" aria-label="两个请求共享前缀的 KV 块">
<text x="20.0" y="26.0" font-size="16" text-anchor="start" style="fill:var(--muted)">两个用户，同一段系统提示</text><text x="20.0" y="69.0" font-size="15" text-anchor="start" style="fill:var(--fg)">用户 1</text><rect x="80.0" y="50.0" width="48.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><rect x="132.0" y="50.0" width="48.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><rect x="184.0" y="50.0" width="48.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><text x="240.0" y="69.0" font-size="16" text-anchor="start" style="fill:var(--muted)">…</text><rect x="258.0" y="50.0" width="48.0" height="26.0" rx="3" style="fill:var(--warn);fill-opacity:0.85"/><rect x="310.0" y="50.0" width="48.0" height="26.0" rx="3" style="fill:var(--warn);fill-opacity:0.85"/><text x="20.0" y="169.0" font-size="15" text-anchor="start" style="fill:var(--fg)">用户 2</text><rect x="80.0" y="150.0" width="48.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><rect x="132.0" y="150.0" width="48.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><rect x="184.0" y="150.0" width="48.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><text x="240.0" y="169.0" font-size="16" text-anchor="start" style="fill:var(--muted)">…</text><rect x="258.0" y="150.0" width="48.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><rect x="310.0" y="150.0" width="48.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><line x1="104.0" y1="80.0" x2="104.0" y2="146.0" style="stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 3;fill:none"/><line x1="156.0" y1="80.0" x2="156.0" y2="146.0" style="stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 3;fill:none"/><line x1="208.0" y1="80.0" x2="208.0" y2="146.0" style="stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 3;fill:none"/><text x="236.0" y="118.0" font-size="14" text-anchor="start" style="fill:var(--accent)">前 50 块哈希相同 → 同一份物理块</text><text x="258.0" y="44.0" font-size="14" text-anchor="start" style="fill:var(--muted)">各自的问题</text>
</svg>
<figcaption>图 9　蓝色是 800 个 token 的系统提示（50 块），两个用户一模一样，算一次、存一份；橙色和绿色是各自的问题，各存各的。</figcaption>
</figure>

省了两样东西。

**显存。** 共用部分只存一份：$800 \times 131,072\ \text{B} = 104.9\ \text{MB}$。每个人只需存自己的 200 个 token：$26.2$ MB。剩余显存能放的人数从 487 变成：

$$
\left\lfloor \frac{63.94\ \text{GB} - 104.9\ \text{MB}}{26.2\ \text{MB}} \right\rfloor = 2,435
$$

（这只是放得下的人数；每一步还是要把每个人用到的 KV cache 读一遍，速度另算。）

**首个 token 的等待时间。** 不复用时，新请求要 prefill 全部 1000 个 token：$2 \times 8.03 \times 10^{9} \times 1000$ 次运算再加注意力，约 16.5 ms，算力说了算。复用后只 prefill 自己的 200 个：运算只要 3.3 ms，但权重总得读一遍，4.8 ms，所以是 4.8 ms。等待时间少了 70.7%。

vLLM 默认打开 prefix caching，用的正是这种逐块哈希（2026-10 核实）。SGLang 的 RadixAttention 把所有缓存过的前缀组织成一棵基数树，按 token 逐段匹配，效果相同。

<details class="pause"><summary>停一下：有人把「当前时间：2026-10-22 14:03:27」写在系统提示的第一行。prefix cache 还能命中吗？</summary>

几乎不能。时间每秒都在变，第一块的 token 就和以前不同，$h_1$ 不同；而 $h_2$ 要用到 $h_1$，所以 $h_2$ 也不同，后面每一块的哈希都跟着变。命中只能从开头连续地命中，第一块不同，800 个 token 全部要重算。会变的内容要放在提示的最后面。

</details>

## 第九步：投机解码：小模型先猜，大模型一次验证

回到第一步：只有一个用户时，算力 99% 以上闲着。有没有办法把闲着的算力换成速度？

**一次验证几个 token 和验证一个，时间几乎一样。** batch 1 时，让大模型同时处理 5 个位置（像 prefill 一样），读的还是同一份权重和同一份 KV cache，运算变成 5 倍：$5 \times$ 原来的运算约 0.084 ms，仍然远小于读数据的 4.83 ms。所以验证 5 个位置也是 4.83 ms。

于是有了**投机解码**（speculative decoding，Leviathan 等，ICML 2023）：

1. 用一个小得多的模型（草稿模型）快速地一个一个猜出 $\gamma$ 个 token（$\gamma$ 读作 gamma，是猜测长度）。
2. 大模型一次前向，同时算出这 $\gamma$ 个位置、再加后面一个位置上它自己的概率分布。
3. 从第一个猜测开始逐个检查，按一个规则决定接受还是拒绝；遇到第一个被拒的就停，后面的猜测全部作废。
4. 大模型在停下的位置自己给出一个 token。所以每一轮至少得到 1 个 token，最多 $\gamma + 1$ 个。

### 接受规则：不改变大模型的输出

规则要保证：最后输出的 token，概率分布和大模型自己一个一个生成时**完全一样**。

用一个能手算的例子：下一个 token 只有三个候选「饭」「粥」「面」。大模型的概率 $p$ 是 $(0.6,\ 0.3,\ 0.1)$，小模型的概率 $q$ 是 $(0.5,\ 0.2,\ 0.3)$。

<figure class="fig">
<svg viewBox="0 0 480 266" role="img" aria-label="大模型与小模型的分布及其重叠部分">
<text x="20.0" y="26.0" font-size="16" text-anchor="start" style="fill:var(--muted)">大模型 p（蓝框）与小模型 q（橙框）</text><rect x="70.0" y="85.0" width="90.0" height="115.0" rx="2" style="fill:var(--ok);fill-opacity:0.35"/><rect x="70.0" y="62.0" width="42.0" height="138.0" rx="2" style="fill:none;stroke:var(--accent);stroke-width:2.5"/><rect x="118.0" y="85.0" width="42.0" height="115.0" rx="2" style="fill:none;stroke:var(--warn);stroke-width:2.5"/><text x="91.0" y="54.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">0.6</text><text x="139.0" y="77.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">0.5</text><text x="115.0" y="222.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">饭</text><rect x="200.0" y="154.0" width="90.0" height="46.0" rx="2" style="fill:var(--ok);fill-opacity:0.35"/><rect x="200.0" y="131.0" width="42.0" height="69.0" rx="2" style="fill:none;stroke:var(--accent);stroke-width:2.5"/><rect x="248.0" y="154.0" width="42.0" height="46.0" rx="2" style="fill:none;stroke:var(--warn);stroke-width:2.5"/><text x="221.0" y="123.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">0.3</text><text x="269.0" y="146.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">0.2</text><text x="245.0" y="222.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">粥</text><rect x="330.0" y="177.0" width="90.0" height="23.0" rx="2" style="fill:var(--ok);fill-opacity:0.35"/><rect x="330.0" y="177.0" width="42.0" height="23.0" rx="2" style="fill:none;stroke:var(--accent);stroke-width:2.5"/><rect x="378.0" y="131.0" width="42.0" height="69.0" rx="2" style="fill:none;stroke:var(--warn);stroke-width:2.5"/><text x="351.0" y="169.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">0.1</text><text x="399.0" y="123.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">0.3</text><text x="375.0" y="222.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">面</text><line x1="60.0" y1="200.0" x2="460.0" y2="200.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="20.0" y="252.0" font-size="15" text-anchor="start" style="fill:var(--ok)">绿色 = 两者取小 = 0.5 + 0.2 + 0.1 = 0.8 = 接受率 α</text>
</svg>
<figcaption>图 10　三个候选 token 上的两个分布。每个 token 取两者中较小的那一截（绿色）加起来就是接受率 α。</figcaption>
</figure>

规则是：小模型抽到 token $x$，以概率

$$
\min\left(1,\ \frac{p(x)}{q(x)}\right)
$$

接受它。逐个看：

- 抽到「饭」（概率 0.5）：$p/q = 0.6/0.5 > 1$，必定接受。
- 抽到「粥」（概率 0.2）：$p/q = 0.3/0.2 > 1$，必定接受。
- 抽到「面」（概率 0.3）：$p/q = 0.1/0.3 = 1/3$，只有三分之一的机会接受。

接受的总概率：

$$
\alpha = 0.5 \times 1 + 0.2 \times 1 + 0.3 \times \frac{1}{3} = 0.5 + 0.2 + 0.1 = 0.8
$$

这正好是图 10 里绿色部分的总和：每个 token 上 $p$ 和 $q$ 取小的那个加起来，$\alpha = \sum_x \min\left(p(x), q(x)\right)$。两个模型越像，$\alpha$ 越大。

被拒绝时（概率 $1 - 0.8 = 0.2$），大模型从「$p$ 比 $q$ 多出来的部分」里重新抽：$p - q = (0.1,\ 0.1,\ -0.2)$，负的记成 0，得到 $(0.1,\ 0.1,\ 0)$，除以总和 0.2 归一化成 $(0.5,\ 0.5,\ 0)$。

验证最终输出「饭」的概率：小模型抽到「饭」并接受，$0.5 \times 1 = 0.5$；或者被拒后重抽到「饭」，$0.2 \times 0.5 = 0.1$；合计 $0.6$，正是 $p(\text{饭})$。「粥」：$0.2 \times 1 + 0.2 \times 0.5 = 0.3$。「面」：$0.3 \times \frac{1}{3} + 0.2 \times 0 = 0.1$。三个都和 $p$ 一样。所以投机解码只改变速度，不改变大模型的输出分布。

### 每一轮期望得到几个 token

设每个猜测被接受的概率都是 $\alpha$，彼此独立（这是论文分析时的简化）。以 $\gamma = 4$、$\alpha = 0.8$ 为例，一轮有五种结局：

<figure class="fig">
<svg viewBox="0 0 480 240" role="img" aria-label="投机解码一轮可能出现的五种结果">
<text x="20.0" y="26.0" font-size="16" text-anchor="start" style="fill:var(--muted)">猜 γ = 4 个，每个独立地以 α = 0.8 被接受</text><rect x="30.0" y="44.0" width="34.0" height="26.0" rx="3" style="fill:var(--warn);fill-opacity:0.85"/><text x="47.0" y="63.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✗</text><rect x="70.0" y="44.0" width="34.0" height="26.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="110.0" y="44.0" width="34.0" height="26.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="150.0" y="44.0" width="34.0" height="26.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="198.0" y="44.0" width="34.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><text x="215.0" y="63.0" font-size="14" text-anchor="middle" font-weight="700" style="fill:var(--bg)">+1</text><text x="240.0" y="63.0" font-size="14" text-anchor="start" style="fill:var(--muted)">概率 0.2</text><text x="345.0" y="63.0" font-size="14" text-anchor="start" style="fill:var(--fg)">得到 1 个 token</text><rect x="30.0" y="82.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="47.0" y="101.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="70.0" y="82.0" width="34.0" height="26.0" rx="3" style="fill:var(--warn);fill-opacity:0.85"/><text x="87.0" y="101.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✗</text><rect x="110.0" y="82.0" width="34.0" height="26.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="150.0" y="82.0" width="34.0" height="26.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="198.0" y="82.0" width="34.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><text x="215.0" y="101.0" font-size="14" text-anchor="middle" font-weight="700" style="fill:var(--bg)">+1</text><text x="240.0" y="101.0" font-size="14" text-anchor="start" style="fill:var(--muted)">概率 0.16</text><text x="345.0" y="101.0" font-size="14" text-anchor="start" style="fill:var(--fg)">得到 2 个 token</text><rect x="30.0" y="120.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="47.0" y="139.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="70.0" y="120.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="87.0" y="139.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="110.0" y="120.0" width="34.0" height="26.0" rx="3" style="fill:var(--warn);fill-opacity:0.85"/><text x="127.0" y="139.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✗</text><rect x="150.0" y="120.0" width="34.0" height="26.0" rx="3" style="fill:none;stroke:var(--line);stroke-width:1.2"/><rect x="198.0" y="120.0" width="34.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><text x="215.0" y="139.0" font-size="14" text-anchor="middle" font-weight="700" style="fill:var(--bg)">+1</text><text x="240.0" y="139.0" font-size="14" text-anchor="start" style="fill:var(--muted)">概率 0.128</text><text x="345.0" y="139.0" font-size="14" text-anchor="start" style="fill:var(--fg)">得到 3 个 token</text><rect x="30.0" y="158.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="47.0" y="177.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="70.0" y="158.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="87.0" y="177.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="110.0" y="158.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="127.0" y="177.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="150.0" y="158.0" width="34.0" height="26.0" rx="3" style="fill:var(--warn);fill-opacity:0.85"/><text x="167.0" y="177.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✗</text><rect x="198.0" y="158.0" width="34.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><text x="215.0" y="177.0" font-size="14" text-anchor="middle" font-weight="700" style="fill:var(--bg)">+1</text><text x="240.0" y="177.0" font-size="14" text-anchor="start" style="fill:var(--muted)">概率 0.1024</text><text x="345.0" y="177.0" font-size="14" text-anchor="start" style="fill:var(--fg)">得到 4 个 token</text><rect x="30.0" y="196.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="47.0" y="215.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="70.0" y="196.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="87.0" y="215.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="110.0" y="196.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="127.0" y="215.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="150.0" y="196.0" width="34.0" height="26.0" rx="3" style="fill:var(--ok);fill-opacity:0.85"/><text x="167.0" y="215.0" font-size="15" text-anchor="middle" font-weight="700" style="fill:var(--bg)">✓</text><rect x="198.0" y="196.0" width="34.0" height="26.0" rx="3" style="fill:var(--accent);fill-opacity:0.85"/><text x="215.0" y="215.0" font-size="14" text-anchor="middle" font-weight="700" style="fill:var(--bg)">+1</text><text x="240.0" y="215.0" font-size="14" text-anchor="start" style="fill:var(--muted)">概率 0.4096</text><text x="345.0" y="215.0" font-size="14" text-anchor="start" style="fill:var(--fg)">得到 5 个 token</text>
</svg>
<figcaption>图 11　绿色是被接受的猜测，橙色是第一个被拒的，之后的猜测全部作废；蓝色「+1」是大模型这一轮自己给出的那个 token（被拒时是修正的，全接受时是多送的）。</figcaption>
</figure>

| 被接受的猜测个数 | 发生的概率 | 这一轮得到的 token |
| --- | --- | --- |
| 0（第 1 个就被拒） | $1 - 0.8 = 0.2$ | 1 |
| 1 | $0.8 \times 0.2 = 0.16$ | 2 |
| 2 | $0.8^2 \times 0.2 = 0.128$ | 3 |
| 3 | $0.8^3 \times 0.2 = 0.1024$ | 4 |
| 4（全部接受） | $0.8^4 = 0.4096$ | 5 |

五个概率加起来是 1。期望得到的 token 数是「概率 × 个数」相加：

$$
0.2 \times 1 + 0.16 \times 2 + 0.128 \times 3 + 0.1024 \times 4 + 0.4096 \times 5
$$

$$
= 0.2 + 0.32 + 0.384 + 0.4096 + 2.048 = 3.3616
$$

换一种数法能得到一般公式。一轮得到的 token 数 = 1（大模型自己给的那个）+ 被接受的猜测个数。第 $i$ 个猜测被接受，要求前 $i$ 个全部接受，概率是 $\alpha^i$。所以期望是：

$$
E = 1 + \alpha + \alpha^2 + \cdots + \alpha^{\gamma}
$$

代入检查：$1 + 0.8 + 0.64 + 0.512 + 0.4096 = 3.3616$，和上面一样。

这是一个等比数列求和。记它为 $E$，两边乘 $\alpha$：

$$
\alpha E = \alpha + \alpha^2 + \cdots + \alpha^{\gamma + 1}
$$

用 $E$ 减去 $\alpha E$，中间的项两两抵消，只剩第一项 1 和最后一项 $\alpha^{\gamma+1}$：

$$
E - \alpha E = 1 - \alpha^{\gamma + 1}
$$

左边提出 $E$，再两边除以 $1 - \alpha$：

$$
E = \frac{1 - \alpha^{\gamma + 1}}{1 - \alpha}
$$

代入：$(1 - 0.8^5) / (1 - 0.8) = (1 - 0.32768) / 0.2 = 3.3616$。

### 加速多少

一轮的成本：小模型跑 $\gamma$ 次，大模型跑 1 次。设小模型跑一次的时间是大模型的 $c$ 倍（论文实验里 $c$ 都小于 0.05），一轮的时间就是大模型一步的 $\gamma c + 1$ 倍。不用投机解码时，大模型一步出 1 个 token，所以：

$$
\text{加速比} = \frac{1 - \alpha^{\gamma + 1}}{(1 - \alpha)(\gamma c + 1)}
$$

代入 $\alpha = 0.8$、$\gamma = 4$、$c = 0.05$：

$$
\frac{3.3616}{4 \times 0.05 + 1} = \frac{3.3616}{1.2} = 2.80
$$

<figure class="fig">
<svg viewBox="0 0 480 280" role="img" aria-label="期望长度与加速比随猜测长度的变化">
<line x1="60.0" y1="230.0" x2="440.0" y2="230.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="60.0" y1="230.0" x2="60.0" y2="40.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="60.0" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0</text><text x="123.3" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2</text><text x="186.7" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">4</text><text x="250.0" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">6</text><text x="313.3" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">8</text><text x="376.7" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">10</text><text x="440.0" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">12</text><text x="54.0" y="235.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0</text><text x="54.0" y="197.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1</text><text x="54.0" y="159.0" font-size="14" text-anchor="end" style="fill:var(--muted)">2</text><text x="54.0" y="121.0" font-size="14" text-anchor="end" style="fill:var(--muted)">3</text><text x="54.0" y="83.0" font-size="14" text-anchor="end" style="fill:var(--muted)">4</text><text x="54.0" y="45.0" font-size="14" text-anchor="end" style="fill:var(--muted)">5</text><line x1="60.0" y1="192.0" x2="440.0" y2="192.0" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:4 3;fill:none"/><text x="440.0" y="270.0" font-size="15" text-anchor="end" style="fill:var(--muted)">猜测长度 γ</text><polyline points="60.0,192.0 91.7,161.6 123.3,137.3 155.0,117.8 186.7,102.3 218.3,89.8 250.0,79.8 281.7,71.9 313.3,65.5 345.0,60.4 376.7,56.3 408.3,53.1 440.0,50.4" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><polyline points="60.0,192.0 91.7,164.9 123.3,145.7 155.0,132.5 186.7,123.5 218.3,117.8 250.0,114.5 281.7,112.9 313.3,112.5 345.0,113.0 376.7,114.2 408.3,115.8 440.0,117.8" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><text x="313.3" y="51.5" font-size="14" text-anchor="middle" style="fill:var(--accent)">每轮期望得到的 token</text><text x="360.8" y="135.6" font-size="14" text-anchor="middle" style="fill:var(--warn)">加速比（c = 0.05）</text><circle cx="186.7" cy="123.5" r="5" style="fill:var(--warn)"/><text x="186.7" y="111.5" font-size="14" text-anchor="middle" style="fill:var(--warn)">2.80</text>
</svg>
<figcaption>图 12　α = 0.8。蓝线是每轮期望得到的 token 数，越猜越多但越来越平；橙线再扣掉小模型的成本，在 γ = 8 附近最高，之后反而下降。</figcaption>
</figure>

猜得越多，期望 token 增长越慢（第 $i$ 个猜测要以 $\alpha^i$ 的概率才用得上），小模型的成本却是一个一个线性加上去的，所以 $\gamma$ 有一个最好的值：这里是 $\gamma = 8$，加速 3.09 倍。论文在 T5-XXL 上实测，输出不变，延迟降到原来的二分之一到三分之一。

<details class="pause"><summary>停一下：如果小模型和大模型完全一样，<i>α</i> 是多少？这时投机解码还有意义吗？</summary>

$p = q$ 时每个 token 上取小就是它自己，$\alpha = \sum_x p(x) = 1$，每个猜测都被接受，一轮得到 $\gamma + 1$ 个 token。但小模型的成本也和大模型一样，$c = 1$，加速比是 $(\gamma + 1)/(\gamma + 1) = 1$，白忙一场。投机解码要的是一个又小（$c$ 小）又像（$\alpha$ 大）的草稿模型。

</details>

### batch 大了以后

投机解码靠的是「验证 5 个位置和验证 1 个一样快」，前提是算力闲着。batch 大了，算力不再闲。以第十步会用到的 batch 388 为例：普通一步 20.0 ms；验证时每人算 5 个位置，运算变成 5 倍，一步变成 32.5 ms，已经是算力说了算；再加上小模型猜 4 次，一轮 36.5 ms。每人每轮期望得到 3.3616 个 token，加速比只剩 $(3.3616 \times 20.0) / 36.5 = 1.84$，比 batch 1 时的 2.80 小了不少；batch 再大、上下文再短，还可能比不用更慢。所以投机解码最适合用户少、要求每个人都快的场景。

## 第十步：吞吐与延迟，选一个点

回到第三步的表。衡量推理服务常用两个数：

- **吞吐**：整张卡每秒出多少个 token，决定一张卡能服务多少人、每个 token 的成本。
- **延迟**：每个用户感受到的速度。分成两段：从发出请求到看到第一个 token 的时间（TTFT，主要是排队加 prefill），以及之后每个 token 之间的间隔（TPOT，就是 decode 一步的时间）。

表里两者是反着走的：batch 从 1 加到 487，吞吐从 207 涨到 20,421 token/s，每个用户的速度从 206.9 降到 41.9 token/s。

所以要先定延迟的要求，再在要求之内把 batch 开到最大。比如要求每个用户至少 50 token/s，也就是一步不超过 $1 / 50 = 20$ ms：

$$
\frac{16.06\ \text{GB} + B \times 0.1311\ \text{GB}}{3.35\ \text{TB/s}} \le 20\ \text{ms}
$$

左右两边乘 3.35 TB/s，右边是 $3.35 \times 10^{12} \times 0.02 = 67.0\ \text{GB}$：

$$
16.06 + 0.1311\,B \le 67.0 \quad \Rightarrow \quad B \le \frac{67.0 - 16.06}{0.1311} \approx 388
$$

batch 取 388，一步 19.98 ms，每人 50.1 token/s，整卡 19,424 token/s。和把显存塞满（487 人、20,421 token/s）相比，吞吐只少了约 5%，每个人却快了约 20%。

真实的服务就是在调这几个旋钮：同时跑的请求上限、每一步最多处理多少个 token（决定 prefill 切多大块）、要不要开投机解码。没有一组对所有场景都最好的设置：聊天产品更在乎每个人的延迟，离线批量处理（比如给一百万条评论打标签）只在乎总吞吐，可以把 batch 开到最大。

## 三个常用的推理引擎（2026-10 核实）

- **vLLM**：PagedAttention 论文的作者团队开源的引擎，生态最广，PyPI 最新版本 0.32.0（2026-10-18 发布），默认块大小 16、默认开启 prefix caching。
- **SGLang**：以 RadixAttention 自动复用前缀出名，适合多轮对话、Agent 这类前缀重复多的负载，PyPI 最新版本 0.5.22（2026-10-16 发布）。
- **TensorRT-LLM**：NVIDIA 官方的推理库，只跑 NVIDIA GPU；新版文档写明旧的 TensorRT 引擎后端已移除，PyTorch 成为唯一的执行后端（1.3.0 预发布文档），PyPI 上的正式版是 1.2.1（2026-04-20 发布）。

三者都实现了连续批处理、分页 KV cache、前缀复用和投机解码，差别主要在调度策略、对新模型和新硬件的支持速度，以及部署方式。

## 实验里讲了什么

1. **屋顶线与 batch。** H100 跑 Llama-3-8B，拖 batch、上下文长度、权重精度，看一步读多少字节、多少时间、计算占用多少，整卡吞吐和每人速度两条曲线；设一个每人速度的下限，看 batch 最大能开多少。
2. **静态 vs 连续批处理。** 文中的 8 个请求（也可以随机生成更多），两种调度的时间线、总步数、槽利用率、平均完成步数。
3. **KV cache：预留 vs 分页。** 一段显存里不断来请求，按最大长度预留和按块分配各能放下几个、浪费多少；改块大小看浪费怎么变。
4. **prefix caching。** 改共用前缀长度、各自部分长度、用户数，看命中的块数、省下的显存和 prefill 时间；把一个会变的时间戳放在开头或结尾，看命中率怎么变。
5. **投机解码。** 拖 $\alpha$、$\gamma$、$c$，公式和蒙特卡洛模拟一起算期望长度与加速比；用「饭 / 粥 / 面」的例子抽两万次，验证接受规则不改变输出分布。

## 和前后两讲的关系

上一讲的量化让每个参数占的字节变少；这一讲让很多人共用一次读取，把 decode 从「带宽说了算、算力闲着」推向两者都用上。两讲都建立在硬件讲的「速度上限 ≈ 带宽 ÷ 要读的字节」上，KV cache 的大小来自 KV Cache 一讲和多头讲的 GQA。下一讲的 MoE 会让事情更复杂：batch 里不同 token 选不同的专家，batch 一大，要读的权重就不再是同一份。

## 延伸阅读

- Woosuk Kwon et al., *Efficient Memory Management for Large Language Model Serving with PagedAttention* (SOSP 2023)
- Gyeong-In Yu et al., *Orca: A Distributed Serving System for Transformer-Based Generative Models* (OSDI 2022)
- Yaniv Leviathan, Matan Kalman, Yossi Matias, *Fast Inference from Transformers via Speculative Decoding* (ICML 2023)
- Lianmin Zheng et al., *SGLang: Efficient Execution of Structured Language Model Programs* (NeurIPS 2024)，RadixAttention
- vLLM 文档：`CacheConfig`（`block_size`、`enable_prefix_caching`）
- NVIDIA H100 Tensor Core GPU 规格表
