from src.config.config_model import config
from src.entity.agent.langgraph_agent import Langgraph_Agent
from src.prompt import system_prompt
from src.extend.tool import list_files,read_file,write_file,run_cmd

config.langsmith_config.init_env() # 初始化环境变量
agent=Langgraph_Agent(config.llm_model,tools=[list_files,read_file,write_file,run_cmd],system_prompt=system_prompt)

agent.memory.load("1") #加载历史会话
res = agent.invoke(r"在D:\Desktop创建一个对langchain框架的介绍文档")
print("ai_agent:", res)
agent.memory.save("1") #保存历史会话(默认不保存)