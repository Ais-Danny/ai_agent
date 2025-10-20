
class OpenAIMessage:
    last_message:str #最后一条消息
    def __init__(self, message_data:dict,history_len:int=0):
        self.message = message_data #所有消息
        self.history_len = history_len  #历史消息长度(对话前的长度)

    def _get_message(self):
        
        for i in range(self.history_len):
            
            print(self.message[i]['text'])
        return self.message