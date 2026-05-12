import inspect
import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Callable

import httpx
from httpx import Response
from httpx_sse import aconnect_sse

from easyagent.interface import IMemory, IContext
from easyagent.memory import Memory
from easyagent.util import build_tool


class MaxToolCallError(Exception):
    """工具调用次数超过限制"""
    def __init__(self, context: IContext):
        self.context = context  # 可用来恢复记忆，但它保留了最后一次工具调用，如果要用，需要处理最后的记录


class ModelResponseError(Exception):
    """模型返回错误"""
    def __init__(self, response: Response, payload: dict, message: str = ""):
        super().__init__(message)
        self.response = response
        self.payload = payload
        self.message = message


class StepType(Enum):
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CONTENT = "content"


@dataclass
class AgentEvent:
    """
    响应步骤
    一般模型思考步骤如下
    思考->工具调用->思考->输出->工具调用->输出
    :ivar type: 步骤类型
    :ivar reasoning: 思考内容
    :ivar content: 输出内容
    :ivar func: 调用的工具
    :ivar args: 工具的参数，下一步必有tool_call_result或tool_call_error
    :ivar error: 工具返回的错误
    :ivar result: 工具的结果
    """
    type: StepType
    # 核心内容
    reasoning: str | None = None
    content: str | None = None
    # 工具相关
    func: Callable | None = None
    args: dict | None = None
    result: Any | None = None
    error: Exception | None = None


class Agent:
    """
    一个聊天助手，支持工具调用和记忆
    """
    def __init__(
            self,
            model: str,
            base_url: str | None = None,
            api_key: str | None = None,
            memory: IMemory | None = None,
            *,
            prompt: str | None = None,
            client: httpx.AsyncClient | None = None,
            tools: list[Callable | dict] | None = None,
            other_params: dict | None = None,
            max_tool_call: int = 20
    ):
        """
        :param model: 模型名称
        :param base_url: OpenAI API 的基础 URL
        :param api_key: OpenAI API 的密钥
        :param memory: 记忆对象
        :param prompt: 系统提示
        :param client: HTTP 客户端
        :param tools: 工具列表，可以是一个函数，会自动包装成工具，并自动调用，也可以是一个字典，用于定义模型内置工具
        :param other_params: 请求中的json其他参数
        :param max_tool_call: 工具调用次数限制
        """
        self.client = client or httpx.AsyncClient(
            base_url=base_url or os.environ["OPENAI_BASE_URL"],
            headers={
                "Authorization": f"Bearer {api_key or os.environ['OPENAI_API_KEY']}",
            },
            timeout=10
        )
        self.model = model
        self.memory = memory if memory is not None else Memory()
        self.other_params = other_params if other_params is not None else {}
        self.max_tool_call = max_tool_call
        self.prompt = prompt
        # 工具部分
        self._tool_registry: dict[str, Callable] # 函数名与函数的映射，用于加快查找
        self._tool_definitions: list[dict]  # 工具的schema缓存，用于减少重复计算
        self._tools: list[Callable | dict]
        self.tools = tools if tools is not None else []

    @property
    def tools(self) -> list[Callable | dict]:
        return self._tools

    @tools.setter
    def tools(self, tools: list[Callable | dict]):
        self._tools = tools
        self._tool_definitions = []
        self._tool_registry = {}
        for func in tools:
            if callable(func):
                self._tool_registry[func.__name__] = func
                self._tool_definitions.append(build_tool(func))
            else:
                self._tool_definitions.append(func)

    async def chat(self, message: str, *, tool_choice: str = "auto") -> AsyncGenerator[str, Any]:
        async for step in self.execute(message, tool_choice=tool_choice):
            if step.content:
                yield step.content

    async def execute(self, message: str, *, tool_choice: str = "auto", save_memory: bool = True) -> AsyncGenerator[AgentEvent, Any]:
        context = self.memory.build_context(message, self.prompt)
        payload = {
            "model": self.model,
            "stream": True,
            **self.other_params
        }
        if self._tool_definitions:
            payload["tools"] = self._tool_definitions
            payload["tool_choice"] = tool_choice
        async for step in self._call(payload, context, self._tool_registry, self.max_tool_call, 0):
            yield step
        if save_memory:
            self.memory.store(context)


    async def _call(self, payload, context, tool_registry, max_tool_call, current_tool_call) -> AsyncGenerator[AgentEvent, Any]:
        """调用Openai Api，并处理工具调用"""
        output = ""
        reasoning_output = ""
        used_tools: list[dict] = []
        payload["messages"] = context.get_messages()
        async with aconnect_sse(self.client, "POST", f"/chat/completions", json=payload) as event_source:
            # 检查一下，如果不是sse协议就直接读取异常信息，否则下面就读不到了
            if "text/event-stream" not in event_source.response.headers.get("content-type", "").partition(";")[0]:
                err = (await event_source.response.aread()).decode()
                raise ModelResponseError(event_source.response, payload, err)
            async for event in event_source.aiter_sse():
                if event.data == "[DONE]":
                    break
                parse = json.loads(event.data)
                if not parse['choices']:
                    continue
                delta = parse['choices'][0].get('delta', {})
                if reasoning_content := delta.get('reasoning_content'):
                    reasoning_output += reasoning_content
                    yield AgentEvent(StepType.REASONING, reasoning=reasoning_content)
                elif content := delta.get('content'):
                    output += content
                    yield AgentEvent(StepType.CONTENT, content=content)
                elif tool_calls := delta.get('tool_calls'):
                    for tool_call in tool_calls:
                        if len(used_tools) < tool_call['index'] + 1:
                            used_tools.append(tool_call)
                        else:
                            used_tools[tool_call['index']]['function']['arguments'] += tool_call['function']['arguments'] or ''
        record: dict[str, Any] = {"role": "assistant"}
        if output:
            record["content"] = output
        if reasoning_output:
            record["reasoning_content"] = reasoning_output
        if used_tools:
            record["tool_calls"] = used_tools
            context.add_message(record)
            if current_tool_call >= max_tool_call:
                raise MaxToolCallError(context)
            for tool_call in used_tools:
                function = tool_registry[tool_call['function']['name']]
                args = json.loads(tool_call['function']['arguments'])
                yield AgentEvent(StepType.TOOL_CALL, func=function, args=args)
                try:
                    if inspect.iscoroutinefunction(function):
                        result = await function(**args)
                    else:
                        result = function(**args)
                    result = str(result)
                except Exception as e:
                    yield AgentEvent(StepType.TOOL_RESULT, func=function, args=args, error=e)
                    result = f"Function {function.__name__} call failed: {e}"
                else:
                    yield AgentEvent(StepType.TOOL_RESULT, func=function, args=args, result=result)
                context.add_message({'role': 'tool', 'tool_call_id': tool_call['id'], 'content': result})
            # 递归调用
            async for step in self._call(payload, context, tool_registry, max_tool_call, current_tool_call + 1):
                yield step
        else:
            context.add_message(record)

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()