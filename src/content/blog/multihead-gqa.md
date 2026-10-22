---
title: "多头注意力与 GQA：为什么要分成几十个头，又为什么让头共享 K、V"
description: "单头注意力只能算一种相关性，多头把向量切成 h 份各算各的，参数量却一个不多；推理时 KV cache 跟着 KV 头数走，于是有了 MQA 和 GQA。用 Llama-2-70B、Llama-3-8B、Llama-3-70B 的公开参数算显存和带宽。六个可交互实验。"
pubDate: 2026-10-17
tags: ["Transformer", "多头注意力", "GQA", "MQA", "KV cache"]
lab: /labs/multihead-gqa/
series: ai-mastery
order: 7
---

## 一句话版本

多头注意力把每个 token 的向量切成 h 段，每段在自己的小空间里独立算一次注意力，最后拼回来、乘 W<sub>O</sub> 混合：参数量和单头一样，却能同时看出好几种不同的「相关性」。推理时每个头的 K、V 都要缓存，显存和带宽跟着 KV 头数走，所以 MQA、GQA 让多个 Q 头共用一组 K、V：Q 照样问各自的问题，要存的东西少了几倍。

## 一个头只能有一种「相关性」

注意力那一讲里，一个 token 用自己的 Q 去和前面每个 token 的 K 做点积，softmax 之后得到一行权重，再按权重读 V。关键在于：**每个 token 只得到一行权重，也就是一种分配注意力的方式。**

可一个 token 同时需要很多信息：前一个 token 是谁、主语在哪、前面提到过的同一个东西在哪。这些问题要的注意力分布完全不同，一个指向紧挨着的位置，一个指向几十个 token 之前。把它们压进同一行权重，只能互相妥协，变成一个谁都没照顾好的平均。

办法是同时算好几行权重。

## 切开：每个头一个低维子空间

多头注意力不是把整套注意力复制 h 遍，而是把 d<sub>model</sub> 维切成 h 份，每份 d<sub>h</sub> = d<sub>model</sub> / h 维：

<figure class="clip"><video src="/videos/multihead-gqa/SplitHeads.webm" poster="/videos/multihead-gqa/SplitHeads.png" controls loop muted playsinline preload="metadata"></video></figure>

具体到矩阵：W<sub>Q</sub> 按列切成 h 块，第 <i>i</i> 块把 x 投影成第 <i>i</i> 个头的 q<sub><i>i</i></sub>（只有 d<sub>h</sub> 维），K、V 同理。每个头独立算

<p class="formula">head<sub><i>i</i></sub> = softmax(q<sub><i>i</i></sub> k<sub><i>i</i></sub>ᵀ / √d<sub>h</sub>) · v<sub><i>i</i></sub></p>

然后拼接，乘输出矩阵：

<p class="formula">MultiHead(x) = Concat(head<sub>1</sub>, …, head<sub><i>h</i></sub>) · W<sub>O</sub></p>

三点值得注意：

- **参数量不变。** W<sub>Q</sub>、W<sub>K</sub>、W<sub>V</sub>、W<sub>O</sub> 合计始终是 4 × d<sub>model</sub>²，切成 1 个头还是 64 个头都一样；算 QKᵀ 的乘法总数也一样。Llama-3-70B 的 d<sub>model</sub> = 8192，切成 64 个头，每头 128 维。
- **代价是每个头的维度变小。** 一个头只在 128 维里比较 Q 和 K，表达力不如 8192 维，但 64 个头各管一摊，整体更划算。
- **W<sub>O</sub> 负责混合。** 拼接后乘 W<sub>O</sub>，等价于每个头乘 W<sub>O</sub> 里属于自己的那几行，再把结果相加。实验 02 在页面里把两种算法都算了一遍，差别只剩浮点舍入。也就是说，每个头都往残差流里写一份自己的修正，W<sub>O</sub> 决定写到哪些方向上。

## 训练出来的头，真的各有分工

头的分工没有人设计，是训练出来的。Clark 等人 2019 年把 BERT-base（12 层 × 12 头，共 144 个头）的注意力逐个画出来，发现：

- 有些头几乎只看**前一个 token**或**后一个 token**：4 个头一半以上的注意力给了前一个 token。
- 很多头在中间层把大量注意力放在 `[SEP]` 这类特殊符号上。作者认为这相当于「这个头这里没事干」时的停靠位置。
- 有些头对应**句法关系**：一个头找名词前的限定词，准确率 94.3%；一个头找动词的宾语，86.8%。
- 有一个头做**指代**：从一个指称词指回前文里说的同一个对象，65% 的情况下找对了。

实验 01 照这几类构造了四个「模式头」（看前一个 token、看句首、看相同 token、看最近的标点），再放两个随机初始化的头对比：同一句话，六张热力图各不相同；随机头则糊成一片，说明分工全靠训练。

## 推理的瓶颈：KV cache 跟着 KV 头数走

生成文本时，模型一个 token 一个 token 地往外吐。为了不重复计算，前面每个 token 在每一层、每个头的 K 和 V 都存下来，这就是 KV cache。每个 token 要存的字节数是：

<p class="formula">2 × 层数 × KV 头数 × d<sub>h</sub> × 每个数的字节数</p>

标准多头注意力（MHA）里 KV 头数 = Q 头数。以 Llama-3-70B 的形状（80 层、每头 128 维、bf16）为例，如果 64 个头各存一份 K、V，每个 token 要 2.62 MB；8K 上下文的一条请求就是 21.5 GB。

而且不只是放得下放不下的问题。每生成一个 token，都要把整段 KV cache 从显存读一遍。H100 SXM 的显存带宽是 3.35 TB/s，读 21.5 GB 就要 6.4 ms，32 条并发就是 200 ms 以上，比读一遍 140 GB 的权重还慢。上下文越长、并发越多，生成速度越是被读 KV cache 卡住。

## MQA 与 GQA：让 Q 头共用 K、V

Shazeer 2019 年提出了一个激进的做法，**多查询注意力（MQA）**：Q 头照样是 h 个，但所有头共用同一组 K、V。KV cache 一下缩小 h 倍。代价是质量会下降，训练也可能不稳定，因为所有头只能在同一份「标签」和「内容」里找东西。

Ainslie 等人 2023 年的 **分组查询注意力（GQA）** 取中间：把 h 个 Q 头分成 g 组，每组共用一组 K、V。g = h 就是 MHA，g = 1 就是 MQA。

<figure class="clip"><video src="/videos/multihead-gqa/GroupedKV.webm" poster="/videos/multihead-gqa/GroupedKV.png" controls loop muted playsinline preload="metadata"></video></figure>

论文还给了一个省钱的办法：不必从头训练，拿现成的 MHA 模型，把同组内的 K、V 头取平均作为初始值，再用约 5% 的预训练算力继续训练（uptraining）。他们的结论是 GQA 的质量接近 MHA，速度接近 MQA。

现在主流开源模型基本都用 GQA。下面是公开 config 里的数（每 token、bf16）：

| 模型 | 层数 | Q 头 | KV 头 | 每 token：实际（GQA） | 若是 MHA | 若是 MQA |
|---|---|---|---|---|---|---|
| Llama-2-70B | 80 | 64 | 8 | 328 KB | 2.62 MB | 41.0 KB |
| Llama-3-8B | 32 | 32 | 8 | 131 KB | 524 KB | 16.4 KB |
| Llama-3-70B | 80 | 64 | 8 | 328 KB | 2.62 MB | 41.0 KB |

Llama-3-70B 用 8 个 KV 头，KV cache 是 MHA 的 1/8：8K 上下文一条请求 2.68 GB，而不是 21.5 GB。同一张卡能多放 8 倍的并发或 8 倍长的上下文，每一步要读的 KV 也少了 8 倍。（Llama 2 系列里只有 34B、70B 用了 GQA，7B、13B 还是 MHA。）

## 质量和速度怎么取舍

- **MHA**：每个头有自己的 K、V，表达力最强，KV cache 最大。
- **MQA**：KV cache 最小，但所有头被迫共享同一份 K、V，质量损失最明显。
- **GQA**：Q 头一个不少，每个头仍然问自己的问题；只是几个头在同一份「标签」和「内容」里查找。8 组左右时质量几乎不掉，KV cache 已经降到几分之一，所以成了默认选择。

还有第三条路：不减少头，而是把 K、V 压缩成一个更短的潜向量，用的时候再展开。这就是 DeepSeek 的 MLA，KV Cache 那一讲会讲到。

## 实验里讲了什么

0. **切头**：拖 h，看 d<sub>model</sub> 和 W<sub>Q</sub> 怎么切，每头维度变小，四个矩阵的参数合计不变。
1. **各看各的**：同一句话上六个头的注意力热力图，四个按规则构造的模式头加两个随机初始化的头；句子可改，可开关因果遮罩。
2. **拼接与 W<sub>O</sub>**：一层注意力每一步的张量形状；页面里真算一个 8 维玩具模型，验证「拼接再乘 W<sub>O</sub>」等于「各头乘自己那块再相加」，以及参数相同、只改头数，输出就不同。
3. **分组示意**：拖 KV 头数 g，看哪些 Q 头共享哪组 K、V，从 MHA 经 GQA 到 MQA。
4. **KV cache 计算器**：Llama-2-70B、Llama-3-8B、Llama-3-70B 或自填参数，改上下文、并发、精度，对比三种方案的显存。
5. **带宽视角**：每生成一个 token 读权重和读 KV cache 各要多久，随上下文增长的曲线，换算成每条请求的 token/s 上限。

## 和前后两讲的关系

注意力 QKV 那一讲讲了一个头怎么用 Q、K、V 算注意力，上一讲给它补上了位置（RoPE，每个头都按同样的角度转 q、k）；这一讲把多头拆开讲清楚，并从推理成本的角度引出 GQA。下一讲是一层里注意力之后的 MLP；再下一讲 KV Cache 接着讲：在 GQA 已经减少了头数之后，怎么再用量化把每个数压小，以及 MLA 怎么换一种方式少存数。

## 延伸阅读

- Vaswani et al., *Attention Is All You Need* (2017)，多头注意力的出处
- Kevin Clark, Urvashi Khandelwal, Omer Levy, Christopher D. Manning, *What Does BERT Look At? An Analysis of BERT's Attention* (2019)
- Noam Shazeer, *Fast Transformer Decoding: One Write-Head is All You Need* (2019)，MQA
- Joshua Ainslie et al., *GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints* (EMNLP 2023)
- Hugo Touvron et al., *Llama 2: Open Foundation and Fine-Tuned Chat Models* (2023)，34B、70B 采用 GQA
