import inspect
from typing import get_type_hints, Callable


def build_tool(func: Callable):
    """将函数包装成 OpenAI API 的 tool 参数格式"""
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    # 获取函数描述
    doc = inspect.getdoc(func) or ""

    # 构建参数 schema
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        # 从 signature 直接获取注解，保留 Annotated 信息
        param_annotation = param.annotation
        
        # 处理 Annotated 类型
        if hasattr(param_annotation, '__metadata__'):
            # Annotated[type, "description"]
            actual_type = param_annotation.__args__[0]
            description = param_annotation.__metadata__[0] if param_annotation.__metadata__ else ""
        else:
            actual_type = param_annotation
            description = ""

        # 转换 Python 类型为 JSON Schema 类型
        json_type = _python_type_to_json_type(actual_type)

        properties[param_name] = {
            "type": json_type
        }
        if description:
            properties[param_name]["description"] = description

        # 如果没有默认值，则为必需参数
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    # 构建 tool 结构
    tool = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }

    return tool


def _python_type_to_json_type(python_type):
    """将 Python 类型转换为 JSON Schema 类型"""
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