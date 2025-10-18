from typing import List, Dict
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from src.config.config_entity import LLM_Model

class Agent:
    memory: MemorySaver
    system_prompt: str = None

    def __init__(self, model: LLM_Model, tools: List = [], system_prompt: str = None):
        """
        model: LLM_Model 对象，需要有 init_model() 方法返回 LangChain ChatModel
        tools: 初始工具列表
        """
        self.model = model.init_model()  # LangChain ChatModel
        self.tools = tools
        self.system_prompt = system_prompt
        self.memory = MemorySaver()
        self.graph = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.memory
        )

    def invoke(self, user_input: str, thread_id: str = "1"):
        messages_for_graph = []
        if self.system_prompt:
            messages_for_graph.append(("system", self.system_prompt))
        messages_for_graph.append(("user", user_input))
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke({"messages": messages_for_graph}, config)
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
