---
title: "Embedding 与 RAG：为什么检索有时答非所问"
description: "一句话怎么变成一个向量、向量库怎么按余弦相似度找最近的、RAG 流水线的七步，以及检索答非所问的五种原因：切块切坏、top-k 不对、模型不认识专业词、问题和答案措辞不像、检索到了模型没用上。页内真实训练一个小 embedding 模型，六个可交互实验。"
pubDate: 2026-10-17
tags: ["Agent", "RAG", "Embedding", "向量检索", "rerank"]
lab: /labs/rag-embedding/
series: ai-mastery
order: 115
---

## 一句话版本

RAG（Retrieval-Augmented Generation，检索增强生成）就是：先从你的资料里**找出**几段最相关的，再把它们**塞进上下文**让模型照着答。「找」靠的是 embedding：把每段文字变成一个向量，意思相近的向量夹角小。检索答非所问，几乎都出在这条流水线的某一环：资料切坏了、取的条数不对、模型不认识你的专业词、你问的话和答案的写法不像，或者找到了但模型没看进去。

## 一句话变成一个向量

注意力那一讲里，Q 和 K 的点积用来衡量两个 token 多相关。embedding 做的是同一件事，只是对象从 token 换成了整句、整段：一个 embedding 模型读进一段文字，吐出一串固定长度的数，比如 1024 个。这串数就是这段文字在「语义空间」里的坐标。

<figure class="clip"><video src="/videos/rag-embedding/TextToVector.webm" poster="/videos/rag-embedding/TextToVector.png" controls loop muted playsinline preload="metadata"></video></figure>

两个向量像不像，看夹角。夹角用余弦相似度算，就是把点积除以两个长度：

<p class="formula">cos <i>θ</i> = (<i>q</i> · <i>d</i>) / (‖<i>q</i>‖ ‖<i>d</i>‖)</p>

「鲜奶开了以后能放多久」和「开封的牛奶要冷藏」没有几个字相同，但训练好的模型会把它们放在几乎同一个方向上，余弦接近 1；「灭火器放在什么地方」和它们接近垂直，余弦接近 0。模型是怎么学会这件事的？大体上是在海量文本上学「哪些说法经常出现在一起」：同一个话题下的词彼此靠近。实验 00 里页内训练的小模型就是这么做的（TF-IDF + SVD，经典的 LSA 方法），语料只有 84 句话，但已经能把三个话题分开。

常见的 embedding 模型与维度（2026 年 10 月 19 日查各家官方文档与模型卡的结果）：

| 模型 | 维度 | 最长输入 | 备注 |
|---|---|---|---|
| OpenAI text-embedding-3-small / -large | 1536 / 3072 | 8191 token | 可用 `dimensions` 参数截短 |
| BAAI BGE-M3（开源） | 1024 | 8192 token | 100 多种语言；同时支持稠密、稀疏、多向量三种检索 |
| Voyage voyage-4 | 1024（可选 256 / 512 / 2048） | 32000 token | `input_type` 区分 query / document |
| Qwen3-Embedding 0.6B / 4B / 8B（开源） | 1024 / 2560 / 4096 | 32K token | 可截短维度；查询前可加任务指令 |

## 向量库与 RAG 流水线

把所有资料的向量存起来，查询时算它和每一条的余弦、取最大的几条，这就是向量库。几十万条以内暴力算就够快；再大就用近似最近邻索引（HNSW 之类），换一点精度省很多时间。

整条流水线分离线和在线两段：

<figure class="clip"><video src="/videos/rag-embedding/RAGPipeline.webm" poster="/videos/rag-embedding/RAGPipeline.png" controls loop muted playsinline preload="metadata"></video></figure>

1. **切块**：长文档切成几百字的 chunk；
2. **向量化**：每块过一遍 embedding 模型；
3. **入库**：向量连同原文存进向量库；
4. **查询向量化**：用户的问题过同一个 embedding 模型；
5. **top-k**：按余弦取最相近的 k 块；
6. **进上下文**：把这 k 块原文和问题一起拼成 prompt；
7. **回答**：模型照着上下文作答。

每一步都可能出错，而且出错时模型照样会一本正经地回答。

## 为什么会答非所问

**切块切坏了。** 按字数硬切，答案所在的那句话正好横跨两块，哪块都不完整；两块各自和问题都只有一半像，排名反而落后于一段只是泛泛沾边的文字。实验 01 里 81 个字的反冲洗步骤，用 100 字的块不重叠地切，被劈进两块，最完整的那块也只有 88%。

**top-k 不对。** k 太小，有多条相关的问题只拿到一部分；k 太大，塞进一堆无关片段，既占上下文又把模型带偏。相似度分数是连续的，没有一条天然的线告诉你第几名以后是垃圾（实验 02）。

**embedding 模型不懂你的专业词。** 模型只认识训练语料里见过的说法。你们公司内部的缩写、产品代号、新名词，它从没见过，变成的向量和这个词的真实含义没有关系。实验 03 里「SOP」在页内模型眼里是生词，查询向量全为 0，一条都搜不到；真实模型不会给 0，但给出的向量同样不可靠。

**问题和答案的措辞不像。** 问题是一句疑问（「发薪日是哪天」），答案是一句陈述（「工资每月 10 日发放」），两者的向量天然有差距。这叫 query 与 passage 的不对称，所以很多模型要求你标明哪边是查询、哪边是文档（Voyage 的 `input_type`、Qwen3-Embedding 加在查询前的任务指令），训练时专门拉近「问题」和「它的答案」。

**检索到了，模型没用上。** 上一讲讲过 Lost in the Middle：上下文中间的内容最容易被忽略，论文里答案埋在 20 篇文档中间时，正确率比不给任何资料还低。相关片段排在第 5 条、夹在一堆无关片段中间，模型可能根本没看见它（实验 04 用的就是上一讲那条示意曲线）。

## 怎么改

- **重叠切块、按句切**：相邻块留几十字重叠，或者只在句号处下刀，答案就不会被劈开。
- **混合检索**：关键词检索（BM25）只认完全一样的词，对缩写、型号、人名特别准；向量检索认意思，对换了说法的问题特别准。两边各出一份排名，用 RRF（倒数排名融合）合并，谁都不漏（实验 03）。
- **rerank**：先用便宜的向量检索粗召回 20–100 条，再用一个更贵但更准的打分模型（cross-encoder，把问题和候选拼在一起读）逐条精排，只留前几条，并把最相关的放在上下文开头或末尾。实验 05 的精排器是简化的模拟（用压缩前的完整词袋打分），但两阶段的结构和真的一样。
- **HyDE**：先让模型就这个问题「编」一段像答案的话，拿这段话去检索，绕过问题和答案措辞不像的问题。

## 实验里讲了什么

0. **向量的相近**：页内真实训练的 24 维 embedding，9 句话三个话题；拖动查询箭头或输入自己的句子，看余弦相似度排序。
1. **切块**：290 字的手册段落，拖块大小和重叠，看三个问题的答案有没有被切断；重叠小时完整与否全凭运气，按句子切则不会劈开句子。
2. **top-k 与召回**：40 条虚构手册的真实向量检索，拖 k 看召回率和噪声：「闭店要做哪些事」有 5 条相关，k = 3 只找到 2 条，k = 12 找到 4 条但塞进 8 条无关的。
3. **关键词 vs 向量 vs 混合**：同一查询三种排名并排（BM25 页内实现）；16 个预设查询上相关条目进前 5 的比例：关键词 13、向量 14、混合 16。
4. **从检索到回答**：真实检索出的 top-k 拼成上下文，拖动答案片段排第几，套用上一讲拟合论文实测点的示意曲线看命中率，中间位置低于不给资料的 56.1%。
5. **rerank**：向量 top-20 → 精排 top-5，16 个查询上相关条目排第 1 的数量从 9 个变成 12 个。

## 和前后两讲的关系

上一讲《上下文窗口是 Agent 的工作记忆》说，外部知识量太大，放不进窗口，要留在外面、按问题检索、只把相关的几段带回来——这一讲就是「取」的具体做法；它的 Lost in the Middle 也解释了为什么取回来的东西还得放对位置。余弦相似度接的是注意力那一讲的点积。下一讲 MCP：检索这样的能力通常会被包装成一个工具（「查一下知识库」）挂给 Agent，Agent 自己决定什么时候调用，MCP 就是这类工具的标准接口。

## 延伸阅读

- Patrick Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (2020)，RAG 一词的出处
- Nelson F. Liu et al., *Lost in the Middle: How Language Models Use Long Contexts* (2023)
- Luyu Gao et al., *Precise Zero-Shot Dense Retrieval without Relevance Labels* (2022)，HyDE
- Gordon V. Cormack et al., *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods* (2009)，RRF
- Stephen Robertson & Hugo Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009)
- OpenAI、Voyage AI、BAAI BGE-M3、Qwen3-Embedding 的官方模型文档与模型卡（表中数据来源，2026 年 10 月 19 日查证）
