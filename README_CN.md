# Axi-EasyAgent

[中文文档](README_CN.md) | [English Documentation](README.md)

一个轻量的Python AI智能体框架，支持对话管理、工具调用和记忆持久化功能。

轻量到什么长度？  

![001.png](001.png)

## 写在前面的话
你知道现在一个AI库要多少空间吗？竟然要200MB！这么多空间比一个浏览器还大！  
如果只想要让AI调一下你的函数，那你能用到这200MB中的多少？ 答案就在这里.

## 功能特性

- 🤖 **智能对话**：基于OpenAI兼容API的流式对话支持
- 🔧 **工具调用**：自动将Python函数转换为AI可调用的工具
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

### 3. 记忆持久化

```python
import os
from easyagent import Agent, Memory

# 加载已有记忆或创建新记忆
if os.path.exists("./memory.json"):
    memory = Memory.load("./memory.json")
else:
    memory = Memory()
    memory.add_message("你好！")  # role:user
    memory.add_message("你坏！")  # role:assistant

agent = Agent("deepseek-v4-flash", memory=memory)

# 对话结束后保存记忆
memory.save("./memory.json")
```

## 核心组件

### Agent 类

智能体核心类，负责管理对话、工具调用和记忆。

**参数说明：**
- `model` (str): 模型名称
- `base_url` (str, optional): API基础URL
- `api_key` (str, optional): API密钥
- `memory` (Memory, optional): 记忆实例
- `prompt` (str, optional): 系统提示词
- `tools` (list[Callable], optional): 可用工具列表
- `complete_memory` (bool): 是否将工具调用和思考过程保存到记忆中
- `max_tool_call` (int): 最大工具调用次数限制

### Memory 类

对话记忆管理类，继承自list，支持消息的增删改查和持久化。如果希望自定义记忆管理，可以继承 `Memory` 类并实现相关方法。

**主要方法：**
- `add_user_message(message)`: 添加用户消息
- `add_assistant_message(message)`: 添加助手消息
- `load(json_file)`: 从JSON文件加载记忆
- `save(json_file)`: 保存记忆到JSON文件
- `compress()`: 压缩记忆，移除推理内容和工具调用记录
