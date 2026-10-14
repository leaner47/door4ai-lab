---
title: "注意力里的 Q、K、V 到底在干什么"
description: "用 3Blue1Brown 的方式讲注意力：点积、softmax、√d、加权求和、多头，再到 MLP 里的知识。六个可交互实验。"
pubDate: 2026-10-14
tags: ["Transformer", "注意力", "QKV", "多头注意力", "MLP"]
lab: /labs/attention-qkv/
series: ai-mastery
order: 5
---

## 一句话版本

每个词是一个向量。注意力让每个词拿自己的 **Q（我想找什么）** 去和别的词的 **K（我能回答什么）** 做点积，点积越大越"对得上"；softmax 把分数变成权重，再按权重把别人的 **V（我能给你什么）** 加到自己身上。公式就是：

**Attention(Q, K, V) = softmax(QKᵀ / √d) · V**

## 实验里讲了什么

1. **点积就是对齐程度。** 二维玩具里，「生物」的 Q 和"毛茸茸的""蓝色"的 K 指向同一边，权重几乎全给了它们；「漫步在」的 Q 则对上名词「生物」。后面的词被遮罩，生成模型只能看前文。
2. **softmax 和 √d。** 用真实的随机高斯向量演示：维度越高点积越大，不缩放时 softmax 变成赢者通吃；除以 √d 后，分布形状与维度无关。
3. **加权求和 V，改写自己。** 结果是加到原向量上的修改量（残差），原来的意思保留，再贴上新信息。
4. **多头。** 三个头同时问"谁修饰我""谁在做动作""我前面是谁"，同一个词从每个头拿到不同信息。
5. **合并与规模。** 各头结果拼接后乘 W_O；按公开架构参数计算 GPT-3、Llama-3-70B、Llama-3-8B 的参数构成：MLP 占大头，GQA 让 K、V 头变少。
6. **MLP 存知识。** 升维、ReLU、降维：偏置加 ReLU 像一个"与门"，只有"迈克尔"和"乔丹"同时出现时才往向量里加"篮球"。

## 和下一讲的关系

生成每个新词时，它的 Q 要和前面所有词的 K 做点积、再读所有词的 V。前面词的 K、V 不会变，所以可以存下来反复用，这就是 KV cache。下一讲讲它为什么占显存、又怎么压。

## 延伸阅读

- Vaswani et al., *Attention Is All You Need* (2017)
- 3Blue1Brown，《深度学习》系列第 6、7 章：Attention in transformers、How might LLMs store facts
- Elhage et al., *A Mathematical Framework for Transformer Circuits* (2021)
