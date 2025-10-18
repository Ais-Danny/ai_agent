from typing import List, Dict, Callable, Any
from langgraph.prebuilt import create_react_agent
from src.config.config_entity import LLM_Model

class HistoryMemory:
    """可管理历史的内存型存储"""
    def __init__(self):
        self.store: Dict[str, List[Dict[str, Any]]] = {}

    def add_message(self, thread_id: str, role: str, content: str):
        if thread_id not in self.store:
            self.store[thread_id] = []
        self.store[thread_id].append({"role": role, "content": content})

    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        return self.store.get(thread_id, [])

    def clear_history(self, thread_id: str):
        if thread_id in self.store:
            del self.store[thread_id]

    def list_threads(self) -> List[str]:
        return list(self.store.keys())
    
class Memory_thread:
    """管理一个线程的内存型存储"""
    def __init__(self, thread_id: str, model: LLM_Model):
        self.thread_id = thread_id