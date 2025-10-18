from abc import ABC, abstractmethod
from typing import List, Dict, Callable, Optional

class BaseAgent(ABC):
    """
    所有 Agent 的抽象基类。
    定义通用接口和共享属性。
    """

    def __init__(
        self,
        tools: Optional[List[Callable]] = None,
        system_prompt: Optional[str] = None
    ):
        self.tools: List[Callable] = tools or []
        self.system_prompt: Optional[str] = system_prompt

    # --- 工具管理（通用实现，子类可复用）---
    def add_tool(self, tool: Callable):
        """添加工具"""
        self.tools.append(tool)

    def remove_tool(self, tool_name: str):
        """根据工具名称移除工具"""
        self.tools = [
            t for t in self.tools
            if getattr(t, "__name__", str(t)) != tool_name
        ]

    def clear_tools(self, tools: List[Callable]):
        """替换工具列表"""
        self.tools = tools[:]

    def list_tools(self) -> List[str]:
        """列出当前工具名称"""
        return [getattr(t, "__name__", str(t)) for t in self.tools]

    # --- 抽象方法：子类必须实现 ---
    @abstractmethod
    def invoke(self, user_input: str, thread_id: str = "1") -> Dict:
        """执行一次对话调用"""
        pass

    @abstractmethod
    def get_last_response(self, result: Dict) -> str:
        """从结果中提取最后一条 LLM 回复"""
        pass

    @abstractmethod
    def _init_graph(self):
        """初始化内部执行图（如 LangGraph Graph）"""
        pass

    # --- 可选：提供默认的 draw_graph（子类可覆盖）---
    def draw_graph(self, filename: str = "graph.png") -> str:
        """
        可视化执行流程图（如果支持）。
        子类若不支持可抛出 NotImplementedError。
        """
        raise NotImplementedError("This agent does not support graph visualization.")