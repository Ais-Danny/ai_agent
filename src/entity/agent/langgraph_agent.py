from typing import List, Dict, Callable
from langgraph.prebuilt import create_react_agent
from langgraph.errors import GraphRecursionError

from src.extend.openai.summarizing_memory import HistoryMemory
from src.config.config_entity import LLM_Model
from src.extend.openai.openai_message import OpenAIMessage
from src.config.config_model import config

class Langgraph_Agent:
    memory: HistoryMemory
    system_prompt: str = None

    def __init__(self, model: LLM_Model, tools: List = [], system_prompt: str = None):
        """
        model: LLM_Model 对象，需要有 init_model() 方法返回 LangChain ChatModel
        tools: 初始工具列表
        system_prompt: llm模型系统提示信息
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

    def invoke(self, user_input: str, thread_id: str = "1",max_steps:int=None,stream_func: callable = None)->OpenAIMessage:
        """
        user_input: 提问内容
        thread_id:  会话id
        max_steps:  最大递归次数
        stream_func: 在流式调用时的回调函数(可用于打印递归过程)
        """
        if max_steps is None:
            max_steps =config.max_steps
        messages_for_graph = []
        if self.system_prompt:
            messages_for_graph.append(("system", self.system_prompt))
        history_messages = self.memory.get_history(thread_id)#获取历史消息
        history_len=1 #历史消息索引(起始索引，system消息默认占一条)
        if history_messages:
            history_len=len(history_messages)-1 #历史消息索引(起始索引，system消息默认占一条)
            messages_for_graph.extend(history_messages)
        messages_for_graph.append(("user", user_input))

        self.memory.add_message(thread_id, "user", user_input)#添加用户消息到历史消息
        try:
            # result = self.graph.invoke(
            #     {"messages": messages_for_graph},
            #     config={"recursion_limit": max_steps},
            # )
            # all_messages = OpenAIMessage(result['messages'],history_len)
            # self.memory.add_message(thread_id,"assistant", all_messages.last_message)#添加系统消息到历史消息

            events = self.graph.stream(
                {"messages": messages_for_graph},
                config={"recursion_limit": max_steps},
                stream_mode="values"
            )
            last_result = None
            for event in events:
                # event 就是一次迭代的结果
                msg = event["messages"][-1]
                # msg 可能是对象或 dict
                role = getattr(msg, "role", getattr(msg, "type", "unknown"))
                content = getattr(msg, "content", str(msg))
                if stream_func and last_result: #跳过第一条打印
                    stream_func(role,content)  # 即时输出
                last_result = event

            all_messages = OpenAIMessage(last_result['messages'], history_len)
            self.memory.add_message(thread_id, "assistant", all_messages.last_message)
        except GraphRecursionError:
            all_messages = OpenAIMessage().set_error("超过最大递归次数限制：{max_steps} 次")
            stream_func("error",all_messages) 
        except Exception as e:
            all_messages = OpenAIMessage().set_error(str(e))
            stream_func("error",all_messages)
        return all_messages


    def draw_graph(self, filename: str = "graph.png") -> str:
        """保存决策图"""
        png_bytes = self.graph.get_graph().draw_mermaid_png()
        with open(filename, "wb") as f:
            f.write(png_bytes)
        return filename
