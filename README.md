# Axi-EasyAgent

[中文文档](README_CN.md) | [English Documentation](README.md)

A lightweight Python AI agent framework with conversation management, tool calling, and memory persistence capabilities.

How lightweight is it?

![001.png](001.png)

## Why Axi-EasyAgent?

Do you know how much space a typical AI library takes nowadays? Up to 200MB! That's larger than a web browser!  
If you only want AI to call your functions, how much of that 200MB do you actually need? The answer is right here.

## Features

- 🤖 **Smart Conversations**: Streaming conversation support based on OpenAI-compatible APIs
- 🔧 **Tool Calling**: Automatically convert Python functions into AI-callable tools
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
memory.add_user_message("Hello!")
memory.add_assistant_message("Hi! How can I help you?")

# Or load from file
import os
if os.path.exists("./memory.json"):
    memory = Memory.load("./memory.json")
```

Memory features:
- Automatically compresses when exceeding length limit (default: 70 messages)
- Supports saving/loading JSON files
- Can inherit and customize memory management

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
    complete_memory=True,  # Save tool calls and thinking to memory
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

## Core Components

### Agent Class

The core agent class responsible for managing conversations, tool calls, and memory.

**Parameters:**
- `model` (str): Model name
- `base_url` (str, optional): API base URL
- `api_key` (str, optional): API key
- `memory` (Memory, optional): Memory instance
- `prompt` (str, optional): System prompt
- `client` (httpx.AsyncClient, optional): HTTP client
- `tools` (list[Callable | dict], optional): Available tools list
- `other_params` (dict, optional): Additional request parameters
- `complete_memory` (bool): Whether to save tool call and thinking processes to memory (default: True)
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

Conversation memory management class that inherits from list, supporting message CRUD operations and persistence. If you want to customize memory management, you can inherit from the `Memory` class and implement relevant methods.

**Main Methods:**
- `add_user_message(message)`: Add user message
- `add_assistant_message(message)`: Add assistant message
- `load(json_file)`: Load memory from JSON file
- `save(json_file)`: Save memory to JSON file
- `compress()`: Compress memory by removing reasoning content and tool call records
- `copy()`: Create a copy of the memory
- `need_compress()`: Check if memory needs compression

### Exception Classes

- `MaxToolCallError`: Raised when the maximum tool call limit is exceeded. Contains the memory state for potential recovery.
- `ModelResponseError`: Raised when the model returns an invalid response. Contains the response, payload, and error message.
