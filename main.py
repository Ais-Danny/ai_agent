from colorama import Fore, Style, init

from src.config.config_model import config
from src.entity.agent.langgraph_agent import Langgraph_Agent
from src.prompt import system_prompt
from src.extend.tool import list_files,read_file,write_file,run_cmd
from src.utils import print_watermark


config.langsmith_config.init_env() # 初始化环境变量
agent=Langgraph_Agent(config.llm_model,tools=[list_files,read_file,write_file,run_cmd],system_prompt=system_prompt)


# agent.memory.load("1") #加载历史会话
# print("myself:", agent.memory.get_history("1"))
# res = agent.invoke(r"在D:\Desktop创建一个对langchain框架的介绍文档",stream_func=print)
# print("ai_agent:", res)
# agent.memory.save("1") #保存历史会话(默认不保存)


def stream_func(role:str, content:str):
    """
    根据角色打印不同颜色
    """
    role_lower = role.lower()
    if role_lower in {"ai", "assistant"}:
        color = Fore.CYAN  # AI 输出青色
    elif role_lower == "tool":
        color = Fore.YELLOW  # 工具输出黄色
    elif role_lower == "error":
        color = Fore.RED
    else:
        color = Fore.WHITE  # 其他角色默认白色
    print(color + f"{role}: {content}")

while True:
    user_input = input("myself: ").strip()
    if user_input.lower() in {"exit", "quit"}:
        print("🔚 结束对话")
        break
    # 调用 agent.invoke 并实时打印迭代信息
    res = agent.invoke(user_input, thread_id="1", stream_func=stream_func)  # 假设你 invoke 支持 stream_func
    # 保存历史
    agent.memory.save("1")