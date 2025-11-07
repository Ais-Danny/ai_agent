from colorama import Fore

# 导入启动打印功能
from src.utils import print_watermark

from src.config.config_model import config
from src.entity.agent.langgraph_agent import Langgraph_Agent
from src.prompt import system_prompt
from src.extend.tool import list_files, read_file, write_file, run_cmd

# 打印启动信息
print_watermark()

# 初始化环境变量
config.langsmith_config.init_env()

# 创建智能体实例
agent = Langgraph_Agent(
    config.llm_model,
    tools=[list_files, read_file, write_file, run_cmd],
    system_prompt=system_prompt
)

def stream_func(role: str, content: str):
    """根据角色打印不同颜色的输出"""
    color_map = {
        "ai": Fore.GREEN,
        "assistant": Fore.GREEN,
        "tool": Fore.YELLOW,
        "error": Fore.RED,
        "user": Fore.BLUE
    }
    color = color_map.get(role.lower(), Fore.WHITE)
    reset = Fore.RESET
    print(f"{color}{role}: {content}{reset}")

if __name__ == "__main__":
    while True:
        # 使用蓝色显示用户输入提示符
        user_input = input(f"{Fore.BLUE}myself: {Fore.RESET}").strip()
        if user_input.lower() in {"exit", "quit"}:
            print(f"{Fore.WHITE}🔚 结束对话{Fore.RESET}")
            break
        # 调用智能体并实时打印
        res = agent.invoke(user_input, thread_id="1", stream_func=stream_func)
        # 自动保存历史对话
        agent.memory.save("1")