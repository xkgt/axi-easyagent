import inspect
import json
import os
from typing import Any, AsyncGenerator, Callable

import httpx
from httpx import Response
from httpx_sse import aconnect_sse

from easyagent.memory import Memory
from easyagent.util import build_tool


class MaxToolCallError(Exception):
    """工具调用次数超过限制"""
    def __init__(self, memory: Memory):
        self.memory = memory  # 可用来恢复记忆，但它保留了最后一次工具调用，如果要用，需要处理最后的记录

    @property
    def effective_memory(self) -> Memory:
        """有效的记忆，不包括工具调用"""
        m = self.memory.copy()
        del m[-1]["tool_calls"]  # 因为错误来自于工具调用限制，所以一定会有tool_calls键
        if "content" not in m[-1] and "reasoning_content" not in m[-1]:  # 如果没有内容，则删除整条记录
            m.pop(-1)
        return m


class ModelResponseError(Exception):
    """模型返回错误"""
    def __init__(self, response: Response, payload: dict, message: str = ""):
        super().__init__(message)
        self.response = response
        self.payload = payload
        self.message = message


class Agent:
    """
    一个聊天助手，支持工具调用和记忆
    """
    def __init__(
            self,
            model: str,
            base_url: str | None = None,
            api_key: str | None = None,
            memory: Memory | None = None,
            *,
            prompt: str | None = None,
            client: httpx.AsyncClient | None = None,
            tools: list[Callable | dict] | None = None,
            other_params: dict | None = None,
            complete_memory: bool = True,
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
        :param complete_memory: 是否将工具调用、思考也保存进记忆
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
        self.complete_memory = complete_memory
        self.max_tool_call = max_tool_call
        self.prompt = prompt
        # 工具部分
        self._tool_registry: dict[str, Callable] = ... # 函数名与函数的映射，用于加快查找
        self._tool_definitions: list[dict] = ...  # 工具的schema缓存，用于减少重复计算
        self._tools: list[Callable | dict] = ...
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
        memory = self.memory.copy()
        if self.prompt:
            memory.insert(0, {'role': 'system', 'content': self.prompt})
        new_memory_index = len(memory)
        memory.add_user_message(message)
        payload = {
            "model": self.model,
            "messages": memory,
            "stream": True,
            **self.other_params
        }
        if self._tool_definitions:
            payload["tools"] = self._tool_definitions
            payload["tool_choice"] = tool_choice
        output = ""
        err = None
        try:
            async for content in self._call(payload, memory, self._tool_registry, self.max_tool_call, 0):
                output += content
                yield content
        except MaxToolCallError as e:
            err = e
            memory = e.effective_memory
        if self.complete_memory:
            self.memory.extend(memory[new_memory_index:])
        else:
            self.memory.add_user_message(message)
            self.memory.add_assistant_message(output)
        if err:
            raise err


    async def _call(self, payload, memory, tool_registry, max_tool_call, current_tool_call) -> AsyncGenerator[str, Any]:
        """调用Openai Api，并处理工具调用"""
        output = ""
        reasoning_output = ""
        used_tools: list[dict] = []
        async with aconnect_sse(self.client, "POST", f"/chat/completions", json=payload) as event_source:
            # 检查一下，如果不是sse协议就直接读取异常信息，否则下面就读不到了
            if "text/event-stream" not in event_source.response.headers.get("content-type", "").partition(";")[0]:
                err = (await event_source.response.aread()).decode()
                raise ModelResponseError(event_source.response, payload, err)
            async for event in event_source.aiter_sse():
                if event.data == "[DONE]":
                    break
                parse = json.loads(event.data)
                delta = parse['choices'][0].get('delta', {})
                if content := delta.get('content'):
                    output += content
                    yield content
                elif reasoning_content := delta.get('reasoning_content'):
                    reasoning_output += reasoning_content
                elif tool_calls := delta.get('tool_calls'):
                    for tool_call in tool_calls:
                        if len(used_tools) < tool_call['index'] + 1:
                            used_tools.append(tool_call)
                        used_tools[tool_call['index']]['function']['arguments'] += tool_call['function']['arguments'] or ''
        record = {"role": "assistant"}
        if output:
            record["content"] = output
        if reasoning_output:
            record["reasoning_content"] = reasoning_output
        if used_tools:
            record["tool_calls"] = used_tools
            memory.append(record)
            if current_tool_call >= max_tool_call:
                raise MaxToolCallError(memory)
            for tool_call in used_tools:
                function = tool_registry[tool_call['function']['name']]
                args = json.loads(tool_call['function']['arguments'])
                if inspect.iscoroutinefunction(function):
                    result = await function(**args)
                else:
                    result = function(**args)
                memory.append({'role': 'tool', 'tool_call_id': tool_call['id'], 'content': result})
            async for content in self._call(payload, memory, tool_registry, max_tool_call, current_tool_call + 1):
                yield content
        else:
            memory.append(record)
