---
title: "Agent 框架全景：LangChain、LangGraph、Agent SDK 替你做了什么"
description: "前面几讲把工具调用、循环、上下文、RAG、MCP、流式、Trace、编排各手写了一遍。这一讲拿 LangChain、LangGraph、LlamaIndex、Claude Agent SDK、OpenAI Agents SDK 逐项对照：每个框架用什么抽象把哪几讲的东西包了起来，怎么选，代价在哪，什么时候才值得上框架。作为 Agent 篇的收尾，最后把 100–135 讲串成一条线。"
pubDate: 2026-10-17
tags: ["Agent", "框架", "LangChain", "LangGraph", "Agent SDK", "复盘"]
series: ai-mastery
order: 140
---

## 一句话版本

Agent 框架没有发明新东西。它们做的，是把你在前面几讲里手写过的那些部件：工具定义和执行、while 循环、消息数组的截断和摘要、检索、MCP 客户端、SSE 解析、span 记录、重试和路由，**事先写好、起好名字、接好线**。你剩下要写的，是工具函数本身和几行配置。

所以读框架文档最快的办法，是带着前面几讲的问题去找：「它的循环在哪？什么时候停？消息数组存在哪？压缩谁来做？工具报错了怎么回填？」每个问题都能在框架里找到一个对应的类或参数。

本讲所有框架的名称、版本和 API 于 **2026-10-19** 核实：先查各家官方文档，再从 PyPI 下载当天最新的安装包，在源码里确认类名和参数确实存在。

## 手写的 Agent 和框架封装的层

<figure class="cf-flow">
<svg viewBox="0 0 360 436" role="img" aria-label="左边是手写 Agent 的八个部件，右边用框架时只剩工具函数要自己写，其余七个部件由框架提供" font-size="13">
<g text-anchor="middle" font-weight="700" fill="var(--fg)">
<text x="90" y="20">手写</text>
<text x="270" y="20">用框架</text>
</g>
<rect x="184" y="70" width="172" height="286" rx="10" fill="var(--accent-soft)" fill-opacity=".55" stroke="var(--accent)" stroke-width="2"/>
<g fill="none" stroke="var(--muted)" stroke-width="1.25">
<rect x="10" y="36" width="160" height="30" rx="7"/>
<rect x="10" y="76" width="160" height="30" rx="7"/>
<rect x="10" y="116" width="160" height="30" rx="7"/>
<rect x="10" y="156" width="160" height="30" rx="7"/>
<rect x="10" y="196" width="160" height="30" rx="7"/>
<rect x="10" y="236" width="160" height="30" rx="7"/>
<rect x="10" y="276" width="160" height="30" rx="7"/>
<rect x="10" y="316" width="160" height="30" rx="7"/>
<rect x="190" y="36" width="160" height="30" rx="7"/>
</g>
<g fill="none" stroke="var(--accent)" stroke-width="1.1" stroke-dasharray="4 3">
<rect x="190" y="76" width="160" height="30" rx="7"/>
<rect x="190" y="116" width="160" height="30" rx="7"/>
<rect x="190" y="156" width="160" height="30" rx="7"/>
<rect x="190" y="196" width="160" height="30" rx="7"/>
<rect x="190" y="236" width="160" height="30" rx="7"/>
<rect x="190" y="276" width="160" height="30" rx="7"/>
<rect x="190" y="316" width="160" height="30" rx="7"/>
</g>
<g stroke="var(--line)" stroke-width="1.25">
<path d="M170 51H190"/><path d="M170 91H190"/><path d="M170 131H190"/><path d="M170 171H190"/>
<path d="M170 211H190"/><path d="M170 251H190"/><path d="M170 291H190"/><path d="M170 331H190"/>
</g>
<g fill="var(--fg)">
<text x="20" y="55.5" font-weight="700">工具函数</text>
<text x="20" y="95.5">Agent Loop</text>
<text x="20" y="135.5">上下文 / 记忆</text>
<text x="20" y="175.5">检索（RAG）</text>
<text x="20" y="215.5">MCP client</text>
<text x="20" y="255.5">流式解析</text>
<text x="20" y="295.5">Trace / 拦截</text>
<text x="20" y="335.5">路由 / 编排</text>
</g>
<g fill="var(--muted)" font-size="12" text-anchor="end">
<text x="160" y="55.5">100</text>
<text x="160" y="95.5">105</text>
<text x="160" y="135.5">110</text>
<text x="160" y="175.5">115</text>
<text x="160" y="215.5">120</text>
<text x="160" y="255.5">125</text>
<text x="160" y="295.5">130</text>
<text x="160" y="335.5">135</text>
</g>
<g text-anchor="middle" font-size="12.5" fill="var(--fg)">
<text x="270" y="55.5" font-weight="700">工具函数（仍要自己写）</text>
<text x="270" y="95.5">run() / query()</text>
<text x="270" y="135.5">会话 · 自动压缩</text>
<text x="270" y="175.5">retriever · index</text>
<text x="270" y="215.5">MCP 适配器</text>
<text x="270" y="255.5">stream() 事件</text>
<text x="270" y="295.5">tracing · hooks</text>
<text x="270" y="335.5">handoff · 图 · 子 Agent</text>
</g>
<text x="270" y="374" text-anchor="middle" font-size="12" fill="var(--accent)">框架替你写好的部分</text>
<rect x="10" y="392" width="340" height="34" rx="8" fill="none" stroke="var(--muted)" stroke-width="1.25"/>
<text x="180" y="413.5" text-anchor="middle" font-weight="700" fill="var(--fg)">模型 API（Messages / Responses）</text>
</svg>
<figcaption>左边每个实线框都是你在对应那一讲里亲手写过的代码；换成框架后，只有工具函数还要自己写，其余七块变成框架里的类和参数（虚线框）。两边最底下调的是同一个模型 API。</figcaption>
</figure>

图里右边那一大块浅色区域，就是你引入框架时「买到」的东西，也是你以后调试时要「穿过」的东西。后面讲的选择和代价，都是围绕这一块展开的。

## 同一个 Agent，三种写法

拿第 105 讲的例子：「北京和上海现在哪个更热」，只有一个工具 `get_temperature(city)`。手写版的核心是那个 while 循环：

```python
messages = [用户的问题]
while True:
    out = model(messages, tools=[get_temperature 的定义])
    messages.append(out)
    if not out.tool_use:
        break
    messages.append(run_tool(out.tool_use))
```

**LangChain**：`create_agent` 把循环、工具执行、消息追加全部包掉，`@tool` 从函数签名和 docstring 生成工具定义。

```python
from langchain.agents import create_agent
from langchain.tools import tool

@tool
def get_temperature(city: str) -> str:
    """查询城市当前气温，city 用中文城市名。"""
    ...

agent = create_agent("openai:gpt-5.5", tools=[get_temperature])
result = agent.invoke({"messages": [{"role": "user", "content": "北京和上海现在哪个更热？"}]})
```

**OpenAI Agents SDK**：`Agent` 是配置，`Runner` 是循环，`@function_tool` 生成 schema（默认开 strict）。

```python
from agents import Agent, Runner, function_tool

@function_tool
def get_temperature(city: str) -> str:
    """查询城市当前气温，city 用中文城市名。"""
    ...

agent = Agent(name="天气助手", instructions="回答天气问题，需要时先查气温。", tools=[get_temperature])
result = Runner.run_sync(agent, "北京和上海现在哪个更热？")
print(result.final_output)
```

**Claude Agent SDK**：自定义工具要放进一个**进程内的 MCP server**，再把 server 交给 Agent。这正是第 120 讲的结构：工具从一个 MCP server 来，host 负责翻译成模型的 `tools`。

```python
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, create_sdk_mcp_server, query, tool

@tool("get_temperature", "查询城市当前气温，city 用中文城市名。", {"city": str})
async def get_temperature(args):
    ...
    return {"content": [{"type": "text", "text": "..."}]}

weather = create_sdk_mcp_server(name="weather", tools=[get_temperature])
options = ClaudeAgentOptions(
    mcp_servers={"weather": weather},
    allowed_tools=["mcp__weather__get_temperature"],
    max_turns=5,
)
async for msg in query(prompt="北京和上海现在哪个更热？", options=options):
    if isinstance(msg, ResultMessage):
        print(msg.result)
```

三段代码里都没有 `while`，也没有 `messages.append`。它们还在，只是搬进了框架里。

## 对照表

行是前面各讲的概念，格子里是这个框架用来实现它的抽象。「—」表示这个框架自身没有对应的东西，或者官方文档里查不到，不代表做不到（自己写进工具或节点里总是可以的）。

### 通用框架：LangChain、LangGraph、LlamaIndex

三者都不绑定某一家模型。LangChain 1.x 的 `create_agent` 返回的就是一张编译好的 LangGraph 图，所以前两列很多格子是同一套机制，只是 LangChain 替你把图画好了，LangGraph 让你自己画。

| 概念 | LangChain 1.4 | LangGraph 1.2 | LlamaIndex 0.14 |
| --- | --- | --- | --- |
| 工具调用（100） | `@tool` 装饰器，函数列表直接传给 `create_agent(tools=…)` | `ToolNode` + `tools_condition`（`langgraph.prebuilt`） | `FunctionTool`、`QueryEngineTool`；普通函数也能直接传 |
| Agent Loop（105） | `create_agent()`，`invoke()` / `stream()` 运行 | `StateGraph`：节点 + 条件边，自己连出「模型 → 工具 → 模型」的环 | `FunctionAgent` / `ReActAgent` / `CodeActAgent`，`await agent.run()`；底层是事件驱动的 Workflow |
| 上下文 / 记忆（110） | `checkpointer` + `thread_id` 存会话，`store` 存长期记忆；`SummarizationMiddleware`、`ContextEditingMiddleware` 压缩 | checkpointer（`InMemorySaver` / `SqliteSaver` / `PostgresSaver`）按 `thread_id` 存每一步的状态；`Store` 跨会话共享 | `Memory.from_defaults(token_limit=…)`：短期消息队列，溢出部分刷进长期 memory block（`FactExtractionMemoryBlock`、`VectorMemoryBlock`） |
| RAG（115） | `langchain-core` 的向量库接口与 `as_retriever()`，`langchain-text-splitters` 切块；旧的检索链移到了 `langchain-classic` | — | 看家本领：`VectorStoreIndex`、retriever、query engine，可包成 `QueryEngineTool` 交给 Agent |
| MCP（120） | `langchain.mcp.MCPAdapter`（1.4 起，beta，基于 FastMCP）；更早用独立包 `langchain-mcp-adapters` | — | `llama-index-tools-mcp`：`BasicMCPClient`、`McpToolSpec`、`get_tools_from_mcp_url`；`workflow_as_mcp` 反过来把 workflow 发布成 server |
| 流式（125） | `agent.stream(stream_mode=…)`，与 LangGraph 同一套模式 | `stream_mode`：`values`、`updates`、`messages`（逐 token）、`custom`、`checkpoints`、`tasks`、`debug` | `handler.stream_events()`，事件有 `AgentStream`、`ToolCallResult` 等 |
| Trace（130） | LangSmith（环境变量 `LANGSMITH_TRACING=true` 打开） | 同左，LangSmith | `instrumentation` 模块：dispatcher + span / event handler，接第三方可观测性平台 |
| 拦截 / 人工确认（130） | middleware：`HumanInTheLoopMiddleware`、`PIIMiddleware`、`ToolCallLimitMiddleware`；自定义钩子 `before_model`、`wrap_model_call`、`wrap_tool_call` 等 | `interrupt()` 暂停，`Command(resume=…)` 带着人的答复恢复，前提是配了 checkpointer | `InputRequiredEvent` / `HumanResponseEvent` + `ctx.wait_for_event` |
| 网关 / 编排（135） | `"openai:gpt-5.5"` 式的模型字符串 + 十几个模型厂商集成包；`ModelFallbackMiddleware`、`ModelRetryMiddleware`；多 Agent 文档给了 subagents、handoffs、router 等模式 | 子图、`Send`（扇出并行）、`Command(goto=…)`；checkpointer 带来的 durable execution（进程挂了能从上一步接着跑） | `AgentWorkflow`：多个 agent 互相 handoff；或自己写 `Workflow` + `@step` |

### 模型厂商的 SDK：Claude Agent SDK、OpenAI Agents SDK

这两个是模型公司自己出的，版本号都还是 0.x，和自家模型、自家平台绑得更紧，换来的是开箱即用的东西更多。

| 概念 | Claude Agent SDK 0.2 | OpenAI Agents SDK 0.24 |
| --- | --- | --- |
| 工具调用（100） | 内置 `Read` `Edit` `Write` `Bash` `Glob` `Grep` `WebSearch` `WebFetch` 等；自定义工具用 `@tool` + `create_sdk_mcp_server()`（进程内 MCP server） | `@function_tool`（从签名和 docstring 生成 schema）；托管工具 `WebSearchTool`、`FileSearchTool`、`CodeInterpreterTool` |
| Agent Loop（105） | `query()`（单次）/ `ClaudeSDKClient`（多轮）；跑的就是 Claude Code 的循环，安装包里自带 Claude Code 二进制；`max_turns`、`max_budget_usd` 兜底 | `Runner.run()` / `run_sync()`；`max_turns` 默认 10，超了抛 `MaxTurnsExceeded` |
| 上下文 / 记忆（110） | 接近窗口上限时自动 compaction（把旧历史摘要掉，流里出现 `compact_boundary`）；会话可 `resume` / `fork_session`；`CLAUDE.md` 每次请求都重新注入 | Sessions：`SQLiteSession`、`RedisSession`、`SQLAlchemySession`、`OpenAIConversationsSession`；`OpenAIResponsesCompactionSession` 负责压缩 |
| RAG（115） | —（没有向量检索抽象，靠 `Grep` / `Glob` / `WebSearch` 现查） | `FileSearchTool`：托管检索，查 OpenAI 平台上的 vector store |
| MCP（120） | `mcp_servers`：stdio、SSE、HTTP、进程内 SDK server 四种；MCP 工具的 schema 默认按需加载（tool search） | `MCPServerStdio`、`MCPServerStreamableHttp`；`HostedMCPTool` 让 Responses API 在服务端直接调远程 server；SSE 仅留给旧 server |
| 流式（125） | `query()` 本身是异步迭代器，逐条给出 `AssistantMessage`、`ResultMessage`；`include_partial_messages=True` 再加逐 token 的 `StreamEvent` | `Runner.run_streamed()` + `result.stream_events()`：`RawResponsesStreamEvent`（逐 token）和 `RunItemStreamEvent`（工具调用等） |
| Trace（130） | `ResultMessage` 带 `total_cost_usd`、`usage`、`num_turns`；hooks 做审计；当前 OpenTelemetry span 的 trace context 会传进 Claude Code 进程 | 默认开启：`trace()` 包住一次运行，自动记 `agent_span`、`generation_span`、`function_span`、`guardrail_span`、`handoff_span`，上传到 OpenAI 的 Traces 面板；可换成自己的 processor |
| 拦截 / 人工确认（130） | `permission_mode`、`allowed_tools` / `disallowed_tools`、`can_use_tool` 回调；`PreToolUse` 等 hooks 能直接拦下一次工具调用 | input / output guardrails 和工具级 guardrails；工具设 `needs_approval` 后运行暂停，`RunState.approve()` / `reject()`，状态可 `to_json()` 存下来以后再续 |
| 网关 / 编排（135） | 只跑 Claude 模型（Anthropic API，或 Bedrock / Vertex / Foundry 渠道）；`fallback_model`；子 Agent 用 `agents={名字: AgentDefinition}` 定义，主 Agent 通过 `Agent` 工具派活 | handoffs（把对话整个交给另一个 Agent）、`Agent.as_tool()`（把 Agent 当工具调）；`MultiProvider`，经 LiteLLM / any-llm 扩展接其他家模型 |

几处值得多看一眼的格子：

- **Claude Agent SDK 的自定义工具是一个 MCP server。** 它没有另起一套工具协议，而是直接复用 MCP（第 120 讲）。工具名因此带前缀：`mcp__weather__get_temperature`。
- **两家厂商 SDK 都把「压缩」做成了默认或一个类。** 第 110 讲手写的截断、滚动窗口、摘要，在这里是 compaction 和 `OpenAIResponsesCompactionSession`。
- **OpenAI 的 trace 默认是开着的，并且会上传。** 第 130 讲的 span 树在它这里不用写一行代码，但这也意味着你的输入输出默认会发到 OpenAI 的平台；文档写明零数据保留（ZDR）的组织用不了这个功能，要关可以设 `OPENAI_AGENTS_DISABLE_TRACING=1`。
- **LangGraph 那几个「—」不是缺陷。** 它定位就是画状态机的底层框架，检索、MCP 这些「部件」交给 LangChain 或你自己，它只管节点怎么连、状态怎么存、在哪暂停。

### 语言与模型绑定

| 框架 | 语言 | 模型绑定 | 2026-10-19 最新版本（PyPI / npm） |
| --- | --- | --- | --- |
| LangChain | Python、TypeScript | 不绑定，按字符串选厂商 | `langchain` 1.4.6 / 1.5.18 |
| LangGraph | Python、TypeScript | 不绑定 | `langgraph` 1.2.16 / `@langchain/langgraph` 1.5.1 |
| LlamaIndex | Python、TypeScript | 不绑定 | `llama-index-core` 0.14.25 / `llamaindex` 0.12.1 |
| Claude Agent SDK | Python、TypeScript | 只用 Claude | `claude-agent-sdk` 0.2.168 / `@anthropic-ai/claude-agent-sdk` 0.3.303 |
| OpenAI Agents SDK | Python、TypeScript | 默认 OpenAI，可经扩展接其他家；托管工具只在 OpenAI 上有 | `openai-agents` 0.24.0 / `@openai/agents` 0.20.0 |

## 怎么选

先问四个问题，大多数情况答完就有结论了。

**1. 原型还是生产？** 原型要的是「十分钟跑起来」，哪个框架的示例离你的任务最近就用哪个，选错了代价也小。生产要的是「出事时查得清、升级时不炸」，这时框架的透明度、版本稳定性、trace 能不能接进你现有的系统，比少写几十行代码重要得多。

**2. 一个简单循环，还是一个需要暂停、恢复、分支的状态机？** 如果 Agent 就是「问一句，转几圈，答一句」，第 105 讲那个循环加上第 110 讲的压缩就够了，任何框架都是锦上添花。真正拉开差距的是这几种需求：

- 要在某一步**停下来等人批准**，而且人可能隔天才回来点；
- 进程重启、机器挂了以后，要**从上一步接着跑**，不能从头再来（已经付过钱的工具调用不能再付一遍）；
- 流程里有**多条分支、并行、回退**，画出来是一张图而不是一条线。

这几种需求的本质都是「把循环的状态存到循环外面」。LangGraph 的 checkpointer + `interrupt()`、OpenAI Agents SDK 的 `RunState.to_json()`、Claude Agent SDK 的会话 `resume`，都是在解决这件事，其中 LangGraph 做得最彻底：每一步都存，任意一步都能恢复或回放。

**3. 团队用什么语言？** 五个框架都同时有 Python 和 TypeScript 版本，这一条现在很少成为决定因素。但两种语言的版本往往不同步（上表里 LangChain 的 Python 是 1.4、JS 是 1.5），某个功能先在哪边出、两边 API 是否一模一样，要分别看文档。

**4. 绑定哪家模型？** 这是最硬的一条。

- 已经确定只用 Claude，而且 Agent 的主要工作是**读写文件、跑命令**（代码助手、运维、数据处理脚本）：Claude Agent SDK 把这套工具和权限模型都带好了，几乎不用自己写工具。
- 主要用 OpenAI，想要托管的检索和 trace：OpenAI Agents SDK 最省事。
- 要能换模型，或者必须用自己部署的开源模型：选 LangChain / LangGraph / LlamaIndex 这类不绑定的。OpenAI Agents SDK 虽然能经 LiteLLM 接别家，但 `FileSearchTool`、`HostedMCPTool` 这些托管工具只在 OpenAI 平台上存在。
- 核心是**大量文档的检索问答**：LlamaIndex 的索引、检索、query engine 这一层最完整。

## 用框架的代价

Anthropic 在《Building effective agents》里专门有一节讲框架，原话的意思是：框架简化了调模型、定义和解析工具、串联调用这些底层工作，容易上手；但它们常常加了额外的抽象层，**遮住了底下真正发出去的 prompt 和收回来的响应**，让调试更难，也诱使人在简单方案就够的时候堆复杂度。建议是先直接用模型 API，很多模式几行代码就能实现；如果用框架，要确保你理解它底下的代码，因为「对底层行为的错误假设」是常见的出错来源。

具体落到三件事上：

**抽象泄漏。** 框架替你做的决定，会改变模型实际看到的东西，而你未必知道：

- 自动压缩会把早期的消息换成摘要。Claude Agent SDK 的文档自己就写着：压缩后，对话早期给出的具体指令可能保不住，长期规则应该写进 `CLAUDE.md`（它每次请求都重新注入），而不是写在第一条 prompt 里。这正是第 110 讲「截断会悄悄删掉第 2 轮的规则」那个问题，只是现在它发生在你看不见的地方。
- 中间件、hooks、托管工具可能往请求里加系统提示、改工具结果、截断输出。你在 trace 里看到的「模型的输入」，可能和你以为自己写的那份差得很远。
- 默认行为里藏着数据去向：前面说的 OpenAI trace 默认上传就是一例。

**调试要穿透几层。** 出问题时你得一层层往下找：LangChain 的 `create_agent` → 某个 middleware → LangGraph 的执行引擎 → `langchain-core` 的聊天模型接口 → 某个厂商集成包 → HTTP 请求。Claude Agent SDK 则是你的 Python 进程 → 一个 Claude Code 子进程 → API，报错可能来自任何一侧。手写版出错时，栈只有一层：就是你那几十行。

**升级时的破坏性变更。** 这一年里真实发生过的：

- LangChain 1.0 把 `langgraph.prebuilt.create_react_agent` 换成了 `langchain.agents.create_agent`（旧函数标为弃用），旧的 chains、检索器、hub 等搬进了单独的 `langchain-classic` 包，import 路径都要改；1.4 又把 MCP 支持从独立包 `langchain-mcp-adapters` 收进了 `langchain.mcp`，而且标着 beta。
- Claude Agent SDK 是由 Claude Code SDK 改名而来，官方专门写了迁移指南。
- LlamaIndex 的 `ChatMemoryBuffer` 已标为弃用，换成 `Memory`。
- 两家厂商 SDK 都还在 0.x，按惯例 0.x 版本之间不保证接口兼容。
- 底下的协议也在变：MCP 已经弃用 SSE 传输（第 120 讲），框架里对应的类迟早要跟着改。

应对办法很朴素：锁定版本号，升级前读 changelog，升级后拿第 130 讲的 eval 集跑一遍回归。

## 建议：先用最少的抽象

按这个顺序来：

1. **先用前面几讲的手写版跑通。** 一个 while 循环、一个工具注册表、一个消息数组、一个最大步数，几十行代码。这一步的目的不是省依赖，而是让你知道每一步发出去的是什么、收回来的是什么。
2. **需要哪块再补哪块。** 上下文涨满了，加第 110 讲的摘要；要看清楚过程，加第 130 讲的 span 记录。每加一块，你都清楚它改了什么。
3. **出现这几个信号时再上框架：** 需要持久化状态、从中断处恢复；需要在某一步停下等人确认，可能等很久；流程有复杂的分支、并行和多个 Agent。这些东西手写也能写，但要写对（特别是「恢复时不重复执行有副作用的工具」）很费功夫，正是框架最值钱的地方。
4. **上了框架，也只用你需要的那一层。** 只要状态持久化，就只用 LangGraph 的图和 checkpointer，不必顺手把模型调用、检索也全换成框架的组件。框架越往上包，你和模型之间隔的东西越多。

判断标准始终是同一个：**你能不能说清楚，框架在这一步替你往模型的上下文里放了什么。** 说得清，就放心用；说不清，先回到手写版把它弄明白。

## 回顾整个 Agent 篇

模型篇讲的是模型内部，Agent 篇讲的是**模型外面的那个程序**，而这个程序是一层一层长出来的。第 100 讲，模型只会生成一段「我要调这个工具」的文本，是你的程序去执行、再把结果塞回对话；第 105 讲在外面套一个 while 循环，这就是 Agent，同时也带来了上下文每圈变长、总发送量二次方增长的问题；第 110 讲回答装不下怎么办：窗口是工作记忆，要截断、摘要、把要紧的事写进持久记忆，并靠 prompt cache 省钱；第 115 讲把窗口装不下的外部知识留在外面，按问题检索，只把相关的几段取回来；第 120 讲给工具定了一个统一插口，让 M × N 份对接代码变成 M + N；第 125 讲把生成过程用 SSE 一段段推给用户，让人不必对着空白干等；第 130 讲把每一次运行记成一棵 span 树，在上面打分、做回归、在危险动作之前拦截；第 135 讲让请求在多个模型和多个 Agent 之间转发和分工。这一讲回头看，所有框架都只是这八块的不同打包方式。部件你都亲手做过一遍了，换哪个框架，你都知道它的每一层底下是什么。

## 练习

**1.** 把第 105 讲那个 while 循环的每一行，对应到 OpenAI Agents SDK 的 `Runner.run()` 里：谁负责「把整个数组发给模型」、谁负责「执行工具并追加结果」、谁负责「没有 tool_use 就退出」？第 105 讲说的三道兜底（最大步数、预算、人工确认），在这个 SDK 里分别是什么？

<details>
<summary>参考答案</summary>

`Runner` 内部就是那个循环：每一轮把 `Agent` 的 instructions、工具定义和到目前为止的全部条目发给模型；模型返回工具调用时，`Runner` 执行 `@function_tool` 包好的函数并把结果作为新条目追加；模型给出最终输出、不再调工具时，循环结束，结果在 `result.final_output`。三道兜底：最大步数是 `max_turns`（默认 10，超了抛 `MaxTurnsExceeded`）；预算没有直接对应的参数（对照：Claude Agent SDK 有 `max_budget_usd`）；人工确认是工具上的 `needs_approval`，运行会暂停，用 `RunState.approve()` / `reject()` 决定后再继续。

</details>

**2.** 一个用 Claude Agent SDK 写的代码助手，用户在第一条消息里说「不要修改 `migrations/` 目录」。跑到第 40 轮，它改了那个目录下的文件。最可能的原因是什么？至少给出两种修法。

<details>
<summary>参考答案</summary>

最可能是上下文接近上限时发生了自动 compaction，第一条消息被换成了摘要，这条规则在摘要里丢了（流里会有一条 `compact_boundary` 系统消息可以核对）。修法：① 把规则写进 `CLAUDE.md` 并通过 `setting_sources` 加载，它每次请求都会重新注入，不受压缩影响；② 不靠模型记住，用权限兜底：`PreToolUse` hook 检查 `Edit` / `Write` 的路径，命中 `migrations/` 就拒绝，或者在权限规则里禁止写这个目录；③ 在 `CLAUDE.md` 里写明压缩时必须保留哪些约束。②是最可靠的，因为它不依赖模型看没看见。

</details>

**3.** 你要做一个报销审核 Agent：它查发票、算金额，超过 5000 元的单子必须停下来等主管批准，主管可能第二天才处理。服务每天夜里会重启一次。用手写版、LangGraph、OpenAI Agents SDK 分别怎么实现「停下来、隔天接着跑」？

<details>
<summary>参考答案</summary>

关键都是把循环的状态存到进程外面。**手写**：遇到需要批准的工具调用时，把整个消息数组和待执行的调用写进数据库，标记「待审批」，结束本次运行；主管批准后，从数据库读回数组，执行那次调用，把结果追加进去，再进入循环。要特别小心已经执行过的工具不能重复执行。**LangGraph**：配一个持久的 checkpointer（如 `PostgresSaver`），在审批节点里调用 `interrupt()`；第二天用同一个 `thread_id` 调 `invoke(Command(resume=批准结果))` 恢复。注意被中断的节点恢复时会从节点开头重跑，`interrupt()` 之前不要放有副作用的操作。**OpenAI Agents SDK**：给「提交报销」工具设 `needs_approval`，运行暂停后把 `RunState` 用 `to_json()` 存起来；第二天读回来，`approve()` 或 `reject()` 后再交给 `Runner` 继续。

</details>

**4.** 公司规定只能调用自己机房部署的开源模型（提供 OpenAI 兼容接口），并且所有 trace 不能离开内网。上面五个框架里哪些可以直接排除？剩下的要注意什么？

<details>
<summary>参考答案</summary>

Claude Agent SDK 直接排除，它只跑 Claude 模型。OpenAI Agents SDK 可以接（经 LiteLLM 等扩展或 OpenAI 兼容接口），但 `FileSearchTool`、`HostedMCPTool`、`WebSearchTool` 这些托管工具都依赖 OpenAI 平台，用不了；而且它的 trace 默认上传到 OpenAI，必须用 `set_tracing_disabled(True)` 或环境变量关掉，再用 `set_trace_processors()` 换成内网的 processor。LangChain / LangGraph / LlamaIndex 不绑定模型，更合适；LangChain 系的默认 trace 去 LangSmith，需要确认关闭或改用自部署方案，LlamaIndex 用 `instrumentation` 接内网的可观测性系统。

</details>

**5.** 你把 LangChain 从 1.3 升到 1.4 之后，同一套 30 道题的 eval 总分没变，但用户反馈「有些问题它以前会查知识库，现在不查了」。按第 130 讲的方法，你该怎么定位？

<details>
<summary>参考答案</summary>

总分没变不代表没有退化，先看逐题的四格计数，找出「过 → 挂」的题，再按题型分组，看是不是集中在需要检索的题上。然后对比新旧版本同一道题的 trace：模型这一轮收到的工具列表、工具说明、系统提示是否一样（框架升级可能改了工具的包装方式、加载方式或默认中间件），以及模型这一轮有没有生成调用检索工具的 `tool_use`。定位到差异后，要么锁回旧版本，要么显式写死那部分配置，并把这几道题补进回归集。

</details>

## 延伸阅读

- Erik Schluntz, Barry Zhang, [Building effective agents](https://www.anthropic.com/research/building-effective-agents), Anthropic (2024-12-19)，「When and how to use frameworks」一节
- LangChain：[LangChain v1 发布说明](https://docs.langchain.com/oss/python/releases/langchain-v1)、[Middleware](https://docs.langchain.com/oss/python/langchain/middleware/overview)、[MCP](https://docs.langchain.com/oss/python/langchain/mcp)、[Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent)
- LangGraph：[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)、[Human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/human-in-the-loop)、[Durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)
- Claude Agent SDK：[Overview](https://code.claude.com/docs/en/agent-sdk/overview)、[How the agent loop works](https://code.claude.com/docs/en/agent-sdk/agent-loop)
- OpenAI Agents SDK：[文档首页](https://openai.github.io/openai-agents-python/)、[Tracing](https://openai.github.io/openai-agents-python/tracing/)、[Sessions](https://openai.github.io/openai-agents-python/sessions/)、[MCP](https://openai.github.io/openai-agents-python/mcp/)
- LlamaIndex：[Agents](https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents)、[Memory](https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/)、[Human in the loop](https://developers.llamaindex.ai/python/framework/understanding/agent/human_in_the_loop/)、[Instrumentation](https://developers.llamaindex.ai/python/framework/module_guides/observability/instrumentation)
