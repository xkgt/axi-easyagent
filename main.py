import asyncio
import os
from typing import Annotated

from easyagent import Agent, Memory


async def get_weather(city: str) -> str:
    """获取天气，仅支持到城市，示例：上海
    如果天气特殊，建议再调用get_weather_detail获取详细信息"""
    print(f"\n调用get_weather工具：{city}")
    print("历史最强暴雨")
    return f"历史最强暴雨，市政府已责令所有户外工作暂停，请待在家里。"


def get_weather_detail(city: Annotated[str, "可以精确到区，示例：上海/青浦区"]) -> str:
    """获取天气详情"""
    print(f"\n调用get_weather_detail工具：{city}")
    print("红色雷暴雨")
    return f"红色雷暴雨"


if os.path.exists("./memory.json"):
    memory = Memory.load("./memory.json")
else:
    memory = Memory()
a = Agent(os.environ["MODEL"], memory=memory, tools=[get_weather, get_weather_detail], prompt="说话尽量简短，不要给任何附加提醒")

async def main():
    print("按q退出")
    while (msg := input("我：")) != "q":
        async for output in a.chat(msg):
            print(output, end="")
        print()
    memory.save("./memory.json")

if __name__ == "__main__":
    asyncio.run(main())