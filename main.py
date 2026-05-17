import asyncio
import os
from typing import Annotated
from pathlib import Path
from easyagent import Agent, Memory, StepType, MCPSession


async def get_weather(city: str) -> str:
    """获取天气，仅支持到城市，示例：上海
    如果天气特殊，建议再调用get_weather_detail获取详细信息"""
    return f"历史最强暴雨，市政府已责令所有户外工作暂停，请待在家里。"


def get_weather_detail(city: Annotated[str, "可以精确到区，示例：上海/青浦区"]) -> str:
    """获取天气详情"""
    return "红色雷暴雨"


# 记忆功能
if os.path.exists("./memory.json"):
    memory = Memory.load("./memory.json")
else:
    memory = Memory()
# 提示词
if os.path.exists("./prompt.md"):
    prompt = Path("./prompt.md").read_text(encoding="utf-8")
else:
    prompt = "说话尽量简短，不要给任何附加提醒"


async def main():
    # 使用MCP，有的话
    try:
        async with (MCPSession.streamable_http("http://127.0.0.1:12306/mcp") as browser,
                    MCPSession.stdio("npx -y @modelcontextprotocol/server-filesystem .") as file_system,
                    MCPSession.sse("http://127.0.0.1:8000/mcp/sse") as item):
            # 一个本地函数，一个浏览器操作，一个文件系统操作，一个自实现的物品操作
            tools = [get_weather, get_weather_detail] + await browser.list_tools() + await file_system.list_tools() + await item.list_tools()
            print("工具:", *(f.__name__ for f in tools))
            await chat_loop(tools)
    except Exception as e:
        print(f"MCP未启动，将不使用MCP: {e}")
        tools = [get_weather, get_weather_detail]
        await chat_loop(tools)


async def chat_loop(tools):
    agent = Agent(os.environ["MODEL"], memory=memory, prompt=prompt, tools=tools)
    print("按q退出")
    # 理论上应该异步读取用户输入，避免堵塞循环，但在这个简单例子中没关系
    while (msg := input("我：")) != "q":
        last_type = None
        async for step in agent.execute(msg):
            if step.type == StepType.REASONING:
                if last_type != StepType.REASONING:
                    print()
                    print("思考: ", end="")
                print(step.reasoning, end="")
            elif step.type == StepType.CONTENT:
                if last_type != StepType.CONTENT:
                    print()
                    print("输出: ", end="")
                print(step.content, end="")
            elif step.type == StepType.TOOL_CALL:
                print()
                print(f"工具调用: {step.func.__name__}({step.args})")
            elif step.type == StepType.TOOL_RESULT:
                if step.error:
                    print(f" - 错误: {step.error}")
                else:
                    print(f" - 结果: {step.result}")
            last_type = step.type
        print()
    memory.save("./memory.json")


if __name__ == "__main__":
    asyncio.run(main())
