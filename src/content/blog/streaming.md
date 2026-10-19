---
title: "流式输出：为什么回答是一个字一个字蹦出来的"
description: "模型本来就是一个 token 一个 token 生成的，流式只是把每一小段立刻推给你。讲首 token 时间（TTFT）和生成速度两个数字、SSE 报文长什么样、Anthropic 与 OpenAI 的流式事件、工具参数怎么分片到达，以及前端接流时的四个坑。六个实验：两条时间线对比、逐字节的 SSE 流、随机切块下三种解析器、分片的工具参数、按真实速度打字、中途取消。"
pubDate: 2026-10-17
tags: ["Agent", "流式输出", "SSE", "TTFT", "推理延迟"]
lab: /labs/streaming/
series: ai-mastery
order: 125
---

## 一句话版本

模型生成回答的方式本来就是一个 token 接一个 token：先把整段 prompt 读一遍（prefill），然后每一步只生成一个新 token（decode）。**不开流式**，服务器要等最后一个 token 生成完，才把整段回答一次性交给你；**开了流式**，每生成一小段就立刻推过来。模型算得一样快，你看到第一个字的时间却从「整段生成完」提前到了「第一个 token 生成完」。

推的方式是 SSE（Server-Sent Events）：一个迟迟不结束的 HTTP 响应，服务器往里一段段写文本，每段是一个事件。

## 回答本来就是一个一个 token 生成的

Token 那一讲讲过自回归：模型每次前向计算只产出下一个 token 的概率分布，抽出一个 token，接到输入末尾，再算下一个。第一遍要把整段 prompt 一次算完，这叫 prefill；之后每遍只算新来的那一个，前面的 K、V 存在 KV Cache 里复用，这叫 decode。

所以「一个字一个字蹦出来」不是前端故意做的打字机特效，而是模型真实的生成节奏。流式输出只是**不再把这些 token 攒起来**。

<figure class="clip"><video src="/videos/streaming/TTFTvsTotal.webm" poster="/videos/streaming/TTFTvsTotal.png" controls loop muted playsinline preload="metadata"></video></figure>

两条时间线上服务器做的事完全一样，终点也完全对齐。区别只在中间那一大段：非流式的用户盯着转圈图标，什么也看不到；流式的用户从第一个 token 开始就在读。

## 两个数字：首 token 时间和生成速度

衡量一次流式生成快不快，看两个数：

- **首 token 时间（TTFT，time to first token）**：从发出请求到收到第一个 token。它主要由排队和 prefill 决定，prompt 越长，prefill 越久。
- **生成速度（token/s）**：之后每秒能吐出多少 token，也就是 decode 的速度。它的倒数就是相邻两个 token 之间的间隔。

<p class="formula">TTFT ≈ 排队 + prompt token 数 ÷ prefill 速度</p>
<p class="formula">总时长 ≈ TTFT + (输出 token 数 − 1) ÷ decode 速度</p>

这两个速度的来源不一样。prefill 一次处理整段 prompt，能把 GPU 的算力用满，瓶颈是算力：每个 token 大约要做 2 × 参数量次浮点运算。decode 每次只算一个 token，却要把全部权重从显存里读一遍，瓶颈是显存带宽（KV Cache 那一讲说过同样的事）。拿公开规格估一下：Llama-3-8B 约 8.03B 参数，bf16 权重 16.06 GB；RTX 4090 显存带宽 1008 GB/s，所以 decode 上限约 1008 ÷ 16.06 ≈ 63 token/s；它的 FP16 Tensor Core 稠密峰值 165.2 TFLOPS，按 50% 利用率，prefill 约 5,100 token/s。prefill 比 decode 快近百倍，所以几千 token 的 prompt 只要零点几秒，几百 token 的回答却要好几秒。

**体感延迟主要看 TTFT。** 实验 00 的默认设置（排队 200 ms、2,000 token 的 prompt、500 token 的回答）下，流式 600 ms 就出第一个字，非流式要等 8.92 s，差了 15 倍。只要生成速度比人的阅读速度快，读者从第一个字开始一路读下去就不会被卡住：实验 04 里 30 token/s 折合约 43 字/s，而中文默读的常见估计是每分钟 300–500 字，也就是每秒 5–8 字。

这也解释了 Agent 为什么常常「感觉慢」：在吐出第一个给用户看的字之前，它可能已经调了几轮工具、读了几份文件，这些都算进 TTFT。很多产品会先把「正在搜索」「正在读取文件」这类中间状态推出来，道理一样：别让人对着空白干等。

## SSE：一个不关闭的 HTTP 响应

普通的 HTTP 响应是「服务器把整个正文写完，连接结束」。SSE 只改了一点：服务器回 `Content-Type: text/event-stream`，然后**不急着结束**，想发什么就往里写一段文本。格式非常简单：

- 每个事件由若干行 `字段: 值` 组成，常用的字段是 `event`（事件名）和 `data`（内容），另外还有 `id` 和 `retry`；
- 以冒号开头的行是注释，常用来保活；
- **一个空行**表示这个事件结束。

<figure class="clip"><video src="/videos/streaming/SSEFrames.webm" poster="/videos/streaming/SSEFrames.png" controls loop muted playsinline preload="metadata"></video></figure>

浏览器原生有一个 `EventSource` 对象专门接 SSE，会自动断线重连。但它只能发 GET 请求、不能自定义请求头，而调用大模型 API 要用 POST 发一大段 JSON、还要带密钥。所以实际接模型流式响应时，一般用 `fetch` 拿到响应体的 `ReadableStream`，自己一块块读、自己解析（或者交给官方 SDK）。

和 WebSocket 比：WebSocket 是双向的，连接建好以后两边随时都能发；SSE 是单向的，只有服务器往客户端推，客户端要说话就另发一个请求。模型回答这件事天然是「我问一次，它说很久」，单向正好够用，而且 SSE 就是普通 HTTP，过代理、过 CDN、做鉴权都和普通接口一样，所以各家模型 API 都选了它。

## API 的流式事件长什么样

以下报文形态于 2026-10-19 对照各家官方文档核实。

**Anthropic Messages API**（请求里加 `"stream": true`）。事件顺序是固定的：一个 `message_start`；然后每个内容块各有一个 `content_block_start`、若干 `content_block_delta`、一个 `content_block_stop`；然后一个或多个 `message_delta`；最后 `message_stop`。中间可能随时夹着 `ping`。下面是官方文档里的示例（节选）：

```text
event: message_start
data: {"type": "message_start", "message": {"id": "msg_1nZdL29xx5MUA1yADyHTEsnR8uuvGzszyY", "type": "message", "role": "assistant", "content": [], "model": "claude-opus-5-5", "stop_reason": null, "stop_sequence": null, "usage": {"input_tokens": 25, "output_tokens": 1}}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}

event: ping
data: {"type": "ping"}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "!"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence":null}, "usage": {"output_tokens": 15}}

event: message_stop
data: {"type": "message_stop"}
```

几个要点：文字在 `text_delta` 里；`message_delta` 带着 `stop_reason` 和 `usage`，文档特别说明这里的 token 数是**累计值**，取最新的就行，不要加起来；流里也可能出现 `event: error`（比如高峰期的 `overloaded_error`，相当于非流式下的 HTTP 529）；文档还要求代码能**容忍没见过的事件类型**，因为以后可能会加。

**OpenAI Chat Completions**（同样是 `"stream": true`）。它没有 `event:` 行，每个事件只有一行 `data:`，内容是一个 `chat.completion.chunk` 对象，文字在 `choices[0].delta.content` 里，最后用一行 `data: [DONE]` 收尾。下面按 API 参考里的示例和字段定义整理（model 名换成了常见的 `gpt-4o`）：

```text
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o","choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}]}

data: [DONE]
```

想拿到 token 用量，要在请求里设 `stream_options: {"include_usage": true}`，这时 `[DONE]` 之前会多一个 `choices` 为空数组、带 `usage` 的 chunk；文档提醒，流如果中途断了，这个用量 chunk 可能收不到。另外 OpenAI 默认会在增量事件里加一个 `obfuscation` 字段（随机字符，用来抹平报文长度、防侧信道），上面的示例省略了它。

两家的共同结构：开头一条元信息，中间一串增量，结尾一条「为什么停、用了多少」。实验 01 里可以左右切换，看同一句话在两种格式下的原始文本。

## 工具调用在流里怎么出现

工具调用那一讲里，模型的回复里会出现一个 `tool_use` 块。在流里，这个块的参数**不是一次给全的**：`content_block_start` 先告诉你工具名和 id，`input` 是空对象；接着一串 `input_json_delta` 事件，每个带一截 JSON 字符串 `partial_json`；最后 `content_block_stop`。官方文档的示例：

```text
event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_01T1x1fJ34qAmk2tNTrN7Up6","name":"get_weather","input":{}}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"location\":"}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":" \"San"}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":" Francisc"}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"o,"}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":" CA\"}"}}

event: content_block_stop
data: {"type":"content_block_stop","index":1}
```

拼到一半的字符串不是合法 JSON，`JSON.parse` 会报错。正确做法：按 `index` 把同一个块的片段拼起来，等这个块的 `content_block_stop` 到了再解析一次。文档还提到，当前模型一次吐出一个完整的键和值，所以事件之间可能有停顿。OpenAI 的对应物是 `delta.tool_calls` 数组：第一个片段带 `id` 和 `function.name`，之后的片段用同一个 `index`，只带一截 `function.arguments` 字符串，处理方法一样。实验 03 把这个过程一片片放给你看。

## 前端接流的四个坑

**半个 UTF-8 字符。** 网络不按事件切块，你读到的字节块可能在任何位置断开。一个汉字在 UTF-8 里占 3 个字节，块边界切在中间时，如果每块单独解码，两半都会变成乱码 �。解法是整个流共用一个 `TextDecoder`，每次调用时传 `{stream: true}`，它会把不完整的尾巴留到下一块。（顺带一提：token 本身也可能只有半个字。o200k_base 把「空格 + 蹦」切成三个 token，每个只有这个字的一部分字节；服务器会等字凑齐再放进 `text_delta`，因为 JSON 字符串里放不了半个字。）

**半条 JSON。** 同样的原因，一个块里可能只有半行 `data:`。必须先把文本攒在缓冲区里，按空行切出完整事件，再解析其中的 JSON。实验 02 在页面里真的把一段流按随机字节边界切开：平均每块 24 字节时，「每块直接解析」的做法 `JSON.parse` 失败 48 次、一个字都没拼出来；「按空行缓冲但每块单独解码」的做法出了 4 个乱码；两样都做对的解析器，任何切法下都和原文一字不差。块越大，前两种「大部分时候没事」，这正是这类 bug 难发现的原因。

**Markdown 渲染跳动。** 模型输出的往往是 Markdown，而流到一半的 Markdown 是残缺的：`**加粗` 还没等到闭合的 `**`，代码块只有开头的三个反引号，表格只来了一半。每来一个增量就把整段重新渲染，页面会闪烁、跳动，代码块会突然吞掉后面所有文字。常见做法是只重新渲染最后一个未完成的段落、对未闭合的语法先做临时补全，或者降低渲染频率（比如每一帧最多渲染一次）。

**用户中途取消。** 点「停止」时，前端用 `AbortController` 中止 `fetch`，连接随之关闭。服务器要过一会儿才发现客户端走了，这期间它还在生成。取消能省下的是「还没生成」的部分；已经生成的输出 token，送没送到都已经算过了，prompt 的输入 token 更是在 prefill 时就全部算完。实验 05 用一个真实的 `ReadableStream` 演示这件事，计费部分是示意，具体以各家规则为准。

## 实验里讲了什么

0. **流式与非流式**：拖 prompt 长度、prefill 速度、输出长度、decode 速度，两条时间线按公式真实计算，看第一个字和最后一个字各在什么时候到；一键套用 RTX 4090 跑 Llama-3-8B 的估算值。
1. **SSE 报文**：页面里用定时器真的一个事件一个事件地推送，左边是原始文本，右边是解析器切出的事件和拼出的回答，可切换 Anthropic / OpenAI 两种格式；切 token 用的是真实的 o200k_base 分词器。
2. **网络不按事件切块**：同一段流按随机字节边界切开，三种解析器在页面里真实执行，看 JSON 解析失败和乱码各从哪来。
3. **流里的工具调用**：`input_json_delta` 一片片到达，每一步都真的 `JSON.parse` 一次，直到 `content_block_stop`。
4. **体感**：调 TTFT、生成速度和阅读速度，一段 315 字（220 个 token）的话真的按这个速度打出来，旁边是读者读到哪里。
5. **中途取消**：生成到一半点停止，看屏幕上显示了多少、服务器实际生成了多少、省下了多少。

## 和前后两讲的关系

这一讲接着两条线。一条是模型篇的 Token 讲：那里讲了 prefill 和 decode，这里看它们怎么变成用户感受到的延迟。另一条是上一讲 MCP：MCP 的 Streamable HTTP 传输里，服务器同样可以用 `text/event-stream` 往回推消息，今天讲的 SSE 格式和解析方法在那里原样适用。

下一讲《Trace 与 Eval》讲怎么看清一个 Agent 到底干了什么、干得好不好。流里的每一个事件都带着时间戳和内容：什么时候开始、首 token 用了多久、调了哪个工具、参数是什么、为什么停、用了多少 token。把这些事件记下来，就是可观测性最直接的数据来源。

## 延伸阅读

- Anthropic, [Streaming Messages](https://platform.claude.com/docs/build-with-claude/streaming)（事件流顺序、`text_delta` / `input_json_delta`、累计 usage、错误事件，本文报文示例的出处）
- OpenAI, [Create chat completion](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) 与 [Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses)（`chat.completion.chunk`、`stream_options`、`data: [DONE]`）
- WHATWG, [HTML Standard: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)（`text/event-stream` 格式与 `EventSource` 的规范定义）
- MDN, [Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) 与 [TextDecoder.decode()](https://developer.mozilla.org/en-US/docs/Web/API/TextDecoder/decode)（`stream` 选项）
