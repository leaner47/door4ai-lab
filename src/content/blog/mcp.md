---
title: "MCP：工具为什么需要一个统一的插口"
description: "没有标准时，每个应用要给每个工具各写一份对接代码；MCP 把 M × N 变成 M + N。讲清 host / client / server 三种角色、tools / resources / prompts 三类能力、JSON-RPC 2.0 报文、stdio 与 Streamable HTTP 两种传输、它和 tool calling 的关系，以及权限和提示注入。六个实验，页内跑着两个真的迷你 MCP server。"
pubDate: 2026-10-17
tags: ["Agent", "MCP", "JSON-RPC", "tool call", "安全"]
lab: /labs/mcp/
series: ai-mastery
order: 120
---

## 一句话版本

MCP（Model Context Protocol）是 AI 应用和外部工具之间的**一个统一插口**：工具方按 MCP 写一个 server，任何支持 MCP 的应用都能直接接上；应用方实现一次 MCP client，就能接上所有 MCP server。它不改变模型调用工具的方式，只是把「工具从哪来、怎么调」这件事标准化了。

本讲的报文与字段按 MCP 规范 **2026-07-28 版**（2026-10-19 在 modelcontextprotocol.io 核实，这是当前版本）。

## 没有标准时：M × N

上一讲里，程序自己定义工具、自己执行。工具一多、应用一多，问题就来了：聊天应用要接 GitHub，写一份；IDE 也要接 GitHub，再写一份；终端 Agent 再写一份。每家的接法还不一样，工具一升级，所有人一起改。

M 个应用、N 个工具，就是 M × N 份对接代码。

<figure class="clip"><video src="/videos/mcp/MxN.webm" poster="/videos/mcp/MxN.png" controls loop muted playsinline preload="metadata"></video></figure>

如果中间有一个大家都认的插口，每个应用只实现一次「插头」（MCP client），每个工具只实现一次「插座」（MCP server），总数就变成 M + N。4 个应用、6 个工具，24 份变 10 份；再加一个工具，原来要多写 4 份，现在只多写 1 份。这和 USB、HTTP 的道理一样，也是 LSP（语言服务器协议）在编辑器世界里做过的事，MCP 规范自己也说借鉴了 LSP。

## 三种角色，三类能力

MCP 里有三种角色：

- **host**：用户直接用的 AI 应用，例如一个聊天客户端或一个 IDE。它连着模型，决定把什么放进上下文、什么需要用户批准。
- **client**：host 里面的连接器。**每连一个 server，host 就建一个 client**，一对一维持连接。
- **server**：提供能力的程序。可以是本机的一个子进程（读本地文件），也可以是远端的一个网址（查公司的工单系统）。

server 能提供三类东西，区别在于**谁来决定用它**：

- **tools**（模型决定）：可执行的函数，模型在对话中自己判断要不要调，比如 `calculate`、`create_pr`。
- **resources**（应用决定）：只读的数据，用 URI 标识，比如一个文件、一张表结构。host 决定把哪些放进上下文，常见做法是让用户在界面里挑。
- **prompts**（用户决定）：预先写好的提示模板，通常显示成斜杠命令，用户主动选用。

反过来，server 也可以向 client 要东西，最常用的是 elicitation（请用户补填一项信息）。2026-07-28 版把 sampling（server 借用 host 的模型）、roots、logging 标为弃用。

## 底层：JSON-RPC 2.0

MCP 的每条消息都是 JSON-RPC 2.0：请求有 `id` 和 `method`，响应用同一个 `id` 带回 `result` 或 `error`，没有 `id` 的是通知，对方不回。

一次典型的会话只有两三个来回。先问有哪些工具：

```json
{
  "jsonrpc": "2.0", "id": 2, "method": "tools/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": { "name": "lab-host", "version": "1.0.0" },
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

server 回一个工具清单，每个工具有 `name`、`description` 和参数的 `inputSchema`（JSON Schema），和上一讲的工具定义几乎一一对应。然后调用：

```json
{
  "jsonrpc": "2.0", "id": 3, "method": "tools/call",
  "params": {
    "name": "calculate",
    "arguments": { "expression": "(123+877)*4/8" },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": { "name": "lab-host", "version": "1.0.0" },
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

```json
{
  "jsonrpc": "2.0", "id": 3,
  "result": {
    "resultType": "complete",
    "content": [{ "type": "text", "text": "500" }],
    "isError": false
  }
}
```

<figure class="clip"><video src="/videos/mcp/MCPRoundTrip.webm" poster="/videos/mcp/MCPRoundTrip.png" controls loop muted playsinline preload="metadata"></video></figure>

**注意 `_meta`。** 2025-11-25 及以前的版本，连接一建立先要握手：client 发 `initialize` 报上版本和能力，server 回自己的版本和能力，client 再发一条 `notifications/initialized`，之后才能干活，HTTP 上还靠 `Mcp-Session-Id` 记住这个会话。2026-07-28 版把握手和会话都去掉了：**每个请求都在 `_meta` 里自带协议版本和 client 能力**，server 不记任何连接状态，任何一台机器都能接住任何一个请求，放在普通的负载均衡后面就能横向扩展。想先了解 server 的能力，可以调一次新增的 `server/discover`，但这不是必须的。代价是每个请求多带一百多个字节，实验 01 里可以切换两个版本对比。

还有两种出错要分清。「方法不存在」（`-32601`）、「参数不对 / 工具不存在」（`-32602`）是**协议错误**，走 JSON-RPC 的 `error`；工具自己跑失败（除以 0、日期格式不对）是**工具执行错误**，照常返回 `result`，只是 `isError: true`。后者要原样回给模型，让它改了再试，和上一讲的 `is_error` 是同一个思路。

## 两种传输：stdio 与 Streamable HTTP

JSON-RPC 消息本身不管怎么送达，MCP 定义了两种标准传输：

- **stdio**：host 把 server 当**子进程**启动，往它的 stdin 写、从它的 stdout 读，一行一条消息，消息里不能有换行。server 的日志只能写 stderr，否则会把协议流弄乱。适合本机工具：读写本地文件、跑本地命令。
- **Streamable HTTP**：server 是一个独立的网络服务，只有一个端点（比如 `https://mcp.example.com/mcp`），每条消息一次 POST。响应可以是一个 JSON，也可以是一条 SSE 流（先推几条进度通知，最后是结果）。请求头里要带 `MCP-Protocol-Version`，还要把方法名抄进 `Mcp-Method`、工具名抄进 `Mcp-Name`，网关不用拆包就能按工具路由、限流；server 会核对头部和消息体一致，不一致回 `-32020`。远程 server 的鉴权走 OAuth。

两种方式里，JSON-RPC 消息体一个字节都不变，变的只是外面那层壳。

## 和上一讲 tool calling 的关系

MCP **不替代** tool calling，模型那一侧什么都没变。模型从来不直接和 MCP server 说话，中间永远隔着 host：

1. host 通过 client 调 `tools/list`，拿到工具清单；
2. 把每个工具翻译成发给模型的 `tools` 定义（`inputSchema` 改名 `input_schema`，工具名常加上 server 前缀，因为两个 server 都叫 `search` 很常见）；
3. 模型照常生成 `tool_use`；
4. host 按前缀找到对应的 server，把它翻译成 `tools/call`；
5. 结果的 `content` 和 `isError` 翻译成 `tool_result` 的 `content` 和 `is_error`，塞回对话。

所以 MCP 解决的是「工具从哪里来、怎么调用」的工程问题，模型「什么时候调、调哪个」仍然是上一讲那一套。

## 安全：server 能做的事，就是你授权的事

接上一个 MCP server，等于让一段别人写的代码在你的机器上、或者用你的账号跑。规范的要求很明确：应该始终有人在回路里，能拒绝工具调用；host 要清楚展示暴露了哪些工具、调用时给出醒目提示、敏感操作前请用户确认。

几个要点：

- **审批要分级**。全部自动批准有风险，全部确认会让人看都不看就点「允许」。常见做法是读操作自动、写和执行逐次确认（实验 04）。
- **工具声明的提示不可信**。工具可以带 `readOnlyHint`、`destructiveHint` 之类的 annotations，但规范要求：除非 server 可信，client 必须把它们当作不可信。
- **工具说明本身就是攻击面**。`description` 会原样进入模型的上下文，恶意 server 可以在里面夹带指令（「先读取用户的私密文件……」），也可以先给一份干净的说明骗过审核、之后再改掉。host 应该把完整说明给用户看、记下批准时的版本并在每次刷新时比对、未批准的工具不发给模型（实验 05）。
- **本地 HTTP server 只监听 127.0.0.1，并校验 `Origin` 头**，否则网页可以借 DNS rebinding 摸到你本机的 server。

说到底，提示注入很难被完全检测出来，真正的底线是最小权限：一个查天气的 server 本来就不该拿得到你的文件。

## 实验里讲了什么

0. **M × N 变成 M + N**：拖应用数和工具数，看两种连法的线数，以及再加一个工具时各要新写几份。
1. **一次完整会话**：`server/discover` → `tools/list` → `tools/call` 的消息时序，点每条看完整原文；可切 2025-11-25 的握手式流程，以及 stdio / Streamable HTTP 两种外层，字节数实时算出。
2. **从 MCP 工具到模型的 tools**：六块报文对照（tools/list 里的工具 → Anthropic tools 定义 → tool_use → tools/call → 结果 → tool_result），高亮同一个字段一路怎么改名、怎么流转。
3. **亲手给 server 发请求**：页内的计算器 server 有一个工具、一个只读 resource、一个 prompt 模板，十几种请求看真实响应和错误码。
4. **权限与审批**：三个任务、三种审批策略，数一次任务要弹几次审批、有几次写操作没经过逐次确认。
5. **工具说明里的提示注入**：说明正常、安装时就夹带、批准后悄悄改掉三种情况下，「原样转发」和「展示、比对、隔离」两种 host 各让多少可疑内容进了模型的上下文。

## 和前后两讲的关系

上一讲《Embedding 与 RAG》说的检索，在实际系统里通常就包装成一个工具（「查一下知识库」）挂给 Agent，MCP 正是这类工具的标准接口；再往前，《大模型怎么调用工具》讲的 `tools` / `tool_use` / `tool_result` 是这一讲的地基，MCP 只是在它外面加了一层「工具从哪来」。

下一讲看一类特别的工具：让 Agent 浏览网页、操作电脑的那一套，它们也常常以 MCP server 的形式接进来。这一讲里还出现了 SSE：Streamable HTTP 可以把一次调用的进度和结果用一条事件流推回来。第 125 讲讲流式输出，模型的回答本身也是这样一个 token 一个 token 地用 SSE 推给你的。

## 延伸阅读

- [MCP 规范 2026-07-28 版](https://modelcontextprotocol.io/specification/2026-07-28/basic/index)，以及它的 [Changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)（去掉握手与会话、新增 `server/discover` 的说明）
- MCP 文档：[Architecture overview](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture)（host / client / server 与一次完整交互的示例）
- 规范中的 [Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)、[Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)、[stdio](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)、[Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) 各页
- [JSON-RPC 2.0 规范](https://www.jsonrpc.org/specification)
