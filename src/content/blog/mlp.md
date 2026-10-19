---
title: "MLP：注意力之后，每个词自己查一查"
description: "一层 Transformer 的另一半。MLP 占了模型的大部分参数：升维、激活、降维，Llama 和 Qwen 用带门的 SwiGLU；一个神经元像一个与门；再在 Qwen3-0.6B 里找出真正在分辨两个「小米」的神经元。"
pubDate: 2026-10-19
tags: ["Transformer", "MLP", "SwiGLU", "Qwen3"]
lab: /labs/mlp/
series: ai-mastery
order: 8
---

## 一句话版本

一层 Transformer = 注意力 + MLP。注意力让词和词交换信息，MLP 对每个位置单独做"升维、非线性、降维"，再通过残差加回原向量。模型的大部分参数在 MLP 里，很多知识也被认为存在这里。

## 参数花在哪

设向量维度 $d$、查询头数 $h$、键值头数 $h_{kv}$、每头维度 $d_h$、MLP 中间维度 $d_{ff}$，每层参数量（忽略偏置和归一化层）：

$$
N_{\text{attn}} = 2\,d\,h\,d_h + 2\,d\,h_{kv}\,d_h \qquad N_{\text{MLP}} = m\,d\,d_{ff}
$$

$m$ 是 MLP 里矩阵的个数，GPT-3 是 2，Llama、Qwen 用 SwiGLU 是 3。代入 Qwen3-0.6B（$d = 1024$，$h = 16$，$h_{kv} = 8$，$d_h = 128$，$d_{ff} = 3072$，28 层）：每层注意力约 6.3 M、MLP 约 9.4 M，加上约 1.6 亿的词表嵌入，合计约 6 亿，和官方数字一致。实验 00 里四个模型的 MLP 都是最大的一块。

## MLP 的形状

最早的写法：

$$
\operatorname{MLP}(x) = W_{\text{down}}\,\operatorname{ReLU}\!\left(W_{\text{up}}\,x + b\right)
$$

Llama、Qwen 用 SwiGLU，多一个门矩阵 $W_{\text{gate}}$：

$$
\operatorname{MLP}(x) = W_{\text{down}}\left(\operatorname{SiLU}\!\left(W_{\text{gate}}\,x\right)\odot W_{\text{up}}\,x\right) \qquad \operatorname{SiLU}(z) = \frac{z}{1+e^{-z}}
$$

$\odot$ 表示逐个相乘：门算出来的数决定 $W_{\text{up}}\,x$ 的每一路放行多少。没有激活函数，两个矩阵相乘还是一个矩阵，MLP 就只能做线性变换；正是激活函数的"折"，让它能表达"满足条件才输出"。

## 一个神经元像一个与门

$W_{\text{up}}$ 的一行和向量做点积，像在提一个问题；ReLU 加偏置 $b$ 决定亮不亮，只有条件同时满足时才亮；$W_{\text{down}}$ 的对应一列是它亮起时往向量里加的方向。实验 02 用"迈克尔 + 乔丹 → 篮球"演示这个与门，去掉偏置后它会乱联想。

## 真实模型里的神经元

把「我在粮油店买了两斤小米」和「我在数码店买了一部小米」分别送进 Qwen3-0.6B，在「小米」的位置记下每层 3072 个神经元的激活，找两句话差得最多的。第 9 层的 2190 号神经元在粮油店那句里激活 6.9，在数码店那句里接近 0；把它在 $W_{\text{down}}$ 里的那一列和词表比，最接近的是"面粉、米饭、淀粉"。第 21 层的 2170 号神经元在「小米」（手机）和「长城」（汽车）两组里都出现，方向接近"系列、配备、造价"。

也有很多神经元的方向读不出意思。一个神经元往往同时参与好几件事（多义神经元），常见的解释是模型把比神经元个数更多的特征叠在同一组神经元里（叠加，superposition），所以"一个神经元对应一个概念"只在少数情况下成立。

## 实验里讲了什么

0. **参数构成。** Qwen3-0.6B、Llama-3-8B、Llama-3-70B、GPT-3 的注意力、MLP、词表嵌入占比。
1. **激活函数。** ReLU、SiLU、GELU 三条曲线，拖动输入看输出。
2. **与门。** 勾选输入特征，看哪个神经元亮起、往向量里加什么。
3. **真实神经元。** Qwen3-0.6B 每层激活差别最大的 6 个神经元，以及它们加进去的方向最接近的词（「小米」和「长城」两组）。

## 和前后两讲的关系

前两讲拆开了注意力（一个头，再到多头与 GQA），这一讲补上一层里的另一半。下一讲 KV Cache 回到推理：生成时前面每个词的 $k$、$v$ 都要存下来，它为什么占显存，又怎么压。

## 延伸阅读

- Shazeer, *GLU Variants Improve Transformer* (2020)
- Geva et al., *Transformer Feed-Forward Layers Are Key-Value Memories* (2021)
- Elhage et al., *Toy Models of Superposition* (2022)
- 3Blue1Brown，《深度学习》第 7 章：How might LLMs store facts
