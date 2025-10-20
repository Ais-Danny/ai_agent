from src.config.config_model import config
from src.entity.agent.langgraph_agent import Langgraph_Agent
from src.prompt import system_prompt
from src.extend.tool import list_files,read_file,write_file,run_cmd

config.langsmith_config.init_env() # 初始化环境变量
agent=Langgraph_Agent(config.llm_model,tools=[list_files,read_file,write_file,run_cmd],system_prompt=system_prompt)


# # --- 用户 A 对话 ---
# res1 = agent.invoke("你好，我是用户A", thread_id="user_A")
# print("user_A:", agent.get_last_response(res1))

# res2 = agent.invoke("你记得我刚才说了什么吗？", thread_id="user_A")
# print("user_A:", agent.get_last_response(res2))

# res3 = agent.invoke("再问你一次，我是谁？", thread_id="user_A")
# print("user_A:", agent.get_last_response(res3))


# # --- 用户 B 对话 ---
# res4 = agent.invoke("你好，我是用户B", thread_id="user_B")
# print("user_B:", agent.get_last_response(res4))

# res5 = agent.invoke("你记得我是谁吗？", thread_id="user_B")
# print("user_B:", agent.get_last_response(res5))

# res6 = agent.invoke("用户A说了什么？", thread_id="user_B")
# print("user_B:", agent.get_last_response(res6))


# res = agent.invoke("读取D:\Desktop\备忘录.txt文件的内容")
# print("ai_agent:", agent.get_last_response(res))



agent.memory.load("1")
res = agent.invoke(r"在D:\Desktop创建一个对langchain框架的介绍文档")
print("ai_agent:", agent.get_last_response(res))
agent.memory.save("1")