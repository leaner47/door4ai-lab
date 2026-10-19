---
title: "MoE 混合专家：参数很多，每次只用一小部分"
description: "Transformer 的参数大头在 MLP。MoE 把一个 MLP 换成很多个专家，再加一个路由器，每个 token 只送给其中几个。看路由器怎么打分、为什么要做负载均衡、容量满了怎么办，再用 Mixtral、DeepSeek-V3、DeepSeek-V4-Flash 的公开参数算总参数、激活参数和 decode 时要读的权重。六个可交互实验。"
pubDate: 2026-10-17
tags: ["Transformer", "MoE", "混合专家", "路由", "推理"]
lab: /labs/mixture-of-experts/
series: ai-mastery
order: 15
---

## 一句话版本

把 Transformer 每层里的那个 MLP 复制成很多份，叫作「专家」，再加一个很小的**路由器**：每个 token 进来，路由器给所有专家打分，只把它送给分数最高的 <i>k</i> 个，把它们的输出按分数加权求和。模型因此可以有很多参数（**总参数**），而每个 token 只用到其中一小部分（**激活参数**）。DeepSeek-V3 总共 671B 参数，每个 token 只激活 37B。

## 参数大头在 MLP

注意力那一讲算过：一层 Transformer 里，注意力负责 token 之间交换信息，MLP 负责每个 token 各自「想一想」，参数大部分在 MLP。以 Llama-3-70B 为例，每层注意力约 1.5 亿参数，MLP 约 7 亿，MLP 占了每层的 82%。

模型想变强，最直接的办法是把 MLP 做大。但稠密模型里每个参数对每个 token 都要算一遍：参数翻倍，每个 token 的计算量也翻倍。MoE 的想法是把这两件事拆开：参数可以很多，但每个 token 只走其中一部分。

## 路由器：打分、取 top-k、加权求和

<figure class="clip"><video src="/videos/mixture-of-experts/RouterTopK.webm" poster="/videos/mixture-of-experts/RouterTopK.png" controls loop muted playsinline preload="metadata"></video></figure>

路由器就是一个线性层，矩阵 <i>W<sub>g</sub></i> 的形状是 <i>d</i> × <i>E</i>（<i>E</i> 是专家数）。对一个 token 的向量 <i>x</i>：

1. **打分**：<i>s</i> = <i>x</i> · <i>W<sub>g</sub></i>，每个专家一个分数；
2. **softmax**：把分数变成概率 <i>p</i>；
3. **top-k**：只留概率最大的 <i>k</i> 个专家，其余专家对这个 token 一次乘法都不做；
4. **加权求和**：留下的 <i>k</i> 个概率重新归一化成权重 <i>g</i>，输出

<p class="formula"><i>y</i> = Σ<sub><i>i</i> ∈ top-<i>k</i></sub> <i>g<sub>i</sub></i> · <i>E<sub>i</sub></i>(<i>x</i>)</p>

每个专家 <i>E<sub>i</sub></i> 本身就是一个普通的 MLP（今天多是 SwiGLU，三个矩阵）。各家细节不同：Mixtral 先取 top-2 再对这两个分数做 softmax，结果和上面一样；DeepSeek-V3 用 sigmoid 代替 softmax 打分，选出 8 个后再归一化。

专家不是人为分好工的。没有人规定哪个专家管数学、哪个管代码，分工是和路由器一起训练出来的，而且往往不是人能一眼看懂的那种分工。实验 05 里，4 个专家在训练中自己把一条折线分成了四段。

## 总参数和激活参数

<figure class="clip"><video src="/videos/mixture-of-experts/TotalVsActive.webm" poster="/videos/mixture-of-experts/TotalVsActive.png" controls loop muted playsinline preload="metadata"></video></figure>

一个 MoE 层的参数 = <i>E</i> 个专家 + 路由器；一个 token 用到的只有 <i>k</i> 个专家 + 路由器。所以要分开看两个数：

- **总参数**决定显存：所有专家都得放在显存里，因为不知道下一个 token 会选谁；
- **激活参数**决定计算：前向一次，每个激活参数大约一次乘法一次加法，每 token 计算量 ≈ 2 × 激活参数。

用公开的 config 算一遍（实验 03 可以逐项改）：

| 模型 | 发布 | 每层专家 | 每 token 激活 | 总参数 | 激活参数 |
|---|---|---|---|---|---|
| Mixtral 8x7B | 2023-12 | 8 个 | 2 个 | 46.7B | 12.9B |
| DeepSeek-V3 | 2024-12 | 256 个路由 + 1 个共享 | 8 + 1 | 671B | 37B |
| DeepSeek-V4-Flash | 2026 | 256 个路由 + 1 个共享 | 6 + 1 | 284B | 13B |

Mixtral 的名字容易误会：8x7B 不是 56B，因为 8 个专家共用同一套注意力和 embedding，只有 MLP 是 8 份。按 config 逐项算：每个专家 1.76 亿参数，32 层 × 8 个专家共 45.1B，加上注意力、embedding 等 1.6B，总共 46.7B；每个 token 只走 2 个专家，激活 12.9B。DeepSeek-V3 一个专家只有 4400 万参数，比 Mixtral 的小得多，但数量多得多，这叫**细粒度专家**：专家越小越多，组合方式越多，分工可以更细。

另一个设计是**共享专家**（DeepSeekMoE 提出）：除了路由选出的 <i>k</i> 个，再放一两个所有 token 都经过的专家，专门学大家都需要的通用知识，路由专家就不用每个都重复存一份。

## 负载均衡：别让大家都挤一个专家

路由器和专家是一起训练的，这里有一个正反馈：某个专家开始时稍微多分到一些 token，它学得更快、输出更好，路由器就更爱选它，它分到的 token 更多……最后少数专家包揽一切，其余专家闲着、几乎学不到东西，花了显存却没用上。实验 01 和 05 都能看到这种塌缩。

常见的三种应对。

**辅助损失**：在训练损失里加一项，惩罚负载不均。Switch Transformer 的写法是

<p class="formula"><i>L</i><sub>aux</sub> = <i>α</i> · <i>E</i> · Σ<sub><i>i</i></sub> <i>f<sub>i</sub></i> · <i>P<sub>i</sub></i></p>

<i>f<sub>i</sub></i> 是这一批分给专家 <i>i</i> 的 token 比例，<i>P<sub>i</sub></i> 是路由器给专家 <i>i</i> 的平均概率。哪个专家又热门、路由器又偏爱，这一项就把它的分数往下压。<i>α</i> 太小管不住，太大又会干扰本来的任务，要调。

**偏置调节**（DeepSeek-V3）：不加损失项，给每个专家一个只用于挑选的偏置。每一步看负载，超载的专家偏置调低一点，空闲的调高一点。它不影响输出的加权，只影响谁被选上。

**容量因子**：每个专家在一批里最多处理 <i>C</i> = 容量因子 × <i>T</i> · <i>k</i> / <i>E</i> 个 token（<i>T</i> 是这一批的 token 数），超出的直接丢掉，这个 token 在这一层少算一个专家，只靠残差连接原样往下传。这样每块 GPU 上的计算形状固定，好调度，代价是丢 token 和空槽白算。DeepSeek-V3 靠负载均衡做到训练和推理都不丢 token。

## 推理时意味着什么

MoE 把「参数多」和「计算多」拆开了，但没有把「显存」省掉：

- **显存看总参数**。DeepSeek-V3 用 FP8 存，光权重就要约 671 GB，一块 80 GB 的卡放不下，必须多卡。上一讲的权重量化，对 MoE 尤其重要。
- **计算看激活参数**。每个 token 的计算量和一个 37B 的稠密模型差不多。
- **decode 读的权重看 batch**。decode 每一步都要把用到的权重从显存读一遍，带宽常常是瓶颈。batch 里只有 1 个 token 时，每层只读 <i>k</i> 个专家，读的量和激活参数一样，这是 MoE 最划算的地方。batch 一大，不同 token 选的专家不同，要读的是它们的并集：DeepSeek-V3 同时 decode 64 个 token 时，每层 256 个专家平均要用到约 222 个，读的权重接近整个模型，而每个专家只分到 2 个多 token。

所以 MoE 推理通常用**专家并行**：把专家分散到很多块 GPU 上，每块卡只放一部分专家，token 被发往存着它所选专家的那块卡，算完再送回来。这样每块卡只读自己那部分专家，再用很大的 batch 让每个专家一次多处理几个 token。

## 实验里讲了什么

0. **路由器**：10 个示例 token 经路由器打分，拖 <i>k</i> 看每个 token 被分到哪些专家，点一个 token 看分数、softmax、top-k 归一化的完整计算。
1. **负载均衡**：把一个专家的偏置调高，让它变成「热门」，再分别只用任务损失、加辅助损失、用 DeepSeek-V3 的偏置调节，在浏览器里真实训练 300 步，看负载柱状图和最大负载 ÷ 平均负载怎么变。
2. **容量因子**：蒙特卡洛模拟一批 token 的路由，拖容量因子和路由偏斜，看多少分配被丢弃、多少槽位空着。
3. **总参数 vs 激活参数**：用 Mixtral 8x7B、DeepSeek-V3、DeepSeek-V4-Flash 的 config 逐项算，和官方数字对照；改层数、专家数、<i>k</i>、共享专家，看总参数、激活参数、每 token 计算量和权重显存。
4. **稠密 vs MoE**：同样的激活参数，比较显存、每 token 计算和 decode 每一步读的权重，batch 从 1 到 1024，并集按真实的组合概率算。
5. **小型真实 MoE**：4 个线性专家拟合一条四段折线，看它们怎么自己分工，以及关掉辅助损失后怎么塌缩。

## 和前后两讲的关系

注意力那一讲讲了 MLP 是每层的参数大头，这一讲把 MLP 换成很多个专家。上一讲的权重量化管的是每个参数占几个字节，这一讲管的是每个 token 用到哪些参数，两者合起来决定一个大模型要多少显存、跑多快。到这里，推理和架构部分就讲完了：一个训练好的模型怎么切 token、怎么算注意力、怎么存 KV cache、怎么压权重、怎么只激活一部分参数。从下一讲开始，讲这些参数是怎么训练出来的：梯度下降。

## 延伸阅读

- Noam Shazeer et al., *Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer* (2017)，Noisy Top-K 门控
- Dmitry Lepikhin et al., *GShard* (2020)，top-2 路由、容量因子与专家并行
- William Fedus, Barret Zoph, Noam Shazeer, *Switch Transformers* (2021)，top-1 路由与辅助损失
- Albert Q. Jiang et al., *Mixtral of Experts* (2024)
- Damai Dai et al., *DeepSeekMoE* (2024)，细粒度专家与共享专家
- DeepSeek-AI, *DeepSeek-V3 Technical Report* (2024)，无辅助损失的负载均衡
- DeepSeek-AI, *DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence* (2026)
