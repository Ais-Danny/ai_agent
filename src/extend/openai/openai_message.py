from typing import List

from langchain_core.messages  import BaseMessage

class Message:
    text:BaseMessage
    tool_calss: list=None
    def __init__(self, message:BaseMessage):
        self.text = message.content
        self.type = message.type
        self.tool_calss = getattr(message, 'tool_calls', None)

class OpenAIMessage:
    question_message:str #提问消息
    last_message:str #最后一条消息
    all_result_messages:list[Message]=[] #所有消息(包含递归调用消息)
    isOk:bool=True #是否正常返回
    error_data:str=None #错误信息
    def __init__(self, message_data:list=[],history_len:int=0):
        if len(message_data)>1:
            self.question_message = message_data[history_len].content #提问消息
            self.last_message = message_data[-1].content #所有消息
            self.history_len = history_len  #历史消息长度(对话前的长度)
            for i in range(self.history_len+1,len(message_data)): #跳过提问的消息
                self.all_result_messages.append(Message(message_data[i]))
    def set_error(self, error_data:str):
        self.isOk = False
        self.error_data = error_data

    
    def __str__(self):
        if not self.isOk:
            return f"Error: {self.error_data}"
        else:
            return self.last_message