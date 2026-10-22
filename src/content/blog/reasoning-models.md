---
title: "推理模型：为什么让模型多想一会儿，答案会更好"
description: "同一道两步的应用题，直接答和先写步骤再答，结果差很多：每个 token 的计算量是固定的，多写 token 就是多算。再往前一步：采样多条推理投票、让验证器挑最好的、在固定预算下比较「大模型少想」和「小模型多想」，最后看推理模型是怎么用可验证奖励训出来的，以及思考 token 的代价。"
pubDate: 2026-10-22
tags: ["推理模型", "思维链", "自洽性", "测试时计算", "强化学习"]
lab: /labs/reasoning-models/
series: ai-mastery
order: 43
---

<!-- 本文由 labs-src/reasoning-models/toy.py 从 article.src.md 生成，图和数字都由脚本算出。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

大模型每生成一个 token，做的计算量是固定的，不管这个 token 难不难。一道要算好几步的题，如果要求模型马上给出答案，它只有一个 token 的计算量可用；如果让它先把中间步骤写出来，每写一个 token 就多一次计算，而且写下的中间结果后面都能读到。这就是**思维链**（chain of thought）。在这个基础上还有两种「多花算力换准确率」的办法：**多想几条**（采样多条推理，投票或让验证器挑），以及**想得更长**（用强化学习把模型训练成习惯写长推理的**推理模型**）。代价也很直接：思考 token 一样要算钱、要等。

下面整讲用同一道题：

> 一箱有 12 个苹果。买了 3 箱，吃掉 7 个，还剩几个？

答案是 $12 \times 3 - 7 = 29$。它要两步：先乘，再减。

## 同一道题，两种答法

**直接答**：读完题，下一个 token 就得是答案。

**分步答**：先写「3 箱是 12 × 3 = 36。吃掉 7 个，36 − 7 = 29。」，最后才写「答案是 29」。

两种答法用的是同一个模型、同样的参数，区别只在模型输出的东西。Wei 等人（2022）把这件事做成了实验：在提示里放 8 道例题，一组例题只写答案，另一组例题写「先列步骤再给答案」，然后让模型做 GSM8K（一套 8 千多道小学数学应用题）。

<figure class="fig">
<svg viewBox="0 0 480 206" role="img" aria-label="GSM8K 上直接答与思维链提示的解题率">
<text x="10.0" y="30.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">PaLM 540B</text><text x="92.0" y="58.0" font-size="15" text-anchor="end" style="fill:var(--muted)">直接答</text><rect x="100.0" y="40.0" width="89.5" height="24.0" rx="4" style="fill:var(--line)"/><text x="197.5" y="58.0" font-size="16" text-anchor="start" style="fill:var(--muted)">17.9%</text><text x="92.0" y="90.0" font-size="15" text-anchor="end" style="fill:var(--muted)">思维链</text><rect x="100.0" y="72.0" width="284.5" height="24.0" rx="4" style="fill:var(--accent)"/><text x="392.5" y="90.0" font-size="16" text-anchor="start" style="fill:var(--accent)">56.9%</text><text x="10.0" y="126.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">GPT-3 175B</text><text x="92.0" y="154.0" font-size="15" text-anchor="end" style="fill:var(--muted)">直接答</text><rect x="100.0" y="136.0" width="78.0" height="24.0" rx="4" style="fill:var(--line)"/><text x="186.0" y="154.0" font-size="16" text-anchor="start" style="fill:var(--muted)">15.6%</text><text x="92.0" y="186.0" font-size="15" text-anchor="end" style="fill:var(--muted)">思维链</text><rect x="100.0" y="168.0" width="234.5" height="24.0" rx="4" style="fill:var(--accent)"/><text x="342.5" y="186.0" font-size="16" text-anchor="start" style="fill:var(--accent)">46.9%</text>
</svg>
<figcaption>图 1　GSM8K（小学数学应用题）的解题率，提示里给 8 个例题。只是把例题的答案改成「先写步骤再给答案」，两个模型的正确率都翻了将近三倍。数据：Wei 等 2022，表 1。</figcaption>
</figure>

例题里多了几行步骤，PaLM 540B 的解题率从 17.9% 涨到 56.9%。这就是**思维链提示**（chain-of-thought prompting）。两个相关的发现：

- 这个效果只在大模型上出现。论文里参数量小于约 100 B 的模型，加了步骤反而不涨甚至变差：小模型写出来的步骤常常是错的。
- 不给例题也行。Kojima 等人（2022）发现只在问题后面加一句「Let's think step by step」（一步一步想），InstructGPT（text-davinci-002）在 GSM8K 上从 10.4% 涨到 40.7%。

为什么写出步骤会有这么大的差别？答案在模型生成每个 token 时做了多少计算。

## 为什么写出来有用：每个 token 的计算量是固定的

### 一个 token 只过一遍模型

前面几讲说过，模型生成一个 token 的过程是：把到目前为止的所有 token 送进去，经过固定数量的层，最后一层输出下一个 token 的概率（Token 那一讲、注意力那一讲）。

拿一个公开的模型算具体数字。Llama-3-8B 有 32 层、约 80.3 亿个参数（记作 $N = 8.03 \times 10^9$）。生成一个 token 时，每个参数大约参与一次乘法和一次加法，所以每个 token 的计算量约为：

$$
\begin{aligned}
2N &= 2 \times 8.03 \times 10^{9} \\
&\approx 1.61 \times 10^{10}\ \text{FLOP}
\end{aligned}
$$

也就是约 16.1 G 次浮点运算。这个数不看 token 的内容：生成「的」和生成一道题的答案，花的计算一样多。

### 直接答：只有一次机会

直接答的时候，答案 token 是模型读完题后生成的第一个 token。要算出 29，所有的计算（先算 $12 \times 3$，再减 7）必须在这一次前向计算里完成，也就是在 32 层里完成。

层是一层接一层算的：第 5 层要等第 4 层算完才能开始。所以 32 层就是一次前向计算里最多能串起来的计算步数。如果一道题需要的串行步骤超过模型一次能做的，模型就只能猜一个看起来像答案的数。

### 分步答：每写一个 token 就多算一次

分步答时，模型一共生成 22 个 token（下图的切分是示意），每个 token 都有自己的一次前向计算。

<figure class="fig">
<svg viewBox="0 0 480 286" role="img" aria-label="直接答只有一次前向计算，分步答每个 token 都有一次">
<text x="10.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">直接答</text><rect x="10.0" y="34.0" width="92.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="56.0" y="56.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">题目……</text><rect x="110.0" y="34.0" width="40.0" height="32.0" rx="6" style="stroke:var(--warn);stroke-width:2.2;fill:none"/><text x="130.0" y="56.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">?</text><rect x="124.0" y="72.0" width="12.0" height="40.0" rx="2" style="fill:var(--line)"/><text x="144.0" y="98.0" font-size="14" text-anchor="start" style="fill:var(--muted)">32 层，一次</text><text x="10.0" y="128.0" font-size="15" text-anchor="start" style="fill:var(--muted)">分步答</text><rect x="10.0" y="140.0" width="21.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="20.5" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">3</text><rect x="16.5" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="35.0" y="140.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="50.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">箱</text><rect x="46.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="69.0" y="140.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="84.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">是</text><rect x="80.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="103.0" y="140.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="118.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">12</text><rect x="114.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="137.0" y="140.0" width="21.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="147.5" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">×</text><rect x="143.5" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="162.0" y="140.0" width="21.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="172.5" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">3</text><rect x="168.5" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="187.0" y="140.0" width="21.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="197.5" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">=</text><rect x="193.5" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="212.0" y="140.0" width="30.0" height="30.0" rx="6" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><text x="227.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">36</text><rect x="223.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="246.0" y="140.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="261.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">。</text><rect x="257.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="280.0" y="140.0" width="48.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="304.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">吃掉</text><rect x="300.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="332.0" y="140.0" width="21.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="342.5" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">7</text><rect x="338.5" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="357.0" y="140.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="372.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">个</text><rect x="368.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="391.0" y="140.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="406.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">，</text><rect x="402.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="425.0" y="140.0" width="30.0" height="30.0" rx="6" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><text x="440.0" y="161.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">36</text><rect x="436.0" y="175.0" width="8.0" height="26.0" rx="2" style="fill:var(--accent)"/><rect x="10.0" y="214.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="25.0" y="235.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">−</text><rect x="21.0" y="249.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="44.0" y="214.0" width="21.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="54.5" y="235.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">7</text><rect x="50.5" y="249.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="69.0" y="214.0" width="21.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="79.5" y="235.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">=</text><rect x="75.5" y="249.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="94.0" y="214.0" width="30.0" height="30.0" rx="6" style="stroke:var(--ok);stroke-width:2.2;fill:none"/><text x="109.0" y="235.0" font-size="15" text-anchor="middle" style="fill:var(--ok)">29</text><rect x="105.0" y="249.0" width="8.0" height="26.0" rx="2" style="fill:var(--ok)"/><rect x="128.0" y="214.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="143.0" y="235.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">。</text><rect x="139.0" y="249.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="162.0" y="214.0" width="48.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="186.0" y="235.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">答案</text><rect x="182.0" y="249.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="214.0" y="214.0" width="30.0" height="30.0" rx="6" style="stroke:var(--line);stroke-width:1.4;fill:none"/><text x="229.0" y="235.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">是</text><rect x="225.0" y="249.0" width="8.0" height="26.0" rx="2" style="fill:var(--line)"/><rect x="248.0" y="214.0" width="30.0" height="30.0" rx="6" style="stroke:var(--ok);stroke-width:2.2;fill:none"/><text x="263.0" y="235.0" font-size="15" text-anchor="middle" style="fill:var(--ok)">29</text><rect x="259.0" y="249.0" width="8.0" height="26.0" rx="2" style="fill:var(--ok)"/>
</svg>
<figcaption>图 2　每个方框是一个生成的 token，下面的小竖条是生成它时做的一次前向计算（都是 32 层）。直接答：答案只有一次计算的机会。分步答：22 个 token，22 次计算；蓝框「36」写下来以后，后面的 token 都能读到它（切分是示意）。</figcaption>
</figure>

关键在蓝框里的「36」。生成它的那次计算只需要做一件事：$12 \times 3$。它被写出来以后，就成了输入的一部分；后面生成「29」的那次计算，可以通过注意力直接读到「36」，只需要再做一件事：$36 - 7$。

所以分步答把一个两步的问题，拆成了两个一步的问题，分在两次前向计算里做。写下的中间结果像草稿纸：算到一半的东西不用全挤在一次计算的内部，可以先写出来，后面再读。

把能串起来的计算深度算出来：

$$
22 \times 32 = 704\ \text{层}
$$

总计算量也跟着涨：$22 \times 16.1\ \text{G} \approx 353\ \text{G}$ 次浮点运算，是直接答的 22 倍。

<figure class="fig">
<svg viewBox="0 0 480 122" role="img" aria-label="直接答与分步答得到答案之前，最多能串着做多少层计算">
<text x="70.0" y="38.0" font-size="16" text-anchor="end" style="fill:var(--fg)">直接答</text><rect x="80.0" y="18.0" width="13.6" height="28.0" rx="4" style="fill:var(--warn)"/><text x="101.6" y="38.0" font-size="16" text-anchor="start" style="fill:var(--warn)">32 层</text><text x="70.0" y="90.0" font-size="16" text-anchor="end" style="fill:var(--fg)">分步答</text><rect x="80.0" y="70.0" width="300.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="388.0" y="90.0" font-size="16" text-anchor="start" style="fill:var(--accent)">704 层</text>
</svg>
<figcaption>图 3　算出最后那个「29」之前，计算最多能一层接一层串多深。直接答只有 32 层；分步答每写一个 token 就多 32 层，22 个 token 是 22 × 32 = 704 层。</figcaption>
</figure>

<details class="pause"><summary>停一下：如果不让模型写步骤，而是让它在答案之前先输出 22 个句点「……」，它也多做了 22 次前向计算。这样有用吗？</summary>

Wei 等人做过这个对照：让模型先输出一串点，点的个数等于算式的字符数，再给答案。结果和直接答差不多，没有用。

原因是句点里没有中间结果。每次前向计算确实多做了，但算出来的东西没有写下来，下一次计算读到的只是又一个「.」。思维链有用，靠的是两样东西一起：**多算**，加上**把算出来的写下来，让后面的计算接着用**。

</details>

这也解释了为什么只有大模型才吃这一套：分步答要求模型每一步都写对，小模型连「12 × 3 = 36」这样的单步都可能写错，后面越写越偏。

## 多想几条：采样，再投票

### 每次答案都可能不一样

模型生成 token 时通常是按概率抽样（温度大于 0），所以同一道题问两次，可能写出两条不同的推理、得到不同的答案。设单条推理答对的概率是 $p$。整讲假设分步答时 $p = 0.6$：问 10 次，平均 6 次得到 29。

Wang 等人（2022）提出**自洽性**（self-consistency）：同一道题采样 $k$ 条推理，看最后的答案，哪个答案出现得最多就选哪个。

### 投票答对的概率：先算 k = 3

先看最坏的情况：错的答案都错成同一个数（比如都算成 $12 \times 3 + 7 = 43$）。这样每一条只有两种结果，对或错。3 条里至少 2 条对，投票就选对。

3 条全对：三条各自独立，概率相乘：

$$
p^3 = 0.6^3 = 0.216
$$

恰好 2 条对：先选哪 2 条对，有 $\binom{3}{2} = 3$ 种选法；每种选法的概率是 $p^2(1-p)$：

$$
3\,p^2(1-p) = 3 \times 0.36 \times 0.4 = 0.432
$$

两种情况加起来：

$$
0.216 + 0.432 = 0.648
$$

只采 1 条是 60%，采 3 条投票是 64.8%。

### 一般的 k：二项分布

$k$ 条里恰好 $i$ 条答对的概率，就是上面那样数出来的：

$$
P(i) = \binom{k}{i}\, p^{i}\, (1-p)^{k-i}
$$

这叫二项分布。投票答对，就是答对的条数超过一半：

$$
P_{\text{投票}} = \sum_{i > k/2} \binom{k}{i}\, p^{i}\, (1-p)^{k-i}
$$

用 $k = 5$ 算一遍。$i$ 从 0 到 5 的六个概率是：0.0102、0.0768、0.2304、0.3456、0.2592、0.0778（六个加起来是 1）。超过一半的是 $i = 3, 4, 5$：

$$
0.3456 + 0.2592 + 0.0778 = 0.6826
$$

<figure class="fig">
<svg viewBox="0 0 480 246" role="img" aria-label="采样 5 条推理，答对条数的二项分布">
<rect x="40.0" y="185.9" width="52.0" height="4.1" rx="3" style="fill:var(--warn)"/><text x="66.0" y="177.9" font-size="15" text-anchor="middle" style="fill:var(--warn)">0.010</text><text x="66.0" y="212.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">0</text><rect x="110.0" y="158.9" width="52.0" height="31.1" rx="3" style="fill:var(--warn)"/><text x="136.0" y="150.9" font-size="15" text-anchor="middle" style="fill:var(--warn)">0.077</text><text x="136.0" y="212.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">1</text><rect x="180.0" y="96.7" width="52.0" height="93.3" rx="3" style="fill:var(--warn)"/><text x="206.0" y="88.7" font-size="15" text-anchor="middle" style="fill:var(--warn)">0.230</text><text x="206.0" y="212.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">2</text><rect x="250.0" y="50.0" width="52.0" height="140.0" rx="3" style="fill:var(--ok)"/><text x="276.0" y="42.0" font-size="15" text-anchor="middle" style="fill:var(--ok)">0.346</text><text x="276.0" y="212.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">3</text><rect x="320.0" y="85.0" width="52.0" height="105.0" rx="3" style="fill:var(--ok)"/><text x="346.0" y="77.0" font-size="15" text-anchor="middle" style="fill:var(--ok)">0.259</text><text x="346.0" y="212.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">4</text><rect x="390.0" y="158.5" width="52.0" height="31.5" rx="3" style="fill:var(--ok)"/><text x="416.0" y="150.5" font-size="15" text-anchor="middle" style="fill:var(--ok)">0.078</text><text x="416.0" y="212.0" font-size="16" text-anchor="middle" style="fill:var(--fg)">5</text><line x1="34.0" y1="190.0" x2="448.0" y2="190.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="241.0" y="236.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">5 条里答对几条</text><line x1="241.0" y1="24.0" x2="241.0" y2="190.0" style="stroke:var(--muted);stroke-width:1.2;stroke-dasharray:4 4;fill:none"/><text x="233.0" y="22.0" font-size="15" text-anchor="end" style="fill:var(--warn)">错的占多数</text><text x="249.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--ok)">对的占多数</text>
</svg>
<figcaption>图 4　单条答对的概率 <i>p</i> = 0.6，采样 5 条，答对条数的分布。绿色三根（3、4、5 条）加起来 0.683，就是投票答对的概率。</figcaption>
</figure>

继续加：9 条 73.3%，41 条 90.3%。Wang 等人用 PaLM 540B 在 GSM8K 上采样 40 条，正确率从单条的 56.5% 涨到 74.4%。

### 投票会放大多数，不管多数对不对

投票的作用是把「多数」变得更确定。如果单条答对率低于一半，多数就是错的，投得越多越错：$p = 0.4$ 时，3 条投票只有 35.2%，41 条只有 9.7%。

<figure class="fig">
<svg viewBox="0 0 480 280" role="img" aria-label="多数投票答对的概率随采样条数的变化">
<line x1="60.0" y1="230.0" x2="440.0" y2="230.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="60.0" y1="230.0" x2="60.0" y2="40.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="60.0" y1="230.0" x2="60.0" y2="235.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="60.0" y="252.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><line x1="172.4" y1="230.0" x2="172.4" y2="235.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="172.4" y="252.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">3</text><line x1="224.7" y1="230.0" x2="224.7" y2="235.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="224.7" y="252.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">5</text><line x1="284.8" y1="230.0" x2="284.8" y2="235.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="284.8" y="252.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">9</text><line x1="337.1" y1="230.0" x2="337.1" y2="235.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="337.1" y="252.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">15</text><line x1="389.4" y1="230.0" x2="389.4" y2="235.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="389.4" y="252.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">25</text><line x1="440.0" y1="230.0" x2="440.0" y2="235.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="440.0" y="252.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">41</text><line x1="55.0" y1="230.0" x2="60.0" y2="230.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="235.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.0</text><line x1="60.0" y1="230.0" x2="440.0" y2="230.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="192.0" x2="60.0" y2="192.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="197.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.2</text><line x1="60.0" y1="192.0" x2="440.0" y2="192.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="154.0" x2="60.0" y2="154.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="159.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.4</text><line x1="60.0" y1="154.0" x2="440.0" y2="154.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="116.0" x2="60.0" y2="116.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="121.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.6</text><line x1="60.0" y1="116.0" x2="440.0" y2="116.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="78.0" x2="60.0" y2="78.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="83.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.8</text><line x1="60.0" y1="78.0" x2="440.0" y2="78.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="40.0" x2="60.0" y2="40.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="45.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1.0</text><line x1="60.0" y1="40.0" x2="440.0" y2="40.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><text x="440.0" y="272.0" font-size="14" text-anchor="end" style="fill:var(--muted)">采样条数 k（对数刻度）</text><text x="56.0" y="28.0" font-size="14" text-anchor="start" style="fill:var(--muted)">投票答对的概率</text><polyline points="60.0,116.0 172.4,106.9 224.7,100.3 259.1,95.1 284.8,90.6 305.4,86.8 322.5,83.5 337.1,80.5 349.9,77.8 361.3,75.4 371.5,73.1 380.8,71.1 389.4,69.2 397.3,67.5 404.6,65.9 411.4,64.4 417.8,63.0 423.8,61.7 429.5,60.5 434.9,59.4 440.0,58.3" style="stroke:var(--ok);stroke-width:2.5;fill:none"/><circle cx="60.0" cy="116.0" r="3.5" style="fill:var(--ok)"/><circle cx="172.4" cy="106.9" r="3.5" style="fill:var(--ok)"/><circle cx="224.7" cy="100.3" r="3.5" style="fill:var(--ok)"/><circle cx="284.8" cy="90.6" r="3.5" style="fill:var(--ok)"/><circle cx="337.1" cy="80.5" r="3.5" style="fill:var(--ok)"/><circle cx="389.4" cy="69.2" r="3.5" style="fill:var(--ok)"/><circle cx="440.0" cy="58.3" r="3.5" style="fill:var(--ok)"/><text x="436.0" y="46.3" font-size="15" text-anchor="end" style="fill:var(--ok)">p = 0.6</text><polyline points="60.0,154.0 172.4,163.1 224.7,169.7 259.1,174.9 284.8,179.4 305.4,183.2 322.5,186.5 337.1,189.5 349.9,192.2 361.3,194.6 371.5,196.9 380.8,198.9 389.4,200.8 397.3,202.5 404.6,204.1 411.4,205.6 417.8,207.0 423.8,208.3 429.5,209.5 434.9,210.6 440.0,211.7" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><circle cx="60.0" cy="154.0" r="3.5" style="fill:var(--warn)"/><circle cx="172.4" cy="163.1" r="3.5" style="fill:var(--warn)"/><circle cx="224.7" cy="169.7" r="3.5" style="fill:var(--warn)"/><circle cx="284.8" cy="179.4" r="3.5" style="fill:var(--warn)"/><circle cx="337.1" cy="189.5" r="3.5" style="fill:var(--warn)"/><circle cx="389.4" cy="200.8" r="3.5" style="fill:var(--warn)"/><circle cx="440.0" cy="211.7" r="3.5" style="fill:var(--warn)"/><text x="436.0" y="199.7" font-size="15" text-anchor="end" style="fill:var(--warn)">p = 0.4</text>
</svg>
<figcaption>图 5　投票答对的概率（最坏情况：错的都错成同一个数）。单条答对率 0.6 时，越投越准，41 条到 90.3%；单条答对率 0.4 时，越投越错。</figcaption>
</figure>

所以采样投票只对模型「多数时候能做对」的题有用。

<details class="pause"><summary>停一下：p = 0.4，采 3 条。如果错的答案每次都不一样（三条里错的那些互不相同），投票答对的概率是多少？</summary>

分三种情况。

至少 2 条对：$0.4^3 + 3 \times 0.4^2 \times 0.6 = 0.064 + 0.288 = 0.352$，对的答案出现 2 次以上，一定赢。

恰好 1 条对：概率 $3 \times 0.4 \times 0.6^2 = 0.432$。另外两条错得各不相同，三个答案各出现一次，打平，随机挑一个，挑中对的概率是 $1/3$，贡献 $0.432 / 3 = 0.144$。

0 条对：投票必错。

合计 $0.352 + 0.144 = 0.496$，比单条的 0.4 高。真实的题目里，错答案通常五花八门，而对的答案只有一个，所以投票的实际效果比上面「最坏情况」好。

</details>

## 让一个打分器来挑：best-of-N 与验证器

投票只看答案出现了几次。另一种办法是请一个**验证器**（verifier）给每个回答打分，选分最高的，叫 **best-of-N**。验证器可以是另一个训练过的模型（奖励模型），也可以是程序：代码题跑测试，数学题代回去验算。

### 上限：N 个里至少有一个对

不管怎么挑，都不可能比「N 个回答里至少有一个是对的」更好。N 个全错的概率是 $(1-p)^N$，所以：

$$
P_{\text{至少一个对}} = 1 - (1-p)^N
$$

$N = 4$：$1 - 0.4^4 = 1 - 0.0256 = 0.974$，也就是 97.4%。这个上限涨得很快，比投票快得多（同样 4 条，投票只有 64.8%，因为 2 对 2 错要抛硬币）。

Brown 等人（2024）在代码修复任务 SWE-bench Lite 上测过这个上限：DeepSeek-Coder-V2 只采 1 次解决 15.9% 的问题，采 250 次时，至少有一次解决的问题达到 56%。

### 验证器不完美时

上限要靠一个完美的验证器才能拿到。现实中的验证器会被骗：有些错答案看起来很像对的。下图用一个简单的验证器模型做蒙特卡洛模拟：对的回答平均得 2 分，错的平均得 0 分，再加上随机噪声；另外，错答案里有一部分（25%）验证器分不出来，也得 2 分。

<figure class="fig">
<svg viewBox="0 0 480 336" role="img" aria-label="四种挑选方式的准确率随回答个数的变化">
<line x1="60.0" y1="236.0" x2="440.0" y2="236.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="60.0" y1="236.0" x2="60.0" y2="40.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="60.0" y1="236.0" x2="60.0" y2="241.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="60.0" y="258.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><line x1="123.3" y1="236.0" x2="123.3" y2="241.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="123.3" y="258.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2</text><line x1="186.7" y1="236.0" x2="186.7" y2="241.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="186.7" y="258.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">4</text><line x1="250.0" y1="236.0" x2="250.0" y2="241.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="250.0" y="258.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">8</text><line x1="313.3" y1="236.0" x2="313.3" y2="241.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="313.3" y="258.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">16</text><line x1="376.7" y1="236.0" x2="376.7" y2="241.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="376.7" y="258.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">32</text><line x1="440.0" y1="236.0" x2="440.0" y2="241.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="440.0" y="258.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">64</text><line x1="55.0" y1="236.0" x2="60.0" y2="236.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="241.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.5</text><line x1="60.0" y1="236.0" x2="440.0" y2="236.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="196.8" x2="60.0" y2="196.8" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="201.8" font-size="14" text-anchor="end" style="fill:var(--muted)">0.6</text><line x1="60.0" y1="196.8" x2="440.0" y2="196.8" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="157.6" x2="60.0" y2="157.6" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="162.6" font-size="14" text-anchor="end" style="fill:var(--muted)">0.7</text><line x1="60.0" y1="157.6" x2="440.0" y2="157.6" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="118.4" x2="60.0" y2="118.4" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="123.4" font-size="14" text-anchor="end" style="fill:var(--muted)">0.8</text><line x1="60.0" y1="118.4" x2="440.0" y2="118.4" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="79.2" x2="60.0" y2="79.2" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="84.2" font-size="14" text-anchor="end" style="fill:var(--muted)">0.9</text><line x1="60.0" y1="79.2" x2="440.0" y2="79.2" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><line x1="55.0" y1="40.0" x2="60.0" y2="40.0" style="stroke:var(--line);stroke-width:1.2;fill:none"/><text x="51.0" y="45.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1.0</text><line x1="60.0" y1="40.0" x2="440.0" y2="40.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><text x="440.0" y="278.0" font-size="14" text-anchor="end" style="fill:var(--muted)">回答个数 N（对数刻度）</text><text x="56.0" y="28.0" font-size="14" text-anchor="start" style="fill:var(--muted)">最后选中的答案是对的</text><polyline points="60.0,196.8 123.3,102.7 186.7,50.0 250.0,40.3 313.3,40.0 376.7,40.0 440.0,40.0" style="stroke:var(--muted);stroke-width:2.5;stroke-dasharray:4 5;fill:none"/><circle cx="60.0" cy="196.8" r="3.2" style="fill:var(--muted)"/><circle cx="123.3" cy="102.7" r="3.2" style="fill:var(--muted)"/><circle cx="186.7" cy="50.0" r="3.2" style="fill:var(--muted)"/><circle cx="250.0" cy="40.3" r="3.2" style="fill:var(--muted)"/><circle cx="313.3" cy="40.0" r="3.2" style="fill:var(--muted)"/><circle cx="376.7" cy="40.0" r="3.2" style="fill:var(--muted)"/><circle cx="440.0" cy="40.0" r="3.2" style="fill:var(--muted)"/><polyline points="60.0,196.9 123.3,117.5 186.7,68.4 250.0,48.8 313.3,43.2 376.7,41.4 440.0,40.7" style="stroke:var(--ok);stroke-width:2.5;fill:none"/><circle cx="60.0" cy="196.9" r="3.2" style="fill:var(--ok)"/><circle cx="123.3" cy="117.5" r="3.2" style="fill:var(--ok)"/><circle cx="186.7" cy="68.4" r="3.2" style="fill:var(--ok)"/><circle cx="250.0" cy="48.8" r="3.2" style="fill:var(--ok)"/><circle cx="313.3" cy="43.2" r="3.2" style="fill:var(--ok)"/><circle cx="376.7" cy="41.4" r="3.2" style="fill:var(--ok)"/><circle cx="440.0" cy="40.7" r="3.2" style="fill:var(--ok)"/><polyline points="60.0,196.2 123.3,137.6 186.7,107.9 250.0,99.4 313.3,97.1 376.7,96.7 440.0,96.2" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><circle cx="60.0" cy="196.2" r="3.2" style="fill:var(--accent)"/><circle cx="123.3" cy="137.6" r="3.2" style="fill:var(--accent)"/><circle cx="186.7" cy="107.9" r="3.2" style="fill:var(--accent)"/><circle cx="250.0" cy="99.4" r="3.2" style="fill:var(--accent)"/><circle cx="313.3" cy="97.1" r="3.2" style="fill:var(--accent)"/><circle cx="376.7" cy="96.7" r="3.2" style="fill:var(--accent)"/><circle cx="440.0" cy="96.2" r="3.2" style="fill:var(--accent)"/><polyline points="60.0,196.8 123.3,196.8 186.7,178.0 250.0,153.6 313.3,123.5 376.7,90.3 440.0,61.0" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><circle cx="60.0" cy="196.8" r="3.2" style="fill:var(--warn)"/><circle cx="123.3" cy="196.8" r="3.2" style="fill:var(--warn)"/><circle cx="186.7" cy="178.0" r="3.2" style="fill:var(--warn)"/><circle cx="250.0" cy="153.6" r="3.2" style="fill:var(--warn)"/><circle cx="313.3" cy="123.5" r="3.2" style="fill:var(--warn)"/><circle cx="376.7" cy="90.3" r="3.2" style="fill:var(--warn)"/><circle cx="440.0" cy="61.0" r="3.2" style="fill:var(--warn)"/><line x1="20.0" y1="300.0" x2="42.0" y2="300.0" style="stroke:var(--muted);stroke-width:3;stroke-dasharray:4 5;fill:none"/><text x="50.0" y="305.0" font-size="14" text-anchor="start" style="fill:var(--muted)">有一个对就算（上限）</text><line x1="250.0" y1="300.0" x2="272.0" y2="300.0" style="stroke:var(--ok);stroke-width:3;fill:none"/><text x="280.0" y="305.0" font-size="14" text-anchor="start" style="fill:var(--ok)">验证器 · 不被骗</text><line x1="20.0" y1="324.0" x2="42.0" y2="324.0" style="stroke:var(--accent);stroke-width:3;fill:none"/><text x="50.0" y="329.0" font-size="14" text-anchor="start" style="fill:var(--accent)">验证器 · 被骗 25%</text><line x1="250.0" y1="324.0" x2="272.0" y2="324.0" style="stroke:var(--warn);stroke-width:3;fill:none"/><text x="280.0" y="329.0" font-size="14" text-anchor="start" style="fill:var(--warn)">多数投票</text>
</svg>
<figcaption>图 6　单个回答答对率 0.6。虚线是「N 个里至少有一个对」，任何挑法都不可能超过它。验证器不被骗时（绿）贴着上限走；有 25% 的错答案能骗过它时（蓝），停在 85.7% 附近上不去。验证器的结果是蒙特卡洛模拟（每点 20 万次）。</figcaption>
</figure>

看蓝线：$N = 8$ 时到了 84.8%，之后几乎不动，$N = 64$ 还是 85.7%。原因是：回答越多，混进「骗过验证器的错答案」的机会也越多。$N$ 很大时，分最高的那一堆里，对的和骗过验证器的错的，比例固定在：

$$
\begin{aligned}
&\frac{p}{p + (1-p) \times 0.25} \\
&= \frac{0.6}{0.6 + 0.1} = 0.857
\end{aligned}
$$

这和 Brown 等人的观察一致：在没有自动验证（不能跑测试、不能核对答案）的任务上，用奖励模型挑或者投票，采样到几百个之后就不再涨了。再看橙线：$N$ 很大时，连最朴素的多数投票（94.6%）都超过了这个会被骗的验证器。**多采样的收益，取决于你能不能认出对的那个。**

OpenAI 介绍 o1 时（2024）给过一组数：AIME 2024（美国数学邀请赛，15 道题）上，o1 每题只答一次平均对 74%，64 次投票 83%，用一个学出来的打分函数在 1000 次里挑是 93%。

## 同样的预算：更大的模型，还是多想一会儿

### 只算推理的钱

上面所有办法都在用推理时的算力换准确率，叫**测试时计算**（test-time compute）。换一个角度问：同样的钱，是买一个更大的模型答一次，还是用小模型多答几次？

生成一个 token 的计算量约是 $2N$。假设大模型的参数是小模型的 14 倍，它生成一个 token 的钱，够小模型生成 14 个。所以「大模型答 1 次」的预算，可以换「小模型答 14 次再投票」。

下面是一个示意模型：两道题，小模型和大模型各有一个单次答对率，准确率用上一节的二项分布真算。

<figure class="fig">
<svg viewBox="0 0 480 336" role="img" aria-label="同样的推理预算下，大模型与小模型多数投票的准确率">
<text x="40.0" y="22.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">容易的题</text><line x1="40.0" y1="226.0" x2="210.0" y2="226.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="40.0" y1="226.0" x2="40.0" y2="56.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="33.0" y="231.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.0</text><line x1="40.0" y1="226.0" x2="210.0" y2="226.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><text x="33.0" y="146.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.5</text><line x1="40.0" y1="141.0" x2="210.0" y2="141.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><text x="33.0" y="61.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1.0</text><line x1="40.0" y1="56.0" x2="210.0" y2="56.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><text x="40.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><text x="74.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2</text><text x="108.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">3</text><text x="142.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">4</text><text x="176.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">5</text><text x="210.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">6</text><polyline points="40.0,94.9 74.0,80.6 108.0,72.4 142.0,67.2 176.0,63.8 210.0,61.5" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><polyline points="40.0,98.5 74.0,98.5 108.0,82.6 142.0,82.6 176.0,73.6 210.0,73.6" style="stroke:var(--fg);stroke-width:2.5;stroke-dasharray:6 4;fill:none"/><circle cx="40.0" cy="94.9" r="3.2" style="fill:var(--accent)"/><circle cx="74.0" cy="80.6" r="3.2" style="fill:var(--accent)"/><circle cx="108.0" cy="72.4" r="3.2" style="fill:var(--accent)"/><circle cx="142.0" cy="67.2" r="3.2" style="fill:var(--accent)"/><circle cx="176.0" cy="63.8" r="3.2" style="fill:var(--accent)"/><circle cx="210.0" cy="61.5" r="3.2" style="fill:var(--accent)"/><circle cx="40.0" cy="98.5" r="3.2" style="fill:var(--fg)"/><circle cx="74.0" cy="98.5" r="3.2" style="fill:var(--fg)"/><circle cx="108.0" cy="82.6" r="3.2" style="fill:var(--fg)"/><circle cx="142.0" cy="82.6" r="3.2" style="fill:var(--fg)"/><circle cx="176.0" cy="73.6" r="3.2" style="fill:var(--fg)"/><circle cx="210.0" cy="73.6" r="3.2" style="fill:var(--fg)"/><text x="280.0" y="22.0" font-size="16" text-anchor="start" font-weight="600" style="fill:var(--fg)">难的题</text><line x1="280.0" y1="226.0" x2="450.0" y2="226.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="280.0" y1="226.0" x2="280.0" y2="56.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="273.0" y="231.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.0</text><line x1="280.0" y1="226.0" x2="450.0" y2="226.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><text x="273.0" y="146.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.5</text><line x1="280.0" y1="141.0" x2="450.0" y2="141.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><text x="273.0" y="61.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1.0</text><line x1="280.0" y1="56.0" x2="450.0" y2="56.0" style="stroke:var(--line);stroke-width:0.6;stroke-dasharray:2 5;fill:none"/><text x="280.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><text x="314.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2</text><text x="348.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">3</text><text x="382.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">4</text><text x="416.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">5</text><text x="450.0" y="246.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">6</text><polyline points="280.0,204.0 314.0,216.9 348.0,221.9 382.0,224.1 416.0,225.1 450.0,225.6" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><polyline points="280.0,124.0 314.0,124.0 348.0,115.8 382.0,115.8 416.0,110.0 450.0,110.0" style="stroke:var(--fg);stroke-width:2.5;stroke-dasharray:6 4;fill:none"/><circle cx="280.0" cy="204.0" r="3.2" style="fill:var(--accent)"/><circle cx="314.0" cy="216.9" r="3.2" style="fill:var(--accent)"/><circle cx="348.0" cy="221.9" r="3.2" style="fill:var(--accent)"/><circle cx="382.0" cy="224.1" r="3.2" style="fill:var(--accent)"/><circle cx="416.0" cy="225.1" r="3.2" style="fill:var(--accent)"/><circle cx="450.0" cy="225.6" r="3.2" style="fill:var(--accent)"/><circle cx="280.0" cy="124.0" r="3.2" style="fill:var(--fg)"/><circle cx="314.0" cy="124.0" r="3.2" style="fill:var(--fg)"/><circle cx="348.0" cy="115.8" r="3.2" style="fill:var(--fg)"/><circle cx="382.0" cy="115.8" r="3.2" style="fill:var(--fg)"/><circle cx="416.0" cy="110.0" r="3.2" style="fill:var(--fg)"/><circle cx="450.0" cy="110.0" r="3.2" style="fill:var(--fg)"/><text x="240.0" y="270.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">预算：够大模型答几次</text><line x1="40.0" y1="296.0" x2="62.0" y2="296.0" style="stroke:var(--accent);stroke-width:3;fill:none"/><text x="70.0" y="301.0" font-size="14" text-anchor="start" style="fill:var(--accent)">小模型 · 同样的钱答 14 倍的次数，投票</text><line x1="40.0" y1="320.0" x2="62.0" y2="320.0" style="stroke:var(--fg);stroke-width:2.5;stroke-dasharray:6 4;fill:none"/><text x="70.0" y="325.0" font-size="14" text-anchor="start" style="fill:var(--fg)">大模型 · 参数多 14 倍</text>
</svg>
<figcaption>图 7　示意模型：两道题上小模型、大模型单次答对率分别是 0.6 / 0.75（容易）和 0.35 / 0.6（难），准确率用二项分布真算。容易的题，把钱花在小模型多答几次上更划算；难的题，小模型单次答对率不到一半，投票越投越错，钱该花在大模型上。</figcaption>
</figure>

读数：

- 容易的题（小模型单次 0.6，大模型 0.75）：预算够大模型答 1 次时，小模型投票 77.1%，大模型 75.0%；够答 3 次时，90.3% 对 84.4%。小模型多想更划算。
- 难的题（小模型 0.35，大模型 0.6）：小模型单次答对率不到一半，投票越投越错，从 12.9% 掉到 2.4%；大模型 60.0%、64.8%。这时只能靠更大的模型。

### 把训练的钱也算进去

Snell 等人（2024）做了更完整的比较：把预训练的计算也算进去。设小模型参数 $N$，大模型 $MN$，两个都用 $D_{\text{pre}}$ 个 token 预训练；推理一个 token 约 $2N$（只有前向）；训练一个 token 约 $6N$（前向 $2N$，反向传播算梯度约是前向的两倍，$4N$）。大模型一生要推理 $D_{\text{inf}}$ 个 token，问：总计算量相同的前提下，小模型可以多推理多少倍（记作 $k$）？

大模型的总计算量是预训练加推理：

$$
6MN\,D_{\text{pre}} + 2MN\,D_{\text{inf}}
$$

小模型推理 $k$ 倍的 token：

$$
6N\,D_{\text{pre}} + 2N\,k\,D_{\text{inf}}
$$

令两者相等，两边同除以 $2N\,D_{\text{inf}}$：

$$
3M\,\frac{D_{\text{pre}}}{D_{\text{inf}}} + M = 3\,\frac{D_{\text{pre}}}{D_{\text{inf}}} + k
$$

把 $k$ 留在一边：

$$
k = M + 3\,(M-1)\,\frac{D_{\text{pre}}}{D_{\text{inf}}}
$$

第一项 $M$ 是推理时每个 token 的价差；第二项是大模型多花的预训练费，摊到每次推理上。代入 $M = 14$，记 $R = D_{\text{inf}} / D_{\text{pre}}$（这个模型一生推理的 token 数是预训练 token 数的几倍）：

- $R = 1$：$k = 14 + 3 \times 13 \times 1 = 53$
- $R = 22$（模型被大量使用）：$k = 14 + 39 / 22 \approx 15.8$
- $R = 0.16$（模型用得少）：$k = 14 + 39 / 0.16 \approx 258$

他们在 MATH 数据集上实验的结论，和上面的示意图一致：

- 容易和中等难度的题，在推理量不大时，把算力花在小模型多想上，可以赢过参数多约 14 倍的模型。
- 最难的题，以及推理量很大（$R \gg 1$，每次推理分到的预训练费很少）时，预训练一个更大的模型更有效。
- 按题目难度选择怎么花推理算力（多采样、逐步修改、用验证器搜索），比一律 best-of-N 省约 4 倍算力。

两种算力不能完全互相替代：**多想只能把模型本来就有可能做对的题做得更稳，做不到它能力之外的题。**

<details class="pause"><summary>停一下：一个模型发布后被几亿人天天用，它推理的 token 比预训练的多得多。按上面的公式，这时多想划算还是换大模型划算？</summary>

用得越多，$R = D_{\text{inf}} / D_{\text{pre}}$ 越大，公式的第二项 $3(M-1)/R$ 越小，$k$ 越接近 $M = 14$。也就是说，大模型的预训练费被摊薄了，小模型能多想的倍数只剩每个 token 的价差。这时只要题目不太简单，花钱在更大的模型上更合适。反过来，一个只在少数场合用的模型，$k$ 可以到几百，多想更划算。

</details>

## 推理模型是怎么训出来的

### 从「提示它多想」到「训练它多想」

思维链提示是在用法上做文章：模型本身没变，靠例题或一句话引导它写步骤。2024 年 9 月 OpenAI 发布 o1，2025 年 1 月 DeepSeek 发布 R1，这类模型叫**推理模型**：它们在回答之前，会先生成一段很长的思考（几百到几万个 token），然后才给出答案。这个习惯是训练出来的。OpenAI 介绍 o1 时说，它的表现随强化学习的训练算力和推理时的思考算力，两条都平稳上涨。

训练方法就是后训练那一讲第五步讲的**可验证奖励的强化学习**（RLVR）和 **GRPO**：给模型有标准答案的题，让它自己写一组回答，程序判对错，组内比平均好的回答被加强。那一讲已经手算过一步 GRPO，这里不重复，只看一个新问题：**为什么这样训练，回答会越来越长？**

### R1-Zero：只奖励答对，模型自己学会了想更久

DeepSeek-R1 报告里的 R1-Zero 是最干净的实验：直接在基座模型 DeepSeek-V3-Base 上做 GRPO，不先做 SFT。提示模板只要求一件事：先把思考过程写在 `<think>` 和 `</think>` 之间，再把答案写在 `<answer>` 和 `</answer>` 之间。奖励只有两项，都由规则判定：

- **答对奖励**：数学题核对最终答案，代码题跑测试用例。
- **格式奖励**：思考和答案是否放在了规定的标签里。

奖励里没有一个字要求「想得长」或「要验算」。他们特意不用神经网络奖励模型，理由是大规模强化学习时它容易被钻空子（RLHF 那一讲的奖励黑客）。

训练过程中发生了两件事：

1. AIME 2024 的 pass@1（每题答一次的正确率）从 15.6% 涨到 71.0%；每题采 64 次投票，到 86.7%（论文后来的修订版训练更久，pass@1 到 77.9%）。
2. 平均回答长度一路上涨，从几百个 token 涨到几千个。模型自己学会了花更多的 token 去想。

### 为什么会变长：GRPO 一组里的账

用我们的苹果题，看一组 4 个回答。其中两个是「短回答」：算完直接交卷；另外两个是「长回答」：算完又把 $29 + 7 = 36$、$36 \div 3 = 12$ 验算一遍，发现不对就改。假设这一组的结果是：短的一对一错，长的两个都对。

奖励 $r = (1, 0, 1, 1)$，平均：

$$
\bar r = \frac{1 + 0 + 1 + 1}{4} = 0.75
$$

偏差是 $0.25,\ -0.75,\ 0.25,\ 0.25$，平方是 $0.0625,\ 0.5625,\ 0.0625,\ 0.0625$，平均 $0.75 / 4 = 0.1875$，开根号得标准差：

$$
\sigma = \sqrt{0.1875} \approx 0.433
$$

优势 $A_i = (r_i - \bar r)/\sigma$：答对的三个都是 $0.25 / 0.433 \approx +0.577$，答错的那个是 $-0.75 / 0.433 \approx -1.732$。

<figure class="fig">
<svg viewBox="0 0 480 254" role="img" aria-label="同一道题的四个回答，两个短的、两个长的，各自的奖励与优势">
<text x="14.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">回答</text><text x="150.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">奖励</text><text x="250.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">优势 A</text><rect x="10.0" y="40.0" width="70.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="45.0" y="62.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">短：对</text><text x="162.0" y="62.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--ok)">1</text><rect x="340.0" y="46.0" width="23.1" height="20.0" rx="3" style="fill:var(--ok)"/><text x="369.1" y="62.0" font-size="15" text-anchor="start" style="fill:var(--ok)">+0.577</text><rect x="10.0" y="84.0" width="70.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="45.0" y="106.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">短：错</text><text x="162.0" y="106.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--warn)">0</text><rect x="270.7" y="90.0" width="69.3" height="20.0" rx="3" style="fill:var(--warn)"/><text x="264.7" y="106.0" font-size="15" text-anchor="end" style="fill:var(--warn)">−1.732</text><rect x="10.0" y="128.0" width="120.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="70.0" y="150.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">长：对</text><text x="162.0" y="150.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--ok)">1</text><rect x="340.0" y="134.0" width="23.1" height="20.0" rx="3" style="fill:var(--ok)"/><text x="369.1" y="150.0" font-size="15" text-anchor="start" style="fill:var(--ok)">+0.577</text><rect x="10.0" y="172.0" width="120.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="70.0" y="194.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">长：对</text><text x="162.0" y="194.0" font-size="16" text-anchor="middle" font-weight="600" style="fill:var(--ok)">1</text><rect x="340.0" y="178.0" width="23.1" height="20.0" rx="3" style="fill:var(--ok)"/><text x="369.1" y="194.0" font-size="15" text-anchor="start" style="fill:var(--ok)">+0.577</text><line x1="340.0" y1="36.0" x2="340.0" y2="216.0" style="stroke:var(--muted);stroke-width:1.2;fill:none"/><text x="14.0" y="242.0" font-size="15" text-anchor="start" style="fill:var(--fg)">短回答优势合计 −1.155　长回答优势合计 +1.155</text>
</svg>
<figcaption>图 8　同一道题采样 4 个回答：两个没检查就交卷的短回答（一对一错），两个算完又验算一遍的长回答（都对）。按组内平均算优势：长回答合计为正，被加强；短回答合计为负，被削弱。奖励里没有一个字提到长度。</figcaption>
</figure>

按风格加起来：两个长回答的优势合计 $+1.155$，两个短回答合计 $+0.577 - 1.732 = -1.155$。GRPO 按优势调概率（后训练那一讲推过：每个回答的优势记到它自己身上），所以「算完再验算」这种写法整体被加强，「直接交卷」整体被削弱。

只要多想一会儿平均更容易答对，这笔账在成千上万道题上反复算，回答就会越来越长。长度不是目标，是**答对**这个目标的副产品。也正因为如此，到了多想也不再多对的地方（比如题已经稳稳做对了），长度就没有理由继续涨；实验 06 可以看到这一点。

### 「aha moment」

R1 报告里记录了一个现象：训练到中途，模型在一道方程题的思考里突然写道「Wait, wait. Wait. That's an aha moment I can flag here.」（等等，等等。这是一个值得标出来的顿悟时刻），然后回头重新检查前面的推导。作者把它叫作「aha moment」：没有人教模型「回头检查」，它在只奖励答对的强化学习里自己学会了停下来反思。论文后来的修订版补充说，这个时刻伴随着思考里「wait」这个词出现次数的突然上升。

要冷静地看这个现象：它是一段被挑出来展示的输出，说明了「反思」这种写法被强化了，不代表模型有了人一样的顿悟。但它确实说明，验算、换思路这些行为，可以从「答对给分」里自己长出来。

### R1-Zero 的毛病，和 R1 的补法

R1-Zero 的思考过程很难读：中英文混在一起，格式乱。原因也在奖励上：奖励只看最终答案，不管思考写得好不好读。

正式版 DeepSeek-R1 的做法（后训练那一讲图 7 的流水线）：先用几千条格式好的长推理示范做一次 SFT（冷启动），再做强化学习，并加了一项「语言一致性」奖励（思考里目标语言的词占的比例）；然后用强化学习后的模型生成大量推理数据，筛选后重新 SFT，最后再做一轮覆盖各类问题的强化学习。

<details class="pause"><summary>停一下：如果一组 4 个回答全都答对了，不管长短，GRPO 会让回答变长吗？</summary>

不会。全对时奖励是 $(1, 1, 1, 1)$，平均是 1，每个回答减去平均都是 0，优势全是 0，这一组什么也不改（后训练那一讲讲过：全对、全错的组没有学习信号）。只有当长短两种写法的对错有差别时，长度才会被推动。所以太简单的题不会把模型训得更啰嗦，太难的题（全错）也不会。

</details>

## 代价：思考 token 也要算钱、算时间

### 算一笔账

思考 token 也是模型生成的 token，和回答 token 一样按**输出 token** 计费，一样要一个一个生成。各家 API 都是这样（见下一节）。即使思考内容不返回给你，也照样计费。

用苹果题算三种答法。假设输出价格是每百万 token \$10、生成速度每秒 100 个 token（示意，实验 04 可以改），只算输出 token：

| 答法 | 输出 token | 每次费用 | 等待时间 | 每天一百万次 |
| --- | --- | --- | --- | --- |
| 直接答 | 3 | \$0.000030 | 0.03 s | \$30 |
| 分步答 | 22 | \$0.00022 | 0.22 s | \$220 |
| 推理模型 | 845 | \$0.00845 | 8.45 s | \$8,450 |

845 来自 Chen 等人（2024）的测量：DeepSeek-R1 在 ASDIV（一套小学数学应用题）上平均每个回答 845 个 token。

计算方法以推理模型为例：每次费用是 $845 \times 10 / 10^6 = 0.00845$ 美元；等待时间是 $845 / 100 = 8.45$ s。单次看很便宜，但它是直接答的 282 倍。每天一百万次请求，就是每天 \$8,450 对 \$30。

<figure class="fig">
<svg viewBox="0 0 480 178" role="img" aria-label="直接答、分步答与推理模型的输出 token 数和等待时间">
<text x="80.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">输出 token</text><text x="300.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">等待时间</text><text x="70.0" y="60.0" font-size="16" text-anchor="end" style="fill:var(--fg)">直接答</text><rect x="80.0" y="40.0" width="26.1" height="28.0" rx="4" style="fill:var(--line)"/><text x="112.1" y="60.0" font-size="15" text-anchor="start" style="fill:var(--fg)">3</text><rect x="300.0" y="40.0" width="19.6" height="28.0" rx="4" style="fill:var(--accent)"/><text x="325.6" y="60.0" font-size="15" text-anchor="start" style="fill:var(--fg)">0.03 s</text><text x="70.0" y="106.0" font-size="16" text-anchor="end" style="fill:var(--fg)">分步答</text><rect x="80.0" y="86.0" width="73.4" height="28.0" rx="4" style="fill:var(--line)"/><text x="159.4" y="106.0" font-size="15" text-anchor="start" style="fill:var(--fg)">22</text><rect x="300.0" y="86.0" width="55.0" height="28.0" rx="4" style="fill:var(--accent)"/><text x="361.0" y="106.0" font-size="15" text-anchor="start" style="fill:var(--fg)">0.22 s</text><text x="70.0" y="152.0" font-size="16" text-anchor="end" style="fill:var(--fg)">推理模型</text><rect x="80.0" y="132.0" width="160.0" height="28.0" rx="4" style="fill:var(--muted)"/><text x="246.0" y="152.0" font-size="15" text-anchor="start" style="fill:var(--fg)">845</text><rect x="300.0" y="132.0" width="120.0" height="28.0" rx="4" style="fill:var(--warn)"/><text x="426.0" y="152.0" font-size="15" text-anchor="start" style="fill:var(--fg)">8.45 s</text>
</svg>
<figcaption>图 9　同一道苹果题三种答法要生成的 token 数，以及按每秒 100 个 token 生成要等多久（对数刻度）。845 是 DeepSeek-R1 在一套小学应用题上平均每个回答的长度。</figcaption>
</figure>

还有两个容易忽略的代价：

- **占上下文。** 思考 token 和其他 token 一样占上下文窗口（见上下文窗口那一讲）。OpenAI 的文档建议，刚开始用推理模型时，给输出上限至少留 25,000 个 token；如果思考把上限用完了，请求会以「未完成」结束，思考的钱付了，却一个字的答案也没拿到。
- **等得久。** 用户盯着屏幕时，多等 8 秒是很明显的。流式输出（流式输出那一讲）能先显示一部分，但思考没结束之前，答案出不来。

### 想太多：2 + 3 = ?

Chen 等人（2024）专门研究了推理模型「想太多」：问「2 加 3 等于几」，QwQ-32B-Preview 在思考里给出了 13 遍解法；这类模型在这道题上用的 token，比普通模型多 1953%。他们统计了很多题：超过 92% 的情况下，第一遍解法就已经是对的，后面的几遍大多只是重复确认。

### 什么时候不值得让模型多想

把前面几节串起来：

- **一步就能做完的事**：查一个事实、翻译一句话、分类、提取字段、闲聊。不存在需要拆开的中间步骤，多想只是花钱。
- **模型怎么想都做不对的事**：知识不在模型里，或者题目超出它的能力。投票会越投越错，验算也验不出来；该换更大的模型、给它查资料的工具（RAG 那一讲），或者换人做。
- **对延迟敏感的场景**：自动补全、实时对话里的短回复。
- **没法认出对答案的场景**：多采样、best-of-N 的收益取决于验证器；没有可靠的验证办法时，采样几百个也停在原地。

值得多想的，是那些需要好几步、每一步模型大概率能做对、最好还能检查对错的任务：数学、写代码改 bug、多步规划。

## 现状：各家 API 里的「思考预算」

以下按各家官方文档整理，**核实日期 2026-10-22**。参数名和可选档位变得很快，用之前以文档为准。

| 平台 | 怎么控制想多少 | 思考内容 | 计费 |
| --- | --- | --- | --- |
| OpenAI | `reasoning.effort`：`none` / `minimal` / `low` / `medium` / `high` / `xhigh` / `max`，每个模型支持其中几档，多数默认 `medium` | 不返回原文 | 按输出 token |
| Anthropic（Claude） | 自适应思考 `thinking: {type: "adaptive"}`，模型自己判断要不要想、想多少；用 `output_config.effort` 设 `low` / `medium` / `high` / `xhigh` / `max`。旧模型用 `budget_tokens` 直接给 token 上限 | 返回摘要，或不返回 | 按完整的思考 token，算输出 |
| Google（Gemini） | `thinking_level`：`minimal` / `low` / `medium` / `high`，各模型支持的档位和默认值不同 | 默认不返回，可开摘要 | 思考 token 按输出计 |
| DeepSeek | `thinking: {type: "enabled"}` 开关（默认开）；`reasoning_effort`：`low` / `high` / `max`（默认 `high`） | 在 `reasoning_content` 字段返回 | — |
| 阿里云百炼（通义千问等） | `enable_thinking` 开关；`thinking_budget` 直接给思考 token 上限 | 在 `reasoning_content` 字段返回 | 思考内容按输出计 |

可以看出一个趋势：早期是直接给一个 token 数（「最多想 8,000 个 token」），现在多数平台改成几个**档位**，甚至让模型自己判断这道题要不要想。原因正是上一节：同一个应用里，大部分请求不值得多想，少数请求值得想很久，一个固定的 token 数照顾不到两头。

用的时候的经验法则：先用低档位或关掉思考，把任务跑一遍，统计哪些题答错；只对答错的那类题提高档位，同时盯着平均输出 token 和延迟。

## 实验里讲了什么

1. **直接答与分步答（示意）**：一个玩具模型，每次前向计算最多做一步运算。改题目的步数，看直接答在哪里开始只能猜，分步答用了几次计算、写下了哪些中间结果。
2. **多数投票计算器**：拖单条答对率 $p$ 和采样条数 $k$，二项分布真算答对条数的分布和投票正确率；可以切换「错答案都相同」和「错答案各不相同」。
3. **best-of-N 与有噪声的验证器**：拖回答个数、验证器的区分度和被骗比例，蒙特卡洛模拟准确率，和「至少一个对」的上限、多数投票对照；也可以抽一组看验证器挑中了哪个。
4. **思考的成本**：输入思考 token 数、回答 token 数、价格、生成速度和每天请求数，算每次费用、每天费用和等待时间。
5. **固定预算下的取舍（示意）**：设大小模型的参数比和各自的单次答对率，在同样的推理预算下，比较「大模型答几次」和「小模型答很多次再投票」。
6. **强化学习让思考变长（示意）**：五档思考长度、越长越容易答对但收益递减，用 GRPO 训练（每点一次 50 步），看平均长度和正确率怎么变；可以加长度惩罚，也可以换成容易或很难的题。

## 和前后两讲的关系

后训练那一讲讲了 RLVR 和 GRPO 的一步怎么算；RLHF 那一讲讲了偏好对齐和奖励黑客，并预告了推理模型用的正是可验证奖励。这一讲把两件事接起来：推理模型就是把「让模型写出中间步骤」这个提示技巧，用可验证奖励的强化学习训练成了习惯。下一讲讲模型评测：推理模型的分数常常是在「每题采 64 次投票」或「pass@k」下报告的，看分数时要先问清楚它花了多少测试时计算，这一讲的二项分布和 best-of-N 正好用得上。

## 延伸阅读

- Jason Wei et al., *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models* (2022)，思维链提示，表 1 与图 5 的对照实验
- Takeshi Kojima et al., *Large Language Models are Zero-Shot Reasoners* (2022)，「Let's think step by step」
- Xuezhi Wang et al., *Self-Consistency Improves Chain of Thought Reasoning in Language Models* (2022)，采样投票
- Bradley Brown et al., *Large Language Monkeys: Scaling Inference Compute with Repeated Sampling* (2024)，覆盖率随采样数上涨与验证器的瓶颈
- Charlie Snell et al., *Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters* (2024)，测试时计算与参数量的取舍
- OpenAI, *Learning to Reason with LLMs* (2024)，o1 的介绍
- DeepSeek-AI, *DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning* (2025)，R1-Zero、aha moment 与 R1 的流水线
- Xingyu Chen et al., *Do NOT Think That Much for 2+3=? On the Overthinking of o1-Like LLMs* (2024)，想太多
