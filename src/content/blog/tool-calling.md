---
title: "大模型怎么调用工具：一次 tool call 的完整来回"
description: "模型本身只会生成文本，所谓「调用工具」是程序替它跑的：把工具的名字、说明和参数 JSON Schema 放进请求，模型生成一段「我要调 X，参数是 …」，程序解析、校验、真的执行，再把结果作为新消息塞回对话。六个实验：走完一次来回的报文、工具定义占多少 token、参数校验与让模型重试、并行调用、结果太长的处理、工具选择的决策。"
pubDate: 2026-10-17
tags: ["Agent", "tool call", "function calling", "JSON Schema", "上下文"]
lab: /labs/tool-calling/
series: ai-mastery
order: 100
---

## 一句话版本

模型不会执行任何东西。它只会生成 token。所谓「大模型调用了一个工具」，完整的意思是：**你在请求里告诉它有哪些工具、怎么用；它在回复里生成一段结构化的「我要调 X，参数是 …」；你的程序把这段解析出来、真的去执行、再把结果作为一条新消息塞回对话；模型读到结果，继续往下说话。**

从头到尾，模型做的只有两件事：生成那段调用请求，和读完结果后生成最终回答。中间真正跑代码的是你写的程序。

<figure class="clip"><video src="/videos/tool-calling/ToolCallLoop.webm" poster="/videos/tool-calling/ToolCallLoop.png" controls loop muted playsinline preload="metadata"></video></figure>

## 为什么需要这一套

前面几讲讲的都是模型内部：token 怎么进去、注意力怎么算、参数怎么训出来。一个训好的模型是一个**冻结的函数**：给它一串 token，它给你下一个 token 的概率分布。它不知道今天几号，不知道你数据库里有多少行，也没法把一封邮件发出去。

这些事都在模型外面。所以工程上的做法不是「让模型变得能上网」，而是：**让模型学会说出一句程序能听懂的话，程序去办，再把结果讲给它听。**

这件事有个意外的好处：模型从「必须什么都记得住」变成了「知道去哪儿查就行」。算 2847 × 193 不用它心算，查今天的汇率不用它背下来。

## 一次来回，具体传了什么

拿 Anthropic 的 Messages API 举例。第一次请求，你除了消息，还要带一个 `tools` 字段：

```json
{
  "model": "claude-sonnet-5-5",
  "max_tokens": 1024,
  "tools": [{
    "name": "get_weather",
    "description": "查询某个城市当前的天气。city 用中文城市名。",
    "input_schema": {
      "type": "object",
      "properties": {
        "city": { "type": "string", "description": "城市名，例如 北京" },
        "unit": { "type": "string", "enum": ["celsius", "fahrenheit"] }
      },
      "required": ["city"]
    }
  }],
  "messages": [{ "role": "user", "content": "上海现在天气怎么样？" }]
}
```

三样东西：**名字**、**给模型看的自然语言说明**、**参数的 JSON Schema**。说明是写给模型读的，schema 既是写给模型的（该给哪些字段）也是写给你自己的（拿来校验）。

模型的回复里出现一个 `tool_use` 内容块，并且 `stop_reason` 是 `tool_use`：

```json
{
  "role": "assistant",
  "content": [{
    "type": "tool_use",
    "id": "toolu_01A09q90qw90lq917835lq9",
    "name": "get_weather",
    "input": { "city": "上海", "unit": "celsius" }
  }],
  "stop_reason": "tool_use"
}
```

**这就是模型做的全部事情**：它生成了这段 JSON。没有任何网络请求、没有任何代码被执行。接下来轮到你的程序：读出 `name` 和 `input`，校验，调真正的函数，拿到结果，拼成一条新的 user 消息发回去。结果放在 `tool_result` 块里，用 `tool_use_id` 对上刚才那次调用：

```json
{
  "role": "user",
  "content": [{
    "type": "tool_result",
    "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
    "content": "{\"city\":\"上海\",\"temperature\":24,\"condition\":\"多云\"}"
  }]
}
```

注意这条消息的角色是 `user`。在模型眼里，工具结果和用户说的话一样，都是「别人告诉我的信息」。第二次请求把这三条消息（user → assistant 的 tool_use → user 的 tool_result）连同原封不动的 `tools` 一起发出去，模型这次读到了天气，于是生成普通文本，`stop_reason` 回到 `end_turn`。

### OpenAI 那边长什么样

字段名不同，流程一模一样。Chat Completions 里工具定义是嵌套的，模型的调用放在 assistant 消息的 `tool_calls` 数组里，结果用一条 `role: "tool"` 的消息送回去：

```json
{ "id": "call_12345xyz", "type": "function",
  "function": { "name": "get_weather", "arguments": "{\"city\":\"上海\"}" } }
```

```json
{ "role": "tool", "tool_call_id": "call_12345xyz", "content": "{\"temperature\":24}" }
```

两处值得记住的差别：OpenAI 的 `arguments` 是一个 **JSON 字符串**（要先 `JSON.parse` 一次），Anthropic 的 `input` 已经是对象；OpenAI 可以在工具定义上开 `strict: true`（配合 `"additionalProperties": false`）强制参数符合 schema。实验 00 里可以左右切换这两种报文形态对照着看。

## 模型是怎么学会生成这种结构的

一个自然的疑问：模型不是在预测下一个 token 吗，怎么会突然吐出一段格式工整的 JSON？

答案是：它还是在预测下一个 token。只不过训练语料里有大量这样的对话——用户提问、助手输出一段工具调用、然后是工具结果、然后是最终回答。见得多了，「在工具定义之后、遇到一个需要外部信息的问题时，接下来最可能出现的 token 序列」就是那段调用结构。它和学会在句号后面换行、在代码块里写 Python 是同一件事。

这解释了两个常被误解的现象：

- **参数可能是错的**。它在生成，不是在填表。类型写错、漏掉必填字段、把枚举值写成中文、甚至编出一个你根本没注册的工具名，都会发生。所以程序必须先拿 schema 校验再执行（实验 02）。
- **它不知道自己调没调成功**。工具报错了，只有你把错误写进 `tool_result` 它才知道。官方文档的建议是：失败时回一个 `is_error: true` 的结果，并且把错误信息写得可操作，模型通常会改两三次再放弃。千万别在程序里直接抛异常中断循环——那样模型什么反馈都收不到。

## 工具定义是上下文里的 token

工具定义不是免费的。它在**每一轮请求里**都要完整发一遍，和系统提示、历史消息挤同一个上下文窗口。

<figure class="clip"><video src="/videos/tool-calling/SchemaToText.webm" poster="/videos/tool-calling/SchemaToText.png" controls loop muted playsinline preload="metadata"></video></figure>

实验 01 里用真实分词器数过：一个 `get_weather`，说明写一段话，连 schema 一共 82 token；三个常用工具 218 token；八个工具、每个都带上例子和注意事项，就是 1134 token。另外 Anthropic 的文档写明，只要请求里带了 `tools`，API 还会自动追加一段系统提示，当前模型在 `tool_choice` 为 `auto` 或 `none` 时是 286 token，`any` 或 `tool` 时是 406 token。

在 200k 的窗口里这点开销不算什么，但是：

- 工具挂到几十个，光定义就是几千 token，而且**每一轮都重付**；
- 窗口小的模型（8k）上，八个带详细说明的工具已经占掉约 17%；
- 工具结果同样占上下文，而且会一直留在历史里（实验 04）。

这就是后面几讲里「工具要分组、要按需加载、结果要压缩」这些做法的由来。

## 并行，以及为什么它省的不只是工具时间

模型可以在**一次回复里生成多个** `tool_use` 块。只要这几个调用互不依赖，程序就可以同时发出去，总时间从「加起来」变成「取最大」。

省下的不只是工具本身的延迟。串行方案里，每多调一个工具就多一轮模型生成——模型要把整个对话重读一遍再生成下一段调用。实验 03 的默认设置下，三个工具串行 3760 ms、并行 2080 ms，省掉的 1680 ms 里有 1200 ms 是省掉的两轮模型生成，只有 480 ms 来自工具本身。

要关掉并行，Anthropic 在 `tool_choice` 里设 `disable_parallel_tool_use`，OpenAI 用 `parallel_tool_calls`。什么时候该关？当工具有副作用、你想一次只批准一个动作的时候。

## 实验里讲了什么

0. **一次 tool call 的来回**：左边消息列表、右边真实报文，点「下一步」走完五步；计算器和单位换算在页内真算，天气来自一张标明了的示例表；可切换 Anthropic / OpenAI 两种形态。
1. **工具定义占多少 token**：勾选工具、改说明长度，用真实分词器数出 token，看它在 8k / 32k / 200k 窗口里占多大。
2. **参数校验**：页内实现了一个最小 JSON Schema 校验器，七种模型输出（类型错、缺必填、多余字段、枚举外取值、工具名幻觉、非法 JSON）逐一看报错，并给出把错误回给模型让它重试的报文。
3. **并行工具调用**：三个独立查询的串行与并行时间线，工具延迟和模型生成耗时都可以拖，看各自占多少。
4. **结果太长**：同一批记录，原样返回 / 截断前 N 条 / 摘要三种策略的 token 对比，以及往后多聊几轮会累计多花多少。
5. **选哪个工具**：一棵写死的规则树演示「调工具还是直接回答」的决策，并说明真模型里没有这棵树——它是学出来的，所以边界模糊得多。

## 和前后两讲的关系

到上一讲为止，整个模型篇讲的都是模型**内部**：token、注意力、梯度下降、反向传播、LayerNorm、LoRA、评测。从这一讲开始是 Agent 篇，讲的是模型**外面的那个程序**：它准备请求、解析回复、执行工具、管理对话。

这一讲只走了一个来回。下一讲《Agent Loop》把它变成一个循环：模型调工具 → 看结果 → 再调 → 再看，直到它认为问题解决为止。循环一旦跑起来，立刻会冒出新问题——什么时候该停、上下文涨满了怎么办、中间步骤要不要给用户看——那些是接下来几讲的内容。

## 延伸阅读

- Anthropic, [Tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) 与 [Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)（`tool_use` / `tool_result` / `is_error` 的权威字段定义与 token 开销）
- OpenAI, [Function calling](https://developers.openai.com/api/docs/guides/function-calling)（`tool_calls`、`strict` 模式、Responses 与 Chat Completions 两种形态）
- Timo Schick et al., *Toolformer: Language Models Can Teach Themselves to Use Tools* (2023)，模型怎么通过自监督学会在文本里插入 API 调用
- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* (2022)，下一讲的底子
