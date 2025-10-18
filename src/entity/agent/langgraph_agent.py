from typing import List, Dict, Callable
from langgraph.prebuilt import create_react_agent
from src.extend.openai.summarizing_memory import HistoryMemory
from src.config.config_entity import LLM_Model

class Langgraph_Agent:
    memory: HistoryMemory
    system_prompt: str = None

    def __init__(self, model: LLM_Model, tools: List = [], system_prompt: str = None):
        """
        model: LLM_Model 对象，需要有 init_model() 方法返回 LangChain ChatModel
        tools: 初始工具列表
        """
        self.model = model.init_model()  # LangChain ChatModel
        self.tools: List = tools[:]  # 工具列表可动态修改
        self.system_prompt = system_prompt
        self.memory = HistoryMemory()
        self._init_graph()

    def _init_graph(self):
        """初始化或刷新 graph 对象"""
        self.graph = create_react_agent(
            model=self.model,
            tools=self.tools
        )

    # --- 工具管理方法 ---
    def add_tool(self, tool: Callable):
        """添加工具并刷新 graph"""
        self.tools.append(tool)
        self._init_graph()

    def remove_tool(self, tool_name: str):
        """根据工具名称移除工具并刷新 graph"""
        self.tools = [t for t in self.tools if getattr(t, "__name__", None) != tool_name]
        self._init_graph()

    def clear_tools(self,tools: List):
        """替换工具列表并刷新 graph"""
        self.tools = tools
        self._init_graph()

    def list_tools(self) -> List[str]:
        """返回当前工具列表名称"""
        return [getattr(t, "__name__", str(t)) for t in self.tools]

    # --- 核心功能 ---
    def invoke(self, user_input: str, thread_id: str = "1"):
        messages_for_graph = []
        if self.system_prompt:
            messages_for_graph.append(("system", self.system_prompt))
        history_messages = self.memory.get_history(thread_id)#获取历史消息
        if history_messages:
            messages_for_graph.extend(history_messages)
        messages_for_graph.append(("user", user_input))

        self.memory.add_message(thread_id, "user", user_input)#添加用户消息到历史消息
        result = self.graph.invoke({"messages": messages_for_graph})
        self.memory.add_message(thread_id,"assistant", self.get_last_response(result))#添加系统消息到历史消息
        return result

    def get_last_response(self, result: Dict) -> str:
        """获取最后一次 LLM 响应文本"""
        return result["messages"][-1].content if "messages" in result else None

    def draw_graph(self, filename: str = "graph.png") -> str:
        """保存决策图"""
        png_bytes = self.graph.get_graph().draw_mermaid_png()
        with open(filename, "wb") as f:
            f.write(png_bytes)
        return filename
