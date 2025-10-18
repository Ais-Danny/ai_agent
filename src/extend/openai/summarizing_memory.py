import json, os
from typing import List, Dict
from pathlib import Path
from langgraph.prebuilt import create_react_agent

from src.config.config_model import config
from src.prompt import summary_prompt


class MemoryThread:
    """管理单个线程的内存型存储"""

    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.history_memory: List = []

    def add_message(self, role: str, content: str):
        self.history_memory.append((role, content))

    def clear_history(self):
        self.history_memory.clear()

    def get_history(self) -> List:
        """超过限制时生成摘要"""
        if sum(len(r) + len(c) for r, c in self.history_memory) > config.max_token_limit:
            summary = self.__create_summary()
            self.clear_history()
            self.add_message("system", summary)
        return self.history_memory

    def __create_summary(self) -> str:
        messages = self.history_memory.copy()
        graph = create_react_agent(model=config.summary_model.init_model(), tools=[])
        messages.append(("user", summary_prompt))
        result = graph.invoke({"messages": messages})
        return result.get("output", str(result))

    def save(self, file_path: str):
        """保存历史到硬盘（自动建目录）"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.history_memory, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, file_path: str):
        """从硬盘加载历史"""
        path = Path(file_path)
        if path.exists():
            self.history_memory = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.history_memory = []


class HistoryMemory:
    """管理多个线程的内存型存储"""

    def __init__(self):
        self._dict_memory: Dict[str, MemoryThread] = {}

    def _get_thread(self, thread_id: str) -> MemoryThread:
        if thread_id not in self._dict_memory:
            self._dict_memory[thread_id] = MemoryThread(thread_id)
        return self._dict_memory[thread_id]

    def add_message(self, thread_id: str, role: str, content: str):
        self._get_thread(thread_id).add_message(role, content)

    def get_history(self, thread_id: str) -> List:
        return self._get_thread(thread_id).get_history()

    def clear_history(self, thread_id: str):
        self._get_thread(thread_id).clear_history()

    def list_threads(self) -> List[str]:
        return list(self._dict_memory.keys())

    def save(self, thread_id: str, file_path: str = ""):
        file_path = file_path or f"./data/memory/{thread_id}.json"
        self._get_thread(thread_id).save(file_path)

    def load(self, thread_id: str, file_path: str = ""):
        file_path = file_path or f"./data/memory/{thread_id}.json"
        self._get_thread(thread_id).load(file_path)
