---
title: "LayerNorm 为什么必需：把每一层的数字拉回同一把尺子"
description: "深网络里向量的大小会随层数漂移：残差流越加越大，不同 token 的向量长度差几十倍，梯度跟着漂，学习率就没法统一。看归一化怎么把一个向量减均值、除标准差拉回同一把尺子，为什么是 LayerNorm 而不是 BatchNorm，RMSNorm 省了什么，Pre-Norm 和 Post-Norm 差在哪。六个可交互实验。"
pubDate: 2026-10-17
tags: ["训练", "LayerNorm", "RMSNorm", "Pre-Norm", "Transformer"]
lab: /labs/layernorm/
series: ai-mastery
order: 35
---

## 一句话版本

深网络里，每一层看到的数字大小会随层数漂移：越往深处向量越长，不同 token 的向量长短也差几十倍。数字大小一漂，梯度跟着漂，一个学习率没法同时适合所有层、所有 token。归一化（Norm）在每一层把每个 token 的向量减去均值、除以标准差，拉回同一把尺子：

<p class="formula"><i>y</i> = <i>γ</i> · (<i>x</i> − <i>μ</i>) / <i>σ</i> + <i>β</i></p>

今天的大模型每一层都有两个 Norm，参数量几乎为零，却是深网络能训起来的必需品。

## 问题：尺度在漂

残差那一讲说过，Transformer 是一条残差流：每一层往主干上加一个修正量，<i>h</i> ← <i>h</i> + <i>F</i>(<i>h</i>)。修正量是由 <i>h</i> 算出来的，<i>h</i> 越长，<i>F</i>(<i>h</i>) 也越长。于是如果不做任何处理，主干的长度会按指数增长：实验 01 里，分支输出和输入差不多长时，每层大约乘 √2，32 层之后是几万倍。

第二种漂移在同一层内部。实验 02 把 256 个随机的 token 向量送进同一个网络，每个 token 走过的 ReLU 路径不一样，长度像随机游走一样越走越散，32 层后最长和最短差几十倍。同一个矩阵 <i>W</i> 要同时伺候这些长短悬殊的向量，没法用同一组参数做好。

这两种漂移最终都落到梯度上。反向传播那一讲说过，每个参数的梯度正比于它看到的输入：输入大一千倍，梯度就大一千倍，学习率乘上去的步子也大一千倍。实验 04 里不做 Norm 的网络，层数或分支大小一变，第 1 层的梯度就差好几个数量级。学习率是对着梯度的量级调的，梯度漂到哪里都不确定，学习率就没法定：实验 05 里，不做 Norm 时能用的学习率范围随层数和分支大小剧烈移动，到 16 层时一档都不剩。

## 做法：减均值，除标准差，再给两个旋钮

归一化的做法很朴素。取一个 token 在这一层的向量 <i>x</i>（Llama-3-8B 里是 4096 个数），算它们的均值 <i>μ</i> 和标准差 <i>σ</i>：

<p class="formula"><i>x̂</i> = (<i>x</i> − <i>μ</i>) / <i>σ</i></p>

<figure class="clip"><video src="/videos/layernorm/NormalizeVector.webm" poster="/videos/layernorm/NormalizeVector.png" controls loop muted playsinline preload="metadata"></video></figure>

减均值是整体平移，把中心挪到 0；除标准差是整体缩放，把散布变成 1。做完以后，不管原来的向量被放大多少倍、平移多少，结果都一模一样（实验 00）：放大和平移这两个自由度被抹掉了，剩下的信息全在各分量的相对大小里。

然后逐维乘 <i>γ</i> 加 <i>β</i>。这两个是网络自己学的参数，每一维一个：如果某一维真的需要更大的尺度或者偏移，网络可以通过 <i>γ</i>、<i>β</i> 把它放回去。它们让归一化不会削弱网络的表达能力，初始值 <i>γ</i> = 1、<i>β</i> = 0，相当于一开始什么都不加。

参数量：Llama-3-8B 每层两个 RMSNorm（下面会讲），每个只有一个 4096 维的 <i>γ</i>，32 层加最后一个合计 2 × 32 × 4096 + 4096 = 266 240 个参数，占 80.3 亿总参数的 0.003%。几乎免费。

## 为什么是 LayerNorm，不是 BatchNorm

归一化最早在卷积网络里流行的是 BatchNorm：对一个 batch 里的所有样本、同一个通道的数字一起算均值和标准差。它对图像很好用，但到了语言模型上有三个麻烦：

- **样本互相依赖。** 一个 token 的输出取决于同一个 batch 里其他句子是什么，训练结果和 batch 怎么拼有关。
- **序列变长。** 句子有长有短，一个 batch 里第 500 个位置可能只有一两句话有，统计量没法算稳。
- **推理时 batch = 1。** 用户一次只发一句话，没有 batch 可以算统计量，只能用训练时存下来的移动平均，训练和推理的行为不一致。

LayerNorm 换了个方向：只用一个 token 自己的 <i>d</i> 个数算均值和标准差，不看别的 token、不看别的样本。这样每个 token 的归一化只依赖它自己，序列多长、batch 多大、训练还是推理，行为完全一样。这正是序列模型需要的。

## RMSNorm：少减一个均值

RMSNorm 把 LayerNorm 再简化一步：不减均值，直接除以均方根 RMS = √(mean(<i>x</i>²))，也去掉 <i>β</i>：

<p class="formula"><i>y</i> = <i>γ</i> · <i>x</i> / RMS(<i>x</i>)</p>

RMS² = <i>σ</i>² + <i>μ</i>²，所以均值为 0 时两者完全相同；均值不为 0 时，RMSNorm 的输出被整体压小一些，但各分量的相对大小不变（实验 03）。提出者的实验发现减均值那一步对效果没什么帮助，省掉它少算一次归约，在 GPU 上更快。Llama、Qwen、Gemma、Mistral 这一代开源模型用的都是 RMSNorm；GPT-2、BERT 用的是 LayerNorm。

## Pre-Norm 还是 Post-Norm

Norm 放在残差块的哪个位置，有两种选择：

<p class="formula">Post-Norm：<i>h</i> ← Norm(<i>h</i> + <i>F</i>(<i>h</i>))　　Pre-Norm：<i>h</i> ← <i>h</i> + <i>F</i>(Norm(<i>h</i>))</p>

2017 年的原版 Transformer 和 BERT 用 Post-Norm：先加再归一化，Norm 在主干上。GPT-2 以后的大模型几乎都改成了 Pre-Norm：Norm 在分支里，主干本身不经过任何变换。

<figure class="clip"><video src="/videos/layernorm/PrePostNorm.webm" poster="/videos/layernorm/PrePostNorm.png" controls loop muted playsinline preload="metadata"></video></figure>

区别在残差那一讲说过的直达通路。Pre-Norm 的主干从输出一路直通到第 1 层，梯度沿着这条路的增益是 1 × 1 × 1 = 1，不管多少层。Post-Norm 的主干每层都被除以一次 <i>σ</i><sub><i>l</i></sub>，直达通路的增益是 ∏ 1/<i>σ</i><sub><i>l</i></sub>，每层打一次折，层数一多就指数级消失（实验 04 的最后一个读数），梯度只能靠一层层分支接力，深网络又回到了没有残差的状态。对 Post-Norm 的分析还发现，它在刚初始化时靠近输出的几层梯度特别大，学习率必须先从很小慢慢升上去（warm-up），否则训练一开始就不稳；Pre-Norm 的梯度在初始化时就是均匀的，可以不用 warm-up。

Pre-Norm 也有代价：主干不再被归一化，长度会随层数按 √<i>L</i> 慢慢增长（实验 01 的蓝线），所以最后一层之后还要再加一个 Norm 才送去算 logits。这是今天大模型的标准写法：每层两个 Norm（注意力前一个、MLP 前一个），最后再一个。

## 实验里讲了什么

0. **一个向量的归一化**：拖动整体放大和平移，输出一动不动；<i>γ</i>、<i>β</i> 是网络自己学的两个旋钮。
1. **残差流的长度**：不做 Norm 时按指数增长，Pre-Norm 按 √<i>L</i> 缓慢增长，Post-Norm 不变。随机矩阵真实前向。
2. **不同 token 的长度分布**：256 个 token 走过同一个无 Norm 的网络，32 层后长度差几十倍；LayerNorm 之后全部等于 √64。
3. **LayerNorm 对 RMSNorm**：同一个向量两种算法的结果，均值为 0 时相同，均值越偏差异越大。
4. **Norm 放在哪，梯度多大**：16 维小网络真实反向传播，不做 Norm 时梯度随层数和分支大小漂几个数量级，两种 Norm 都压回同一量级；Post-Norm 直达通路的增益随层数指数消失。
5. **学习率的可用范围**：三种设计各试 7 档学习率训练 200 步。不做 Norm 时可用范围随层数和分支大小剧烈移动，有 Norm 时基本不动。

## 和前后两讲的关系

残差那一讲（第 25）给了主干和直达通路，这一讲解释主干上的数字为什么会漂、Norm 怎么把它拉回来，以及 Norm 放在分支里才能保住直达通路。上一讲反向传播（第 30）说梯度正比于每层看到的输入，这一讲就是它的直接后果：输入的尺度不稳，梯度就不稳，学习率就没法定。下一讲讲预训练：把梯度下降、反向传播、残差和 LayerNorm 装成一个完整的训练步，看模型怎么从一大堆文字里学会说话。

## 延伸阅读

- Jimmy Lei Ba, Jamie Ryan Kiros, Geoffrey E. Hinton, *Layer Normalization* (2016)
- Sergey Ioffe, Christian Szegedy, *Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift* (2015)
- Biao Zhang, Rico Sennrich, *Root Mean Square Layer Normalization* (2019)，RMSNorm 原论文
- Ruibin Xiong et al., *On Layer Normalization in the Transformer Architecture* (ICML 2020)，Post-Norm 为什么需要 warm-up、Pre-Norm 为什么可以不用
- Hugo Touvron et al., *LLaMA: Open and Efficient Foundation Language Models* (2023)，第 2.2 节说明 Pre-Norm + RMSNorm 的选择
