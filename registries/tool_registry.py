from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable
    requires_network: bool = False


_REGISTRY: Dict[str, Tool] = {}


def register(name: str, description: str, parameters: dict,
             requires_network: bool = False):
    def wrapper(func):
        _REGISTRY[name] = Tool(name, description, parameters, func, requires_network)
        return func
    return wrapper


def get_tool(name: str) -> Optional[Tool]:
    return _REGISTRY.get(name)


def list_tools() -> List[Tool]:
    return list(_REGISTRY.values())


def names() -> List[str]:
    return list(_REGISTRY.keys())


def execute(name: str, args: dict) -> str:
    tool = _REGISTRY.get(name)
    if not tool:
        return f"未知工具: {name}"
    # 网络门禁先留着，等 NETWORK_AVAILABLE 全局变量就位后启用
    # if tool.requires_network and not NETWORK_AVAILABLE:
    #     return f"❌ 当前无网络，{name} 不可用"
    try:
        return tool.func(**args)
    except Exception as e:
        return f"工具失败: {e}"


def get_schemas(names_filter: list = None) -> list:
    tools = list(_REGISTRY.values())
    if names_filter:
        tools = [t for t in tools if t.name in names_filter]
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
        }
        for t in tools
    ]


def clear():
    _REGISTRY.clear()