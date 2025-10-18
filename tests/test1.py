from src.config.config_model import config
from src.entity.agent.langgraph_agent import Langgraph_Agent

config.langsmith_config.init_env() # 初始化环境变量
agent=Langgraph_Agent(config.llm_model)


# history = agent.checkpointer.list(
#     config={"configurable": {"thread_id": "user_A"}}
# )

# for h in history:
#     print("CheckpointID:", h.checkpoint["id"])      # checkpoint 是 dict-like
#     print("Metadata:", h.metadata)

# --- 用户 A 对话 ---
res1 = agent.invoke("你好，我是用户A", thread_id="user_A")
print("user_A:", agent.get_last_response(res1))

res2 = agent.invoke("你记得我刚才说了什么吗？", thread_id="user_A")
print("user_A:", agent.get_last_response(res2))

res3 = agent.invoke("再问你一次，我是谁？", thread_id="user_A")
print("user_A:", agent.get_last_response(res3))


# --- 用户 B 对话 ---
res4 = agent.invoke("你好，我是用户B", thread_id="user_B")
print("user_B:", agent.get_last_response(res4))

res5 = agent.invoke("你记得我是谁吗？", thread_id="user_B")
print("user_B:", agent.get_last_response(res5))

res6 = agent.invoke("用户A说了什么？", thread_id="user_B")
print("user_B:", agent.get_last_response(res6))