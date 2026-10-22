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
\frac{16.06\ \text{GB}}{3.35\ \text{TB/s}} = \frac{16.06 \times 10^{9}}{3.35 \times 10^{12}}\ \text{s} = {{n:t1_ms}}\ \text{ms}
$$

搬进来之后要算多少？每个参数和输入相乘一次、再加到结果里一次，是 2 次运算，所以一个 token 要：

$$
2 \times 8{,}030{,}261{,}248 = {{n:fl1_g}} \times 10^{9}\ \text{次运算}
$$

H100 算完它要：

$$
\frac{{{n:fl1_g}} \times 10^{9}}{989.4 \times 10^{12}}\ \text{s} = {{n:tc1_ms}}\ \text{ms}
$$

{{fig1}}

搬数据 {{n:t1_ms}} ms，计算 {{n:tc1_ms}} ms，差了 {{n:ratio1}} 倍。计算单元只在 $1/{{n:ratio1}}$（约 {{n:util_w1}}） 的时间里干活，其余时间在等数据。这时速度完全由带宽决定：一秒最多出 $1 / {{n:t1_ms}}\ \text{ms} \approx {{n:tok1}}$ 个 token。这就是「decode 受带宽限制」的意思。

<details class="pause"><summary>停一下：按量化那一讲，把权重换成 INT4（按组 128，每个权重约 4.125 位），一个人用时每秒最多出几个 token？算力利用率变高还是变低？</summary>

权重变成 $8{,}030{,}261{,}248 \times 4.125 / 8 = {{n:int4_gb}}\ \text{GB}$，读一遍要 ${{n:int4_gb}} / 3.35\ \text{TB/s} = {{n:int4_ms}}\ \text{ms}$，每秒最多 {{n:int4_tok}} 个 token，快了将近 4 倍。要算的运算次数没变（反量化还要多算一点），时间却短了，所以算力利用率变高了，但仍然只有 1% 左右，GPU 照样大部分时间在等。

</details>

## 第二步：一份权重，很多人共用

现在有 64 个用户同时在等回答。最笨的做法是一个一个来：每人 {{n:t1_ms}} ms，轮一圈要 $64 \times {{n:t1_ms}}\ \text{ms} \approx {{n:seq64}}\ \text{ms}$。

注意一件事：64 个人用的是**同一份权重**。把 64 个人这一步的输入拼成一个 64 行的矩阵，权重读进来一次，和 64 行分别相乘，64 个人各得到一个 token。这叫**批处理**（batching），64 是 **batch 大小** $B$。

这一步要读的字节没变，还是 16.06 GB，搬运时间还是 {{n:t1_ms}} ms。运算次数变成 64 倍：

$$
64 \times {{n:fl1_g}} \times 10^{9} = {{n:nk64_fl}} \times 10^{12}\ \text{次}, \qquad \frac{{{n:nk64_fl}} \times 10^{12}}{989.4 \times 10^{12}}\ \text{s} = {{n:nk64_tc}}\ \text{ms}
$$

{{n:nk64_tc}} ms 仍然比 {{n:t1_ms}} ms 短，计算可以和搬运同时进行，所以这一步还是 {{n:t1_ms}} ms，但出了 64 个 token。整张卡每秒出 $64 / {{n:t1_ms}}\ \text{ms} \approx {{n:nk64_tot}}$ 个 token，是一个人时的 64 倍，几乎白送。

能一直白送下去吗？用一个数来判断：**算术强度**，即每从显存读 1 字节，做多少次运算（单位 FLOP/B）。

- batch $B$ 时，运算 $= B \times 2 \times 8{,}030{,}261{,}248$，读的字节 $= 2 \times 8{,}030{,}261{,}248$，两者相除，算术强度正好是 $B$。
- H100 自己也有一个比值：算力除以带宽，$989.4 \times 10^{12} / 3.35 \times 10^{12} \approx {{n:ridge}}$ FLOP/B。意思是每读 1 字节，它有能力做 {{n:ridge}} 次运算。

算术强度低于 {{n:ridge}}，数据跟不上，速度由带宽决定，强度每翻一倍，每秒完成的运算也翻一倍；高于 {{n:ridge}}，算力用满，再加大 batch 也不会更快。把这两段画在一起，就是**屋顶线**（roofline）：

$$
\text{可达到的算力} = \min\left(\text{峰值算力},\ \text{算术强度} \times \text{带宽}\right)
$$

{{fig2}}

只看权重的话，batch 一直加到 {{n:ridge}} 左右都是白送。可我们漏算了一样东西。

## 第三步：把 KV cache 算进来

KV Cache 那一讲讲过：每个 token 在每一层都存一份 K 和一份 V，生成下一个 token 时，前面所有 token 的 K、V 都要读一遍。Llama-3-8B 每个 token 的 KV cache 是：

$$
\underbrace{2}_{K \text{ 和 } V} \times \underbrace{32}_{\text{层}} \times \underbrace{8}_{\text{KV 头}} \times \underbrace{128}_{\text{头维度}} \times \underbrace{2\ \text{B}}_{\text{BF16}} = {{n:kv_tok}}\ \text{B}
$$

（8 个 KV 头而不是 32 个，是多头那一讲的 GQA 省下来的。）

假设每个用户的对话已经有 1000 个 token，一个人的 KV cache 就是：

$$
1000 \times {{n:kv_tok}}\ \text{B} = {{n:kv_user_mb}}\ \text{MB}
$$

关键在于：权重是大家共用的，**KV cache 是每人一份**。batch 里有 $B$ 个人，这一步就要读 $B$ 份。于是一步要读的字节变成：

$$
\text{读的字节} = 16.06\ \text{GB} + B \times {{n:kv_user_gb}}\ \text{GB}
$$

代入 $B = 64$：

$$
16.06 + 64 \times {{n:kv_user_gb}} = 16.06 + {{n:kvgb64}} = {{n:by64}}\ \text{GB}
$$

$$
\frac{{{n:by64}}\ \text{GB}}{3.35\ \text{TB/s}} = {{n:t64}}\ \text{ms}
$$

{{fig3}}

运算也多了一点：注意力要拿当前位置的 $q$ 和前面 1000 个 $k$ 做点积、再按份额加权 1000 个 $v$，每个 token 多出约 ${{n:attn_g}} \times 10^{9}$ 次运算，合计每人 ${{n:fl_tok_g}} \times 10^{9}$ 次。64 人共 {{n:tc64}} ms，仍小于 {{n:t64}} ms，所以这一步是 {{n:t64}} ms，出 64 个 token：

- 整张卡每秒：$64 / {{n:t64}}\ \text{ms} \approx {{n:tot64}}$ 个 token；
- 每个用户每秒：$1 / {{n:t64}}\ \text{ms} \approx {{n:per64}}$ 个 token。

换几个 batch 大小，同样算：

| batch $B$ | 一步读的字节 | 一步的时间 | 计算占用 | 整卡 token/s | 每个用户 token/s |
| --- | --- | --- | --- | --- | --- |
| 1 | {{n:by1}} GB | {{n:t1}} ms | {{n:util1}} | {{n:tot1}} | {{n:per1}} |
| 8 | {{n:by8}} GB | {{n:t8}} ms | {{n:util8}} | {{n:tot8}} | {{n:per8}} |
| 64 | {{n:by64}} GB | {{n:t64}} ms | {{n:util64}} | {{n:tot64}} | {{n:per64}} |
| 256 | {{n:by256}} GB | {{n:t256}} ms | {{n:util256}} | {{n:tot256}} | {{n:per256}} |
| {{n:bmax}} | {{n:by487}} GB | {{n:t487}} ms | {{n:util487}} | {{n:tot487}} | {{n:per487}} |

最后一行的 {{n:bmax}} 是显存的上限：80 GB 减去权重 16.06 GB 还剩 {{n:free_gb}} GB，每人 {{n:kv_user_gb}} GB，最多放 $\lfloor {{n:free_gb}} / {{n:kv_user_gb}} \rfloor = {{n:bmax}}$ 个人（这里没扣激活值等运行开销，实际要再少一些）。这张卡在这个设定下，最多同时伺候 {{n:bmax}} 个用户。

{{fig4}}

表里还有一件事：**计算占用始终没到 100%**。batch 越大，算术强度越接近一个上限：多一个人，多读 {{n:kv_user_mb}} MB，多算 ${{n:fl_tok_g}} \times 10^{9}$ 次，比值是 ${{n:fl_tok_g}} \times 10^{9} / ({{n:kv_user_mb}} \times 10^{6}) \approx {{n:ilim}}$ FLOP/B，比拐点 {{n:ridge}} 低。所以上下文有 1000 个 token 时，不管 batch 多大，decode 都是带宽说了算，而越来越多的带宽花在了读 KV cache 上。这就是 GQA、MLA 和 KV cache 量化值钱的地方：KV cache 小一半，同样的带宽就能多伺候将近一倍的人。

<details class="pause"><summary>停一下：如果每个用户的上下文从 1000 个 token 变成 4000 个，最多能同时服务几个人？</summary>

每人的 KV cache 变成 $4000 \times {{n:kv_tok}}\ \text{B} = 524.3\ \text{MB}$。剩余显存还是 {{n:free_gb}} GB，$\lfloor {{n:free_gb}} / 0.5243 \rfloor = 121$ 个人，只有原来的四分之一左右。上下文越长，能同时伺候的人越少。

</details>

## 第四步：静态批处理：一批走完，下一批才进来

道理清楚了：batch 越大越划算。可真实的请求不是整整齐齐一起来、一起走的，每个回答长短不一。

把规模缩小到能数格子：只有 4 个**槽**（batch 最多 4 个人），排队的有 8 个请求 A–H，各自要生成的 token 数是：

| 请求 | A | B | C | D | E | F | G | H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 要生成的 token | 7 | 2 | 3 | 8 | 2 | 6 | 4 | 3 |

每一步，每个占着槽的请求出 1 个 token（为了好数，先不算读入问题的 prefill）。

最直接的做法是**静态批处理**：A、B、C、D 组成一批，一起开始；这一批里最长的 D 要 8 步，所以要等 8 步全部结束，才换下一批 E、F、G、H，这一批最长的 F 要 6 步。

{{fig5}}

一共 $8 + 6 = {{n:st_t}}$ 步。4 个槽 × {{n:st_t}} 步 = {{n:st_slots}} 个格子，真正出 token 的只有 $7 + 2 + 3 + 8 + 2 + 6 + 4 + 3 = {{n:tot_out}}$ 个，利用率 ${{n:tot_out}} / {{n:st_slots}}$ = {{n:st_util}}。B 在第 2 步就说完了，它的槽空等 6 步；E 只要 2 个 token，却要排到第 9 步才开始，第 10 步才拿到完整回答。

## 第五步：连续批处理：谁说完了，下一步就补人

换个规矩：**每一步结束时检查一遍**，谁说完了，就把它的槽交给队首的下一个请求，下一步新请求就开始生成。这叫**连续批处理**（continuous batching），最早由 Orca（Yu 等，OSDI 2022）以「按迭代调度」的名字提出：调度的单位是一步，而不是一整个请求。

照这个规矩一步步排：

- 第 1–2 步：A、B、C、D 在跑。B 第 2 步说完。
- 第 3 步：E 补进 B 的槽。C 第 3 步说完。
- 第 4 步：F 补进 C 的槽。E 第 4 步说完（它从第 3 步开始，2 个 token）。
- 第 5 步：G 补进 E 的槽。A 第 7 步说完。
- 第 8 步：H 补进 A 的槽。D、G 第 8 步说完，F 第 9 步说完，H 第 10 步说完。

{{fig6}}

同样 8 个请求，{{n:cb_t}} 步全部完成，利用率 ${{n:tot_out}} / {{n:cb_slots}}$ = {{n:cb_util}}。每个请求完成的平均步数也从 {{n:st_avg}} 降到 {{n:cb_avg}}：E 第 4 步就拿到了回答，而不是第 10 步。

真实的服务里还要处理新请求的 prefill：一个刚进来的请求要先把整段问题读一遍，算出它的 KV cache。prefill 一次处理几百上千个 token，一份权重乘很多行，算术强度高，是算力说了算；如果整段一口气做完，同一步里正在 decode 的人都要等它。常见的做法是**分块 prefill**（chunked prefill）：把长问题切成几块，每一步只带一块，和大家的 decode 拼在一起算。

## 第六步：KV cache 放在哪：按最大长度预留

连续批处理让 batch 一直满着，batch 能多大，取决于显存里放得下多少份 KV cache。第三步算的是理想情况，每份正好占自己那么多。实际做到这一点并不容易。

问题出在：一个请求开始时，**不知道它最后会生成多少个 token**。早期的做法是按允许的最大长度，给每个请求预留一整段连续的显存，这样它怎么写都不会越界。

用最小的例子数格子：显存一共 36 格，每格放 1 个 token 的 K、V；每个请求最长 12 个 token。此刻有三个请求，已经写了 5、9、3 个 token。

- 按最大长度预留：每个请求占 12 格，三个占满 {{n:res_alloc}} 格，实际只写了 $5 + 9 + 3 = {{n:res_used}}$ 格，其余 $36 - 17 = 19$ 格被占着没用，浪费 $19 / 36$ = {{n:res_waste}}。新请求一个也进不来。

这还只是一种浪费（预留了没用上）。另外，请求结束后释放的一段段空间大小不一，新请求要的连续长度可能哪一段都放不下，这叫**外部碎片**。PagedAttention 论文（Kwon 等，SOSP 2023）实测了当时的系统：KV cache 区域里，真正存着 token 状态的只有 20.4%–38.2%。

## 第七步：PagedAttention：按页分配，用到才给

操作系统早就遇到过同样的问题，办法是**分页**：内存切成固定大小的页，程序看到的是连续的地址，实际可以散落在任何物理页上，由一张页表记录对应关系，用到一页才分配一页。

PagedAttention 把这一套搬到 KV cache 上：

1. 显存切成固定大小的**块**，每块放固定个数 token 的 K、V。我们的例子里每块 4 格。
2. 每个请求有一张**块表**，记着它的第 0、1、2…… 个逻辑块分别放在第几号物理块。
3. 请求写满一块，才再分配一块；请求结束，块还回空闲池。
4. 注意力算子按块表去各个物理块里取 K、V，不要求它们挨在一起。

同样三个请求：5 个 token 要 $\lceil 5/4 \rceil = 2$ 块，9 个要 3 块，3 个要 1 块，一共 6 块 = {{n:pg_alloc}} 格。占着没用的只有每个请求最后一块里的空格：$24 - 17 = 7$ 格，浪费 $7 / 24$ = {{n:pg_waste}}。更要紧的是还空出 3 块，可以再接新请求。

{{fig7}}

{{fig8}}

浪费有上限：每个请求只有最后一块可能没写满，最多空「块大小 − 1」格。真实的块是 16 个 token（vLLM 默认值，2026-10 核实），Llama-3-8B 一块是 $16 \times {{n:kv_tok}}\ \text{B} = {{n:block_mb}}\ \text{MiB}$。平均每个请求空 $(16-1)/2 = 7.5$ 格，对一个 1000 个 token 的请求是 {{n:waste_avg}}。外部碎片也没有了：所有块一样大，任何一个空块都能给任何请求用。

论文报告，这样做让 vLLM 在延迟相同的情况下，吞吐比 FasterTransformer、Orca 高 2–4 倍，序列越长、模型越大，提升越明显。省下的显存变成了更大的 batch，而第三步已经算过，batch 越大吞吐越高。

块表还带来一个额外的好处：两个请求的块表可以指向同一个物理块。这就是下一步的基础。

## 第八步：prefix caching：相同的开头只算一次、只存一份

很多请求的开头一模一样：同一个应用的系统提示、同一份长文档、多轮对话里之前的每一轮。设我们例子里每个用户的 1000 个 token 中，前 800 个是所有人共用的系统提示，后 200 个是各自的问题。

前 800 个 token 一样，它们的 K、V 也一样吗？一样。第 $i$ 个位置的 K、V 只取决于第 1 到第 $i$ 个 token（模型只往前看，位置编码也只看位置号），开头完全相同，算出来就完全相同。

所以只要认出「这一块和以前某一块一样」，就能直接复用。办法是给每个**写满的块**算一个哈希：

$$
h_j = \operatorname{hash}\left(h_{j-1},\ \text{第 } j \text{ 块的 } 16 \text{ 个 token}\right)
$$

把前一块的哈希也算进去，是因为同样 16 个 token，前面的内容不同，K、V 就不同；带上 $h_{j-1}$，哈希相同就意味着从开头到这一块全部相同。800 个 token 正好是 $800 / 16 = {{n:shared_blocks}}$ 块。新请求进来，从第一块开始逐块算哈希、查表，前 {{n:shared_blocks}} 块都能查到，就让它的块表直接指向已有的物理块，从第 51 块开始才自己算。

{{fig9}}

省了两样东西。

**显存。** 共用部分只存一份：$800 \times {{n:kv_tok}}\ \text{B} = {{n:shared_mb}}\ \text{MB}$。每个人只需存自己的 200 个 token：${{n:own_mb}}$ MB。剩余显存能放的人数从 {{n:bmax}} 变成：

$$
\left\lfloor \frac{{{n:free_gb}}\ \text{GB} - {{n:shared_mb}}\ \text{MB}}{{{n:own_mb}}\ \text{MB}} \right\rfloor = {{n:b_prefix}}
$$

（这只是放得下的人数；每一步还是要把每个人用到的 KV cache 读一遍，速度另算。）

**首个 token 的等待时间。** 不复用时，新请求要 prefill 全部 1000 个 token：$2 \times 8.03 \times 10^{9} \times 1000$ 次运算再加注意力，约 {{n:pf_full}} ms，算力说了算。复用后只 prefill 自己的 200 个：运算只要 {{n:pf_own_c}} ms，但权重总得读一遍，{{n:pf_own_m}} ms，所以是 {{n:pf_own}} ms。等待时间少了 {{n:pf_save}}。

vLLM 默认打开 prefix caching，用的正是这种逐块哈希（2026-10 核实）。SGLang 的 RadixAttention 把所有缓存过的前缀组织成一棵基数树，按 token 逐段匹配，效果相同。

<details class="pause"><summary>停一下：有人把「当前时间：2026-10-22 14:03:27」写在系统提示的第一行。prefix cache 还能命中吗？</summary>

几乎不能。时间每秒都在变，第一块的 token 就和以前不同，$h_1$ 不同；而 $h_2$ 要用到 $h_1$，所以 $h_2$ 也不同，后面每一块的哈希都跟着变。命中只能从开头连续地命中，第一块不同，800 个 token 全部要重算。会变的内容要放在提示的最后面。

</details>

## 第九步：投机解码：小模型先猜，大模型一次验证

回到第一步：只有一个用户时，算力 99% 以上闲着。有没有办法把闲着的算力换成速度？

**一次验证几个 token 和验证一个，时间几乎一样。** batch 1 时，让大模型同时处理 5 个位置（像 prefill 一样），读的还是同一份权重和同一份 KV cache，运算变成 5 倍：$5 \times$ 原来的运算约 {{n:v1_tc}} ms，仍然远小于读数据的 {{n:d1_ms}} ms。所以验证 5 个位置也是 {{n:v1_ms}} ms。

于是有了**投机解码**（speculative decoding，Leviathan 等，ICML 2023）：

1. 用一个小得多的模型（草稿模型）快速地一个一个猜出 $\gamma$ 个 token（$\gamma$ 读作 gamma，是猜测长度）。
2. 大模型一次前向，同时算出这 $\gamma$ 个位置、再加后面一个位置上它自己的概率分布。
3. 从第一个猜测开始逐个检查，按一个规则决定接受还是拒绝；遇到第一个被拒的就停，后面的猜测全部作废。
4. 大模型在停下的位置自己给出一个 token。所以每一轮至少得到 1 个 token，最多 $\gamma + 1$ 个。

### 接受规则：不改变大模型的输出

规则要保证：最后输出的 token，概率分布和大模型自己一个一个生成时**完全一样**。

用一个能手算的例子：下一个 token 只有三个候选「饭」「粥」「面」。大模型的概率 $p$ 是 $(0.6,\ 0.3,\ 0.1)$，小模型的概率 $q$ 是 $(0.5,\ 0.2,\ 0.3)$。

{{fig10}}

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

{{fig11}}

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
= 0.2 + 0.32 + 0.384 + 0.4096 + 2.048 = {{n:e4}}
$$

换一种数法能得到一般公式。一轮得到的 token 数 = 1（大模型自己给的那个）+ 被接受的猜测个数。第 $i$ 个猜测被接受，要求前 $i$ 个全部接受，概率是 $\alpha^i$。所以期望是：

$$
E = 1 + \alpha + \alpha^2 + \cdots + \alpha^{\gamma}
$$

代入检查：$1 + 0.8 + 0.64 + 0.512 + 0.4096 = {{n:e4}}$，和上面一样。

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

代入：$(1 - 0.8^5) / (1 - 0.8) = (1 - 0.32768) / 0.2 = {{n:e4}}$。

### 加速多少

一轮的成本：小模型跑 $\gamma$ 次，大模型跑 1 次。设小模型跑一次的时间是大模型的 $c$ 倍（论文实验里 $c$ 都小于 0.05），一轮的时间就是大模型一步的 $\gamma c + 1$ 倍。不用投机解码时，大模型一步出 1 个 token，所以：

$$
\text{加速比} = \frac{1 - \alpha^{\gamma + 1}}{(1 - \alpha)(\gamma c + 1)}
$$

代入 $\alpha = 0.8$、$\gamma = 4$、$c = 0.05$：

$$
\frac{{{n:e4}}}{4 \times 0.05 + 1} = \frac{{{n:e4}}}{1.2} = {{n:sp4}}
$$

{{fig12}}

猜得越多，期望 token 增长越慢（第 $i$ 个猜测要以 $\alpha^i$ 的概率才用得上），小模型的成本却是一个一个线性加上去的，所以 $\gamma$ 有一个最好的值：这里是 $\gamma = {{n:best_g}}$，加速 {{n:sp_best}} 倍。论文在 T5-XXL 上实测，输出不变，延迟降到原来的二分之一到三分之一。

<details class="pause"><summary>停一下：如果小模型和大模型完全一样，<i>α</i> 是多少？这时投机解码还有意义吗？</summary>

$p = q$ 时每个 token 上取小就是它自己，$\alpha = \sum_x p(x) = 1$，每个猜测都被接受，一轮得到 $\gamma + 1$ 个 token。但小模型的成本也和大模型一样，$c = 1$，加速比是 $(\gamma + 1)/(\gamma + 1) = 1$，白忙一场。投机解码要的是一个又小（$c$ 小）又像（$\alpha$ 大）的草稿模型。

</details>

### batch 大了以后

投机解码靠的是「验证 5 个位置和验证 1 个一样快」，前提是算力闲着。batch 大了，算力不再闲。以第十步会用到的 batch {{n:bsla}} 为例：普通一步 {{n:spbs_td}} ms；验证时每人算 5 个位置，运算变成 5 倍，一步变成 {{n:spbs_tv}} ms，已经是算力说了算；再加上小模型猜 4 次，一轮 {{n:spbs_tot}} ms。每人每轮期望得到 {{n:e4}} 个 token，加速比只剩 $({{n:e4}} \times {{n:spbs_td}}) / {{n:spbs_tot}} = {{n:spbs}}$，比 batch 1 时的 {{n:spb1}} 小了不少；batch 再大、上下文再短，还可能比不用更慢。所以投机解码最适合用户少、要求每个人都快的场景。

## 第十步：吞吐与延迟，选一个点

回到第三步的表。衡量推理服务常用两个数：

- **吞吐**：整张卡每秒出多少个 token，决定一张卡能服务多少人、每个 token 的成本。
- **延迟**：每个用户感受到的速度。分成两段：从发出请求到看到第一个 token 的时间（TTFT，主要是排队加 prefill），以及之后每个 token 之间的间隔（TPOT，就是 decode 一步的时间）。

表里两者是反着走的：batch 从 1 加到 {{n:bmax}}，吞吐从 {{n:tot1}} 涨到 {{n:tot487}} token/s，每个用户的速度从 {{n:per1}} 降到 {{n:per487}} token/s。

所以要先定延迟的要求，再在要求之内把 batch 开到最大。比如要求每个用户至少 50 token/s，也就是一步不超过 $1 / 50 = 20$ ms：

$$
\frac{16.06\ \text{GB} + B \times {{n:kv_user_gb}}\ \text{GB}}{3.35\ \text{TB/s}} \le 20\ \text{ms}
$$

左右两边乘 3.35 TB/s，右边是 $3.35 \times 10^{12} \times 0.02 = 67.0\ \text{GB}$：

$$
16.06 + {{n:kv_user_gb}}\,B \le 67.0 \quad \Rightarrow \quad B \le \frac{67.0 - 16.06}{{{n:kv_user_gb}}} \approx {{n:bsla}}
$$

batch 取 {{n:bsla}}，一步 {{n:tsla}} ms，每人 {{n:persla}} token/s，整卡 {{n:totsla}} token/s。和把显存塞满（{{n:bmax}} 人、{{n:tot487}} token/s）相比，吞吐只少了约 5%，每个人却快了约 20%。

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
