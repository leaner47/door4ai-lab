---
title: "LoRA 为什么省参数：微调只学一个低秩修正"
description: "先算一笔账：全量微调 Llama-3-8B 连权重带优化器状态要 128 GB 显存。LoRA 把权重冻住，只学一个秩 r 的修正 ΔW = B·A，可训练参数从 d × k 降到 r × (d + k)。在浏览器里真实微调一个小网络，看微调的改动为什么本来就近似低秩、r = 1 能做到什么、合并与切换怎么做，再算 Llama-3-8B 各层投影加 LoRA 的参数量。六个可交互实验。"
pubDate: 2026-10-17
tags: ["训练", "微调", "LoRA", "低秩", "QLoRA"]
lab: /labs/lora/
series: ai-mastery
order: 40
---

## 一句话版本

微调不是重新训练，而是在预训练好的权重上做一点修改。LoRA 的观察是：这一点修改本身就近似低秩，所以不必动整个矩阵，只学两个瘦长的小矩阵：

<p class="formula"><i>W′</i> = <i>W</i> + Δ<i>W</i> = <i>W</i> + <i>B·A</i>　　<i>B</i>：<i>d</i> × <i>r</i>　<i>A</i>：<i>r</i> × <i>k</i>　<i>r</i> ≪ <i>d</i>, <i>k</i></p>

<i>W</i> 冻住不动，可训练参数从 <i>d</i> × <i>k</i> 变成 <i>r</i> × (<i>d</i> + <i>k</i>)。<i>d</i> = <i>k</i> = 4096、<i>r</i> = 8 时，是 16.8 M 对 65 536，不到 0.4%。训完还能把 <i>B·A</i> 加回 <i>W</i>，推理时和原模型一样快。

## 预训练之后还有一步：微调

预训练那一讲说的训练，是用海量文本从零把一个模型训出来。它花的是上万张卡、几个月。但预训练好的模型只会「接着写」，要让它按指令回答、说某个领域的行话、输出固定格式，还要在小得多的数据上再训一会儿，这叫微调（fine-tuning）。

最直接的做法是全量微调：所有参数都参与梯度下降。问题是显存。按混合精度 + Adam 的常规记法，每个可训练参数要存 bf16 权重（2 B）、bf16 梯度（2 B）、fp32 主权重（4 B）和 Adam 的两个状态（各 4 B），一共 16 B。Llama-3-8B 有 8.03 B 参数：

<p class="formula">8.03 × 10<sup>9</sup> × 16 B ≈ 128.5 GB</p>

这还没算激活值。一张 80 GB 的 H100 放不下，得多卡切分。而真正要「学」的东西往往很少，几千条指令数据而已。为几千条数据搬动 80 亿个参数、存三份状态，不成比例。

## LoRA：冻住 W，只学一个修正

Transformer 的每一层里，q、k、v、o 四个投影和 MLP 的三个矩阵，都是「输入向量乘一个矩阵」。LoRA（Low-Rank Adaptation，Hu 等，2021）对其中要微调的矩阵这样做：

<figure class="clip"><video src="/videos/lora/LowRankUpdate.webm" poster="/videos/lora/LowRankUpdate.png" controls loop muted playsinline preload="metadata"></video></figure>

原来的 <i>W</i>（<i>d</i> × <i>k</i>）一个数都不动。旁边新加两个矩阵：<i>A</i> 是 <i>r</i> × <i>k</i>，<i>B</i> 是 <i>d</i> × <i>r</i>，前向时输出变成 <i>W x</i> + <i>B A x</i>。<i>B·A</i> 乘出来正好是 <i>d</i> × <i>k</i>，和 <i>W</i> 同形，可以看成叠在 <i>W</i> 上的修正量 Δ<i>W</i>。训练只更新 <i>A</i> 和 <i>B</i>。

参数怎么算：<i>A</i> 有 <i>r</i> × <i>k</i> 个数，<i>B</i> 有 <i>d</i> × <i>r</i> 个，合计 <i>r</i> × (<i>d</i> + <i>k</i>)。<i>r</i> 是「秩」，通常取 4 到 64，比 <i>d</i>、<i>k</i>（几千到上万）小两三个数量级。

两个工程细节：<i>A</i> 用随机高斯初始化，<i>B</i> 初始化为全零，所以训练一开始 Δ<i>W</i> = 0，模型和预训练时一模一样，再从那里慢慢偏离；修正项还会乘一个常数 <i>α</i>/<i>r</i>，调它和调学习率差不多。

## 秩是什么：矩阵真正的自由度

一列数 <i>u</i>（<i>d</i> 个）乘一行数 <i>v</i>（<i>k</i> 个），得到一个 <i>d</i> × <i>k</i> 的矩阵，第 <i>i</i> 行第 <i>j</i> 列是 <i>u<sub>i</sub> v<sub>j</sub></i>。它有 <i>d</i> × <i>k</i> 个格子，但每一行都是同一行 <i>v</i> 的倍数，真正的自由度只有 <i>d</i> + <i>k</i>。这叫秩 1。把 <i>r</i> 个这样的外积叠起来，就是秩 <i>r</i>：

<figure class="clip"><video src="/videos/lora/RankIntuition.webm" poster="/videos/lora/RankIntuition.png" controls loop muted playsinline preload="metadata"></video></figure>

<i>B·A</i> 正是这么一个东西：<i>B</i> 的第 <i>t</i> 列乘 <i>A</i> 的第 <i>t</i> 行是一个秩 1 矩阵，<i>r</i> 个加起来。所以「LoRA 只学一个秩不超过 <i>r</i> 的 Δ<i>W</i>」和「LoRA 只有 <i>r</i> × (<i>d</i> + <i>k</i>) 个参数」是同一句话。

## 为什么低秩就够

这是 LoRA 成立的关键。全量微调时没有人限制 Δ<i>W</i> 的秩，它可以是任何 <i>d</i> × <i>k</i> 矩阵。可实际上微调改的东西很有限：任务数据只覆盖模型见过的东西的一小角，参数要往哪里动，是由这一小角数据决定的。LoRA 论文把这叫「低内在秩」（low intrinsic rank），并在 GPT-3 175B 上做了实验：只给注意力的 <i>W<sub>q</sub></i>、<i>W<sub>v</sub></i> 加 LoRA，<i>r</i> = 1 在 WikiSQL 上 73.4%，<i>r</i> = 64 是 73.5%；MultiNLI 上 91.3% 对 91.4%。秩 1 已经够了。他们还把 <i>r</i> = 8 和 <i>r</i> = 64 学到的 Δ<i>W</i> 做 SVD 比较，最重要的前几个方向高度重合，多出来的秩学的大多是噪声。

实验 02 在一个小网络上重复这件事：先在任务 A 上训好，再全量微调到任务 B，把中间一层 32 × 32 的 Δ<i>W</i> 做 SVD。前 4 个奇异值就占了 93% 的能量；同样尺寸的随机矩阵要前 17 个才到 90%。微调的改动确实比「随便一个矩阵」规整得多。

## 用的时候：合并，或者切换

<i>B·A</i> 是线性的，这带来两个好处。

**合并。** 训完算一次 <i>W′</i> = <i>W</i> + <i>B·A</i>，存成一个和原来同形的矩阵，推理时就是一个普通模型，没有额外的矩阵乘法，没有额外延迟。实验 04 里合并前后的输出只差 10<sup>−16</sup> 量级的浮点误差。

**切换。** 不合并时，底座 <i>W</i> 只放一份，每个任务各带一对小小的 <i>A</i>、<i>B</i>。Llama-3-8B 的 q、k、v、o 投影加 <i>r</i> = 16 的 LoRA，一整套只有 13.6 M 参数，bf16 存下来 27 MB；全量微调出来的模型每个 16 GB。一台机器载一个底座、挂几十个 LoRA，按请求切换，是现在多租户微调服务的标准做法。

## QLoRA：底座也压一压

LoRA 把可训练部分压到百分之一以下之后，显存的大头变成了只读的底座：8B 模型 bf16 要 16 GB。QLoRA（Dettmers 等，2023）把冻结的底座量化成 4 bit 存（每参数 0.5 B，约 4 GB），算的时候临时反量化，LoRA 部分照旧用 bf16 训练。这样一张 24 GB 的消费级显卡就能微调 8B 模型，论文里用一张 48 GB 的卡微调了 65B。

这和 KV Cache 那一讲是同一个思路的两面：量化压的是每个数的位宽，低秩压的是数的个数。MLA 用低秩潜向量代替完整的 K、V，是在推理时少存数；LoRA 用低秩修正代替完整的 Δ<i>W</i>，是在训练时少学数。

## 实验里讲了什么

0. **矩阵的秩**：拖 <i>r</i>，看一个 16 × 16 矩阵由 <i>r</i> 个外积叠成，数值秩由页内 SVD 算出。
1. **参数计数器**：拖 <i>d</i>、<i>k</i>、<i>r</i>，看全量 <i>d</i> × <i>k</i> 与 LoRA <i>r</i> × (<i>d</i> + <i>k</i>) 的参数量、占比和显存。
2. **真实的 ΔW**：小网络先预训练再全量微调，对 Δ<i>W</i> 做 SVD，前 4 个奇异值占 93% 能量，随机矩阵远远不到。
3. **全量 vs LoRA**：同一个底座适应任务 B，<i>r</i> = 1 只动 5.8% 的参数，误差降到全量的同一量级。
4. **合并与切换**：同一底座 + 两个 LoRA，点按钮切换任务；合并前后输出只差浮点误差。
5. **Llama-3-8B 的账**：各层投影加 LoRA 的参数量表，全量微调 128.5 GB，LoRA 16.3 GB，QLoRA 4.2 GB（均不含激活）。

## 和前后两讲的关系

梯度下降、残差连接、LayerNorm、预训练几讲说的是怎么把一个模型从零训出来。这一讲说的是训出来之后怎么改：微调要动的参数其实很少，LoRA 用低秩把它说清楚、算便宜。它的低秩思想和 KV Cache 那讲的 MLA 一脉相承。微调具体要把模型改成什么样，下一讲讲后训练：只会续写的基座模型，怎样经过 SFT、偏好对齐和可验证奖励的强化学习变成助手；再下一讲专门拆开偏好对齐。

## 延伸阅读

- Edward J. Hu et al., *LoRA: Low-Rank Adaptation of Large Language Models* (2021)，原论文，第 7 节是关于 Δ<i>W</i> 低秩的分析
- Armen Aghajanyan et al., *Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning* (2020)，「微调的内在维度很低」这一观察的出处
- Tim Dettmers et al., *QLoRA: Efficient Finetuning of Quantized LLMs* (2023)
- Samyam Rajbhandari et al., *ZeRO: Memory Optimizations Toward Training Trillion Parameter Models* (2020)，「混合精度 + Adam 每参数 16 B」的记法来自这里
- Meta, *Llama 3* 模型卡与 `config.json`：本讲 Llama-3-8B 的架构参数来源
