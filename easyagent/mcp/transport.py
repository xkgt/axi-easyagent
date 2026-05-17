import asyncio
import json

from typing import Callable, Coroutine
from urllib.parse import urljoin

import httpx
from httpx import AsyncClient, Timeout
from httpx_sse import aconnect_sse, EventSource


async def no_handler(_):
    pass


class Transport:
    def __init__(self):
        self.on_message: Callable[[dict], Coroutine] = no_handler

    async def send(self, payload: dict):
        ...

    def is_alive(self) -> bool:
        ...

    async def __aenter__(self):
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...


class SSETransport(Transport):
    def __init__(self, sse_url: str, client: AsyncClient | None = None):
        """
        :param client: 注意自定义客户端的read超时必须为None，因为SSE会长时间无数据
        """
        super().__init__()
        self.sse_url = sse_url.rstrip("/")
        self.client = client or AsyncClient(timeout=Timeout(
            connect=10.0,
            read=None,  # SSE 必须禁用
            write=10.0,
            pool=10.0,
        ))
        self.message_url_future = asyncio.Future()
        self._listen_task: asyncio.Task | None = None

    def is_alive(self) -> bool:
        # 任务存在、没被取消、且没有执行结束
        return (
            self._listen_task is not None
            and not self._listen_task.done()
        )

    async def send(self, payload: dict):
        url = self.message_url_future.result()
        await self.client.post(url, json=payload)

    async def _listen(self):
        try:
            async with aconnect_sse(self.client, "GET", self.sse_url) as event_source:
                if "text/event-stream" not in event_source.response.headers.get("content-type", "").partition(";")[0]:
                    err = (await event_source.response.aread()).decode()
                    raise httpx.HTTPError(err)
                async for event in event_source.aiter_sse():
                    if event.event == "endpoint" and not self.message_url_future.done():
                        self.message_url_future.set_result(urljoin(self.sse_url, event.data))
                    elif event.event == "message":
                        await self.on_message(json.loads(event.data))
        except asyncio.CancelledError:
            ...
        except Exception as e:
            # 如果发生非取消类的异常，任务会结束，is_alive 将返回 False
            if not self.message_url_future.done():
                self.message_url_future.set_exception(e)
            raise e

    async def __aenter__(self):
        self._listen_task = asyncio.create_task(self._listen())
        await asyncio.wait_for(self.message_url_future, timeout=5)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        await self.client.aclose()


class StdioTransport(Transport):
    def __init__(self, cmd: str):
        super().__init__()
        self.cmd = cmd
        self.proc: asyncio.subprocess.Process | None = None
        self._read_task: asyncio.Task | None = None

    def is_alive(self) -> bool:
        # 进程存在且 returncode 为 None 表示进程还在运行
        return self.proc is not None and self.proc.returncode is None and not self._read_task.done()

    async def _read_loop(self):
        try:
            while True:
                line = await self.proc.stdout.readline()
                if not line: break
                await self.on_message(json.loads(line.decode()))
        except asyncio.CancelledError:  # 仅处理取消异常，其他异常抛出来
            ...

    async def send(self, payload: dict):
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        await self.proc.stdin.drain()

    async def __aenter__(self):
        self.proc = await asyncio.create_subprocess_shell(
            self.cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE
        )
        self._read_task = asyncio.create_task(self._read_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._read_task:
            self._read_task.cancel()
        if self.proc:
            if self.proc.stdin:
                self.proc.stdin.close()
            try:
                self.proc.kill()
                await self.proc.wait()
            except ProcessLookupError:
                pass


class StreamableHttpTransport(Transport):
    def __init__(self, url: str, client: AsyncClient | None = None):
        super().__init__()
        self.url = url.rstrip("/")
        self.client = client or AsyncClient(timeout=Timeout(
            connect=10.0,
            read=30.0,
            write=10.0,
            pool=10.0,
        ))
        self._session_id: str | None = None

    def is_alive(self) -> bool:
        return not self.client.is_closed

    async def send(self, payload: dict):
        if not self.is_alive():
            raise ConnectionError("Streamable HTTP transport is not alive")

        # Streamable HTTP 规范：通过 POST 发送 JSON-RPC 消息
        # 添加必要的请求头
        headers = {
            "Accept": "application/json,text/event-stream",
            "Content-Type": "application/json"
        }
        # 如果有会话ID，添加到请求头
        if self._session_id:
            headers["mcp-session-id"] = self._session_id

            # 保存会话ID（如果服务端返回）
        async with self.client.stream("POST", self.url, json=payload, headers=headers) as response:
            self._session_id = response.headers.get("mcp-session-id", self._session_id)
            # 根据 Content-Type 处理响应
            content_type = response.headers.get("content-type", "").partition(";")[0]
            if "text/event-stream" in content_type:
                event_source = EventSource(response)
                # 处理 SSE 流响应
                async for event in event_source.aiter_sse():
                    await self.on_message(json.loads(event.data))
            elif "application/json" in content_type:
                # 处理 JSON 响应 - 需要先读取内容
                content = await response.aread()
                data = json.loads(content.decode("utf-8"))
                await self.on_message(data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()