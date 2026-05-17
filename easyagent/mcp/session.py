import asyncio
import uuid
from importlib.metadata import version
from typing import overload, Callable, Awaitable, Any

from httpx import AsyncClient

from easyagent.mcp.transport import Transport, SSETransport, StdioTransport, StreamableHttpTransport
from easyagent.util import wrap_function


class MCPSession:
    def __init__(self, transport: Transport, timeout: int = 10):
        self.transport = transport
        self.timeout = timeout
        self.transport.on_message = self._process
        self._futures: dict[str, asyncio.Future] = {}

    @overload
    async def post(self, method: str, params: dict) -> dict:
        ...

    @overload
    async def post(self, method: str, params: dict, notification: bool) -> Any | None:
        ...

    async def post(self, method: str, params: dict, notification=False) -> Any | None:
        if not self.transport.is_alive():
            raise RuntimeError("Transport is not alive")
        id_ = uuid.uuid4().hex
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        if not notification:
            self._futures[id_] = asyncio.Future()
            payload["id"] = id_
        try:
            await self.transport.send(payload)
        except Exception as e:
            if not notification:
                del self._futures[id_]
            raise e
        if not notification:
            try:
                return await asyncio.wait_for(self._futures[id_], timeout=self.timeout)
            finally:
                del self._futures[id_]

    async def list_tools(self) -> list[Callable[..., Awaitable]]:
        """根据MCP返回的工具列表，直接构建出一套可调用的函数"""
        schemas = (await self.post("tools/list", {}))["tools"]
        tools = []
        for schema in schemas:
            # 避免闭包问题
            def create_tool(_schema):
                async def e(**kwargs):
                    return (await self.post("tools/call", {"name": _schema["name"], "arguments": kwargs}))["content"]
                func = wrap_function(e, _schema["name"], _schema["description"], _schema["inputSchema"])
                return func

            func = create_tool(schema)
            func.__qualname__ = f"MCP function {schema['name']} from {self.transport}"
            tools.append(func)
        return tools

    async def _protocol_init(self):
        await self.post("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {
                "name": "easyagent",
                "version": version("axi-easyagent")
            }
        })
        await self.post("notifications/initialized", {}, notification=True)

    async def _process(self, msg: dict):
        msg_id = msg.get("id", None)
        if "error" in msg:
            if msg_id in self._futures:  # None不可能在_future，所以也可以同时排除没有id key的情况
                self._futures[msg["id"]].set_exception(RuntimeError(msg))
            else:
                raise RuntimeError(msg)
        elif msg_id in self._futures:
            self._futures[msg["id"]].set_result(msg["result"])

    async def __aenter__(self):
        await self.transport.__aenter__()
        try:
            await self._protocol_init()
            return self
        except Exception as e:
            await self.transport.__aexit__(None, None, None)
            raise e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.transport.__aexit__(exc_type, exc_val, exc_tb)

    @classmethod
    def sse(cls, sse_url: str, client: AsyncClient | None = None):
        return cls(SSETransport(sse_url, client=client))

    @classmethod
    def stdio(cls, cmd: str):
        return cls(StdioTransport(cmd))

    @classmethod
    def streamable_http(cls, url: str, client: AsyncClient | None = None):
        return cls(StreamableHttpTransport(url, client=client))