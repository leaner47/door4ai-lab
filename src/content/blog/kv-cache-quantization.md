---
title: "KV Cache 为什么能压、怎么压"
description: "从一组数怎么压成 4 bit，讲到 DeepSeek 为什么能把 KV cache 砍掉 90%。五个可交互实验。"
pubDate: 2026-10-13
tags: ["LLM 推理", "量化", "KV cache", "MLA"]
lab: /labs/kv-cache/
series: ai-mastery
order: 10
---

## 起因：前文不变，结果也不变

跑大模型时内存吃紧，主要是 KV cache：每个 token 在每一层都要存一份 K 和一份 V，生成每个新 token 都要把它们完整读一遍。既然前文不变，前文的 K、V 就不变，这正是 prefix caching 的依据。但"存到更便宜的介质上"并不能解决问题，因为瓶颈是带宽：解码时每个 token 都要读完整段 KV cache，HBM 是 TB/s 级，SSD 只有几 GB/s，光存储更慢。真正有效的办法是让 KV 本身变小。

## 实验里讲了什么

上面的实验分五步：

1. **量化就是把数放到网格上。** 在 [min, max] 之间铺 2^bits 条网格线，每个数吸附到最近的一条；只存"第几条"（整数），外加整组共享的 scale 和 zero。拖 bits 到 2、打开离群值开关，看一个大数怎么把其余 15 个数的分辨率吃掉。
2. **注意力为什么扛得住误差。** softmax 是指数放大，只有头部几个 token 拿到权重；V 侧的误差被加权平均抵消。int8 几乎无损，int4 相似度仍在 0.99 以上，int2 开始翻车。
3. **K 的离群值长在通道上，V 的不是。** K 矩阵里有几条竖着的亮线（固定通道对所有 token 偏大，和 RoPE 及锚点维度有关），V 的大值零散、偏按 token 分布。所以 K 按通道分组、V 按 token 分组，这就是 KIVI 的结论。
4. **算一算显存。** 每 token 占用 = 2 × 层数 × KV 头数 × 头维度 × 字节数。70B 模型 128K 上下文、bf16 时 KV cache 就要 40 GB；切到 int4 变 10 GB；换 MLA 架构再降一个量级。
5. **MLA：不压每个数，而是少存数。** K 和 V 都从同一个隐状态投影而来，冗余很大；MLA 只存一个 512 维的潜向量，用时再展开。量化压位宽，MLA 压个数，两者正交可叠加。

## 延伸阅读

- KIVI: *A Tuning-Free Asymmetric 2bit Quantization for KV Cache* (2024)
- KVQuant: *Towards 10 Million Context Length LLM Inference with KV Cache Quantization* (2024)
- DeepSeek-V2 技术报告中关于 Multi-head Latent Attention 的章节
