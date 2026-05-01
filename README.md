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

### 3. Memory Persistence

```python
import os
from easyagent import Agent, Memory

# Load existing memory or create new memory
if os.path.exists("./memory.json"):
    memory = Memory.load("./memory.json")
else:
    memory = Memory()
    memory.add_message("Hello!")  # role: user
    memory.add_message("You're bad!")  # role: assistant

agent = Agent("deepseek-v4-flash", memory=memory)

# Save memory after conversation
memory.save("./memory.json")
```

## Core Components

### Agent Class

The core agent class responsible for managing conversations, tool calls, and memory.

**Parameters:**
- `model` (str): Model name
- `base_url` (str, optional): API base URL
- `api_key` (str, optional): API key
- `memory` (Memory, optional): Memory instance
- `prompt` (str, optional): System prompt
- `tools` (list[Callable], optional): Available tools list
- `complete_memory` (bool): Whether to save tool call and thinking processes to memory
- `max_tool_call` (int): Maximum tool call limit

### Memory Class

Conversation memory management class that inherits from list, supporting message CRUD operations and persistence. If you want to customize memory management, you can inherit from the `Memory` class and implement relevant methods.

**Main Methods:**
- `add_user_message(message)`: Add user message
- `add_assistant_message(message)`: Add assistant message
- `load(json_file)`: Load memory from JSON file
- `save(json_file)`: Save memory to JSON file
- `compress()`: Compress memory by removing reasoning content and tool call records
