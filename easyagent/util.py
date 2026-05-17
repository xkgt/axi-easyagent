import inspect
from typing import get_origin, Callable


def build_tool(func: Callable):
    """将函数转换为 OpenAI tool schema"""

    doc = inspect.getdoc(func) or ""

    # ======================================================
    # 1. 优先使用 warp_function 注入的 schema（推荐路径）
    # ======================================================
    if hasattr(func, "__input_schema__"):
        schema = func.__input_schema__

        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": doc,
                "parameters": schema,  # 已经是完整 JSON Schema
            }
        }

    # ======================================================
    # 2. fallback：没有 schema 才解析 signature
    # ======================================================
    sig = inspect.signature(func)

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        annotation = param.annotation

        # fallback 类型处理
        json_type = _python_type_to_json_type(annotation)

        properties[name] = {"type": json_type}

        if param.default == inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }
    }


def _python_type_to_json_type(python_type):
    """将 Python 类型转换为 JSON Schema 类型"""
    origin = get_origin(python_type)
    if origin is not None:
        python_type = origin
    if python_type is str:
        return "string"
    elif python_type is int:
        return "integer"
    elif python_type is float:
        return "number"
    elif python_type is bool:
        return "boolean"
    elif python_type is list:
        return "array"
    elif python_type is dict:
        return "object"
    else:
        return "string"  # 默认返回 string


def wrap_function(
    func,
    name: str,
    desc: str,
    argument_schema: dict,
):
    """
    MCP Tool Function Wrapper

    只做三件事：
    1. 设置函数名
    2. 设置函数描述
    3. 挂载原始 JSON Schema（供 AI / runtime 使用）
    """

    # --- 基础元信息 ---
    func.__name__ = name
    func.__doc__ = desc

    # --- 核心：保存完整 schema ---
    func.__input_schema__ = argument_schema

    return func