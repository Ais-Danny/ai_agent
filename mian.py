# pip install langchain langgraph openai pyautogui
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from langgraph.graph import StateGraph,START, END
from langchain_core.messages import ToolMessage
from typing import TypedDict,Annotated
from langgraph.graph.message import add_messages
from IPython.display import Image, display
from langchain_core.tools import tool
import pyautogui

@tool
def add(a: int, b: int) -> int:
    """Adds a and b."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiplies a and b."""
    return a * b

tools = [add, multiply]

# 1. 定义大模型
llm = ChatOllama(
    model="deepseek-v3.1:671b-cloud",  # 或 "gpt-3.5-turbo"
    temperature=0,
    api_key="YOUR_OPENAI_API_KEY",
)
llm_with_tools = llm.bind_tools(tools)

# 定义状态模型
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 定义节点函数
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 创建图形
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START,"chatbot")
graph_builder.add_edge("chatbot",END)

# 编译图形
graph = graph_builder.compile()

try:
    png_bytes = graph.get_graph().draw_mermaid_png()
    with open("graph.png", "wb") as f:
        f.write(png_bytes)
except Exception :
    # This requires some extra dependencies and is optional
    pass

