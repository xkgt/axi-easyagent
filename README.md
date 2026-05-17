# Axi-EasyAgent

[中文文档](README_CN.md) | [English Documentation](README.md)

A lightweight and simple Python AI agent framework — turn your Python functions into AI tools, connect MCP servers with zero friction, and manage conversations with built-in memory.

How lightweight is it?

![001.png](001.png)

## Why Axi-EasyAgent?
Do you know how much space a typical AI library takes nowadays? Up to 200MB! That's larger than a web browser!  
If you only want AI to call your functions, how much of that 200MB do you actually need? The answer is right here.

## Features

- 🤖 **Smart Conversations**: Streaming conversation support based on OpenAI-compatible APIs
- 🔧 **Tool Calling**: Automatically convert Python functions into AI-callable tools
- 🔌 **MCP Integration**: Seamless MCP server connection — tools from MCP servers become callables just like your own functions
- 💾 **Memory Management**: Built-in conversation memory system with persistent storage and auto-compression
- ⚡ **Async Processing**: Full async programming support for improved response efficiency
- 🔄 **Streaming Output**: Real-time streaming responses for enhanced user experience

## Installation

```bash
pip install axi-easyagent
```

## Quick Start

### 1. Environment Configuration

Configure environment variables, or hardcode them directly in your code (not recommended)
```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=your-api-key-here
```
Note: easyagent does not automatically read .env files. Please load them yourself.

### 2. Quick Start Example

```python
import asyncio
from typing import Annotated
from easyagent import Agent

async def get_weather(city: str) -> str:
    """Get weather information"""
    return f"The weather in {city} is sunny"

def get_weather_detail(city: Annotated[str, "Can be precise to district, e.g.: Shanghai/Qingpu District"]) -> str:
    """Get detailed weather information"""
    return f"Detailed weather info for {city}: Temperature 25°C, Humidity 60%"

async def main():
    agent = Agent(
        "deepseek-v4-flash",
        tools=[get_weather, get_weather_detail],
        prompt="Keep responses brief"
    )
    
    while (msg := input("You: ")) != "q":
        async for output in agent.chat(msg):
            print(output, end="")
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

## Step-by-Step Guide

### Step 1: Create Memory

Memory is used to store conversation history. You can create a new memory or load existing memory:

```python
from easyagent import Memory

# Create new memory
memory = Memory()
memory.store_turn("Hello!", "Hi! How can I help you?")

# Or load from file
import os

if os.path.exists("./memory.json"):
    memory = Memory.load("./memory.json")
```

Memory features:
- Automatically compresses when exceeding length limit (default: 70 messages)
- Supports saving/loading JSON files
- Can inherit and customize memory management via `IMemory` interface

### Step 2: Create Agent

Create an AI assistant with various configuration options:

```python
from easyagent import Agent

# Basic creation
agent = Agent("deepseek-v4-flash")

# With memory
agent = Agent("deepseek-v4-flash", memory=memory)

# With system prompt
agent = Agent("deepseek-v4-flash", prompt="You are a helpful assistant")

# With tools
async def get_weather(city: str) -> str:
    """Get weather information"""
    return f"The weather in {city} is sunny"

agent = Agent("deepseek-v4-flash", tools=[get_weather])

# Full configuration
agent = Agent(
    model="deepseek-v4-flash",
    base_url="https://api.example.com/v1",
    api_key="your-api-key",
    memory=memory,
    prompt="Keep responses brief",
    tools=[get_weather],
    max_tool_call=20  # Maximum tool call limit
)
```

### Step 3: Use chat Method

The `chat` method is the simplest way to interact with the agent, returning only the final output content:

```python
import asyncio
from easyagent import Agent

async def main():
    agent = Agent("deepseek-v4-flash", prompt="Keep responses brief")
    
    while (msg := input("You: ")) != "q":
        async for output in agent.chat(msg):
            print(output, end="")
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

Features:
- Returns streaming text output
- Automatically handles tool calls in the background
- Suitable for simple conversation scenarios

### Step 4: Use execute Method

The `execute` method provides detailed control over the entire response process, returning `AgentEvent` objects for each step:

```python
import asyncio
from easyagent import Agent, AgentEvent, StepType

async def main():
    agent = Agent("deepseek-v4-flash", prompt="Keep responses brief")
    
    while (msg := input("You: ")) != "q":
        last_type = None
        async for step in agent.execute(msg):
            # Handle reasoning content
            if step.type == StepType.REASONING:
                if last_type != StepType.REASONING:
                    print()
                    print("Thinking: ", end="")
                print(step.reasoning, end="")
            
            # Handle output content
            elif step.type == StepType.CONTENT:
                if last_type != StepType.CONTENT:
                    print()
                    print("Output: ", end="")
                print(step.content, end="")
            
            # Handle tool call
            elif step.type == StepType.TOOL_CALL:
                print()
                print(f"Tool Call: {step.func.__name__}({step.args})", end="")
            
            # Handle tool result
            elif step.type == StepType.TOOL_RESULT:
                if step.error:
                    print(f" - Error: {step.error}")
                else:
                    print(f" - Result: {step.result}")
            
            last_type = step.type
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

Event types (StepType):
- `REASONING`: Model thinking process
- `CONTENT`: Model output content
- `TOOL_CALL`: Tool being called
- `TOOL_RESULT`: Tool execution result (success or error)

Advantages:
- Real-time display of thinking process
- Monitor tool call details
- Handle errors gracefully
- Suitable for complex scenarios requiring detailed control

## MCP Integration

Axi-EasyAgent provides first-class MCP (Model Context Protocol) support. You can connect to any MCP server via SSE, Stdio, or Streamable HTTP — and its tools become regular Python functions you can call directly or pass to the Agent.

### Quick Example

```python
import asyncio
from easyagent import Agent, MCPSession

async def main():
    # Connect to an MCP server via stdio (e.g., a filesystem server)
    async with MCPSession.stdio("npx -y @modelcontextprotocol/server-filesystem .") as session:
        # list_tools() returns a list of callable functions — just like your own!
        tools = await session.list_tools()
        
        # Each tool is a real Python function with proper signature, docstring, and type hints
        print(tools[0].__name__)          # e.g. "read_file"
        print(tools[0].__doc__)           # tool description from the MCP server
        
        # You can call them directly like any function
        content = await tools[0](path="README.md")
        print(content)
        
        # Or pass them to an Agent — exactly like your own functions
        agent = Agent("deepseek-v4-flash", tools=tools)
        async for output in agent.chat("What's in the README?"):
            print(output, end="")

asyncio.run(main())
```

### Mixing MCP Tools with Your Own Functions

MCP tools and your own Python functions are treated exactly the same — you can mix them freely:

```python
async def get_weather(city: str) -> str:
    """Get weather for a city"""
    return f"{city}: sunny, 25°C"

async with (
    MCPSession.stdio("npx -y @modelcontextprotocol/server-filesystem .") as fs,
    MCPSession.sse("http://localhost:8000/mcp/sse") as custom_server,
):
    # Mix local functions and MCP tools seamlessly
    all_tools = [get_weather] + await fs.list_tools() + await custom_server.list_tools()
    agent = Agent("deepseek-v4-flash", tools=all_tools)
```

### Supported Transport Types

| Transport | Factory Method | Use Case |
|-----------|---------------|----------|
| **Stdio** | `MCPSession.stdio(cmd)` | Local MCP servers launched as subprocesses |
| **SSE** | `MCPSession.sse(url)` | Remote MCP servers with Server-Sent Events |
| **Streamable HTTP** | `MCPSession.streamable_http(url)` | Remote MCP servers with HTTP streaming |

> **Key insight**: `MCPSession.list_tools()` introspects the MCP server's tool schemas and dynamically builds Python functions with proper `__name__`, `__doc__`, and `__input_schema__`. When you pass them to `Agent`, they work exactly like the functions you wrote by hand. No boilerplate, no manual schema wrangling.

## Core Components

### Agent Class

The core agent class responsible for managing conversations, tool calls, and memory.

**Parameters:**
- `model` (str): Model name
- `base_url` (str, optional): API base URL
- `api_key` (str, optional): API key
- `memory` (IMemory, optional): Memory instance (defaults to Memory())
- `prompt` (str, optional): System prompt
- `client` (httpx.AsyncClient, optional): HTTP client
- `tools` (list[Callable | dict], optional): Available tools list
- `other_params` (dict, optional): Additional request parameters
- `max_tool_call` (int): Maximum tool call limit (default: 20)

**Main Methods:**
- `chat(message, *, tool_choice="auto")`: Async generator that yields content strings
- `execute(message, *, tool_choice="auto", save_memory=True)`: Async generator that yields AgentEvent objects with detailed execution information

### AgentEvent Class

A dataclass representing a single event in the model's response process.

**Attributes:**
- `type` (StepType): Event type (REASONING, TOOL_CALL, TOOL_RESULT, CONTENT)
- `reasoning` (str | None): Model's thinking/reasoning content
- `content` (str | None): Model's output content
- `func` (Callable | None): The tool being called
- `args` (dict | None): Arguments passed to the tool
- `result` (Any | None): Result from tool execution
- `error` (Exception | None): Error from tool execution

### StepType Enum

Enumeration of event types in the response process:
- `REASONING`: Model is thinking/reasoning
- `TOOL_CALL`: Tool is being called
- `TOOL_RESULT`: Tool execution completed (with result or error)
- `CONTENT`: Model output content

### Memory Class

Conversation memory management class that inherits from list, supporting message CRUD operations and persistence. If you want to customize memory management, you can inherit from the `IMemory` interface and implement relevant methods.

**Main Methods:**
- `store_turn(user: str, assistant: str)`: Add a user-assistant message pair
- `build_context(query: str, system: str)`: Build context for the model
- `store(context: IContext)`: Store context messages into memory
- `compress()`: Compress memory by removing reasoning content and tool call records
- `save(file: str)`: Save memory to JSON file
- `load(file: str)`: Load memory from JSON file (class method)

### MCPSession Class

The MCP session manager that connects to MCP servers and exposes their tools as Python functions.

**Factory Methods:**
- `MCPSession.stdio(cmd: str)`: Connect via subprocess stdio
- `MCPSession.sse(sse_url: str, client: AsyncClient | None = None)`: Connect via SSE
- `MCPSession.streamable_http(url: str, client: AsyncClient | None = None)`: Connect via Streamable HTTP

**Main Methods:**
- `list_tools() -> list[Callable[..., Awaitable]]`: Fetch the MCP server's tool list and return them as callable async functions. Each function has proper `__name__`, `__doc__`, and input schema — ready to pass directly to `Agent(tools=...)`.

**Supports async context manager:**
```python
async with MCPSession.stdio("some-command") as session:
    tools = await session.list_tools()
```

### Transport Classes

- `SSETransport(sse_url, client)`: SSE-based transport for MCP servers
- `StdioTransport(cmd)`: Subprocess stdio-based transport for local MCP servers
- `StreamableHttpTransport(url, client)`: HTTP streaming transport for remote MCP servers

### Exception Classes

- `MaxToolCallError`: Raised when the maximum tool call limit is exceeded. Contains the context for potential recovery.
- `ModelResponseError`: Raised when the model returns an invalid response. Contains the response, payload, and error message.

### Utility Functions

- `build_tool(func: Callable)`: Converts a Python function to OpenAI API tool format, automatically extracting function signature, type hints, and docstring.
