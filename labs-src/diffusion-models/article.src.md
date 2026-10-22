---
title: "扩散模型：AI 是怎么从一片噪声里画出图的"
description: "文生图模型不是一笔一笔画，而是从一片随机噪声出发，一步步把噪声擦掉。用一张只有两个像素的小图，一步步走完：前向加噪和噪声调度、训练目标「猜噪声」、往回走一步的公式、采样步数与 DDIM、潜空间扩散、交叉注意力和 classifier-free guidance，最后看现在的扩散 Transformer 与流匹配。"
pubDate: 2026-10-22
tags: ["扩散模型", "DDPM", "Stable Diffusion", "文生图"]
lab: /labs/diffusion-models/
series: ai-mastery
order: 50
---

<!-- 本文由 labs-src/diffusion-models/toy.py 从 article.src.md 生成（随机抽样的部分来自 mc.mjs，用的是实验页同一份 core.js）。改文章请改 article.src.md 再运行脚本。 -->

## 一句话版本

扩散模型先学会一件很窄的事：**给它一张加了噪声的图，它猜出加进去的噪声是什么**。训练时，我们拿真图一步步加噪声，直到变成一片纯噪声，然后让网络在每一步猜噪声。画图时反过来：从一片纯随机的噪声出发，每一步让网络猜一下「这里面哪些是噪声」，减掉一点，重复几十到上千次，噪声被一点点擦掉，剩下的就是一张新图。文字通过注意力进到网络里，告诉它往哪个方向擦。

下面用一张只有两个像素的小图，把这条路一步一步走完。

## 第一步：一张只有两个像素的「图」

上一讲说过，图在电脑里是一张数字表。扩散模型的论文（DDPM，Ho 等 2020）先把每个像素从 0 到 255 线性换算到 $-1$ 到 $1$：$-1$ 是黑，$1$ 是白，$0$ 是中灰。我们也这样做。

为了能画在纸上，我们的图只有两个像素：左像素和右像素。一张图就是两个数，比如

$$
x_0 = (0.7,\ -0.7)
$$

左像素 0.7（很亮），右像素 $-0.7$（很暗），这是一张「左边亮」的图。下标 0 的意思是「还没加噪声」。

两个数可以画成平面上的一个点：横坐标是左像素，纵坐标是右像素。训练数据是很多张这样的图，有的「左边亮」，有的「右边亮」，每张都有一点点不同：

{{fig1}}

右下那团的中心是 $(0.7,\ -0.7)$，左上那团的中心是 $(-0.7,\ 0.7)$，每团的点围着中心散开，散开的程度（标准差）是 0.1。真实的图有几十万个像素，就是几十万维空间里的一个点，道理一样，只是画不出来。

**生成一张图**，在这个平面上就是：**在点密的地方挑一个新点**。挑到右下那团里，就是一张新的「左边亮」的图。模型要学的，就是这些点长什么样。

## 第二步：往图上加一点噪声

**噪声** $\varepsilon$（读作 epsilon）是一组随机数，每个数都独立地从**标准正态分布**里抽：平均是 0，标准差是 1，大多数落在 $-2$ 到 $2$ 之间。我们的图有两个像素，所以 $\varepsilon$ 也是两个数。比如抽到

$$
\varepsilon_1 = (0.6,\ -0.2)
$$

加一步噪声的公式是：

$$
x_1 = \sqrt{\alpha_1}\;x_0 + \sqrt{\beta_1}\;\varepsilon_1
$$

$$
\alpha_1 + \beta_1 = 1
$$

$\beta_1$ 是这一步加多少噪声，是一个 0 到 1 之间的小数；$\alpha_1 = 1 - \beta_1$。我们先取 $\beta_1 = 0.1$，那么 $\alpha_1 = 0.9$，$\sqrt{0.9} = 0.9487$，$\sqrt{0.1} = 0.3162$。逐个像素代进去。左像素：

$$
\begin{aligned}
&0.9487 \times 0.7 + 0.3162 \times 0.6 \\
&= {{n:x1a}} + {{n:x1b}} = 0.8538
\end{aligned}
$$

右像素：

$$
\begin{aligned}
&0.9487 \times (-0.7) \\
&\quad + 0.3162 \times (-0.2) \\
&= -{{n:x1a}} {{n:x1c}} = -0.7273
\end{aligned}
$$

所以 $x_1 = {{n:x1}}$。

{{fig2}}

为什么不直接 $x_0 + \varepsilon_1$，而要先把 $x_0$ 乘一个比 1 小的 $\sqrt{0.9}$？因为要让数字的「大小」不随加噪变大。一组数散开的程度用**方差**（标准差的平方）衡量。两个互不相关的随机量相加，方差相加；一个随机量乘以 $k$，方差乘以 $k^2$。假设图的方差是 1（像素在 −1 到 1 之间，量级差不多），噪声的方差正好是 1，那么

$$
\begin{aligned}
\operatorname{Var}(x_1) &= (\sqrt{0.9})^2 \times 1 \\
&\quad + (\sqrt{0.1})^2 \times 1 \\
&= 0.9 + 0.1 = 1
\end{aligned}
$$

加完一步，方差还是 1。如果不缩小，每步方差加 1，加一千步就是一千，数字越来越大，网络很难处理。先缩小再加噪，让图一点点「褪色」成噪声，而不是被噪声越堆越大。

## 第三步：一步步加到底，和一步到位的公式

接着加。每一步都用同一个公式，只是 $\beta$ 不同、噪声重新抽：

$$
x_t = \sqrt{\alpha_t}\;x_{t-1} + \sqrt{\beta_t}\;\varepsilon_t
$$

$t$ 是第几步。手算用的小例子只走 4 步，四步的 $\alpha$ 取 0.9、0.8、0.5、0.25（对应 $\beta$ 是 0.1、0.2、0.5、0.75，越往后加得越多）。四步的新噪声依次是 $\varepsilon_1 = (0.6,\ -0.2)$、$\varepsilon_2 = (-1.2,\ 0.9)$、$\varepsilon_3 = {{n:e3}}$、$\varepsilon_4 = (-0.5,\ -0.8)$。逐步代进去，得到 $x_1 = {{n:x1}}$，$x_2 = {{n:x2s}}$，$x_3 = {{n:x3s}}$，$x_4 = {{n:x4s}}$。

{{fig3}}

训练时要在任意一步上取样，一步步算太慢。好在可以一步跳到第 $t$ 步。把前两步写在一起：

$$
\begin{aligned}
x_2 &= \sqrt{\alpha_2}\;x_1 + \sqrt{\beta_2}\;\varepsilon_2 \\
&= \sqrt{\alpha_2}\,\bigl(\sqrt{\alpha_1}\;x_0 + \sqrt{\beta_1}\;\varepsilon_1\bigr) \\
&\qquad + \sqrt{\beta_2}\;\varepsilon_2 \\
&= \sqrt{\alpha_1 \alpha_2}\;x_0 \\
&\qquad + \sqrt{\alpha_2 \beta_1}\;\varepsilon_1 + \sqrt{\beta_2}\;\varepsilon_2
\end{aligned}
$$

第二、三行把 $x_1$ 的式子代进去，第四、五行把括号乘开。$x_0$ 前面的系数是 $\sqrt{0.9 \times 0.8} = \sqrt{0.72}$。最后一行是**噪声部分**：两个独立噪声的和，用上一步的方差规则：

$$
\begin{aligned}
\alpha_2 \beta_1 + \beta_2 &= 0.8 \times 0.1 + 0.2 \\
&= 0.28 = 1 - 0.72
\end{aligned}
$$

正态分布有一个好性质：两个独立的正态随机量相加，结果还是正态的。所以这个噪声部分就等于「一个新的标准正态噪声乘以 $\sqrt{0.28}$」。把一路乘下来的 $\alpha$ 记作 $\bar\alpha_t$（读作 alpha bar）：

$$
\bar\alpha_t = \alpha_1 \alpha_2 \cdots \alpha_t
$$

每多走一步，同样的推导都成立（新的噪声方差 $= \alpha_t(1 - \bar\alpha_{t-1}) + \beta_t = \alpha_t - \bar\alpha_t + 1 - \alpha_t = 1 - \bar\alpha_t$），所以任意一步都可以一步到位：

$$
x_t = \sqrt{\bar\alpha_t}\;x_0 + \sqrt{1 - \bar\alpha_t}\;\varepsilon
$$

这里的 $\varepsilon$ 是一个标准正态噪声，代表前 $t$ 步噪声合起来的总效果。我们的例子里 $\bar\alpha_3 = 0.9 \times 0.8 \times 0.5 = 0.36$，$\sqrt{0.36} = 0.6$，$\sqrt{1 - 0.36} = 0.8$。前三步的噪声合起来，正好是 $0.8 \times (-1,\ 0.5)$（$\varepsilon_3$ 就是这样选的），也就是 $\varepsilon = (-1,\ 0.5)$：

$$
\begin{aligned}
x_3 &= 0.6 \times (0.7,\ -0.7) \\
&\qquad + 0.8 \times (-1,\ 0.5) \\
&= (0.42 - 0.8,\ \ -0.42 + 0.4) \\
&= {{n:x3}}
\end{aligned}
$$

和一步步算出来的 $x_3$ 是同一个点。这个 $x_3$ 和 $\varepsilon = (-1,\ 0.5)$ 会一直用到最后。

<details class="pause"><summary>停一下：第 4 步之后 ᾱ 是多少？原图还剩几成？</summary>

$\bar\alpha_4 = 0.36 \times 0.25 = 0.09$。原图的系数是 $\sqrt{0.09} = 0.3$，噪声的系数是 $\sqrt{0.91} = 0.954$。原图只剩三成，噪声占了绝大部分，但还没有完全变成噪声。真实模型要走到原图几乎为 0，所以要多走很多步（下一步）。

</details>

## 第四步：真实的噪声调度

每一步加多少噪声（$\beta_1, \beta_2, \dots$）叫**噪声调度**。DDPM 论文用的是：一共 $T = 1000$ 步，$\beta_t$ 从 $\beta_1 = 10^{-4}$ 线性增加到 $\beta_{1000} = 0.02$：

$$
\beta_t = 10^{-4} + (0.02 - 10^{-4}) \cdot \frac{t - 1}{999}
$$

每一步只加很少的噪声，但一千步乘下来，$\bar\alpha_{1000} = {{n:abT}}$，原图的系数 $\sqrt{\bar\alpha_{1000}} = {{n:sabT}}$，不到百分之一。几个中间值：$\bar\alpha_{100} = {{n:ab100}}$，$\bar\alpha_{250} = {{n:ab250}}$，$\bar\alpha_{500} = {{n:ab500}}$（原图系数 {{n:sab500}}）。

{{fig4}}

{{fig5}}

看图 5：同一批 300 张图一起加噪。到 $t = 1000$，所有的点混成一团以原点为中心、标准差为 1 的「云」，原来的两团完全看不出来。这正是我们要的终点：**纯噪声是我们知道怎么抽的分布**。画图时，就从这团云里随便抽一个点出发。

调度不止一种。Nichol 和 Dhariwal（2021）指出线性调度的最后一段噪声太多、对生成质量贡献很小（跳过最后 20% 的反向步，FID 几乎不变），提出了**余弦调度**，让 $\bar\alpha_t$ 按余弦曲线下降。实验 01 可以切换两种调度对比。Stable Diffusion v1 的配置用的是另一组线性参数（$\beta$ 从 0.00085 到 0.012，也是 1000 步）。

## 第五步：训练目标：猜噪声

现在反过来想：如果有人给你 $x_3 = {{n:x3}}$，并告诉你 $t = 3$，你能猜出原图吗？

一步到位的公式只有两个未知：$x_0$ 和 $\varepsilon$。知道其中一个，就能解出另一个。把公式移项：

$$
x_0 = \frac{x_t - \sqrt{1 - \bar\alpha_t}\;\varepsilon}{\sqrt{\bar\alpha_t}}
$$

代入真实噪声 $\varepsilon = (-1,\ 0.5)$。先算分子 $x_3 - 0.8\,\varepsilon$，$0.8\,\varepsilon = (-0.8,\ 0.4)$：

$$
\begin{aligned}
&(-0.38,\ -0.02) - (-0.8,\ 0.4) \\
&= (0.42,\ -0.42)
\end{aligned}
$$

再除以 0.6：

$$
x_0 = \frac{(0.42,\ -0.42)}{0.6} = {{n:x0back}}
$$

正是原图。**猜出噪声，就等于猜出了原图**。所以扩散模型的网络只做一件事：输入加了噪的图 $x_t$ 和步数 $t$，输出它对噪声的猜测，记作 $\varepsilon_\theta(x_t, t)$。$\theta$ 是网络的全部参数；网络在 DDPM 里是一个 U-Net（一种卷积网络），后面会看到它也可以是 Transformer。

怎么训练？和前面几讲一样，定一个损失，用梯度下降把它压低。DDPM 的训练循环是：

1. 从训练数据里取一张图 $x_0$；
2. 从 1 到 $T$ 里均匀地随机取一个步数 $t$；
3. 抽一个标准正态噪声 $\varepsilon$；
4. 用一步到位的公式算出 $x_t$；
5. 让网络猜噪声，损失是猜的和真的差的平方：

$$
L = \bigl\lVert\, \varepsilon - \varepsilon_\theta(x_t,\ t) \,\bigr\rVert^2
$$

6. 反向传播算梯度，更新 $\theta$，回到第 1 条。

$\lVert\cdot\rVert^2$ 是把每个像素上的差平方再加起来。我们的例子里，假设网络猜的是 $\hat\varepsilon = {{n:eh}}$（这个数从哪来，下一步会算），损失是

$$
\begin{aligned}
L &= (-1 - (-0.3519))^2 \\
&\qquad + (0.5 - (-0.1453))^2 \\
&= 0.6481^2 + 0.6453^2 = {{n:lossEh}}
\end{aligned}
$$

{{fig6}}

DDPM 论文把这个损失叫 $L_\text{simple}$，把很多张图、很多个随机的 $t$ 上的损失取平均：

$$
L_\text{simple} = \mathbb{E}_{x_0,\ t,\ \varepsilon}\Bigl[\, \bigl\lVert\, \varepsilon - \varepsilon_\theta(x_t,\ t) \bigr\rVert^2 \Bigr]
$$

$$
x_t = \sqrt{\bar\alpha_t}\,x_0 + \sqrt{1 - \bar\alpha_t}\,\varepsilon
$$

$\mathbb{E}$ 表示「对随机取的 $x_0$、$t$、$\varepsilon$ 取平均」。为什么猜噪声而不直接猜原图？两者能互相换算（上面的移项），数学上等价；但噪声在每一步都是标准差为 1 的数，大小稳定，网络好学。DDPM 论文实测这样训出来的图最好（CIFAR-10 上 FID 3.17）。第七步会推出：这个损失正好就是「让往回走的每一步走对」。

## 第六步：最好的猜法也猜不准

网络只看到 $x_3 = {{n:x3}}$，看不到原图。原图可能来自「左边亮」那团，也可能来自「右边亮」那团。它能做到的最好，是猜**平均下来最准**的那个值。下面把这个「最好的猜法」算出来；实验页里大部分实验用的就是它（标明「解析最优预测」），它是一个完美训练的网络能达到的极限。

**第 1 小步：如果知道原图来自哪一团。** 假设来自「左边亮」，中心 $\mu_A = (0.7,\ -0.7)$。那么 $x_3$ 离「缩小后的中心」$0.6\,\mu_A = (0.42,\ -0.42)$ 的偏差

$$
\begin{aligned}
d_A &= (-0.38,\ -0.02) \\
&\quad - (0.42,\ -0.42) \\
&= {{n:dA}}
\end{aligned}
$$

由两部分组成：原图偏离中心的部分（乘了 0.6，方差 $0.36 \times 0.1^2 = 0.0036$），和噪声部分（乘了 0.8，方差 $0.64$）。总方差 $v = 0.0036 + 0.64 = {{n:v3}}$。两个独立的正态量相加后，看到总和，每一部分「平均分到多少」按方差比例分：噪声部分平均分到偏差的 $0.64 / {{n:v3}}$。噪声部分是 $0.8\,\varepsilon$，所以 $0.8\,\hat\varepsilon_A = \frac{0.64}{v}\,d_A$，两边除以 0.8：

$$
\begin{aligned}
\hat\varepsilon_A &= \frac{0.8}{v}\, d_A \\
&= {{n:sb3v}} \times {{n:dA}} \\
&= {{n:eA}}
\end{aligned}
$$

几乎就是真实的 $(-1,\ 0.5)$：只要知道团，猜得很准。同样，假设来自「右边亮」：$d_B = {{n:dB}}$，$\hat\varepsilon_B = {{n:eB}}$。

**第 2 小步：两团各有多大可能。** 每团加噪后在 $x_3$ 附近的密度，和 $e^{-\lVert d \rVert^2 / (2v)}$ 成正比（两团的 $v$ 相同，前面的常数约掉了）：

| 团 | $\lVert d \rVert^2$ | $\lVert d \rVert^2 / (2v)$ | $e^{-(\cdot)}$ | 可能性 $r$ |
| --- | --- | --- | --- | --- |
| 左边亮 | {{n:d2A}} | {{n:argA}} | {{n:expA}} | {{n:rApct}} |
| 右边亮 | {{n:d2B}} | {{n:argB}} | {{n:expB}} | {{n:rBpct}} |

可能性 = 自己的 $e^{-(\cdot)}$ 除以两团之和，比如左边亮是 ${{n:expA}} / ({{n:expA}} + {{n:expB}}) = {{n:rApctTex}}$。两团的训练图一样多，所以不用再乘别的权重。$x_3$ 离右边亮那团更近，可能性反而更大。

**第 3 小步：加权平均。**

$$
\begin{aligned}
\hat\varepsilon &= r_A\,\hat\varepsilon_A + r_B\,\hat\varepsilon_B \\
&= {{n:rA}} \times {{n:eA}} \\
&\quad + {{n:rB}} \times {{n:eB}} \\
&= {{n:eh}}
\end{aligned}
$$

这就是第五步里那个 $\hat\varepsilon$。它的损失是 {{n:lossEh}}；而如果知道原图来自左边亮，$\hat\varepsilon_A$ 的损失只有 {{n:lossEa}}。差出来的那部分，是只看 $x_3$ 无论如何都猜不出来的。

{{fig7}}

用平方误差训练的网络，最终学到的就是这个「加权平均」（平方误差最小的猜法总是平均值）。所以训练损失有一个降不下去的底：

{{fig15}}

<details class="pause"><summary>停一下：t 很小（比如 t = 1）时，网络还容易猜错团吗？</summary>

不容易。$t = 1$ 时 $\bar\alpha_1 = 0.9$，$x_1$ 离原图很近，噪声只占 $\sqrt{0.1} = 0.32$ 倍，一眼就看得出它在哪一团，$r$ 几乎是 100% 和 0%。猜错团只会发生在 $t$ 大、噪声多的时候。反过来说：噪声多时网络只能猜出「大概是哪类图」，噪声少时才猜细节。画图时也是这个顺序，先定大局，再补细节。

</details>

## 第七步：往回走一步

有了猜噪声的网络，怎么从 $x_t$ 走回 $x_{t-1}$？先看一个更简单的问题：**如果同时知道 $x_t$ 和原图 $x_0$**，$x_{t-1}$ 应该在哪？

两条线索各给出一个「钟形」的估计：

- 从 $x_0$ 看：一步到位的公式说 $x_{t-1}$ 在 $\sqrt{\bar\alpha_{t-1}}\,x_0$ 附近，方差 $1 - \bar\alpha_{t-1}$。
- 从 $x_t$ 看：$x_t = \sqrt{\alpha_t}\,x_{t-1} + \sqrt{\beta_t}\,\varepsilon_t$，倒过来，$x_{t-1}$ 在 $x_t / \sqrt{\alpha_t}$ 附近，方差 $\beta_t / \alpha_t$。

两个独立的钟形估计合起来，还是钟形：**精度**（方差的倒数）相加，中心按精度加权平均。为什么？钟形是 $e^{-(\text{二次式})}$，两个钟形相乘，指数相加，两个二次式加起来还是二次式，配方后就得到新的中心和方差：$x^2$ 的系数是两个精度之和，中心是按精度加权的平均。

代入 $t = 3$ 的数字（$\bar\alpha_2 = 0.72$，$\alpha_3 = \beta_3 = 0.5$）：

| 线索 | 中心 | 方差 | 精度 |
| --- | --- | --- | --- |
| 从 $x_0$ | ${{n:cen1}}$ | $0.28$ | {{n:prec1}} |
| 从 $x_3$ | ${{n:cen2}}$ | $1$ | {{n:prec2}} |

（第一行的中心是 $\sqrt{0.72} \times (0.7,\ -0.7)$，方差 $1 - 0.72$；第二行的中心是 $(-0.38,\ -0.02) / \sqrt{0.5}$，方差 $0.5 / 0.5$。精度是方差的倒数。）

合起来，精度 ${{n:prec1}} + {{n:prec2}} = {{n:precsum}}$，方差是它的倒数 ${{n:bt}}$，中心是

$$
\tilde\mu = \frac{ {{n:prec1}} \times \text{中心}_1 + {{n:prec2}} \times \text{中心}_2 }{ {{n:precsum}} }
$$

分子的第一项是 ${{n:prec1}} \times {{n:cen1}} = {{n:num1}}$，第二项是 $1 \times {{n:cen2}}$，相加：

$$
\begin{aligned}
&{{n:num1}} \\
&\quad + {{n:cen2}} \\
&= {{n:numsum}}
\end{aligned}
$$

除以 {{n:precsum}}：

$$
\begin{aligned}
\tilde\mu &= \frac{ {{n:numsum}} }{ {{n:precsum}} } \\
&= {{n:mupost}}
\end{aligned}
$$

一般地，这个合起来的方差记作 $\tilde\beta_t$，中心记作 $\tilde\mu_t$：

$$
\tilde\beta_t = \frac{1 - \bar\alpha_{t-1}}{1 - \bar\alpha_t}\,\beta_t
$$

$$
\begin{aligned}
\tilde\mu_t &= \frac{\sqrt{\bar\alpha_{t-1}}\,\beta_t}{1 - \bar\alpha_t}\,x_0 \\
&\quad + \frac{\sqrt{\alpha_t}\,(1 - \bar\alpha_{t-1})}{1 - \bar\alpha_t}\,x_t
\end{aligned}
$$

（精度之和 $\frac{1}{1 - \bar\alpha_{t-1}} + \frac{\alpha_t}{\beta_t}$ 通分，分子是 $\beta_t + \alpha_t - \alpha_t\bar\alpha_{t-1} = 1 - \bar\alpha_t$，取倒数就是 $\tilde\beta_t$；中心的两个系数是各自的精度乘以 $\tilde\beta_t$ 再乘各自的中心。）验算：$x_0$ 的系数 $\frac{0.8485 \times 0.5}{0.64} = {{n:cx0}}$，$x_3$ 的系数 $\frac{0.7071 \times 0.28}{0.64} = {{n:cxt}}$，${{n:cx0}} \times (0.7,\ -0.7) + {{n:cxt}} \times (-0.38,\ -0.02) = {{n:mupost}}$，和上面一样。

**可我们不知道 $x_0$。** 但第五步说过：猜出噪声，就能写出 $x_0$。把 $x_0 = (x_t - \sqrt{1 - \bar\alpha_t}\,\varepsilon) / \sqrt{\bar\alpha_t}$ 代进 $\tilde\mu_t$，合并同类项：

- $x_t$ 的系数：$\frac{\sqrt{\alpha_t}(1 - \bar\alpha_{t-1})}{1 - \bar\alpha_t} + \frac{\sqrt{\bar\alpha_{t-1}}\,\beta_t}{1 - \bar\alpha_t} \cdot \frac{1}{\sqrt{\bar\alpha_t}}$。因为 $\sqrt{\bar\alpha_{t-1}} / \sqrt{\bar\alpha_t} = 1 / \sqrt{\alpha_t}$，第二项是 $\frac{\beta_t}{\sqrt{\alpha_t}(1 - \bar\alpha_t)}$；两项通分，分子 $\alpha_t(1 - \bar\alpha_{t-1}) + \beta_t = 1 - \bar\alpha_t$，所以系数是 $\frac{1}{\sqrt{\alpha_t}}$。
- $\varepsilon$ 的系数：$-\frac{\sqrt{\bar\alpha_{t-1}}\,\beta_t}{1 - \bar\alpha_t} \cdot \frac{\sqrt{1 - \bar\alpha_t}}{\sqrt{\bar\alpha_t}} = -\frac{\beta_t}{\sqrt{\alpha_t}\,\sqrt{1 - \bar\alpha_t}}$。

合起来：

$$
\tilde\mu_t = \frac{1}{\sqrt{\alpha_t}}\Bigl( x_t - \frac{\beta_t}{\sqrt{1 - \bar\alpha_t}}\,\varepsilon \Bigr)
$$

用真实噪声验算：$\frac{\beta_3}{\sqrt{1 - \bar\alpha_3}} = \frac{0.5}{0.8} = {{n:keps}}$，括号里是 $(-0.38,\ -0.02) - {{n:keps}} \times (-1,\ 0.5) = {{n:inner_true}}$，再乘 $1 / \sqrt{0.5} = {{n:ia3}}$，得 ${{n:mutrue}}$，和上面算的 $\tilde\mu$ 一样。

现在把真实的 $\varepsilon$ 换成网络猜的 $\hat\varepsilon$，就是 DDPM 往回走一步的公式：

$$
\begin{aligned}
x_{t-1} &= \frac{1}{\sqrt{\alpha_t}}\Bigl( x_t - \frac{\beta_t}{\sqrt{1 - \bar\alpha_t}}\,\varepsilon_\theta \Bigr) \\
&\quad + \sigma_t\, z
\end{aligned}
$$

$\varepsilon_\theta$ 是 $\varepsilon_\theta(x_t, t)$ 的简写，$z$ 是一个新抽的标准正态噪声，$\sigma_t^2$ 取 $\tilde\beta_t$（DDPM 论文说取 $\beta_t$ 效果也差不多）。代入 $\hat\varepsilon = {{n:eh}}$：括号里是 $(-0.38,\ -0.02) - {{n:keps}} \times {{n:eh}} = {{n:inner_th}}$，乘 ${{n:ia3}}$ 得均值 ${{n:muth}}$。再加 $\sigma_3 z$，$\sigma_3 = \sqrt{ {{n:bt}} } = {{n:sbt}}$，抽到 $z = (0.4,\ -0.2)$：

$$
\begin{aligned}
x_2 &= {{n:muth}} \\
&\quad + {{n:sbt}} \times (0.4,\ -0.2) \\
&= {{n:x2}}
\end{aligned}
$$

{{fig8}}

为什么还要加新噪声 $\sigma_t z$？因为「知道 $x_t$ 时 $x_{t-1}$ 在哪」本来就不是一个确定的点，而是一个有宽度的钟形（方差 $\tilde\beta_t$）。只取中心不加噪声，每一步都取「平均」，最后画出来的是很多张图的平均，发糊。

**损失为什么是猜噪声。** 训练想让网络算出的均值 $\mu_\theta$ 接近真正的 $\tilde\mu$。两者只差在 $\varepsilon$ 换成了 $\varepsilon_\theta$：

$$
\tilde\mu - \mu_\theta = \frac{\beta_t}{\sqrt{\alpha_t}\,\sqrt{1 - \bar\alpha_t}}\,\bigl(\varepsilon_\theta - \varepsilon\bigr)
$$

我们的数：系数 $\frac{0.5}{0.7071 \times 0.8} = {{n:kloss}}$，$\tilde\mu - \mu_\theta = {{n:mudiff}}$，正好是 ${{n:kloss}}$ 乘以 $\hat\varepsilon - \varepsilon$。所以「均值走对」和「噪声猜对」只差一个常数倍。DDPM 从概率模型的下界出发，推出的损失就是 $\lVert \varepsilon - \varepsilon_\theta \rVert^2$ 乘一个随 $t$ 变的系数；把这个系数去掉，就是第五步的 $L_\text{simple}$，论文发现去掉后生成的图更好。

## 第八步：从纯噪声画出一张图

把第七步重复 $T$ 次，就是画图（DDPM 论文的采样算法）：

1. 抽 $x_T$：每个像素一个标准正态随机数；
2. 对 $t = T, T-1, \dots, 1$：用网络算 $\varepsilon_\theta(x_t, t)$，按第七步的公式得到 $x_{t-1}$（最后一步 $t = 1$ 不加新噪声）；
3. 输出 $x_0$。

{{fig9}}

看图 9：300 个点从一团噪声出发。前半程（$t$ 从 1000 到 500）点只是慢慢往两边分，这时网络只能判断「大概是哪一类」；后半程两团才逐渐收紧，这时在补细节。每个点最后落在哪一团，取决于它出发时的噪声和一路上抽到的 $z$：**同一个模型，换一个随机种子，就画出另一张图**。

代价是：画一张图要调用网络 1000 次。DDPM 论文里，在 256 × 256 的数据集上，一批 128 张图要 300 s。

## 第九步：步数与速度：DDIM

能不能少走几步？最直接的办法是跳着走：只在 $t = 1000, 750, 500, 250$ 这几个时刻调用网络，每次从一个时刻跳到下一个。第七步的公式只要把 $\alpha_t$ 换成两个时刻之间的比值 $\bar\alpha_t / \bar\alpha_{t'}$（$\beta_t$ 相应换成 1 减这个比值，$\bar\alpha_{t-1}$ 换成 $\bar\alpha_{t'}$）就能用。

**DDIM**（Song、Meng、Ermon，2020）给了一种更好的跳法，而且不加新噪声。它分两步：先用猜的噪声估出原图，再把这个原图按目标时刻的比例重新和**同一个**猜的噪声混合：

$$
\hat x_0 = \frac{x_t - \sqrt{1 - \bar\alpha_t}\,\hat\varepsilon}{\sqrt{\bar\alpha_t}}
$$

$$
x_{t'} = \sqrt{\bar\alpha_{t'}}\;\hat x_0 + \sqrt{1 - \bar\alpha_{t'}}\;\hat\varepsilon
$$

从我们的 $x_3$ 直接跳到 $t' = 1$。先算分子 $x_3 - 0.8\,\hat\varepsilon$：

$$
\begin{aligned}
&{{n:x3}} \\
&\quad - 0.8 \times {{n:eh}} \\
&= {{n:x0h_inner}}
\end{aligned}
$$

除以 0.6：

$$
\begin{aligned}
\hat x_0 &= \frac{ {{n:x0h_inner}} }{0.6} \\
&= {{n:x0h}}
\end{aligned}
$$

再按 $t' = 1$ 的比例重新混合，得到 $x_1$（$\sqrt{\bar\alpha_1} = \sqrt{0.9}$，$\sqrt{1 - \bar\alpha_1} = \sqrt{0.1}$）：

$$
\begin{aligned}
&{{n:ddim_a}} \times {{n:x0h}} \\
&+ {{n:ddim_b}} \times {{n:eh}} \\
&= {{n:x1ddim}}
\end{aligned}
$$

注意 $\hat x_0 = {{n:x0h}}$ 在两团中间，偏右边亮：在 $t = 3$ 这么吵的时候，网络猜的原图是「两团的加权平均」，一张两边都发灰的图。这也说明了为什么**步数不能太少**：一步从纯噪声跳到 $t = 0$，得到的就是这张平均图，所有点挤在中间。步数多一些，每一步只跳一小段，下一步再根据新的位置重新猜，点才会逐渐分到两团里去。

{{fig10}}

在我们的玩具数据上，DDIM 走 5 步时 {{n:q5ddim}} 的点落在某一团里，10 步 {{n:q10ddim}}，50 步 {{n:q50ddim}}；DDPM 走 5 步只有 {{n:q5ddpm}}，10 步 {{n:q10ddpm}}，走满 1000 步是 {{n:q1000ddpm}}（真实数据本身按同一标准是 {{n:qtrue}}）。DDIM 论文报告，同样的质量下它比 DDPM 快 10 到 50 倍。Stable Diffusion v1 的示例脚本默认走 50 步。

## 第十步：潜空间扩散：先压小，再扩散

一张 512 × 512 的彩色图有 $512 \times 512 \times 3 = {{n:pix}}$ 个数。在这么大的图上每一步都跑一次网络、跑几十步，非常贵；而且这些数里很大一部分是人眼不在意的细碎纹理。

**潜空间扩散**（Rombach 等，2022，Stable Diffusion 就是它）的做法是：先单独训练一个**自编码器**（VAE）。它的编码器把图压小，解码器再把小图还原成原图；训练目标是「还原得像」。训好之后冻住不动，扩散只在压小后的「潜空间」里做：

- 训练：真图 → 编码器 → 小图 $z_0$，然后在 $z_0$ 上做前面讲的一切（加噪、猜噪声）；
- 生成：从噪声出发，在小图上走完反向的几十步，得到 $z_0$，最后用解码器还原成像素。

Stable Diffusion v1 的自编码器每个方向缩小 8 倍，把 $H \times W \times 3$ 的图变成 $\frac{H}{8} \times \frac{W}{8} \times 4$ 的潜空间（4 个通道）。512 × 512 的图变成 64 × 64 × 4：

$$
64 \times 64 \times 4 = {{n:lat}}
$$

$$
\frac{ {{n:pix}} }{ {{n:lat}} } = {{n:ratio}}
$$

{{fig11}}

少了 48 倍。换个角度看：潜空间里的每个位置对应原图一块 8 × 8 像素，这块有 $8 \times 8 \times 3 = 192$ 个数，被压成 4 个数，$192 / 4 = 48$。这和上一讲把图切成小块、每块换成一个向量是同一个想法，只是这里的「每块的向量」是为了还原原图而训练的，不是为了配文字。

上一讲的视觉 token，是把图切块后**读进**模型；这里反过来，模型在这张 64 × 64 的「块的网格」上**画**，最后由解码器翻译回像素。Stable Diffusion v1 的去噪网络是一个 8.6 亿参数的 U-Net，先在 256 × 256 的图上训练，再在 512 × 512 上微调，数据是 LAION-5B 的一个子集。

## 第十一步：文字怎么进来：交叉注意力

到这里，模型画的是「训练数据里随便一张图」。要按文字画，网络得同时看到文字：$\varepsilon_\theta(x_t,\ t,\ c)$，$c$ 是文字。

Stable Diffusion v1 用上一讲的 CLIP 的**文字编码器**（ViT-L/14 那一版，冻住不训）把提示词变成一串向量：最多 77 个 token，每个 token 768 个数。然后在 U-Net 中间插入**交叉注意力**层。它和注意力那讲的算法一模一样，只有一个区别：$q$ 来自图，$k$ 和 $v$ 来自文字。

- 潜空间里的每个位置（64 × 64 那一层有 4096 个位置）各出一个查询 $q$；
- 每个文字 token 各出一个键 $k$ 和一个值 $v$；
- 每个位置拿自己的 $q$ 和所有文字 token 的 $k$ 打分，softmax 成份额，按份额把 $v$ 加到自己身上。

分数是一张 4096 × 77 的表：每个位置一行，每个文字 token 一列。

用一个位置、三个 token 手算一遍。提示词是「一只 橘 猫」，这个位置的 $q = (1.0,\ 0.5)$，三个 token 的 $k$ 是 $(0.2,\ 0.1)$、$(0.9,\ 0.3)$、$(0.4,\ 1.0)$：

| token | $q \cdot k$ | $\div \sqrt{2}$ | $e^{(\cdot)}$ | 份额 |
| --- | --- | --- | --- | --- |
| 一只 | $1.0 \times 0.2 + 0.5 \times 0.1 = {{n:caS0}}$ | {{n:caSS0}} | {{n:caE0}} | {{n:caW0}} |
| 橘 | $1.0 \times 0.9 + 0.5 \times 0.3 = {{n:caS1}}$ | {{n:caSS1}} | {{n:caE1}} | {{n:caW1}} |
| 猫 | $1.0 \times 0.4 + 0.5 \times 1.0 = {{n:caS2}}$ | {{n:caSS2}} | {{n:caE2}} | {{n:caW2}} |

（总和 ${{n:caE0}} + {{n:caE1}} + {{n:caE2}} = {{n:caSum}}$，份额 = 各自除以总和。）三个 token 的 $v$ 是 $(0.1,\ 0)$、$(1.0,\ 0.2)$、$(0.1,\ 0.9)$，按份额加起来，这个位置得到 ${{n:caOut}}$，加到它原来的向量上。

{{fig12}}

和文字模型不同，这里没有因果遮罩：每个位置都能看所有文字 token。不同位置的 $q$ 不同，所以画猫头的位置多看「猫」，画毛色的位置多看「橘」。每一步去噪都会重新做一遍，文字就这样一步步把画面往它说的方向推。

## 第十二步：classifier-free guidance：让图更听话

只把文字喂进去，模型画出来的东西常常和提示词「沾边但不够像」。**classifier-free guidance**（Ho 和 Salimans，2022）用一个简单的办法加强文字的作用。

**训练时**：按一定概率把文字换成空的（Stable Diffusion v1-4 是 10%）。这样同一个网络学会两件事：有文字时的猜测 $\varepsilon_\theta(x_t, t, c)$，和没有文字时的猜测 $\varepsilon_\theta(x_t, t, \varnothing)$。

**画图时**：每一步把两种猜测都算一遍，然后沿着「有文字减去没文字」的方向多走一点：

$$
\begin{aligned}
\tilde\varepsilon &= \varepsilon_\theta(x_t, t, \varnothing) \\
&\quad + s\,\bigl(\varepsilon_\theta(x_t, t, c) - \varepsilon_\theta(x_t, t, \varnothing)\bigr)
\end{aligned}
$$

$s$ 叫 **guidance scale**。$s = 0$ 等于不看文字；$s = 1$ 就是普通的有文字的猜测；$s > 1$ 是在「有文字」的基础上再往同一个方向多推。Ho 和 Salimans 的论文把它写成 $(1 + w)\,\varepsilon_c - w\,\varepsilon_\varnothing$，两种写法的关系是 $s = 1 + w$。Stable Diffusion v1 的默认值是 $s = 7.5$。代价是每一步要跑两次网络。

**一步步看 $s$ 的作用。** 回到 $x_3 = {{n:x3}}$，条件是「左边亮」。没有文字时，网络的最好猜测就是第六步算的 $\hat\varepsilon = {{n:eh}}$（两团加权）；有文字「左边亮」时，它知道原图来自左边亮那团，最好的猜测是 $\hat\varepsilon_A = {{n:eA}}$。两者之差是 $\hat\varepsilon_A - \hat\varepsilon$。对每个 $s$ 算出 $\tilde\varepsilon$，再用第九步的式子看它对应的原图猜测 $\hat x_0 = (x_3 - 0.8\,\tilde\varepsilon) / 0.6$：

| $s$ | $\tilde\varepsilon$ | $\hat x_0$ |
| --- | --- | --- |
| 0 | ${{n:ge0}}$ | ${{n:gx0}}$ |
| 1 | ${{n:ge1}}$ | ${{n:gx1}}$ |
| 3 | ${{n:ge3}}$ | ${{n:gx3}}$ |
| 7.5 | ${{n:ge7_5}}$ | ${{n:gx7_5}}$ |

{{fig13}}

$s = 1$ 时，网络猜的原图 ${{n:gx1}}$ 就在左边亮那团的中心附近。$s = 3$ 时，它沿同一个方向冲到了 ${{n:gx3}}$：像素超过了 1，比训练里任何一张图都更「左边亮」。真实画图时每一步都会这样往外推一下，后面的步再把一部分拉回来，但 $s$ 越大，拉回来的越少。

下面换一份两团互相重叠的数据（左边亮那团的中心 $(0.35,\ -0.35)$，右边亮那团 $(-0.35,\ 0.35)$，标准差都是 0.4），条件是左边亮，看不同 $s$ 下画出来的 300 个点：

{{fig14}}

| $s$ | 落在左边亮一侧 | 散布（标准差） | 有像素超出 $[-1,\ 1]$ |
| --- | --- | --- | --- |
| 0 | {{n:cl0}} | {{n:csd0}} | {{n:cc0}} |
| 1 | {{n:cl1}} | {{n:csd1}} | {{n:cc1}} |
| 3 | {{n:cl3}} | {{n:csd3}} | {{n:cc3}} |
| 7.5 | {{n:cl7_5}} | {{n:csd7_5}} | {{n:cc7_5}} |

（真实的「左边亮」数据：{{n:cltrue}} 落在左边亮一侧，散布 {{n:csdtrue}}。）$s = 1$ 时画得和真实数据差不多，也继承了它的「不够典型」：一成的点落在了另一侧。$s$ 增大，三件事一起发生：**更听话**（全部落在左边亮一侧）、**更单调**（散布变小，画出来的图彼此更像）、**更过头**（越来越多的像素超出范围，在真实图上就是颜色过饱和、对比过强）。Ho 和 Salimans 的论文里也是这样：$w$ 增大，Inception Score（衡量「像不像某一类」）一路上升，FID（衡量和真实图的整体差距，越低越好）先降后升，在 ImageNet 64 × 64 上 $w = 0.1$ 时最低。7.5 这类较大的值，是用多样性换「更贴提示词」。

<details class="pause"><summary>停一下：s 取负数会怎样？</summary>

$s < 0$ 是从「没文字」往「有文字」的反方向走，图会故意避开文字描述的内容。常见的「负面提示词」用的就是同一个公式：把 $\varepsilon_\theta(x_t, t, \varnothing)$ 换成负面提示词的猜测，于是每一步都在远离它。

</details>

## 第十三步：现在的扩散模型

前面讲的是 2020 到 2022 年的经典做法。之后最大的两个变化（2026-10-22 核实）：

- **扩散 Transformer（DiT）**：Peebles 和 Xie（2022）把 U-Net 换成 Transformer：把潜空间切成 2 × 2 的小块，每块当一个 token，和上一讲的图像块一模一样。256 × 256 的图压成 32 × 32 × 4 的潜空间，切出 $(32/2)^2 = 256$ 个 token。它在 ImageNet 256 × 256 上 FID 2.27，当时最好。
- **流匹配（flow matching）**：Lipman 等（2022）。不再一步步「加一点噪、缩一点图」，而是让原图和噪声之间连一条直线：$x_t = (1 - t)\,x_0 + t\,\varepsilon$，$t$ 从 0 到 1；网络学的不是噪声，而是沿这条线的速度 $v = \varepsilon - x_0$。我们的例子：$t = 0.5$ 时 $x = {{n:fmx}}$，要学的速度是 $(-1,\ 0.5) - (0.7,\ -0.7) = {{n:fmv}}$。给定 $x_t$ 和 $t$，速度、噪声、原图三者能互相换算，所以本质上还是「猜噪声」的近亲，只是路径更直、少几步也走得准。Stable Diffusion 3（Esser 等，2024）用的就是这种直线路径（rectified flow）加 Transformer，文字和图像各用一套权重。Black Forest Labs 的 FLUX.2 [dev] 在模型卡上写的是「320 亿参数的 rectified flow transformer」。

不管哪一种，骨架都是这一讲的：从噪声出发，一个网络反复猜「该往哪走」，文字通过注意力进来，guidance 决定听话的程度，计算放在压小后的潜空间里做。

## 实验里讲了什么

1. **01 前向加噪**：拖动 $t$，看一批图怎样褪成噪声；切换线性 / 余弦调度，看 $\sqrt{\bar\alpha_t}$ 和 $\sqrt{1 - \bar\alpha_t}$ 两条曲线。
2. **02 训练目标：猜噪声**：点平面选一张图、换噪声、拖 $t$，看真实噪声、解析最优的猜测和损失；再在页内真的训练一个小网络，看损失停在最优损失的上方。
3. **03 反向去噪**：从纯噪声出发，一步步往回走，看点怎样分到两团（或一个圆环）上；可切换 DDPM / DDIM、解析最优 / 页内训练的网络。
4. **04 步数与质量**：拖步数，看画出来的点和「落在团里的比例」，以及网络调用次数。
5. **05 guidance scale**：在两团或重叠的两团上选条件、拖 $s$，看听话程度、散布和超出范围的比例。
6. **06 潜空间计算器**：输入图片尺寸、缩小倍数、通道数和切块大小，算潜空间有多少个数、压缩多少倍、DiT 要多少个 token。

## 和前后两讲的关系

这一讲用到的零件都在前面：训练就是梯度下降和反向传播，损失是平方误差；交叉注意力就是注意力那讲的 $q$、$k$、$v$；文字编码器是上一讲的 CLIP；潜空间的「每块一个向量」和 DiT 的「每块一个 token」，就是上一讲切块的想法。上一讲是把图**读进**模型，这一讲是让模型把图**画出来**。

这一讲是模型篇的最后一讲。下一讲进入 Agent 篇：模型本身不再变，我们站到模型外面，看怎么用 prompt、工具和循环让它把事做成。

## 延伸阅读

- Ho, Jain, Abbeel，*Denoising Diffusion Probabilistic Models*，2020（DDPM：$T = 1000$，$\beta$ 从 $10^{-4}$ 到 0.02，$L_\text{simple}$，采样算法）。
- Song, Meng, Ermon，*Denoising Diffusion Implicit Models*，2020（DDIM，快 10 到 50 倍）。
- Nichol, Dhariwal，*Improved Denoising Diffusion Probabilistic Models*，2021（余弦调度）。
- Rombach 等，*High-Resolution Image Synthesis with Latent Diffusion Models*，2022；CompVis，Stable Diffusion v1 的代码仓库、配置文件与模型卡（8 倍下采样、4 通道潜空间、CLIP ViT-L/14 文字编码器、交叉注意力、10% 丢弃文字、默认 scale 7.5 与 50 步）。
- Ho, Salimans，*Classifier-Free Diffusion Guidance*，2022（arXiv 2207.12598）。
- Peebles, Xie，*Scalable Diffusion Models with Transformers*，2022（DiT）。
- Lipman 等，*Flow Matching for Generative Modeling*，2022；Esser 等，*Scaling Rectified Flow Transformers for High-Resolution Image Synthesis*，2024（Stable Diffusion 3）。
- Black Forest Labs，FLUX.2 [dev] 模型卡（Hugging Face）。
