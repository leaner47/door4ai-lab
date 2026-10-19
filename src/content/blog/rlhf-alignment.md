---
title: "RLHF 与偏好对齐：模型是怎么学会「好好说话」的"
description: "预训练模型只会续写，要经过监督微调和偏好对齐才会好好回答。同一个问题两个回答、人选一个：用 Bradley–Terry 把成对偏好变成分数，训练奖励模型，再用 PPO 加 KL 惩罚去优化，看它怎么被钻空子；DPO 跳过奖励模型一步到位；最后是 AI 反馈和可验证奖励。六个可交互实验。"
pubDate: 2026-10-17
tags: ["训练", "对齐", "RLHF", "奖励模型", "DPO", "强化学习"]
lab: /labs/rlhf-alignment/
series: ai-mastery
order: 42
---

## 一句话版本

人很难写出「什么是好回答」的公式，但看到两个回答，很容易说出哪个更好。偏好对齐就是利用这一点：收集大量「同一个问题、两个回答、人选一个」的数据，先训练一个**奖励模型**学会给回答打分，再用强化学习让模型朝高分方向改，同时用一根 **KL 绳子**拴住它，不让它离原来的模型太远：

<p class="formula">最大化　E[<i>r</i>(<i>x</i>, <i>y</i>)] − <i>β</i> · KL(<i>π</i> ‖ <i>π</i><sub>ref</sub>)</p>

这套做法叫 RLHF（Reinforcement Learning from Human Feedback，基于人类反馈的强化学习）。DPO 是它的简化版：不单独训练奖励模型，直接用偏好对改模型。

## 预训练模型只会续写

前面几讲说的训练，是让模型在海量文本上预测下一个 token。这样训出来的模型知识很多，但它学会的是「接着写」：你问「怎么煮溏心蛋」，它可能接着写出五个类似的问题，因为网页上问题常常扎堆出现。它不知道自己该回答，更不知道怎样的回答算好。

所以现在的对话模型都要再经过两段训练，合起来是三段式（实验 05 有两个公开模型的数据量）：

1. **预训练**：几万亿 token 的文本，目标是预测下一个 token。Llama 2 用了 2 T token。
2. **监督微调（SFT）**：人写的「问题 + 示范回答」，还是交叉熵损失，模型照着学，学会按指令回答的格式。量不大：InstructGPT 约 1.3 万条，Llama 2-Chat 是 27 540 条。
3. **偏好对齐**：人不再写答案，只在模型自己的几个回答里挑好的。Llama 2-Chat 收集了超过 140 万次这样的二选一比较。

第 2 步之后模型已经会回答了，但回答得好不好、该详细还是简洁、遇到危险请求怎么拒绝，示范数据教不全：示范只告诉模型「一个」好回答长什么样，没告诉它「为什么这个比那个好」。第 3 步补的就是这个。InstructGPT 论文里，标注员更喜欢经过三段训练的 1.3 B 模型，而不是只做了预训练的 175 B GPT-3。

## 把「哪个更好」变成一个分数

偏好数据长这样：同一个 prompt，模型生成两个回答，标注员选一个。要从里面学东西，先得把「A 比 B 好」变成能求导的数。办法是假设每个回答有一个分数 <i>r</i>，人选 A 的概率只取决于分数差：

<p class="formula">P(A 胜 B) = σ(<i>r</i><sub>A</sub> − <i>r</i><sub>B</sub>)</p>

σ 是 sigmoid，把任意实数压到 0 到 1 之间。这叫 Bradley–Terry 模型，1952 年提出，本来是给比赛排名用的。

<figure class="clip"><video src="/videos/rlhf-alignment/PreferencePair.webm" poster="/videos/rlhf-alignment/PreferencePair.png" controls loop muted playsinline preload="metadata"></video></figure>

评测那一讲的 Arena Elo 就是同一个模型：Elo 公式里的 1 / (1 + 10<sup>−<i>D</i>/400</sup>) 和 σ 只差一个换底，Elo 分差 = 400 / ln 10 × <i>r</i> 的差，约 174 倍。

**奖励模型**就是一个读入 (prompt, 回答)、输出一个分数的网络，通常拿 SFT 模型改：去掉预测 token 的输出层，换成输出一个数。训练它只需要让「人选中的那个」分数更高：

<p class="formula">损失 = −log σ(<i>r</i>(<i>x</i>, <i>y</i><sub>w</sub>) − <i>r</i>(<i>x</i>, <i>y</i><sub>l</sub>))</p>

<i>y</i><sub>w</sub> 是被选中的回答，<i>y</i><sub>l</sub> 是落选的。这就是一个二分类的逻辑回归，用梯度下降训练。实验 00 从 200 次对局里拟合出 5 个回答的分数，实验 01 训练一个只有三个权重的小奖励模型：如果标注员对长回答有一点偏爱，奖励模型会把这点偏爱原样学走。

## 用强化学习往高分走，用 KL 拴住

有了奖励模型，就能对任何新回答打分，不再需要人在旁边。接下来让模型（这时叫**策略** <i>π</i>）对一批 prompt 生成回答，奖励模型打分，按分数更新参数，再生成、再打分，反复循环。生成回答这一步是采样，不能直接对它求导，所以要用强化学习的办法，InstructGPT 和 Llama 2-Chat 用的是 PPO（Proximal Policy Optimization，Schulman 等，2017）。

<figure class="clip"><video src="/videos/rlhf-alignment/RLHFLoop.webm" poster="/videos/rlhf-alignment/RLHFLoop.png" controls loop muted playsinline preload="metadata"></video></figure>

光往高分走会出事，所以目标里还有一项 KL 惩罚：KL(<i>π</i> ‖ <i>π</i><sub>ref</sub>) 衡量现在的策略和参考模型（SFT 之后的模型）的输出分布差多远，<i>β</i> 是绳子的松紧。它有两个作用。第一，奖励模型只在它见过的那类回答上打分可靠，策略跑得太远，进入奖励模型没见过的区域，分数就不可信了。第二，SFT 模型学会的语言能力和知识不能丢，不能为了讨好奖励模型把话都说不利索了。

这个目标有一个干净的最优解：<i>π</i>* ∝ <i>π</i><sub>ref</sub> · e<sup><i>r</i>/<i>β</i></sup>。参考模型原来的概率，按奖励的指数加权。<i>β</i> 越小，越往高分的回答集中；<i>β</i> 越大，越像参考模型。实验 03 在 5 种回答风格上真实地做这个优化，并和这个解析解对照。

这一步也常用上一讲的 LoRA 来做：底座冻住、只训练 LoRA，参考模型就是关掉 LoRA 的同一个底座，不必在显存里再放一份完整模型。

## 奖励黑客：模型会钻空子

奖励模型只是人的偏好的一个近似，而强化学习非常擅长找近似里的漏洞。这叫**奖励黑客**（reward hacking）。最常见的一种是越写越长：标注员往往觉得长一点的回答更认真，奖励模型学到了「长 = 好」，策略就发现多写几段最容易涨分。Singhal 等（2023）的分析发现，在他们研究的其中两个设置里，PPO 带来的奖励提升有 70%–90% 来自回答变长；只按长度给奖励，就能复现大部分效果。

Gao、Schulman、Hilton（2022）做了一个干净的实验：用一个大的「金标准」奖励模型扮演人，用一个小的代理奖励模型去训练策略。优化越多，代理分数一直在涨，金标准分数先涨后跌。这就是评测那一讲的 Goodhart 定律：一个度量一旦成为优化目标，就不再是好的度量。实验 02 用两个旋钮复现了这条先升后降的曲线。

KL 惩罚、更好的奖励模型（更多数据、按长度做校正）、及早停止，都是在跟这件事对抗。

## DPO：不训练奖励模型，直接用偏好对

RLHF 要训两个模型、跑一个强化学习循环，调参很麻烦。Rafailov 等（2023）注意到，上面那个最优解可以倒过来写：

<p class="formula"><i>r</i>(<i>x</i>, <i>y</i>) = <i>β</i> log <i>π</i>*(<i>y</i>|<i>x</i>) / <i>π</i><sub>ref</sub>(<i>y</i>|<i>x</i>) + 常数</p>

也就是说，策略自己就隐含着一个奖励：一个回答的概率比参考模型高了多少，就说明它被「奖励」了多少。把这个隐式奖励代进奖励模型的 Bradley–Terry 损失，常数在两个回答相减时消掉，得到 DPO（Direct Preference Optimization）的损失：

<p class="formula">−log σ( <i>β</i> log <i>π</i>(<i>y</i><sub>w</sub>|<i>x</i>)/<i>π</i><sub>ref</sub>(<i>y</i><sub>w</sub>|<i>x</i>) − <i>β</i> log <i>π</i>(<i>y</i><sub>l</sub>|<i>x</i>)/<i>π</i><sub>ref</sub>(<i>y</i><sub>l</sub>|<i>x</i>) )</p>

直觉是：让被选中的回答的概率相对参考模型升高，让落选的降低，<i>β</i> 控制愿意偏离参考模型多远。训练只需要对偏好数据做普通的梯度下降，像 SFT 一样简单，不用采样、不用奖励模型。论文的副标题就是「你的语言模型其实是一个奖励模型」。

实验 04 用同一组偏好对，一边走 RLHF 的两步（拟合奖励 + KL 优化），一边直接最小化 DPO 损失，两者得到的分布重合到浮点误差。这在理论上成立；实际中两者会有差别，因为 DPO 只在现成的偏好数据上学，而 RLHF 会不断用当前策略生成新回答再打分。

## 让 AI 给反馈：RLAIF 与 Constitutional AI

人工标注贵、慢，还会累。一个自然的想法是让一个强模型代替人来比较两个回答，这叫 RLAIF（Reinforcement Learning from AI Feedback）。

Anthropic 的 Constitutional AI（Bai 等，2022）是这条路的代表：先写下一套自然语言的原则（「宪法」），比如要求回答无害、不协助危险的请求。第一阶段，模型按某条原则批评自己的回答、改写，再用改写后的回答做监督微调；第二阶段，让模型按原则判断两个回答哪个更好，用这些 AI 给出的偏好训练偏好模型，再做强化学习。论文里，「无害」方面的偏好标签全由 AI 生成，「有用」方面仍用人工标注。好处是规则写在明处，改原则就能改行为。Google 的 Lee 等（2023）在摘要、对话等任务上比较了 RLAIF 与 RLHF，效果相当。

## 有标准答案时：可验证奖励

数学题有标准答案，代码可以跑测试。这类任务不需要奖励模型去「猜」人喜欢什么，直接用程序判对错当奖励：对了给分，错了不给。AI2 的 Tülu 3（Lambert 等，2024）把它叫作 RLVR（Reinforcement Learning with Verifiable Rewards），用于数学和精确遵循指令。

这正是推理模型的主要训练方式。DeepSeek-R1（2025）的 R1-Zero 版本直接在基座模型上做强化学习，不先做 SFT，奖励全部是规则：答案对不对（数学题核对答案、代码跑测试）、格式对不对（思考过程放在指定标签里）。他们特意不用神经网络奖励模型，理由正是它容易被钻空子。只靠这种奖励，模型自己学会了写长长的推理过程、回头检查，AIME 2024 的 pass@1 从 15.6% 涨到 71.0%。算法是 GRPO：同一道题采样一组回答，用组内平均分当基准，好于平均的回答被加强，同样带 KL 惩罚。

可验证奖励也不是万能的：它只覆盖有标准答案的任务，「写一封得体的拒绝邮件」仍然要靠人或 AI 的偏好。

## 实验里讲了什么

0. **Bradley–Terry**：拖分数差看偏好概率和对应的 Elo 分差；再用梯度上升从 200 次对局里拟合出 5 个回答的分数，对照观测胜率与拟合胜率。
1. **奖励模型**：用模拟标注员的成对偏好训练一个三特征线性奖励模型；标注员每百字多给 0.3 分，奖励模型就学到约 0.3 的长度权重。
2. **奖励黑客**：策略沿奖励模型的梯度调长度和认真程度，奖励一路涨，真实质量在第 94 步左右见顶后下跌。
3. **KL 惩罚**：5 种回答风格上的真实优化，拖 <i>β</i> 看分布离参考模型多远、期望奖励和真实质量怎么变，并与解析解对照。
4. **DPO**：同一组偏好对，直接最小化 DPO 损失，结果与「奖励模型 + KL 优化」重合，隐式奖励差等于奖励模型分差。
5. **三段式**：InstructGPT 与 Llama 2-Chat 三个阶段的数据长什么样、有多少（数字取自论文）。

## 和前后两讲的关系

梯度下降那一讲给了训练的基本动作；奖励模型和 DPO 本质上都是在偏好数据上做梯度下降，只是损失换成了 Bradley–Terry。上一讲的 LoRA 说的是怎么便宜地改一个训练好的模型，这一讲说的是往哪个方向改：SFT 教格式，偏好对齐教好坏，而且这一步本身也常用 LoRA 来做。对齐之后模型是不是真的变好了、有没有只是学会了讨好奖励模型，下一讲讲模型评测，Arena 的 Elo 和这里的 Bradley–Terry 是同一回事。

## 延伸阅读

- Paul Christiano et al., *Deep Reinforcement Learning from Human Preferences* (2017)，用人类偏好训练奖励模型的早期工作
- Long Ouyang et al., *Training Language Models to Follow Instructions with Human Feedback* (2022)，InstructGPT，三段式的经典描述
- Hugo Touvron et al., *Llama 2: Open Foundation and Fine-Tuned Chat Models* (2023)，第 3 节详细写了 SFT、奖励模型和 RLHF 的数据与做法
- Leo Gao, John Schulman, Jacob Hilton, *Scaling Laws for Reward Model Overoptimization* (2022)
- Prasann Singhal et al., *A Long Way to Go: Investigating Length Correlations in RLHF* (2023)
- Rafael Rafailov et al., *Direct Preference Optimization: Your Language Model is Secretly a Reward Model* (2023)
- Yuntao Bai et al., *Constitutional AI: Harmlessness from AI Feedback* (2022)
- Harrison Lee et al., *RLAIF vs. RLHF: Scaling Reinforcement Learning from Human Feedback with AI Feedback* (2023)
- Nathan Lambert et al., *Tülu 3: Pushing Frontiers in Open Language Model Post-Training* (2024)，RLVR 一词的出处
- DeepSeek-AI, *DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning* (2025)
