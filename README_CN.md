# Axi-EasyAgent

[中文文档](README_CN.md) | [English Documentation](README.md)

一个轻量、简洁的 Python AI 智能体框架 — 将 Python 函数一键变成 AI 工具，零摩擦连接 MCP 服务，内置对话记忆管理。

轻量到什么程度？

![001.png](001.png)

## 写在前面的话
你知道现在一个AI库要多少空间吗？竟然要200MB！这么多空间比一个浏览器还大！  
如果只想要让AI调一下你的函数，那你能用到这200MB中的多少？ 答案就在这里.

## 功能特性

- 🤖 **智能对话**：基于OpenAI兼容API的流式对话支持
- 🔧 **工具调用**：自动将Python函数转换为AI可调用的工具
- 🔌 **MCP 集成**：无缝连接 MCP 服务 — MCP 服务的工具会变成和你自己写的函数一样的可调用对象
- 💾 **记忆管理**：内置对话记忆系统，支持持久化存储和自动压缩
- ⚡ **异步处理**：全面支持异步编程，提高响应效率
- 🔄 **流式输出**：实时流式响应，提升用户体验

## 安装

```bash
pip install axi-easyagent
```

## 快速开始

### 1. 环境配置

配置环境变量 ，或者直接写死在代码中（不建议）
```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=your-api-key-here
```
注：easyagent不会自动读取.env文件，请自行加载

### 2. 快速上手

```python
import asyncio
from typing import Annotated
from easyagent import Agent

async def get_weather(city: str) -> str:
    """获取天气信息"""
    return f"{city}的天气是晴天"

def get_weather_detail(city: Annotated[str, "可以精确到区，示例：上海/青浦区"]) -> str:
    """获取天气详细信息"""
    return f"{city}的详细天气信息：温度25°C，湿度60%"

async def main():
    agent = Agent(
        "deepseek-v4-flash",
        tools=[get_weather, get_weather_detail],
        prompt="说话尽量简短"
    )
    
    while (msg := input("我：")) != "q":
        async for output in agent.chat(msg):
            print(output, end="")
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

## 逐步教程

### 步骤 1：创建记忆

记忆用于存储对话历史，可以创建新记忆或加载已有记忆：

```python
from easyagent import Memory

# 创建新记忆
memory = Memory()
memory.store_turn("你好！", "嗨！有什么可以帮助你的？")

# 或从文件加载
import os

if os.path.exists("./memory.json"):
    memory = Memory.load("./memory.json")
```

记忆特性：
- 超过长度限制时自动压缩（默认：70条消息）
- 支持保存/加载JSON文件
- 可通过 `IMemory` 接口继承自定义记忆管理

### 步骤 2：创建助手

创建AI助手，支持多种配置选项：

```python
from easyagent import Agent

# 基础创建
agent = Agent("deepseek-v4-flash")

# 带记忆
agent = Agent("deepseek-v4-flash", memory=memory)

# 带系统提示词
agent = Agent("deepseek-v4-flash", prompt="你是一个有帮助的助手")

# 带工具
async def get_weather(city: str) -> str:
    """获取天气信息"""
    return f"{city}的天气是晴天"

agent = Agent("deepseek-v4-flash", tools=[get_weather])

# 完整配置
agent = Agent(
    model="deepseek-v4-flash",
    base_url="https://api.example.com/v1",
    api_key="your-api-key",
    memory=memory,
    prompt="说话尽量简短",
    tools=[get_weather],
    max_tool_call=20  # 最大工具调用次数限制
)
```

### 步骤 3：使用 chat 方法

`chat` 方法是最简单的交互方式，只返回最终的输出内容：

```python
import asyncio
from easyagent import Agent

async def main():
    agent = Agent("deepseek-v4-flash", prompt="说话尽量简短")
    
    while (msg := input("我：")) != "q":
        async for output in agent.chat(msg):
            print(output, end="")
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

特点：
- 返回流式文本输出
- 自动在后台处理工具调用
- 适合简单对话场景

### 步骤 4：使用 execute 方法

`execute` 方法提供对整个响应过程的详细控制，返回每个步骤的 `AgentEvent` 对象：

```python
import asyncio
from easyagent import Agent, AgentEvent, StepType

async def main():
    agent = Agent("deepseek-v4-flash", prompt="说话尽量简短")
    
    while (msg := input("我：")) != "q":
        last_type = None
        async for step in agent.execute(msg):
            # 处理思考内容
            if step.type == StepType.REASONING:
                if last_type != StepType.REASONING:
                    print()
                    print("思考: ", end="")
                print(step.reasoning, end="")
            
            # 处理输出内容
            elif step.type == StepType.CONTENT:
                if last_type != StepType.CONTENT:
                    print()
                    print("输出: ", end="")
                print(step.content, end="")
            
            # 处理工具调用
            elif step.type == StepType.TOOL_CALL:
                print()
                print(f"工具调用: {step.func.__name__}({step.args})", end="")
            
            # 处理工具结果
            elif step.type == StepType.TOOL_RESULT:
                if step.error:
                    print(f" - 错误: {step.error}")
                else:
                    print(f" - 结果: {step.result}")
            
            last_type = step.type
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

事件类型（StepType）：
- `REASONING`: 模型思考过程
- `CONTENT`: 模型输出内容
- `TOOL_CALL`: 工具被调用
- `TOOL_RESULT`: 工具执行结果（成功或错误）

优势：
- 实时显示思考过程
- 监控工具调用细节
- 优雅处理错误
- 适合需要精细控制的复杂场景

## MCP 集成

Axi-EasyAgent 提供了一流的 MCP（模型上下文协议）支持。你可以通过 SSE、Stdio 或 Streamable HTTP 连接任何 MCP 服务 — 其工具会变成普通的 Python 函数，可以直接调用或传给 Agent 使用。

### 快速示例

```python
import asyncio
from easyagent import Agent, MCPSession

async def main():
    # 通过 stdio 连接 MCP 服务（例如文件系统服务）
    async with MCPSession.stdio("npx -y @modelcontextprotocol/server-filesystem .") as session:
        # list_tools() 返回可调用函数列表 — 就像你自己写的一样！
        tools = await session.list_tools()
        
        # 每个工具都是真正的 Python 函数，有正确的签名、文档字符串和类型提示
        print(tools[0].__name__)          # 例如 "read_file"
        print(tools[0].__doc__)           # MCP 服务提供的工具描述
        
        # 你可以像普通函数一样直接调用
        content = await tools[0](path="README.md")
        print(content)
        
        # 或者传给 Agent — 和自己写的函数完全一样
        agent = Agent("deepseek-v4-flash", tools=tools)
        async for output in agent.chat("README里写了什么？"):
            print(output, end="")

asyncio.run(main())
```

### 混合使用 MCP 工具和自己的函数

MCP 工具和你自己的 Python 函数被完全同等对待 — 你可以自由混用：

```python
async def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city}：晴天，25°C"

async with (
    MCPSession.stdio("npx -y @modelcontextprotocol/server-filesystem .") as fs,
    MCPSession.sse("http://localhost:8000/mcp/sse") as custom_server,
):
    # 无缝混用本地函数和 MCP 工具
    all_tools = [get_weather] + await fs.list_tools() + await custom_server.list_tools()
    agent = Agent("deepseek-v4-flash", tools=all_tools)
```

### 支持的传输类型

| 传输方式 | 工厂方法 | 适用场景 |
|---------|---------|---------|
| **Stdio** | `MCPSession.stdio(cmd)` | 以子进程方式启动的本地 MCP 服务 |
| **SSE** | `MCPSession.sse(url)` | 使用 Server-Sent Events 的远程 MCP 服务 |
| **Streamable HTTP** | `MCPSession.streamable_http(url)` | 使用 HTTP 流式传输的远程 MCP 服务 |

> **核心要点**：`MCPSession.list_tools()` 会内省 MCP 服务的工具 schema，动态构建出带有正确 `__name__`、`__doc__` 和 `__input_schema__` 的 Python 函数。传入 `Agent` 后，它们和你手写的函数表现完全一样。无需样板代码，无需手动处理 schema。

## 核心组件

### Agent 类

智能体核心类，负责管理对话、工具调用和记忆。

**参数说明：**
- `model` (str): 模型名称
- `base_url` (str, optional): API基础URL
- `api_key` (str, optional): API密钥
- `memory` (IMemory, optional): 记忆实例（默认为Memory()）
- `prompt` (str, optional): 系统提示词
- `client` (httpx.AsyncClient, optional): HTTP客户端
- `tools` (list[Callable | dict], optional): 可用工具列表
- `other_params` (dict, optional): 请求中的其他参数
- `max_tool_call` (int): 工具调用次数限制 (默认: 20)

**主要方法：**
- `chat(message, *, tool_choice="auto")`: 异步生成器，生成内容字符串
- `execute(message, *, tool_choice="auto", save_memory=True)`: 异步生成器，生成包含详细执行信息的 AgentEvent 对象

### AgentEvent 类

表示模型响应过程中单个事件的数据类。

**属性：**
- `type` (StepType): 事件类型 (REASONING, TOOL_CALL, TOOL_RESULT, CONTENT)
- `reasoning` (str | None): 模型的思考/推理内容
- `content` (str | None): 模型的输出内容
- `func` (Callable | None): 被调用的工具
- `args` (dict | None): 传递给工具的参数
- `result` (Any | None): 工具执行的结果
- `error` (Exception | None): 工具执行的错误

### StepType 枚举

响应过程中的事件类型枚举：
- `REASONING`: 模型思考/推理
- `TOOL_CALL`: 工具被调用
- `TOOL_RESULT`: 工具执行完成（包含结果或错误）
- `CONTENT`: 模型输出内容

### Memory 类

对话记忆管理类，支持消息的增删改查和持久化。如果希望自定义记忆管理，可以继承 `IMemory` 接口并实现相关方法。

**主要方法：**
- `store_turn(user: str, assistant: str)`: 添加一轮用户和助手消息
- `build_context(query: str, system: str)`: 为模型构建上下文
- `store(context: IContext)`: 将上下文中的消息存储到记忆中
- `compress()`: 压缩记忆，移除推理内容和工具调用记录
- `save(file: str)`: 保存记忆到JSON文件
- `load(file: str)`: 从JSON文件加载记忆（类方法）

### MCPSession 类

MCP 会话管理器，负责连接 MCP 服务并将其工具暴露为 Python 函数。

**工厂方法：**
- `MCPSession.stdio(cmd: str)`：通过子进程标准输入输出连接
- `MCPSession.sse(sse_url: str, client: AsyncClient | None = None)`：通过 SSE 连接
- `MCPSession.streamable_http(url: str, client: AsyncClient | None = None)`：通过 Streamable HTTP 连接

**主要方法：**
- `list_tools() -> list[Callable[..., Awaitable]]`：获取 MCP 服务的工具列表，返回可调用的异步函数。每个函数都有正确的 `__name__`、`__doc__` 和输入 schema — 可直接传给 `Agent(tools=...)`。

**支持异步上下文管理器：**
```python
async with MCPSession.stdio("some-command") as session:
    tools = await session.list_tools()
```

### Transport 传输类

- `SSETransport(sse_url, client)`：基于 SSE 的 MCP 传输
- `StdioTransport(cmd)`：基于子进程标准输入输出的本地 MCP 传输
- `StreamableHttpTransport(url, client)`：基于 HTTP 流式传输的远程 MCP 传输

### 异常类

- `MaxToolCallError`: 当超过最大工具调用限制时抛出。包含可用于恢复的上下文。
- `ModelResponseError`: 当模型返回无效响应时抛出。包含响应、载荷和错误信息。

### 工具函数

- `build_tool(func: Callable)`: 将Python函数转换为OpenAI API工具格式，自动提取函数签名、类型提示和文档字符串。
