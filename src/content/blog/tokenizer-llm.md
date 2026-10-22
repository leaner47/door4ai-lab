---
title: "Token 是什么：一句话是怎么进出大模型的"
description: "从真实的 GPT-4o 分词器开始，亲手训练一个 BPE，看中文为什么费 token，再跟着一串整数走完 Embedding、注意力、FFN、logits 和采样。六个可交互实验。"
pubDate: 2026-10-15
tags: ["入门", "token", "分词", "BPE", "推理流程", "采样"]
lab: /labs/tokenizer-llm/
series: ai-mastery
order: 4
---

## 一句话版本

大模型看不见文字。分词器先把文字切成一段段 **token**，每个 token 对应词表里的一个整数编号。模型只做一件事：读进一串编号，给出"下一个 token 是谁"的概率，抽出一个，接回去，再来一遍。

## Token 是怎么切出来的

主流做法叫 **BPE（Byte Pair Encoding）**，分两个阶段：

1. **训练**：从 256 个字节起步，统计语料里所有相邻片段对的出现次数，把最常见的一对合并成新 token，记下这条规则，重复到词表达到预定大小（GPT-4o 约 20 万个）。
2. **编码**：遇到新文本时，先拆成字节，再按训练时记下的顺序一条条套用合并规则，能合并就合并，最后查表得到编号。

结果是：常见的词整个算一个 token，罕见的词被拆成几块，任何文字都能表示，不会有"不认识的字"。

**中文的情况**：一个汉字在 UTF-8 里是 3 个字节。训练语料里中文越多，常用字和常用词越早被合并成整块。GPT-2 的语料以英文为主，同一句中文要用的 token 常常是 GPT-4o 的两到三倍。

## 进了模型以后

1. **Embedding 查表**：每个编号取出一行向量，一串编号变成一个 `[T × d]` 的矩阵。
2. **L 层 Transformer**：每层先做注意力（token 之间交换信息，这是它们唯一交流的地方），再做 FFN（每个 token 各自变换，参数大头在这里）。每层都有残差连接和 Norm。
3. **输出投影**：只取最后一个位置的向量，乘一个 `d × V` 的矩阵，得到词表里每个 token 的分数（logits）。
4. **采样**：logits 除以温度、softmax 成概率、按 top-p 截断，抽出一个 token。
5. **循环**：把新 token 接到输入末尾，回到第 1 步，直到抽到结束 token。第一遍要把整段输入一次算完（Prefill），之后每遍只算新来的一个（Decode），前面的 K、V 存在 KV Cache 里复用。

## 实验里讲了什么

0. **真实分词器**：用 GPT-2 和 GPT-4o 的分词规则切你输入的句子，看中文、英文、代码、emoji 分别被切成什么样。
1. **亲手训练 BPE**：一步步合并最常见的相邻对，看词表变大、总 token 数变少。默认语料 low ×5、lower ×2、newest ×6、widest ×3 是给定的词频（出自 Sennrich 等人 2016 年的 BPE 论文），实验下方可展开每个数字的算法：片段对次数 = 含这一对的词的频次之和，总 token 数 = 各词片段数 × 频次之和。
2. **用规则切新词**：没见过的 lowest 被切成 low + est。
3. **字节级 BPE 与中文**：在浏览器里用一段中文语料真的训练一个字节级 BPE，拖动合并次数，看字节碎片怎么长成字、再长成词。
4. **模型里的五站**：选 GPT-2、Llama-3-8B 或 Llama-3-70B，按公开架构参数看每一站的形状和参数占比。
5. **自回归**：播放 Prefill 和 Decode，看每一遍算多少 token、KV Cache 怎么长。
6. **温度和 top-p**：在真实的概率分布上拖滑块，看分布怎么变尖、变平，再亲手抽几个 token。

## 和前后两讲的关系

第 1 讲讲的显存和带宽，决定了第 5 个实验里每一遍能跑多快。下一讲先把这里用到的数学（向量、矩阵乘法、softmax、温度）一步一步算清楚，再下一讲把第 2 站"注意力"拆开，看 Q、K、V 到底在算什么。

## 延伸阅读

- Sennrich et al., *Neural Machine Translation of Rare Words with Subword Units* (2016)，BPE 用于分词的出处
- Andrej Karpathy, *Let's build the GPT Tokenizer*（视频）与 minbpe 代码
- Transformer Explainer（poloclub）：在浏览器里跑 GPT-2 的交互式可视化
- AnimatedLLM（kasnerz）：带中文界面的 LLM 生成过程动画
