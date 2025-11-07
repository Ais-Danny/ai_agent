#通用工具
import pyfiglet
from colorama import Fore, Style, init

# 初始化 colorama 支持 Windows 终端颜色
init(autoreset=True)

def print_watermark():
    ascii_text = pyfiglet.figlet_format("AI AGENT", font="big")
    print(Fore.CYAN + ascii_text)
    print(Fore.YELLOW + "Author : Ais-Danny")
    print(Fore.BLUE + Style.BRIGHT + "Powered by: https://github.com/Ais-Danny/ai_agent.git")
    print(Fore.BLUE + "Version: V1.0.0.1")
    print(Fore.MAGENTA + "="*60)
