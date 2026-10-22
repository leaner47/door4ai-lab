---
title: "预训练是什么：模型是怎么从一大堆文字里学会说话的"
description: "预训练只让模型做一件事：给前文，猜下一个 token。用一句「我爱吃米饭。」一步步算清楚：一句话拆出几个训练样本、因果遮罩怎么让它们一次算完、交叉熵为什么是 −ln p、一个训练步怎样把前面几讲拼成一条线；再看数据怎么清洗、去重、配比，学习率为什么先预热再衰减，最后在页内真的训一个中文小模型。"
pubDate: 2026-10-22
tags: ["训练", "预训练", "交叉熵", "数据", "学习率"]
lab: /labs/pretraining/
series: ai-mastery
order: 37
---

<!-- 本文由 labs-src/pretraining/toy.py 从 article.src.md 生成，图和数字都由脚本算出。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

预训练只让模型做一件事：**给它一段文字的前半截，让它猜下一个 token**。猜的结果是一组概率，正确的那个 token 概率越高越好；把「越高越好」写成一个要往下压的数，就是交叉熵损失 $-\ln p$。准备几万亿个 token 的文字（网页、代码、书、多种语言，清洗、去重、按比例混好），一批一批喂进去：前向算概率，算交叉熵，反向传播算梯度，优化器更新参数，重复上百万步。为了猜得准，模型不得不学会语法、记住事实、摸到一点推理的门道。但它学会的始终是「接着写」，变成会回答问题的助手是后训练的事。

下面用一句话「我爱吃米饭。」从头算到尾。这句话和它的数字会一直用到最后。

## 第一步：一句话能拆出多少个训练样本

先把问题缩到最小。词表只有 7 个 token，每个汉字和句号各算一个：

$$
\text{我}\quad \text{爱}\quad \text{吃}\quad \text{米}\quad \text{饭}\quad \text{粥}\quad \text{。}
$$

（真实模型的词表有十几万个 token，Token 那一讲讲过；这里只是为了能把每个数都写出来。）

「我爱吃米饭。」是 6 个 token。预训练的题目是「读前面，猜下一个」，所以这句话里藏着 5 道题：读「我」猜「爱」，读「我爱」猜「吃」，读「我爱吃」猜「米」，读「我爱吃米」猜「饭」，读「我爱吃米饭」猜「。」。

<figure class="fig">
<svg viewBox="0 0 480 218" role="img" aria-label="一句话拆成五个训练样本">
<text x="20.0" y="30.0" font-size="15" text-anchor="start" style="fill:var(--muted)">样本 1</text><rect x="90.0" y="8.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="107.0" y="30.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">我</text><rect x="130.0" y="8.0" width="34.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><text x="147.0" y="30.0" font-size="17" text-anchor="middle" font-weight="600" style="fill:var(--accent)">爱</text><text x="176.0" y="30.0" font-size="15" text-anchor="start" style="fill:var(--muted)">猜第 2 个</text><text x="20.0" y="72.0" font-size="15" text-anchor="start" style="fill:var(--muted)">样本 2</text><rect x="90.0" y="50.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="107.0" y="72.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">我</text><rect x="130.0" y="50.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="147.0" y="72.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">爱</text><rect x="170.0" y="50.0" width="34.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><text x="187.0" y="72.0" font-size="17" text-anchor="middle" font-weight="600" style="fill:var(--accent)">吃</text><text x="216.0" y="72.0" font-size="15" text-anchor="start" style="fill:var(--muted)">猜第 3 个</text><text x="20.0" y="114.0" font-size="15" text-anchor="start" style="fill:var(--muted)">样本 3</text><rect x="90.0" y="92.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="107.0" y="114.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">我</text><rect x="130.0" y="92.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="147.0" y="114.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">爱</text><rect x="170.0" y="92.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="187.0" y="114.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">吃</text><rect x="210.0" y="92.0" width="34.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><text x="227.0" y="114.0" font-size="17" text-anchor="middle" font-weight="600" style="fill:var(--accent)">米</text><text x="256.0" y="114.0" font-size="15" text-anchor="start" style="fill:var(--muted)">猜第 4 个</text><text x="20.0" y="156.0" font-size="15" text-anchor="start" style="fill:var(--muted)">样本 4</text><rect x="90.0" y="134.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="107.0" y="156.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">我</text><rect x="130.0" y="134.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="147.0" y="156.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">爱</text><rect x="170.0" y="134.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="187.0" y="156.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">吃</text><rect x="210.0" y="134.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="227.0" y="156.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">米</text><rect x="250.0" y="134.0" width="34.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><text x="267.0" y="156.0" font-size="17" text-anchor="middle" font-weight="600" style="fill:var(--accent)">饭</text><text x="296.0" y="156.0" font-size="15" text-anchor="start" style="fill:var(--muted)">猜第 5 个</text><text x="20.0" y="198.0" font-size="15" text-anchor="start" style="fill:var(--muted)">样本 5</text><rect x="90.0" y="176.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="107.0" y="198.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">我</text><rect x="130.0" y="176.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="147.0" y="198.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">爱</text><rect x="170.0" y="176.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="187.0" y="198.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">吃</text><rect x="210.0" y="176.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="227.0" y="198.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">米</text><rect x="250.0" y="176.0" width="34.0" height="32.0" rx="6" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="267.0" y="198.0" font-size="17" text-anchor="middle" style="fill:var(--fg)">饭</text><rect x="290.0" y="176.0" width="34.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2.4;fill:none"/><text x="307.0" y="198.0" font-size="17" text-anchor="middle" font-weight="600" style="fill:var(--accent)">。</text><text x="336.0" y="198.0" font-size="15" text-anchor="start" style="fill:var(--muted)">猜第 6 个</text>
</svg>
<figcaption>图 1　「我爱吃米饭。」6 个 token，拆出 5 个训练样本。灰框是给模型看的前文，蓝框是要它猜的下一个 token。</figcaption>
</figure>

一般地，一段 $n$ 个 token 的文字能拆出 $n-1$ 个训练样本，每个位置一个（第一个 token 前面什么都没有，没法猜，所以少一个）。题目和答案都来自文字本身，不需要任何人标注，所以网上所有文字都能直接拿来用。这也是「预训练」能用上几万亿个 token 的原因。

换成真实规模：Llama 3 405B 训练的大部分时间里，一条序列是 8192 个 token，就是约 8 千个样本；一批 1600 万个 token，就是约 1600 万个样本。

## 第二步：因果遮罩，让 5 道题一次算完

5 道题如果一道一道算，就要把模型跑 5 遍。Transformer 可以一遍算完：把整句话 6 个 token 一起送进去，每个位置各输出一组「下一个 token 的概率」。第 1 个位置的输出用来猜「爱」，第 2 个位置的输出用来猜「吃」，以此类推。

这里有个漏洞。注意力那一讲说过，每个位置会给句子里的其他位置打分、按份额取内容。如果第 3 个位置（「吃」）能看到第 4 个位置（「米」），它猜「米」时就等于偷看了答案，直接抄过来就行，损失一下子变成 0，模型什么都没学会。

所以要加**因果遮罩**（causal mask）：每个位置只能看见自己和前面的位置。做法是在 softmax 之前，把「看后面」的那些分数改成 $-\infty$。因为 $e^{-\infty} = 0$，这些位置分到的份额正好是 0，等于看不见。

<figure class="fig">
<svg viewBox="0 0 480 300" role="img" aria-label="因果遮罩：每个位置只能看到自己和前面的字">
<text x="140.0" y="42.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">我</text><text x="180.0" y="42.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">爱</text><text x="220.0" y="42.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">吃</text><text x="260.0" y="42.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">米</text><text x="300.0" y="42.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">饭</text><text x="340.0" y="42.0" font-size="16" text-anchor="middle" style="fill:var(--muted)">。</text><text x="240.0" y="18.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">能看到的字</text><text x="108.0" y="80.0" font-size="15" text-anchor="end" style="fill:var(--fg)">第 1 位 我</text><rect x="123.0" y="57.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="123.0" y="57.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="163.0" y="57.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="203.0" y="57.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="243.0" y="57.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="283.0" y="57.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="323.0" y="57.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><text x="374.0" y="80.0" font-size="15" text-anchor="start" style="fill:var(--accent)">→ 猜 爱</text><text x="108.0" y="120.0" font-size="15" text-anchor="end" style="fill:var(--fg)">第 2 位 爱</text><rect x="123.0" y="97.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="123.0" y="97.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="163.0" y="97.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="163.0" y="97.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="203.0" y="97.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="243.0" y="97.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="283.0" y="97.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="323.0" y="97.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><text x="374.0" y="120.0" font-size="15" text-anchor="start" style="fill:var(--accent)">→ 猜 吃</text><text x="108.0" y="160.0" font-size="15" text-anchor="end" style="fill:var(--fg)">第 3 位 吃</text><rect x="123.0" y="137.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="123.0" y="137.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="163.0" y="137.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="163.0" y="137.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="203.0" y="137.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="203.0" y="137.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="243.0" y="137.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="283.0" y="137.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="323.0" y="137.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><text x="374.0" y="160.0" font-size="15" text-anchor="start" style="fill:var(--accent)">→ 猜 米</text><text x="108.0" y="200.0" font-size="15" text-anchor="end" style="fill:var(--fg)">第 4 位 米</text><rect x="123.0" y="177.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="123.0" y="177.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="163.0" y="177.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="163.0" y="177.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="203.0" y="177.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="203.0" y="177.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="243.0" y="177.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="243.0" y="177.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="283.0" y="177.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><rect x="323.0" y="177.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><text x="374.0" y="200.0" font-size="15" text-anchor="start" style="fill:var(--accent)">→ 猜 饭</text><text x="108.0" y="240.0" font-size="15" text-anchor="end" style="fill:var(--fg)">第 5 位 饭</text><rect x="123.0" y="217.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="123.0" y="217.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="163.0" y="217.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="163.0" y="217.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="203.0" y="217.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="203.0" y="217.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="243.0" y="217.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="243.0" y="217.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="283.0" y="217.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="283.0" y="217.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="323.0" y="217.0" width="34.0" height="34.0" rx="4" style="stroke:var(--line);stroke-width:1.2;stroke-dasharray:3 3;fill:none"/><text x="374.0" y="240.0" font-size="15" text-anchor="start" style="fill:var(--accent)">→ 猜 。</text><text x="108.0" y="280.0" font-size="15" text-anchor="end" style="fill:var(--fg)">第 6 位 。</text><rect x="123.0" y="257.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="123.0" y="257.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="163.0" y="257.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="163.0" y="257.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="203.0" y="257.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="203.0" y="257.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="243.0" y="257.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="243.0" y="257.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="283.0" y="257.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="283.0" y="257.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><rect x="323.0" y="257.0" width="34.0" height="34.0" rx="4" style="fill:var(--accent-soft)"/><rect x="323.0" y="257.0" width="34.0" height="34.0" rx="4" style="stroke:var(--accent);stroke-width:1.2;fill:none"/><text x="374.0" y="280.0" font-size="15" text-anchor="start" style="fill:var(--muted)">→ 猜 —</text>
</svg>
<figcaption>图 2　一次前向同时算出 6 个位置。第 <i>i</i> 行是第 <i>i</i> 个位置能看到的字：实心格能看到，虚线格被遮住。每一行右边是它要猜的字；最后一位后面没有字，不算损失。</figcaption>
</figure>

看图 2 第 3 行：「吃」能看见「我」「爱」「吃」三格，后面三格是虚线，看不见；它右边要猜的是「米」。每一行能看见的东西，正好就是这一行那道题允许看的前文。所以一次前向就同时、公平地做完了 5 道题。

<details class="pause"><summary>停一下：如果忘了加因果遮罩，训练损失会怎样？训出来的模型能用来生成文字吗？</summary>

训练损失会迅速降到接近 0，因为每个位置都能看到下一个位置的 token，学会「把右边那个字抄过来」就行。但这样的模型没法生成：生成时右边还没有字（正是要它写的那个），它学会的那招用不上，等于什么都没学。所以训练损失低得反常时，第一件要查的事就是遮罩。

</details>

## 第三步：在一个位置上，模型给出一组概率

拿第 4 道题来看：读「我爱吃米」，猜下一个。模型最后一层给 7 个候选各一个分数（logit，可以是任意实数）。假设此刻的分数是：

| 候选 | 我 | 爱 | 吃 | 米 | 饭 | 粥 | 。 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 分数 $z$ | 0 | 0 | 0 | 0 | 2.0 | 1.5 | 0.5 |

分数变成概率用 softmax（注意力那一讲用过）：每个分数取 $e$ 的指数，再除以所有指数的和。

先算指数：$e^{2.0} = 7.389$，$e^{1.5} = 4.482$，$e^{0.5} = 1.649$，分数是 0 的 4 个都是 $e^{0} = 1$。加起来：

$$
\begin{aligned}
&7.389 + 4.482 + 1.649 + 4 \times 1 \\
&= 17.519
\end{aligned}
$$

正确答案「饭」的概率：

$$
p(\text{饭}) = \frac{7.389}{17.519} = 0.422
$$

同样算出 $p(\text{粥}) = 0.256$，$p(\text{。}) = 0.094$，其余 4 个各 $0.057$。

<figure class="fig">
<svg viewBox="0 0 480 232" role="img" aria-label="读完我爱吃米之后七个候选的概率">
<text x="40.0" y="26.0" font-size="16" text-anchor="end" style="fill:var(--fg)">我</text><rect x="52.0" y="10.0" width="40.6" height="22.0" rx="4" style="fill:var(--line)"/><text x="100.6" y="27.0" font-size="15" text-anchor="start" style="fill:var(--muted)">0.057</text><text x="40.0" y="58.0" font-size="16" text-anchor="end" style="fill:var(--fg)">爱</text><rect x="52.0" y="42.0" width="40.6" height="22.0" rx="4" style="fill:var(--line)"/><text x="100.6" y="59.0" font-size="15" text-anchor="start" style="fill:var(--muted)">0.057</text><text x="40.0" y="90.0" font-size="16" text-anchor="end" style="fill:var(--fg)">吃</text><rect x="52.0" y="74.0" width="40.6" height="22.0" rx="4" style="fill:var(--line)"/><text x="100.6" y="91.0" font-size="15" text-anchor="start" style="fill:var(--muted)">0.057</text><text x="40.0" y="122.0" font-size="16" text-anchor="end" style="fill:var(--fg)">米</text><rect x="52.0" y="106.0" width="40.6" height="22.0" rx="4" style="fill:var(--line)"/><text x="100.6" y="123.0" font-size="15" text-anchor="start" style="fill:var(--muted)">0.057</text><text x="40.0" y="154.0" font-size="16" text-anchor="end" style="fill:var(--fg)">饭</text><rect x="52.0" y="138.0" width="300.0" height="22.0" rx="4" style="fill:var(--accent)"/><text x="360.0" y="155.0" font-size="15" text-anchor="start" style="fill:var(--accent)">0.422</text><text x="40.0" y="186.0" font-size="16" text-anchor="end" style="fill:var(--fg)">粥</text><rect x="52.0" y="170.0" width="182.0" height="22.0" rx="4" style="fill:var(--line)"/><text x="242.0" y="187.0" font-size="15" text-anchor="start" style="fill:var(--muted)">0.256</text><text x="40.0" y="218.0" font-size="16" text-anchor="end" style="fill:var(--fg)">。</text><rect x="52.0" y="202.0" width="66.9" height="22.0" rx="4" style="fill:var(--line)"/><text x="126.9" y="219.0" font-size="15" text-anchor="start" style="fill:var(--muted)">0.094</text>
</svg>
<figcaption>图 3　读完「我爱吃米」，模型给 7 个候选的概率。正确答案「饭」是 0.422。</figcaption>
</figure>

另外 4 道题也各有一组概率。我们只关心每道题里**正确答案**分到的那个数：

| 题 | 读到 | 要猜 | 正确答案的概率 $p$ |
| --- | --- | --- | --- |
| 1 | 我 | 爱 | 0.312 |
| 2 | 我爱 | 吃 | 0.552 |
| 3 | 我爱吃 | 米 | 0.216 |
| 4 | 我爱吃米 | 饭 | 0.422 |
| 5 | 我爱吃米饭 | 。 | 0.670 |

## 第四步：从「概率越高越好」到 $-\ln p$

训练要一个数来衡量「猜得有多差」，然后把它往下压。我们一步一步把它造出来。

**(1) 一道题：正确答案的概率越高越好。** 第 4 题里「饭」是 0.422，如果能调到 0.9，就是猜得更好。

**(2) 一整句话：5 个概率乘起来。** 模型按这组概率写出「我爱吃米饭。」这整句话的概率，是先写出「爱」的概率，乘上接着写出「吃」的概率，一直乘到「。」（概率的乘法规则：几件事接连发生的概率，等于每一步的条件概率相乘）：

$$
\begin{aligned}
P(\text{整句}) &= 0.312 \times 0.552 \times 0.216 \\
&\quad \times 0.422 \times 0.670 = 0.0105
\end{aligned}
$$

训练的目标可以说成：**让训练文字整句出现的概率尽量大**。

**(3) 乘积不好用，取对数变成加法。** 一句话只有 5 个 token，乘积已经只有 0.0105；一条 8192 个 token 的序列，乘积会小到计算机的浮点数表示不了（变成 0）。而且乘积对每一项的导数都牵连着其余所有项。取对数可以解决这两个问题：$\ln(ab) = \ln a + \ln b$，乘积变成求和。$\ln$ 是单调递增的，乘积越大，它的对数也越大，所以「让乘积最大」和「让对数之和最大」是同一件事。

$$
\begin{aligned}
&\ln P(\text{整句}) \\
&= \ln 0.312 + \ln 0.552 + \ln 0.216 \\
&\quad + \ln 0.422 + \ln 0.670 \\
&= -4.558
\end{aligned}
$$

（直接算 $\ln 0.0105$ 也是 $-4.558$，两种算法一致。）

**(4) 加负号，变成要往下压的数。** 概率都小于 1，对数都是负数。习惯上把训练写成「把损失往下压」，所以加个负号，每一项都变成正数：

| 题 | 要猜 | $p$ | $-\ln p$ |
| --- | --- | --- | --- |
| 1 | 爱 | 0.312 | 1.165 |
| 2 | 吃 | 0.552 | 0.594 |
| 3 | 米 | 0.216 | 1.535 |
| 4 | 饭 | 0.422 | 0.863 |
| 5 | 。 | 0.670 | 0.400 |

<figure class="fig">
<svg viewBox="0 0 480 280" role="img" aria-label="负对数曲线和五个位置">
<line x1="50.0" y1="230.0" x2="460.0" y2="230.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="50.0" y1="230.0" x2="50.0" y2="20.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="50.0" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0</text><text x="250.0" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0.5</text><text x="450.0" y="250.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><text x="42.0" y="177.9" font-size="14" text-anchor="end" style="fill:var(--muted)">1</text><text x="42.0" y="120.7" font-size="14" text-anchor="end" style="fill:var(--muted)">2</text><text x="42.0" y="63.6" font-size="14" text-anchor="end" style="fill:var(--muted)">3</text><text x="250.0" y="272.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">正确 token 的概率 <tspan font-style="italic">p</tspan></text><text x="58.0" y="28.0" font-size="15" text-anchor="start" style="fill:var(--muted)">损失 −ln <tspan font-style="italic">p</tspan></text><polyline points="62.0,29.6 63.9,38.2 65.9,45.6 67.8,52.2 69.8,58.1 71.7,63.5 73.6,68.4 75.6,72.9 77.5,77.1 79.5,80.9 81.4,84.6 83.3,88.0 85.3,91.2 87.2,94.3 89.2,97.2 91.1,100.0 93.0,102.6 95.0,105.1 96.9,107.5 98.9,109.9 100.8,112.1 102.7,114.2 104.7,116.3 106.6,118.3 108.6,120.2 110.5,122.1 112.4,123.9 114.4,125.6 116.3,127.3 118.3,129.0 120.2,130.6 122.1,132.1 124.1,133.6 126.0,135.1 128.0,136.6 129.9,138.0 131.8,139.3 133.8,140.7 135.7,142.0 137.7,143.3 139.6,144.5 141.5,145.7 143.5,146.9 145.4,148.1 147.4,149.3 149.3,150.4 151.2,151.5 153.2,152.6 155.1,153.6 157.1,154.7 159.0,155.7 160.9,156.7 162.9,157.7 164.8,158.7 166.8,159.6 168.7,160.6 170.6,161.5 172.6,162.4 174.5,163.3 176.5,164.2 178.4,165.1 180.3,165.9 182.3,166.8 184.2,167.6 186.2,168.4 188.1,169.2 190.0,170.0 192.0,170.8 193.9,171.6 195.9,172.4 197.8,173.1 199.7,173.9 201.7,174.6 203.6,175.3 205.6,176.0 207.5,176.7 209.4,177.4 211.4,178.1 213.3,178.8 215.3,179.5 217.2,180.2 219.1,180.8 221.1,181.5 223.0,182.1 225.0,182.7 226.9,183.4 228.8,184.0 230.8,184.6 232.7,185.2 234.7,185.8 236.6,186.4 238.5,187.0 240.5,187.6 242.4,188.2 244.4,188.8 246.3,189.3 248.2,189.9 250.2,190.4 252.1,191.0 254.1,191.5 256.0,192.1 257.9,192.6 259.9,193.1 261.8,193.7 263.8,194.2 265.7,194.7 267.6,195.2 269.6,195.7 271.5,196.2 273.5,196.7 275.4,197.2 277.3,197.7 279.3,198.2 281.2,198.7 283.2,199.2 285.1,199.6 287.0,200.1 289.0,200.6 290.9,201.0 292.9,201.5 294.8,201.9 296.7,202.4 298.7,202.8 300.6,203.3 302.6,203.7 304.5,204.2 306.4,204.6 308.4,205.0 310.3,205.5 312.3,205.9 314.2,206.3 316.1,206.7 318.1,207.1 320.0,207.5 322.0,208.0 323.9,208.4 325.8,208.8 327.8,209.2 329.7,209.6 331.7,210.0 333.6,210.3 335.5,210.7 337.5,211.1 339.4,211.5 341.4,211.9 343.3,212.3 345.2,212.6 347.2,213.0 349.1,213.4 351.1,213.8 353.0,214.1 354.9,214.5 356.9,214.9 358.8,215.2 360.8,215.6 362.7,215.9 364.6,216.3 366.6,216.6 368.5,217.0 370.5,217.3 372.4,217.7 374.3,218.0 376.3,218.4 378.2,218.7 380.2,219.0 382.1,219.4 384.0,219.7 386.0,220.0 387.9,220.4 389.9,220.7 391.8,221.0 393.7,221.3 395.7,221.7 397.6,222.0 399.6,222.3 401.5,222.6 403.4,222.9 405.4,223.2 407.3,223.6 409.3,223.9 411.2,224.2 413.1,224.5 415.1,224.8 417.0,225.1 419.0,225.4 420.9,225.7 422.8,226.0 424.8,226.3 426.7,226.6 428.7,226.9 430.6,227.2 432.5,227.4 434.5,227.7 436.4,228.0 438.4,228.3 440.3,228.6 442.2,228.9 444.2,229.2 446.1,229.4 448.1,229.7 450.0,230.0" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><circle cx="174.7" cy="163.4" r="5.5" style="fill:var(--accent)"/><text x="182.7" y="155.4" font-size="14" text-anchor="start" style="fill:var(--accent)">爱 1.17</text><circle cx="270.7" cy="196.0" r="5.5" style="fill:var(--accent)"/><text x="276.7" y="184.0" font-size="14" text-anchor="start" style="fill:var(--accent)">吃 0.59</text><circle cx="136.2" cy="142.3" r="5.5" style="fill:var(--accent)"/><text x="144.2" y="134.3" font-size="14" text-anchor="start" style="fill:var(--accent)">米 1.53</text><circle cx="218.7" cy="180.7" r="5.5" style="fill:var(--accent)"/><text x="210.7" y="198.7" font-size="14" text-anchor="end" style="fill:var(--accent)">饭 0.86</text><circle cx="318.0" cy="207.1" r="5.5" style="fill:var(--accent)"/><text x="326.0" y="225.1" font-size="14" text-anchor="start" style="fill:var(--accent)">。 0.40</text>
</svg>
<figcaption>图 4　橙色曲线是 −ln <i>p</i>：概率越接近 1，损失越接近 0；概率越接近 0，损失越大，而且涨得越来越快。蓝点是「我爱吃米饭。」5 个位置，标的是要猜的字和它的损失。</figcaption>
</figure>

看图 4 的曲线：$p = 1$ 时损失正好是 0（猜得百分之百准，没什么可罚）；$p$ 越小损失越大，而且越往左涨得越快。第 3 题的「米」只有 0.216，罚得最重；第 5 题的「。」有 0.670，罚得最轻。

**(5) 取平均。** 句子有长有短，直接求和的话长句子的损失天然更大。所以除以题数，取平均：

$$
\begin{aligned}
L &= \frac{1}{5}\sum_{i=1}^{5} \bigl(-\ln p_i\bigr) \\
&= \frac{4.558}{5} = 0.912
\end{aligned}
$$

<figure class="fig">
<svg viewBox="0 0 480 220" role="img" aria-label="五个位置的损失和平均损失">
<rect x="70.0" y="76.1" width="54.0" height="113.9" rx="3" style="fill:var(--warn)"/><text x="97.0" y="70.1" font-size="14" text-anchor="middle" style="fill:var(--warn)">1.165</text><text x="97.0" y="210.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">→爱</text><rect x="150.0" y="131.9" width="54.0" height="58.1" rx="3" style="fill:var(--warn)"/><text x="177.0" y="125.9" font-size="14" text-anchor="middle" style="fill:var(--warn)">0.594</text><text x="177.0" y="210.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">→吃</text><rect x="230.0" y="40.0" width="54.0" height="150.0" rx="3" style="fill:var(--warn)"/><text x="257.0" y="34.0" font-size="14" text-anchor="middle" style="fill:var(--warn)">1.535</text><text x="257.0" y="210.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">→米</text><rect x="310.0" y="105.6" width="54.0" height="84.4" rx="3" style="fill:var(--warn)"/><text x="337.0" y="99.6" font-size="14" text-anchor="middle" style="fill:var(--warn)">0.863</text><text x="337.0" y="210.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">→饭</text><rect x="390.0" y="150.9" width="54.0" height="39.1" rx="3" style="fill:var(--warn)"/><text x="417.0" y="144.9" font-size="14" text-anchor="middle" style="fill:var(--warn)">0.400</text><text x="417.0" y="210.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">→。</text><line x1="60.0" y1="100.9" x2="454.0" y2="100.9" style="stroke:var(--fg);stroke-width:1.5;stroke-dasharray:6 4;fill:none"/><text x="56.0" y="105.9" font-size="14" text-anchor="end" style="fill:var(--fg)">平均 0.912</text>
</svg>
<figcaption>图 5　每个位置的损失 −ln <i>p</i>，虚线是它们的平均 0.912，这就是这句话的交叉熵损失。</figcaption>
</figure>

这就是**交叉熵损失**（cross-entropy loss）。一般写法是：

$$
L = -\frac{1}{N}\sum_{i=1}^{N} \ln p_\theta\bigl(x_{i+1} \mid x_{1..i}\bigr)
$$

$N$ 是题数（位置数），$p_\theta(x_{i+1} \mid x_{1..i})$ 是参数为 $\theta$ 的模型读完前 $i$ 个 token 之后，给正确的第 $i+1$ 个 token 的概率。「交叉熵」这个名字来自信息论：它比较的是两个分布，一个是正确答案（正确 token 是 1、其他都是 0），一个是模型给的概率；正确答案只有一个位置是 1，展开之后就只剩正确那一项的 $-\ln p$。

<details class="pause"><summary>停一下：第 3 题的概率如果从 0.216 提到 0.432（翻一倍），这一题的损失降多少？第 5 题从 0.670 提到 0.900 呢？</summary>

$-\ln p$ 的变化等于 $\ln$ 新概率减 $\ln$ 旧概率。第 3 题：$\ln 0.432 - \ln 0.216 = \ln 2 \approx 0.693$，损失从 1.535 降到 0.842。第 5 题：$\ln 0.900 - \ln 0.670 = \ln 1.343 \approx 0.295$，损失从 0.400 降到 0.105。概率翻一倍，不管原来是多少，损失都降同样的 0.693。所以交叉熵最在意那些「猜得很差」的位置：把 1% 提到 2% 和把 40% 提到 80% 一样值钱。

</details>

## 第五步：困惑度，把损失换回「在几个选项里犹豫」

损失 0.912 是多少？不好直观理解。把它放回指数上：

$$
\mathrm{PPL} = e^{L} = e^{0.912} = 2.49
$$

这个数叫**困惑度**（perplexity）。它的意思是：模型平均每猜一个 token，相当于在 2.49 个同样可能的选项里挑一个。为什么能这么说？把第四步倒着走一遍：$L$ 是 5 个 $-\ln p$ 的平均，$e^{-L}$ 就是 5 个 $p$ 的几何平均（5 个数乘起来再开 5 次方）：

$$
e^{-L} = \sqrt[5]{0.0105} = 0.402
$$

平均每题给正确答案 0.402 的概率，相当于在 $1 / 0.402 = 2.49$ 个等可能的选项里瞎猜。完全没学过的模型给 7 个候选平均分，每题 $1/7$，困惑度就是 7；猜得百分之百准，困惑度是 1。后面模型评测那一讲会把困惑度当作评测指标再讲一遍：它就是训练损失换了个单位。

## 第六步：一个训练步，把前面几讲拼成一条线

上面的概率是凭空「假设」的。现在给它一个真模型：**bigram 模型**，最简单的语言模型。它猜下一个 token 时只看上一个 token，参数是一张 $7 \times 7$ 的分数表：第「米」行就是「上一个字是米时，7 个候选的分数」，正是第三步那一行 $(0, 0, 0, 0, 2.0, 1.5, 0.5)$。前面 5 道题的概率，都是从这张表里查出来、再做 softmax 得到的。这张表里的 49 个数就是这个模型的全部参数，训练就是调它们。

<figure class="fig">
<svg viewBox="0 0 480 310" role="img" aria-label="一个训练步的五个环节">
<rect x="60.0" y="10.0" width="300.0" height="44.0" rx="8" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="76.0" y="38.0" font-size="17" text-anchor="start" font-weight="600" style="fill:var(--fg)">取一批文本</text><text x="346.0" y="38.0" font-size="15" text-anchor="end" style="fill:var(--muted)">切成 token</text><line x1="210.0" y1="56.0" x2="210.0" y2="60.0" style="stroke:var(--muted);stroke-width:1.6;fill:none"/><path d="M210.0 70.0 L205.9 60.9 L214.1 60.9 z" style="fill:var(--muted)"/><rect x="60.0" y="72.0" width="300.0" height="44.0" rx="8" style="stroke:var(--accent);stroke-width:2.2;fill:none"/><text x="76.0" y="100.0" font-size="17" text-anchor="start" font-weight="600" style="fill:var(--accent)">前向</text><text x="346.0" y="100.0" font-size="15" text-anchor="end" style="fill:var(--muted)">每个位置的概率</text><line x1="210.0" y1="118.0" x2="210.0" y2="122.0" style="stroke:var(--muted);stroke-width:1.6;fill:none"/><path d="M210.0 132.0 L205.9 122.9 L214.1 122.9 z" style="fill:var(--muted)"/><rect x="60.0" y="134.0" width="300.0" height="44.0" rx="8" style="stroke:var(--warn);stroke-width:2.2;fill:none"/><text x="76.0" y="162.0" font-size="17" text-anchor="start" font-weight="600" style="fill:var(--warn)">交叉熵</text><text x="346.0" y="162.0" font-size="15" text-anchor="end" style="fill:var(--muted)">−ln p 取平均</text><line x1="210.0" y1="180.0" x2="210.0" y2="184.0" style="stroke:var(--muted);stroke-width:1.6;fill:none"/><path d="M210.0 194.0 L205.9 184.9 L214.1 184.9 z" style="fill:var(--muted)"/><rect x="60.0" y="196.0" width="300.0" height="44.0" rx="8" style="stroke:var(--warn);stroke-width:2.2;fill:none"/><text x="76.0" y="224.0" font-size="17" text-anchor="start" font-weight="600" style="fill:var(--warn)">反向传播</text><text x="346.0" y="224.0" font-size="15" text-anchor="end" style="fill:var(--muted)">每个参数的梯度</text><line x1="210.0" y1="242.0" x2="210.0" y2="246.0" style="stroke:var(--muted);stroke-width:1.6;fill:none"/><path d="M210.0 256.0 L205.9 246.9 L214.1 246.9 z" style="fill:var(--muted)"/><rect x="60.0" y="258.0" width="300.0" height="44.0" rx="8" style="stroke:var(--ok);stroke-width:2.2;fill:none"/><text x="76.0" y="286.0" font-size="17" text-anchor="start" font-weight="600" style="fill:var(--ok)">优化器更新</text><text x="346.0" y="286.0" font-size="15" text-anchor="end" style="fill:var(--muted)">参数往下坡走一步</text><path d="M364 280.0 H400 V32.0 H374" style="stroke:var(--muted);stroke-width:1.6;stroke-dasharray:5 4;fill:none"/><path d="M364 32.0 l10 -6 v12 z" style="fill:var(--muted)"/><text x="408.0" y="161.0" font-size="15" text-anchor="start" style="fill:var(--muted)">下一批</text>
</svg>
<figcaption>图 6　一个训练步。前向（注意力、MLP 几讲）、交叉熵（本讲）、反向传播、优化器（梯度下降一讲）首尾相接，换一批数据再来一遍。</figcaption>
</figure>

一个训练步有五个环节。

**(1) 取一批文本。** 这一批只有两句话：「我爱吃米饭。」和「我爱吃米粥。」，合起来 10 道题。

**(2) 前向。** 每道题查表、做 softmax，得到正确答案的概率。第一句的 5 个就是上面那张表；第二句前 3 题和第一句一样，第 4 题要猜「粥」，概率是 0.256，第 5 题读到「粥」，表里「粥」那一行全是 0，7 个候选平均分，「。」是 $1/7 = 0.143$。

**(3) 交叉熵。** 10 个 $-\ln p$ 取平均，这一批的损失是 1.116。

**(4) 反向传播。** 要知道每个参数往哪边调。反向传播那一讲说过，可以用数值微分来验证：把「米」行「饭」那一格的分数加 0.01，重新算第 4 题的损失，从 0.8633 变成 0.8575，降了 0.0058。而反向传播给出的这一格的梯度是 $p - 1 = 0.422 - 1 = -0.578$，乘上 0.01 正好是 $-0.0058$，一致。一般地，交叉熵对每个分数的梯度都是：

$$
\frac{\partial(-\ln p_y)}{\partial z_k} = p_k - y_k
$$

$y_k$ 在正确答案处是 1，其他是 0。梯度就是「模型给的概率减去正确答案」（后训练那一讲会把这个式子完整推一遍）。

整批的梯度是 10 道题各自的梯度加起来再除以 10。「米」这一行被两道题用到：第一句要它猜「饭」，第二句要它猜「粥」。把两道题的 $p - y$ 加起来除以 10：

| 候选 | 第一句（猜饭）的 $p - y$ | 第二句（猜粥）的 $p - y$ | 合起来 ÷ 10 |
| --- | --- | --- | --- |
| 饭 | $0.422 - 1$ | $0.422$ | $-0.016$ |
| 粥 | $0.256$ | $0.256 - 1$ | $-0.049$ |
| 。 | $0.094$ | $0.094$ | $0.019$ |
| 其余 4 个 | $0.057$ | $0.057$ | $0.011$ |

**(5) 优化器更新。** 用梯度下降那一讲的规则 $\theta \leftarrow \theta - \eta \nabla L$，学习率 $\eta = 4$。「米」行每个分数减去 $4 \times$ 梯度：

| 候选 | 原分数 | $- 4 \times$ 梯度 | 新分数 |
| --- | --- | --- | --- |
| 饭 | 2.0 | $+0.016 \times 4$ | 2.063 |
| 粥 | 1.5 | $+0.049 \times 4$ | 1.695 |
| 。 | 0.5 | $-0.019 \times 4$ | 0.425 |
| 其余 4 个 | 0 | $-0.011 \times 4$ | -0.046 |

再做一次 softmax：「粥」从 25.6% 升到 29.2%，「饭」从 42.2% 变成 42.1%，几乎没动。

<figure class="fig">
<svg viewBox="0 0 480 260" role="img" aria-label="米那一行在一个训练步之前与之后">
<text x="80.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">走一步之前</text><text x="290.0" y="22.0" font-size="15" text-anchor="start" style="fill:var(--muted)">走一步之后</text><text x="66.0" y="53.0" font-size="16" text-anchor="end" style="fill:var(--fg)">我</text><rect x="80.0" y="36.0" width="16.0" height="22.0" rx="4" style="fill:var(--line)"/><text x="102.0" y="53.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.057</text><rect x="290.0" y="36.0" width="14.3" height="22.0" rx="4" style="fill:var(--line)"/><text x="310.3" y="53.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.051</text><text x="66.0" y="85.0" font-size="16" text-anchor="end" style="fill:var(--fg)">爱</text><rect x="80.0" y="68.0" width="16.0" height="22.0" rx="4" style="fill:var(--line)"/><text x="102.0" y="85.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.057</text><rect x="290.0" y="68.0" width="14.3" height="22.0" rx="4" style="fill:var(--line)"/><text x="310.3" y="85.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.051</text><text x="66.0" y="117.0" font-size="16" text-anchor="end" style="fill:var(--fg)">吃</text><rect x="80.0" y="100.0" width="16.0" height="22.0" rx="4" style="fill:var(--line)"/><text x="102.0" y="117.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.057</text><rect x="290.0" y="100.0" width="14.3" height="22.0" rx="4" style="fill:var(--line)"/><text x="310.3" y="117.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.051</text><text x="66.0" y="149.0" font-size="16" text-anchor="end" style="fill:var(--fg)">米</text><rect x="80.0" y="132.0" width="16.0" height="22.0" rx="4" style="fill:var(--line)"/><text x="102.0" y="149.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.057</text><rect x="290.0" y="132.0" width="14.3" height="22.0" rx="4" style="fill:var(--line)"/><text x="310.3" y="149.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.051</text><text x="66.0" y="181.0" font-size="16" text-anchor="end" style="fill:var(--fg)">饭</text><rect x="80.0" y="164.0" width="118.0" height="22.0" rx="4" style="fill:var(--accent)"/><text x="204.0" y="181.0" font-size="14" text-anchor="start" style="fill:var(--accent)">0.422</text><rect x="290.0" y="164.0" width="117.9" height="22.0" rx="4" style="fill:var(--accent)"/><text x="413.9" y="181.0" font-size="14" text-anchor="start" style="fill:var(--accent)">0.421</text><text x="66.0" y="213.0" font-size="16" text-anchor="end" style="fill:var(--fg)">粥</text><rect x="80.0" y="196.0" width="71.6" height="22.0" rx="4" style="fill:var(--accent)"/><text x="157.6" y="213.0" font-size="14" text-anchor="start" style="fill:var(--accent)">0.256</text><rect x="290.0" y="196.0" width="81.7" height="22.0" rx="4" style="fill:var(--accent)"/><text x="377.7" y="213.0" font-size="14" text-anchor="start" style="fill:var(--accent)">0.292</text><text x="66.0" y="245.0" font-size="16" text-anchor="end" style="fill:var(--fg)">。</text><rect x="80.0" y="228.0" width="26.3" height="22.0" rx="4" style="fill:var(--line)"/><text x="112.3" y="245.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.094</text><rect x="290.0" y="228.0" width="22.9" height="22.0" rx="4" style="fill:var(--line)"/><text x="318.9" y="245.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.082</text>
</svg>
<figcaption>图 7　bigram 表里「米」那一行的 7 个概率。这一批里「米」后面一次是「饭」、一次是「粥」：「粥」明显升了，「饭」几乎没动，其余 5 个都降。</figcaption>
</figure>

「饭」的分数明明加了，概率为什么没涨？因为「粥」的分数加得更多（梯度大了约三倍），softmax 只看分数之间的差，「饭」相对「粥」反而吃亏了一点。这一步在做的事是：这一批数据里「米」后面一半是「饭」、一半是「粥」，所以把「粥」往上拉，让两者靠近。

整张表的其他行也同时更新（「我」「爱」「吃」那几行各被两道题推向同一个答案，涨得很干脆）。重新算一遍，这一批的损失从 1.116 降到 0.848。这就是一个完整的训练步。

真实的大模型，每个环节都一样，只是规模不同：一批是 1600 万个 token；前向不是查一张表，而是穿过几十上百层的注意力、MLP、残差和 LayerNorm（前面那几讲）；反向传播把梯度一层层传回去；优化器是 AdamW（梯度下降那一讲）。Llama 3 405B 这样走了 120 万步左右，总共读了 15.6 T（万亿）个 token，花了 $3.8 \times 10^{25}$ 次浮点运算。模型多大、数据多少、算力怎么分配最划算，是下一讲 Scaling Laws 的题目。

## 第七步：一直训下去，损失停在哪

在这两句话上反复走训练步：

<figure class="fig">
<svg viewBox="0 0 480 258" role="img" aria-label="在两句话上反复训练的损失曲线">
<line x1="60.0" y1="210.0" x2="458.0" y2="210.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="60.0" y1="210.0" x2="60.0" y2="22.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="60.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0</text><text x="157.5" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">20</text><text x="255.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">40</text><text x="352.5" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">60</text><text x="450.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">80</text><text x="52.0" y="155.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.4</text><text x="52.0" y="95.0" font-size="14" text-anchor="end" style="fill:var(--muted)">0.8</text><text x="52.0" y="35.0" font-size="14" text-anchor="end" style="fill:var(--muted)">1.2</text><text x="255.0" y="252.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">训练步数</text><text x="68.0" y="28.0" font-size="15" text-anchor="start" style="fill:var(--muted)">平均损失</text><line x1="60.0" y1="189.2" x2="450.0" y2="189.2" style="stroke:var(--ok);stroke-width:1.5;stroke-dasharray:6 4;fill:none"/><text x="450.0" y="181.2" font-size="14" text-anchor="end" style="fill:var(--ok)">下限 0.139</text><polyline points="60.0,42.6 64.9,82.8 69.8,109.4 74.6,126.9 79.5,138.7 84.4,147.1 89.2,153.2 94.1,157.9 99.0,161.6 103.9,164.5 108.8,166.9 113.6,168.9 118.5,170.6 123.4,172.0 128.2,173.2 133.1,174.3 138.0,175.2 142.9,176.0 147.8,176.8 152.6,177.4 157.5,178.0 162.4,178.6 167.2,179.0 172.1,179.5 177.0,179.9 181.9,180.3 186.8,180.6 191.6,180.9 196.5,181.2 201.4,181.5 206.2,181.8 211.1,182.0 216.0,182.2 220.9,182.5 225.8,182.7 230.6,182.8 235.5,183.0 240.4,183.2 245.2,183.4 250.1,183.5 255.0,183.7 259.9,183.8 264.8,183.9 269.6,184.0 274.5,184.2 279.4,184.3 284.2,184.4 289.1,184.5 294.0,184.6 298.9,184.7 303.8,184.8 308.6,184.9 313.5,185.0 318.4,185.0 323.2,185.1 328.1,185.2 333.0,185.3 337.9,185.3 342.8,185.4 347.6,185.5 352.5,185.5 357.4,185.6 362.2,185.6 367.1,185.7 372.0,185.8 376.9,185.8 381.8,185.9 386.6,185.9 391.5,186.0 396.4,186.0 401.2,186.1 406.1,186.1 411.0,186.1 415.9,186.2 420.8,186.2 425.6,186.3 430.5,186.3 435.4,186.3 440.2,186.4 445.1,186.4 450.0,186.5" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><circle cx="60.0" cy="42.6" r="5" style="fill:var(--warn)"/><text x="70.0" y="46.6" font-size="14" text-anchor="start" style="fill:var(--warn)">1.116</text><circle cx="64.9" cy="82.8" r="4" style="fill:var(--warn)"/><text x="74.9" y="92.8" font-size="14" text-anchor="start" style="fill:var(--warn)">第 1 步后 0.848</text>
</svg>
<figcaption>图 8　在这两句话上一步一步训练，平均损失从 1.116 往下走，但不会到 0：它停在绿色虚线 0.139 附近。</figcaption>
</figure>

10 步之后损失是 0.287，80 步之后是 0.157，越来越平，停在 0.139 附近，不会降到 0。为什么？

10 道题里，有 8 道的答案是确定的：「我」后面一定是「爱」，「爱」后面一定是「吃」……这 8 道题的概率可以一直推向 1，损失推向 0。剩下 2 道题是「米」后面：一次是「饭」，一次是「粥」。bigram 只看到「米」，没法区分这两次，最好的做法就是各给 50%。这时两道题的损失各是 $-\ln 0.5 = \ln 2 = 0.693$，平均到 10 道题上：

$$
\begin{aligned}
L_{\min} &= \frac{2 \times \ln 2}{10} \\
&= \frac{2 \times 0.693}{10} = 0.139
\end{aligned}
$$

80 步之后，「米」后面「饭」「粥」各是 48.9%，正在逼近各一半。

这说明了预训练的一个基本事实：**损失有下限，下限就是数据本身的不确定性**。人写的文字里，很多地方下一个字本来就有好几种合理的写法，再强的模型也只能给出一个分布。模型能做的，是把「本来就确定」的部分猜对，把「本来就不确定」的部分猜成正确的比例。

<details class="pause"><summary>停一下：如果这一批是三句「我爱吃米饭。」和一句「我爱吃米粥。」，「米」那一行最后会学成什么？</summary>

「米」后面出现了 4 次，3 次是「饭」、1 次是「粥」。最好的分布就是照着数据的比例：$p(\text{饭}) = 3/4$，$p(\text{粥}) = 1/4$。这时这 4 道题的损失是 $3 \times (-\ln 0.75) + 1 \times (-\ln 0.25) = 3 \times 0.288 + 1.386 = 2.249$。可以试着把 $p(\text{饭})$ 改成 0.8 或 0.7 再算，都比 2.249 大。交叉熵最小的地方，正好是模型的概率等于数据里的频率。

</details>

## 数据从哪来

模型学到的一切都来自训练文字，所以数据是预训练里最花功夫的部分。公开报告里的来源大致是这几类：

- **网页**：量最大。最常见的来源是 Common Crawl，一个定期抓取公开网页、免费发布快照的非营利项目。
- **代码**：GitHub 等公开代码仓库。
- **书和百科**：数量少，但文字质量高、知识密度大。
- **多种语言**：网页里英文占多数，其他语言要专门收集，或从网页里按语言挑出来。

原始网页不能直接用。抓下来的 HTML 里，大部分是导航栏、广告、版权声明、乱码、机器生成的垃圾页，还有大量重复。下面三节分别讲清洗、去重和配比。

## 清洗：把网页变成干净的文字

HuggingFace 公开了它从 Common Crawl 做出 FineWeb 数据集（15 T 个 token，来自 96 个快照）的全过程，每一步都有数字，可以当作标准做法来看：

1. **抽取正文。** 用 trafilatura 从原始 HTML 里抽出正文，去掉导航、菜单这类边角文字。他们比较过，直接用 Common Crawl 自带的纯文本版本，会留下太多菜单和模板文字。
2. **基础过滤。** 屏蔽成人网站的网址；用一个 fastText 语言分类器只留英文（得分至少 0.65）；再用一组质量和重复规则去掉明显的垃圾页。做完这一步约剩 36 T 个 token。
3. **去重。** 下一节专门讲。每个快照内部去重之后约剩 20 T 个 token。
4. **规则过滤。** 一组来自 C4 数据集的规则，再加三条他们自己定的规则，比如「以标点结尾的行不到 12%」的文档去掉（多半是列表、菜单拼成的页面），「重复行里的字符占 10% 以上」的去掉，「短于 30 个字符的行占 67% 以上」的去掉。
5. **隐私。** 把邮箱地址和公网 IP 地址替换掉。

Llama 3 的报告列出了类似的步骤，并多了一步**用模型打分**：训练一个小分类器（他们用的是 DistilRoberta）给每篇文档的质量打分，按分数筛。FineWeb 也做了一个这样的子集 FineWeb-Edu：先让 Llama-3-70B-Instruct 给 46 万个网页按「有没有教育价值」打 0–5 分，再用这些打分训练一个小分类器，去给全部 15 T 个 token 打分，只留 3 分以上的，剩 1.3 T 个 token。用更少但更好的数据训练，效果反而更好，这是近几年数据工作的一个主线。

## 去重：同一段话不要读一百遍

网上有大量重复：转载的文章、同一个模板生成的页面、每个月都被抓一次的同一个网页。重复的坏处有两个：一是浪费算力，同样的内容读一百遍，花一百份钱只学到一份东西；二是模型会把高频重复的段落背下来，原样吐出。

完全相同的文档好办，算一个指纹比较就行。难的是「几乎一样」的文档，比如只改了日期、只差一句话的转载。判断两篇文档有多像，常用 **Jaccard 相似度**。拿两段只差两个字的话举例：

- A：今天天气很好我们去公园
- B：今天天气很好我们去看书

**(1) 切成片段。** 每相邻两个字切成一段（真实做法常用 5 个词一段），A 和 B 各得 10 段。

<figure class="fig">
<svg viewBox="0 0 480 98" role="img" aria-label="两段文字切成两个字一段的片段">
<text x="8.0" y="30.0" font-size="15" text-anchor="start" style="fill:var(--muted)">A</text><rect x="30.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="52.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">今天</text><rect x="74.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="96.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">天天</text><rect x="118.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="140.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">天气</text><rect x="162.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="184.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">气很</text><rect x="206.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="228.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">很好</text><rect x="250.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="272.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">好我</text><rect x="294.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="316.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">我们</text><rect x="338.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="360.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">们去</text><rect x="382.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--warn);stroke-width:2.2;fill:none"/><text x="404.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">去公</text><rect x="426.0" y="8.0" width="44.0" height="32.0" rx="6" style="stroke:var(--warn);stroke-width:2.2;fill:none"/><text x="448.0" y="30.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">公园</text><text x="8.0" y="78.0" font-size="15" text-anchor="start" style="fill:var(--muted)">B</text><rect x="30.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="52.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">今天</text><rect x="74.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="96.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">天天</text><rect x="118.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="140.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">天气</text><rect x="162.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="184.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">气很</text><rect x="206.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="228.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">很好</text><rect x="250.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="272.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">好我</text><rect x="294.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="316.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">我们</text><rect x="338.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--accent);stroke-width:2;fill:none"/><text x="360.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--accent)">们去</text><rect x="382.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--warn);stroke-width:2.2;fill:none"/><text x="404.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">去看</text><rect x="426.0" y="56.0" width="44.0" height="32.0" rx="6" style="stroke:var(--warn);stroke-width:2.2;fill:none"/><text x="448.0" y="78.0" font-size="15" text-anchor="middle" style="fill:var(--warn)">看书</text>
</svg>
<figcaption>图 9　两段文字各切成 10 个「两字片段」。蓝框两边都有（8 个），橙框只有一边有（各 2 个）。</figcaption>
</figure>

**(2) 数交集和并集。** 两边都有的片段是交集，有 8 个；所有出现过的不同片段是并集，$8 + 2 + 2 = 12$ 个。

**(3) 相除。**

$$
J(A, B) = \frac{\lvert A \cap B \rvert}{\lvert A \cup B \rvert} = \frac{8}{12} = 0.667
$$

完全相同是 1，没有一个片段相同是 0。

问题是规模：几十亿篇文档两两比较，是几亿亿次。**MinHash** 用一个巧妙的办法把它变便宜。给每个片段算一个随机的哈希值（一个看起来随机的数），每篇文档只记下它所有片段里**最小的那个哈希值**。两篇文档记下的最小值相同的概率，正好等于它们的 Jaccard 相似度。为什么？

- 把 A 和 B 的片段合在一起（就是并集，12 个），看其中哈希值最小的那一个。哈希是随机的，所以 12 个片段里谁最小，机会均等。
- 如果最小的那个在交集里（两边都有），那它在 A 里是最小的，在 B 里也是最小的，两篇文档记下的值相同。
- 如果它只在一边，那一边记下的是它，另一边记下的是别的，不同。
- 所以「相同」的概率 = 交集占并集的比例 = $8/12 = 0.667$，正是 Jaccard 相似度。

用很多个不同的哈希函数各算一次，数一数有几个相同，就能估出相似度，而每篇文档只需要存几十上百个数。

FineWeb 用 112 个哈希函数，分成 14 组、每组 8 个：只要有一组的 8 个值全部相同，就判为重复。一组 8 个全相同的概率是 $J^8$；14 组里至少有一组全相同的概率是 $1 - (1 - J^8)^{14}$。代入 A 和 B 的 $J = 0.667$：$J^8 = 0.0390$，$1 - J^8 = 0.9610$，14 次方是 0.573，被判为重复的概率是 42.7%。代入 $J = 0.75$ 是 77.2%，$J = 0.5$ 只有 5.3%。

<figure class="fig">
<svg viewBox="0 0 480 220" role="img" aria-label="MinHash 分桶后被判为重复的概率曲线">
<line x1="60.0" y1="200.0" x2="458.0" y2="200.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="60.0" y1="200.0" x2="60.0" y2="22.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="60.0" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0</text><text x="157.5" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0.25</text><text x="255.0" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0.5</text><text x="352.5" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0.75</text><text x="450.0" y="220.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1</text><text x="52.0" y="120.0" font-size="14" text-anchor="end" style="fill:var(--muted)">50%</text><text x="52.0" y="35.0" font-size="14" text-anchor="end" style="fill:var(--muted)">100%</text><text x="454.0" y="192.0" font-size="15" text-anchor="end" style="fill:var(--muted)">Jaccard 相似度</text><text x="68.0" y="28.0" font-size="15" text-anchor="start" style="fill:var(--muted)">被当成重复的概率</text><polyline points="60.0,200.0 62.0,200.0 63.9,200.0 65.8,200.0 67.8,200.0 69.8,200.0 71.7,200.0 73.7,200.0 75.6,200.0 77.5,200.0 79.5,200.0 81.5,200.0 83.4,200.0 85.3,200.0 87.3,200.0 89.2,200.0 91.2,200.0 93.2,200.0 95.1,200.0 97.0,200.0 99.0,200.0 100.9,200.0 102.9,200.0 104.8,200.0 106.8,200.0 108.8,200.0 110.7,200.0 112.7,200.0 114.6,200.0 116.5,200.0 118.5,200.0 120.5,200.0 122.4,200.0 124.4,200.0 126.3,200.0 128.2,200.0 130.2,200.0 132.2,200.0 134.1,200.0 136.1,200.0 138.0,200.0 139.9,200.0 141.9,200.0 143.8,200.0 145.8,200.0 147.8,200.0 149.7,200.0 151.6,200.0 153.6,200.0 155.6,200.0 157.5,200.0 159.4,200.0 161.4,200.0 163.4,199.9 165.3,199.9 167.2,199.9 169.2,199.9 171.1,199.9 173.1,199.9 175.1,199.9 177.0,199.8 178.9,199.8 180.9,199.8 182.8,199.8 184.8,199.7 186.8,199.7 188.7,199.7 190.7,199.6 192.6,199.6 194.5,199.5 196.5,199.5 198.4,199.4 200.4,199.3 202.3,199.3 204.3,199.2 206.2,199.1 208.2,199.0 210.2,198.9 212.1,198.7 214.1,198.6 216.0,198.4 218.0,198.3 219.9,198.1 221.8,197.9 223.8,197.7 225.8,197.5 227.7,197.2 229.7,197.0 231.6,196.7 233.6,196.4 235.5,196.0 237.5,195.7 239.4,195.3 241.4,194.9 243.3,194.4 245.2,193.9 247.2,193.4 249.2,192.9 251.1,192.3 253.1,191.6 255.0,190.9 256.9,190.2 258.9,189.4 260.9,188.6 262.8,187.7 264.8,186.8 266.7,185.8 268.6,184.7 270.6,183.6 272.6,182.4 274.5,181.1 276.5,179.8 278.4,178.4 280.3,176.9 282.3,175.3 284.2,173.7 286.2,171.9 288.1,170.1 290.1,168.2 292.0,166.2 294.0,164.1 295.9,161.9 297.9,159.6 299.9,157.3 301.8,154.8 303.8,152.2 305.7,149.6 307.6,146.8 309.6,144.0 311.6,141.1 313.5,138.0 315.5,134.9 317.4,131.7 319.4,128.5 321.3,125.1 323.2,121.8 325.2,118.3 327.2,114.8 329.1,111.2 331.0,107.6 333.0,104.0 334.9,100.4 336.9,96.8 338.8,93.1 340.8,89.5 342.8,85.9 344.7,82.4 346.6,78.9 348.6,75.5 350.6,72.1 352.5,68.8 354.4,65.6 356.4,62.6 358.4,59.6 360.3,56.8 362.2,54.1 364.2,51.6 366.2,49.2 368.1,47.0 370.1,44.9 372.0,43.0 374.0,41.2 375.9,39.6 377.8,38.2 379.8,36.9 381.8,35.8 383.7,34.8 385.6,33.9 387.6,33.2 389.6,32.5 391.5,32.0 393.4,31.5 395.4,31.2 397.4,30.9 399.3,30.6 401.2,30.5 403.2,30.3 405.1,30.2 407.1,30.2 409.1,30.1 411.0,30.1 412.9,30.0 414.9,30.0 416.9,30.0 418.8,30.0 420.8,30.0 422.7,30.0 424.7,30.0 426.6,30.0 428.5,30.0 430.5,30.0 432.4,30.0 434.4,30.0 436.3,30.0 438.3,30.0 440.2,30.0 442.2,30.0 444.1,30.0 446.1,30.0 448.1,30.0 450.0,30.0" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><line x1="352.5" y1="200.0" x2="352.5" y2="68.8" style="stroke:var(--muted);stroke-width:1.2;stroke-dasharray:4 4;fill:none"/><circle cx="320.0" cy="127.4" r="5.5" style="fill:var(--accent)"/><text x="310.0" y="131.4" font-size="14" text-anchor="end" style="fill:var(--accent)">A 和 B：42.7%</text><circle cx="352.5" cy="68.8" r="4.5" style="fill:var(--fg)"/><text x="362.5" y="82.8" font-size="14" text-anchor="start" style="fill:var(--fg)">0.75：77.2%</text>
</svg>
<figcaption>图 10　FineWeb 的设置（112 个哈希，分成 14 组、每组 8 个）下，两篇文档被当成重复的概率。相似度过了 0.75 左右，曲线迅速升到接近 100%。</figcaption>
</figure>

分组让这条曲线变得很陡：明显不像的文档几乎不会被误判，非常像的几乎一定被抓到。

去重也不是越狠越好。FineWeb 的一个发现是：把 96 个快照放在一起全局去重，只剩约 4 T 个 token，训出来的模型反而没有变好；每个快照内部各自去重，剩约 20 T，效果更好。他们检查发现，全局去重删掉的旧快照内容里，有不少比留下的质量更高。Llama 3 则是三层一起做：同一个网址只留最新的版本；文档层面用 MinHash 去掉近似重复；行的层面，在每 3000 万篇文档里出现超过 6 次的行删掉（多半是网站模板里的固定文字）。

## 配比：各种数据混多少

清洗、去重之后，每种数据有多少就是多少。但训练时从哪里抽、抽多少，是另一个独立的决定，叫**数据配比**（data mix）。GPT-3 的论文给了一张完整的表：

| 数据源 | token 数 | 训练时的抽样比例 | 训练 3000 亿 token 时读了几遍 |
| --- | --- | --- | --- |
| Common Crawl（过滤后） | 4100 亿 | 60% | 0.44 |
| WebText2 | 190 亿 | 22% | 2.9 |
| Books1 | 120 亿 | 8% | 1.9 |
| Books2 | 550 亿 | 8% | 0.43 |
| Wikipedia | 30 亿 | 3% | 3.4 |

<figure class="fig">
<svg viewBox="0 0 480 240" role="img" aria-label="GPT-3 各数据源的数据量份额与抽样比例">
<text x="190.0" y="22.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">占全部数据量</text><text x="380.0" y="22.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">训练时抽样的比例</text><text x="118.0" y="54.0" font-size="15" text-anchor="end" style="fill:var(--fg)">Common Crawl</text><rect x="130.0" y="38.0" width="123.2" height="22.0" rx="4" style="fill:var(--line)"/><text x="259.2" y="55.0" font-size="14" text-anchor="start" style="fill:var(--muted)">82.2%</text><rect x="330.0" y="38.0" width="90.0" height="22.0" rx="4" style="fill:var(--accent)"/><text x="426.0" y="55.0" font-size="14" text-anchor="start" style="fill:var(--accent)">60%</text><text x="118.0" y="94.0" font-size="15" text-anchor="end" style="fill:var(--fg)">WebText2</text><rect x="130.0" y="78.0" width="5.7" height="22.0" rx="4" style="fill:var(--line)"/><text x="141.7" y="95.0" font-size="14" text-anchor="start" style="fill:var(--muted)">3.8%</text><rect x="330.0" y="78.0" width="33.0" height="22.0" rx="4" style="fill:var(--accent)"/><text x="369.0" y="95.0" font-size="14" text-anchor="start" style="fill:var(--accent)">22%</text><text x="118.0" y="134.0" font-size="15" text-anchor="end" style="fill:var(--fg)">Books1</text><rect x="130.0" y="118.0" width="3.6" height="22.0" rx="4" style="fill:var(--line)"/><text x="139.6" y="135.0" font-size="14" text-anchor="start" style="fill:var(--muted)">2.4%</text><rect x="330.0" y="118.0" width="12.0" height="22.0" rx="4" style="fill:var(--accent)"/><text x="348.0" y="135.0" font-size="14" text-anchor="start" style="fill:var(--accent)">8%</text><text x="118.0" y="174.0" font-size="15" text-anchor="end" style="fill:var(--fg)">Books2</text><rect x="130.0" y="158.0" width="16.5" height="22.0" rx="4" style="fill:var(--line)"/><text x="152.5" y="175.0" font-size="14" text-anchor="start" style="fill:var(--muted)">11.0%</text><rect x="330.0" y="158.0" width="12.0" height="22.0" rx="4" style="fill:var(--accent)"/><text x="348.0" y="175.0" font-size="14" text-anchor="start" style="fill:var(--accent)">8%</text><text x="118.0" y="214.0" font-size="15" text-anchor="end" style="fill:var(--fg)">Wikipedia</text><rect x="130.0" y="198.0" width="1.0" height="22.0" rx="4" style="fill:var(--line)"/><text x="136.9" y="215.0" font-size="14" text-anchor="start" style="fill:var(--muted)">0.6%</text><rect x="330.0" y="198.0" width="4.5" height="22.0" rx="4" style="fill:var(--accent)"/><text x="340.5" y="215.0" font-size="14" text-anchor="start" style="fill:var(--accent)">3%</text>
</svg>
<figcaption>图 11　GPT-3 的五个数据源。灰条是各自占全部 4990 亿 token 的份额，蓝条是训练时实际从它抽样的比例。书和维基百科被多抽，网页被少抽。</figcaption>
</figure>

五个数据源一共 499 亿个 token，Common Crawl 占 82.2%，但只抽了 60%；维基百科只占 0.6%，却抽了 3%，整个训练过程读了 3.4 遍，而网页连一遍都没读完。论文的说法是：质量越高的数据，抽得越多。

Llama 3 的报告按内容类别给出了最终配比：约 50% 通用知识、25% 数学与推理、17% 代码、8% 多语言。数学和代码的比例远高于它们在网页里的自然占比，因为这类数据对推理能力帮助大。报告还描述了一个收尾的做法：训练最后阶段，把高质量的代码和数学数据加大比例，同时把学习率降到 0，叫**退火**（annealing）。他们报告，这一步让 8B 模型在 GSM8K 和 MATH 两个数学评测的验证集上分别提高了 24.0% 和 6.4%；对 405B 模型几乎没有提升。

配比怎么定，目前主要靠在小模型上做对照实验：同样的算力，换一种配比训一遍，看评测分数。

## 学习率：先预热，再余弦衰减

梯度下降那一讲说，训练大模型「默认几乎都是 AdamW，再配上先升后降的学习率曲线」。这一节把这条曲线讲清楚。Llama 3 405B 的设置是：峰值学习率 $8 \times 10^{-5}$；前 8000 步从 0 线性升到峰值，叫**预热**（warmup）；之后在剩下的步数里沿余弦曲线降到 $8 \times 10^{-7}$，总共 120 万步。

<figure class="fig">
<svg viewBox="0 0 480 210" role="img" aria-label="Llama 3 405B 的学习率曲线：全程与前两万步">
<line x1="56.0" y1="184.0" x2="252.0" y2="184.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="56.0" y1="184.0" x2="56.0" y2="28.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="56.0" y="202.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">0</text><text x="151.0" y="202.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">60 万</text><text x="246.0" y="202.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">120 万</text><text x="151.0" y="22.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">全程 120 万步</text><polyline points="56.0,184.0 56.6,109.0 57.3,34.0 57.9,34.0 58.5,34.0 59.2,34.0 59.8,34.1 60.4,34.1 61.1,34.1 61.7,34.2 62.3,34.3 63.0,34.3 63.6,34.4 64.2,34.5 64.9,34.6 65.5,34.7 66.1,34.8 66.8,34.9 67.4,35.1 68.0,35.2 68.7,35.3 69.3,35.5 69.9,35.6 70.6,35.8 71.2,36.0 71.8,36.2 72.5,36.4 73.1,36.6 73.7,36.8 74.4,37.0 75.0,37.2 75.6,37.4 76.3,37.7 76.9,37.9 77.5,38.2 78.2,38.4 78.8,38.7 79.4,39.0 80.1,39.3 80.7,39.6 81.3,39.9 82.0,40.2 82.6,40.5 83.2,40.8 83.9,41.2 84.5,41.5 85.1,41.8 85.8,42.2 86.4,42.6 87.0,42.9 87.7,43.3 88.3,43.7 88.9,44.1 89.6,44.5 90.2,44.9 90.8,45.3 91.5,45.7 92.1,46.1 92.7,46.6 93.4,47.0 94.0,47.5 94.6,47.9 95.3,48.4 95.9,48.8 96.5,49.3 97.2,49.8 97.8,50.3 98.4,50.8 99.1,51.3 99.7,51.8 100.3,52.3 101.0,52.8 101.6,53.3 102.2,53.8 102.9,54.4 103.5,54.9 104.1,55.5 104.8,56.0 105.4,56.6 106.0,57.1 106.7,57.7 107.3,58.3 107.9,58.9 108.6,59.5 109.2,60.1 109.8,60.7 110.5,61.3 111.1,61.9 111.7,62.5 112.4,63.1 113.0,63.7 113.6,64.4 114.3,65.0 114.9,65.6 115.5,66.3 116.2,66.9 116.8,67.6 117.4,68.2 118.1,68.9 118.7,69.6 119.3,70.2 120.0,70.9 120.6,71.6 121.2,72.3 121.9,72.9 122.5,73.6 123.1,74.3 123.8,75.0 124.4,75.7 125.0,76.4 125.7,77.1 126.3,77.9 126.9,78.6 127.6,79.3 128.2,80.0 128.8,80.7 129.5,81.5 130.1,82.2 130.7,82.9 131.4,83.7 132.0,84.4 132.6,85.2 133.3,85.9 133.9,86.6 134.5,87.4 135.2,88.2 135.8,88.9 136.4,89.7 137.1,90.4 137.7,91.2 138.3,91.9 139.0,92.7 139.6,93.5 140.2,94.2 140.9,95.0 141.5,95.8 142.1,96.6 142.8,97.3 143.4,98.1 144.0,98.9 144.7,99.7 145.3,100.4 145.9,101.2 146.6,102.0 147.2,102.8 147.8,103.6 148.5,104.3 149.1,105.1 149.7,105.9 150.4,106.7 151.0,107.5 151.6,108.2 152.3,109.0 152.9,109.8 153.5,110.6 154.2,111.4 154.8,112.2 155.4,112.9 156.1,113.7 156.7,114.5 157.3,115.3 158.0,116.1 158.6,116.8 159.2,117.6 159.9,118.4 160.5,119.2 161.1,119.9 161.8,120.7 162.4,121.5 163.0,122.3 163.7,123.0 164.3,123.8 164.9,124.6 165.6,125.3 166.2,126.1 166.8,126.8 167.5,127.6 168.1,128.3 168.7,129.1 169.4,129.9 170.0,130.6 170.6,131.3 171.3,132.1 171.9,132.8 172.5,133.6 173.2,134.3 173.8,135.0 174.4,135.8 175.1,136.5 175.7,137.2 176.3,137.9 177.0,138.6 177.6,139.4 178.2,140.1 178.9,140.8 179.5,141.5 180.1,142.2 180.8,142.9 181.4,143.6 182.0,144.2 182.7,144.9 183.3,145.6 183.9,146.3 184.6,146.9 185.2,147.6 185.8,148.3 186.5,148.9 187.1,149.6 187.7,150.2 188.4,150.9 189.0,151.5 189.6,152.1 190.3,152.8 190.9,153.4 191.5,154.0 192.2,154.6 192.8,155.2 193.4,155.8 194.1,156.4 194.7,157.0 195.3,157.6 196.0,158.2 196.6,158.8 197.2,159.4 197.9,159.9 198.5,160.5 199.1,161.0 199.8,161.6 200.4,162.1 201.0,162.7 201.7,163.2 202.3,163.7 202.9,164.2 203.6,164.7 204.2,165.2 204.8,165.7 205.5,166.2 206.1,166.7 206.7,167.2 207.4,167.7 208.0,168.1 208.6,168.6 209.3,169.0 209.9,169.5 210.5,169.9 211.2,170.4 211.8,170.8 212.4,171.2 213.1,171.6 213.7,172.0 214.3,172.4 215.0,172.8 215.6,173.2 216.2,173.6 216.9,173.9 217.5,174.3 218.1,174.7 218.8,175.0 219.4,175.3 220.0,175.7 220.7,176.0 221.3,176.3 221.9,176.6 222.6,176.9 223.2,177.2 223.8,177.5 224.5,177.8 225.1,178.1 225.7,178.3 226.4,178.6 227.0,178.8 227.6,179.1 228.3,179.3 228.9,179.5 229.5,179.7 230.2,179.9 230.8,180.1 231.4,180.3 232.1,180.5 232.7,180.7 233.3,180.9 234.0,181.0 234.6,181.2 235.2,181.3 235.9,181.4 236.5,181.6 237.1,181.7 237.8,181.8 238.4,181.9 239.0,182.0 239.7,182.1 240.3,182.2 240.9,182.2 241.6,182.3 242.2,182.4 242.8,182.4 243.5,182.4 244.1,182.5 244.7,182.5 245.4,182.5 246.0,182.5" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><line x1="282.0" y1="184.0" x2="468.0" y2="184.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="282.0" y1="184.0" x2="282.0" y2="28.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="282.0" y="202.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">0</text><text x="354.0" y="202.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">8000</text><text x="462.0" y="202.0" font-size="13" text-anchor="middle" style="fill:var(--muted)">2 万</text><text x="372.0" y="22.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">前 2 万步放大</text><polyline points="282.0,184.0 282.6,182.8 283.2,181.5 283.8,180.2 284.4,179.0 285.0,177.8 285.6,176.5 286.2,175.2 286.8,174.0 287.4,172.8 288.0,171.5 288.6,170.2 289.2,169.0 289.8,167.8 290.4,166.5 291.0,165.2 291.6,164.0 292.2,162.8 292.8,161.5 293.4,160.2 294.0,159.0 294.6,157.8 295.2,156.5 295.8,155.2 296.4,154.0 297.0,152.8 297.6,151.5 298.2,150.2 298.8,149.0 299.4,147.8 300.0,146.5 300.6,145.2 301.2,144.0 301.8,142.8 302.4,141.5 303.0,140.2 303.6,139.0 304.2,137.8 304.8,136.5 305.4,135.2 306.0,134.0 306.6,132.8 307.2,131.5 307.8,130.2 308.4,129.0 309.0,127.8 309.6,126.5 310.2,125.2 310.8,124.0 311.4,122.8 312.0,121.5 312.6,120.2 313.2,119.0 313.8,117.8 314.4,116.5 315.0,115.3 315.6,114.0 316.2,112.7 316.8,111.5 317.4,110.2 318.0,109.0 318.6,107.8 319.2,106.5 319.8,105.2 320.4,104.0 321.0,102.8 321.6,101.5 322.2,100.2 322.8,99.0 323.4,97.7 324.0,96.5 324.6,95.3 325.2,94.0 325.8,92.7 326.4,91.5 327.0,90.2 327.6,89.0 328.2,87.8 328.8,86.5 329.4,85.2 330.0,84.0 330.6,82.8 331.2,81.5 331.8,80.2 332.4,79.0 333.0,77.8 333.6,76.5 334.2,75.2 334.8,74.0 335.4,72.8 336.0,71.5 336.6,70.2 337.2,69.0 337.8,67.8 338.4,66.5 339.0,65.2 339.6,64.0 340.2,62.8 340.8,61.5 341.4,60.2 342.0,59.0 342.6,57.7 343.2,56.5 343.8,55.2 344.4,54.0 345.0,52.8 345.6,51.5 346.2,50.2 346.8,49.0 347.4,47.8 348.0,46.5 348.6,45.2 349.2,44.0 349.8,42.8 350.4,41.5 351.0,40.2 351.6,39.0 352.2,37.8 352.8,36.5 353.4,35.2 354.0,34.0 354.6,34.0 355.2,34.0 355.8,34.0 356.4,34.0 357.0,34.0 357.6,34.0 358.2,34.0 358.8,34.0 359.4,34.0 360.0,34.0 360.6,34.0 361.2,34.0 361.8,34.0 362.4,34.0 363.0,34.0 363.6,34.0 364.2,34.0 364.8,34.0 365.4,34.0 366.0,34.0 366.6,34.0 367.2,34.0 367.8,34.0 368.4,34.0 369.0,34.0 369.6,34.0 370.2,34.0 370.8,34.0 371.4,34.0 372.0,34.0 372.6,34.0 373.2,34.0 373.8,34.0 374.4,34.0 375.0,34.0 375.6,34.0 376.2,34.0 376.8,34.0 377.4,34.0 378.0,34.0 378.6,34.0 379.2,34.0 379.8,34.0 380.4,34.0 381.0,34.0 381.6,34.0 382.2,34.0 382.8,34.0 383.4,34.0 384.0,34.0 384.6,34.0 385.2,34.0 385.8,34.0 386.4,34.0 387.0,34.0 387.6,34.0 388.2,34.0 388.8,34.0 389.4,34.0 390.0,34.0 390.6,34.0 391.2,34.0 391.8,34.0 392.4,34.0 393.0,34.0 393.6,34.0 394.2,34.0 394.8,34.0 395.4,34.0 396.0,34.0 396.6,34.0 397.2,34.0 397.8,34.0 398.4,34.0 399.0,34.0 399.6,34.0 400.2,34.0 400.8,34.0 401.4,34.0 402.0,34.0 402.6,34.0 403.2,34.0 403.8,34.0 404.4,34.0 405.0,34.0 405.6,34.0 406.2,34.0 406.8,34.0 407.4,34.0 408.0,34.0 408.6,34.0 409.2,34.0 409.8,34.0 410.4,34.0 411.0,34.0 411.6,34.0 412.2,34.0 412.8,34.0 413.4,34.0 414.0,34.0 414.6,34.0 415.2,34.0 415.8,34.0 416.4,34.0 417.0,34.0 417.6,34.0 418.2,34.0 418.8,34.0 419.4,34.0 420.0,34.0 420.6,34.0 421.2,34.0 421.8,34.0 422.4,34.0 423.0,34.0 423.6,34.0 424.2,34.0 424.8,34.0 425.4,34.0 426.0,34.0 426.6,34.0 427.2,34.0 427.8,34.0 428.4,34.0 429.0,34.0 429.6,34.0 430.2,34.0 430.8,34.0 431.4,34.0 432.0,34.0 432.6,34.0 433.2,34.0 433.8,34.0 434.4,34.0 435.0,34.0 435.6,34.0 436.2,34.0 436.8,34.0 437.4,34.0 438.0,34.0 438.6,34.0 439.2,34.0 439.8,34.0 440.4,34.0 441.0,34.0 441.6,34.0 442.2,34.0 442.8,34.0 443.4,34.0 444.0,34.0 444.6,34.0 445.2,34.0 445.8,34.0 446.4,34.0 447.0,34.0 447.6,34.0 448.2,34.0 448.8,34.0 449.4,34.0 450.0,34.0 450.6,34.0 451.2,34.0 451.8,34.0 452.4,34.0 453.0,34.0 453.6,34.0 454.2,34.0 454.8,34.0 455.4,34.0 456.0,34.0 456.6,34.0 457.2,34.0 457.8,34.0 458.4,34.0 459.0,34.0 459.6,34.0 460.2,34.0 460.8,34.0 461.4,34.0 462.0,34.0" style="stroke:var(--accent);stroke-width:2.5;fill:none"/><text x="50.0" y="39.0" font-size="13" text-anchor="end" style="fill:var(--muted)">8×10⁻⁵</text><text x="50.0" y="189.0" font-size="13" text-anchor="end" style="fill:var(--muted)">0</text><line x1="354.0" y1="184.0" x2="354.0" y2="34.0" style="stroke:var(--muted);stroke-width:1.2;stroke-dasharray:4 4;fill:none"/><text x="318.0" y="116.5" font-size="14" text-anchor="middle" style="fill:var(--warn)">预热</text><text x="166.8" y="91.0" font-size="14" text-anchor="start" style="fill:var(--warn)">余弦衰减</text>
</svg>
<figcaption>图 12　Llama 3 405B 的学习率：前 8000 步从 0 线性升到 8×10⁻⁵，之后沿余弦曲线降到 8×10⁻⁷。左边看全程，预热只占最开始的 0.67%，几乎看不见；右边把前 2 万步放大。</figcaption>
</figure>

写成公式，$t$ 是当前步数，$T_w = 8000$ 是预热步数，$T = 1{,}200{,}000$ 是总步数：

预热阶段（$t < T_w$）：

$$
\eta(t) = \eta_{\max} \cdot \frac{t}{T_w}
$$

衰减阶段（$t \ge T_w$）：

$$
\begin{aligned}
\eta(t) &= \eta_{\min} + \frac{\eta_{\max} - \eta_{\min}}{2} \\
&\quad \times \left(1 + \cos\frac{\pi (t - T_w)}{T - T_w}\right)
\end{aligned}
$$

检查一下第二个式子的两端。刚预热完 $t = T_w$：$\cos 0 = 1$，括号里是 2，$\eta = \eta_{\min} + (\eta_{\max} - \eta_{\min}) = \eta_{\max}$，接上了预热的终点。训练结束 $t = T$：$\cos \pi = -1$，括号里是 0，$\eta = \eta_{\min}$。中间点 $\cos(\pi/2) = 0$，正好是两者的平均，约 $4.04 \times 10^{-5}$。

### 为什么开头要预热

**原因一：Adam 的第一步不管梯度大小，每个参数都走满一步。** 梯度下降那一讲说过，Adam 为每个参数记录两个平均值：梯度的平均 $m$ 和梯度平方的平均 $v$，用 $m / \sqrt{v}$ 决定步子。具体是（$g_t$ 是第 $t$ 步的梯度，$\beta_1$、$\beta_2$ 是两个接近 1 的常数，常用 0.9 和 0.95 到 0.999）：

$$
m_t = \beta_1 m_{t-1} + (1 - \beta_1)\, g_t
$$

$$
v_t = \beta_2 v_{t-1} + (1 - \beta_2)\, g_t^2
$$

开始时 $m_0 = v_0 = 0$。第一步之后 $m_1 = (1 - \beta_1) g_1$，$v_1 = (1 - \beta_2) g_1^2$。因为从 0 起步，这两个数偏小，Adam 会把它们分别除以 $1 - \beta_1$ 和 $1 - \beta_2$ 做修正，于是修正后正好是 $\hat m_1 = g_1$，$\hat v_1 = g_1^2$。第一步的步子是：

$$
\eta \cdot \frac{\hat m_1}{\sqrt{\hat v_1}} = \eta \cdot \frac{g_1}{\lvert g_1 \rvert} = \pm \eta
$$

不管某个参数的梯度是大是小，第一步都朝它的梯度方向走满整整一个 $\eta$。而这个方向只来自一批数据，平均还没攒起来，噪声很大。几千亿个参数同时按一个噪声很大的方向各走满一步，模型很容易一下子被推到很糟的地方。前几十、几百步也类似：$v$ 只平均了很少几步，还不可靠（Liu 等 2019 年的 RAdam 论文专门分析过这一点）。预热让最开始的步子很小，等两个平均值攒够了再放开。

**原因二：刚初始化时，地形更陡。** 梯度下降那一讲推过，学习率不能超过 $2/a$（$a$ 是曲率）。训练刚开始、参数还是随机数时，损失地形往往比后面陡得多，同一个学习率在开头会发散、到后面却正合适。LayerNorm 那一讲也提到，Post-Norm 的网络在初始化时靠近输出的几层梯度特别大，不预热就训不稳。

### 为什么后面要衰减

梯度下降那一讲说过：每批数据是随机抽的，梯度带着噪声，所以「到了谷底也停不稳」。这个「停不稳」可以算出来有多大。

用那一讲的碗 $L = \tfrac{1}{2} a x^2$，最低点在 $x = 0$，斜率是 $a x$。每一步的梯度再加上一个随机噪声 $\varepsilon$，它的平均是 0、方差是 $\sigma^2$，每步独立：

$$
\begin{aligned}
x_{t+1} &= x_t - \eta\,(a x_t + \varepsilon_t) \\
&= (1 - \eta a)\, x_t - \eta\, \varepsilon_t
\end{aligned}
$$

两边取方差。$x_t$ 和这一步的新噪声 $\varepsilon_t$ 无关，方差直接相加；乘一个常数 $c$，方差乘 $c^2$：

$$
\begin{aligned}
\operatorname{Var}(x_{t+1}) &= (1 - \eta a)^2 \operatorname{Var}(x_t) \\
&\quad + \eta^2 \sigma^2
\end{aligned}
$$

走了很多步之后，$x$ 在谷底附近晃，方差不再变化，记作 $V$。把 $V$ 代入两边：

$$
V = (1 - \eta a)^2\, V + \eta^2 \sigma^2
$$

把含 $V$ 的项移到左边，再把 $(1 - \eta a)^2 = 1 - 2\eta a + \eta^2 a^2$ 展开：

$$
V \bigl(2\eta a - \eta^2 a^2\bigr) = \eta^2 \sigma^2
$$

两边除以 $\eta a (2 - \eta a)$：

$$
V = \frac{\eta\, \sigma^2}{a\,(2 - \eta a)}
$$

代入 $a = 1$、$\sigma = 1$。学习率 0.1 时 $V = 0.1 / 1.9 = 0.0526$，也就是一般离谷底 $\sqrt{V} \approx 0.229$；学习率 0.01 时 $V = 0.01 / 1.99 = 0.0050$，一般离谷底 0.071。学习率小 10 倍，晃动的方差小约 10.5 倍。**学习率决定了停在谷底附近晃多大的圈**。

所以前期用大学习率快速走到谷底附近，后期把学习率降下来，让参数在谷底停得更稳、损失再降一截。余弦曲线是一种常用的降法：开头降得慢（大部分时间保持较大的学习率），结尾也降得慢（平滑地收尾）。

<details class="pause"><summary>停一下：如果整个训练都用峰值学习率、既不预热也不衰减，会出什么问题？</summary>

两头各一个问题。开头：Adam 的头几步每个参数都按一批噪声很大的梯度走满一步，地形又陡，容易损失飙升甚至变成 NaN。结尾：学习率一直很大，参数一直在谷底附近晃一个大圈（上面算的 $V$ 和 $\eta$ 成正比），损失降不下去最后那一截。实验 05 可以把三种做法放在一起比。

</details>

## 亲手训一个：页内的中文小模型

上面的 bigram 只有 7 个 token、两句话。实验 04 在页面里放了一段 654 个字的中文小语料（自编的小学生作文风格的句子），再留出一句 18 个字的话不给模型看，用来检查它在没见过的文字上猜得怎么样（这叫验证集）。词表是语料里出现过的 220 个字（加一个表示「开头」的特殊 token）。模型有两种可选：

- **bigram**：一张 220 × 220 的分数表，48,400 个参数，只看上一个字。
- **小 MLP**：看前 4 个字，每个字查一个 24 维的向量，拼起来过一个 64 个神经元的隐藏层，再输出 220 个分数，共 25,788 个参数。

训练就是本讲的那个训练步：每步随机取 32 个位置，前向、交叉熵、手写的反向传播、AdamW 更新；学习率先预热 100 步，再余弦衰减，共 2000 步。下面是默认设置下的真实结果（在 node 里用实验页的同一份代码跑出来）：

<figure class="fig">
<svg viewBox="0 0 480 258" role="img" aria-label="页内小模型的训练损失和验证损失">
<line x1="56.0" y1="210.0" x2="459.0" y2="210.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><line x1="56.0" y1="210.0" x2="56.0" y2="22.0" style="stroke:var(--line);stroke-width:1.5;fill:none"/><text x="56.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">0</text><text x="154.8" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">500</text><text x="253.5" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1000</text><text x="352.2" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">1500</text><text x="451.0" y="230.0" font-size="14" text-anchor="middle" style="fill:var(--muted)">2000</text><text x="48.0" y="155.0" font-size="14" text-anchor="end" style="fill:var(--muted)">2</text><text x="48.0" y="95.0" font-size="14" text-anchor="end" style="fill:var(--muted)">4</text><text x="48.0" y="35.0" font-size="14" text-anchor="end" style="fill:var(--muted)">6</text><text x="253.5" y="252.0" font-size="15" text-anchor="middle" style="fill:var(--muted)">训练步数</text><polyline points="56.0,48.0 60.9,52.7 65.9,71.8 70.8,106.1 75.8,141.9 80.7,169.8 85.6,185.7 90.6,194.6 95.5,200.5 100.4,203.1 105.4,204.9 110.3,206.5 115.2,206.9 120.2,207.2 125.1,207.4 130.1,207.5 135.0,208.0 139.9,208.2 144.9,207.7 149.8,208.0 154.8,208.2 159.7,207.7 164.6,207.8 169.6,208.2 174.5,208.0 179.4,208.2 184.4,208.0 189.3,207.8 194.2,208.1 199.2,208.2 204.1,208.3 209.1,208.5 214.0,208.4 218.9,208.2 223.9,208.5 228.8,208.4 233.8,208.7 238.7,208.7 243.6,208.7 248.6,208.7 253.5,208.5 258.4,208.4 263.4,208.6 268.3,208.4 273.2,208.5 278.2,208.6 283.1,208.9 288.1,208.8 293.0,208.9 297.9,208.6 302.9,208.7 307.8,208.8 312.8,208.8 317.7,208.8 322.6,208.8 327.6,208.8 332.5,208.9 337.4,208.8 342.4,209.0 347.3,209.0 352.2,209.0 357.2,208.9 362.1,208.9 367.1,209.0 372.0,209.0 376.9,209.0 381.9,209.0 386.8,209.1 391.8,209.1 396.7,209.0 401.6,209.0 406.6,209.0 411.5,209.0 416.4,209.0 421.4,209.0 426.3,209.0 431.2,209.0 436.2,209.0 441.1,209.1 446.1,209.1 451.0,209.0" style="stroke:var(--warn);stroke-width:2.5;fill:none"/><polyline points="56.0,49.4 60.9,52.5 65.9,63.3 70.8,90.0 75.8,109.2 80.7,133.4 85.6,137.2 90.6,136.7 95.5,140.5 100.4,141.4 105.4,136.5 110.3,139.2 115.2,140.5 120.2,141.3 125.1,139.4 130.1,138.8 135.0,139.9 139.9,141.1 144.9,138.8 149.8,141.1 154.8,138.5 159.7,140.4 164.6,135.2 169.6,139.0 174.5,137.6 179.4,135.3 184.4,133.5 189.3,134.3 194.2,135.4 199.2,135.8 204.1,136.0 209.1,137.0 214.0,138.3 218.9,135.6 223.9,132.7 228.8,131.6 233.8,133.3 238.7,134.2 243.6,133.6 248.6,130.6 253.5,131.8 258.4,131.7 263.4,130.8 268.3,129.8 273.2,129.3 278.2,126.4 283.1,127.0 288.1,127.9 293.0,126.7 297.9,126.2 302.9,123.8 307.8,124.4 312.8,123.2 317.7,122.9 322.6,122.0 327.6,121.6 332.5,121.1 337.4,119.2 342.4,117.4 347.3,117.2 352.2,117.0 357.2,117.9 362.1,118.2 367.1,118.3 372.0,116.8 376.9,115.8 381.9,113.9 386.8,113.7 391.8,114.7 396.7,114.5 401.6,113.9 406.6,113.0 411.5,113.2 416.4,112.7 421.4,112.3 426.3,112.1 431.2,111.3 436.2,109.9 441.1,109.5 446.1,108.6 451.0,108.4" style="stroke:var(--accent);stroke-width:2.5;stroke-dasharray:6 4;fill:none"/><text x="451.0" y="199.0" font-size="14" text-anchor="end" style="fill:var(--warn)">训练 0.03</text><text x="451.0" y="98.4" font-size="14" text-anchor="end" style="fill:var(--accent)">验证 3.39</text><circle cx="100.4" cy="141.4" r="5" style="fill:var(--accent)"/><text x="110.4" y="161.4" font-size="14" text-anchor="start" style="fill:var(--accent)">最低 2.29（第 225 步）</text><text x="66.0" y="52.0" font-size="14" text-anchor="start" style="fill:var(--muted)">开始 5.40</text>
</svg>
<figcaption>图 13　实验 04 默认设置下真实训练的结果。橙色实线是训练文字上的平均损失，蓝色虚线是留出来没给它看的一句话上的平均损失。</figcaption>
</figure>

一开始损失是 $\ln 220 \approx 5.39$：参数是随机的，220 个字差不多平均分，困惑度约 220。训练到最后，训练损失降到 0.03。模型从「我」开始往下写 30 个字，不同步数时写出来的是：

| 步数 | bigram | 小 MLP |
| --- | --- | --- |
| 0 | `我三妈时中欢师操唱西再草小养老伞图田走到坐回道写爱图农事为然养` | `我只妈候中喜操讲歌瓜业草午井师着珠田慢到边回彩写爱珠农事因然养` |
| 50 | `我三妈校中欢师讲唱西再草小乡真伞图田走秋坐回道写爱珠落事为然养` | `我棵饭学，鸡学点口很跳天上鱼有头照秋坐西公师色家爱光片事欢后奶` |
| 100 | `我帮妈草中都操场子里有门小讲老雨照农慢黄坐放停放爱灰稻故哪仗井` | `我球吃米饭，里脸在树候。我课的湖馆，回叶久叫星很爱咯在借看碗大` |
| 200 | `我讲仗地里有里收稻子里的。公园里映着伞去忙擦桌子。挂牙道彩虹和` | `我们我们去公园。今天天气了，天边挂着一道落上馆。我借了静奶讲和` |
| 500 | `我和一点。奶奶奶家，天上，刷牙，爸爸做饭，天还要早点，每天来的` | `我爱吃米饭，也爱吃面条。妈妈做的面条又长又香。老师说，多看书，` |
| 2000 | `我帮忙擦桌子。农民伯伯在门前，同学。公园。学校里跑步。明天天边` | `我爱吃米饭，也爱吃面条。妈妈做的面条又长又香。老师说，多看书，` |

可以看到几个阶段：一开始是乱码（每个字随机挑）；接着学会了哪些字常出现、哪些字常挨着（「公园」「天气」）；再往后能写出整句话，标点也放对了位置。bigram 只看上一个字，最后也只能做到词语通顺、句子不通（「奶奶奶家」这种重复，它分不清是第几个「奶」），训练损失停在 1.36 左右。

小 MLP 有个问题：它最后写出的句子，几乎是原文一字不差。看图 13 的蓝线：验证损失在第 225 步降到最低 2.29，之后反而一路涨到 3.39。语料只有六百多个字，而模型有两万多个参数，它最省事的办法是把原文**背下来**，背得越熟，碰到没见过的句子越不会猜。这就是预训练需要海量、去过重的数据的原因：数据多到背不下来，模型只能去学文字背后的规律。真实的大模型，大部分数据只读一遍左右，训练损失和验证损失几乎重合。

## 模型在预训练里学到了什么

预训练的目标只有「猜下一个 token」，但要把几万亿个 token 都猜准，模型必须学会很多东西：

- **语法和用词。** 「我爱吃米」后面接「饭」，不接「爱」。小模型在两百步之内就学会了常见的字词搭配。对大模型做探测的研究（比如 Tenney 等 2019 年对 BERT 的分析）发现，网络的不同层里能读出词性、句法结构这类信息，没有任何人教过它们。
- **事实。** 要猜准「法国的首都是」后面那个词，模型必须记住这件事。Petroni 等 2019 年把语言模型当作知识库来查，用填空的方式问它事实，发现预训练模型里存了大量事实性知识。我们的 bigram 学到的「米后面一半是饭、一半是粥」，就是一条从数据里统计出来的「知识」。
- **推理的雏形。** 训练文字里有大量解题过程、论证、代码。为了猜准解题过程的下一步，模型要摸到一点推理的门道。GPT-2 的论文发现，只做预训练的模型已经能在没有专门训练的情况下做一些阅读理解、翻译和摘要；Wei 等 2022 年发现，足够大的预训练模型在提示里给几个「一步一步写出推理过程」的例子，就能在数学应用题上做得好得多。

但模型学会的始终是**模仿训练文字往下写**。网页上「17 × 3 等于多少？」这样的句子，后面跟着的往往是下一道练习题，所以预训练出来的模型读到一个问题，很可能接着出题，而不是回答。它有知识，但不知道自己该当一个回答问题的助手。把它变成助手，要在预训练之后再做一轮训练，这是后面「后训练」那一讲的内容。

## 实验里讲了什么

1. **一句话拆成训练样本。** 输入任意一句话，看它拆成多少个「前文 → 下一个」的样本，以及因果遮罩里每个位置能看到什么。
2. **交叉熵计算器。** 拖动「我爱吃米饭。」5 个位置上正确答案的概率，看每个位置的 $-\ln p$、平均损失、整句概率和困惑度怎么变。
3. **一个训练步。** 本讲的 bigram 表和两句话：一步一步走，看前向的概率、梯度 $p - y$、更新后的「米」那一行，以及损失逼近下限 0.139。
4. **在中文小语料上真实训练。** 选 bigram 或小 MLP，看训练损失和验证损失的曲线，以及生成的文字从乱码变通顺、再变成背原文；可以换学习率调度、从任意开头往下写。
5. **学习率调度。** 拖动峰值、预热步数和衰减终点，看 warmup + cosine 曲线（默认是 Llama 3 405B 的设置）；再在带噪声的碗上比较不衰减、余弦衰减两种做法，最后停在谷底附近晃多大的圈。
6. **数据配比。** GPT-3 五个数据源的数据量与抽样比例、每个来源读了几遍；Llama 3 按内容类别的配比。

## 和前后两讲的关系

前面几讲把训练的零件一个个拆开讲了：梯度下降怎么更新参数，残差连接和 LayerNorm 怎么让深网络训得动，反向传播怎么算梯度。上一讲是 LayerNorm。这一讲把它们装成一台完整的机器：给它几万亿个 token 和一个目标「猜下一个」，一批一批地转起来。下一讲是 Scaling Laws：模型参数、数据量和算力之间有什么规律，同样多的算力，该训多大的模型、喂多少数据。再往后，LoRA 和后训练两讲讲预训练之后的事：怎么只改一点参数去适应新任务，怎么把只会续写的基座模型变成助手。

## 延伸阅读

- Llama Team, AI @ Meta, *The Llama 3 Herd of Models* (2024)，第 3 节：数据清洗、去重、配比、退火与学习率设置
- Guilherme Penedo et al., *The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale* (2024)
- Tom B. Brown et al., *Language Models are Few-Shot Learners* (2020)，表 2.2 是 GPT-3 的数据配比
- Alec Radford et al., *Language Models are Unsupervised Multitask Learners* (2019)，GPT-2
- Liyuan Liu et al., *On the Variance of the Adaptive Learning Rate and Beyond* (2019)，RAdam，分析 Adam 为什么需要预热
- Andrei Z. Broder, *On the Resemblance and Containment of Documents* (1997)，MinHash 的出处
- Fabio Petroni et al., *Language Models as Knowledge Bases?* (2019)
- Andrej Karpathy, *makemore*，从 bigram 到 MLP 的字符级语言模型，实验 04 的结构与它相同
