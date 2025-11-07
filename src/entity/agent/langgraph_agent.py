from typing import List, Callable
from langgraph.prebuilt import create_react_agent
from langgraph.errors import GraphRecursionError

from src.extend.openai.summarizing_memory import HistoryMemory
from src.config.config_entity import LLM_Model
from src.extend.openai.openai_message import OpenAIMessage
from src.config.config_model import config

class Langgraph_Agent:
    def __init__(self, model: LLM_Model, tools: List = None, system_prompt: str = None):
        """
        初始化LangGraph智能体
        
        Args:
            model: LLM_Model对象，包含init_model()方法
            tools: 工具列表
            system_prompt: 系统提示信息
        """
        self.model = model.init_model()
        self.tools = tools.copy() if tools else []
        self.system_prompt = system_prompt
        self.memory = HistoryMemory()
        self._init_graph()

    def _init_graph(self):
        """初始化或刷新graph对象"""
        self.graph = create_react_agent(model=self.model, tools=self.tools)

    # --- 工具管理方法 ---
    def add_tool(self, tool: Callable):
        """添加工具并刷新graph"""
        self.tools.append(tool)
        self._init_graph()

    def remove_tool(self, tool_name: str):
        """根据工具名称移除工具并刷新graph"""
        self.tools = [t for t in self.tools if getattr(t, "__name__", None) != tool_name]
        self._init_graph()

    def set_tools(self, tools: List):
        """替换工具列表并刷新graph"""
        self.tools = tools.copy()
        self._init_graph()

    def list_tools(self) -> List[str]:
        """返回当前工具列表名称"""
        return [getattr(t, "__name__", str(t)) for t in self.tools]

    def invoke(self, user_input: str, thread_id: str = "1", max_steps: int = None, 
               stream_func: Callable = None) -> OpenAIMessage:
        """
        调用智能体处理用户输入
        
        Args:
            user_input: 提问内容
            thread_id: 会话id
            max_steps: 最大递归次数
            stream_func: 流式调用时的回调函数
            
        Returns:
            OpenAIMessage: 处理结果
        """
        # 准备消息
        max_steps = max_steps or config.max_steps
        messages = []
        
        # 添加系统提示
        if self.system_prompt:
            messages.append(("system", self.system_prompt))
            
        # 添加历史消息
        history_messages = self.memory.get_history(thread_id)
        history_len = len(history_messages) if history_messages else 1
        if history_messages:
            messages.extend(history_messages)
            history_len = len(history_messages)
        
        # 添加当前用户输入
        messages.append(("user", user_input))
        self.memory.add_message(thread_id, "user", user_input)
        
        # 处理响应
        try:
            events = self.graph.stream(
                {"messages": messages},
                config={"recursion_limit": max_steps},
                stream_mode="values"
            )
            
            last_result = None
            for event in events:
                msg = event["messages"][-1]
                role = getattr(msg, "role", getattr(msg, "type", "unknown"))
                content = getattr(msg, "content", str(msg))
                
                # 跳过第一次迭代的打印
                if stream_func and last_result:
                    stream_func(role, content)
                    
                last_result = event
            
            # 处理最终结果
            all_messages = OpenAIMessage(last_result['messages'], history_len)
            self.memory.add_message(thread_id, "assistant", all_messages.last_message)
            
        except GraphRecursionError:
            all_messages = OpenAIMessage().set_error(f"超过最大递归次数限制：{max_steps} 次")
            if stream_func:
                stream_func("error", str(all_messages))
                
        except Exception as e:
            all_messages = OpenAIMessage().set_error(str(e))
            if stream_func:
                stream_func("error", str(all_messages))
                
        return all_messages

    def draw_graph(self, filename: str = "graph.png") -> str:
        """保存决策图"""
        png_bytes = self.graph.get_graph().draw_mermaid_png()
        with open(filename, "wb") as f:
            f.write(png_bytes)
        return filename
