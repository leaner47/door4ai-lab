---
title: "Agent Loop：为什么一个 while 循环就是 Agent"
description: "把 Agent 拆成模型 + 工具 + 一个 while 循环：模型想调工具就执行、把结果追加回消息数组、再调一次模型，直到它不再调工具。看上下文怎么每圈变长、总发送量怎么二次方增长，循环在哪里停、工具失败怎么兜，以及 Anthropic 对 workflow 与 agent 的区分。六个可交互实验。"
pubDate: 2026-10-17
tags: ["Agent", "Agent Loop", "ReAct", "工具调用", "Harness"]
lab: /labs/agent-loop/
series: ai-mastery
order: 105
---

## 一句话版本

Agent 没有什么神秘的新部件。它是上一讲的工具调用，外面套了一个循环：

```python
messages = [用户的问题]
while True:
    out = model(messages)          # 把整个数组发给模型
    messages.append(out)
    if not out.tool_use:           # 模型不再想调工具 → 这就是最终回答
        break
    r = run_tool(out.tool_use)     # 由程序执行工具
    messages.append(r)             # 把结果追加回去，再转一圈
```

模型每转一圈只做一件事：读完目前为止的全部消息，决定是再调一次工具，还是直接回答。决定「再调一次」的是模型，真正执行工具、把结果塞回数组、决定什么时候强行停下的，是模型外面的这段程序。

## 循环的一圈里发生了什么

<figure class="clip"><video src="/videos/agent-loop/WhileLoop.webm" poster="/videos/agent-loop/WhileLoop.png" controls loop muted playsinline preload="metadata"></video></figure>

拿「北京和上海现在哪个更热」举例，工具只有一个 `get_temperature(city)`。第一圈，模型读到问题，输出一段思考和一条 `tool_use`：查北京。程序看到 `tool_use`，去查，得到 22 °C，以 `tool_result` 的形式追加到数组末尾。第二圈，模型重新读整个数组（问题、它自己上一圈的输出、工具结果），决定再查上海。第三圈，两个温度都在数组里了，模型直接写出答案，输出里没有 `tool_use`，循环退出。

三个细节值得盯住：

- **模型从不执行任何东西。** 它只是输出「我想调这个工具、参数是这些」。执行、权限、超时、日志全在循环这一侧。
- **每一圈都把整个数组重新发一遍。** 模型是无状态的，它不记得上一圈，所以上一圈的全部内容都得再发一次。
- **退出条件是「模型没有再输出 tool_use」。** 在消息 API 里就是 `stop_reason` 从 `tool_use` 变成 `end_turn`。模型不想停，循环就不会自己停。

## ReAct：先想，再做，再看结果

<figure class="clip"><video src="/videos/agent-loop/ReActTrace.webm" poster="/videos/agent-loop/ReActTrace.png" controls loop muted playsinline preload="metadata"></video></figure>

这个循环的学术出处是 ReAct（Reason + Act，Yao et al., 2022）。它的做法是让模型在每一步都交替写两种东西：先写一段 **Thought**（推理：现在知道什么、还缺什么、下一步该做什么），再写一条 **Action**（行动：调哪个工具、什么参数）；程序执行后把 **Observation**（观察：工具返回了什么）接在后面，模型再写下一组 Thought / Action。论文里的对照实验说明，只推理不行动会编造事实，只行动不推理会在步骤间迷路，两者交替才在问答和决策任务上都明显更好。

和上面的循环对照：Thought 和 Action 是同一次模型输出里的两部分；Observation 就是 `tool_result`；一组 Thought → Action → Observation 就是循环的一圈；最后一个 Action 是 `Finish[答案]`，相当于「没有 tool_use」。今天各家 API 里的「思考」或「推理」字段，和 ReAct 里的 Thought 是同一个位置。

## 上下文越转越长，总发送量是二次方的

因为每圈都重发整个数组，第 <i>i</i> 圈发送的长度是 <i>c</i><sub>0</sub> + (<i>i</i> − 1)(<i>k</i> + <i>m</i>)：<i>c</i><sub>0</sub> 是系统提示和问题，<i>k</i> 是每条工具结果的长度，<i>m</i> 是每圈模型输出的长度。<i>n</i> 圈的总发送量：

<p class="formula">Σ = <i>n c</i><sub>0</sub> + (<i>k</i> + <i>m</i>) · <i>n</i>(<i>n</i> − 1)/2</p>

后一项是 <i>n</i> 的二次方：圈数翻一倍，总 token 大约翻四倍。实验 01 里按 <i>c</i><sub>0</sub> = 800、<i>k</i> = 400、<i>m</i> = 80 算，10 圈总共发 29600 个 token，20 圈发 107200 个，40 圈发 406400 个。一次搜索工具返回几千 token 很常见，这个数字还要再乘十。

prompt cache 能把这件事从二次方压回接近线性：前一圈已经发过的前缀在服务端缓存了，这一圈只有新追加的 <i>k</i> + <i>m</i> 个 token 按原价，命中的部分按折扣价。实验 01 里可以拖折扣比例看省多少。但注意，cache 省的是钱和首字延迟，不省上下文窗口：数组本身还是那么长，模型的注意力还是要铺在整个数组上。这是第 110 讲的问题。

## 终止条件、预算、失败

模型不想停循环就不会停，所以程序这一侧必须自己兜底，常见的有三道：

1. **最大步数**：转了 <i>N</i> 圈还没结束，强制退出。
2. **token 或金钱预算**：累计发送量超过上限就停。因为上下文是二次方增长的，这条线往往比你以为的来得早（实验 02）。
3. **人工确认**：在关键动作（删文件、付钱、发消息）前暂停，等人点头。

工具会失败：超时、报错、返回空。实验 03 比较了三种策略。**直接放弃**最省事，但 <i>N</i> 次调用里任何一次失败整个任务就失败，成功率是 (1 − <i>p</i>)<sup><i>N</i></sup>。**把错误回给模型重试**：错误信息照样作为 `tool_result` 追加进数组，模型自己看到「超时」，再试一次或者换个参数；允许重试 <i>R</i> 次后成功率变成 (1 − <i>p</i><sup><i>R</i>+1</sup>)<sup><i>N</i></sup>，代价是多转几圈、多发几次上下文。**换工具**：失败后改用备用工具。实践里几乎总是把错误回填给模型，让它自己决定重试还是换路，这也是循环这个结构的好处：失败只是又一条消息。

## Harness：围绕模型的那一圈程序

上面这些东西（循环本身、工具的执行、权限检查、步数和预算、日志、出错处理）合起来有个名字：**harness**。模型只负责「下一步做什么」，harness 负责把它的决定变成真实世界里的动作，并且在它失控时拦住。同一个模型，换一套 harness，能力和安全性会差很多：工具描述写得好不好、错误信息回填得清不清楚、什么动作要确认，都在这一层。

Anthropic 在《Building effective agents》（Erik Schluntz 与 Barry Zhang，2024 年 12 月）里把这类系统分成两种：**workflow** 是「LLM 和工具通过预先定义的代码路径编排」的系统，步骤是写死的；**agent** 是「LLM 动态地决定自己的流程和工具使用」的系统，由模型自己决定下一步。文章列了五种 workflow 模式（prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer），然后才讲自主 agent，并给了三条原则：保持设计简单；让规划步骤对用户透明；认真打磨工具的文档和接口。它的建议很直接：先找最简单的方案，能用一次调用解决就别用 workflow，能用 workflow 的就别用 agent，只有当步骤数和路径真的无法预先确定时，才让模型来决定。实验 04 用规则模拟比较了两者的步数分布：workflow 步数是常数，agent 平均可能更省但有一条长尾。

最后一个词：**orchestrator**。一个主 agent 把任务拆开，派给几个子 agent 各自去转各自的循环，再把结果汇总。它本质上还是这一讲的循环，只是「工具」变成了另一个 agent。这里点到为止，多 Agent 编排留到第 135 讲。

## 实验里讲了什么

0. **最小的 Agent Loop**：规则模拟的模型完成「比较两个城市温度」，逐步播放思考 → tool_use → 执行 → tool_result → 最终回答，右侧消息数组每圈长两条。
1. **上下文累积**：拖工具结果长度和步数，看每步上下文长度与累计发送 token 的二次方增长，对比有无 prompt cache。
2. **终止条件**：设最大步数和 token 预算，看循环在第几圈停、为什么停；勾上「模型卡住」看两个兜底谁先拦住它。
3. **失败处理**：工具按概率失败，20000 次蒙特卡洛比较直接放弃、回填重试、换工具三种策略的成功率与平均调用次数，与解析解对照。
4. **Workflow vs Agent**：同一任务固定流水线与模型自主决定两种方式的步数分布。
5. **ReAct 轨迹阅读器**：一条真实格式的 Thought / Action / Observation 轨迹，点每一行看它对应循环的哪个环节、消息数组里的什么角色。

## 和前后两讲的关系

上一讲讲了工具调用：模型怎么输出一条结构化的 `tool_use`，程序怎么执行并把结果回填。这一讲把「回填之后再调一次模型」变成循环，就得到了 Agent。下一讲把循环、工具执行、权限这些模型外面的程序当作一个整体来看，它叫 harness。循环里上下文每圈都在变长、每圈都要整个重发，则是第 110 讲「上下文与记忆」要解决的问题：窗口装不下了怎么办、哪些要留、哪些要压缩或存到外面。

## 延伸阅读

- Shunyu Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* (2022, arXiv:2210.03629)，ReAct 原论文
- Erik Schluntz, Barry Zhang, *Building effective agents*, Anthropic (2024-12-19)，workflow 与 agent 的区分、五种 workflow 模式、三条原则
